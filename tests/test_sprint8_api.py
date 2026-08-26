import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.app import app
from src.modules.assignments.models import Assignment, AssignmentSubmission
from src.modules.users.models import User

# This is a scaffold for sprint 8 API tests.
# These require the database and test fixtures to run.
# They verify that the assignment endpoints work according to the sprint spec.

@pytest.mark.asyncio
async def test_get_assignments_unauthorized(ac: AsyncClient):
    """Test that unauthorized users cannot list assignments"""
    response = await ac.get("/api/assignments")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_my_classes_unauthorized(ac: AsyncClient):
    """Test that unauthorized users cannot list their classes"""
    response = await ac.get("/api/classes/my")
    assert response.status_code == 401

# Real integration tests with DB fixtures would go here...
# Testing creation, updating, batch delete, etc.
