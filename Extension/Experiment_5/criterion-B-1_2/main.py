import os
import gc
import re
import sys
import data_loader
import model_config
import constraints
import solver
import results_processor
import queue_mapper


def _natural_sort_key(filename):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', filename)]


def get_results_folder(path):
    if os.path.isfile(path):
        subfolder = os.path.basename(os.path.dirname(path))
    elif os.path.isdir(path):
        subfolder = os.path.basename(os.path.normpath(path))
    else:
        subfolder = ''
    return os.path.join('Results', subfolder) if subfolder else 'Results'


def process_single_file(file_path, results_folder):
    model        = None
    df           = None
    flows        = None
    packet_instances = None
    start_times  = None
    is_scheduled = None
    gap_callback = None

    try:
        input_filename = os.path.basename(file_path)
        print(f"\nProcessing file: {input_filename}")

        df          = data_loader.load_flow_data(file_path)
        hyperperiod = data_loader.compute_hyperperiod(df)
        flows       = model_config.create_flow_dictionaries(df)

        fixed_classes = queue_mapper.run_mapper(flows, hyperperiod, results_folder, input_filename)

        print(" Stage 2 : GCL Scheduling Optimizer")
        print("=" * 60)

        model, solver_params = model_config.setup_gurobi_model(hyperperiod)

        start_times, is_scheduled, packet_instances = model_config.generate_packet_instances(model, flows, hyperperiod, fixed_classes)

        constraints.add_constraints(model, packet_instances, start_times, is_scheduled, solver_params)

        be_packet_count = solver.setup_objective(model, packet_instances, is_scheduled)

        gap_callback = solver.GapStabilityCallback(max_stable_iterations=5, check_interval=8000)

        stats_dict, _ = results_processor.capture_model_stats(model)

        execution_time, gap_history, stopping_reason = solver.solve_model(model, gap_callback)

        results_processor.save_model_stats_to_csv(stats_dict, input_filename, results_folder, execution_time, optimizer="GCL", append=True)

        number_flows = len(df['Flow'])

        results_processor.handle_results(model, packet_instances, start_times, is_scheduled, execution_time, gap_history, stopping_reason, number_flows, input_filename, results_folder)

        return True

    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if model is not None:
            try:
                model.dispose()
            except:
                pass

        if df              is not None: del df
        if flows           is not None: del flows
        if packet_instances is not None: del packet_instances
        if start_times     is not None: del start_times
        if is_scheduled    is not None: del is_scheduled
        if gap_callback    is not None: del gap_callback

        gc.collect()


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python main.py <input_folder>          # run all CSVs in folder")
        print("  python main.py <path/to/file.csv>      # run a single file")
        return

    path = sys.argv[1]

    if os.path.isfile(path):
        if not path.endswith('.csv'):
            print(f"Error: '{path}' is not a CSV file.")
            return

        results_folder = get_results_folder(path)
        os.makedirs(results_folder, exist_ok=True)
        print(f"Results will be saved to: '{results_folder}'")
        process_single_file(path, results_folder)

    elif os.path.isdir(path):
        csv_files = sorted([f for f in os.listdir(path) if f.endswith('.csv')], key=_natural_sort_key)

        if not csv_files:
            print(f"No CSV files found in '{path}'")
            return

        results_folder = get_results_folder(path)
        os.makedirs(results_folder, exist_ok=True)
        print(f"Found {len(csv_files)} CSV files in '{path}'")
        print(f"Results will be saved to: '{results_folder}'")

        stats_folder = os.path.join(results_folder, 'stats')
        pending_files = []
        skipped = 0
        for csv_file in csv_files:
            base_name = os.path.splitext(csv_file)[0]
            stats_filepath = os.path.join(stats_folder, f'model_stats_{base_name}.csv')
            if os.path.exists(stats_filepath):
                skipped += 1
            else:
                pending_files.append(csv_file)

        print(f"Already processed: {skipped}  |  Remaining: {len(pending_files)}")

        if not pending_files:
            print("All files already processed. Nothing to do.")
            return

        csv_files = pending_files

        successful, failed = 0, 0

        for i, csv_file in enumerate(csv_files, 1):
            print(f"\nProcessing {i}/{len(csv_files)}: {csv_file}")
            file_path = os.path.join(path, csv_file)

            if process_single_file(file_path, results_folder):
                successful += 1
            else:
                failed += 1

            gc.collect()

        print("\nBatch Summary")
        print(f"Total     : {len(csv_files)}")
        print(f"Successful: {successful}")
        print(f"Failed    : {failed}")

    else:
        print(f"Error: '{path}' is not a valid file or directory.")


if __name__ == "__main__":
    main()
