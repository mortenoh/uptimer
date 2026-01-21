"""Tests for pipeline execution utilities."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from uptimer.pipeline import instantiate_stage, run_pipeline
from uptimer.schemas import Stage
from uptimer.stages.base import CheckContext, CheckResult, Status


class TestInstantiateStage:
    """Tests for instantiate_stage function."""

    def test_instantiate_http_stage(self) -> None:
        """Test instantiating a basic HTTP stage."""
        stage = Stage(type="http")
        instance = instantiate_stage(stage)
        assert instance is not None
        assert hasattr(instance, "check")

    def test_instantiate_with_options(self) -> None:
        """Test instantiating stage with options."""
        stage = Stage(type="threshold", min=0, max=1000, value="$elapsed_ms")
        instance = instantiate_stage(stage)
        assert instance is not None
        assert instance.min_value == 0
        assert instance.max_value == 1000

    def test_instantiate_with_invalid_options_falls_back(self) -> None:
        """Test that invalid options fall back to defaults."""
        stage = Stage(type="http")
        # HTTP stage doesn't take min/max, but we pass them anyway
        stage.min = 100  # This option doesn't apply to HTTP
        instance = instantiate_stage(stage)
        assert instance is not None


class TestRunPipeline:
    """Tests for run_pipeline function."""

    def test_single_stage_pipeline(self) -> None:
        """Test pipeline with a single stage."""
        mock_result = CheckResult(
            status=Status.UP,
            url="https://example.com",
            message="200 OK",
            elapsed_ms=100.0,
            details={"status_code": 200},
        )
        mock_stage = MagicMock()
        mock_stage.check.return_value = mock_result

        with patch("uptimer.pipeline.instantiate_stage", return_value=mock_stage):
            pipeline = [Stage(type="http")]
            status, message, elapsed, details = run_pipeline("https://example.com", pipeline)

        assert status == "up"
        assert "200 OK" in message
        assert elapsed == 100.0
        assert "http" in details

    def test_multi_stage_pipeline(self) -> None:
        """Test pipeline with multiple stages."""
        http_result = CheckResult(
            status=Status.UP,
            url="https://example.com",
            message="200 OK",
            elapsed_ms=100.0,
            details={"status_code": 200},
        )
        threshold_result = CheckResult(
            status=Status.UP,
            url="https://example.com",
            message="100ms < 1000ms",
            elapsed_ms=0.1,
            details={"value": 100, "threshold": 1000},
        )

        mock_http = MagicMock()
        mock_http.check.return_value = http_result
        mock_threshold = MagicMock()
        mock_threshold.check.return_value = threshold_result

        stages_map = {"http": mock_http, "threshold": mock_threshold}

        def mock_instantiate(stage: Stage) -> MagicMock:
            return stages_map[stage.type]

        with patch("uptimer.pipeline.instantiate_stage", side_effect=mock_instantiate):
            pipeline = [Stage(type="http"), Stage(type="threshold", max=1000)]
            status, message, elapsed, _details = run_pipeline("https://example.com", pipeline)

        assert status == "up"
        assert "http:" in message
        assert "threshold:" in message
        assert elapsed == pytest.approx(100.1, rel=0.01)  # pyright: ignore[reportUnknownMemberType]

    def test_pipeline_worst_status_wins(self) -> None:
        """Test that worst status (down > degraded > up) is returned."""
        up_result = CheckResult(
            status=Status.UP,
            url="https://example.com",
            message="OK",
            elapsed_ms=10.0,
            details={},
        )
        down_result = CheckResult(
            status=Status.DOWN,
            url="https://example.com",
            message="Failed",
            elapsed_ms=10.0,
            details={},
        )

        mock_up = MagicMock()
        mock_up.check.return_value = up_result
        mock_down = MagicMock()
        mock_down.check.return_value = down_result

        def mock_instantiate(stage: Stage) -> MagicMock:
            return mock_up if stage.type == "http" else mock_down

        with patch("uptimer.pipeline.instantiate_stage", side_effect=mock_instantiate):
            pipeline = [Stage(type="http"), Stage(type="contains", pattern="missing")]
            status, _message, _elapsed, _details = run_pipeline("https://example.com", pipeline)

        assert status == "down"

    def test_pipeline_context_values_included(self) -> None:
        """Test that context values are included in details."""
        result = CheckResult(
            status=Status.UP,
            url="https://example.com",
            message="OK",
            elapsed_ms=10.0,
            details={},
        )

        def mock_check(url: str, verbose: bool = False, context: CheckContext | None = None) -> CheckResult:
            if context:
                context.values["extracted"] = 42
            return result

        mock_stage = MagicMock()
        mock_stage.check.side_effect = mock_check

        with patch("uptimer.pipeline.instantiate_stage", return_value=mock_stage):
            pipeline = [Stage(type="jq", expr=".count", store_as="extracted")]
            _status, _message, _elapsed, details = run_pipeline("https://example.com", pipeline)

        assert "_values" in details
        values: dict[str, Any] = details["_values"]  # type: ignore[assignment]
        assert values["extracted"] == 42
