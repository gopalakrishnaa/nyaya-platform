"""Tests for the cases router (GET /v1/cases, GET /v1/cases/{id}, GET /health)."""
from __future__ import annotations

import uuid
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.database import get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_db() -> MagicMock:
    """A dummy AsyncSession that satisfies FastAPI's dependency injection."""
    return MagicMock()


@pytest_asyncio.fixture()
async def client(mock_db: MagicMock) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient wired to the FastAPI app with the DB dependency overridden."""

    async def _override_get_db() -> AsyncGenerator[Any, None]:
        yield mock_db

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_returns_ok_status(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        data = response.json()
        assert data.get("status") == "ok"


# ---------------------------------------------------------------------------
# GET /v1/cases — list
# ---------------------------------------------------------------------------

class TestListCases:
    @pytest.mark.asyncio
    async def test_list_cases_returns_200(self, client: AsyncClient) -> None:
        empty_page: dict[str, Any] = {"items": [], "total": 0, "page": 1, "page_size": 20}

        with patch("api.routers.cases.CaseService") as MockService:
            MockService.return_value.list_cases = AsyncMock(return_value=empty_page)
            response = await client.get("/v1/cases")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_cases_returns_expected_shape(self, client: AsyncClient) -> None:
        empty_page: dict[str, Any] = {"items": [], "total": 0, "page": 1, "page_size": 20}

        with patch("api.routers.cases.CaseService") as MockService:
            MockService.return_value.list_cases = AsyncMock(return_value=empty_page)
            response = await client.get("/v1/cases")

        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20

    @pytest.mark.asyncio
    async def test_list_cases_pocso_filter_forwarded_to_service(
        self, client: AsyncClient
    ) -> None:
        empty_page: dict[str, Any] = {"items": [], "total": 0, "page": 1, "page_size": 20}

        with patch("api.routers.cases.CaseService") as MockService:
            mock_list = AsyncMock(return_value=empty_page)
            MockService.return_value.list_cases = mock_list
            response = await client.get("/v1/cases?pocso=true")

        assert response.status_code == 200
        mock_list.assert_called_once()
        call_kwargs = mock_list.call_args.kwargs
        assert call_kwargs.get("pocso") is True, (
            f"Expected pocso=True forwarded to service, got: {call_kwargs}"
        )

    @pytest.mark.asyncio
    async def test_list_cases_default_pagination_params(self, client: AsyncClient) -> None:
        empty_page: dict[str, Any] = {"items": [], "total": 0, "page": 1, "page_size": 20}

        with patch("api.routers.cases.CaseService") as MockService:
            mock_list = AsyncMock(return_value=empty_page)
            MockService.return_value.list_cases = mock_list
            await client.get("/v1/cases")

        call_kwargs = mock_list.call_args.kwargs
        assert call_kwargs.get("page") == 1
        assert call_kwargs.get("page_size") == 20


# ---------------------------------------------------------------------------
# GET /v1/cases/{id} — single case
# ---------------------------------------------------------------------------

class TestGetCase:
    @pytest.mark.asyncio
    async def test_unknown_uuid_returns_404(self, client: AsyncClient) -> None:
        with patch("api.routers.cases.CaseService") as MockService:
            MockService.return_value.get_case_with_timeline = AsyncMock(return_value=None)
            response = await client.get(f"/v1/cases/{uuid.uuid4()}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_unknown_uuid_404_body(self, client: AsyncClient) -> None:
        with patch("api.routers.cases.CaseService") as MockService:
            MockService.return_value.get_case_with_timeline = AsyncMock(return_value=None)
            response = await client.get(f"/v1/cases/{uuid.uuid4()}")

        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_valid_case_returns_200(self, client: AsyncClient) -> None:
        case_id = str(uuid.uuid4())
        mock_case: dict[str, Any] = {
            "id": case_id,
            "case_ref": "MH/2024/001",
            "victim_pseudonym": "V-Alpha",
            "crime_category": "RAPE",
            "status": "TRIAL_ONGOING",
            "incident_date": "2024-01-15",
            "incident_date_approx": False,
            "state": "Maharashtra",
            "district": "Mumbai",
            "ipc_sections": [376],
            "pocso_applicable": False,
            "fast_track_court": True,
            "num_victims": 1,
            "num_accused": 1,
            "victim_age_group": "ADULT",
            "event_count": 3,
            "last_event_at": "2024-06-01",
            "overall_confidence": 0.92,
            "conviction_achieved": False,
            "conviction_date": None,
            "sentence_years": None,
            "compensation_inr": None,
            "created_at": "2024-01-20T00:00:00",
            "updated_at": "2024-06-01T00:00:00",
            "events": [],
        }

        with patch("api.routers.cases.CaseService") as MockService:
            MockService.return_value.get_case_with_timeline = AsyncMock(return_value=mock_case)
            response = await client.get(f"/v1/cases/{case_id}")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_valid_case_response_contains_case_ref(self, client: AsyncClient) -> None:
        case_id = str(uuid.uuid4())
        mock_case: dict[str, Any] = {
            "id": case_id,
            "case_ref": "KA/2024/042",
            "victim_pseudonym": "V-Beta",
            "crime_category": "SEXUAL_ASSAULT",
            "status": "INVESTIGATION",
            "incident_date": None,
            "incident_date_approx": True,
            "state": "Karnataka",
            "district": "Bengaluru",
            "ipc_sections": [354],
            "pocso_applicable": False,
            "fast_track_court": False,
            "num_victims": None,
            "num_accused": None,
            "victim_age_group": None,
            "event_count": 1,
            "last_event_at": None,
            "overall_confidence": None,
            "conviction_achieved": False,
            "conviction_date": None,
            "sentence_years": None,
            "compensation_inr": None,
            "created_at": "2024-03-01T00:00:00",
            "updated_at": "2024-03-01T00:00:00",
            "events": [],
        }

        with patch("api.routers.cases.CaseService") as MockService:
            MockService.return_value.get_case_with_timeline = AsyncMock(return_value=mock_case)
            response = await client.get(f"/v1/cases/{case_id}")

        data = response.json()
        assert "case_ref" in data, f"Response missing 'case_ref' field: {data.keys()}"
        assert data["case_ref"] == "KA/2024/042"
