import gurobipy as gp
from gurobipy import GRB
import re

def add_constraints(model, packet_instances, start_times, is_scheduled, solver_params):
    """
    Add all scheduling constraints to the Gurobi model with redundancy elimination.
    
    Args:
        model (gp.Model): Gurobi model to add constraints to.
        packet_instances (list): List of packet instance dictionaries.
        start_times (dict): Start time variables for each packet.
        is_scheduled (dict): Scheduling decision variables for BE packets (or 1 for TT).
        solver_params (dict): Solver parameters including Cipg, t_max, and M.
        
    Returns:
        dict: Statistics about constraints added and redundancy elimination.
    """
    Cipg = solver_params['Cipg']
    M = solver_params['M']
    
    # Track packet pairs that already have ordering constraints to avoid redundancy
    constrained_pairs = set()
    
    # Statistics tracking
    stats = {
        'fifo_constraints': 0,
        'tie_break_constraints': 0,
        'edf_constraints': 0,
        'physical_constraints': 0,
        'skipped_constraints': 0,
        'total_constrained_pairs': 0,
        'total_packet_instances': len(packet_instances)
    }
    
    # Calculate the maximum execution time across all packets
    max_execution_time = max(pkt["Execution Time"] for pkt in packet_instances)
    
    # 1. Arrival and Deadline Constraints
    for pkt in packet_instances:
        pkt_id = pkt["Packet"]
        arrival_time = pkt["Arrival"]
        deadline = pkt["Deadline"]
        exec_time = pkt["Execution Time"]
        s = start_times[pkt_id]
        
        if pkt["Class"] == 8:  # BE packets
            sched = is_scheduled[pkt_id]
            model.addConstr(s >= arrival_time * sched, name=f"arrival_{pkt_id}")
            model.addConstr(s + exec_time <= deadline + M * (1 - sched), name=f"deadline_{pkt_id}")
        else:  # TT packets
            model.addConstr(s >= arrival_time, name=f"arrival_{pkt_id}")
            model.addConstr(s + exec_time <= deadline, name=f"deadline_{pkt_id}")
    
    # 2. FIFO Constraints within Same Queue
    for i, pkt1 in enumerate(packet_instances):
        for j, pkt2 in enumerate(packet_instances):
            if (pkt1["Arrival"] < pkt2["Arrival"] and 
                pkt1["Class"] == pkt2["Class"]):
                
                s1 = start_times[pkt1["Packet"]]
                s2 = start_times[pkt2["Packet"]]
                e1 = pkt1["Execution Time"]
                
                # Earlier packet must finish before later packet starts
                model.addConstr(s1 + e1 + Cipg <= s2, name=f"fifo_{stats['fifo_constraints']}")
                stats['fifo_constraints'] += 1
                
                # Track this pair as constrained
                constrained_pairs.add((pkt1["Packet"], pkt2["Packet"]))
    
    # 3. Tie-Breaking Constraints for Same Queue and Arrival Time
    def get_flow_priority(flow_name):
        """Extract numeric priority from flow name (e.g., 'Flow1' -> 1)."""
        match = re.search(r'\d+', flow_name)
        return int(match.group()) if match else 999
    
    # Add flow priority to packet instances for easier access
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
                
                # Determine packet priority using tie-breaking rules
                should_pkt1_go_first = (
                    pkt1["Deadline"] < pkt2["Deadline"] or
                    (pkt1["Deadline"] == pkt2["Deadline"] and
                     pkt1["Execution Time"] > pkt2["Execution Time"]) or
                    (pkt1["Deadline"] == pkt2["Deadline"] and
                     pkt1["Execution Time"] == pkt2["Execution Time"] and
                     pkt1["Flow_Priority"] < pkt2["Flow_Priority"])
                )
                
                if pkt1["Class"] == 8:  # Both BE packets
                    sched1 = is_scheduled[pkt1["Packet"]]
                    sched2 = is_scheduled[pkt2["Packet"]]
                    
                    # Only apply constraint if both packets are scheduled
                    both_sched = model.addVar(vtype=GRB.BINARY, name=f"tie_both_sched_{stats['tie_break_constraints']}")
                    model.addConstr(both_sched <= sched1, name=f"tie_both1_{stats['tie_break_constraints']}")
                    model.addConstr(both_sched <= sched2, name=f"tie_both2_{stats['tie_break_constraints']}")
                    model.addConstr(both_sched >= sched1 + sched2 - 1, name=f"tie_both_and_{stats['tie_break_constraints']}")
                    
                    if should_pkt1_go_first:
                        model.addConstr(s1 + e1 + Cipg <= s2 + M * (1 - both_sched), 
                                      name=f"tie_break_be_{stats['tie_break_constraints']}")
                        # Track this pair as constrained (conditional on both being scheduled)
                        constrained_pairs.add((pkt1["Packet"], pkt2["Packet"]))
                    else:
                        model.addConstr(s2 + e2 + Cipg <= s1 + M * (1 - both_sched), 
                                      name=f"tie_break_be_{stats['tie_break_constraints']}")
                        # Track this pair as constrained (conditional on both being scheduled)
                        constrained_pairs.add((pkt2["Packet"], pkt1["Packet"]))
                        
                else:  # Both TT packets
                    # TT packets are always scheduled, so directly apply ordering constraint
                    if should_pkt1_go_first:
                        model.addConstr(s1 + e1 + Cipg <= s2, 
                                      name=f"tie_break_tt_{stats['tie_break_constraints']}")
                        constrained_pairs.add((pkt1["Packet"], pkt2["Packet"]))
                    else:
                        model.addConstr(s2 + e2 + Cipg <= s1, 
                                      name=f"tie_break_tt_{stats['tie_break_constraints']}")
                        constrained_pairs.add((pkt2["Packet"], pkt1["Packet"]))
                
                stats['tie_break_constraints'] += 1
    
    # 4. EDF Constraints for TT Packets (different arrival times)
    for i, pkt1 in enumerate(packet_instances):
        for j, pkt2 in enumerate(packet_instances):
            if (pkt1["Packet"] != pkt2["Packet"] and  # Fixed: Added missing check
                pkt1["Deadline"] < pkt2["Deadline"] and
                pkt1["Class"] != 8 and pkt2["Class"] != 8 and
                pkt1["Arrival"] != pkt2["Arrival"]):
                
                s1 = start_times[pkt1["Packet"]]
                s2 = start_times[pkt2["Packet"]]
                e1 = pkt1["Execution Time"]
                e2 = pkt2["Execution Time"]
                
                # Binary variables for overlap detection
                overlap = model.addVar(vtype=GRB.BINARY, name=f"overlap_{stats['edf_constraints']}")
                before1 = model.addVar(vtype=GRB.BINARY, name=f"before1_{stats['edf_constraints']}")
                before2 = model.addVar(vtype=GRB.BINARY, name=f"before2_{stats['edf_constraints']}")
                
                # Overlap detection constraints
                model.addConstr(s1 + e1 <= s2 + M * before1, name=f"before1_def_{stats['edf_constraints']}")
                # Fixed: Use e2 instead of e1 for pkt2
                model.addConstr(s2 + e2 <= s1 + M * before2, name=f"before2_def_{stats['edf_constraints']}")
                model.addConstr(before1 + before2 >= 1 - overlap, name=f"overlap_def_{stats['edf_constraints']}")
                
                # If they overlap, earlier deadline goes first
                model.addConstr(s1 + e1 + Cipg <= s2 + M * (1 - overlap), name=f"edf_{stats['edf_constraints']}")
                stats['edf_constraints'] += 1
                
                # Track this pair as constrained when overlap occurs
                constrained_pairs.add((pkt1["Packet"], pkt2["Packet"]))
    
    # 5. Physical Medium Non-overlap Constraints (only for unconstrained pairs)
    max_execution_time = max(pkt["Execution Time"] for pkt in packet_instances)
    
    for i, pkt1 in enumerate(packet_instances):
        for j, pkt2 in enumerate(packet_instances[i+1:], start=i+1):
            if pkt1["Packet"] == pkt2["Packet"]:
                continue
            
            # Check if this pair already has ordering constraints
            pair1 = (pkt1["Packet"], pkt2["Packet"])
            pair2 = (pkt2["Packet"], pkt1["Packet"])
            
            if pair1 in constrained_pairs or pair2 in constrained_pairs:
                stats['skipped_constraints'] += 1
                continue  # Skip - already constrained by FIFO, tie-breaking, or EDF
                
            s1 = start_times[pkt1["Packet"]]
            s2 = start_times[pkt2["Packet"]]
            e1 = pkt1["Execution Time"]
            e2 = pkt2["Execution Time"]
            c1 = pkt1["Class"]
            c2 = pkt2["Class"]
            
            sched1 = is_scheduled[pkt1["Packet"]] if c1 == 8 else 1
            sched2 = is_scheduled[pkt2["Packet"]] if c2 == 8 else 1
            
            # Binary variable to choose ordering
            order = model.addVar(vtype=GRB.BINARY, name=f"order_{stats['physical_constraints']}")
            
            if c1 != 8 and c2 != 8:  # Both TT packets
                model.addConstr(s1 + e1 + Cipg <= s2 + M * order, name=f"nonoverlap1_{stats['physical_constraints']}")
                model.addConstr(s2 + e2 + Cipg <= s1 + M * (1 - order), name=f"nonoverlap2_{stats['physical_constraints']}")
                
            elif c1 == 8 and c2 == 8:  # Both BE packets
                # Only apply if both are scheduled
                both_sched = model.addVar(vtype=GRB.BINARY, name=f"both_sched_{stats['physical_constraints']}")
                model.addConstr(both_sched <= sched1, name=f"both_sched1_{stats['physical_constraints']}")
                model.addConstr(both_sched <= sched2, name=f"both_sched2_{stats['physical_constraints']}")
                model.addConstr(both_sched >= sched1 + sched2 - 1, name=f"both_sched_and_{stats['physical_constraints']}")
                
                model.addConstr(s1 + e1 + Cipg <= s2 + M * (1 - both_sched) + M * order, 
                              name=f"be_nonoverlap1_{stats['physical_constraints']}")
                model.addConstr(s2 + e2 + Cipg <= s1 + M * (1 - both_sched) + M * (1 - order), 
                              name=f"be_nonoverlap2_{stats['physical_constraints']}")
                
            elif c1 == 8 and c2 != 8:  # BE before TT
                # Fixed: Removed duplicate e1 term
                model.addConstr(s1 + e1 + max_execution_time <= s2 + M * (1 - sched1) + M * order, 
                              name=f"be_tt_nonoverlap1_{stats['physical_constraints']}")
                model.addConstr(s2 + e2 + Cipg <= s1 + M * (1 - sched1) + M * (1 - order), 
                              name=f"be_tt_nonoverlap2_{stats['physical_constraints']}")
                
            elif c1 != 8 and c2 == 8:  # TT before BE
                model.addConstr(s1 + e1 + Cipg <= s2 + M * (1 - sched2) + M * order, 
                              name=f"tt_be_nonoverlap1_{stats['physical_constraints']}")
                # Fixed: Removed duplicate e2 term
                model.addConstr(s2 + e2 + max_execution_time <= s1 + M * (1 - sched2) + M * (1 - order), 
                              name=f"tt_be_nonoverlap2_{stats['physical_constraints']}")
            
            stats['physical_constraints'] += 1