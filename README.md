## Weakly-Hard Real-Time Flow Scheduling in Time-Sensitive Networks.

 We are synthesizing Gate Control List (GCL) for Time Aware Shaper (TAS).

### Objective of the Paper
This paper addresses the challenge of scheduling traffic in Time-Sensitive Networking (TSN) systems where flows can tolerate a bounded number of deadline misses. Instead of enforcing strict hard real-time guarantees for every packet, we incorporate weakly-hard timing constraints—expressed as (m, K) or equivalently (w, h)—which allow controlled deadline violations while maintaining system stability. The goal is to synthesize efficient Gate Control Lists (GCLs) for the IEEE 802.1Qbv Time-Aware Shaper by ensuring all mandatory packets meet their deadlines while maximizing how many optional packets can be successfully transmitted.

### Optimization Model
We develop an ILP-based scheduling formulation that separates packets into mandatory and optional categories. Mandatory packets must always meet their deadlines, while optional packets are served only if resources permit. The optimization assigns weights to optional packets so that more important flows can be prioritized. The model ultimately aims to schedule as many optional packets as possible without compromising the timing guarantees of mandatory traffic.




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




