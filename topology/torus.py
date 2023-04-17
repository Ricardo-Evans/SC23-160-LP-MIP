import topology.network
import numpy as np


def node_name(*args: int) -> str:
    return ",".join(map(str, args))


def edge_name(dimension: int, start: topology.network.Node, end: topology.network.Node) -> str:
    return f"link on dimension {dimension}, from {start} to {end}"


def torus_recursive(degree: int, dimension: int, capacity: float, network: topology.network.Network, node_map: dict[topology.network.Node, np.ndarray], *args: int) -> None:
    if dimension < 0:
        raise ValueError("negative dimension not allowed")
    if dimension == 0:
        node = network.insert_node(node_name(*args))
        node_map[node] = np.asarray(args)
        return
    for i in range(degree):
        torus_recursive(degree, dimension - 1, capacity, network, node_map, *args, i)
    for node in network.nodes.values():
        coordinator = node_map[node]
        left_coordinator = np.copy(coordinator)
        left_coordinator[-dimension] = (left_coordinator[-dimension] + degree - 1) % degree
        right_coordinator = np.copy(coordinator)
        right_coordinator[-dimension] = (right_coordinator[-dimension] + 1) % degree
        node_left = network.find_node(node_name(*left_coordinator))
        node_right = network.find_node(node_name(*right_coordinator))
        network.insert_edge(edge_name(dimension, node, node_left), node, node_left, capacity)
        network.insert_edge(edge_name(dimension, node, node_right), node, node_right, capacity)


def torus(degree: int, dimension: int, capacity: float) -> topology.network.Network:
    network = topology.network.Network()
    torus_recursive(degree, dimension, capacity, network, {})
    assert network.node_count() == degree ** dimension
    assert network.edge_count() == degree ** dimension * 2 * dimension
    return network


def uniform_traffic(network: topology.network.Network, capacity: float) -> topology.network.TrafficPattern:
    traffic_pattern = set()
    for i in network.nodes.values():
        for j in network.nodes.values():
            if i == j:
                continue
            traffic_pattern.add(topology.network.Flow(i, j, capacity))
    return traffic_pattern
