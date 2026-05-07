import csv
import json
import re

# ── Content Type Detection ────────────────────────────────────
def detect_content_type(content: str) -> str:
    """Detect whether question content is HTML, MARKDOWN, or TEXT."""
    if re.search(r'<[a-zA-Z][^>]*>', content):
        return "HTML"
    elif re.search(r'```|^\|.+\|$|^#{1,6} ', content, re.MULTILINE):
        return "MARKDOWN"
    else:
        return "TEXT"


# ── Options Parser ────────────────────────────────────────────
def parse_options(options_data: str) -> list[dict]:
    """Parse the JSON string in Options Data column."""
    try:
        return json.loads(options_data)
    except json.JSONDecodeError:
        print(f"  [Warning] Could not parse options: {options_data[:60]}...")
        return []


def get_correct_answer(options: list[dict]) -> str:
    """Extract the correct answer text from options."""
    for opt in options:
        if opt.get("is_correct_option") == 1:
            return opt.get("option_content", "")
    return "NOT FOUND"


# ── CSV Reader ────────────────────────────────────────────────
def read_csv(filepath: str) -> list[dict]:
    """Read MCQs from your CSV format and enrich with parsed data."""
    mcqs = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            options = parse_options(row["Options Data"])
            mcqs.append({
                "question_id":    row["Question ID"],
                "question":       row["Question Content"],
                "content_type":   detect_content_type(row["Question Content"]),
                "options":        options,
                "correct_answer": get_correct_answer(options),
                "raw_options":    row["Options Data"]  # keep original for saving
            })
    print(f"[Tool] Read {len(mcqs)} MCQs from {filepath}")
    return mcqs


# ── Batch Maker ───────────────────────────────────────────────
def make_batches(mcqs: list[dict], batch_size: int = 5) -> list[list[dict]]:
    """Split MCQs into smaller batches for the agent to process."""
    batches = []
    for i in range(0, len(mcqs), batch_size):
        batches.append(mcqs[i:i + batch_size])
    print(f"[Tool] Created {len(batches)} batches of up to {batch_size} MCQs each")
    return batches


# ── Summary Display ───────────────────────────────────────────
def show_summary(changes: list[dict]) -> None:
    """Display a readable summary of all proposed changes."""
    print("\n" + "="*65)
    print("📋  REVIEW SUMMARY — Proposed Changes")
    print("="*65)

    if not changes:
        print("✅  No changes needed. All MCQs look good!")
        return

    for i, change in enumerate(changes, 1):
        print(f"\n[{i}] ID      : {change.get('question_id', 'N/A')}")
        print(f"    Type    : {change.get('content_type', 'N/A')}")
        print(f"    Question: {str(change.get('question', ''))[:80]}...")
        print(f"    Issue   : {change.get('issue')}")
        print(f"    Fix     : {change.get('fix')}")

    print("\n" + "="*65)
    print(f"  Total issues found: {len(changes)}")
    print("="*65)


# ── CSV Saver ─────────────────────────────────────────────────
def save_csv(filepath: str, original_mcqs: list[dict], changes: list[dict]) -> str:
    """
    Save reviewed MCQs back in the original CSV format.
    Only changed MCQs get updated — rest stay exactly as they were.
    """
    # Build a lookup of changes by question_id
    changes_by_id = {c["question_id"]: c for c in changes}

    rows = []
    for mcq in original_mcqs:
        qid = mcq["question_id"]
        if qid in changes_by_id:
            change = changes_by_id[qid]
            # Use updated options if provided, else keep original
            updated_options = change.get("updated_options", mcq["options"])
            rows.append({
                "Question ID":      qid,
                "Question Content": change.get("updated_question", mcq["question"]),
                "Options Data":     json.dumps(updated_options)
            })
        else:
            rows.append({
                "Question ID":      qid,
                "Question Content": mcq["question"],
                "Options Data":     mcq["raw_options"]
            })

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Question ID", "Question Content", "Options Data"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"[Tool] Saved {len(rows)} MCQs to {filepath}")
    return f"✅ Saved to {filepath}"

def save_remarks(filepath: str, changes: list[dict]) -> str:
    """Save review remarks to a JSON file for manual inspection/editing."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(changes, f, indent=2)
    print(f"[Tool] Remarks saved to {filepath}")
    return filepath


def load_remarks(filepath: str) -> list[dict]:
    """Load review remarks from JSON file (after manual edits if any)."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)