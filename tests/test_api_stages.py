"""Tests for stages API endpoints."""

from typing import Any

import mongomock
import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from uptimer.settings import clear_settings_cache
from uptimer.storage import Storage
from uptimer.web.api.deps import clear_storage_cache, get_storage
from uptimer.web.app import create_app


@pytest.fixture(autouse=True)
def clear_caches() -> None:
    """Clear caches before each test."""
    clear_settings_cache()
    clear_storage_cache()


@pytest.fixture
def storage() -> Storage:
    """Create a storage instance with mongomock."""
    client: MongoClient[dict[str, Any]] = mongomock.MongoClient()
    return Storage(
        mongodb_uri="mongodb://localhost:27017",
        mongodb_db="test_uptimer",
        results_retention=100,
        client=client,
    )


@pytest.fixture
def client(storage: Storage) -> TestClient:
    """Create test client with storage override."""
    app = create_app()

    def override_storage() -> Storage:
        return storage

    app.dependency_overrides[get_storage] = override_storage

    return TestClient(app)


@pytest.fixture
def auth_client(client: TestClient) -> TestClient:
    """Create authenticated test client."""
    client.post("/login", data={"username": "admin", "password": "admin"})
    return client


class TestListStages:
    """Tests for GET /api/stages."""

    def test_list_stages_unauthorized(self, client: TestClient) -> None:
        """Test listing stages without auth."""
        response = client.get("/api/stages")
        assert response.status_code == 401
        assert response.json()["detail"] == "Authentication required"

    def test_list_stages(self, auth_client: TestClient) -> None:
        """Test listing all available stages."""
        response = auth_client.get("/api/stages")
        assert response.status_code == 200
        data: list[dict[str, Any]] = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

        # Check that required stages exist
        stage_types: list[str] = [s["type"] for s in data]
        assert "http" in stage_types
        assert "dhis2" in stage_types
        assert "ssl" in stage_types
        assert "dns" in stage_types
        assert "tcp" in stage_types
        assert "contains" in stage_types
        assert "jsonpath" in stage_types
        assert "threshold" in stage_types

    def test_list_stages_structure(self, auth_client: TestClient) -> None:
        """Test that each stage has the correct structure."""
        response = auth_client.get("/api/stages")
        assert response.status_code == 200
        data = response.json()

        for stage in data:
            assert "type" in stage
            assert "name" in stage
            assert "description" in stage
            assert "is_network_stage" in stage
            assert "options" in stage
            assert isinstance(stage["options"], list)

    def test_http_stage_info(self, auth_client: TestClient) -> None:
        """Test HTTP stage has correct info."""
        response = auth_client.get("/api/stages")
        data = response.json()

        http_stage = next(s for s in data if s["type"] == "http")
        assert http_stage["name"] == "HTTP"
        assert http_stage["is_network_stage"] is True
        assert isinstance(http_stage["options"], list)

    def test_jsonpath_stage_info(self, auth_client: TestClient) -> None:
        """Test JSONPath stage has correct info and options."""
        response = auth_client.get("/api/stages")
        data = response.json()

        jsonpath_stage = next(s for s in data if s["type"] == "jsonpath")
        assert jsonpath_stage["name"] == "JSONPath"
        assert jsonpath_stage["is_network_stage"] is False

        option_names = [o["name"] for o in jsonpath_stage["options"]]
        assert "expr" in option_names
        assert "store_as" in option_names

        expr_option = next(o for o in jsonpath_stage["options"] if o["name"] == "expr")
        assert expr_option["required"] is True
        assert expr_option["type"] == "string"

    def test_threshold_stage_info(self, auth_client: TestClient) -> None:
        """Test Threshold stage has correct info and options."""
        response = auth_client.get("/api/stages")
        data = response.json()

        threshold_stage = next(s for s in data if s["type"] == "threshold")
        assert threshold_stage["name"] == "Threshold"
        assert threshold_stage["is_network_stage"] is False

        option_names = [o["name"] for o in threshold_stage["options"]]
        assert "value" in option_names
        assert "min" in option_names
        assert "max" in option_names

        min_option = next(o for o in threshold_stage["options"] if o["name"] == "min")
        assert min_option["type"] == "number"

    def test_ssl_stage_info(self, auth_client: TestClient) -> None:
        """Test SSL stage has correct info and options."""
        response = auth_client.get("/api/stages")
        data = response.json()

        ssl_stage = next(s for s in data if s["type"] == "ssl")
        assert ssl_stage["name"] == "SSL Certificate"
        assert ssl_stage["is_network_stage"] is True

        option_names = [o["name"] for o in ssl_stage["options"]]
        assert "warn_days" in option_names

        warn_days = next(o for o in ssl_stage["options"] if o["name"] == "warn_days")
        assert warn_days["type"] == "number"
        assert warn_days["default"] == 30

    def test_contains_stage_info(self, auth_client: TestClient) -> None:
        """Test Contains stage has correct info and options."""
        response = auth_client.get("/api/stages")
        data = response.json()

        contains_stage = next(s for s in data if s["type"] == "contains")
        assert contains_stage["name"] == "Contains"
        assert contains_stage["is_network_stage"] is False

        option_names = [o["name"] for o in contains_stage["options"]]
        assert "pattern" in option_names
        assert "negate" in option_names

        pattern_option = next(o for o in contains_stage["options"] if o["name"] == "pattern")
        assert pattern_option["required"] is True

        negate_option = next(o for o in contains_stage["options"] if o["name"] == "negate")
        assert negate_option["type"] == "boolean"
        assert negate_option["default"] is False
