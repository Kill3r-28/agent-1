import sys
from tools import read_csv, save_csv, load_remarks

def apply_remarks(csv_filename: str):
    input_path   = f"input/{csv_filename}"
    remarks_path = f"review-remarks/{csv_filename.replace('.csv', '-review-remarks.json')}"
    output_path  = f"output/{csv_filename.replace('.csv', '-reviewed.csv')}"

    print(f"\n📂  Input  : {input_path}")
    print(f"📝  Remarks: {remarks_path}")
    print(f"💾  Output : {output_path}\n")

    mcqs    = read_csv(input_path)
    changes = load_remarks(remarks_path)

    print(f"[Apply] Loaded {len(changes)} remark(s)")
    save_csv(output_path, mcqs, changes)
    print(f"\n✅  Done! Output saved to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 apply.py <csv-filename>")
        print("Example: python3 apply.py sql-mcqs.csv")
    else:
        apply_remarks(sys.argv[1])