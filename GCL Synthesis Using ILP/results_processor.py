import pandas as pd
import os
import sys
import io
import gurobipy as gp
from gurobipy import GRB

def capture_model_stats(model):
    """
    Capture model.printStats() output and return as structured data
    
    Args:
        model (gp.Model): Gurobi model to capture statistics from
        
    Returns:
        tuple: (stats_dict, stats_text) containing structured data and raw text
    """
    # Capture the printed output
    old_stdout = sys.stdout
    sys.stdout = captured_output = io.StringIO()
    
    try:
        model.printStats()
        stats_text = captured_output.getvalue()
    finally:
        sys.stdout = old_stdout
    
    # Parse the captured text into structured data
    stats_dict = {}
    lines = stats_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            # Special handling for different types of data
            if key == "Variable types":
                # Parse variable types: "0 continuous, 50532 integer (50340 binary)"
                parts = value.split(',')
                
                for part in parts:
                    part = part.strip()
                    if 'continuous' in part:
                        continuous_count = int(part.split()[0])
                        stats_dict['Continuous_Variables'] = continuous_count
                    elif 'integer' in part:
                        # Handle "50532 integer (50340 binary)"
                        if '(' in part and ')' in part:
                            # Extract integer count
                            integer_part = part.split('integer')[0].strip()
                            integer_count = int(integer_part)
                            stats_dict['Integer_Variables'] = integer_count
                            
                            # Extract binary count from parentheses
                            binary_part = part.split('(')[1].split('binary')[0].strip()
                            binary_count = int(binary_part)
                            stats_dict['Binary_Variables'] = binary_count
                        else:
                            # Just integer without binary specification
                            integer_count = int(part.split()[0])
                            stats_dict['Integer_Variables'] = integer_count
                            
            elif key == "Matrix range" or key == "Objective range" or key == "Bounds range" or key == "RHS range":
                # Parse ranges like "[1e+00, 1e+06]"
                if '[' in value and ']' in value:
                    range_values = value.strip('[]').split(',')
                    if len(range_values) == 2:
                        min_val = range_values[0].strip()
                        max_val = range_values[1].strip()
                        stats_dict[f'{key}_Min'] = min_val
                        stats_dict[f'{key}_Max'] = max_val
                else:
                    stats_dict[key] = value
                    
            elif 'rows' in value and 'columns' in value and 'nonzeros' in value:
                # Parse "72711 rows, 50532 columns, 213612 nonzeros"
                parts = value.split(',')
                for part in parts:
                    part = part.strip()
                    if 'rows' in part:
                        rows = int(part.split()[0])
                        stats_dict['Rows'] = rows
                    elif 'columns' in part:
                        columns = int(part.split()[0])
                        stats_dict['Columns'] = columns
                    elif 'nonzeros' in part:
                        nonzeros = int(part.split()[0])
                        stats_dict['Nonzeros'] = nonzeros
            else:
                # Try to convert numeric values for other fields
                try:
                    if '.' in value and 'e' not in value.lower():
                        value = float(value)
                    elif value.isdigit():
                        value = int(value)
                except ValueError:
                    # Keep as string if not numeric
                    pass
                    
                stats_dict[key] = value
        else:
            # Handle lines without colons (like model name, problem type)
            if 'model' in line.lower() and "'" in line:
                # Extract model name
                model_name = line.split("'")[1]
                stats_dict['Model_Name'] = model_name
            elif line in ['MIP', 'LP', 'QP', 'MILP', 'MIQP']:
                stats_dict['Problem_Type'] = line
    
    return stats_dict, stats_text

def save_model_stats_to_csv(stats_dict, input_filename, results_folder):
    """
    Save model statistics to CSV file in Results/stats folder
    
    Args:
        stats_dict (dict): Dictionary containing model statistics
        input_filename (str): Name of the input CSV file
        results_folder (str): Base results folder path
        
    Returns:
        str: Path to the saved statistics file
    """
    # Create DataFrame from stats dictionary
    stats_df = pd.DataFrame([stats_dict])
    
    # Add input filename for reference
    stats_df['Input_File'] = input_filename
    
    # Create stats folder path
    stats_folder = os.path.join(results_folder, 'stats')
    os.makedirs(stats_folder, exist_ok=True)
    
    # Create filename
    base_name = os.path.splitext(input_filename)[0]
    stats_filename = f'model_stats_{base_name}.csv'
    stats_filepath = os.path.join(stats_folder, stats_filename)
    
    # Save to CSV
    stats_df.to_csv(stats_filepath, index=False)
    print(f"Model statistics saved to '{stats_filepath}'")
    
    return stats_filepath


def process_results(model, packet_instances, start_times, is_scheduled, execution_time, stopping_reason, number_flows):
    """
    Process optimization results and generate logs and summaries.
    
    Args:
        model (gp.Model): Solved Gurobi model.
        packet_instances (list): List of packet instance dictionaries.
        start_times (dict): Start time variables for each packet.
        is_scheduled (dict): Scheduling decision variables for BE packets (or 1 for TT).
        execution_time (float): Solver execution time in seconds.
        stopping_reason (str): Reason for solver termination.
        number_flows (int): Number of flows in the input data.
    
    Returns:
        tuple: (all_packets_df, gcl_df) containing comprehensive packet status and GCL DataFrames.
    """
    all_packets_log = []
    gcl_log = []
    
    for pkt in packet_instances:
        pkt_id = pkt["Packet"]
        arrival = pkt["Arrival"]
        deadline = pkt["Deadline"]
        exec_time = pkt["Execution Time"]
        packet_class = pkt["Class"]
        flow_name = pkt["Flow"]
        
        # Check if scheduling decision is valid
        is_sched = False
        try:
            is_sched = is_scheduled[pkt_id].x >= 0.5 if packet_class == 8 else True
        except AttributeError:
            print(f"Warning: Unable to access scheduling decision for {pkt_id}. Assuming not scheduled.")
            is_sched = False if packet_class == 8 else True
        
        if is_sched:
            try:
                start = int(start_times[pkt_id].x)
                gate_close = start + exec_time
                response_time = gate_close - arrival
                status = "Scheduled - Deadline Met" if gate_close <= deadline else "Scheduled - Deadline Missed"
                
                gcl_log.append({
                    "Packet": pkt_id,
                    "Class": packet_class,
                    "Arrival": arrival,
                    "Gate Open": start,
                    "Gate Close": gate_close,
                    "Deadline": deadline,
                    "Response Time": response_time
                })
            except AttributeError:
                print(f"Warning: Unable to access start time for {pkt_id}. Marking as unscheduled.")
                start = None
                gate_close = None
                response_time = None
                status = "Scheduled - Invalid Start Time"
        else:
            start = None
            gate_close = None
            response_time = None
            status = "BE - Not Scheduled" if packet_class == 8 else "TT - Not Scheduled (ERROR!)"
        
        all_packets_log.append({
            "Flow": flow_name,
            "Packet": pkt_id,
            "Class": packet_class,
            "Arrival": arrival,
            "Deadline": deadline,
            "Execution Time": exec_time,
            "Gate Open": start,
            "Gate Close": gate_close,
            "Response Time": response_time,
            "Status": status,
            "Scheduled": "Yes" if is_sched else "No",
            "Deadline Met": "Yes" if is_sched and gate_close is not None and gate_close <= deadline else "No" if is_sched else "N/A",
            "Solver_Execution_Time_Seconds": execution_time,
            "Solver_Execution_Time_Minutes": execution_time / 60,
            "Solver_Status": model.status,
            "Objective_Value": model.objVal if model.SolCount > 0 else None,
            "Stopping_Reason": stopping_reason
        })
    
    all_packets_df = pd.DataFrame(all_packets_log).sort_values(by=["Flow", "Arrival"]).reset_index(drop=True)
    gcl_df = pd.DataFrame(gcl_log).sort_values(by="Gate Open").reset_index(drop=True) if gcl_log else pd.DataFrame()
    
    return all_packets_df, gcl_df

def save_results(all_packets_df, gcl_df, number_flows, input_filename, results_folder):
    """
    Save packet status and GCL to CSV files with input filename prefix.
    
    Args:
        all_packets_df (pd.DataFrame): Comprehensive packet status DataFrame.
        gcl_df (pd.DataFrame): GCL DataFrame for scheduled packets.
        number_flows (int): Number of flows in the input data.
        input_filename (str): Name of the input CSV file (without path).
        results_folder (str): Path to the results folder.
    """
    # Create the results folder if it doesn't exist
    os.makedirs(results_folder, exist_ok=True)
    
    base_name = os.path.splitext(input_filename)[0]
    all_packets_filename = f'all_packets_status_{base_name}.csv'
    all_packets_filepath = os.path.join(results_folder, all_packets_filename)
    all_packets_df.to_csv(all_packets_filepath, index=False)
    print(f"All packets status saved to '{all_packets_filepath}'")
    
    #if not gcl_df.empty:
    #    gcl_filename = f'optimized_gcl_{base_name}.csv'
    #    gcl_filepath = os.path.join(results_folder, gcl_filename)
    #    gcl_df.to_csv(gcl_filepath, index=False)
    #    print(f"Scheduled packets GCL saved to '{gcl_filepath}'")

def print_summary(all_packets_df, model, execution_time):
    """
    Print summary statistics and status breakdown.
    
    Args:
        all_packets_df (pd.DataFrame): Comprehensive packet status DataFrame.
        model (gp.Model): Solved Gurobi model.
        execution_time (float): Solver execution time in seconds.
    """
    total_packets = len(all_packets_df)
    scheduled_packets = len(all_packets_df[all_packets_df["Scheduled"] == "Yes"])
    scheduled_tt = len(all_packets_df[(all_packets_df["Class"] != 8) & (all_packets_df["Scheduled"] == "Yes")])
    scheduled_be = len(all_packets_df[(all_packets_df["Class"] == 8) & (all_packets_df["Scheduled"] == "Yes")])
    unscheduled_tt = len(all_packets_df[(all_packets_df["Class"] != 8) & (all_packets_df["Scheduled"] == "No")])
    unscheduled_be = len(all_packets_df[(all_packets_df["Class"] == 8) & (all_packets_df["Scheduled"] == "No")])
    deadline_violations = len(all_packets_df[all_packets_df["Deadline Met"] == "No"])
    
    print(f"\n=== PACKET SCHEDULING SUMMARY ===")
    print(f"Total packets: {total_packets}")
    print(f"Scheduled packets: {scheduled_packets}")
    print(f"  - TT packets scheduled: {scheduled_tt}")
    print(f"  - BE packets scheduled: {scheduled_be}")
    print(f"Unscheduled packets: {total_packets - scheduled_packets}")
    print(f"  - TT packets unscheduled: {unscheduled_tt} {'(ERROR!)' if unscheduled_tt > 0 else ''}")
    print(f"  - BE packets unscheduled: {unscheduled_be}")
    print(f"Deadline violations: {deadline_violations}")
    
    status_counts = all_packets_df['Status'].value_counts()
    print(f"\n=== STATUS BREAKDOWN ===")
    for status, count in status_counts.items():
        print(f"{status}: {count}")
    
    if deadline_violations > 0:
        print(f"\nWARNING: {deadline_violations} packets missed their deadlines!")
        violated_packets = all_packets_df[all_packets_df["Deadline Met"] == "No"]
        print("Packets that missed deadlines:")
        print(violated_packets[["Packet", "Class", "Arrival", "Deadline", "Gate Close", "Response Time"]])
    else:
        print("\nAll scheduled packets meet their deadlines ✓")
    
    print(f"\n=== SAMPLE OF ALL PACKETS STATUS ===")
    display_cols = ["Flow", "Packet", "Class", "Status", "Solver_Execution_Time_Minutes", "Stopping_Reason"]
    print(all_packets_df[display_cols].head(10).to_string(index=False))
    
    print(f"\n=== SOLVER PERFORMANCE SUMMARY ===")
    print(f"Execution Time: {execution_time:.4f} seconds ({execution_time/60:.2f} minutes)")
    print(f"Solver Status: {model.status}")
    print(f"Objective Value: {model.objVal if model.SolCount > 0 else 'N/A'}")
    print(f"Stopping Reason: {all_packets_df['Stopping_Reason'].iloc[0]}")

def handle_results(model, packet_instances, start_times, is_scheduled, execution_time, gap_history, stopping_reason, number_flows, input_filename, results_folder):
    """
    Handle results processing, saving, and printing.
    
    Args:
        model (gp.Model): Solved Gurobi model.
        packet_instances (list): List of packet instance dictionaries.
        start_times (dict): Start time variables for each packet.
        is_scheduled (dict): Scheduling decision variables for BE packets.
        execution_time (float): Solver execution time in seconds.
        gap_history (list): Gap history from callback.
        stopping_reason (str): Reason for solver termination.
        number_flows (int): Number of flows in the input data.
        input_filename (str): Name of the input CSV file (without path).
        results_folder (str): Path to the results folder.
    """
    
    # Define solver statuses that can have valid solutions
    valid_solution_statuses = [
        GRB.OPTIMAL,        # 2 - Optimal solution found
        GRB.INTERRUPTED,    # 11 - Optimization was interrupted
        GRB.NODE_LIMIT,     # 8 - Node limit reached
        GRB.TIME_LIMIT,     # 9 - Time limit reached
        GRB.SOLUTION_LIMIT, # 10 - Solution limit reached
        GRB.SUBOPTIMAL      # 13 - Suboptimal solution found
    ]
    
    # Print solver status information
    print(f"Optimization ended with status {model.status}")
    status_names = {
        2: "OPTIMAL", 8: "NODE_LIMIT", 9: "TIME_LIMIT", 
        10: "SOLUTION_LIMIT", 11: "INTERRUPTED", 13: "SUBOPTIMAL"
    }
    status_name = status_names.get(model.status, f"UNKNOWN({model.status})")
    print(f"Status name: {status_name}")
    print(f"Solution count: {model.SolCount}")
    
    # Check if we have a valid solution to process
    if model.status in valid_solution_statuses and model.SolCount > 0:
        print(f"\nSolution found! Status: {model.status}")
        print(f"Objective value: {model.objVal}")
        
        all_packets_df, gcl_df = process_results(model, packet_instances, start_times, is_scheduled, 
                                                execution_time, stopping_reason, number_flows)
        save_results(all_packets_df, gcl_df, number_flows, input_filename, results_folder)
        print_summary(all_packets_df, model, execution_time)
        
        if gap_history:
            print(f"\n=== GAP STABILITY ANALYSIS ===")
            print(f"Total gap checks performed: {len(gap_history)}")
            print(f"Final stable count: {max(entry['check'] for entry in gap_history) if gap_history else 0}")
            print("\nGap History (last 5 checks):")
            for entry in gap_history[-5:]:
                print(f"  Check {entry['check']}: Gap={entry['gap']*100:.3f}%, "
                      f"Solution={entry['solution']}, Time={entry['time']:.0f}s")
                
    elif model.status == GRB.INFEASIBLE:
        print("No feasible solution found!")
        model.computeIIS()
        model.write("infeasible.ilp")
        print("IIS written to infeasible.ilp")
    
    else:
        print(f"No solution available. Status: {model.status}, Solution count: {model.SolCount}")