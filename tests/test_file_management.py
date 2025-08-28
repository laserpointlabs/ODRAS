import os
import io
import asyncio
import json
import pytest

from httpx import AsyncClient, ASGITransport

from backend.main import app
@pytest.fixture(autouse=True)
def _set_env(tmp_path, monkeypatch):
    # Use local filesystem storage for tests
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    # Ensure allowed user for login
    monkeypatch.setenv("ALLOWED_USERS", "admin,tester,jdehart")
    # Point local storage to a temp directory to avoid polluting repo
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path / "files"))


async def _login(client: AsyncClient, username: str = "jdehart") -> str:
    r = await client.post("/api/auth/login", json={"username": username, "password": ""})
    assert r.status_code == 200, r.text
    data = r.json()
    token = data.get("token")
    assert token
    return token


async def _ensure_demo_project(client: AsyncClient, token: str, name: str = "Demo Project") -> str:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    # Create project
    r = await client.post("/api/projects", headers=headers, json={"name": name})
    assert r.status_code == 200, r.text
    pid = r.json()["project"]["project_id"]
    # Verify listing includes it
    r = await client.get("/api/projects", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert any(p["project_id"] == pid for p in r.json().get("projects", []))
    return pid


@pytest.mark.asyncio
async def test_upload_and_list_files():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as client:
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create demo project and upload files
        pid = await _ensure_demo_project(client, token)
        content = b"# Title\nSome text.\n"
        files = {"file": ("sample.md", io.BytesIO(content), "text/markdown")}
        data = {"project_id": pid, "tags": json.dumps({"docType": "knowledge", "status": "new"})}
        r = await client.post("/api/files/upload", files=files, data=data, headers=headers)
        assert r.status_code == 200, r.text
        up = r.json()
        assert up.get("success") is True
        assert up.get("file_id")

        # List files by project
        r = await client.get("/api/files", params={"project_id": pid})
        assert r.status_code == 200
        listing = r.json()
        assert listing.get("success") is True
        files_list = listing.get("files") or []
        assert any(f.get("filename") == "sample.md" for f in files_list)


@pytest.mark.asyncio
async def test_start_ingestion_workflow(monkeypatch):
    # Patch BPMN deployment to no-op
    async def _noop(*args, **kwargs):
        return None
    monkeypatch.setattr("backend.api.workflows._ensure_bpmn_deployed", _noop)

    # Patch httpx.AsyncClient inside workflows to avoid real Camunda calls
    class _FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"id": "proc_test_123"}

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return _FakeResp()

    monkeypatch.setattr("backend.api.workflows.httpx.AsyncClient", _FakeAsyncClient)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as client:
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        pid = await _ensure_demo_project(client, token)

        body = {
            "processKey": "ingestion_pipeline",
            "projectId": pid,
            "fileIds": ["file-1", "file-2"],
            "params": {"chunking": {"sizeTokens": 350, "overlapTokens": 50}, "embedding": {"modelId": "e5-large-v2"}},
        }
        r = await client.post("/api/workflows/start", content=json.dumps(body), headers=headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("success") is True
        assert data.get("runId") == "proc_test_123"
        assert data.get("processKey") == "ingestion_pipeline"


@pytest.mark.asyncio
async def test_full_file_manager_flow_jdehart(monkeypatch):
    # Stub Camunda client
    class _FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"id": "proc_full_456"}

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return _FakeResp()

    monkeypatch.setattr("backend.api.workflows.httpx.AsyncClient", _FakeAsyncClient)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as client:
        token = await _login(client, username="jdehart")
        headers = {"Authorization": f"Bearer {token}"}

        # Create project
        pid = await _ensure_demo_project(client, token, name="Demo Project FM")

        # Upload multiple file types
        def _upload(name: str, data: bytes, mime: str):
            return client.post(
                "/api/files/upload",
                headers=headers,
                files={"file": (name, io.BytesIO(data), mime)},
                data={"project_id": pid, "tags": json.dumps({"docType": "knowledge", "status": "new"})},
            )

        r1 = await _upload("sample.md", b"# H1\nHello\n", "text/markdown")
        r2 = await _upload("notes.txt", b"plain text\n", "text/plain")
        r3 = await _upload("table.csv", b"a,b\n1,2\n", "text/csv")
        assert r1.status_code == 200 and r2.status_code == 200 and r3.status_code == 200
        fids = [r1.json().get("file_id"), r2.json().get("file_id"), r3.json().get("file_id")]
        assert all(fids)

        # List and verify
        lr = await client.get("/api/files", params={"project_id": pid})
        assert lr.status_code == 200
        files_list = lr.json().get("files") or []
        names = {f.get("filename") for f in files_list}
        assert {"sample.md", "notes.txt", "table.csv"}.issubset(names)

        # Start ingestion for all
        body = {
            "processKey": "ingestion_pipeline",
            "projectId": pid,
            "fileIds": fids,
            "params": {"chunking": {"sizeTokens": 350, "overlapTokens": 50}, "embedding": {"modelId": "e5-large-v2"}},
        }
        wr = await client.post(
            "/api/workflows/start",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            content=json.dumps(body),
        )
        assert wr.status_code == 200
        data = wr.json()
        assert data.get("success") is True
        assert data.get("runId") == "proc_full_456"


