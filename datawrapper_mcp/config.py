"""Configuration and constants for the Datawrapper MCP server."""

import difflib
from typing import Any

from datawrapper import (
    AreaChart,
    ArrowChart,
    BarChart,
    BaseChart,
    ColumnChart,
    LineChart,
    MultipleColumnChart,
    ScatterPlot,
    StackedBarChart,
)

# Map of chart type names to their Pydantic classes
CHART_CLASSES: dict[str, type[Any]] = {
    "bar": BarChart,
    "line": LineChart,
    "area": AreaChart,
    "arrow": ArrowChart,
    "column": ColumnChart,
    "multiple_column": MultipleColumnChart,
    "scatter": ScatterPlot,
    "stacked_bar": StackedBarChart,
}


def resolve_chart_type(chart_type: str) -> type[Any]:
    """Look up a chart type's Pydantic class, or raise a helpful error.

    Datawrapper types without a typed class (UNTYPED_TYPES, by API id)
    resolve to BaseChart.

    The error lists close spelling matches (e.g. "stackedbar" ->
    "stacked_bar") so a calling model can self-correct on its next tool
    call, without needing an interactive round-trip back to a human.
    """
    if chart_type in CHART_CLASSES:
        return CHART_CLASSES[chart_type]
    if chart_type in UNTYPED_TYPES:
        return BaseChart
    suggestions = difflib.get_close_matches(
        chart_type, [*CHART_CLASSES, *UNTYPED_TYPES], n=3, cutoff=0.5
    )
    hint = (
        f"Did you mean: {', '.join(suggestions)}?"
        if suggestions
        else (
            f"Valid chart types: {', '.join(CHART_CLASSES)}. "
            f"Types without a typed schema, by API id: {', '.join(UNTYPED_TYPES)}."
        )
    )
    msg = f"Unknown chart_type '{chart_type}'. {hint}"
    raise ValueError(msg)


# Map Datawrapper API type IDs to simplified names
# See: https://developer.datawrapper.de/docs/chart-types
API_TYPE_TO_SIMPLIFIED: dict[str, str] = {
    "d3-bars": "bar",
    "d3-bars-stacked": "stacked_bar",
    "d3-arrow-plot": "arrow",
    "column-chart": "column",
    "multiple-columns": "multiple_column",
    "d3-area": "area",
    "d3-lines": "line",
    "d3-scatter-plot": "scatter",
}

# CAMBIO fork: every visualization type the Datawrapper API offers
# (GET /v3/visualizations), by API id.
DATAWRAPPER_TYPES: dict[str, str] = {
    "d3-bars": "Bar chart",
    "d3-bars-split": "Split bars - one bar panel per series, side by side",
    "d3-bars-stacked": "Stacked bars",
    "d3-bars-grouped": "Grouped bars - bars for several series grouped by category",
    "d3-bars-bullet": "Bullet bars - each bar against a target or comparison value",
    "d3-dot-plot": "Dot plot - several values per category as dots on one line",
    "d3-range-plot": "Range plot - the gap between two values per category",
    "d3-arrow-plot": "Arrow plot",
    "column-chart": "Column chart",
    "grouped-column-chart": "Grouped columns - columns for several series side by side",
    "stacked-column-chart": "Stacked columns - part-to-whole per category, vertical",
    "multiple-columns": "Small multiples of column charts",
    "d3-lines": "Line chart",
    "multiple-lines": "Multiple lines - small multiples of line charts",
    "d3-area": "Area chart",
    "d3-scatter-plot": "Scatter plot",
    "d3-pies": "Pie chart - parts of a whole",
    "d3-donuts": "Donut chart - parts of a whole, with a label in the center",
    "d3-multiple-pies": "Multiple pies - small multiples of pie charts",
    "d3-multiple-donuts": "Multiple donuts - small multiples of donut charts",
    "election-donut-chart": "Election donut - seats per party in a half or full donut",
    "tables": "Table - sortable and searchable, with optional heatmaps and bars",
    "d3-maps-choropleth": (
        "Choropleth map - regions colored by value. Needs a basemap and key "
        "settings: clone an existing map's metadata with get_chart"
    ),
    "d3-maps-symbols": (
        "Symbol map - sized symbols on a basemap. Clone an existing map's "
        "metadata with get_chart"
    ),
    "locator-map": (
        "Locator map - markers and areas on a map. Clone an existing map's "
        "metadata with get_chart"
    ),
}

# Types without a typed class. They are created as BaseChart, with their
# type-specific settings passed as raw Datawrapper metadata. The set shrinks
# on its own as typed classes are added to API_TYPE_TO_SIMPLIFIED.
UNTYPED_TYPES: dict[str, str] = {
    api_id: description
    for api_id, description in DATAWRAPPER_TYPES.items()
    if api_id not in API_TYPE_TO_SIMPLIFIED
}

# Types whose height follows their content (a row per bar, dot or table row),
# which the Datawrapper editor resizes to fit whenever it renders them. Other
# types keep the height they are given. /v3/visualizations lists these with a
# fixed height and without supportsFitHeight.
FIT_CONTENT_TYPES = {
    "d3-arrow-plot",
    "d3-bars",
    "d3-bars-bullet",
    "d3-bars-grouped",
    "d3-bars-split",
    "d3-bars-stacked",
    "d3-dot-plot",
    "d3-range-plot",
    "tables",
}


def fits_content(chart_type: str) -> bool:
    """Whether a type, by simplified name or API id, is sized to its content."""
    api_types = {name: api for api, name in API_TYPE_TO_SIMPLIFIED.items()}
    return api_types.get(chart_type, chart_type) in FIT_CONTENT_TYPES
