# Flow Scheduling in Time-Sensitive Networks Under Weakly-Hard Constraints.

This repository contains the source code and the raw data files to test and reproduce the submission to IEEE TON paper.

## Table of Contents

- [Objective of the Paper](#objective-of-the-paper)
- [Scheduling Algorithms](#scheduling-algorithms)
- [Repository](#repository)
- [Environment Setup](#environment-setup)
- [Optimizer Setup](#optimizer-setup)
- [Sample Runs of the Experiments](#sample-runs-of-the-experiments)
- [Reproducing the Results](#reproducing-the-results)
  - [Experiment 1: Comparing Lazy Search with ILP](#experiment-1-comparing-lazy-search-with-ilp)
  - [Experiment 2: Stress Test](#experiment-2-stress-test)
  - [Experiment 3: Impact of Weight on Optional Packets](#experiment-3-impact-of-weight-on-optional-packets)
  - [Experiment 4: Evaluating Dedicated Queue Reservation for Optional Flows](#experiment-4-evaluating-dedicated-queue-reservation-for-optional-flows)
  - [Experiment 5: Studying Weakly-Hard Requirements](#experiment-5-studying-weakly-hard-requirements)
  - [Hardware Experiment](#hardware-experiment)
- [Run All Experiments](#run-all-experiments)
  - [Experiment 1](#experiment-1)
  - [Experiment 2](#experiment-2)
  - [Experiment 3](#experiment-3)
  - [Experiment 4](#experiment-4)
  - [Experiment 5](#experiment-5)
  - [Note: Running Criterion A Instead of Criterion B](#note-running-criterion-a-instead-of-criterion-b)
- [Notes](#notes)

## Objective of the Paper
This paper addresses the challenge of scheduling traffic in Time-Sensitive Networking (TSN) systems where flows can tolerate a bounded number of deadline misses. Instead of enforcing strict hard real-time guarantees for every packet, we incorporate "weakly-hard" timing constraints which allow controlled deadline violations while maintaining system stability. The goal is to synthesize efficient Gate Control Lists (GCLs) for the IEEE 802.1Qbv Time-Aware Shaper by ensuring all mandatory packets meet their deadlines while maximizing how many optional packets can be successfully transmitted.

Two ordering criteria are studied throughout the artifact:

- **Criterion A** — optional packets follow a *critical* (fixed, worst-case-first) sequence within their weakly-hard window.
- **Criterion B** — optional packets may be scheduled in an *arbitrary* sequence within their weakly-hard window, chosen by a queue-mapping optimizer (Stage 1) before GCL synthesis (Stage 2).

## Scheduling Algorithms
We developed two algorithms to synthesize Gate Control Lists (GCLs): (a) Lazy Search and (b) an ILP-based approach. In both methods, packets are classified as mandatory or optional. Mandatory packets must always meet their deadlines to ensure system correctness, whereas optional packets are transmitted only when sufficient resources are available. The Lazy Search algorithm is scalable and but inefficient in resource utilization, leading to lower admission of optional packets. In contrast, the ILP-based approach jointly optimizes scheduling and resource allocation, resulting in higher admissibility of optional packets.



## Environment Setup
The experiments require Python 3.13 with `pandas`, `numpy`, `matplotlib`, `seaborn`, and `gurobipy`. We recommend using a [conda](https://www.anaconda.com/download/success) environment. The commands below are shown only to illustrate the intended setup — you do not need to create this environment or install anything to browse or read this repository.

```bash
conda create -n ae_79 python=3.13 -y
conda activate ae_79
pip install pandas numpy matplotlib seaborn gurobipy
```

## Optimizer Setup
We have formulated an ILP-based Gate Control Lists (GCLs) extraction method to optimize the admissibility of the optional packets. For the optimization module, we are using **Gurobi** for solving the ILP model. Gurobi license is necessary to run the ILP formulation.

#### Note: Without installing a license, you can still run the experiments under a certain number of constraints. We have provided sample inputs to run individual experiments which can be run without any license. See [Sample Runs of the Experiments](#sample-runs-of-the-experiments).

Gurobi license can be installed from the reference of [set up a Gurobi license](https://support.gurobi.com/hc/en-us/articles/12872879801105-How-do-I-retrieve-and-set-up-a-Gurobi-license). If you are an academic user, you can install the license from [here](https://support.gurobi.com/hc/en-us/articles/4534601245713-How-do-I-get-started-with-Gurobi-for-academic-users). Make sure the license is installed inside the python environment.


## Sample Runs of the Experiments

The folder `Sample_run` contains examples of each experiment for a single input file, and it is possible to run without any **license**. We can run `Experiment_1` (ILP, Lazy Search, and the Criterion B queue-mapping stage), `Experiment_4`, and `Experiment_5` in this way. Feel free to test them, if you intend to run the codes. Each experiment is self-contained in its own directory. Navigate into the experiment folder and run `main.py` (or `main_mapper.py`) from there. Results are saved as `.csv` files in the corresponding `Results/` directory.

#### Experiment 1 — ILP

```bash
cd path/to/TSN_Overload/Extension/Sample_run/Experiment_1_ILP/
python main.py input_csvs/sample_1.csv
```
Output: `Experiment_1_ILP/Results/`


#### Experiment 1 — Lazy Search

```bash
cd path/to/TSN_Overload/Extension/Sample_run/Experiment_1_Lazy_Search/
python main.py input_csvs/sample_1.csv
```
Output: `Experiment_1_Lazy_Search/Results/`


#### Experiment 1 — Criterion B Queue Mapper (Stage 1)

Criterion B first runs a queue-local mapping optimizer before GCL synthesis. This sample runs that stage in isolation:

```bash
cd path/to/TSN_Overload/Extension/Sample_run/Experiment_1_Mapper/
python main_mapper.py input_csvs/sample_1.csv
```
Output: `Experiment_1_Mapper/Results/`


#### Experiment 4 — No Reserved Queue

```bash
cd path/to/TSN_Overload/Extension/Sample_run/Experiment_4_No_Reserved_Queue/
python main.py input_csvs/sample_1.csv
```
Output: `Experiment_4_No_Reserved_Queue/Results/`


#### Experiment 5 — Hard Deadline

```bash
cd path/to/TSN_Overload/Extension/Sample_run/Experiment_5_Hard_deadline/
python main.py input_csvs/sample_1.csv
```
Output: `Experiment_5_Hard_deadline/Results/`




## Reproducing the Results

We conducted five sets of experiments (Experiment 1–5). In all experiments, the total switch utilization is varied from **0.4 to 1.2** (i.e., [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]). For each utilization level, we generated 100 random input instances.

Running all experiments from scratch may take a significant amount of time. For example, when the number of flows is **48** and the utilization is **0.8**, solving a single instance may require **30–60 minutes** using the optimizer. Therefore, for convenience and reproducibility, we provide all raw output files in each experiment's `Results` directory. These files can be directly used to regenerate all figures and tables reported in the paper via `run_experiments.py`.


### Experiment 1: Comparing Lazy Search with ILP

In this experiment, we compare the schedulability ratio and optional packet admissibility ratio between the ILP-based and Lazy Search algorithms, for both Criterion A and Criterion B. The number of flows is varied as 16, 32, and 48.

To reproduce the results corresponding to the schedulability-ratio and optional-packet-admissibility figures, run:

```bash
cd path/to/TSN_Overload/Extension/
python run_experiments.py exp1
```

The generated figures will be saved in:

```
Figures/Experiment_1/
```

### Experiment 2: Stress Test

This experiment presents the runtime behavior of the proposed ILP-based approach under different numbers of constraints. It highlights how the computation time grows as the scheduling problem becomes more complex, for both the queue-mapping stage and the GCL-synthesis stage.

To generate the results corresponding to Fig. 9 and Table I, run the following commands:

```bash
cd path/to/TSN_Overload/Extension/
python run_experiments.py exp2
```

After execution, the figure and table will be available in:

```
Figures/Experiment_2/
```

### Experiment 3: Impact of Weight on Optional Packets

This experiment studies how packet weights influence the admission of optional packets, for both Criterion A and Criterion B. We consider a scenario with 48 flows at a total utilization of 1.0, using different weakly-hard parameters. Specifically, 50% of the flows are configured with a group size of 2 and the remaining 50% with a group size of 3.

We evaluate three weight configurations:

* Configuration 1: All flows are assigned equal weights.
* Configuration 2: Flows with the group-size-3 weakly-hard constraint are given a higher weight (100), while flows with the group-size-2 constraint have a lower weight (1).
* Configuration 3: The weight assignments in Configuration 2 are reversed.

To regenerate Table III of the paper, execute:

```bash
cd path/to/TSN_Overload/Extension/
python run_experiments.py exp3
```

The generated results will be stored in:

```
Figures/Experiment_3/
```

### Experiment 4: Evaluating Dedicated Queue Reservation for Optional Flows

This experiment evaluates the benefit of reserving dedicated queues for optional flows. We compare the proposed ILP-based approach with a baseline configuration where all flows are allowed to use all 8 queues, and the scheduling objective is to minimize response time. This experiment does not have a Criterion A / Criterion B split — it compares reserved-queue (`ILP`) vs. no-reserved-queue (`ILP_Hard`) only.

We analyze the impact of these strategies by comparing the percentage of successfully scheduled mandatory and optional packets.

To reproduce the results, execute:

```bash
cd path/to/TSN_Overload/Extension/
python run_experiments.py exp4
```

The generated outputs will be available in:

```
Figures/Experiment_4/Extension/
```

### Experiment 5: Studying Weakly-Hard Requirements

This experiment investigates the impact of different weakly-hard constraints on system schedulability, for both Criterion A and Criterion B. We evaluate multiple weakly-hard configurations — group sizes of 2 and 3, in both orderings — and compare them with the hard real-time case, where no deadline violations are allowed. The results highlight the schedulability improvement achieved by relaxing strict real-time requirements.

To reproduce the results, run:

```bash
cd path/to/TSN_Overload/Extension/
python run_experiments.py exp5
```

The generated outputs will be stored in:

```
Figures/Experiment_5/
```

### Hardware Experiment

We validated our ILP-based scheduling algorithm on the [InnoRoute Real-Time HAT](https://innoroute.com/realtimehat/) to demonstrate feasibility and effectiveness in a real hardware environment. We have two following scenarios: (i) Proposed ILP with reserved queue for optional packets (both Lazy Search and ILP), and (ii) Response-time minimization without queue reservation (all flows across 8 queues). Configure the TSN switch egress port as all gate open (follow the documentation of [InnoRoute Real-Time HAT](https://innoroute.com/realtimehat/)). Take a set of flows and run both optimization models to get the start time of each packet. Use their start time (gate open time) and generate VLAN-tagged UDP packets with precise timestamps (start time of packets). We send the packets through the switch using `tcpreplay`. The availability of the hardware and setting it up are time consuming, and because of that, we provided the raw outputs as `.csv` files to generate Fig. 13(a)-(c). Execute the following command from the repository root to generate the figure:

```bash
cd path/to/TSN_Overload/Extension/
python run_experiments.py hardware
```

Output: `Figures/Hardware_Exps/`




## Run All Experiments
> **Note:** Running these experiments from scratch may take several hours to days for each data point depending on the hardware configuration, and **the optimizer results can vary as well**. Most of our experiments were run on a high-performance computer, except Experiment 2 (which was run on a regular device to measure realistic runtime).

First, remove all the result directories:
**Linux**
```bash
find . -type d -name "Results" -exec rm -rf {} +
```
**Windows** using Command Prompt
```bash
for /d /r . %d in (Results) do @if exist "%d" rmdir /s /q "%d"
```

All examples below use **Criterion B** paths. See the [note at the end of this section](#note-running-criterion-a-instead-of-criterion-b) for how to run the equivalent Criterion A configuration.

### Experiment 1

This section explains how to run the ILP-based and Lazy Search (heuristic) algorithms for Criterion B, using the provided input files. Each experiment is executed using a `.csv` file that defines the flow configuration. Criterion B additionally runs a queue-mapping optimizer (Stage 1) before GCL synthesis (Stage 2) — this is handled automatically inside `main.py` for `criterion-B-ILP` / `criterion-B-Lazy`.

#### ILP-Based Method

To execute the ILP solver for a single input instance, run:

```bash
cd path/to/TSN_Overload/Extension/Experiment_1/criterion-B-ILP/
python main.py flows_48/flows_48_u_0.8/input_csvs/flows_48_u_0.8_7q_run_01.csv
```
Output: `flows_48/flows_48_u_0.8/Results/`

For example, to evaluate a case with 32 flows and utilization = 1.0, use:

```bash
python main.py flows_32/flows_32_u_1.0/input_csvs/flows_32_u_1.0_7q_run_01.csv
```

Similarly, you can test other flow sizes and utilization levels by selecting the corresponding input file.

There is also a `criterion-B-random-ILP` variant (random rather than arbitrary-but-optimized packet ordering), which follows the exact same command pattern under `Experiment_1/criterion-B-random-ILP/`.


#### Lazy Search (Heuristic)

To run the heuristic method for a single input instance:

```bash
cd path/to/TSN_Overload/Extension/Experiment_1/criterion-B-Lazy/
python main.py flows_48/flows_48_u_0.8/input_csvs/flows_48_u_0.8_7q_run_01.csv
```
Output: `flows_48/flows_48_u_0.8/Results/`

A `criterion-B-random-Lazy` variant is available the same way under `Experiment_1/criterion-B-random-Lazy/`.


#### Running All Input Instances

To process all `.csv` files within a directory at once, omit the filename argument and provide the folder instead. For example:

```bash
python main.py flows_48/flows_48_u_0.8/input_csvs
```

This will automatically execute the algorithm for every input instance in the selected directory, and the outputs will be saved in the corresponding output directory. Some utilization folders (e.g. `u_0.8`, `u_1.2`) save results under a lowercase `results/` directory instead of `Results/` — check both when locating output for a given run.


### Experiment 2

For details about the setup, please refer to [Experiment 2: Stress Test](#experiment-2-stress-test). In this experiment, the number of packets is varied as 201, 252, 306, 351, 402, 450, and 501. There are two stages, each in its own folder: `GCL-optimizer` (Stage 2, GCL synthesis) and `mapper` (Stage 1, queue mapping).

To execute the GCL-synthesis stage for a specific number of packets, run:

```bash
cd path/to/TSN_Overload/Extension/Experiment_2/GCL-optimizer/
python main.py input_csvs/flows_48_u_0.8_p201/flows_48_u_0.8_p201_run_01.csv
```

The generated output will be stored in:

```
Results/flows_48_u_0.8_p201/
```

To execute the queue-mapping stage for the same packet count, run:

```bash
cd path/to/TSN_Overload/Extension/Experiment_2/mapper/
python main_mapper.py input_csvs/flows_48_u_0.8_p201
```

The generated output will be stored in:

```
Results/flows_48_u_0.8_p201/
```

To evaluate other cases (e.g., 252, 306, 351, 402, 450, and 501), replace `p201` with `p{number_of_packets}` in either command. If you want to run all instances at once for a given packet count, omit the filename and pass the folder instead, e.g. `python main.py input_csvs/flows_48_u_0.8_p252`.

### Experiment 3

This experiment is conducted under three different configurations, for both Criterion A and Criterion B. For details about the setup, please refer to [Experiment 3: Impact of Weight on Optional Packets](#experiment-3-impact-of-weight-on-optional-packets).

#### Configuration 1 (No weight)

```bash
cd path/to/TSN_Overload/Extension/Experiment_3/criterion-B/No_weight
python main.py input_csvs/flows_48_u_1.0_7q_run_01.csv
```
Output: `Results/`

#### Configuration 2 (group size 3, weighted)

```bash
cd path/to/TSN_Overload/Extension/Experiment_3/criterion-B/m_1_k_3_100
python main.py input_csvs/flows_48_u_1.0_7q_run_01.csv
```
Output: `Results/`

#### Configuration 3 (group size 2, weighted)

```bash
cd path/to/TSN_Overload/Extension/Experiment_3/criterion-B/m_1_k_2_100
python main.py input_csvs/flows_48_u_1.0_7q_run_01.csv
```
Output: `Results/`

To process all input instances in a directory, remove the file name and provide only the folder path:

```bash
python main.py input_csvs
```

### Experiment 4

This section describes how to run the ILP-based approaches used to evaluate the impact of dedicated queue reservation. This experiment has no Criterion A / Criterion B split.

To run the model with reserved queues, execute:

```bash
cd path/to/TSN_Overload/Extension/Experiment_4/ILP
python main.py input_csvs/flows_48_u_1.0/flows_48_u_1.0_7q_run_01.csv
```

The generated output will be stored in:

```
Results/flows_48_u_1.0/
```

To run the model without any reserved queue, execute:

```bash
cd path/to/TSN_Overload/Extension/Experiment_4/ILP_Hard
python main.py input_csvs/flows_48_u_1.0_8queues/flows_48_u_1.0_8q_run_01.csv
```

The output will be saved in:

```
Results/flows_48_u_1.0/
```

To process all input instances in a directory, remove the file name and provide only the folder path. For example:

```bash
python main.py input_csvs/flows_48_u_1.0_8queues/
```

This will execute the model for every input instance in the selected directory and store the results in the corresponding output folder.

### Experiment 5

In this experiment, we first evaluate the hard real-time setting where no bounded deadline misses are allowed. This baseline is shared between Criterion A and Criterion B (there is only one `hard` folder). To run this configuration, execute:

```bash
cd path/to/TSN_Overload/Extension/Experiment_5/hard
python main.py input_csvs/flows_48_u_1.0/flows_48_u_1.0_7q_run_01.csv
```
Output: `Results/flows_48_u_1.0/`

We also compare this setting with different Criterion B weakly-hard constraints — group sizes of `1_2`, `1_3`, and `2_3`. To run a specific configuration, update the corresponding directory. For example, to evaluate the `1_2` group-size configuration:

```bash
cd path/to/TSN_Overload/Extension/Experiment_5/criterion-B-1_2
python main.py input_csvs/flows_48_u_1.0/flows_48_u_1.0_7q_run_01.csv
```
Output: `Results/flows_48_u_1.0/`

To run the other weakly-hard configurations, change the directory accordingly (`Experiment_5/criterion-B-1_3` or `Experiment_5/criterion-B-2_3`).

To process all input instances in a directory, remove the file name and provide only the folder path. For example:

```bash
python main.py input_csvs/flows_48_u_1.0/
```

### Note: Running Criterion A Instead of Criterion B

Everywhere above uses **Criterion B** as the example. For most experiments, running Criterion A is as simple as replacing `criterion-B` with `criterion-A` in the folder path and keeping every command, argument, and output location the same: `Experiment_5/criterion-B-1_2` → `Experiment_5/criterion-A-1_2` (and likewise for `1_3`, `2_3`).



## Notes
Running these experiments from scratch may take several hours to days for each data point depending on the hardware configuration, and **the optimizer results can vary as well**. Most of our experiments were run on a high-performance computer, except Experiment 2 (which was run on a regular device to measure realistic runtime).

The experiments with varying utilization rate need to be run for all utilization rates (0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2) with all 100 instances of `.csv` files to reproduce the results following the methodology of the paper.
