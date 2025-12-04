import gurobipy as gp
from gurobipy import GRB

def create_flow_dictionaries(df):
    flows = []
    for _, row in df.iterrows():
        flows.append({
            "Flow": row["Flow"],
            "Period": int(row["Period"]),
            "Deadline": int(row["Deadline"]),
            "Execution Time": int(row["Execution Time"]),
            "Queue": int(row["Queue"]),
            "w": int(row["w"]),
            "h": int(row["h"])
        })
    return flows

def setup_gurobi_model(hyperperiod):
    model = gp.Model("NetworkScheduler")
    model.setParam('OutputFlag', 1)
    model.setParam('MIPGap', 0.01)
    model.setParam('MIPFocus', 1)
    model.setParam('Threads', 0)
    model.setParam('Cuts', 3)
    model.setParam('Presolve', 2)
    model.setParam('LazyConstraints', 1)
    model.setParam('TimeLimit', 2700)
    
    solver_params = {
        'Cipg': 96,
        't_max': hyperperiod,
        'M': hyperperiod
    }
    
    return model, solver_params

def generate_packet_instances(model, flows, hyperperiod, t_max):
    start_times = {}
    is_scheduled = {}
    packet_instances = []
    
    for i, flow in enumerate(flows):
        T = flow['Period']
        L = flow['Execution Time']
        D = flow['Deadline']
        queue_class = flow['Queue']
        
        num_instances = hyperperiod // T
        
        for j in range(num_instances):
            arrival_time = j * T
            deadline = j * T + D
            pkt_id = f'P{flow["Flow"][1:]}_{j+1}'
            
            s_var = model.addVar(vtype=GRB.INTEGER, lb=0, ub=t_max, name=f"start_{pkt_id}")
            start_times[pkt_id] = s_var
            
            is_scheduled[pkt_id] = 1
            
            packet_instances.append({
                "Flow": flow["Flow"],
                "Packet": pkt_id,
                "Arrival": arrival_time,
                "Deadline": deadline,
                "Execution Time": L,
                "Class": queue_class
            })
    
    return start_times, is_scheduled, packet_instances