import os
import gc
import data_loader
import model_config
import constraints
import solver
import results_processor

def main():
    input_file = "input_csvs/flows_16_u_0.4_7q_run_01.csv"
    results_folder = "Results/"
    
    os.makedirs(results_folder, exist_ok=True)
    
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found!")
        return
    
    input_filename = os.path.basename(input_file)
    print(f"\nProcessing file: {input_filename}")
    
    try:
        df = data_loader.load_flow_data(input_file)
        hyperperiod = data_loader.compute_hyperperiod(df)
        print(f"Hyperperiod, H = {hyperperiod}")
        
        flows = model_config.create_flow_dictionaries(df)
        
        model, solver_params = model_config.setup_gurobi_model(hyperperiod)
        
        start_times, is_scheduled, packet_instances = model_config.generate_packet_instances(
            model, flows, hyperperiod
        )
        
        constraints.add_constraints(model, packet_instances, start_times, is_scheduled, solver_params)
        
        solver.setup_objective(model, packet_instances, is_scheduled)
        gap_callback = solver.GapStabilityCallback(max_stable_iterations=10, check_interval=5000)

        print(f"\n=== DETAILED MODEL INFO ===")
        stats_dict, stats_text = results_processor.capture_model_stats(model)
        print(stats_text)
        results_processor.save_model_stats_to_csv(stats_dict, input_filename, results_folder)

        execution_time, gap_history, stopping_reason = solver.solve_model(model, gap_callback)
        
        number_flows = len(df['Flow'])
        results_processor.handle_results(
            model, packet_instances, start_times, is_scheduled,
            execution_time, gap_history, stopping_reason, number_flows,
            input_filename, results_folder
        )
        
        
        model.dispose()
        gc.collect()
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
