import os
import json
import time
from main import analyze_file

def process_dataset(dataset_dir, output_report_file):
    print(f"\nStarting analysis on dataset: {dataset_dir}")
    results = []
    success_count = 0
    error_count = 0
    total_folded = 0
    total_eliminated = 0
    total_unreachable = 0
    start_time = time.time()

    for root, _, files in os.walk(dataset_dir):
        for file in files:
            if file.endswith(".c"):
                filepath = os.path.join(root, file)
                print(f"Analyzing: {filepath}...", end=" ")
                result = analyze_file(filepath)
                
                if result["status"] == "success":
                    print(f"SUCCESS (Folded: {result['constants_folded']}, Eliminated: {result['dead_code_removed']}, Unreachable: {result['unreachable_blocks_removed']})")
                    success_count += 1
                    total_folded += result['constants_folded']
                    total_eliminated += result['dead_code_removed']
                    total_unreachable += result['unreachable_blocks_removed']
                else:
                    print(f"FAILED: {result['error_msg']}")
                    error_count += 1
                results.append(result)

    end_time = time.time()
    summary = {
        "dataset": dataset_dir,
        "total_files_processed": success_count + error_count,
        "successful_parses": success_count,
        "failed_parses": error_count,
        "total_constants_folded": total_folded,
        "total_dead_code_removed": total_eliminated,
        "total_unreachable_blocks_removed": total_unreachable,
        "time_taken_seconds": round(end_time - start_time, 2)
    }

    with open(output_report_file, 'w') as f:
        json.dump(summary, f, indent=4)

    print("\n" + "="*50)
    print(f"Dataset {dataset_dir} COMPLETE")
    print(f"Successes: {summary['successful_parses']} | Failures: {summary['failed_parses']}")
    print(f"Total Folded: {summary['total_constants_folded']}")
    print(f"Total Eliminated: {summary['total_dead_code_removed']}")
    print(f"Total Unreachable Removed: {summary['total_unreachable_blocks_removed']}")
    print("="*50)

if __name__ == "__main__":
    codenet_files = os.listdir("datasets/codenet") if os.path.exists("datasets/codenet") else []
    svcomp_files = os.listdir("datasets/sv_comp") if os.path.exists("datasets/sv_comp") else []

    if codenet_files:
        process_dataset("datasets/codenet", "codenet_report.json")
    else:
        print("Skipping CodeNet: No files found in datasets/codenet")

    if svcomp_files:
        process_dataset("datasets/sv_comp", "sv_comp_report.json")
    else:
         print("Skipping SV-COMP: No files found in datasets/sv_comp")