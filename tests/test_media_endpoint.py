from unittest.mock import patch, AsyncMock
import pytest
from fastapi.testclient import TestClient

import src.app  # noqa: F401
from src.app import app
from src.modules.auth.dependencies import get_current_user
from src.modules.users.models import User

client = TestClient(app)


def test_delete_media_requires_auth():
    app.dependency_overrides.clear()
    response = client.request("DELETE", "/api/media", json={"publicId": "test_public_id", "resourceType": "image"})
    assert response.status_code == 401


@patch("src.modules.media.router.delete_media", new_callable=AsyncMock)
def test_delete_media_authenticated_success(mock_delete_media):
    mock_delete_media.return_value = {"result": "ok"}
    mock_user = User(id=1, email="user@example.com", role="student", status="active")

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = client.request(
            "DELETE",
            "/api/media",
            json={"publicId": "branches/photo_123", "resourceType": "image"},
            headers={"Authorization": "Bearer mock_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["deleted"] is True
        assert data["data"]["publicId"] == "branches/photo_123"
        assert data["data"]["result"] == "ok"
        mock_delete_media.assert_called_once_with(public_id="branches/photo_123", resource_type="image")
    finally:
        app.dependency_overrides.clear()


@patch("src.modules.media.router.delete_media", new_callable=AsyncMock)
def test_delete_media_already_deleted_idempotent(mock_delete_media):
    mock_delete_media.return_value = {"result": "not_found"}
    mock_user = User(id=2, email="admin@example.com", role="admin", status="active")

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = client.request(
            "DELETE",
            "/api/media",
            json={"publicId": "non_existent_asset", "resourceType": "video"},
            headers={"Authorization": "Bearer mock_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["deleted"] is True
        assert data["data"]["result"] == "not_found"
        mock_delete_media.assert_called_once_with(public_id="non_existent_asset", resource_type="video")
    finally:
        app.dependency_overrides.clear()


def test_delete_media_invalid_resource_type():
    mock_user = User(id=1, email="user@example.com", role="student", status="active")

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = client.request(
            "DELETE",
            "/api/media",
            json={"publicId": "some_id", "resourceType": "invalid_type"},
            headers={"Authorization": "Bearer mock_token"},
        )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()

