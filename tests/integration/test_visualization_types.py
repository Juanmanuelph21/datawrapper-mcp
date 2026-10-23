"""DATAWRAPPER_TYPES must match the types the Datawrapper API offers.

CAMBIO fork only. Needs network access, so it runs with the integration tests.
"""

import pytest
import requests

from datawrapper_mcp.config import DATAWRAPPER_TYPES


@pytest.mark.integration
def test_datawrapper_types_match_the_api():
    response = requests.get("https://api.datawrapper.de/v3/visualizations", timeout=30)
    response.raise_for_status()

    assert {vis["id"] for vis in response.json()} == set(DATAWRAPPER_TYPES)
