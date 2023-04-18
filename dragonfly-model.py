import math
import sys
import typing

import gurobipy as gp

import topology.dragonfly
import topology.network
import util


def step_model(model: gp.Model, inject_rate_constraint: gp.Constr, rate: float) -> typing.Tuple[str, float]:
    print(f"solving start: injection rate: {rate}")
    inject_rate_constraint.setAttr(gp.GRB.Attr.RHS, rate)
    model.update()
    model.optimize()
    status = model.getAttr(gp.GRB.Attr.Status)
    objective = model.getObjective().getValue() / rate if status == gp.GRB.OPTIMAL else math.inf
    print(f"solving end: injection rate: {rate}, status: {util.Status[status]}, objective:{objective}")
    print()
    return util.Status[status], objective


def main():
    parameter_reader = util.parameter_reader(sys.argv)
    next(parameter_reader)
    dataset_name = next(parameter_reader)
    p, a, h, ocs_layer_count, background_layer, fixed_ocs_layer, random_generator, link_capacity, group_count = util.parse_dragonfly_parameter(parameter_reader)
    mip_gap = float(t) if (t := next(parameter_reader)) is not None else 0.0001
    network = topology.dragonfly.dragonfly(p, a, h, link_capacity, ocs_layer_count=ocs_layer_count,
                                           background_layer=background_layer, fixed_ocs_layers=fixed_ocs_layer,
                                           random_generator=random_generator)
    traffic_pattern = util.load_dragonfly_dataset(dataset_name, network, group_count, p, a, link_capacity, random_generator)
    total_traffic = sum(flow.rate for flow in traffic_pattern)
    print("compiling network model")
    model, variables, constraints = network.compile(traffic_pattern)
    model.setParam(gp.GRB.Param.MIPGap, mip_gap)
    model.setObjective(
        gp.quicksum((
            flow_rate
            for flow_rates_at_edge in variables.flow_status.values()
            for flow_rate in flow_rates_at_edge.values()
        )) / total_traffic,
        gp.GRB.MINIMIZE)
    inject_rate_constraint = constraints.inject_rate_constraint
    start = 0.0
    stop = 1.0
    precision = 0.01
    print("begin model solving")
    status_history, objective_history = util.solve_models_by_step(start, stop, precision, lambda rate: step_model(model, inject_rate_constraint, rate))
    print(status_history)
    print(objective_history)


if __name__ == '__main__':
    main()
