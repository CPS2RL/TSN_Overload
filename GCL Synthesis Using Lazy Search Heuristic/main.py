import os
import gc
from process_single_file import process_single_file

def main():
    input_file = 'flows_48/flows_48_u_1.2_1.csv'
    output_folder = 'Results/flows_48_u_1.2'
    
    os.makedirs(output_folder, exist_ok=True)
    
    if not os.path.exists(input_file):
        print(f"File not found: {input_file}")
        return
    
    result = process_single_file(input_file, output_folder)
    
    if result is not False:
        if result is True:
            print(f"\nSystem is SCHEDULABLE")
        else:
            print(f"\nSystem is UNSCHEDULABLE")
    else:
        print(f"\nProcessing FAILED")
    
    gc.collect()

if __name__ == "__main__":
    main()