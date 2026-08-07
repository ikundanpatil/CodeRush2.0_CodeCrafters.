"""In-memory node/edge representation of an evidence graph, serializable for
the /api/evidence/graph/{research_run_id} response."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class GraphNode:
    id: str
    type: str
    label: str


@dataclass
class GraphEdge:
    from_: str
    to: str
    relationship: str


@dataclass
class EvidenceGraph:
    research_run_id: str
    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)

    def add_node(self, node_id: str, node_type: str, label: str):
        if any(n.id == node_id for n in self.nodes):
            return
        self.nodes.append(GraphNode(id=node_id, type=node_type, label=label))

    def add_edge(self, from_id: str, to_id: str, relationship: str):
        self.edges.append(GraphEdge(from_=from_id, to=to_id, relationship=relationship))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "research_run_id": self.research_run_id,
            "nodes": [{"id": n.id, "type": n.type, "label": n.label} for n in self.nodes],
            "edges": [{"from": e.from_, "to": e.to, "relationship": e.relationship} for e in self.edges],
        }
