"""Handler for creating Datawrapper charts."""

import asyncio
from typing import Any

from datawrapper import BaseChart
from mcp.types import ImageContent

from datawrapper_mcp.config import resolve_chart_type
from datawrapper_mcp.types import CreateChartArgs
from datawrapper_mcp.utils import json_to_dataframe

from .preview import try_export_preview


def untyped_chart_config(chart_type: str, config: dict[str, Any]) -> dict[str, Any]:
    """Prepare the config of a type without a typed class, built as BaseChart.

    BaseChart only warns about fields it doesn't know and then drops them, so a
    typed-class field such as color_category would vanish without notice.
    Reject those instead and point to metadata, where type settings go.
    """
    fields = BaseChart.model_fields
    known = {*fields, *(field.alias for field in fields.values() if field.alias)}
    unknown = sorted(set(config) - known)
    if unknown:
        raise ValueError(
            f"Unknown field(s) for '{chart_type}': {', '.join(unknown)}. Types "
            "without a typed schema only take the common fields shown by "
            "get_chart_schema. Put type-specific settings in metadata, e.g. "
            '{"metadata": {"visualize": {...}, "axes": {...}}}.'
        )
    # get_chart's config carries the type too; the API id passed here wins
    config = {k: v for k, v in config.items() if k not in ("chart_type", "chart-type")}
    return {**config, "chart-type": chart_type}


async def create_chart(
    arguments: CreateChartArgs,
) -> tuple[dict[str, Any], list[ImageContent]]:
    """Create a chart with full Pydantic model configuration.

    Returns:
        A tuple of (metadata_dict, preview_images).
    """
    chart_type = arguments["chart_type"]
    token = arguments.get("access_token") or None  # normalize "" → None

    # Convert data to DataFrame
    df = json_to_dataframe(arguments["data"])

    # Get chart class and validate config
    chart_class: type[Any] = resolve_chart_type(chart_type)

    # Validate and create chart using Pydantic model
    try:
        config = arguments["chart_config"]
        if chart_class is BaseChart:
            config = untyped_chart_config(chart_type, config)
        chart = chart_class.model_validate(config)
    except Exception as e:
        raise ValueError(
            f"Invalid chart configuration: {e!s}\n\n"
            f"Use get_chart_schema with chart_type '{chart_type}' "
            f"to see the valid schema."
        ) from e

    # Set data on chart instance
    chart.data = df

    # Create chart using Pydantic instance method. Synchronous and
    # network-bound, so run it off the event loop (see export.py/preview.py).
    await asyncio.to_thread(
        chart.create, access_token=token, folder_id=arguments.get("folder_id")
    )

    metadata: dict[str, Any] = {
        "chart_id": chart.chart_id,
        "chart_type": chart_type,
        "title": chart.title,
        "edit_url": chart.get_editor_url(),
    }

    # Size the chart to fit, unless its metadata already gives it a height
    # (say, settings copied from a chart made in the editor).
    raw_metadata = config.get("metadata") or config.get("raw_metadata") or {}
    fit_height = "embed-height" not in raw_metadata.get("publish", {})
    images: list[ImageContent] = []
    preview = await try_export_preview(chart, access_token=token, fit_height=fit_height)
    if preview:
        images.append(preview)

    return metadata, images
