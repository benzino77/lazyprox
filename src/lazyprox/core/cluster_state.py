from collections.abc import Sequence
from dataclasses import dataclass

from lazyprox.data import ProxmoxData


@dataclass(frozen=True)
class NodeState:
    name: str
    status: str


def snapshot_nodes() -> list[NodeState]:
    raw_nodes = ProxmoxData.p_prox_resources.get(ProxmoxData.BASE_NODES, [])
    return [NodeState(name=node["node"], status=str(node.get("status", ""))) for node in raw_nodes]


def online_node_names(nodes: Sequence[NodeState]) -> list[str]:
    return [node.name for node in nodes if node.status == "online"]
