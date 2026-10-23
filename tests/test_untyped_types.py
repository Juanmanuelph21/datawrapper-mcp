"""Datawrapper types without a typed class, created and edited as BaseChart.

CAMBIO fork only: these types travel as raw Datawrapper metadata until the
datawrapper library gets a typed class for them.
"""

import json
from unittest.mock import patch

import pytest
from datawrapper import BaseChart
from fastmcp import Client

from datawrapper_mcp.config import (
    API_TYPE_TO_SIMPLIFIED,
    CHART_CLASSES,
    DATAWRAPPER_TYPES,
    UNTYPED_TYPES,
    resolve_chart_type,
)
from datawrapper_mcp.handlers.create import create_chart
from datawrapper_mcp.handlers.retrieve import get_chart_info
from datawrapper_mcp.handlers.schema import get_chart_schema
from datawrapper_mcp.handlers.update import update_chart
from datawrapper_mcp.server import mcp
from datawrapper_mcp.utils import deep_merge

DONUT_METADATA = {
    "axes": {"slices": "seats"},
    "visualize": {
        "donut_hole_size": 45,
        "show_percent": True,
        "pie_size": {"inside_labels": 85, "outside_labels": 50},
    },
}


def fetched_donut() -> BaseChart:
    """A donut chart as get_chart returns it: a BaseChart with raw metadata."""
    return BaseChart.model_validate(
        {
            "chart-type": "d3-donuts",
            "chart_id": "abc12",
            "title": "Seats by party",
            "metadata": {
                **DONUT_METADATA,
                "describe": {"number-format": "0.0%"},
            },
        }
    )


# -- config --


def test_untyped_types_exclude_typed_classes():
    assert set(UNTYPED_TYPES) == set(DATAWRAPPER_TYPES) - set(API_TYPE_TO_SIMPLIFIED)
    assert "d3-pies" in UNTYPED_TYPES
    assert "d3-bars" not in UNTYPED_TYPES
    assert set(API_TYPE_TO_SIMPLIFIED) <= set(DATAWRAPPER_TYPES)


def test_untyped_types_resolve_to_base_chart():
    assert resolve_chart_type("tables") is BaseChart
    assert resolve_chart_type("bar") is CHART_CLASSES["bar"]


def test_unknown_type_suggests_untyped_ids():
    with pytest.raises(ValueError, match="Did you mean: d3-pies"):
        resolve_chart_type("d3-pie")


# -- create_chart --


async def test_create_untyped_chart_passes_metadata():
    created = []

    def fake_create(self, access_token=None, folder_id=None):
        self.chart_id = "new12"
        created.append(self)

    with (
        patch.object(BaseChart, "create", fake_create),
        patch("datawrapper_mcp.handlers.create.try_export_preview", return_value=None),
    ):
        result, _ = await create_chart(
            {
                "data": [{"party": "A", "seats": 10}, {"party": "B", "seats": 5}],
                "chart_type": "d3-donuts",
                "chart_config": {
                    "title": "Seats by party",
                    "theme": "cambio-colombia",
                    "metadata": DONUT_METADATA,
                },
            }
        )

    assert result["chart_id"] == "new12"
    assert result["chart_type"] == "d3-donuts"
    serialized = created[0].serialize_model()
    assert serialized["type"] == "d3-donuts"
    assert serialized["theme"] == "cambio-colombia"
    metadata = serialized["metadata"]
    assert metadata["axes"] == {"slices": "seats"}
    assert metadata["visualize"]["donut_hole_size"] == 45
    assert metadata["visualize"]["pie_size"] == {
        "inside_labels": 85,
        "outside_labels": 50,
    }


async def test_create_untyped_chart_rejects_typed_fields():
    with pytest.raises(ValueError, match=r"color_category.*metadata"):
        await create_chart(
            {
                "data": [{"party": "A", "seats": 10}],
                "chart_type": "d3-pies",
                "chart_config": {"title": "T", "color_category": {"A": "#ff0000"}},
            }
        )


def test_create_untyped_config_uses_requested_type():
    from datawrapper_mcp.handlers.create import untyped_chart_config

    # A config copied from get_chart still names the old type
    config = untyped_chart_config(
        "d3-pies", {"title": "T", "chart_type": "d3-donuts", "metadata": {}}
    )

    assert BaseChart.model_validate(config).chart_type == "d3-pies"


# -- get_chart --


async def test_get_untyped_chart_returns_metadata():
    with patch(
        "datawrapper_mcp.handlers.retrieve.get_chart", return_value=fetched_donut()
    ):
        result = await get_chart_info({"chart_id": "abc12"})

    data = json.loads(result[0].text)
    assert data["type"] == "d3-donuts"
    assert data["metadata"]["axes"] == {"slices": "seats"}
    assert data["metadata"]["visualize"]["donut_hole_size"] == 45


# -- update_chart --


async def test_update_untyped_chart_merges_metadata():
    chart = fetched_donut()

    with (
        patch("datawrapper_mcp.handlers.update.get_chart", return_value=chart),
        patch.object(BaseChart, "update", lambda self, access_token=None: None),
        patch("datawrapper_mcp.handlers.update.try_export_preview", return_value=None),
    ):
        await update_chart(
            {
                "chart_id": "abc12",
                "chart_config": {
                    "title": "New title",
                    "metadata": {"visualize": {"pie_size": {"inside_labels": 70}}},
                },
            }
        )

    assert chart.title == "New title"
    visualize = chart.raw_metadata["visualize"]
    assert visualize["pie_size"] == {"inside_labels": 70, "outside_labels": 50}
    assert visualize["donut_hole_size"] == 45
    assert chart.raw_metadata["axes"] == {"slices": "seats"}
    assert chart.serialize_model()["metadata"]["describe"]["number-format"] == "0.0%"


async def test_update_untyped_chart_rejects_non_dict_metadata():
    with (
        patch(
            "datawrapper_mcp.handlers.update.get_chart", return_value=fetched_donut()
        ),
        pytest.raises(ValueError, match="Invalid chart configuration"),
    ):
        await update_chart({"chart_id": "abc12", "chart_config": {"metadata": "x"}})


# -- get_chart_schema and list_chart_types --


async def test_schema_for_untyped_type_explains_metadata():
    result = await get_chart_schema({"chart_type": "d3-pies"})

    data = json.loads(result[0].text)
    assert data["class_name"] == "BaseChart"
    assert "metadata" in data["schema"]["properties"]
    assert "metadata.visualize" in data["usage"]
    assert "get_chart" in data["usage"]


async def test_list_chart_types_includes_untyped_types():
    async with Client(transport=mcp) as client:
        result = await client.call_tool("list_chart_types", {})

    text = result.content[0].text
    assert "• d3-pies:" in text
    assert "• tables:" in text
    assert "• d3-bars:" not in text


# -- deep_merge --


def test_deep_merge_recurses_into_dicts_and_replaces_the_rest():
    base = {"a": {"b": 1, "c": [1, 2]}, "d": 1}

    merged = deep_merge(base, {"a": {"c": [3], "e": 2}, "d": {"f": 1}})

    assert merged == {"a": {"b": 1, "c": [3], "e": 2}, "d": {"f": 1}}
    assert base == {"a": {"b": 1, "c": [1, 2]}, "d": 1}
