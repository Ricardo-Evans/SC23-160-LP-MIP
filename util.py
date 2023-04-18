import os
import random
import typing

import gurobipy as gp
import numpy as np

import topology.dragonfly
import topology.network

ParameterReader = typing.Generator[str, None, None]
DragonflyParameters = typing.Tuple[int, int, int, int, bool, bool, random.Random, float, int]
ModelStep = typing.Callable[[float], tuple[str | typing.Iterable[str], float | typing.Iterable[float]]]
ModelHistory = typing.Tuple[typing.List[str | typing.Iterable[str]], typing.List[float | typing.Iterable[float]]]

Status = {
    gp.GRB.LOADED: "loaded",
    gp.GRB.OPTIMAL: "optimal",
    gp.GRB.INFEASIBLE: "infeasible",
    gp.GRB.INF_OR_UNBD: "infeasible/unbounded",
    gp.GRB.UNBOUNDED: "unbounded",
    gp.GRB.CUTOFF: "cutoff",
    gp.GRB.ITERATION_LIMIT: "iteration limit",
    gp.GRB.NODE_LIMIT: "node limit",
    gp.GRB.TIME_LIMIT: "time limit",
    gp.GRB.SOLUTION_LIMIT: "solution limit",
    gp.GRB.INTERRUPTED: "interrupted",
    gp.GRB.NUMERIC: "numeric",
    gp.GRB.SUBOPTIMAL: "suboptimal",
    gp.GRB.INPROGRESS: "in progress",
    gp.GRB.USER_OBJ_LIMIT: "user objective limit",
}


def parameter_reader(arguments: list[str]) -> ParameterReader:
    i = 0
    while True:
        if i < len(arguments):
            yield arguments[i]
            i += 1
        else:
            yield None


def parse_dragonfly_parameter(reader: ParameterReader) -> DragonflyParameters:
    p = int(next(reader))
    a = int(next(reader))
    h = int(next(reader))
    ocs_layer_count = int(t) if (t := next(reader)) is not None else 0
    background_layer = t.lower() == 'true' if (t := next(reader)) is not None else True
    fixed_ocs_layer = t.lower() == 'true' if (t := next(reader)) is not None else False
    random_seed = int(t) if (t := next(reader)) is not None else 0
    random_generator = random.Random(random_seed)
    link_capacity = 100.0
    group_count = a * h + 1
    return p, a, h, ocs_layer_count, background_layer, fixed_ocs_layer, random_generator, link_capacity, group_count


def load_dragonfly_dataset(dataset_name: str, network: topology.network.Network, group_count: int, p: int, a: int, link_capacity: float, random_generator: random.Random = None) -> topology.network.TrafficPattern:
    if os.path.isfile(dataset_name):
        traffic = np.loadtxt(dataset_name)
        traffic_pattern = topology.dragonfly.convert_traffic_matrix(traffic, network, group_count, p, a, link_capacity)
    else:
        match dataset_name:
            case "group-neighbor":
                traffic_pattern = topology.dragonfly.group_neighbor_traffic(network, group_count, p, a, link_capacity)
            case "nearest-neighbor":
                traffic_pattern = topology.dragonfly.nearest_neighbor_traffic(network, group_count, p, a, link_capacity)
            case "random-group-to-group":
                traffic_pattern = topology.dragonfly.random_group_to_group_traffic(network, group_count, p, a, link_capacity, random_generator)
            case "random-node-to-node":
                traffic_pattern = topology.dragonfly.random_node_to_node_traffic(network, group_count, p, a, link_capacity, random_generator)
            case "all-to-all":
                traffic_pattern = topology.dragonfly.all_to_all_traffic(network, group_count, p, a, link_capacity)
            case "adversarial":
                traffic_pattern = topology.dragonfly.adversarial_traffic(network, group_count, p, a, link_capacity)
            case _:
                raise ValueError("the traffic pattern is not a valid file or a known classic pattern")
    return traffic_pattern


def solve_models_by_step(start: float, stop: float, precision: float, model: ModelStep) -> ModelHistory:
    status_history = []
    objective_history = []
    for step in np.linspace(start + precision, stop, round((stop - start) / precision)):
        status, objective = model(step)
        status_history.append(status)
        objective_history.append(objective)
    return status_history, objective_history
