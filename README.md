# Weakly-Hard Real-Time Flow Scheduling in Time-Sensitive Networks.

This repository contains the source code and the raw data files to test and reproduce the RTAS 2026 paper, "Weakly-Hard Real-Time Flow Scheduling in Time Sensitive Networks".

## Objective of the Paper
This paper addresses the challenge of scheduling traffic in Time-Sensitive Networking (TSN) systems where flows can tolerate a bounded number of deadline misses. Instead of enforcing strict hard real-time guarantees for every packet, we incorporate weakly-hard timing constraints—expressed as (m, K) or equivalently (w, h)—--which allow controlled deadline violations while maintaining system stability. The goal is to synthesize efficient Gate Control Lists (GCLs) for the IEEE 802.1Qbv Time-Aware Shaper by ensuring all mandatory packets meet their deadlines while maximizing how many optional packets can be successfully transmitted.

## Scheduling Algorithms
We developed two algorithms to synthesize Gate Control Lists (GCLs): (a) Lazy Search and (b) an ILP-based approach. In both methods, packets are classified as mandatory or optional. Mandatory packets must always meet their deadlines to ensure system correctness, whereas optional packets are transmitted only when sufficient resources are available. The Lazy Search algorithm is scalable and but inefficient in resource utilization, leading to lower admission of optional packets. In contrast, the ILP-based approach jointly optimizes scheduling and resource allocation, resulting in higher admissibility of optional packets.

## Repository
The link for our repository is: https://anonymous.4open.science/r/TSN_Overload/README.md . This is an anonymized github repository (as for the double blinded evaluation). Please download the repository using the `Download Repository` from the upper right.

## Environment Setup
First, we need to set up our local environment to run the artifact. We can set up the environment for windows and Linux. We also recommend setting up a [conda](https://www.anaconda.com/download/success) environment for python. During installation, select "Add Anaconda to PATH" option. Example installation on Linux:
```
bash Anaconda3-2025.12.1-Linux-x86_64.sh
```
For windows run the downloaded `.exe` file to install anaconda into your system. After installing anaconda, navigate to the project directory:
```
cd path/to/Artifact_Eval_RTAS
```
Below here, we will describe the environment setup in both operating system:

### Linux
Run the setup script which will create the conda environment, install required pakages including fonts to plot exactly as in the paper:
```
bash setup.sh
```
Then activate the evironment using:
```
conda activate ae_79
```

### Windows

Create and activate the conda environment:
```
conda create -n ae_79 python=3.13.9 -y
conda activate ae_79
```
Install the required packages:
```
pip install -r requirements.txt
```

## Optimizer Setup
We have formulated an ILP-based Gate Control Lists (GCLs) extraction method to optimize the admissibility of the optional packets. For the optimization module, we are using **Gurobi** for solving the ILP model. Gurobi license is necessary to run the ILP formulation. 

#### Note: Without installing licesnce you can still run the experiments under a certain number of constraints. I have provided sample inputs to run individual experiments which can be run without any license. See [Sample Runs of the Experiments](#sample-runs-of-the-experiments).

Gurobi licese can be installed from the reference of [set up a Gurobi lincese](https://support.gurobi.com/hc/en-us/articles/12872879801105-How-do-I-retrieve-and-set-up-a-Gurobi-license). If you are an academic user, you can install the lincese form [here]([https://portal.gurobi.com/iam/licenses/request](https://support.gurobi.com/hc/en-us/articles/4534601245713-How-do-I-get-started-with-Gurobi-for-academic-users). Make sure the license is installed inside the python environment.


## Sample Runs of the Experiments

The folder `Sample_run` containts examples of the each experiment for a single input file and it is possible to run without any **licnese**. We can run `Experiment_1`, `Experiment_4`, and `Experiment_5` in this way. Feel free to test them, if you intend to run the codes. In order to run the sample experiments, for example, Experiment_1_ILP, then do the following commands:
Each experiment is self-contained in its own directory. Navigate into the experiment folder and run `main.py` from there. Results are saved as `.csv` files in the corresponding `Results/` directory.

#### Experiment 1 — ILP

```bash
cd path/to/Artifact_Eval_RTAS/Sample_run/Experiment_1_ILP/
python main.py input_csvs/sample_1.csv
```
Output: `Experiment_1_ILP/Results/`


#### Experiment 1 — Lazy Search

```bash
cd path/to/Artifact_Eval_RTAS/Sample_run/Experment_1_Lazy_Search/
python main.py input_csvs/sample_1.csv
```
Output: `Experment_1_Lazy_Search/Results/`


#### Experiment 4 — No Reserved Queue

```bash
cd path/to/Artifact_Eval_RTAS/Sample_run/Experment_4_No_Reserved_Queue/
python main.py input_csvs/sample_1.csv
```
Output: `Experment_4_No_Reserved_Queue/Results/`


#### Experiment 5 — Hard Deadline

```bash
cd path/to/Artifact_Eval_RTAS/Sample_run/Experment_5_Hard_deadline/
python main.py input_csvs/sample_1.csv
```
Output: `Experment_5_Hard_deadline/Results/`


## Run All Experiments

If you intend to run the experiments where it exceeds the certain number of constriants, you need Gurobi license (See [Optimizer Setup](#optimizer-setup)). The experiments are listed as Experiment_1, Experiment_2, Experiment_3, Experiment_4, and Experiment_5. For all the experiments, we had varied our utilization rate from 0.4 to 1.2 ([0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]) and for each utilization level, we have tested both our algorithms with 100 generated inputs.
### Experiment 1
Here, we have compared schedulability ratio and optional packet admissibility ratio for ILP and Lazy Serach algorithm. In order to run the code:

**ILP**
Navigate 






## Notes

- To process **all** `.csv` files in `input_csvs/` at once, omit the filename argument:
  ```bash
  python main.py
  ```
- Results for each run are saved as `.csv` files under the `Results/` directory of the respective experiment folder.
#### Installation

#### Prerequisites
- Python 3.7 or higher
- pip package manager
- Gurobi Optimizer (requires license)


-Get Lincense for Gurobi Optimizer from (https://www.gurobi.com/)

#### Usage

1. Prepare your input CSV file
   - Navigate to `GCL Synthesis Using ILP/main.py`and change the directory of `input_file`
2. Input csv format
   | Flow | Period | Deadline | Execution  | w | h | Queue |
   |------|--------|----------|------------|---|---|-------|
   | F1   | 400000 | 400000   | 6000       | 1 | 2 | 6     |
   | F2   | 500000 | 500000   | 8000       | 1 | 1 | 5     |
   | ...  | ...    | ...      | ...        | ..| ..| ...   |
   
   


### Impact of Weight on Optional Packets
We use weights to assign relative priority for optional packets. By default, each flow has a weight of 1.0.

#### How to Configure Flow Weights

1. Navigate to `GCL Synthesis Using ILP/solver.py`
2. Modify the `flow_weights` dictionary to assign custom weights to specific flows:
```python
flow_weights = {"F1": 1.0, "F2": 2.0, "F3": 0.5}
```

#### Example
```python
flow_weights = {
    "F1": 10.0, "F2": 5.0, "F3": 10.0 }
```

**Note:** You can design the flow weights based on your specific application requirements. Higher weights indicate higher priority for scheduling.


### Lazy Search Alogrithm
Our goal is to guarantee deadlines for mandatory packets while opportunistically scheduling optional packets during slack times using our Lazy Search heuristic. The algorithm orders packets, generates GCLs for mandatory flows using EDF, and then fills slack intervals with optional packets only when they can complete without interference. If an optional packet is scheduled before a mandatory, we utilize a guard band. Navigate to the folder **GCL Synthesis Using Lazy Search Heuristic** and this can be run similarly to the GCL synthesis ILP


### No Reserved Queue
We use an optimization model that assigns optional packets to a reserved queue. To evaluate whether this is better than keeping them in their original queues, we minimize packet response time while allowing flows to use all available queues. Navigate to the folder **GCL Synthesis with No Reserved Queue** and this can be run similarly to the GCL synthesis ILP, but with flow-to-queue assignment across all eight queues.


### Hardware Experiment

We validated our ILP-based scheduling algorithm on the [InnoRoute Real-Time HAT](https://innoroute.com/realtimehat/) to demonstrate feasibility and effectiveness in a real hardware environment. We have two following scenarios: (i) Proposed ILP with reserved queue for optional packets, and (ii) Response-time minimization without queue reservation (all flows across 8 queues). Configure the TSN switch egress port as all gate open (follow the documentation of [InnoRoute Real-Time HAT](https://innoroute.com/realtimehat/)). Take a set of flows and run  both optimization model to get the start time of each packet. Use their start time (gate open time) and generates VLAN-tagged UDP packets with precise timestamps (start time of packets). We send the packets through the switch using `tcpreplay`:
```bash
sudo tcpreplay -i RT0 --preload-pcap --timer=nano --loop=1 generated_packets.pcap
```

and capture the packets after forwarding through the switch:
```bash
sudo tcpdump -i RT0 -n -w captured_packets.pcap -tt -s 65535
```

Then we can analyze the captured packets to find out potential deadline violations. We can measure response time, R<sub>i</sub> and calculate Sparsity where Sparsity = R<sub>i</sub>/D<sub>i</sub> to generate Figure 12 of our paper.




