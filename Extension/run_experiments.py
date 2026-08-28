# run_experiments.py

import os
import glob
import argparse
import numpy as np
import pandas as pd
from plot_params import (
    plot_exps, plot_box, plot_weakly_hard, plot_ilp_hard, plot_bar_response,
    plot_schedulability_ratio, plot_be_admissibility_ratio,
    plot_weakly_hard_schedulability,
)

# ============================================================
#  EXPERIMENT 1 — folder layout per criterion
# ============================================================
# Criterion A (w,h) and Criterion B (m,k) / (m,k)-random results live in
# Experiment_1/<criterion>/flows_<n>/... with two different nesting styles,
# and the Results folder is sometimes cased "Results", sometimes "results".
CRITERIA_EXP1 = {
    'Criterion A-ILP'         : 'criterion-A-ILP',
    'Criterion A-Lazy'        : 'criterion-A-Lazy',
    'Criterion B-ILP'         : 'criterion-B-ILP',
    'Criterion B-Lazy'        : 'criterion-B-Lazy',
    'Criterion B-Random-ILP'  : 'criterion-B-random-ILP',
    'Criterion B-Random-Lazy' : 'criterion-B-random-Lazy',
}


def _exp1_results_dir(criterion, flow_count, u):
    base  = f'Experiment_1/{criterion}/flows_{flow_count}'
    u_dir = f"flows_{flow_count}_u_{u}"

    # Criterion A style: Results/<u_dir>
    candidate = os.path.join(base, 'Results', u_dir)
    if os.path.isdir(candidate):
        return candidate

    # Criterion B style: <u_dir>/Results (or lowercase 'results')
    for res_name in ('Results', 'results'):
        candidate = os.path.join(base, u_dir, res_name)
        if os.path.isdir(candidate):
            return candidate

    return None


def _exp1_schedulability_ratio(criterion, flow_count, u, total_runs=100):
    folder = _exp1_results_dir(criterion, flow_count, u)
    if folder is None:
        print(f"Warning: results folder not found — {criterion} flows_{flow_count} u={u}")
        return 0.0
    count = len(glob.glob(os.path.join(folder, '*.csv')))
    return count / total_runs


def _exp1_be_admissibility_ratio(criterion, flow_count, u):
    folder = _exp1_results_dir(criterion, flow_count, u)
    if folder is None:
        return 0.0

    be_total = 0
    be_sched = 0
    for csv_file in glob.glob(os.path.join(folder, '*.csv')):
        try:
            df = pd.read_csv(csv_file)
        except Exception as e:
            print(f"Error in {os.path.basename(csv_file)}: {e}")
            continue

        if 'Class' in df.columns:  # ILP-style result files
            be_total += (df['Class'] == 8).sum()
            be_sched += ((df['Class'] == 8) & (df['Scheduled'] == 'Yes')).sum()
        elif 'Queue' in df.columns:  # Lazy-style result files
            be_total += (df['Queue'] == 8).sum()
            be_sched += ((df['Queue'] == 8) & (df['Scheduled'] == True)).sum()

    return (be_sched / be_total) if be_total > 0 else 0.0

# ============================================================
#  HELPER
# ============================================================
def compute_be_rates(base_dir):
    csv_files = glob.glob(os.path.join(base_dir, '*.csv'))
    if not csv_files:
        print(f"Warning: no files found at {base_dir}")
        return None, None, None

    rates_f1_f24  = []
    rates_f25_f48 = []
    rates_overall = []

    for csv_file in csv_files:
        try:
            df             = pd.read_csv(csv_file)
            df['Flow_Num'] = df['Flow'].str.extract(r'F(\d+)').astype(int)

            f1_f24   = df[df['Flow_Num'].between(1, 24)]
            be_total = (f1_f24['Class'] == 8).sum()
            be_sched = ((f1_f24['Class'] == 8) & (f1_f24['Scheduled'] == 'Yes')).sum()
            if be_total > 0:
                rates_f1_f24.append(be_sched / be_total * 100)

            f25_f48  = df[df['Flow_Num'].between(25, 48)]
            be_total = (f25_f48['Class'] == 8).sum()
            be_sched = ((f25_f48['Class'] == 8) & (f25_f48['Scheduled'] == 'Yes')).sum()
            if be_total > 0:
                rates_f25_f48.append(be_sched / be_total * 100)

            be_total = (df['Class'] == 8).sum()
            be_sched = ((df['Class'] == 8) & (df['Scheduled'] == 'Yes')).sum()
            if be_total > 0:
                rates_overall.append(be_sched / be_total * 100)

        except Exception as e:
            print(f"Error in {os.path.basename(csv_file)}: {e}")

    avg_f1_f24  = sum(rates_f1_f24)  / len(rates_f1_f24)  if rates_f1_f24  else 0
    avg_f25_f48 = sum(rates_f25_f48) / len(rates_f25_f48) if rates_f25_f48 else 0
    avg_overall = sum(rates_overall) / len(rates_overall)  if rates_overall else 0

    return avg_f1_f24, avg_f25_f48, avg_overall


# ============================================================
#  EXPERIMENT 1a — Schedulability Ratio (Criterion A vs Criterion B vs B-random)
# ============================================================
def run_exp1_schedulability():
    utilization_values = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
    flow_counts         = [16, 32, 48]

    for flow_count in flow_counts:
        records = []
        for u in utilization_values:
            row = {'Utilization': round(u, 2)}
            for col_name, criterion in CRITERIA_EXP1.items():
                row[col_name] = _exp1_schedulability_ratio(criterion, flow_count, u)
            records.append(row)
        data = pd.DataFrame(records)
        print(f"\nflow_count={flow_count}\n{data.to_string()}")
        plot_schedulability_ratio(
            df=data,
            output_dir='Figures/Experiment_1',
            output_name=f'schedulability_ratio_flows_{flow_count}',
        )


# ============================================================
#  EXPERIMENT 1b — Optional Packet Admissibility Ratio (Criterion A vs B vs B-random)
# ============================================================
def run_exp1_be():
    utilization_values = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
    flow_counts         = [16, 32, 48]

    for flow_count in flow_counts:
        records = []
        for u in utilization_values:
            row = {'Utilization': round(u, 2)}
            for col_name, criterion in CRITERIA_EXP1.items():
                row[col_name] = round(_exp1_be_admissibility_ratio(criterion, flow_count, u), 4)
            records.append(row)
        data = pd.DataFrame(records)
        print(f"\nflow_count={flow_count}\n{data.to_string()}")
        plot_be_admissibility_ratio(
            df=data,
            output_dir='Figures/Experiment_1',
            output_name=f'be_packet_ratio_flows_{flow_count}',
        )


# ============================================================
#  EXPERIMENT 2 — Stress Test Box Plot + Table 1
# ============================================================
def run_exp2_stress():
    base_dir_time        = 'Experiment_2/GCL-optimizer/Results/flows_48_u_0.8_{}'
    base_dir_constraints = 'Experiment_2/GCL-optimizer/Results/flows_48_u_0.8_{}/stats'
    base_dir_mapping     = 'Experiment_2/mapper/Results/flows_48_u_0.8_{}/stats'
    packet_vals          = ['p201', 'p252', 'p306', 'p351', 'p402', 'p450', 'p501']
    records              = []

    for p in packet_vals:
        time_folder        = base_dir_time.format(p)
        constraints_folder = base_dir_constraints.format(p)
        mapping_folder      = base_dir_mapping.format(p)

        time_files = glob.glob(os.path.join(time_folder, '*.csv'))
        all_times  = []
        for csv_file in time_files:
            try:
                df = pd.read_csv(csv_file)
                if 'Solver_Execution_Time_Seconds' in df.columns:
                    all_times.append(df['Solver_Execution_Time_Seconds'].iloc[0])
            except Exception as e:
                print(f"Error in {p} time - {os.path.basename(csv_file)}: {e}")

        stats_files  = glob.glob(os.path.join(constraints_folder, '*.csv'))
        min_int_vars = float('inf')
        max_int_vars = float('-inf')
        for csv_file in stats_files:
            try:
                df = pd.read_csv(csv_file)
                if 'Integer_Variables' in df.columns:
                    val          = int(df['Integer_Variables'].iloc[0])
                    min_int_vars = min(min_int_vars, val)
                    max_int_vars = max(max_int_vars, val)
            except Exception as e:
                print(f"Error in {p} stats - {os.path.basename(csv_file)}: {e}")

        # Mapping constraint count is identical across runs for a given packet
        # count (no range) — take it from the first available stats file.
        mapping_int_vars = None
        for csv_file in glob.glob(os.path.join(mapping_folder, '*.csv')):
            try:
                df = pd.read_csv(csv_file)
                if 'Integer_Variables' in df.columns:
                    mapping_int_vars = int(df['Integer_Variables'].iloc[0])
                    break
            except Exception as e:
                print(f"Error in {p} mapping stats - {os.path.basename(csv_file)}: {e}")

        if not all_times:
            print(f"Warning: no solver time data for {p}")
            continue

        times_array   = np.array(all_times)
        q1            = np.percentile(times_array, 25)
        median        = np.percentile(times_array, 50)
        q3            = np.percentile(times_array, 75)
        iqr           = q3 - q1
        lower_bound   = q1 - 1.5 * iqr
        upper_bound   = q3 + 1.5 * iqr
        lower_whisker = np.min(times_array[times_array >= lower_bound])
        upper_whisker = np.max(times_array[times_array <= upper_bound])
        outliers      = times_array[(times_array < lower_bound) | (times_array > upper_bound)].tolist()

        records.append({
            'Packet'              : p,
            'Number of Constrains': [min_int_vars, max_int_vars],
            'q1'                  : q1,
            'median'              : median,
            'q3'                  : q3,
            'lower_whisker'       : lower_whisker,
            'upper_whisker'       : upper_whisker,
            'outlier'             : outliers,
            'min_int_vars'        : min_int_vars,
            'max_int_vars'        : max_int_vars,
            'mapping_int_vars'    : mapping_int_vars,
        })

    data = pd.DataFrame(records)
    print("\n", data[['Packet', 'median', 'q1', 'q3', 'lower_whisker', 'upper_whisker']])

    # --- Table 1 ---
    table1 = pd.DataFrame({
        'Number of Packets'    : [int(p[1:]) for p in data['Packet']],
        'Mapping'              : [row['mapping_int_vars'] for _, row in data.iterrows()],
        'GCL'                  : [f"[{int(row['min_int_vars'])}, {int(row['max_int_vars'])}]"
                                  for _, row in data.iterrows()],
    })
    os.makedirs('Figures/Experiment_2', exist_ok=True)
    table1.to_csv('Figures/Experiment_2/Table_1.csv', index=False)
    print("\nTable 1:")
    print(table1.to_string(index=False))

    # --- Plot ---
    os.makedirs('Figures/Experiment_2', exist_ok=True)
    plot_box(
        data=data,
        output_file='Figures/Experiment_2/Fig_9.pdf',
        base_font_size=20,
        line_scale=1.45,
        plot_size=(9, 6),
        xlabel='Number of Constraints',
        ylabel='Time (s)',
        cutoff=3600,
        ylim=(-5, 4000),
    )


# ============================================================
#  EXPERIMENT 3 — OPAR Table
# ============================================================
def run_exp3_opar():
    # Conf. 1 = No_weight (no weighting distinction — weighted/non-weighted left blank)
    # Conf. 2 = group size 3: Criterion A w_1_h_2_100 / Criterion B m_1_k_3_100
    #           F1-F24 = weighted, F25-F48 = non-weighted
    # Conf. 3 = group size 2: Criterion A w_1_h_1_100 / Criterion B m_1_k_2_100
    #           F25-F48 = weighted, F1-F24 = non-weighted (roles flipped vs Conf. 2)
    _, _, overall_conf1_A = compute_be_rates('Experiment_3/criterion-A/No_weight/Results')
    _, _, overall_conf1_B = compute_be_rates('Experiment_3/criterion-B/No_weight/Results')

    f1_f24_conf2_A, f25_f48_conf2_A, overall_conf2_A = compute_be_rates('Experiment_3/criterion-A/w_1_h_2_100/Results')
    f1_f24_conf2_B, f25_f48_conf2_B, overall_conf2_B = compute_be_rates('Experiment_3/criterion-B/m_1_k_3_100/Results')

    f1_f24_conf3_A, f25_f48_conf3_A, overall_conf3_A = compute_be_rates('Experiment_3/criterion-A/w_1_h_1_100/Results')
    f1_f24_conf3_B, f25_f48_conf3_B, overall_conf3_B = compute_be_rates('Experiment_3/criterion-B/m_1_k_2_100/Results')

    table = pd.DataFrame({
        'Configuration'                    : ['Conf. 1', 'Conf. 2', 'Conf. 3'],
        'Weighted OPAR (%) Criterion A'    : ['-', f"{f1_f24_conf2_A:.2f}",  f"{f25_f48_conf3_A:.2f}"],
        'Weighted OPAR (%) Criterion B'    : ['-', f"{f1_f24_conf2_B:.2f}",  f"{f25_f48_conf3_B:.2f}"],
        'Non-Weighted OPAR (%) Criterion A': ['-', f"{f25_f48_conf2_A:.2f}", f"{f1_f24_conf3_A:.2f}"],
        'Non-Weighted OPAR (%) Criterion B': ['-', f"{f25_f48_conf2_B:.2f}", f"{f1_f24_conf3_B:.2f}"],
        'Total OPAR (%) Criterion A'       : [f"{overall_conf1_A:.2f}", f"{overall_conf2_A:.2f}", f"{overall_conf3_A:.2f}"],
        'Total OPAR (%) Criterion B'       : [f"{overall_conf1_B:.2f}", f"{overall_conf2_B:.2f}", f"{overall_conf3_B:.2f}"],
    })
    print(f"\n{table.to_string(index=False)}")

    os.makedirs('Figures/Experiment_3', exist_ok=True)
    table.to_csv('Figures/Experiment_3/Table_2.csv', index=False)
    print("Saved: Figures/Experiment_3/Table_2.csv")

# ============================================================
#  EXPERIMENT 4 — ILP vs ILP_Hard
# ============================================================
def run_exp4_ilp_hard():
    base_dir_ilp      = 'Experiment_4/ILP/Results/'
    base_dir_ilp_hard = 'Experiment_4/ILP_Hard/Results/'
    utilization_values = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
    flow_count         = 48

    records_mandatory = []
    records_be        = []

    for u in utilization_values:
        folder_name  = f"flows_{flow_count}_u_{u}"

        # --- ILP ---
        ilp_folder   = os.path.join(base_dir_ilp, folder_name)
        ilp_files    = glob.glob(os.path.join(ilp_folder, '*.csv'))
        ilp_be_total = 0
        ilp_be_sched = 0
        for file_path in ilp_files:
            try:
                df            = pd.read_csv(file_path)
                ilp_be_total += (df['Class'] == 8).sum()
                ilp_be_sched += ((df['Class'] == 8) & (df['Scheduled'] == 'Yes')).sum()
            except Exception as e:
                print(f"Error ILP {os.path.basename(file_path)}: {e}")
        ilp_mandatory_pct = 100.0
        ilp_be_pct        = (ilp_be_sched / ilp_be_total * 100) if ilp_be_total > 0 else 0

        # --- ILP_Hard ---
        hard_folder          = os.path.join(base_dir_ilp_hard, folder_name)
        hard_files           = glob.glob(os.path.join(hard_folder, '*.csv'))
        hard_mandatory_rates = []
        hard_be_rates        = []

        for file_path in hard_files:
            try:
                df              = pd.read_csv(file_path)
                total_mandatory = 0
                total_be        = 0
                mandatory_met   = 0
                be_met          = 0
                flows_sorted    = sorted(df['Flow'].unique(), key=lambda x: int(x[1:]))

                for flow in flows_sorted:
                    flow_packets            = df[df['Flow'] == flow].copy()
                    flow_packets['seq_num'] = flow_packets['Packet'].str.extract(r'P\d+_(\d+)').astype(int)
                    flow_packets            = flow_packets.sort_values('seq_num')

                    for idx, (_, packet) in enumerate(flow_packets.iterrows()):
                        is_mandatory = (idx % 3) in [0, 1]
                        if is_mandatory:
                            total_mandatory += 1
                            if packet['Deadline_Met'] == 'Yes':
                                mandatory_met += 1
                        else:
                            total_be += 1
                            if packet['Deadline_Met'] == 'Yes':
                                be_met += 1

                if total_mandatory > 0:
                    hard_mandatory_rates.append(mandatory_met / total_mandatory * 100)
                if total_be > 0:
                    hard_be_rates.append(be_met / total_be * 100)

            except Exception as e:
                print(f"Error ILP_Hard {os.path.basename(file_path)}: {e}")

        hard_mandatory_pct = sum(hard_mandatory_rates) / len(hard_mandatory_rates) if hard_mandatory_rates else 0
        hard_be_pct        = sum(hard_be_rates)        / len(hard_be_rates)        if hard_be_rates        else 0

        print(f"u={u}: ILP mandatory={ilp_mandatory_pct:.1f}%, Optional={ilp_be_pct:.2f}% | "
              f"ILP_Hard mandatory={hard_mandatory_pct:.2f}%, Optional={hard_be_pct:.2f}%")

        records_mandatory.append({
            'Utilization'          : round(u, 2),
            'ILP (Reserved)'       : ilp_mandatory_pct,
            'ILP_Hard (No Reserve)': hard_mandatory_pct,
        })
        records_be.append({
            'Utilization'          : round(u, 2),
            'ILP (Reserved)'       : ilp_be_pct,
            'ILP_Hard (No Reserve)': hard_be_pct,
        })

    data_mandatory = pd.DataFrame(records_mandatory)
    data_be        = pd.DataFrame(records_be)
    print("\nMandatory:\n", data_mandatory)
    print("\nOptional:\n",        data_be)

    os.makedirs('Figures/Experiment_4', exist_ok=True)
    plot_ilp_hard(
        df=data_mandatory,
        x_col='Utilization',
        y_cols=['ILP (Reserved)', 'ILP_Hard (No Reserve)'],
        labels=['Reserved', 'No Reserved'],
        output_file='Figures/Experiment_4/Fig_10_a.pdf',
        base_font_size=18, plot_size=(4.5, 3.25),
        xlabel='Utilization', ylabel='Admissibility (%)',
        xticks=[0.4, 0.6, 0.8, 1.0, 1.2],
        yticks=[0, 25, 50, 75, 100], ylim=(-5, 105),
    )
    plot_ilp_hard(
        df=data_be,
        x_col='Utilization',
        y_cols=['ILP (Reserved)', 'ILP_Hard (No Reserve)'],
        labels=['Reserved', 'No Reserved'],
        output_file='Figures/Experiment_4/Fig_10_b.pdf',
        base_font_size=18, plot_size=(4.5, 3.25),
        xlabel='Utilization', ylabel='Admissibility (%)',
        xticks=[0.4, 0.6, 0.8, 1.0, 1.2],
        yticks=[0, 25, 50, 75, 100], ylim=(-5, 105),
    )


# ============================================================
#  EXPERIMENT 5 — Weakly Hard Schedulability
# ============================================================
# All Experiment_5 configs use a flat layout: Experiment_5/<folder>/Results/flows_<n>_u_<u>/
CRITERIA_EXP5 = {
    'Hard'              : 'hard',
    'Criterion A (1,2)' : 'criterion-A-1_2',
    'Criterion A (1,3)' : 'criterion-A-1_3',
    'Criterion A (2,3)' : 'criterion-A-2_3',
    'Criterion B (1,2)' : 'criterion-B-1_2',
    'Criterion B (1,3)' : 'criterion-B-1_3',
    'Criterion B (2,3)' : 'criterion-B-2_3',
}


def _exp5_results_dir(folder, flow_count, u):
    candidate = f'Experiment_5/{folder}/Results/flows_{flow_count}_u_{u}'
    return candidate if os.path.isdir(candidate) else None


def _exp5_schedulability_ratio(folder, flow_count, u, total_runs=100):
    results_dir = _exp5_results_dir(folder, flow_count, u)
    if results_dir is None:
        print(f"Warning: results folder not found — {folder} flows_{flow_count} u={u} (treating as 0.0)")
        return 0.0
    count = len(glob.glob(os.path.join(results_dir, '*.csv')))
    return count / total_runs


def run_exp5_weakly_hard():
    utilization_values = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
    flow_count          = 48
    records             = []

    for u in utilization_values:
        row = {'Utilization': round(u, 2)}
        for col_name, folder in CRITERIA_EXP5.items():
            row[col_name] = _exp5_schedulability_ratio(folder, flow_count, u)
        records.append(row)

    data = pd.DataFrame(records)
    print(data.to_string())

    plot_weakly_hard_schedulability(
        df=data,
        output_dir='Figures/Experiment_5',
        output_name='schedulability_non_m_k',
    )


# ============================================================
#  HARDWARE EXPERIMENTS
# ============================================================
def run_hardware_exps():
    xticks = [1, 50, 100, 150, 200]
    yticks = [0, 0.5, 1.0]
    os.makedirs('Figures/Hardware_Exps', exist_ok=True)

    plot_bar_response(
        df=pd.read_csv('Hardware_Experiments/results_heuristic.csv'),
        output_file='Figures/Hardware_Exps/Fig_13_a.pdf',
        xticks=xticks, yticks=yticks,
        apply_class_override=False,
    )
    plot_bar_response(
        df=pd.read_csv('Hardware_Experiments/results_7q.csv'),
        output_file='Figures/Hardware_Exps/Fig_13_b.pdf',
        xticks=xticks, yticks=yticks,
        apply_class_override=False,
    )
    plot_bar_response(
        df=pd.read_csv('Hardware_Experiments/results_8q.csv'),
        output_file='Figures/Hardware_Exps/Fig_13_c.pdf',
        xticks=xticks, yticks=yticks,
        apply_class_override=True,
    )


# ============================================================
#  MAIN — argument parser
# ============================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run experiments and generate figures.')
    parser.add_argument(
        'experiment',
        choices=['exp1', 'exp2', 'exp3', 'exp4', 'exp5', 'hardware', 'all'],
        help='Which experiment to run'
    )
    args = parser.parse_args()

    if args.experiment == 'exp1':
        run_exp1_schedulability()
        run_exp1_be()
    elif args.experiment == 'exp2':
        run_exp2_stress()
    elif args.experiment == 'exp3':
        run_exp3_opar()
    elif args.experiment == 'exp4':
        run_exp4_ilp_hard()
    elif args.experiment == 'exp5':
        run_exp5_weakly_hard()
    elif args.experiment == 'hardware':
        run_hardware_exps()
    elif args.experiment == 'all':
        run_exp1_schedulability()
        run_exp1_be()
        run_exp2_stress()
        run_exp3_opar()
        run_exp4_ilp_hard()
        run_exp5_weakly_hard()
        run_hardware_exps()