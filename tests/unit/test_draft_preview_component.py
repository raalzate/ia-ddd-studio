"""Unit tests for src/ui/components/draft_preview.py — render_draft_preview."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from domain.models.draft import Draft, DraftSummary


def _make_draft(snapshot=None):
    return Draft(
        id=str(uuid.uuid4()),
        generation_id="gen-456",
        project_name="TestProject",
        summary=DraftSummary(
            label="TestProject v1.0 — 2 agg, 4 evt, 3 cmd",
            aggregate_count=2,
            event_count=4,
            command_count=3,
            node_total=9,
        ),
        snapshot=snapshot
        if snapshot is not None
        else {
            "nombre_proyecto": "TestProject",
            "version": "1.0",
            "big_picture": {
                "descripcion": "Big picture description",
                "nodos": [
                    {
                        "tipo_elemento": "Evento",
                        "nombre": "OrderCreated",
                        "descripcion": "Order was created",
                    }
                ],
            },
            "agregados": [
                {
                    "nombre_agregado": "OrderAgg",
                    "entidad_raiz": "Order",
                    "nodos": [
                        {
                            "tipo_elemento": "Agregado",
                            "nombre": "OrderAgg",
                            "descripcion": "Order aggregate",
                        }
                    ],
                }
            ],
            "read_models": [{"nombre": "Dashboard", "descripcion": "Shows orders"}],
        },
        created_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
        updated_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
    )


@patch("ui.components.draft_preview.st")
def test_render_draft_preview_shows_content(mock_st):
    from ui.components.draft_preview import render_draft_preview

    mock_st.expander.return_value.__enter__ = MagicMock()
    mock_st.expander.return_value.__exit__ = MagicMock()

    draft = _make_draft()
    render_draft_preview(draft)

    mock_st.subheader.assert_called_once()
    mock_st.caption.assert_called_once()


@patch("ui.components.draft_preview.st")
def test_render_draft_preview_empty_snapshot(mock_st):
    from ui.components.draft_preview import render_draft_preview

    draft = _make_draft(snapshot={"empty": True})
    # Override to falsy
    draft.snapshot = {}
    render_draft_preview(draft)

    mock_st.warning.assert_called_once()


@patch("ui.components.draft_preview.st")
def test_render_draft_preview_none_snapshot(mock_st):
    from ui.components.draft_preview import render_draft_preview

    draft = _make_draft()
    draft.snapshot = None
    render_draft_preview(draft)

    mock_st.warning.assert_called_once()
