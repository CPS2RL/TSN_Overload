import os
import gc
import re
import sys
import data_loader
import model_config
import queue_mapper


def _natural_sort_key(filename):
    """Split filename into (text, number) chunks for correct numeric ordering.
    e.g. run_01, run_02, ..., run_10  instead of run_01, run_10, run_02."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', filename)]


def process_single_file(file_path, results_folder):
    flows = None

    try:
        input_filename = os.path.basename(file_path)
        print(f"\nProcessing file: {input_filename}")

        df          = data_loader.load_flow_data(file_path)
        hyperperiod = data_loader.compute_hyperperiod(df)
        flows       = model_config.create_flow_dictionaries(df)

        # ── Stage 1 only: Queue-local mapping optimizer ───────────────────
        queue_mapper.run_mapper(flows, hyperperiod, results_folder, input_filename)

        return True

    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if flows is not None: del flows
        gc.collect()


def get_results_folder(path):
    """
    Derives the results folder from the input path.

    File:   input_csvs-mk/flows_48_u_0.8_p201/flows_48_u_0.8_p201_01.csv
              -> Results/flows_48_u_0.8_p201/
    Folder: input_csvs-mk/flows_48_u_0.8_p201/
              -> Results/flows_48_u_0.8_p201/
    """
    norm = os.path.normpath(path)
    parts = norm.split(os.sep)

    if os.path.isfile(path):
        subfolder = parts[-2] if len(parts) >= 2 else ''
    elif os.path.isdir(path):
        subfolder = parts[-1]
    else:
        subfolder = ''

    return os.path.join('Results', subfolder) if subfolder else 'Results'


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python main_mapper.py <input_folder>          # run all CSVs in folder")
        print("  python main_mapper.py <path/to/file.csv>      # run a single file")
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

        # ── Resume: skip files already processed ─────────────────────────
        # A file is "processed" once its mapping output exists.
        mapping_folder = os.path.join(results_folder, 'mapping')
        pending_files = []
        skipped = 0
        for csv_file in csv_files:
            base_name = os.path.splitext(csv_file)[0]
            mapping_filepath = os.path.join(mapping_folder, f'mapping_{base_name}.csv')
            if os.path.exists(mapping_filepath):
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
