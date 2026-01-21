"""Shared pipeline execution utilities."""

from typing import Any

import structlog

from uptimer.schemas import Stage
from uptimer.stages import CheckContext, get_stage

logger = structlog.get_logger()


def instantiate_stage(stage: Stage) -> Any:
    """Instantiate a stage with the appropriate options from Stage config.

    Args:
        stage: Stage configuration from monitor pipeline

    Returns:
        Instantiated stage object ready for checking
    """
    stage_class = get_stage(stage.type)

    # Build kwargs from Stage options
    kwargs: dict[str, Any] = {}

    # Auth options (for dhis2, etc.)
    if stage.username:
        kwargs["username"] = stage.username
    if stage.password:
        kwargs["password"] = stage.password

    # Value extractor options
    if stage.expr:
        kwargs["expr"] = stage.expr
    if stage.store_as:
        kwargs["store_as"] = stage.store_as

    # Threshold options
    if stage.min is not None:
        kwargs["min_value"] = stage.min
    if stage.max is not None:
        kwargs["max_value"] = stage.max
    if stage.value:
        kwargs["value_ref"] = stage.value

    # Pattern/contains options
    if stage.pattern:
        kwargs["pattern"] = stage.pattern
    if stage.negate:
        kwargs["negate"] = stage.negate

    # Age stage options
    if stage.max_age is not None:
        kwargs["max_age"] = stage.max_age

    # SSL options (only for ssl stage)
    if stage.type == "ssl" and stage.warn_days:
        kwargs["warn_days"] = stage.warn_days

    # TCP options
    if stage.port is not None:
        kwargs["port"] = stage.port

    # DNS options
    if stage.expected_ip:
        kwargs["expected_ip"] = stage.expected_ip

    # JSON schema options
    if stage.schema_:
        kwargs["schema"] = stage.schema_

    # HTTP headers
    if stage.headers:
        kwargs["headers"] = stage.headers

    # Try to instantiate with kwargs, fall back to no-args
    try:
        return stage_class(**kwargs)
    except TypeError as e:
        logger.warning(
            "Stage instantiation with options failed, using defaults",
            stage_type=stage.type,
            error=str(e),
            provided_options=list(kwargs.keys()),
        )
        return stage_class()


def run_pipeline(url: str, pipeline: list[Stage]) -> tuple[str, str, float, dict[str, object]]:
    """Run all pipeline stages for a monitor and return aggregated results.

    Args:
        url: URL to check
        pipeline: List of pipeline stage configurations

    Returns:
        Tuple of (final_status, message, total_elapsed_ms, all_details)
    """
    # Create shared context for the pipeline
    context = CheckContext(url=url)

    all_details: dict[str, object] = {}
    total_elapsed_ms = 0.0
    final_status = "up"
    messages: list[str] = []

    for i, stage in enumerate(pipeline):
        stage_instance = instantiate_stage(stage)
        result = stage_instance.check(url, verbose=False, context=context)

        total_elapsed_ms += result.elapsed_ms
        messages.append(f"{stage.type}: {result.message}")

        # Store stage details with index to handle multiple stages of same type
        stage_key = f"{stage.type}" if pipeline.count(stage) == 1 else f"{stage.type}_{i}"
        all_details[stage_key] = result.details

        # Use worst status (down > degraded > up)
        if result.status.value == "down":
            final_status = "down"
        elif result.status.value == "degraded" and final_status != "down":
            final_status = "degraded"

    # Include extracted values in details
    if context.values:
        all_details["_values"] = context.values

    return final_status, "; ".join(messages), total_elapsed_ms, all_details
