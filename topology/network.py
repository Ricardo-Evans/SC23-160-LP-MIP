import typing
from typing import Any

import deprecated
import gurobipy as gp

InjectRateName = "inject_rate"
InjectRateConstraintName = "inject_rate_constraint"
Variables = typing.NamedTuple("Variables", flow_status=dict['Edge', dict['Flow', gp.Var]] | None, inject_rate=gp.Var, enabled_edges=dict['Edge', gp.Var] | None)
Constraints = typing.NamedTuple("Constraints",
                                inject_rate_constraint=gp.Constr, edge_capacity_constraints=dict['Edge', gp.Constr], net_flow_rate_at_each_node_constraints=dict['Node', dict['Flow', gp.Constr]],
                                enabled_edges_constraints=dict['Edge', gp.Constr] | None, conflict_edges_constraints=dict[str, gp.Constr] | None, synchronous_edges_constraints=dict[str, gp.Constr] | None)
TrafficPattern = set['Flow']
CompiledNetwork = tuple[gp.Model, Variables, Constraints]


class Node:
    def __init__(self, name: str) -> None:
        self.name = name

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.name == other.name
        else:
            return False

    def __hash__(self) -> int:
        return hash(self.name)

    def __str__(self) -> str:
        return self.name


class Edge:
    def __init__(self, name: str, start: Node, end: Node, capacity: float) -> None:
        self.name = name
        self.start = start
        self.end = end
        self.capacity = capacity

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.name == other.name and self.start == other.start and self.end == other.end
        else:
            return False

    def __hash__(self) -> int:
        return hash((self.name, self.start, self.end))

    def __str__(self) -> str:
        return self.name

    def is_connected_to(self, node: Node) -> bool:
        return self.start == node or self.end == node

    def net_coefficient_at(self, node: Node) -> float:
        return (
            -1.0 if node == self.start else
            1.0 if node == self.end else
            0.0
        )


class Flow:
    def __init__(self, start: Node, end: Node, rate: float) -> None:
        self.start = start
        self.end = end
        self.rate = rate

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.start == other.start and self.end == other.end
        else:
            return False

    def __hash__(self) -> int:
        return hash((self.start, self.end))

    def __str__(self) -> str:
        return f"flow from {self.start} to {self.end}"

    def net_rate_at(self, node: Node) -> float:
        return (
            -self.rate if node == self.start else
            self.rate if node == self.end else
            0.0
        )


class Network:

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, Edge] = {}
        self.conflict_edges: dict[str, set[Edge]] = {}
        self.synchronous_edges: dict[str, set[Edge]] = {}

    @deprecated.deprecated("not implemented correctly yet")
    def merge(self, network: 'Network') -> None:
        pass
        # self.merge_nodes(network)
        # self.merge_edges(network)
        # self.conflict_edges.union(network.conflict_edges)
        # self.synchronous_edges.union(network.synchronous_edges)

    def merge_nodes(self, network: 'Network') -> None:
        for key, value in network.nodes.items():
            if key in self.nodes:
                raise ValueError(f"node {key} already exist in network")
            self.nodes[key] = value

    def merge_edges(self, network: 'Network') -> None:
        for key, value in network.edges.items():
            if key in self.edges:
                raise ValueError(f"edge {key} already exist in network")
            self.edges[key] = value

    def insert_node(self, name: str) -> Node:
        node = Node(name)
        self.nodes[name] = node
        return node

    def insert_edge(self, name: str, start: Node, end: Node, capacity: float) -> Edge:
        edge = Edge(name, start, end, capacity)
        self.edges[name] = edge
        return edge

    def find_node(self, name: str) -> Node:
        return self.nodes[name]

    def find_edge(self, name: str) -> Edge:
        return self.edges[name]

    def delete_node(self, node: Node) -> None:
        del self.nodes[node.name]

    def delete_edge(self, edge: Edge) -> None:
        del self.edges[edge.name]

    def define_conflict_edges(self, name: str, *edges: Edge) -> None:
        if len(edges) <= 1:
            raise ValueError("at least two edges must be provided")
        self.conflict_edges[name] = set(edges)

    def define_synchronous_edges(self, name: str, *edges: Edge) -> None:
        if len(edges) <= 1:
            raise ValueError("at least two edges must be provided")
        self.synchronous_edges[name] = set(edges)

    def node_count(self) -> int:
        return len(self.nodes)

    def edge_count(self) -> int:
        return len(self.edges)

    def compile(self, traffic_pattern: TrafficPattern, initial_inject_rate=1.0, optimize_empty_flows: bool = True) -> CompiledNetwork:
        print("compiling model")
        model = gp.Model()
        print("compiling topology information")
        directly_connected_edges: dict[Node, set[Edge]] = {}
        for edge in self.edges.values():
            if edge.start not in directly_connected_edges:
                directly_connected_edges[edge.start] = set()
            if edge.end not in directly_connected_edges:
                directly_connected_edges[edge.end] = set()
            directly_connected_edges[edge.start].add(edge)
            directly_connected_edges[edge.end].add(edge)
        print("compiling flow rates at every edge")
        flow_status: dict[Edge, dict[Flow, gp.Var]] = {
            edge: {
                flow: model.addVar(lb=0.0, ub=gp.GRB.INFINITY, obj=0.0, vtype=gp.GRB.CONTINUOUS, name=flow_status_name(edge, flow), column=None)
                for flow in traffic_pattern
                if not optimize_empty_flows or flow.rate != 0
            }
            for edge in self.edges.values()
        }
        print("compiling inject rate")
        inject_rate: gp.Var = model.addVar(lb=0.0, ub=1.0, obj=0.0, vtype=gp.GRB.CONTINUOUS, name=InjectRateName, column=None)
        print("compiling inject rate constraint")
        inject_rate_constraint: gp.Constr = model.addConstr(inject_rate == initial_inject_rate, name=InjectRateConstraintName)
        print("compiling edge capacity constraints")
        edge_capacity_constraints: dict[Edge, gp.Constr] = {
            edge: model.addConstr(gp.quicksum(flow_status[edge].values()) <= edge.capacity, name=capacity_constraint_name(edge))
            for edge in self.edges.values()
        }
        print("compiling net flow rate constraints")
        net_flow_rate_at_each_node_constraints: dict[Node, dict[Flow, gp.Constr]] = {
            node: {
                flow: model.addConstr(
                    gp.quicksum((
                        edge.net_coefficient_at(node) * flow_status[edge][flow]
                        for edge in directly_connected_edges[node]
                    )) == flow.net_rate_at(node) * inject_rate,
                    name=net_rate_constraint_name(node, flow)
                )
                for flow in traffic_pattern
                if not optimize_empty_flows or flow.rate != 0
            }
            for node in self.nodes.values()
        }
        enabled_edges: dict[Edge, gp.Var] | None = None
        enabled_edges_constraints: dict[Edge, gp.Constr] | None = None
        conflict_edges_constraints: dict[set[Edge], gp.Constr] | None = None
        synchronous_edges_constraints: dict[set[Edge], gp.Var] | None = None
        if len(self.conflict_edges) > 0 or len(self.synchronous_edges) > 0:
            print("compiling reconfigurable constraints")
            enabled_edges: dict[Edge, gp.Var] = {
                edge: model.addVar(lb=0.0, ub=1.0, obj=0.0, vtype=gp.GRB.BINARY, name=enabled_edges_name(edge), column=None)
                for edge in self.edges.values()
            }
            enabled_edges_constraints: dict[Edge, gp.Constr] = {
                edge: model.addConstr(
                    (enabled == 0) >>
                    (gp.quicksum(flow_status[edge].values()) == 0),
                    name=enabled_edges_name(edge))
                for edge, enabled in enabled_edges.items()
            }
            if len(self.conflict_edges) > 0:
                print("compiling conflict edges constraints")
                conflict_edges_constraints: dict[str, gp.Constr] = {
                    conflict_edges_name: model.addConstr(
                        gp.quicksum((
                            enabled_edges[edge]
                            for edge in conflict_edges
                        )) <= 1, name=conflict_edges_constraint_name(conflict_edges_name))
                    for conflict_edges_name, conflict_edges in self.conflict_edges.items()
                }
            if len(self.synchronous_edges) > 0:
                print("compiling synchronous edges constraints")
                synchronous_edges_constraints: dict[str, gp.Constr] = {
                    synchronous_edges_name: model.addConstr(
                        gp.or_(
                            gp.quicksum((
                                enabled_edges[edge]
                                for edge in synchronous_edges
                            )) == 0,
                            gp.quicksum((
                                enabled_edges[edge]
                                for edge in synchronous_edges
                            )) == len(synchronous_edges)
                        ),
                        name=synchronous_edges_constraint_name(synchronous_edges_name))
                    for synchronous_edges_name, synchronous_edges in self.synchronous_edges.items()
                }
        variables = Variables(flow_status, inject_rate, enabled_edges)
        constraints = Constraints(inject_rate_constraint, edge_capacity_constraints, net_flow_rate_at_each_node_constraints, enabled_edges_constraints, conflict_edges_constraints, synchronous_edges_constraints)
        return model, variables, constraints


def flow_status_name(edge: Edge, flow: Flow) -> str:
    return f"rate of {flow} at {edge}"


def enabled_edges_name(edge: Edge) -> str:
    return f"{edge} enabled"


def capacity_constraint_name(edge: Edge) -> str:
    return f"capacity constraint at {edge}"


def net_rate_constraint_name(node: Node, flow: Flow) -> str:
    return f"net rate constraint of {flow} at {node}"


def enabled_edges_constraint_name(edge: Edge) -> str:
    return f"enabled constraint at {edge}"


def conflict_edges_constraint_name(conflict_edges_name: str) -> str:
    return f"conflict edges constraint for {conflict_edges_name}"


def synchronous_edges_constraint_name(synchronous_edges_name: str) -> str:
    return f"synchronous edges constraints for {synchronous_edges_name}"
