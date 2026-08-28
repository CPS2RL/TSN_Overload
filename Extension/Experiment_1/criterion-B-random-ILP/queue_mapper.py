import os
import re
import random
from collections import defaultdict

import pandas as pd


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


def _build_random_mapping(flows: list[dict], H: int, seed: int) -> dict:
    rng = random.Random(seed)
    assignment = {}

    for f in flows:
        T   = f["Period"]
        m   = f["m"]
        k   = f["k"]
        num = H // T
        mandatory_count = k - m

        base = [1] * mandatory_count + [0] * m
        rng.shuffle(base)

        flow_id = f["Flow"]
        for j in range(num):
            pkt_id = f'P{flow_id[1:]}_{j + 1}'
            assignment[pkt_id] = bool(base[j % k])

    return assignment


def _extract_results(packets: list[dict], assignment: dict) -> pd.DataFrame:
    rows = []
    for p in packets:
        pid     = p["id"]
        is_mand = assignment[pid]
        ptype   = "M" if is_mand else "O"
        rows.append({
            "Queue":     p["Queue"],
            "Flow":      p["Flow"],
            "Packet_ID": pid,
            "Type":      ptype,
            "Arrival":   p["Arrival"],
            "Deadline":  p["Deadline"],
            "Exec":      p["Exec"],
        })
    return (pd.DataFrame(rows)
              .sort_values(["Queue", "Flow", "Arrival"])
              .reset_index(drop=True))


def _save_mapping(df: pd.DataFrame, results_folder: str, csv_stem: str) -> None:
    mapping_folder = os.path.join(results_folder, "mapping")
    os.makedirs(mapping_folder, exist_ok=True)
    path = os.path.join(mapping_folder, f"mapping_{csv_stem}.csv")
    df.to_csv(path, index=False)
    print(f"Mapping saved → {path}")


def run_mapper(flows: list[dict], H: int,
               results_folder: str, input_filename: str,
               seed: int = 42) -> dict:
    print("\n" + "=" * 60)
    print(" Stage 1 : Random (m,k) Mapping")
    print("=" * 60)

    packets    = _generate_packets(flows, H)
    assignment = _build_random_mapping(flows, H, seed)

    print(f"Flows: {len(flows)}  |  Packets: {len(packets)}  |  H: {H}  |  Seed: {seed}")

    mandatory_count = sum(1 for v in assignment.values() if v)
    optional_count  = len(assignment) - mandatory_count
    print(f"Mandatory: {mandatory_count}  |  Optional: {optional_count}")

    fixed_classes = {}
    for p in packets:
        pid = p["id"]
        fixed_classes[pid] = p["base_class"] if assignment[pid] else 8

    df       = _extract_results(packets, assignment)
    csv_stem = os.path.splitext(input_filename)[0]
    _save_mapping(df, results_folder, csv_stem)

    print("=" * 60)
    print(" Stage 1 complete")
    print("=" * 60 + "\n")

    return fixed_classes
