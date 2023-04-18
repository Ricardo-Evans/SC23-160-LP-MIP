# SC-2023-MUSE-solver
It should be noticed that we evaluate static Dragonfly with adaptive routing and "Thoughtful MUSE" by using the solver, and the other version of MUSE, i.e., "Quick-minded MUSE" is evaluated in the simulator that is introduced in another repository <https://github.com/Lee-Zijian/SC-2023-MUSE-simulator>.

## Dependency

* gurobi 10 (Requires a valid license)
* numpy
* deprecated
* scipy

All the dependencies are installed in the conda environment SC23-160. But you may need to install your gurobi license. You may install your license according to the documentation of gurobi.

## Usage

```bash
python dragonfly-model.py dataset p a h [ocs_layer_count=0] [background_layer=True] [fixed_ocs_layer=False] [random_seed=0] [mip_gap=0.0001]
```

The dataset parameter can be either a dataset file (normalized traffic matrix, see examples in datasets folder) or a name in the following list:

* group-neighbor
* nearest-neighbor
* random-group-to-group
* random-node-to-node
* all-to-all
* adversarial

The p, a, h parameters are integer parameters of the dragonfly topology.

The ocs_layer_count parameter determines the count of OCS layers.

The background_layer means whether the static dragonfly layer is enabled.

The fixed_ocs_layer is used only for test purpose. If enabled, all the OCS layers will be fixed to a random static state.

The random_seed is used to generate random numbers. Used in random traffics, random topologies, etc.

The mip_gap is used by the MIP solver, when the relative difference between the objective of a valid solution (may not be optimal) and a proved upper bound is within the parameter, the solution is considered as an optimal solution. The smaller value brings better accuracy while the larger value brings faster solving speed.
