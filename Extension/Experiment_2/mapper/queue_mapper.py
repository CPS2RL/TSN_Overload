import math
import os
import re
import time
from collections import defaultdict
from functools import reduce

import pandas as pd
import gurobipy as gp
from gurobipy import GRB

import results_processor


def _lcm(a: int, b: int) -> int:
    return abs(a * b) // math.gcd(a, b)


def _generate_packets(flows: list[dict], H: int) -> list[dict]:
    packets = []
    for f in flows:
        T   = f["Period"]
        D   = f["Deadline"]
        C   = f["Execution Time"]
        q   = f["Queue"]
        m   = f["m"]
        k   = f["k"]
        num = H // T
        match = re.search(r'\d+', f["Flow"])
        prio  = int(match.group()) if match else 999

        for j in range(num):
            pkt_id = f'P{f["Flow"][1:]}_{j + 1}'
            packets.append({
                "id":            pkt_id,
                "Flow":          f["Flow"],
                "Flow_Priority": prio,
                "Queue":         q,
                "base_class":    q,
                "Arrival":       j * T,
                "Deadline":      j * T + D,
                "Exec":          C,
                "m":             m,
                "k":             k,
            })
    return packets


def _build_model(packets: list[dict], H: int):
    model = gp.Model("QueueMapper")
    model.setParam("OutputFlag", 1)
    model.setParam("MIPGap", 0.01)
    model.setParam("MIPFocus", 1)
    model.setParam("Threads", 0)
    model.setParam("Cuts", 3)
    model.setParam("Presolve", 2)
    model.setParam("TimeLimit", 3600)
    model.setParam("SolutionLimit", 1)

    tag   = {}
    start = {}
    f_var = {}

    for p in packets:
        pid = p["id"]
        tag[pid]   = model.addVar(vtype=GRB.BINARY,     name=f"tag_{pid}")
        start[pid] = model.addVar(vtype=GRB.INTEGER, lb=0, ub=H, name=f"start_{pid}")
        f_var[pid] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, ub=H, name=f"f_{pid}")

    model.update()

    flow_pkts: dict[str, list] = defaultdict(list)
    for p in packets:
        flow_pkts[p["Flow"]].append(p)

    for flow_name, fpkts in flow_pkts.items():
        N           = len(fpkts)
        m           = fpkts[0]["m"]
        k           = fpkts[0]["k"]
        window_size = k
        mandatory   = k - m
        for j in range(N):
            window_ids = [fpkts[(j + l) % N]["id"] for l in range(window_size)]
            model.addConstr(gp.quicksum(tag[pid] for pid in window_ids) == mandatory, name=f"mk_{flow_name}_{j}")

    for p in packets:
        pid = p["id"]
        arr = p["Arrival"]
        dl  = p["Deadline"]
        C   = p["Exec"]
        model.addConstr(start[pid] >= arr - H * (1 - tag[pid]),       name=f"arr_{pid}")
        model.addConstr(start[pid] <= (dl - C) + H * (1 - tag[pid]), name=f"dl_{pid}")

    queue_groups: dict[int, list] = defaultdict(list)
    for p in packets:
        queue_groups[p["Queue"]].append(p)

    pair_idx = 0
    for q_pkts in queue_groups.values():
        for i in range(len(q_pkts)):
            for j in range(i + 1, len(q_pkts)):
                p   = q_pkts[i]
                q   = q_pkts[j]
                pid = p["id"]
                qid = q["id"]
                relax = H * (2 - tag[pid] - tag[qid])

                if p["Arrival"] < q["Arrival"]:
                    model.addConstr(start[pid] + p["Exec"] <= start[qid] + relax, name=f"fifo_{pair_idx}")
                elif q["Arrival"] < p["Arrival"]:
                    model.addConstr(start[qid] + q["Exec"] <= start[pid] + relax, name=f"fifo_{pair_idx}")
                else:
                    p_dl, q_dl = p["Deadline"], q["Deadline"]
                    p_ex, q_ex = p["Exec"],     q["Exec"]
                    p_fp, q_fp = p["Flow_Priority"], q["Flow_Priority"]

                    if   p_dl != q_dl:   p_first = p_dl < q_dl
                    elif p_ex != q_ex:   p_first = p_ex > q_ex
                    else:                p_first = p_fp < q_fp

                    if p_first:
                        model.addConstr(start[pid] + p["Exec"] <= start[qid] + relax, name=f"tiebreak_pq_{pair_idx}")
                    else:
                        model.addConstr(start[qid] + q["Exec"] <= start[pid] + relax, name=f"tiebreak_qp_{pair_idx}")
                pair_idx += 1

    for p in packets:
        pid = p["id"]
        model.addConstr(f_var[pid] <= H * tag[pid],                     name=f"mcc1_{pid}")
        model.addConstr(f_var[pid] >= start[pid] - H * (1 - tag[pid]), name=f"mcc2_{pid}")
        model.addConstr(f_var[pid] <= start[pid],                       name=f"mcc3_{pid}")

    obj = gp.quicksum(tag[p["id"]] * p["Deadline"] - f_var[p["id"]] - tag[p["id"]] * p["Exec"] for p in packets)
    model.setObjective(obj, GRB.MAXIMIZE)

    return model, tag, start, f_var


def _extract_results(packets: list[dict], tag: dict, start: dict) -> pd.DataFrame:
    rows = []
    for p in packets:
        pid     = p["id"]
        is_mand = int(tag[pid].X + 0.5) == 1
        ptype   = "M" if is_mand else "O"
        if is_mand:
            s_val  = int(start[pid].X + 0.5)
            finish = s_val + p["Exec"]
            slack  = p["Deadline"] - finish
        else:
            s_val = finish = slack = None
        rows.append({
            "Queue":     p["Queue"],
            "Flow":      p["Flow"],
            "Packet_ID": pid,
            "Type":      ptype,
            "Arrival":   p["Arrival"],
            "Deadline":  p["Deadline"],
            "Exec":      p["Exec"],
            "Start":     s_val,
            "Finish":    finish,
            "Slack":     slack,
        })
    return pd.DataFrame(rows).sort_values(["Queue", "Flow", "Arrival"]).reset_index(drop=True)


def _save_mapping(df: pd.DataFrame, results_folder: str, csv_stem: str) -> None:
    mapping_folder = os.path.join(results_folder, "mapping")
    os.makedirs(mapping_folder, exist_ok=True)
    path = os.path.join(mapping_folder, f"mapping_{csv_stem}.csv")
    df.to_csv(path, index=False)
    print(f"Mapping saved → {path}")


def run_mapper(flows: list[dict], H: int, results_folder: str, input_filename: str) -> dict:
    print("\n" + "=" * 60)
    print(" Stage 1 : Queue-Local Mapping Optimizer")
    print("=" * 60)

    packets = _generate_packets(flows, H)
    print(f"Flows: {len(flows)}  |  Packets: {len(packets)}  |  H: {H}")

    model, tag, start, f_var = _build_model(packets, H)

    t0      = time.time()
    model.optimize()
    elapsed = time.time() - t0

    valid_statuses = [GRB.OPTIMAL, GRB.SUBOPTIMAL, GRB.TIME_LIMIT, GRB.INTERRUPTED, GRB.NODE_LIMIT, GRB.SOLUTION_LIMIT]

    if model.status not in valid_statuses or model.SolCount == 0:
        if model.status == GRB.INFEASIBLE:
            print("Mapper infeasible")
        raise RuntimeError(f"Mapper found no solution. Gurobi status: {model.status}")

    print(f"Mapper objective : {model.objVal:.2f}")
    print(f"Mapper solve time: {elapsed:.2f}s")

    fixed_classes = {}
    for p in packets:
        pid     = p["id"]
        is_mand = int(tag[pid].X + 0.5) == 1
        fixed_classes[pid] = p["base_class"] if is_mand else 8

    df       = _extract_results(packets, tag, start)
    csv_stem = os.path.splitext(input_filename)[0]
    _save_mapping(df, results_folder, csv_stem)

    stats_dict, _ = results_processor.capture_model_stats(model)
    results_processor.save_model_stats_to_csv(stats_dict, input_filename, results_folder, elapsed, optimizer="Mapping", append=False)

    model.dispose()

    print("=" * 60)
    print(" Stage 1 complete")
    print("=" * 60 + "\n")

    return fixed_classes