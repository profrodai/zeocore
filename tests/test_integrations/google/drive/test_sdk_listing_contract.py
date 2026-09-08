"""Exercise Google's actual discovery request validation without a live account."""

import json
from urllib.parse import parse_qs, urlsplit

import pytest
from googleapiclient.discovery import build
from googleapiclient.http import HttpMockSequence

from zeo_core.integrations.google.drive.operations.list_files import list_files
from zeo_core.integrations.google.drive.service import GoogleDriveService


@pytest.mark.parametrize("surface", ["service", "operation"])
@pytest.mark.parametrize("populated", [False, True])
def test_listing_uses_google_sdk_wire_parameters(surface: str, populated: bool) -> None:
    files = (
        [{"id": "test-file", "name": "probe.txt", "mimeType": "text/plain"}]
        if populated
        else []
    )
    http = HttpMockSequence([({"status": "200"}, json.dumps({"files": files}))])
    api = build("drive", "v3", http=http, static_discovery=True)
    if surface == "service":
        service = GoogleDriveService()
        service._initialized = True
        service.drive_service = api
        result = service.list_files(remote_path="test-folder")
    else:
        result = list_files(api, folder_id="test-folder")
    assert result.success, result.error
    assert result.content is not None and len(result.content) == len(files)
    if populated:
        assert result.content[0]["id"] == "test-file"
    assert len(http.request_sequence) == 1
    uri, method, body, _headers = http.request_sequence[0]
    query = parse_qs(urlsplit(uri).query)
    assert method == "GET" and body is None
    assert query["pageSize"] == ["100"]
    assert "test-folder" in query["q"][0]
    assert "page_size" not in query
