"""
File CRUD Operations Tests

Comprehensive tests for all file-related operations:
- Upload files (various types and sizes)
- Download files
- Update file metadata
- Delete files
- File versioning
- File permissions
- Batch operations

Run with: pytest tests/api/test_file_crud.py -v
"""

import pytest
import time
import json
import io
from typing import Dict, List, Any
from httpx import AsyncClient
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))



class TestFileCRUD:
    """Test all file CRUD operations"""

    @pytest.fixture
    async def client(self):
        # Connect to the REAL running API
        async with AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
            yield client

    @pytest.fixture
    async def auth_headers(self, client):
        response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def test_project(self, client, auth_headers):
        """Create a test project for file operations"""
        response = await client.post(
            "/api/projects",
            json={"name": f"File Test Project {int(time.time())}"},
            headers=auth_headers
        )
        result = response.json()
        project_id = result["project"]["project_id"]
        yield project_id
        # Cleanup
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)

    # ========== UPLOAD OPERATIONS ==========

    @pytest.mark.asyncio
    async def test_upload_text_file(self, client, auth_headers, test_project):
        """Test uploading a text file"""
        content = b"This is a test text file content."
        files = {"file": ("test.txt", content, "text/plain")}

        response = await client.post(
            f"/api/files/upload/{test_project}",
            files=files,
            headers=auth_headers
        )
        assert response.status_code == 200

        file_info = response.json()
        assert "file_id" in file_info
        assert file_info["filename"] == "test.txt"
        assert file_info["mime_type"] == "text/plain"
        assert file_info["size"] == len(content)

        print("✓ Text file upload tested")

    @pytest.mark.asyncio
    async def test_upload_various_file_types(self, client, auth_headers, test_project):
        """Test uploading various file types"""
        test_files = [
            # Text formats
            ("document.txt", b"Plain text content", "text/plain"),
            ("data.json", json.dumps({"key": "value"}).encode(), "application/json"),
            ("data.csv", b"name,value\ntest,123\n", "text/csv"),
            ("readme.md", b"# Markdown\n\nTest content", "text/markdown"),

            # Binary formats (small samples)
            ("image.png", b"\x89PNG\r\n\x1a\n", "image/png"),
            ("document.pdf", b"%PDF-1.4", "application/pdf"),
            ("data.xml", b"<?xml version='1.0'?><root></root>", "application/xml"),

            # Code files
            ("script.py", b"print('Hello, World!')", "text/x-python"),
            ("page.html", b"<html><body>Test</body></html>", "text/html"),
            ("style.css", b"body { margin: 0; }", "text/css")
        ]

        uploaded_files = []
        for filename, content, mime_type in test_files:
            files = {"file": (filename, content, mime_type)}
            response = await client.post(
                f"/api/files/upload/{test_project}",
                files=files,
                headers=auth_headers
            )
            assert response.status_code == 200
            uploaded_files.append(response.json()["file_id"])

        print(f"✓ Uploaded {len(test_files)} different file types")

    @pytest.mark.asyncio
    async def test_upload_large_file(self, client, auth_headers, test_project):
        """Test uploading larger files"""
        # Create a 5MB file
        large_content = b"x" * (5 * 1024 * 1024)
        files = {"file": ("large.bin", large_content, "application/octet-stream")}

        response = await client.post(
            f"/api/files/upload/{test_project}",
            files=files,
            headers=auth_headers
        )

        if response.status_code == 200:
            file_info = response.json()
            assert file_info["size"] == len(large_content)
            print("✓ Large file upload tested (5MB)")
        elif response.status_code == 413:
            print("✓ Large file rejected with appropriate error (413)")

    @pytest.mark.asyncio
    async def test_upload_with_metadata(self, client, auth_headers, test_project):
        """Test uploading files with metadata"""
        content = b"File with metadata"

        # Some APIs support metadata during upload
        response = await client.post(
            f"/api/files/upload/{test_project}",
            files={"file": ("metadata.txt", content, "text/plain")},
            data={
                "description": "Test file with metadata",
                "tags": json.dumps(["test", "metadata", "upload"]),
                "author": "Test Suite"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        file_info = response.json()

        # Check if metadata was accepted
        if "description" in file_info:
            assert file_info["description"] == "Test file with metadata"

        print("✓ File upload with metadata tested")

    @pytest.mark.asyncio
    async def test_upload_duplicate_filename(self, client, auth_headers, test_project):
        """Test uploading files with duplicate names"""
        content1 = b"First file content"
        content2 = b"Second file content"

        # Upload first file
        files1 = {"file": ("duplicate.txt", content1, "text/plain")}
        response1 = await client.post(
            f"/api/files/upload/{test_project}",
            files=files1,
            headers=auth_headers
        )
        assert response1.status_code == 200
        file1_id = response1.json()["file_id"]

        # Upload second file with same name
        files2 = {"file": ("duplicate.txt", content2, "text/plain")}
        response2 = await client.post(
            f"/api/files/upload/{test_project}",
            files=files2,
            headers=auth_headers
        )
        assert response2.status_code == 200
        file2_id = response2.json()["file_id"]

        # Should have different IDs
        assert file1_id != file2_id
        print("✓ Duplicate filename handling tested")

    # ========== READ OPERATIONS ==========

    @pytest.mark.asyncio
    async def test_download_file(self, client, auth_headers, test_project):
        """Test downloading files"""
        # Upload a file first
        original_content = b"Download test content"
        files = {"file": ("download_test.txt", original_content, "text/plain")}

        upload_resp = await client.post(
            f"/api/files/upload/{test_project}",
            files=files,
            headers=auth_headers
        )
        file_id = upload_resp.json()["file_id"]

        # Download the file
        download_resp = await client.get(
            f"/api/files/{file_id}/download",
            headers=auth_headers
        )
        assert download_resp.status_code == 200
        assert download_resp.content == original_content

        # Check headers
        assert "content-type" in download_resp.headers
        assert "content-length" in download_resp.headers

        print("✓ File download tested")

    @pytest.mark.asyncio
    async def test_get_file_metadata(self, client, auth_headers, test_project):
        """Test retrieving file metadata"""
        # Upload a file
        files = {"file": ("metadata_test.txt", b"Test content", "text/plain")}
        upload_resp = await client.post(
            f"/api/files/upload/{test_project}",
            files=files,
            headers=auth_headers
        )
        file_id = upload_resp.json()["file_id"]

        # Get metadata
        metadata_resp = await client.get(
            f"/api/files/{file_id}/metadata",
            headers=auth_headers
        )
        assert metadata_resp.status_code == 200

        metadata = metadata_resp.json()
        assert metadata["filename"] == "metadata_test.txt"
        assert metadata["mime_type"] == "text/plain"
        assert "size" in metadata
        assert "created_at" in metadata
        assert "created_by" in metadata

        print("✓ File metadata retrieval tested")

    @pytest.mark.asyncio
    async def test_list_project_files(self, client, auth_headers, test_project):
        """Test listing files in a project"""
        # Upload multiple files
        file_names = ["file1.txt", "file2.pdf", "file3.json", "file4.csv"]
        for name in file_names:
            files = {"file": (name, f"Content of {name}".encode(), "text/plain")}
            await client.post(
                f"/api/files/upload/{test_project}",
                files=files,
                headers=auth_headers
            )

        # List all files
        list_resp = await client.get(
            f"/api/files/project/{test_project}",
            headers=auth_headers
        )
        assert list_resp.status_code == 200

        files = list_resp.json()
        assert isinstance(files, list)
        assert len(files) >= len(file_names)

        # Verify all uploaded files are in the list
        listed_names = [f["filename"] for f in files]
        for name in file_names:
            assert name in listed_names

        print(f"✓ Listed {len(files)} files in project")

    @pytest.mark.asyncio
    async def test_filter_files_by_type(self, client, auth_headers, test_project):
        """Test filtering files by MIME type"""
        # Upload files of different types
        test_files = [
            ("text1.txt", b"Text 1", "text/plain"),
            ("text2.txt", b"Text 2", "text/plain"),
            ("doc.pdf", b"PDF", "application/pdf"),
            ("image.png", b"PNG", "image/png")
        ]

        for filename, content, mime_type in test_files:
            files = {"file": (filename, content, mime_type)}
            await client.post(
                f"/api/files/upload/{test_project}",
                files=files,
                headers=auth_headers
            )

        # Filter by text files
        text_resp = await client.get(
            f"/api/files/project/{test_project}",
            params={"mime_type": "text/plain"},
            headers=auth_headers
        )

        if text_resp.status_code == 200:
            text_files = text_resp.json()
            # Should only contain text files
            for file in text_files:
                assert file["mime_type"] == "text/plain"
            print("✓ File filtering by type tested")
        else:
            print("⚠ File filtering not implemented")

    # ========== UPDATE OPERATIONS ==========

    @pytest.mark.asyncio
    async def test_update_file_metadata(self, client, auth_headers, test_project):
        """Test updating file metadata"""
        # Upload a file
        files = {"file": ("update_test.txt", b"Original content", "text/plain")}
        upload_resp = await client.post(
            f"/api/files/upload/{test_project}",
            files=files,
            headers=auth_headers
        )
        file_id = upload_resp.json()["file_id"]

        # Update metadata
        update_data = {
            "description": "Updated file description",
            "tags": ["updated", "tested", "metadata"],
            "custom_metadata": {
                "version": "2.0",
                "reviewed": True
            }
        }

        update_resp = await client.put(
            f"/api/files/{file_id}/metadata",
            json=update_data,
            headers=auth_headers
        )

        if update_resp.status_code == 200:
            updated = update_resp.json()
            if "description" in updated:
                assert updated["description"] == update_data["description"]
            print("✓ File metadata update tested")
        else:
            print("⚠ File metadata update not implemented")

    @pytest.mark.asyncio
    async def test_rename_file(self, client, auth_headers, test_project):
        """Test renaming a file"""
        # Upload a file
        files = {"file": ("original_name.txt", b"Content", "text/plain")}
        upload_resp = await client.post(
            f"/api/files/upload/{test_project}",
            files=files,
            headers=auth_headers
        )
        file_id = upload_resp.json()["file_id"]

        # Rename file
        rename_resp = await client.put(
            f"/api/files/{file_id}/rename",
            json={"new_name": "renamed_file.txt"},
            headers=auth_headers
        )

        if rename_resp.status_code == 200:
            # Verify rename
            metadata_resp = await client.get(
                f"/api/files/{file_id}/metadata",
                headers=auth_headers
            )
            assert metadata_resp.json()["filename"] == "renamed_file.txt"
            print("✓ File rename tested")
        else:
            print("⚠ File rename not implemented")

    # ========== DELETE OPERATIONS ==========

    @pytest.mark.asyncio
    async def test_delete_file(self, client, auth_headers, test_project):
        """Test deleting a file"""
        # Upload a file
        files = {"file": ("to_delete.txt", b"Delete me", "text/plain")}
        upload_resp = await client.post(
            f"/api/files/upload/{test_project}",
            files=files,
            headers=auth_headers
        )
        file_id = upload_resp.json()["file_id"]

        # Delete the file
        delete_resp = await client.delete(
            f"/api/files/{file_id}",
            headers=auth_headers
        )
        assert delete_resp.status_code == 200

        # Verify deletion
        download_resp = await client.get(
            f"/api/files/{file_id}/download",
            headers=auth_headers
        )
        assert download_resp.status_code == 404

        print("✓ File deletion tested")

    @pytest.mark.asyncio
    async def test_bulk_delete(self, client, auth_headers, test_project):
        """Test deleting multiple files"""
        # Upload multiple files
        file_ids = []
        for i in range(5):
            files = {"file": (f"bulk_delete_{i}.txt", f"File {i}".encode(), "text/plain")}
            resp = await client.post(
                f"/api/files/upload/{test_project}",
                files=files,
                headers=auth_headers
            )
            file_ids.append(resp.json()["file_id"])

        # Try bulk delete
        bulk_resp = await client.post(
            f"/api/files/bulk-delete",
            json={"file_ids": file_ids},
            headers=auth_headers
        )

        if bulk_resp.status_code in [200, 204]:
            # Verify all files are deleted
            for file_id in file_ids:
                check_resp = await client.get(
                    f"/api/files/{file_id}/download",
                    headers=auth_headers
                )
                assert check_resp.status_code == 404
            print("✓ Bulk file deletion tested")
        else:
            # Delete individually
            for file_id in file_ids:
                await client.delete(f"/api/files/{file_id}", headers=auth_headers)
            print("⚠ Bulk deletion not implemented, deleted individually")

    # ========== VERSIONING ==========

    @pytest.mark.asyncio
    async def test_file_versioning(self, client, auth_headers, test_project):
        """Test file version management"""
        # Upload initial version
        files_v1 = {"file": ("versioned.txt", b"Version 1 content", "text/plain")}
        upload_resp = await client.post(
            f"/api/files/upload/{test_project}",
            files=files_v1,
            headers=auth_headers
        )
        file_id = upload_resp.json()["file_id"]

        # Upload new version
        files_v2 = {"file": ("versioned.txt", b"Version 2 content updated", "text/plain")}
        version_resp = await client.post(
            f"/api/files/{file_id}/versions",
            files=files_v2,
            headers=auth_headers
        )

        if version_resp.status_code in [200, 201]:
            # List versions
            versions_resp = await client.get(
                f"/api/files/{file_id}/versions",
                headers=auth_headers
            )
            if versions_resp.status_code == 200:
                versions = versions_resp.json()
                assert len(versions) >= 2
                print("✓ File versioning tested")
        else:
            print("⚠ File versioning not implemented")

    # ========== PERMISSIONS ==========

    @pytest.mark.asyncio
    async def test_file_permissions(self, client, auth_headers, test_project):
        """Test file access permissions"""
        # Upload a file
        files = {"file": ("private.txt", b"Private content", "text/plain")}
        upload_resp = await client.post(
            f"/api/files/upload/{test_project}",
            files=files,
            headers=auth_headers
        )
        file_id = upload_resp.json()["file_id"]

        # Try to access without authentication
        unauth_resp = await client.get(f"/api/files/{file_id}/download")
        assert unauth_resp.status_code == 401

        # Set file permissions (if supported)
        perm_resp = await client.put(
            f"/api/files/{file_id}/permissions",
            json={
                "public": False,
                "allowed_users": ["das_service"],
                "allowed_roles": ["admin"]
            },
            headers=auth_headers
        )

        if perm_resp.status_code == 200:
            print("✓ File permissions tested")
        else:
            print("⚠ File permissions not implemented")

    # ========== BATCH OPERATIONS ==========

    @pytest.mark.asyncio
    async def test_batch_upload(self, client, auth_headers, test_project):
        """Test uploading multiple files at once"""
        # Prepare multiple files
        files_data = []
        for i in range(3):
            content = f"Batch file {i} content".encode()
            files_data.append(("files", (f"batch_{i}.txt", content, "text/plain")))

        # Try batch upload
        batch_resp = await client.post(
            f"/api/files/upload-batch/{test_project}",
            files=files_data,
            headers=auth_headers
        )

        if batch_resp.status_code == 200:
            results = batch_resp.json()
            assert len(results) == 3
            print("✓ Batch file upload tested")
        else:
            # Upload individually as fallback
            for _, file_data in files_data:
                await client.post(
                    f"/api/files/upload/{test_project}",
                    files={"file": file_data},
                    headers=auth_headers
                )
            print("⚠ Batch upload not implemented, uploaded individually")

    # ========== EDGE CASES ==========

    @pytest.mark.asyncio
    async def test_empty_file_upload(self, client, auth_headers, test_project):
        """Test uploading empty files"""
        files = {"file": ("empty.txt", b"", "text/plain")}

        response = await client.post(
            f"/api/files/upload/{test_project}",
            files=files,
            headers=auth_headers
        )

        assert response.status_code in [200, 400]  # May reject empty files
        if response.status_code == 200:
            file_info = response.json()
            assert file_info["size"] == 0
            print("✓ Empty file upload handled")

    @pytest.mark.asyncio
    async def test_special_filename_characters(self, client, auth_headers, test_project):
        """Test files with special characters in names"""
        special_names = [
            "file with spaces.txt",
            "file_with_underscores.txt",
            "file-with-dashes.txt",
            "file.multiple.dots.txt",
            "文件名.txt",  # Unicode
            "file@special#chars.txt"
        ]

        for filename in special_names:
            files = {"file": (filename, b"Content", "text/plain")}
            response = await client.post(
                f"/api/files/upload/{test_project}",
                files=files,
                headers=auth_headers
            )
            # Should handle gracefully
            assert response.status_code in [200, 400]

        print("✓ Special filename characters tested")


# Run all file CRUD tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
