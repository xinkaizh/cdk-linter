import importlib
import logging
from pathlib import Path
from cdk_linter.core.cfn.resource_graph import GraphEdgeType, ResourceGraph

logger = logging.getLogger(__name__)


def visualize(graph: ResourceGraph) -> None:
    """
    Generate a resource dependency visualization file at repo root.
    If `graphviz` is unavailable, logs a warning and returns None.
    """
    if not graph._all_nodes:
        raise ValueError("Cannot visualize an empty graph")

    def _format_edge_label(edge_type: GraphEdgeType) -> str:
        return edge_type.name.replace("_", " ").title()

    def _node_color(resource_type_name: str) -> str:
        color_map = {
            "LAMBDA": "#B3E5FC",
            "ROLE": "#FFE0B2",
            "POLICY": "#FFCDD2",
            "DDB": "#C8E6C9",
            "S3": "#FFF9C4",
            "SQS": "#D1C4E9",
        }
        return color_map.get(resource_type_name, "#E0E0E0")

    ordered_nodes = sorted(graph._all_nodes, key=lambda node: node.resource.id)
    ordered_edges = sorted(
        (edge for node in ordered_nodes for edge in node.outgoing_edges),
        key=lambda edge: (
            edge.source.resource.id,
            edge.destination.resource.id,
            edge.type.name,
        ),
    )

    try:
        graphviz = importlib.import_module("graphviz")
    except ImportError:
        logger.warning("graphviz package is not installed; skipping graph visualization")
        return

    dot = graphviz.Digraph("dependency_graph")
    dot.attr(rankdir="LR")
    dot.attr(
        "graph",
        bgcolor="white",
        splines="spline",
        nodesep="0.6",
        ranksep="1.0",
    )
    dot.attr(
        "node",
        shape="box",
        style="rounded,filled",
        fontname="Helvetica",
        color="#424242",
    )
    dot.attr("edge", fontname="Helvetica", color="#616161")

    for node in ordered_nodes:
        dot.node(
            node.resource.id,
            label=f"{node.resource.id}\n{node.resource.type.name}",
            fillcolor=_node_color(node.resource.type.name),
            tooltip=node.resource.type.value,
        )

    for edge in ordered_edges:
        dot.edge(
            edge.source.resource.id,
            edge.destination.resource.id,
            label=_format_edge_label(edge.type),
        )

    output_base = Path.cwd() / "dependency_graph"
    try:
        artifact_path = dot.render(
            filename=output_base.stem,
            directory=str(output_base.parent),
            format="svg",
            cleanup=True,
        )
    except Exception as e:
        logger.warning(f"failed to render dependency graph with graphviz: {e}")
        return

    logger.info(f"dependency graph generated at {artifact_path}")
