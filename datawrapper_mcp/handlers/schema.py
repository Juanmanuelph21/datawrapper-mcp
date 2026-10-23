"""Handler for retrieving chart schemas."""

import json
from typing import Any

from datawrapper import BaseChart
from mcp.types import TextContent

from datawrapper_mcp.config import resolve_chart_type
from datawrapper_mcp.types import GetChartSchemaArgs

UNTYPED_USAGE = (
    "'{chart_type}' has no typed schema yet. This schema lists the common fields "
    "(title, intro, byline, source_name, source_url, notes, theme, language, "
    "transformations...), which go at the top level of chart_config and win "
    "over anything in metadata. Put this type's own settings in "
    'chart_config["metadata"] as raw Datawrapper metadata: metadata.visualize '
    "for styling and metadata.axes to map data columns. The reliable way to get "
    "them right is to read a chart of this type made in the Datawrapper editor "
    "with get_chart and reuse its metadata.visualize and metadata.axes. "
    "Text and data settings (describe, data) belong in the top-level fields, "
    "not in metadata."
)


def clean_chart_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Strip schema examples that embed a DataFrame (not JSON serializable)."""
    schema.pop("examples", None)
    return schema


async def get_chart_schema(arguments: GetChartSchemaArgs) -> list[TextContent]:
    """Get the Pydantic schema for a chart type."""
    chart_type = arguments["chart_type"]
    chart_class: type[Any] = resolve_chart_type(chart_type)

    schema = clean_chart_schema(chart_class.model_json_schema())

    result = {
        "chart_type": chart_type,
        "class_name": chart_class.__name__,
        "schema": schema,
        "usage": (
            "Use this schema to construct a chart_config dict for create_chart. "
            "The schema shows all available properties, their types, and descriptions."
        ),
    }
    if chart_class is BaseChart:
        result["usage"] = UNTYPED_USAGE.format(chart_type=chart_type)

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
