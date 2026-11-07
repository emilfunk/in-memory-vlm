"""Unit tests for CDP browser integration."""

import pytest
from in_memory_vlm.browser.cdp_client import CDPError, extract_from_browser_tab, get_dom_extractor_script


def test_get_dom_extractor_script():
    script = get_dom_extractor_script()
    assert "OffscreenCanvas" in script
    assert "convertToBlob" in script
    assert "keyframes" in script


@pytest.mark.asyncio
async def test_cdp_connection_refused():
    # Connecting to an unused port should raise CDPError
    with pytest.raises(CDPError, match="Could not connect to browser CDP"):
        await extract_from_browser_tab(cdp_port=59999, target_url="https://example.com")
