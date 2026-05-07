import anthropic
import json
import os
from tools import read_csv, make_batches, show_summary, save_csv, save_remarks, load_remarks

# ── Prompt Loader ─────────────────────────────────────────────
def load_prompt(subject: str) -> str:
    """Load the subject-specific prompt from prompts/ folder."""
    prompt_path = f"prompts/{subject}.txt"
    if os.path.exists(prompt_path):
        with open(prompt_path, "r") as f:
            print(f"[Agent] Loaded prompt: {prompt_path}")
            return f.read()
    else:
        print(f"[Agent] No specific prompt found for '{subject}', using default.")
        return open("prompts/default.txt").read()


# ── Detect subject from filename ──────────────────────────────
def detect_subject(filename: str) -> str:
    """
    Auto-detect subject from CSV filename.
    e.g. 'sql-mcqs.csv' → 'sql'
         'javascript-mcqs.csv' → 'javascript'
    """
    base = os.path.basename(filename)        # 'sql-mcqs.csv'
    name = base.replace(".csv", "")          # 'sql-mcqs'
    subject = name.split("-")[0].lower()     # 'sql'
    return subject


# ── JSON Parser ───────────────────────────────────────────────
def parse_response(raw: str) -> list[dict]:
    """Safely parse model response — 3 layers of fallback."""
    cleaned = raw.strip()

    # Layer 1: strip markdown code fences if present
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()

    # Layer 2: find the JSON array boundaries
    start = cleaned.find("[")
    end   = cleaned.rfind("]") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON array found in response")

    json_str = cleaned[start:end]

    # Layer 3: try parsing
    return json.loads(json_str)


# ── Main Agent Loop ───────────────────────────────────────────
def run_agent(csv_filename: str, subject: str):
    input_path  = f"input/{csv_filename}"
    output_path = f"output/{csv_filename.replace('.csv', '-reviewed.csv')}"

    print(f"\n🤖  MCQ Review Agent Starting...")
    print(f"📂  Input  : {input_path}")
    print(f"🎯  Subject: {subject.upper()}")
    print(f"💾  Output : {output_path}\n")

    # Step 1: Load prompt & MCQs
    system_prompt = load_prompt(subject)
    client        = anthropic.Anthropic()
    mcqs          = read_csv(input_path)
    batches       = make_batches(mcqs, batch_size=5)

    all_changes  = []
    failed_batch = []
    total        = len(batches)

    # Step 2: Process each batch
    for i, batch in enumerate(batches, 1):
        print(f"[Agent] Batch {i}/{total} "
              f"(Q{(i-1)*5+1}–{min(i*5, len(mcqs))})...",
              end=" ", flush=True)

        payload = []
        for mcq in batch:
            payload.append({
                "question_id":    mcq["question_id"],
                "question":       mcq["question"],
                "content_type":   mcq["content_type"],
                "options":        mcq["options"],
                "correct_answer": mcq["correct_answer"]
            })

        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4096,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": json.dumps(payload, indent=2)}
                ]
            )
            changes = parse_response(response.content[0].text)
            if changes:
                all_changes.extend(changes)
                print(f"⚠️  {len(changes)} issue(s) found")
            else:
                print("✅  Clean")

        except (ValueError, json.JSONDecodeError):
            print(f"⚠️  Parse failed — will retry")
            failed_batch.append((i, batch))

    # Step 3: Retry failed batches once
    if failed_batch:
        print(f"\n🔁  Retrying {len(failed_batch)} failed batch(es)...\n")
        for i, batch in failed_batch:
            print(f"[Retry] Batch {i}...", end=" ", flush=True)
            try:
                client   = anthropic.Anthropic()
                response = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=2048,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": json.dumps(batch, indent=2)},
                        {"role": "assistant", "content": "Here is the JSON array:"},
                        {"role": "user", "content": "Please return only the JSON array, no extra text."}
                    ]
                )
                changes = parse_response(response.content[0].text)
                if changes:
                    all_changes.extend(changes)
                    print(f"⚠️  {len(changes)} issue(s) found")
                else:
                    print("✅  Clean")
            except (ValueError, json.JSONDecodeError):
                print(f"❌  Failed again — skipping batch {i}")

    # Step 4: Show summary
    show_summary(all_changes)

    if not all_changes:
        print("\n🎉  All MCQs passed review! No remarks file generated.")
        return

    # Step 5: Save remarks to JSON
    remarks_path = f"review-remarks/{csv_filename.replace('.csv', '-review-remarks.json')}"
    save_remarks(remarks_path, all_changes)

    print(f"""
┌─────────────────────────────────────────────────────────┐
│  📝  Review remarks saved!                              │
│                                                         │
│  File: {remarks_path:<49}│
│                                                         │
│  → Open this file and edit any remarks if needed        │
│  → Each entry has: issue, fix, updated_question,        │
│    and updated_options                                   │
│  → Save the file when done                              │
└─────────────────────────────────────────────────────────┘
""")

    # Step 6: Wait for user to review/edit remarks
    confirm = input("✏️   Done reviewing remarks? Apply changes and generate output? (yes/no): ").strip().lower()

    if confirm != "yes":
        print(f"❌  Output not generated. Your remarks are saved at {remarks_path}")
        print(f"    Run this anytime to apply them:")
        print(f"    python3 apply.py {csv_filename}")
        return

    # Step 7: Load remarks (picks up any manual edits made)
    final_changes = load_remarks(remarks_path)
    print(f"[Agent] Loaded {len(final_changes)} remark(s) from {remarks_path}")

    save_csv(output_path, mcqs, final_changes)
    print(f"\n✅  Done! Reviewed file saved to {output_path}")


# ── Entry point ───────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python3 agent.py <csv-filename> <subject>")
        print("Example: python3 agent.py sql-mcqs.csv sql")
        print("Example: python3 agent.py js-mcqs.csv javascript")
    else:
        run_agent(sys.argv[1], sys.argv[2])