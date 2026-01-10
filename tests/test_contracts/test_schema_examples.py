# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_contracts/test_schema_examples.py
# role: tests
# neighbors: __init__.py, test_artifacts.py, test_capabilities.py, test_dependency_boundaries.py, test_envelopes.py
# exports: TestSchemaExamples
# git_branch: feat/9-make-setup-work
# git_commit: 3a380e47
# === QV-LLM:END ===

"""
Tests that validate all json_schema_extra examples are valid.

This ensures documentation examples remain correct as schemas evolve.
Uses model_json_schema() rather than accessing model_config directly
for forward compatibility across Pydantic versions.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError
from quack_core.contracts import (
    ArtifactRef,
    RunManifest,
    StorageRef,
)
from quack_core.contracts.common.ids import is_valid_uuid


def _get_schema_examples(model):
    """
    Extract examples from a Pydantic model's JSON schema.

    Uses model_json_schema() for forward compatibility rather than
    accessing model_config directly.
    """
    schema = model.model_json_schema()
    return schema.get("examples", [])


def _assert_examples_validate(model):
    """
    Assert that all examples in a model's schema validate successfully.

    Args:
        model: Pydantic model class to test

    Raises:
        AssertionError: If no examples exist or validation fails
    """
    examples = _get_schema_examples(model)
    assert examples, f"{model.__name__} should have examples in schema"

    for i, example in enumerate(examples):
        try:
            instance = model.model_validate(example)
            assert instance is not None
        except ValidationError as e:
            pytest.fail(f"{model.__name__} example {i} failed validation:\n{e}")


class TestSchemaExamples:
    """Test that all schema examples can be validated successfully."""

    def test_storage_ref_examples_validate(self):
        """Test that StorageRef examples are valid."""
        _assert_examples_validate(StorageRef)

    def test_artifact_ref_examples_validate(self):
        """Test that ArtifactRef examples are valid."""
        _assert_examples_validate(ArtifactRef)

    def test_run_manifest_examples_validate(self):
        """Test that RunManifest examples are valid."""
        examples = _get_schema_examples(RunManifest)
        assert len(examples) >= 3, \
            "RunManifest should have multiple domain examples (media, text, crm, etc.)"
        _assert_examples_validate(RunManifest)

    def test_run_manifest_examples_represent_diverse_domains(self):
        """Test that RunManifest examples demonstrate different capability domains."""
        examples = _get_schema_examples(RunManifest)

        tool_names = set()
        for i, example in enumerate(examples):
            manifest = RunManifest.model_validate(example)
            tool_names.add(manifest.tool.name)

        assert len(tool_names) >= 3, \
            f"RunManifest examples should represent diverse domains, got: {tool_names}"

    def test_run_manifest_examples_use_namespaced_naming(self):
        """
        Test that manifest examples use namespaced tool names and artifact roles.

        Convention: tool.name and artifact.role should use domain.identifier format
        (e.g., 'media.slice_video', 'text.summary_md').
        """
        for i, example in enumerate(_get_schema_examples(RunManifest)):
            manifest = RunManifest.model_validate(example)

            # Tool name should be namespaced (contain a dot)
            assert "." in manifest.tool.name, \
                f"Example {i}: tool name '{manifest.tool.name}' must be namespaced (e.g., 'domain.tool')"

            # Input artifact roles should be namespaced
            for input_idx, manifest_input in enumerate(manifest.inputs):
                role = manifest_input.artifact.role
                assert "." in role, \
                    f"Example {i}, input {input_idx}: role '{role}' must be namespaced (e.g., 'domain.role')"

            # Output artifact roles should be namespaced
            for output_idx, output in enumerate(manifest.outputs):
                role = output.role
                assert "." in role, \
                    f"Example {i}, output {output_idx}: role '{role}' must be namespaced (e.g., 'domain.role')"

    def test_run_manifest_examples_have_valid_uuids(self):
        """
        Test that all UUIDs in manifest examples are valid format.

        Uses is_valid_uuid() rather than string length checks to ensure
        actual UUID validity.
        """
        for i, example in enumerate(_get_schema_examples(RunManifest)):
            manifest = RunManifest.model_validate(example)

            # Check run_id
            assert is_valid_uuid(manifest.run_id), \
                f"Example {i}: run_id '{manifest.run_id}' is not a valid UUID"

            # Check artifact_ids in inputs
            for input_idx, manifest_input in enumerate(manifest.inputs):
                artifact_id = manifest_input.artifact.artifact_id
                assert is_valid_uuid(artifact_id), \
                    f"Example {i}, input {input_idx}: artifact_id '{artifact_id}' is not a valid UUID"

            # Check artifact_ids in outputs
            for output_idx, output in enumerate(manifest.outputs):
                artifact_id = output.artifact_id
                assert is_valid_uuid(artifact_id), \
                    f"Example {i}, output {output_idx}: artifact_id '{artifact_id}' is not a valid UUID"

    def test_run_manifest_examples_have_valid_timestamps(self):
        """
        Test that timestamps in examples are ISO format with Z suffix and parseable.

        Validates both format (Z suffix) and parseability to catch subtle issues
        like missing 'T' separator.
        """
        for i, example in enumerate(_get_schema_examples(RunManifest)):
            # Check raw example data for timestamp format
            started_at = example.get("started_at", "")
            assert started_at.endswith("Z"), \
                f"Example {i}: started_at should use Z format (got: {started_at})"

            # Verify it's actually parseable as ISO 8601
            try:
                datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            except ValueError as e:
                pytest.fail(
                    f"Example {i}: started_at '{started_at}' is not valid ISO 8601: {e}")

            # Check finished_at if present
            if "finished_at" in example:
                finished_at = example["finished_at"]
                assert finished_at.endswith("Z"), \
                    f"Example {i}: finished_at should use Z format (got: {finished_at})"

                try:
                    datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
                except ValueError as e:
                    pytest.fail(
                        f"Example {i}: finished_at '{finished_at}' is not valid ISO 8601: {e}")

    def test_run_manifest_examples_enforce_status_invariants(self):
        """
        Test that manifest examples demonstrate proper status invariants.

        Validates the contracts enforced by model validators:
        - success: error must be None
        - error: outputs and intermediates must be empty, error must be present
        - skipped: outputs and intermediates must be empty
        """
        for i, example in enumerate(_get_schema_examples(RunManifest)):
            manifest = RunManifest.model_validate(example)

            if manifest.status.value == "success":
                # Success cannot have error field
                assert manifest.error is None, \
                    f"Example {i}: success status cannot have error field"

            elif manifest.status.value == "error":
                # Error must have error field
                assert manifest.error is not None, \
                    f"Example {i}: error status must have error field"
                # Error cannot have outputs or intermediates
                assert manifest.outputs == [], \
                    f"Example {i}: error status must have empty outputs"
                assert manifest.intermediates == [], \
                    f"Example {i}: error status must have empty intermediates"

            elif manifest.status.value == "skipped":
                # Skipped cannot have outputs or intermediates
                assert manifest.outputs == [], \
                    f"Example {i}: skipped status must have empty outputs"
                assert manifest.intermediates == [], \
                    f"Example {i}: skipped status must have empty intermediates"

    def test_run_manifest_examples_keep_intermediates_empty(self):
        """
        Test that examples use empty intermediates for clarity.

        While intermediates are allowed for success status, examples should
        keep them empty to demonstrate the clean/common case. This is a
        documentation quality check, not a schema requirement.
        """
        for i, example in enumerate(_get_schema_examples(RunManifest)):
            manifest = RunManifest.model_validate(example)

            # For documentation clarity, examples should show the clean case
            assert manifest.intermediates == [], \
                f"Example {i}: examples should use empty intermediates for clarity " \
                f"(intermediates are allowed but make examples more complex)"
