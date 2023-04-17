import random

import deprecated
import numpy as np

import topology.network


def tor_uplink(node: topology.network.Node) -> str:
    return f"TOR uplink, {node}"


def tor_downlink(node: topology.network.Node) -> str:
    return f"TOR downlink, {node}"


def inner_group_link(group_id: int, start: topology.network.Node, end: topology.network.Node) -> str:
    return f"inner link of group {group_id}, start {start}, end {end}"


def inter_group_link(start_group_id: int, end_group_id: int) -> str:
    return f"inter group link from {start_group_id} to {end_group_id}"


def switch_name(group_id: int, switch_id: int) -> str:
    return f"group {group_id}, switch {switch_id}"


def node_name(switch: topology.network.Node, node_id: int) -> str:
    return f"{switch}, node {node_id}"


def ocs_link(ocs_layer: int, start: topology.network.Node, end: topology.network.Node) -> str:
    return f"ocs link on layer {ocs_layer}, start {start}, end {end}"


def fixed_ocs_link(ocs_layer: int, start: topology.network.Node, end: topology.network.Node) -> str:
    return f"fixed ocs link on layer {ocs_layer}, start {start}, end {end}"


def conflict_links_name(ocs_layer: int, group_index: int) -> str:
    return f"conflict ocs links for group {group_index} on layer {ocs_layer}"


def dragonfly(p: int, a: int, h: int, link_capacity: float, ocs_layer_count: int = 0, background_layer: bool = True, fixed_ocs_layers: bool = False, random_generator: random.Random = None) -> topology.network.Network:
    group_count = a * h + 1
    network = topology.network.Network()
    groups = []
    for group_id in range(0, group_count):
        group = []
        for switch_id in range(0, a):
            switch = network.insert_node(switch_name(group_id, switch_id))
            for node_id in range(0, p):
                node = network.insert_node(node_name(switch, node_id))
                network.insert_edge(tor_uplink(node), switch, node, link_capacity)
                network.insert_edge(tor_downlink(node), node, switch, link_capacity)
            group.append(switch)
        for x in group:
            for y in group:
                if x == y:
                    continue
                network.insert_edge(inner_group_link(group_id, x, y), x, y, link_capacity)
        groups.append(group)
    if background_layer:
        for group_id, group in enumerate(groups):
            for target_id, target in enumerate(groups):
                if group_id == target_id:
                    continue
                current_switch = group[(group_id + group_count - target_id - 1) % group_count // h]
                target_switch = target[(target_id + group_count - group_id - 1) % group_count // h]
                network.insert_edge(inter_group_link(group_id, target_id), current_switch, target_switch, link_capacity)
    for layer in range(ocs_layer_count):
        for group in range(group_count):
            conflict_edges = []
            for target_group in range(group_count):
                if group == target_group:
                    continue
                switch = network.find_node(switch_name(group, layer % a))
                target_switch = network.find_node(switch_name(target_group, layer % a))
                conflict_edges.append((switch, target_switch))
            if fixed_ocs_layers:
                if random_generator is None:
                    random_generator = random.Random()
                switch, target_switch = random_generator.choice(conflict_edges)
                network.insert_edge(ocs_link(layer, switch, target_switch), switch, target_switch, link_capacity)
            else:
                network.define_conflict_edges(conflict_links_name(layer, group), *[network.insert_edge(ocs_link(layer, s, t), s, t, link_capacity) for (s, t) in conflict_edges])
    return network


def group_neighbor_traffic(network: topology.network.Network, group_count: int, p: int, a: int, link_capacity: float) -> topology.network.TrafficPattern:
    """
    group neighbor traffic, each node send to the node of the same position in the next group
    :param network:
    :param group_count:
    :param p:
    :param a:
    :param link_capacity:
    :return:
    """
    traffic_pattern = set()
    for group_id in range(group_count):
        target_group_id = (group_id + 1) % group_count
        for switch_id in range(a):
            switch = network.find_node(topology.dragonfly.switch_name(group_id, switch_id))
            target_switch = network.find_node(topology.dragonfly.switch_name(target_group_id, switch_id))
            for node_id in range(p):
                node = network.find_node(topology.dragonfly.node_name(switch, node_id))
                target_node = network.find_node(topology.dragonfly.node_name(target_switch, node_id))
                traffic_pattern.add(topology.network.Flow(node, target_node, link_capacity))
    return traffic_pattern


def nearest_neighbor_traffic(network: topology.network.Network, group_count: int, p: int, a: int, link_capacity: float) -> topology.network.TrafficPattern:
    """
    nearest neighbor traffic, each node send to the next node, whether the same switch, whether in the same group
    :param network:
    :param group_count:
    :param p:
    :param a:
    :param link_capacity:
    :return:
    """
    traffic_pattern = set()
    for group_id in range(group_count):
        next_group_id = (group_id + 1) % group_count
        for switch_id in range(a):
            switch = network.find_node(topology.dragonfly.switch_name(group_id, switch_id))
            next_switch_id = (switch_id + 1) % a
            if next_switch_id <= switch_id:
                next_switch = network.find_node(topology.dragonfly.switch_name(next_group_id, next_switch_id))
            else:
                next_switch = network.find_node(topology.dragonfly.switch_name(group_id, next_switch_id))
            for node_id in range(p):
                node = network.find_node(topology.dragonfly.node_name(switch, node_id))
                next_node_id = (node_id + 1) % p
                if next_node_id <= node_id:
                    next_node = network.find_node(topology.dragonfly.node_name(next_switch, next_node_id))
                else:
                    next_node = network.find_node(topology.dragonfly.node_name(switch, next_node_id))
                traffic_pattern.add(topology.network.Flow(node, next_node, link_capacity))
    return traffic_pattern


def all_to_all_traffic(network: topology.network.Network, group_count: int, p: int, a: int, link_capacity: float) -> topology.network.TrafficPattern:
    """
    all to all traffic, each node send to every node except the nodes in the same group
    :param network:
    :param group_count:
    :param p:
    :param a:
    :param link_capacity:
    :return:
    """
    traffic_pattern = set()
    for group_id in range(group_count):
        for switch_id in range(a):
            switch = network.find_node(switch_name(group_id, switch_id))
            for node_id in range(p):
                node = network.find_node(node_name(switch, node_id))
                for target_group_id in range(group_count):
                    if group_id == target_group_id:
                        continue
                    for target_switch_id in range(a):
                        target_switch = network.find_node(switch_name(target_group_id, target_switch_id))
                        for target_node_id in range(p):
                            target_node = network.find_node(node_name(target_switch, target_node_id))
                            traffic_pattern.add(topology.network.Flow(node, target_node, link_capacity / ((group_count - 1) * p * a)))
    return traffic_pattern


def adversarial_traffic(network: topology.network.Network, group_count: int, p: int, a: int, link_capacity: float) -> topology.network.TrafficPattern:
    """
    adversarial traffic, every two groups are paired, every node send to the node of the same position in the paired group
    :param network:
    :param group_count:
    :param p:
    :param a:
    :param link_capacity:
    :return:
    """
    traffic_pattern = set()
    for group_id in range(0, group_count, 2):
        opposite_group_id = group_id + 1
        if opposite_group_id >= group_count:
            continue
        for switch_id in range(a):
            switch = network.find_node(topology.dragonfly.switch_name(group_id, switch_id))
            opposite_switch = network.find_node(topology.dragonfly.switch_name(opposite_group_id, switch_id))
            for node_id in range(p):
                node = network.find_node(topology.dragonfly.node_name(switch, node_id))
                opposite_node = network.find_node(topology.dragonfly.node_name(opposite_switch, node_id))
                traffic_pattern.add(topology.network.Flow(node, opposite_node, link_capacity))
                traffic_pattern.add(topology.network.Flow(opposite_node, node, link_capacity))
    return traffic_pattern


def adversarial_traffic_remaining_all_to_all(network: topology.network.Network, group_count: int, p: int, a: int, link_capacity: float) -> topology.network.TrafficPattern:
    """
    same to adversarial traffic, but the possible remaining group do an all-to-all inner group traffic
    :param network:
    :param group_count:
    :param p:
    :param a:
    :param link_capacity:
    :return:
    """
    traffic_pattern = adversarial_traffic(network, group_count, p, a, link_capacity)
    node_count_per_group = p * a
    if group_count % 2 != 0:
        group_id = group_count - 1
        for switch_id_i in range(a):
            for node_id_i in range(p):
                for switch_id_j in range(a):
                    for node_id_j in range(p):
                        if switch_id_i == switch_id_j and node_id_i == node_id_j:
                            continue
                        switch_i = network.find_node(topology.dragonfly.switch_name(group_id, switch_id_i))
                        switch_j = network.find_node(topology.dragonfly.switch_name(group_id, switch_id_j))
                        node_i = network.find_node(topology.dragonfly.node_name(switch_i, node_id_i))
                        node_j = network.find_node(topology.dragonfly.node_name(switch_j, node_id_j))
                        traffic_pattern.add(topology.network.Flow(node_i, node_j, link_capacity / (node_count_per_group - 1)))
    return traffic_pattern


def random_group_to_group_traffic(network: topology.network.Network, group_count: int, p: int, a: int, link_capacity: float, random_generator: random.Random = None) -> topology.network.TrafficPattern:
    traffic_pattern = set()
    income_flow_count = {}
    outcome_flow_count = {}
    pairs = set()
    if random_generator is None:
        random_generator = random.Random()
    for group_id in range(group_count):
        while True:
            target_group_id = random_generator.randrange(group_count)
            if target_group_id != group_id:
                break
        if group_id not in outcome_flow_count:
            outcome_flow_count[group_id] = 0
        if target_group_id not in income_flow_count:
            income_flow_count[target_group_id] = 0
        outcome_flow_count[group_id] += 1
        income_flow_count[target_group_id] += 1
        pairs.add((group_id, target_group_id))
    for group_id, target_group_id in pairs:
        for switch_id in range(a):
            switch = network.find_node(topology.dragonfly.switch_name(group_id, switch_id))
            target_switch = network.find_node(topology.dragonfly.switch_name(target_group_id, switch_id))
            for node_id in range(p):
                node = network.find_node(topology.dragonfly.node_name(switch, node_id))
                target_node = network.find_node(topology.dragonfly.node_name(target_switch, node_id))
                traffic_pattern.add(topology.network.Flow(node, target_node, link_capacity / max(income_flow_count[target_group_id], outcome_flow_count[group_id])))
    return traffic_pattern


def random_node_to_node_traffic(network: topology.network.Network, group_count: int, p: int, a: int, link_capacity: float, random_generator: random.Random = None) -> topology.network.TrafficPattern:
    node_count = group_count * p * a
    traffic_matrix = np.zeros((node_count, node_count))
    income_flow_count = {}
    outcome_flow_count = {}
    pairs = set()
    for i in range(node_count):
        while True:
            j = random_generator.randrange(0, node_count)
            if i != j:
                break
        if i not in outcome_flow_count:
            outcome_flow_count[i] = 0
        if j not in income_flow_count:
            income_flow_count[j] = 0
        outcome_flow_count[i] += 1
        income_flow_count[j] += 1
        pairs.add((i, j))
    for (i, j) in pairs:
        traffic_matrix[i, j] = 1 / max(income_flow_count[j], outcome_flow_count[i])
    return convert_traffic_matrix(traffic_matrix, network, group_count, p, a, link_capacity)


@deprecated.deprecated("wrong traffic, needs correction")
def bit_complementary_traffic(network: topology.network.Network, group_count: int, p: int, a: int, link_capacity: float) -> topology.network.TrafficPattern:
    node_count = group_count * p * a
    traffic = np.zeros((node_count, node_count))
    for i in range(node_count):
        j = (~i) & (node_count - 1)
        if i == j:
            continue
        traffic[i, j] = 1
    return convert_traffic_matrix(traffic, network, group_count, p, a, link_capacity)


def convert_traffic_matrix(traffic: np.ndarray, network: topology.network.Network, group_count: int, p: int, a: int, link_capacity: float) -> topology.network.TrafficPattern:
    assert traffic.ndim == 2
    node_map = {}
    traffic_pattern = set()
    for group_id in range(group_count):
        for switch_id in range(a):
            switch = network.find_node(topology.dragonfly.switch_name(group_id, switch_id))
            for node_id in range(p):
                node = network.find_node(topology.dragonfly.node_name(switch, node_id))
                node_map[len(node_map)] = node
    node_count = len(node_map)
    assert traffic.shape[0] <= node_count and traffic.shape[1] <= node_count
    traffic = np.pad(traffic, ((0, node_count - traffic.shape[0]), (0, node_count - traffic.shape[0])))
    traffic *= link_capacity
    for i in range(traffic.shape[0]):
        for j in range(traffic.shape[1]):
            if traffic[i, j] == 0:
                continue
            traffic_pattern.add(topology.network.Flow(node_map[i], node_map[j], traffic[i, j]))
    return traffic_pattern
