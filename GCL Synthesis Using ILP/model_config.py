import gurobipy as gp
from gurobipy import GRB

def create_flow_dictionaries(df):
    """
    Convert DataFrame rows into a list of flow dictionaries.
    
    Args:
        df (pd.DataFrame): DataFrame containing flow data.
    
    Returns:
        list: List of dictionaries with flow attributes.
    """
    flows = []
    for _, row in df.iterrows():
        flows.append({
            "Flow": row["Flow"],
            "Period": int(row["Period"]),
            "Deadline": int(row["Deadline"]),
            "Execution Time": int(row["Execution Time"]),
            "Queue": int(row["Queue"]),
            "w": int(row["w"]),  # Number of allowed misses
            "h": int(row["h"])   # Number of mandatory hits
        })
    return flows

def setup_gurobi_model(hyperperiod):
    """
    Initialize and configure the Gurobi model.
    
    Args:
        hyperperiod (int): The computed hyperperiod for the scheduling horizon.
    
    Returns:
        gp.Model: Configured Gurobi model.
        dict: Dictionary to store solver parameters.
    """
    model = gp.Model("NetworkScheduler")
    model.setParam('OutputFlag', 1)  # Enable output
    model.setParam('MIPGap', 0.01)   # 1% optimality gap
    model.setParam('MIPFocus', 1)    # Focus on feasible solutions
    model.setParam('Threads', 0)        # Use 20 threads
    model.setParam('Cuts', 3)
    model.setParam('Presolve', 2)
    model.setParam('LazyConstraints', 1) # Support for callbacks
    model.setParam('TimeLimit', 3600) 
    
    solver_params = {
        'Cipg': 96,  # Inter-packet gap
        't_max': hyperperiod,
        'M': hyperperiod  # Big M for logical constraints
    }
    
    return model, solver_params

def generate_packet_instances(model, flows, hyperperiod):
    """
    Generate packet instances and decision variables for the Gurobi model.
    
    Args:
        model (gp.Model): Gurobi model to add variables to.
        flows (list): List of flow dictionaries.
        hyperperiod (int): The scheduling hyperperiod.
    
    Returns:
        dict: Start time variables for each packet.
        dict: Scheduling decision variables for BE packets.
        list: List of packet instance dictionaries.
    """
    start_times = {}
    is_scheduled = {}
    packet_instances = []
    
    for i, flow in enumerate(flows):
        T = flow['Period']
        L = flow['Execution Time']
        D = flow['Deadline']
        base_class = flow['Queue']
        h = flow['h']
        w = flow['w']
        group_size = h + w
        num_instances = hyperperiod // T
        
        for j in range(num_instances):
            arrival_time = j * T
            deadline = j * T + D
            group_index = j % group_size
            queue_class = base_class if group_index < h else 8
            pkt_id = f'P{flow["Flow"][1:]}_{j+1}'
            
            # Decision variables
            s_var = model.addVar(vtype=GRB.INTEGER, lb=0, ub=hyperperiod, name=f"start_{pkt_id}")
            start_times[pkt_id] = s_var
            
            if queue_class == 8:
                sched_var = model.addVar(vtype=GRB.BINARY, name=f"sched_{pkt_id}")
                is_scheduled[pkt_id] = sched_var
            else:
                is_scheduled[pkt_id] = 1  # Always scheduled for TT
            
            packet_instances.append({
                "Flow": flow["Flow"],
                "Packet": pkt_id,
                "Arrival": arrival_time,
                "Deadline": deadline,
                "Execution Time": L,
                "Class": queue_class
            })
    
    return start_times, is_scheduled, packet_instances