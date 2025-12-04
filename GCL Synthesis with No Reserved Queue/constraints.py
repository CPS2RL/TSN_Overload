import gurobipy as gp
from gurobipy import GRB
import re

def add_constraints(model, packet_instances, start_times, is_scheduled, solver_params):
    Cipg = solver_params['Cipg']
    M = solver_params['M']
    
    constrained_pairs = set()
    max_execution_time = max(pkt["Execution Time"] for pkt in packet_instances)
    
    stats = {
        'arrival_constraints': 0,
        'response_time_constraints': 0,
        'fifo_constraints': 0,
        'tie_break_constraints': 0,
        'edf_constraints': 0,
        'physical_constraints': 0,
        'skipped_constraints': 0,
        'total_constrained_pairs': 0,
        'total_packet_instances': len(packet_instances)
    }
    
    for pkt in packet_instances:
        pkt_id = pkt["Packet"]
        arrival_time = pkt["Arrival"]
        deadline = pkt["Deadline"]
        exec_time = pkt["Execution Time"]
        s = start_times[pkt_id]
        
        model.addConstr(s >= arrival_time, name=f"arrival_{pkt_id}")
        stats['arrival_constraints'] += 1
        
        response_time = s + exec_time - arrival_time
        model.addConstr(response_time >= exec_time, name=f"min_response_{pkt_id}")
        stats['response_time_constraints'] += 1
    
    for i, pkt1 in enumerate(packet_instances):
        for j, pkt2 in enumerate(packet_instances):
            if (pkt1["Arrival"] < pkt2["Arrival"] and 
                pkt1["Class"] == pkt2["Class"]):
                
                s1 = start_times[pkt1["Packet"]]
                s2 = start_times[pkt2["Packet"]]
                e1 = pkt1["Execution Time"]
                
                model.addConstr(s1 + e1 + Cipg <= s2, name=f"fifo_{stats['fifo_constraints']}")
                stats['fifo_constraints'] += 1
                
                constrained_pairs.add((pkt1["Packet"], pkt2["Packet"]))
    
    def get_flow_priority(flow_name):
        match = re.search(r'\d+', flow_name)
        return int(match.group()) if match else 999
    
    for pkt in packet_instances:
        pkt["Flow_Priority"] = get_flow_priority(pkt["Flow"])
    
    for i, pkt1 in enumerate(packet_instances):
        for j, pkt2 in enumerate(packet_instances):
            if (pkt1["Packet"] != pkt2["Packet"] and
                pkt1["Class"] == pkt2["Class"] and
                pkt1["Arrival"] == pkt2["Arrival"]):
                
                s1 = start_times[pkt1["Packet"]]
                s2 = start_times[pkt2["Packet"]]
                e1 = pkt1["Execution Time"]
                e2 = pkt2["Execution Time"]
                
                should_pkt1_go_first = False
                if pkt1["Deadline"] < pkt2["Deadline"]:
                    should_pkt1_go_first = True
                elif pkt1["Deadline"] > pkt2["Deadline"]:
                    should_pkt1_go_first = False
                else:
                    if pkt1["Execution Time"] > pkt2["Execution Time"]:
                        should_pkt1_go_first = True
                    elif pkt1["Execution Time"] < pkt2["Execution Time"]:
                        should_pkt1_go_first = False
                    else:
                        if pkt1["Flow_Priority"] < pkt2["Flow_Priority"]:
                            should_pkt1_go_first = True
                
                if should_pkt1_go_first:
                    model.addConstr(s1 + e1 + Cipg <= s2, 
                                  name=f"tie_break_tt_{stats['tie_break_constraints']}")
                    constrained_pairs.add((pkt1["Packet"], pkt2["Packet"]))
                else:
                    model.addConstr(s2 + e2 + Cipg <= s1, 
                                  name=f"tie_break_tt_{stats['tie_break_constraints']}")
                    constrained_pairs.add((pkt2["Packet"], pkt1["Packet"]))
                
                stats['tie_break_constraints'] += 1
    
    for i, pkt1 in enumerate(packet_instances):
        for j, pkt2 in enumerate(packet_instances):
            if (pkt1["Packet"] != pkt2["Packet"] and
                pkt1["Deadline"] < pkt2["Deadline"] and
                pkt1["Arrival"] != pkt2["Arrival"]):
                
                s1 = start_times[pkt1["Packet"]]
                s2 = start_times[pkt2["Packet"]]
                e1 = pkt1["Execution Time"]
                e2 = pkt2["Execution Time"]
                
                overlap = model.addVar(vtype=GRB.BINARY, name=f"overlap_{stats['edf_constraints']}")
                before1 = model.addVar(vtype=GRB.BINARY, name=f"before1_{stats['edf_constraints']}")
                before2 = model.addVar(vtype=GRB.BINARY, name=f"before2_{stats['edf_constraints']}")
                
                model.addConstr(s1 + e1 <= s2 + M * before1, name=f"before1_def_{stats['edf_constraints']}")
                model.addConstr(s2 + e2 <= s1 + M * before2, name=f"before2_def_{stats['edf_constraints']}")
                model.addConstr(before1 + before2 >= 1 - overlap, name=f"overlap_def_{stats['edf_constraints']}")
                
                model.addConstr(s1 + e1 + Cipg <= s2 + M * (1 - overlap), name=f"edf_{stats['edf_constraints']}")
                stats['edf_constraints'] += 1
                
                constrained_pairs.add((pkt1["Packet"], pkt2["Packet"]))
    
    for i, pkt1 in enumerate(packet_instances):
        for j, pkt2 in enumerate(packet_instances[i+1:], start=i+1):
            if pkt1["Packet"] == pkt2["Packet"]:
                continue
            
            pair1 = (pkt1["Packet"], pkt2["Packet"])
            pair2 = (pkt2["Packet"], pkt1["Packet"])
            
            if pair1 in constrained_pairs or pair2 in constrained_pairs:
                stats['skipped_constraints'] += 1
                continue
                
            s1 = start_times[pkt1["Packet"]]
            s2 = start_times[pkt2["Packet"]]
            e1 = pkt1["Execution Time"]
            e2 = pkt2["Execution Time"]
            
            order = model.addVar(vtype=GRB.BINARY, name=f"order_{stats['physical_constraints']}")
            
            model.addConstr(s1 + e1 + Cipg <= s2 + M * order, name=f"nonoverlap1_{stats['physical_constraints']}")
            model.addConstr(s2 + e2 + Cipg <= s1 + M * (1 - order), name=f"nonoverlap2_{stats['physical_constraints']}")
            
            stats['physical_constraints'] += 1
    
    stats['total_constrained_pairs'] = len(constrained_pairs)
    
    print(f"\n=== CONSTRAINT STATISTICS ===")
    print(f"Arrival constraints: {stats['arrival_constraints']}")
    print(f"Response time constraints: {stats['response_time_constraints']}")
    print(f"FIFO constraints: {stats['fifo_constraints']}")
    print(f"Tie-break constraints: {stats['tie_break_constraints']}")
    print(f"EDF constraints: {stats['edf_constraints']}")
    print(f"Physical constraints: {stats['physical_constraints']}")
    print(f"Skipped constraints: {stats['skipped_constraints']}")
    print(f"Total constrained pairs: {stats['total_constrained_pairs']}")
    
    return stats