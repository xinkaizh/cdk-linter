from __future__ import annotations
from dataclasses import dataclass, field
from cdk_linter.core.cfn.cfn_resource import CfnResource

"""
ResourceGraph is implemented as adjacency list:
{
    n1: [e1, e2, e3, ...],
    n2: [e1, e2, ...],
    ...
}
"""

@dataclass
class GraphNode:
    """Represents a node in resource graph"""
    resource: CfnResource
    outgoing_edges: list[GraphEdge] = field(default_factory=list)


@dataclass
class GraphEdge:
    """Base class for an edge"""
    source: GraphNode
    destination: GraphNode


@dataclass
class ResourceGraph:
    data: set[GraphNode]
