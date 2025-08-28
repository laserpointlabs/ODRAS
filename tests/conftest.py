import sys
from pathlib import Path

# Ensure project root is on sys.path for `import backend`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uuid
import types
import pytest


class InMemoryDB:
    def __init__(self):
        self.projects = {}  # project_id -> {project_id, name, is_active}
        self.members = {}   # project_id -> set(user_id)

    def _conn(self):
        return None

    def _return(self, _):
        return None

    # Users (not used here)
    def get_or_create_user(self, username: str, display_name=None, is_admin: bool = False):
        # Return a minimal dict compatible with main.login expectations
        return {"user_id": f"user-{username}", "username": username, "display_name": display_name or username, "is_admin": is_admin}

    # Projects
    def create_project(self, name: str, owner_user_id: str, description=None):
        pid = str(uuid.uuid4())
        proj = {
            "project_id": pid,
            "name": name,
            "description": description,
            "created_at": None,
            "updated_at": None,
            "created_by": owner_user_id,
            "is_active": True,
        }
        self.projects[pid] = proj
        self.members.setdefault(pid, set()).add(owner_user_id)
        return proj

    def list_projects_for_user(self, user_id: str, active=True):
        res = []
        for pid, proj in self.projects.items():
            if user_id in self.members.get(pid, set()):
                if active is None or proj["is_active"] == active:
                    res.append({**proj, "role": "owner"})
        return res

    def is_user_member(self, project_id: str, user_id: str) -> bool:
        return user_id in self.members.get(project_id, set())

    def archive_project(self, project_id: str) -> None:
        if project_id in self.projects:
            self.projects[project_id]["is_active"] = False

    def restore_project(self, project_id: str) -> None:
        if project_id in self.projects:
            self.projects[project_id]["is_active"] = True

    def rename_project(self, project_id: str, new_name: str):
        if project_id in self.projects:
            self.projects[project_id]["name"] = new_name
            return self.projects[project_id]
        raise ValueError("Project not found")


@pytest.fixture(autouse=True)
def monkeypatch_db(monkeypatch):
    # Patch backend.main.db with in-memory DB
    import backend.main as main
    main.db = InMemoryDB()
    # Patch files router DB dependency to avoid real Postgres membership checks
    from backend.api import files as files_api

    class _FilesDB:
        def is_user_member(self, project_id: str, user_id: str) -> bool:
            return True

    main.app.dependency_overrides[files_api.get_db_service] = lambda: _FilesDB()
    yield


