import gurobipy as gp
from gurobipy import GRB
import time

class GapStabilityCallback:
    def __init__(self, max_stable_iterations=5, check_interval=2000):
        self.max_stable_iterations = max_stable_iterations
        self.check_interval = check_interval
        self.last_gap = None
        self.stable_count = 0
        self.iteration_count = 0
        self.gap_history = []
        
    def __call__(self, model, where):
        if where == GRB.Callback.MIP:
            self.iteration_count += 1
            
            if self.iteration_count % self.check_interval == 0:
                objbst = model.cbGet(GRB.Callback.MIP_OBJBST)
                objbnd = model.cbGet(GRB.Callback.MIP_OBJBND)
                nodcnt = model.cbGet(GRB.Callback.MIP_NODCNT)
                runtime = model.cbGet(GRB.Callback.RUNTIME)
                
                if objbst != GRB.INFINITY and objbst != 0:
                    current_gap = abs(objbst - objbnd) / abs(objbst)
                    rounded_gap = round(current_gap * 1000, 1)
                    
                    print(f"Check #{len(self.gap_history)+1}: Gap: {current_gap*100:.3f}%, "
                          f"Total Response Time: {int(objbst)}, Nodes: {int(nodcnt)}, Time: {runtime:.0f}s")
                    
                    if self.last_gap is None:
                        self.last_gap = rounded_gap
                        self.stable_count = 1
                    elif abs(rounded_gap - self.last_gap) < 1:
                        self.stable_count += 1
                        print(f"   → Gap stable for {self.stable_count} consecutive checks")
                    else:
                        self.stable_count = 1
                        self.last_gap = rounded_gap
                        print(f"   → Gap changed, resetting counter")
                    
                    self.gap_history.append({
                        'check': len(self.gap_history) + 1,
                        'gap': current_gap,
                        'solution': int(objbst),
                        'bound': objbnd,
                        'nodes': int(nodcnt),
                        'time': runtime
                    })
                    
                    if self.stable_count >= self.max_stable_iterations:
                        print(f"\n STOPPING: Gap has been stable at {current_gap*100:.3f}% "
                              f"for {self.stable_count} consecutive checks")
                        print(f" Best solution found: Total Response Time = {int(objbst)}")
                        model.terminate()

def setup_objective(model, packet_instances, start_times):
    response_times = []
    
    for pkt in packet_instances:
        s = start_times[pkt["Packet"]]
        arrival = pkt["Arrival"]
        exec_time = pkt["Execution Time"]
        response_time = s + exec_time - arrival
        response_times.append(response_time)
    
    model.setObjective(gp.quicksum(response_times), GRB.MINIMIZE)
    print(f"Minimizing total response time for {len(response_times)} packets")
    
    return len(response_times)

def solve_model(model, gap_callback):
    print(" Starting optimization with gap stability monitoring...")
    print(f" Will stop if gap remains stable for {gap_callback.max_stable_iterations} consecutive checks")
    print(f" Checking every {gap_callback.check_interval:,} nodes")
    
    solve_start_time = time.time()
    
    try:
        model.optimize(gap_callback)
    except KeyboardInterrupt:
        print("\n Optimization interrupted by user (Ctrl+C)")
    
    solve_end_time = time.time()
    execution_time = solve_end_time - solve_start_time
    
    print(f"\n=== SOLVER PERFORMANCE ===")
    print(f"Execution time: {execution_time:.4f} seconds")
    print(f"Execution time: {execution_time/60:.2f} minutes")
    
    if gap_callback.gap_history:
        print(f"\n=== GAP STABILITY ANALYSIS ===")
        print(f"Total gap checks performed: {len(gap_callback.gap_history)}")
        print(f"Final stable count: {gap_callback.stable_count}")
        
        print("\nGap History (last 5 checks):")
        for entry in gap_callback.gap_history[-5:]:
            print(f"  Check {entry['check']}: Gap={entry['gap']*100:.3f}%, "
                  f"Total Response Time={entry['solution']}, Time={entry['time']:.0f}s")
    
    stopping_reason = "Unknown"
    if model.status == GRB.OPTIMAL:
        stopping_reason = "Proven Optimal (Gap = 0%)"
    elif gap_callback.stable_count >= gap_callback.max_stable_iterations:
        stopping_reason = f"Gap Stable for {gap_callback.stable_count} Checks"
    else:
        stopping_reason = f"Gurobi Status: {model.status}"
    
    print(f"\n=== STOPPING REASON ===")
    print(f" {stopping_reason}")
    
    return execution_time, gap_callback.gap_history, stopping_reason