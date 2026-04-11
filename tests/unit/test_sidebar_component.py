"""Unit tests for src/ui/components/sidebar.py — helper functions."""

from unittest.mock import patch


@patch("ui.components.sidebar.st")
def test_get_draft_service_creates_singleton(mock_st):
    from ui.components.sidebar import _get_draft_service

    mock_st.session_state = {}
    service = _get_draft_service()
    assert service is not None
    assert "_draft_service" in mock_st.session_state


@patch("ui.components.sidebar.st")
def test_get_draft_service_returns_existing(mock_st):
    from ui.components.sidebar import _get_draft_service

    sentinel = object()
    mock_st.session_state = {"_draft_service": sentinel}
    service = _get_draft_service()
    assert service is sentinel
