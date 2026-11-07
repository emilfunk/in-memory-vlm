"""Unit tests for OpenCLI client integration."""

from in_memory_vlm.browser.opencli_client import is_opencli_available, get_dom_extractor_script


def test_get_dom_extractor_script():
    script = get_dom_extractor_script()
    assert "OffscreenCanvas" in script
    assert "video" in script


def test_is_opencli_available():
    # Verify opencli detection returns a boolean cleanly without raising
    result = is_opencli_available()
    assert isinstance(result, bool)
