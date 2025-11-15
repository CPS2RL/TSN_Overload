## Integration of Weakly-Hard Real-Time Flows into Time-Sensitive Neworking. We are synthesizing Gate Control List (GCL) for Time Aware Shaper (TAS).

### Objective of the Paper
This paper addresses the challenge of scheduling traffic in Time-Sensitive Networking (TSN) systems where flows can tolerate a bounded number of deadline misses. Instead of enforcing strict hard real-time guarantees for every packet, we incorporate weakly-hard timing constraints—expressed as (m, K) or equivalently (w, h)—which allow controlled deadline violations while maintaining system stability. The goal is to synthesize efficient Gate Control Lists (GCLs) for the IEEE 802.1Qbv Time-Aware Shaper by ensuring all mandatory packets meet their deadlines while maximizing how many optional packets can be successfully transmitted.

### Optimization Model
We develop an ILP-based scheduling formulation that separates packets into mandatory and optional categories. Mandatory packets must always meet their deadlines, while optional packets are served only if resources permit. The optimization assigns weights to optional packets so that more important flows can be prioritized. The model ultimately aims to schedule as many optional packets as possible without compromising the timing guarantees of mandatory traffic.




#### Installation

#### Prerequisites
- Python 3.7 or higher
- pip package manager
- Gurobi Optimizer (requires license)

 Install required packages
   ```bash
   pip install -r requirements.txt
   ```
-Get Lincense for Gurobi Optimizer from (https://www.gurobi.com/)

#### Usage

1. Prepare your input CSV file
   - Place your input CSV file in the `input_csvs/` directory
2. Input csv format
   | Flow | Period | Deadline | Execution  | w | h | Queue |
   |------|--------|----------|------------|---|---|-------|
   | F1   | 400000 | 400000   | 6000       | 1 | 2 | 6     |
   | F2   | 500000 | 500000   | 8000       | 1 | 1 | 5     |
   | ...  | ...    | ...      | ...        | ..| ..| ...   |
   
   





