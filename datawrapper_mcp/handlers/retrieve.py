"""Handler for retrieving chart information."""

import asyncio
import json
from typing import Any

from datawrapper import BaseChart, get_chart
from mcp.types import TextContent

from datawrapper_mcp.config import API_TYPE_TO_SIMPLIFIED
from datawrapper_mcp.types import GetChartArgs


async def get_chart_info(arguments: GetChartArgs) -> list[TextContent]:
    """Get information about an existing chart including complete configuration."""
    chart_id = arguments["chart_id"]
    token = arguments.get("access_token")

    # Get chart using factory function. Synchronous and network-bound, so
    # run it off the event loop (see export.py/preview.py).
    chart = await asyncio.to_thread(get_chart, chart_id, access_token=token)

    # Get the complete config
    config = chart.model_dump()

    # Convert DataFrame to list of records if data exists
    if config.get("data") is not None and hasattr(config["data"], "to_dict"):
        config["data"] = config["data"].to_dict(orient="records")

    # Convert API type to simplified name for consistency with list_chart_types
    simplified_type = API_TYPE_TO_SIMPLIFIED.get(chart.chart_type, chart.chart_type)

    result: dict[str, Any] = {
        "chart_id": chart.chart_id,
        "title": chart.title,
        "type": simplified_type,
        "config": config,
        "public_url": chart.get_public_url(),
        "edit_url": chart.get_editor_url(),
    }

    # A type without a typed class keeps its own settings in the raw API
    # metadata, which model_dump() leaves out. Return it so they can be read,
    # reused in create_chart or changed with update_chart.
    if type(chart) is BaseChart:
        result["metadata"] = chart.raw_metadata

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
