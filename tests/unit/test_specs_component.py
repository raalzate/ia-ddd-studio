"""Unit tests for src/ui/components/specs.py — _clean_puml helper."""


class TestCleanPuml:
    def test_strips_markdown_fences(self):
        from ui.components.specs import _clean_puml

        raw = "```plantuml\n@startuml\nA -> B\n@enduml\n```"
        result = _clean_puml(raw)
        assert result.startswith("@startuml")
        assert result.endswith("@enduml")
        assert "```" not in result

    def test_no_fences(self):
        from ui.components.specs import _clean_puml

        raw = "@startuml\nA -> B\n@enduml"
        result = _clean_puml(raw)
        assert result == raw

    def test_strips_prose_before_startuml(self):
        from ui.components.specs import _clean_puml

        raw = "Here is the diagram:\n@startuml\nA -> B\n@enduml"
        result = _clean_puml(raw)
        assert result.startswith("@startuml")

    def test_empty_input(self):
        from ui.components.specs import _clean_puml

        assert _clean_puml("") == ""

    def test_only_backticks(self):
        from ui.components.specs import _clean_puml

        result = _clean_puml("```\ncontent\n```")
        assert "```" not in result
        assert "content" in result

    def test_handles_fences_without_newline(self):
        from ui.components.specs import _clean_puml

        result = _clean_puml("```")
        assert "```" not in result
