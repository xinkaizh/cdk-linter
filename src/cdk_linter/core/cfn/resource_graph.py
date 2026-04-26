from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
import logging
from typing import Any
from cdk_linter.core.cfn.cfn_resource import CfnResource

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """Represents a node in resource graph"""
    resource: CfnResource
    outgoing_edges: list[GraphEdge] = field(default_factory=list)

    def __hash__(self):
        return hash(self.resource.id)


@dataclass
class GraphEdge:
    """Base class for an edge"""
    source: GraphNode
    destination: GraphNode
    type: GraphEdgeType
    metadata: dict[Any, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"GraphEdge({self.source.resource.id} -> {self.destination.resource.id} | {self.type.name})"


class GraphEdgeType(Enum):
    """Formally defines types of edges. Each type represents a different kind of relationship between two nodes."""
    ROLE_CONTAINS_POLICY = auto()  # src (IAM role) contains dst (IAM policy)
    LAMBDA_EXECUTION_ROLE = auto()  # src (Lambda) uses dst (IAM role) as execution role
    POLICY_ALLOWs_ACTION = auto()  # src (IAM policy) allows actions on dst (any type)

class ResourceGraph:
    """
    ResourceGraph is implemented as adjacency list:
    {
        n1: [e1, e2, e3, ...],
        n2: [e1, e2, ...],
        ...
    }
    """

    def __init__(self) -> None:
        self._all_nodes: set[GraphNode] = set()
        self._rid_to_node: dict[str, GraphNode] = dict()

    def get_node_by_rid(self, resource_id: str) -> GraphNode:
        return self._rid_to_node.get(resource_id)

    def add_node(self, node: GraphNode):
        """
        Add a GraphNode to the graph.
        If you don't want to manipulate raw GraphNode, use `add_resource()` instead.
        """
        self._all_nodes.add(node)
        self._rid_to_node[node.resource.id] = node

    def add_edge(self, edge: GraphEdge):
        """
        Add a GraphEdge to the graph.
        If you don't want to manipulate raw GraphEdge, use `connect_resources()` instead.
        """
        if edge.source not in self._all_nodes or edge.destination not in self._all_nodes:
            raise ValueError("Source or destination not exist in graph")
        edge.source.outgoing_edges.append(edge)
    
    def add_resource(self, resource: CfnResource):
        """
        Add a CfnResource to the graph (a GraphNode will be created automatically).
        """
        node = GraphNode(resource, [])
        self.add_node(node)

    def connect_resources(self, source: CfnResource, destination: CfnResource, type: GraphEdgeType, metadata: dict[Any, Any] = {}):
        """
        Connect two CfnResources together (a GraphEdge will be created automatically).
        """
        src_node = self.get_node_by_rid(source.id)
        dst_node = self.get_node_by_rid(destination.id)
        if src_node is None or dst_node is None:
            raise ValueError("Source or destination not exist in graph")
        edge = GraphEdge(source=src_node, destination=dst_node, type=type, metadata=metadata)
        self.add_edge(edge)
