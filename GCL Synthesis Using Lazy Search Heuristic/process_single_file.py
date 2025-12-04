import pandas as pd
import math
import os
from functools import reduce

def process_single_file(file_path, output_folder):
    try:
        print(f"Processing file: {file_path}")
        
        filename = os.path.basename(file_path)
        base_filename = os.path.splitext(filename)[0]
        
        df = pd.read_csv(file_path)
        
        required_columns = ['Flow', 'Period', 'Deadline', 'Execution Time', 'Queue', 'w', 'h']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"ERROR: Missing required columns: {missing_columns}")
            return False
        
        number_flows = len(df['Flow'])
        periods = df['Period'].tolist()
        w = df['w'].tolist()
        h = df['h'].tolist()
        k = [w[i] + h[i] for i in range(len(w))]
        products = [k[i] * periods[i] for i in range(len(k))]

        def lcm(a, b):
            return abs(a * b) // math.gcd(a, b)

        H = reduce(lcm, products)
        hyperperiod = H
        
        print(f"Hyperperiod calculated: {hyperperiod}")
        
        flows = []
        for _, row in df.iterrows():
            flows.append({
                "Flow": row["Flow"],
                "Period": int(row["Period"]),
                "Deadline": int(row["Deadline"]),
                "Execution Time": int(row["Execution Time"]),
                "Queue": int(row["Queue"]),
                "w": int(row["w"]),
                "h": int(row["h"])
            })

        packet_instances = []

        for i, flow in enumerate(flows):
            T = flow['Period']
            L = flow['Execution Time']
            D = flow['Deadline']
            base_class = flow['Queue']
            h = flow['h']
            w = flow['w']
            group_size = h + w
            num_instances = hyperperiod // T
            
            for j in range(num_instances):
                arrival = j * T
                deadline = j * T + D
                
                group_index = j % group_size
                queue_class = base_class if group_index < h else 8
                
                packet_instances.append({
                    "Flow": flow["Flow"],
                    "Packet": f'P{flow["Flow"][1:]}_{j+1}',
                    "Arrival": arrival,
                    "Deadline": deadline,
                    "Execution Time": L,
                    "Class": queue_class,
                    "Flow_ID": int(flow["Flow"][1:])
                })

        packet_df = pd.DataFrame(packet_instances)
        print(f"Generated {len(packet_instances)} packet instances")

        queues = {}
        for queue_id in range(1, 9):
            queue_packets = packet_df[packet_df['Class'] == queue_id].copy()
            
            if not queue_packets.empty:
                queue_packets_sorted = queue_packets.sort_values(
                    by=['Arrival', 'Deadline', 'Execution Time', 'Flow_ID'],
                    ascending=[True, True, False, True]
                ).reset_index(drop=True)
                
                queues[queue_id] = queue_packets_sorted.copy()

        def edf_scheduler_fixed(queues, cipg=96, max_time=None):
            working_queues = {}
            for queue_id in range(1, 8):
                if queue_id in queues:
                    working_queues[queue_id] = queues[queue_id].copy().reset_index(drop=True)
            
            schedule = []
            
            t = 0
            
            if max_time is None:
                max_time = hyperperiod
            
            packet_count = 0
            
            while t < max_time:
                all_eligible_packets = []
                
                for queue_id in range(1, 8):
                    if queue_id in working_queues and len(working_queues[queue_id]) > 0:
                        eligible_packets = working_queues[queue_id][
                            working_queues[queue_id]['Arrival'] <= t
                        ]
                        
                        for idx, packet in eligible_packets.iterrows():
                            all_eligible_packets.append({
                                'queue_id': queue_id,
                                'packet_data': packet,
                                'packet_index': idx,
                                'queue_position': idx
                            })
                
                if not all_eligible_packets:
                    next_arrivals = []
                    for queue_id in range(1, 8):
                        if queue_id in working_queues and len(working_queues[queue_id]) > 0:
                            remaining_packets = working_queues[queue_id]
                            if not remaining_packets.empty:
                                next_arrival = remaining_packets['Arrival'].min()
                                if next_arrival > t:
                                    next_arrivals.append(next_arrival)
                    
                    if next_arrivals:
                        t = min(next_arrivals)
                    else:
                        break
                    continue
                
                earliest_deadline_packet = min(all_eligible_packets,
                                             key=lambda x: (x['packet_data']['Deadline'],
                                                           -x['packet_data']['Execution Time'],
                                                           x['packet_data']['Flow_ID']))
                
                selected_queue_id = earliest_deadline_packet['queue_id']
                selected_position = earliest_deadline_packet['queue_position']
                
                if selected_position == 0:
                    packet_to_schedule = earliest_deadline_packet
                else:
                    head_packet_data = working_queues[selected_queue_id].iloc[0]
                    packet_to_schedule = {
                        'queue_id': selected_queue_id,
                        'packet_data': head_packet_data,
                        'packet_index': 0,
                        'queue_position': 0
                    }
                
                packet_data = packet_to_schedule['packet_data']
                queue_id = packet_to_schedule['queue_id']
                
                gate_open = t
                gate_close = t + packet_data['Execution Time']
                
                schedule_entry = {
                    'Packet_ID': packet_data['Packet'],
                    'Flow': packet_data['Flow'],
                    'Queue': queue_id,
                    'Arrival': packet_data['Arrival'],
                    'Deadline': packet_data['Deadline'],
                    'Execution_Time': packet_data['Execution Time'],
                    'Gate_Open': gate_open,
                    'Gate_Close': gate_close,
                    'Schedule_Order': packet_count + 1
                }
                
                schedule.append(schedule_entry)
                
                working_queues[queue_id] = working_queues[queue_id].drop(working_queues[queue_id].index[0]).reset_index(drop=True)
                
                t = gate_close + cipg
                packet_count += 1
                
                remaining_packets = sum(len(q) for q in working_queues.values())
                if remaining_packets == 0:
                    break
            
            return schedule

        schedule = edf_scheduler_fixed(queues, cipg=96, max_time=hyperperiod)
        schedule_df = pd.DataFrame(schedule)
        print(f"EDF scheduler completed: {len(schedule)} packets scheduled")

        busy_periods = []
        for _, packet in schedule_df.iterrows():
            busy_start = packet['Gate_Open']
            busy_end = packet['Gate_Close'] + 96
            busy_periods.append([busy_start, busy_end])

        busy_periods.sort()

        merged_busy = []
        for start, end in busy_periods:
            if not merged_busy or merged_busy[-1][1] < start:
                merged_busy.append([start, end])
            else:
                merged_busy[-1][1] = max(merged_busy[-1][1], end)

        available_intervals = []

        if merged_busy and merged_busy[0][0] > 0:
            available_intervals.append([0, merged_busy[0][0]])

        for i in range(len(merged_busy) - 1):
            gap_start = merged_busy[i][1]
            gap_end = merged_busy[i + 1][0]
            if gap_end > gap_start:
                available_intervals.append([gap_start, gap_end])

        if merged_busy and merged_busy[-1][1] < hyperperiod:
            available_intervals.append([merged_busy[-1][1], hyperperiod])

        if not merged_busy:
            available_intervals.append([0, hyperperiod])

        scheduled_be_packets = []

        if 8 in queues:
            be_packets = queues[8].copy()
            max_execution_time = packet_df['Execution Time'].max()
            
            for interval_idx, (interval_start, interval_end) in enumerate(available_intervals):
                
                guard_band_needed = False
                
                if not schedule_df.empty:
                    before_packets = schedule_df[schedule_df['Gate_Close'] + 96 == interval_start]
                    
                    after_packets = schedule_df[schedule_df['Gate_Open'] == interval_end]
                    
                    if not before_packets.empty and not after_packets.empty:
                        guard_band_needed = True
                
                guard_band_duration = 12000 if guard_band_needed else 0
                
                packets_in_interval = []
                current_time = interval_start
                
                remaining_be_packets = be_packets[~be_packets['Packet'].isin([p['Packet_ID'] for p in scheduled_be_packets])]
                
                for packet_idx, packet in remaining_be_packets.iterrows():
                    packet_id = packet["Packet"]
                    arrival = packet["Arrival"]
                    deadline = packet["Deadline"]
                    exec_time = packet["Execution Time"]
                    
                    gate_open = max(arrival, current_time)
                    gate_close = gate_open + exec_time
                    
                    space_from_start = gate_close - interval_start + 96
                    total_space_with_guard = space_from_start + guard_band_duration
                    
                    if (gate_open >= interval_start and 
                        gate_close <= deadline and
                        total_space_with_guard <= (interval_end - interval_start)):
                        
                        packet_entry = {
                            'Packet_ID': packet_id,
                            'Flow': packet['Flow'],
                            'Queue': 8,
                            'Arrival': arrival,
                            'Deadline': deadline,
                            'Execution_Time': exec_time,
                            'Gate_Open': gate_open,
                            'Gate_Close': gate_close,
                            'Interval_Start': interval_start,
                            'Interval_End': interval_end
                        }
                        
                        packets_in_interval.append(packet_entry)
                        
                        current_time = gate_close + 96
                
                for i, packet_entry in enumerate(packets_in_interval):
                    is_last_in_interval = (i == len(packets_in_interval) - 1)
                    
                    if guard_band_needed and is_last_in_interval:
                        packet_entry.update({
                            'Guard_Band_Needed': True,
                            'Guard_Band_Duration': guard_band_duration,
                            'Guard_Band_Start': packet_entry['Gate_Close'] + 96,
                            'Guard_Band_End': packet_entry['Gate_Close'] + 96 + guard_band_duration
                        })
                    else:
                        packet_entry.update({
                            'Guard_Band_Needed': False,
                            'Guard_Band_Duration': 0,
                            'Guard_Band_Start': None,
                            'Guard_Band_End': None
                        })
                    
                    scheduled_be_packets.append(packet_entry)

        print(f"BE scheduler completed: {len(scheduled_be_packets)} BE packets scheduled")

        scheduled_packet_ids = set()

        if not schedule_df.empty:
            scheduled_packet_ids.update(schedule_df['Packet_ID'].tolist())

        if scheduled_be_packets:
            scheduled_packet_ids.update([p['Packet_ID'] for p in scheduled_be_packets])

        queues_1_7_packets = packet_df[packet_df['Class'].isin([1, 2, 3, 4, 5, 6, 7])]
        unscheduled_1_7 = []
        deadline_misses_1_7 = []

        for _, packet in queues_1_7_packets.iterrows():
            packet_id = packet['Packet']
            if packet_id not in scheduled_packet_ids:
                unscheduled_1_7.append(packet_id)

        if not schedule_df.empty:
            for _, scheduled_packet in schedule_df.iterrows():
                if scheduled_packet['Gate_Close'] > scheduled_packet['Deadline']:
                    deadline_misses_1_7.append({
                        'Packet_ID': scheduled_packet['Packet_ID'], 
                        'Gate_Close': scheduled_packet['Gate_Close'],
                        'Deadline': scheduled_packet['Deadline'],
                        'Miss_Amount': scheduled_packet['Gate_Close'] - scheduled_packet['Deadline']
                    })

        is_scheduleable = len(unscheduled_1_7) == 0 and len(deadline_misses_1_7) == 0

        print("=" * 60)
        print("SCHEDULEABILITY ANALYSIS FOR QUEUES 1-7")
        print("=" * 60)
        print(f"Total packets in queues 1-7: {len(queues_1_7_packets)}")
        print(f"Unscheduled packets in queues 1-7: {len(unscheduled_1_7)}")
        print(f"Deadline misses in queues 1-7: {len(deadline_misses_1_7)}")

        if unscheduled_1_7:
            print(f"\nUnscheduled packets from queues 1-7:")
            for packet_id in unscheduled_1_7:
                packet_info = queues_1_7_packets[queues_1_7_packets['Packet'] == packet_id].iloc[0]
                print(f"  {packet_id} (Queue {packet_info['Class']}): Arrival={packet_info['Arrival']}, Deadline={packet_info['Deadline']}")

        if deadline_misses_1_7:
            print(f"\nDeadline misses in queues 1-7:")
            for miss in deadline_misses_1_7:
                print(f"  {miss['Packet_ID']}: Deadline={miss['Deadline']}, Gate_Close={miss['Gate_Close']}, Miss_Amount={miss['Miss_Amount']}")

        print(f"SCHEDULEABILITY RESULT: {'SCHEDULEABLE' if is_scheduleable else 'UNSCHEDULEABLE'}")

        if 8 in queues:
            total_be_packets = len(queues[8])
            scheduled_be_count = len(scheduled_be_packets)
            print(f"Total BE packets (Queue 8): {total_be_packets}")
            print(f"Scheduled BE packets: {scheduled_be_count}")
            print(f"Dropped BE packets: {total_be_packets - scheduled_be_count}")
        else:
            print("No BE packets (Queue 8) found")

        print("=" * 60)

        if is_scheduleable:
            all_packets = []

            for _, packet in packet_df.iterrows():
                packet_id = packet['Packet']
                is_scheduled = packet_id in scheduled_packet_ids
                
                packet_info = {
                    'Packet_ID': packet_id,
                    'Flow': packet['Flow'],
                    'Queue': packet['Class'],
                    'Arrival': packet['Arrival'],
                    'Deadline': packet['Deadline'],
                    'Execution_Time': packet['Execution Time'],
                    'Scheduled': is_scheduled
                }
                
                if is_scheduled:
                    if packet_id in schedule_df['Packet_ID'].values:
                        scheduled_packet = schedule_df[schedule_df['Packet_ID'] == packet_id].iloc[0]
                        packet_info.update({
                            'Gate_Open': scheduled_packet['Gate_Open'],
                            'Gate_Close': scheduled_packet['Gate_Close'],
                            'Response_Time': scheduled_packet['Gate_Close'] - packet['Arrival']
                        })
                    else:
                        be_packet = next((p for p in scheduled_be_packets if p['Packet_ID'] == packet_id), None)
                        if be_packet:
                            packet_info.update({
                                'Gate_Open': be_packet['Gate_Open'],
                                'Gate_Close': be_packet['Gate_Close'],
                                'Response_Time': be_packet['Gate_Close'] - packet['Arrival']
                            })
                else:
                    packet_info.update({
                        'Gate_Open': None,
                        'Gate_Close': None,
                        'Response_Time': None
                    })
                
                all_packets.append(packet_info)

            complete_packet_df = pd.DataFrame(all_packets)

            scheduled_packets = complete_packet_df[complete_packet_df['Scheduled'] == True].copy()
            unscheduled_packets = complete_packet_df[complete_packet_df['Scheduled'] == False].copy()

            if not scheduled_packets.empty:
                scheduled_packets = scheduled_packets.sort_values('Gate_Open')
            if not unscheduled_packets.empty:
                unscheduled_packets = unscheduled_packets.sort_values('Arrival')

            complete_packet_df = pd.concat([scheduled_packets, unscheduled_packets], ignore_index=True)

            output_csv_path = os.path.join(output_folder, f"all_packet_status_{base_filename}.csv")
            complete_packet_df.to_csv(output_csv_path, index=False)
            print(f"Complete schedule saved to '{output_csv_path}'")
            
            return True
        else:
            return "unschedulable"
            
    except Exception as e:
        print(f"ERROR processing file {file_path}: {str(e)}")
        return False