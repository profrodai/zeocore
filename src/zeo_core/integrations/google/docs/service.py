"""
Google Docs integration service for zeo_core.

This module provides the main service class for Google Docs integration:
`documents.get`, `documents.create`, and `documents.batchUpdate` (per
RULING-408 DESIGN-01, exactly these 3 methods -- no more, no less, no
escape-hatch method), plus two index-free convenience methods built on top
of `batchUpdate` (`replace_text`, `append_text`) and a recursive plain-text
extraction helper for `get_document`'s "TOMORROW'S DEMO REQUIREMENT".

CONFIG TIMING (RULING-408 DESIGN-04 / item 4): this class follows
`google/mail/service.py`'s DEFERRED CONFIG pattern, not `drive/service.py`'s
or `calendar/service.py`'s eager pattern. Config resolution (calling the
config provider, constructing `GoogleAuthProvider`, calling
`get_credentials()`, calling `googleapiclient.discovery.build(...)`) all
happens INSIDE `initialize()`, never in `__init__` -- constructing this
service from a fresh directory with no config file must never raise;
`initialize()` is where a genuine missing-config failure surfaces, and only
there.

ERROR-HANDLING SHAPE (per drive/service.py, copied for its shape only, not
its config timing): every public method wraps its SDK call in an inner
try/except that logs and returns an `IntegrationResult.error_result(...)`,
inside an outer try/except catching `ZeoApiError` / `ZeoBaseAuthError` /
`Exception` around the whole method body.

Structural precedent for "no separate operations/ package": `google/
calendar/service.py` -- everything inline in this file, matching the
identical dead/unwired-package concern documented there for drive's own
operations/ package (not repeated here).
"""

import logging
from typing import Any, cast

from zeo_core.core.errors import (
    ZeoApiError,
    ZeoBaseAuthError,
    ZeoIntegrationError,
)
from zeo_core.integrations.core.base import BaseIntegrationService
from zeo_core.integrations.core.protocols import ConfigProviderProtocol
from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.google.auth import GoogleAuthProvider
from zeo_core.integrations.google.config import GoogleConfigProvider
from zeo_core.integrations.google.docs.protocols import (
    DocsIntegrationProtocol,
    DocsService,
    GoogleCredentials,
)
from zeo_core.integrations.google.docs.request_builder import DocsRequestBuilder

# mypy's nonetype-type check rejects `types.NoneType` used as a type
# expression directly; google/drive/service.py and google/mail/service.py
# already established this same module-level alias (`NoneType =
# type(None)`) as the fix for the identical pattern -- matched here rather
# than inventing a new idiom.
NoneType = type(None)


class GoogleDocsService(BaseIntegrationService, DocsIntegrationProtocol):
    """Integration service for Google Docs."""

    # Per RULING-408 item 5: narrower than Drive's `.../auth/drive` --
    # read-write documents scope only, since `create` and `batchUpdate`
    # need write access but nothing here needs Drive-wide file access.
    SCOPES: list[str] = [
        "https://www.googleapis.com/auth/documents",
    ]

    def __init__(
        self,
        client_secrets_file: str | None = None,
        credentials_file: str | None = None,
        config_path: str | None = None,
        scopes: list[str] | None = None,
        log_level: int = logging.INFO,
    ) -> None:
        """
        Initialize the Google Docs integration service.

        Per the deferred-config pattern (mirroring `google/mail/service.py`
        exactly): NO config resolution, auth provider construction, or API
        client construction happens here. Those all happen inside
        `initialize()`. Constructing this service, even from a fresh
        directory with no config file anywhere, must never raise.

        Args:
            client_secrets_file: Path to the client secrets file.
            credentials_file: Path to the credentials file.
            config_path: Path to the configuration file.
            scopes: OAuth scopes for the Docs API.
            log_level: Logging level.
        """
        config_provider = GoogleConfigProvider("docs", log_level)
        super().__init__(
            config_provider=config_provider,
            auth_provider=None,
            config=None,
            config_path=config_path,
            log_level=log_level,
        )

        # If explicit parameters are provided, override configuration from
        # file -- same "custom_config short-circuits file loading" shape as
        # google/mail/service.py's own __init__.
        self.custom_config: dict[str, object] = {}
        if client_secrets_file and credentials_file:
            self.custom_config = {
                "client_secrets_file": client_secrets_file,
                "credentials_file": credentials_file,
            }

        self.scopes: list[str] = list(scopes) if scopes is not None else self.SCOPES

        self.auth_provider: GoogleAuthProvider | None = None
        # Typed Any, matching drive/service.py's `self.drive_service: Any`
        # and calendar/service.py's `self.calendar_service: Any` convention
        # (2 of the 3 structural siblings; mail is the outlier with a real
        # Protocol type). A real `DocsService | None` annotation forces
        # mypy strict to check every `self.docs_service.documents()...`
        # call site against `DocsDocumentsResource`'s exact signature,
        # which a bare `unittest.mock.MagicMock()` (this package's test
        # convention, matching calendar/test_service.py's SDK-boundary
        # mocking style -- see docs/protocols.py's own docstring) does not
        # structurally satisfy. `Any` here matches the two-out-of-three
        # sibling precedent and keeps tests mocking at the real SDK
        # boundary rather than needing a hand-built Protocol-conforming
        # mock class.
        self.docs_service: Any = None
        self.config: dict[str, object] = {}

    @property
    def name(self) -> str:
        """Get the name of the integration."""
        return "GoogleDocs"

    @property
    def version(self) -> str:
        """Get the version of the integration."""
        return "1.0.0"

    def _require_config_provider(self) -> ConfigProviderProtocol:
        """Return `self.config_provider`, narrowed to non-None.

        `self.config_provider` is typed `ConfigProviderProtocol | None` on
        the base class, but `__init__` always constructs and passes a real
        `GoogleConfigProvider` before `super().__init__` -- never `None`
        for this concrete class (same reasoning as
        `GoogleMailService._require_config_provider`). Raises if that
        invariant is ever violated (defensive, not expected).
        """
        if self.config_provider is None:
            raise ZeoIntegrationError(
                "GoogleDocsService has no config_provider configured"
            )
        return self.config_provider

    def _initialize_config(self) -> dict[str, object] | None:
        """
        Initialize configuration from parameters or config file.

        Returns:
            The initialized configuration or None if failed.

        Raises:
            ZeoIntegrationError: If configuration initialization fails in
                expected ways.
        """
        try:
            if self.custom_config:
                self.config = self.custom_config
            else:
                config_provider = self._require_config_provider()
                config_result = config_provider.load_config(self.config_path)
                if not config_result.success or not config_result.content:
                    raise ZeoIntegrationError(
                        "Failed to load configuration from file", {}
                    )
                self.config = config_result.content

            return self.config
        except ZeoIntegrationError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize configuration: {e}")
            return None

    def initialize(self) -> IntegrationResult[NoneType]:
        """
        Initialize the Google Docs service.

        Returns:
            IntegrationResult indicating success or failure.
        """
        init_result: IntegrationResult[NoneType] = super().initialize()
        if not init_result.success:
            return init_result

        try:
            config: dict[str, object] | None = self._initialize_config()
            if config is None:
                self._initialized = False
                return IntegrationResult.error_result(
                    "Failed to initialize configuration"
                )

            client_secrets_file: str = str(config["client_secrets_file"])
            credentials_file_value: object = config.get("credentials_file")
            credentials_file: str | None = (
                str(credentials_file_value)
                if credentials_file_value is not None
                else None
            )

            self.auth_provider = GoogleAuthProvider(
                client_secrets_file=client_secrets_file,
                credentials_file=credentials_file,
                scopes=self.scopes,
                log_level=self.log_level,
            )

            try:
                credentials = self.auth_provider.get_credentials()
            except ZeoBaseAuthError as auth_error:
                self.logger.error(f"Authentication failed: {auth_error}")
                return IntegrationResult.error_result(
                    f"Failed to authenticate with Google Docs: {auth_error}"
                )

            try:
                from googleapiclient.discovery import build

                self.docs_service = cast(
                    DocsService,
                    build(
                        "docs",
                        "v1",
                        credentials=cast(GoogleCredentials, credentials),
                    ),
                )
            except Exception as api_error:
                raise ZeoApiError(
                    f"Failed to initialize Google Docs API: {api_error}",
                    service="Google Docs",
                    api_method="build",
                    original_error=api_error,
                ) from api_error

            self._initialized = True
            return IntegrationResult.success_result(
                message="Google Docs service initialized successfully"
            )
        except ZeoApiError as e:
            self._initialized = False
            self.logger.error(f"API error during initialization: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self._initialized = False
            self.logger.error(f"Authentication error during initialization: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self._initialized = False
            self.logger.error(f"Failed to initialize Google Docs service: {e}")
            return IntegrationResult.error_result(
                f"Failed to initialize Google Docs service: {e}"
            )

    # ------------------------------------------------------------------
    # Plain-text extraction (recursive body walk)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_paragraph_text(paragraph: dict[str, Any]) -> str:
        """
        Concatenate the `textRun.content` strings of a single `paragraph`
        StructuralElement's `elements` list, in order.

        Args:
            paragraph: A Docs API `Paragraph` object (the value of a
                StructuralElement's `"paragraph"` key).

        Returns:
            The concatenated plain text of this paragraph's text runs.
        """
        text_parts: list[str] = []
        for element in paragraph.get("elements", []):
            if not isinstance(element, dict):
                continue
            text_run = element.get("textRun")
            if isinstance(text_run, dict):
                content = text_run.get("content")
                if isinstance(content, str):
                    text_parts.append(content)
        return "".join(text_parts)

    @classmethod
    def _extract_table_text(cls, table: dict[str, Any]) -> str:
        """
        Recursively walk a Docs API `table` element's cells and concatenate
        their plain text, in row-then-column order.

        A `table` has `tableRows` -> each row has `tableCells` -> each cell
        has its own `content` list of `StructuralElement`s (which may
        themselves contain further nested tables) -- extracted out of
        `_extract_structural_elements_text` to keep that method's own
        branch count under the C901 threshold, same reasoning as
        `google/config.py`'s `_apply_nested_integrations_google`/
        `_apply_direct_service_key` split; behavior unchanged from the
        original inline block.

        Args:
            table: A Docs API `Table` object (the value of a
                StructuralElement's `"table"` key).

        Returns:
            The concatenated plain text of every text run inside this
            table's cells, in order.
        """
        text_parts: list[str] = []
        for row in table.get("tableRows", []):
            if not isinstance(row, dict):
                continue
            for cell in row.get("tableCells", []):
                if not isinstance(cell, dict):
                    continue
                cell_content = cell.get("content", [])
                if isinstance(cell_content, list):
                    text_parts.append(
                        cls._extract_structural_elements_text(cell_content)
                    )
        return "".join(text_parts)

    @classmethod
    def _extract_structural_elements_text(cls, elements: list[dict[str, Any]]) -> str:
        """
        Recursively walk a list of Docs API `StructuralElement`s and
        concatenate all plain text found, in document order.

        Body content is a list of `StructuralElement`s. The ones that carry
        text directly are `paragraph` elements. Two other kinds nest MORE
        `StructuralElement`s inside themselves and must be walked
        recursively rather than skipped:

        - `table`: has `tableRows` -> each row has `tableCells` -> each
          cell has its own `content` list of `StructuralElement`s (which
          may themselves contain further nested tables). See
          `_extract_table_text` for that walk.
        - `tableOfContents`: has its own `content` list of
          `StructuralElement`s (typically paragraphs).

        Args:
            elements: A list of Docs API `StructuralElement` dicts (e.g.
                `document["body"]["content"]`, or a table cell's own
                `content` list).

        Returns:
            The concatenated plain text of every text run found while
            walking `elements` and any structures nested inside them, in
            order.
        """
        text_parts: list[str] = []
        for element in elements:
            if not isinstance(element, dict):
                continue

            paragraph = element.get("paragraph")
            if isinstance(paragraph, dict):
                text_parts.append(cls._extract_paragraph_text(paragraph))
                continue

            table = element.get("table")
            if isinstance(table, dict):
                text_parts.append(cls._extract_table_text(table))
                continue

            toc = element.get("tableOfContents")
            if isinstance(toc, dict):
                toc_content = toc.get("content", [])
                if isinstance(toc_content, list):
                    text_parts.append(
                        cls._extract_structural_elements_text(toc_content)
                    )
                continue

        return "".join(text_parts)

    @classmethod
    def _extract_text(cls, document: dict[str, Any]) -> str:
        """
        Recursively walk a Docs API document's `body.content` structure and
        concatenate all `textRun.content` strings in document order.

        Args:
            document: A Docs API `Document` resource dict (as returned by
                `documents.get`).

        Returns:
            The document's plain text.
        """
        body = document.get("body")
        if not isinstance(body, dict):
            return ""
        content = body.get("content", [])
        if not isinstance(content, list):
            return ""
        return cls._extract_structural_elements_text(content)

    # ------------------------------------------------------------------
    # documents.get
    # ------------------------------------------------------------------

    def get_document(self, document_id: str) -> IntegrationResult[dict[str, Any]]:
        """
        Retrieve a document by ID (wraps `documents.get`).

        Args:
            document_id: ID of the document to retrieve.

        Returns:
            IntegrationResult containing the full document resource dict.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            if self.docs_service is None:
                return IntegrationResult.error_result(
                    "Google Docs service is not initialized"
                )

            try:
                document = (
                    self.docs_service.documents().get(documentId=document_id).execute()
                )
            except Exception as api_error:
                self.logger.error(f"Failed to get document: {api_error}")
                return IntegrationResult.error_result(
                    f"Failed to get document from Google Docs: {api_error}"
                )

            return IntegrationResult.success_result(
                content=cast(dict[str, Any], document),
                message=f"Retrieved document {document_id}",
            )
        except ZeoApiError as e:
            self.logger.error(f"API error during getting document: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during getting document: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to get document: {e}")
            return IntegrationResult.error_result(
                f"Failed to get document from Google Docs: {e}"
            )

    def get_document_text(self, document_id: str) -> IntegrationResult[str]:
        """
        Retrieve a document and flatten its body to plain text.

        Convenience wrapper around `get_document` plus the recursive
        `_extract_text` body walk (see that method's docstring for how
        tables and table-of-contents elements are handled recursively,
        not just flat top-level paragraphs).

        Args:
            document_id: ID of the document to retrieve.

        Returns:
            IntegrationResult containing the document's plain text.
        """
        doc_result = self.get_document(document_id)
        if not doc_result.success or doc_result.content is None:
            return IntegrationResult.error_result(
                doc_result.error or "Failed to get document"
            )

        try:
            text = self._extract_text(doc_result.content)
            return IntegrationResult.success_result(
                content=text,
                message=f"Extracted text from document {document_id}",
            )
        except Exception as e:
            self.logger.error(f"Failed to extract document text: {e}")
            return IntegrationResult.error_result(
                f"Failed to extract text from document {document_id}: {e}"
            )

    # ------------------------------------------------------------------
    # documents.create
    # ------------------------------------------------------------------

    def create_document(self, title: str) -> IntegrationResult[dict[str, Any]]:
        """
        Create a new, empty document with the given title (wraps
        `documents.create`).

        Args:
            title: Title of the new document.

        Returns:
            IntegrationResult containing the created document resource dict
            (includes `documentId`).
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            if self.docs_service is None:
                return IntegrationResult.error_result(
                    "Google Docs service is not initialized"
                )

            body: dict[str, object] = {"title": title}
            try:
                document = self.docs_service.documents().create(body=body).execute()
            except Exception as api_error:
                self.logger.error(f"Failed to create document: {api_error}")
                return IntegrationResult.error_result(
                    f"Failed to create document in Google Docs: {api_error}"
                )

            return IntegrationResult.success_result(
                content=cast(dict[str, Any], document),
                message=f"Created document '{title}'",
            )
        except ZeoApiError as e:
            self.logger.error(f"API error during creating document: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during creating document: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to create document: {e}")
            return IntegrationResult.error_result(
                f"Failed to create document in Google Docs: {e}"
            )

    # ------------------------------------------------------------------
    # documents.batchUpdate (+ index-free convenience methods)
    # ------------------------------------------------------------------

    def batch_update(
        self, document_id: str, requests: list[dict[str, Any]]
    ) -> IntegrationResult[dict[str, Any]]:
        """
        Apply a batch of update requests to a document (wraps
        `documents.batchUpdate`).

        Per RULING-408 DESIGN-03: `requests` is routed through
        `DocsRequestBuilder`, which reverse-sorts by body-anchoring index
        before sending -- applying the highest-index edits first avoids
        earlier edits invalidating the indices later edits were computed
        against. See `request_builder.py`'s module docstring for the full
        rationale.

        Args:
            document_id: ID of the document to update.
            requests: Docs API `Request` dicts (each shaped exactly like
                the real API, e.g. `{"insertText": {...}}`).

        Returns:
            IntegrationResult containing the `batchUpdate` response dict.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            if self.docs_service is None:
                return IntegrationResult.error_result(
                    "Google Docs service is not initialized"
                )

            ordered_requests = DocsRequestBuilder.from_requests(requests).build()
            body: dict[str, object] = {"requests": ordered_requests}

            try:
                response = (
                    self.docs_service.documents()
                    .batchUpdate(documentId=document_id, body=body)
                    .execute()
                )
            except Exception as api_error:
                self.logger.error(f"Failed to apply batch update: {api_error}")
                return IntegrationResult.error_result(
                    f"Failed to apply batch update in Google Docs: {api_error}"
                )

            return IntegrationResult.success_result(
                content=cast(dict[str, Any], response),
                message=f"Applied {len(ordered_requests)} update(s) to {document_id}",
            )
        except ZeoApiError as e:
            self.logger.error(f"API error during batch update: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except ZeoBaseAuthError as e:
            self.logger.error(f"Authentication error during batch update: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to apply batch update: {e}")
            return IntegrationResult.error_result(
                f"Failed to apply batch update in Google Docs: {e}"
            )

    def replace_text(
        self,
        document_id: str,
        find: str,
        replace: str,
        match_case: bool = False,
    ) -> IntegrationResult[dict[str, Any]]:
        """
        Replace all occurrences of `find` with `replace` in a document.

        Index-free by construction: `replaceAllText` matches by string, not
        offset, so the caller never computes or passes a text index.

        Args:
            document_id: ID of the document to update.
            find: Text to search for.
            replace: Text to replace matches with.
            match_case: Whether the search should be case-sensitive.

        Returns:
            IntegrationResult containing the `batchUpdate` response dict.
        """
        request: dict[str, Any] = {
            "replaceAllText": {
                "containsText": {"text": find, "matchCase": match_case},
                "replaceText": replace,
            }
        }
        return self.batch_update(document_id, [request])

    def append_text(
        self, document_id: str, text: str
    ) -> IntegrationResult[dict[str, Any]]:
        """
        Append `text` to the end of the document body.

        Index-free by construction: uses `endOfSegmentLocation` with no
        `segmentId` (meaning "end of the document body"), which the Docs
        API accepts on `insertText` as an alternative to an explicit
        `location.index` -- this keeps `append_text` a single API call with
        no prior `get` needed to compute an end index, and the caller never
        computes or passes an index either way.

        Args:
            document_id: ID of the document to update.
            text: Text to append.

        Returns:
            IntegrationResult containing the `batchUpdate` response dict.
        """
        request: dict[str, Any] = {
            "insertText": {
                "endOfSegmentLocation": {},
                "text": text,
            }
        }
        return self.batch_update(document_id, [request])

    def validate_config(self, config: dict[str, object]) -> tuple[bool, list[str]]:
        """
        Validate the service configuration.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            Tuple of (is_valid, list of error messages).
        """
        from zeo_core.integrations.google.config import GoogleDocsConfig

        errors: list[str] = []
        try:
            GoogleDocsConfig(**config)
            return True, []
        except Exception as e:
            errors.append(f"Configuration validation failed: {e}")
            return False, errors
