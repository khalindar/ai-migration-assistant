import json


def build_mermaid(dependencies: dict) -> str:
    """
    Build a Mermaid graph TD diagram from a dependency dict.
    dependencies = {
        "ServiceA": ["ServiceB", "ServiceC"],
        "ServiceB": ["Redis"],
        ...
    }
    """
    lines = ["graph TD"]
    seen_edges = set()

    for source, targets in dependencies.items():
        src = _sanitize(source)
        if not targets:
            lines.append(f"    {src}")
        for target in targets:
            tgt = _sanitize(target)
            edge = f"{src} --> {tgt}"
            if edge not in seen_edges:
                lines.append(f"    {edge}")
                seen_edges.add(edge)

    return "\n".join(lines)


def build_plotly_graph_data(dependencies: dict) -> dict:
    """
    Convert dependencies into Plotly-compatible nodes and edges for a network graph.
    Returns {"nodes": [...], "edges": [...]}
    """
    nodes = set()
    edges = []

    for source, targets in dependencies.items():
        nodes.add(source)
        for target in targets:
            nodes.add(target)
            edges.append({"from": source, "to": target})

    node_list = [{"id": n, "label": n} for n in nodes]
    return {"nodes": node_list, "edges": edges}


def _sanitize(name: str) -> str:
    return name.replace(" ", "_").replace("-", "_").replace(".", "_")


def render_mermaid_html(diagram: str) -> str:
    escaped = diagram.replace("`", "\\`")
    return f"""
    <div style="background:#1a1a2e;border-radius:12px;padding:20px;">
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({{startOnLoad:true, theme:'dark'}});</script>
    <div class="mermaid">
{diagram}
    </div>
    </div>
    """
