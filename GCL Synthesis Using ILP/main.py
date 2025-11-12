import os
import gc
import sys  # Add this line
import data_loader
import model_config
import constraints
import solver
import results_processor

def process_single_file(file_path, results_folder):
    # Initialize variables
    model = None
    df = None
    flows = None
    packet_instances = None
    start_times = None
    is_scheduled = None
    gap_callback = None
    
    try:
        input_filename = os.path.basename(file_path)
        print(f"\nProcessing file: {input_filename}")
        
        # Step 1: Load data and compute hyperperiod
        df = data_loader.load_flow_data(file_path)
        hyperperiod = data_loader.compute_hyperperiod(df)
        print(f"Hyperperiod, H = {hyperperiod}")
        
        # Step 2: Convert to flow dictionaries
        flows = model_config.create_flow_dictionaries(df)
        
        # Step 3: Set up Gurobi model
        model, solver_params = model_config.setup_gurobi_model(hyperperiod)
        
        # Step 4: Generate packet instances
        start_times, is_scheduled, packet_instances = model_config.generate_packet_instances(model, flows, hyperperiod)
        
        # Step 5: Add constraints
        constraints.add_constraints(model, packet_instances, start_times, is_scheduled, solver_params)
        
        # Step 6: Set up objective and solve
        be_packet_count = solver.setup_objective(model, packet_instances, is_scheduled)
        gap_callback = solver.GapStabilityCallback(max_stable_iterations=10, check_interval=5000)

        # CAPTURE AND SAVE MODEL STATISTICS
        print(f"\n=== DETAILED MODEL INFO ===")
        stats_dict, stats_text = results_processor.capture_model_stats(model)
        print(stats_text)  # Still print to console
        
        # Save model statistics to CSV in Results/stats folder
        results_processor.save_model_stats_to_csv(stats_dict, input_filename, results_folder)

        execution_time, gap_history, stopping_reason = solver.solve_model(model, gap_callback)
        
        # Step 7: Process and save results (now passing results_folder)
        number_flows = len(df['Flow'])
        results_processor.handle_results(
            model, packet_instances, start_times, is_scheduled,
            execution_time, gap_history, stopping_reason, number_flows, 
            input_filename, results_folder  # Pass results folder here
        )
        
        # Verify that output files were created
        all_packets_filename = f'all_packets_status_{os.path.splitext(input_filename)[0]}.csv'
        all_packets_filepath = os.path.join(results_folder, all_packets_filename)
        
        if os.path.exists(all_packets_filepath):
            print(f"Confirmed: Output file '{all_packets_filepath}' created.")
        else:
            print(f"Warning: Output file '{all_packets_filepath}' not found.")
        
        return True
        
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return False
        
    finally:
        # MEMORY CLEANUP SECTION
        print("Cleaning up memory...")
        
        # Dispose of Gurobi model explicitly
        if model is not None:
            try:
                model.dispose()
                print("Gurobi model disposed.")
            except:
                pass  # Model might already be disposed
        
        # Clear large data structures
        if df is not None:
            del df
        if flows is not None:
            del flows
        if packet_instances is not None:
            del packet_instances
        if start_times is not None:
            del start_times
        if is_scheduled is not None:
            del is_scheduled
        if gap_callback is not None:
            del gap_callback
        
        # Force garbage collection
        gc.collect()
        print("Memory cleanup completed.")

def main():
    """
    Main function to process all CSV files in a specified folder.
    """
    # CONFIGURE PATHS HERE - ONLY PLACE YOU NEED TO CHANGE
    input_folder = 'input_csvs/flows_48' #######################################################################
    results_folder = 'Results/flows_48'  #######################################################################
    
    # Create directories if they don't exist
    os.makedirs(input_folder, exist_ok=True)
    os.makedirs(results_folder, exist_ok=True)
    
    # Get list of CSV files
    csv_files = [f for f in os.listdir(input_folder) if f.endswith('.csv')]
    
    if not csv_files:
        print(f"No CSV files found in {input_folder}")
        return
    
    print(f"Found {len(csv_files)} CSV files to process: {csv_files}")
    print(f"Input folder: {input_folder}")
    print(f"Results folder: {results_folder}")
    
    successful = 0
    failed = 0
    
    for i, csv_file in enumerate(csv_files, 1):
        print(f"\n{'='*50}")
        print(f"Processing file {i}/{len(csv_files)}: {csv_file}")
        print(f"{'='*50}")
        
        file_path = os.path.join(input_folder, csv_file)
        
        if process_single_file(file_path, results_folder):
            successful += 1
        else:
            failed += 1
        
        # Additional cleanup between files
        print(f"Completed file {i}/{len(csv_files)}. Running additional cleanup...")
        gc.collect()  # Force garbage collection between files
        
        # Optional: Print memory usage if psutil is available
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            print(f"Current memory usage: {memory_mb:.2f} MB")
        except ImportError:
            pass  # psutil not available, skip memory reporting
    
    print(f"\n{'='*30}")
    print("BATCH PROCESSING SUMMARY")
    print(f"{'='*30}")
    print(f"Total files processed: {len(csv_files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Results saved to: {results_folder}")
    
    # Final cleanup
    print("\nPerforming final memory cleanup...")
    gc.collect()

if __name__ == "__main__":
    main()