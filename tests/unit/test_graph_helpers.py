"""Unit tests for pure helper functions in src/ui/visualization/graph.py."""


def test_edge_style_returns_matching_keyword():
    from ui.visualization.graph import _edge_style

    color, style, pw = _edge_style("Este comando dispara el proceso")
    assert color == "#42A5F5"
    assert style == "solid"


def test_edge_style_returns_default_for_unknown():
    from ui.visualization.graph import _edge_style

    color, style, pw = _edge_style("some unknown description")
    assert color == "#90A4AE"
    assert style == "solid"
    assert pw == "1.0"


def test_edge_style_case_insensitive():
    from ui.visualization.graph import _edge_style

    color, _, _ = _edge_style("PRODUCE un evento")
    assert color == "#FF8C00"


def test_html_label_generates_valid_html():
    from ui.visualization.graph import _html_label

    result = _html_label("Evento", "OrderCreated")
    assert "OrderCreated" in result
    assert "Evento" in result
    assert result.startswith("<<TABLE")
    assert result.endswith(">>")


def test_html_label_with_badge():
    from ui.visualization.graph import _html_label

    result = _html_label("Comando", "CreateOrder", badge=" [NEW]")
    assert "[NEW]" in result


def test_html_label_escapes_special_chars():
    from ui.visualization.graph import _html_label

    result = _html_label("Evento", "Order<Created>&More")
    assert "&lt;" in result
    assert "&amp;" in result


def test_style_dict_contains_standard_types():
    from ui.visualization.graph import _STYLE

    expected_types = ["Actor", "Comando", "Evento", "Agregado", "Política", "Read Model"]
    for t in expected_types:
        assert t in _STYLE, f"Missing style for {t}"
        fill, font, shape, style, border = _STYLE[t]
        assert fill.startswith("#")
        assert font.startswith("#")


def test_state_badge_mapping():
    from ui.visualization.graph import _STATE_BADGE

    assert _STATE_BADGE["nuevo"] == " [NEW]"
    assert _STATE_BADGE["modificado"] == " [MOD]"
    assert _STATE_BADGE["eliminado"] == " [DEL]"
    assert _STATE_BADGE["existente"] == ""


def test_rank_order_covers_main_types():
    from ui.visualization.graph import _RANK_ORDER

    assert _RANK_ORDER["Actor"] < _RANK_ORDER["Comando"]
    assert _RANK_ORDER["Comando"] < _RANK_ORDER["Evento"]
    assert _RANK_ORDER["Evento"] < _RANK_ORDER["Read Model"]


def test_icons_dict_has_entries_for_styles():
    from ui.visualization.graph import _ICONS, _STYLE

    for tipo in _STYLE:
        assert tipo in _ICONS, f"Missing icon for {tipo}"


def test_edge_keywords_coverage():
    from ui.visualization.graph import _EDGE_KEYWORDS

    assert "dispara" in _EDGE_KEYWORDS
    assert "produce" in _EDGE_KEYWORDS
    assert "proyecta" in _EDGE_KEYWORDS
    assert "activa" in _EDGE_KEYWORDS
