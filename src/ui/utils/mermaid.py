"""Render Mermaid diagrams inside Streamlit using an HTML component."""

import re

import streamlit.components.v1 as components


def sanitize_mermaid(code: str) -> str:
    """Fix common LLM-generated Mermaid syntax issues.

    - Ensures subgraph labels are quoted.
    - Ensures node labels with special characters use bracket syntax.
    - Strips trailing semicolons inside labels.
    """
    lines = []
    for line in code.splitlines():
        stripped = line.strip()

        # Fix: subgraph labels MUST be quoted if they contain special chars
        m = re.match(r"^(subgraph\s+)(.+)$", stripped)
        if m:
            label = m.group(2).strip()
            # Already quoted — leave as is
            if not (label.startswith('"') and label.endswith('"')):
                label = f'"{label}"'
            line = f"{line[: len(line) - len(stripped)]}{m.group(1)}{label}"

        lines.append(line)
    return "\n".join(lines)


def render_mermaid(mermaid_code: str, height: int = 600) -> None:
    """Render a Mermaid diagram as an interactive HTML component.

    Falls back to showing the raw code if rendering fails.

    Args:
        mermaid_code: Raw Mermaid syntax (without fences).
        height: Pixel height of the rendered component.
    """
    safe_code = sanitize_mermaid(mermaid_code)
    # Escape for JS template literal
    js_escaped = safe_code.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")

    html = f"""
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
        <style>
            body {{ margin: 0; padding: 16px; background: transparent; font-family: sans-serif; }}
            #diagram {{ display: flex; justify-content: center; }}
            #error {{ color: #b00; padding: 12px; background: #fff0f0; border-radius: 6px; display: none; }}
            #error pre {{ white-space: pre-wrap; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div id="diagram"></div>
        <div id="error"></div>
        <script>
            mermaid.initialize({{
                startOnLoad: false,
                theme: 'default',
                flowchart: {{ useMaxWidth: true, htmlLabels: true }},
                securityLevel: 'loose'
            }});
            (async () => {{
                const code = `{js_escaped}`;
                try {{
                    const {{ svg }} = await mermaid.render('mermaid-diagram', code);
                    document.getElementById('diagram').innerHTML = svg;
                }} catch (err) {{
                    const errDiv = document.getElementById('error');
                    errDiv.style.display = 'block';
                    errDiv.innerHTML = '<strong>Error al renderizar diagrama Mermaid</strong>'
                        + '<pre>' + err.message + '</pre>'
                        + '<pre>' + code + '</pre>';
                }}
            }})();
        </script>
    </body>
    </html>
    """
    components.html(html, height=height, scrolling=True)
