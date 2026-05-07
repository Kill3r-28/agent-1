# MCQ Review Agent 🤖

An AI-powered agent that reviews Multiple Choice Questions for technical accuracy, clarity, and non-obviousness.

---

## Project Structure

```
agent-1/
├── input/                → drop your CSV files here
├── output/               → reviewed CSVs land here
├── prompts/              → one .txt file per subject
├── review-remarks/       → JSON remarks files (auto-generated)
├── agent.py              → main agent loop
├── apply.py              → apply remarks standalone (anytime)
└── tools.py              → file read/write utilities
```

---

## How to Run

```bash
python3 agent.py <csv-filename> <subject>
```

**Example:**
```bash
python3 agent.py sql-mcqs.csv sql
```

---

## Agent Workflow

```
1. Reads MCQs from input/<csv-filename>
        ↓
2. Loads prompt from prompts/<subject>.txt
        ↓
3. Reviews in batches of 5 via Claude Haiku
        ↓
4. Saves all remarks to:
   review-remarks/sql-mcqs-review-remarks.json
        ↓
5. Prompts you to open & edit the remarks file
   (change anything you disagree with)
        ↓
6. You confirm yes → agent reads the (possibly edited)
   JSON → generates output CSV
```

> If you say **no** at step 6, remarks are still saved.
> Run `python3 apply.py sql-mcqs.csv` anytime later to apply them.

---

## Input Format

Your CSV must have exactly these 3 columns:

| Column | Description |
|---|---|
| `Question ID` | Unique identifier for each MCQ |
| `Question Content` | The question — can be plain TEXT, MARKDOWN, or HTML |
| `Options Data` | JSON array of options (see below) |

**Options Data format:**
```json
[
  {"option_content": "SELECT * FROM users", "is_correct_option": 0},
  {"option_content": "SELECT ALL FROM users", "is_correct_option": 1},
  {"option_content": "FETCH * FROM users", "is_correct_option": 0},
  {"option_content": "GET * FROM users", "is_correct_option": 0}
]
```

> `is_correct_option: 1` = correct answer, `0` = wrong answer.
> Each MCQ must have **exactly one** option with value `1`.

---

## Review Remarks File

After every run, a JSON file is saved to `review-remarks/`:

**Filename:** `<input-filename>-review-remarks.json`
**Example:** `review-remarks/sql-mcqs-review-remarks.json`

**Structure of each remark:**
```json
[
  {
    "question_id": "abc123",
    "content_type": "MARKDOWN",
    "issue": "Correct answer is obvious to a naive user",
    "fix": "Replace wrong options with more plausible alternatives",
    "updated_question": "...",
    "updated_options": [
      {"option_content": "...", "is_correct_option": 0},
      {"option_content": "...", "is_correct_option": 1},
      {"option_content": "...", "is_correct_option": 0},
      {"option_content": "...", "is_correct_option": 0}
    ]
  }
]
```

**You can freely edit:**
- `issue` — your own note about what's wrong
- `fix` — what should change
- `updated_question` — corrected question text
- `updated_options` — corrected options and correct answer

> ⚠️ Keep the JSON structure intact while editing. Only one option should have `is_correct_option: 1`.

---

## Applying Remarks Later

If you said **no** at the confirmation step and want to apply remarks after editing the JSON:

```bash
python3 apply.py sql-mcqs.csv
```

This reads the remarks file, applies changes, and saves the output CSV — no re-review needed.

---

## Prompts

Each subject needs its own prompt file in `prompts/`.

| File | Used when you run |
|---|---|
| `prompts/sql.txt` | `python3 agent.py sql-mcqs.csv sql` |
| `prompts/javascript.txt` | `python3 agent.py js-mcqs.csv javascript` |
| `prompts/default.txt` | Fallback if subject prompt not found |

**A good prompt file must include:**
- Role definition (e.g. "You are an expert SQL reviewer...")
- Domain-specific rules (terminology, syntax standards)
- Review criteria (correctness, non-obviousness, clarity)
- Exact JSON response format (copy from an existing prompt)

> ⚠️ The response format section at the bottom of every prompt must stay identical across all prompt files — only the role and domain rules change.

---

## API Setup

This agent uses **Claude Haiku** via the Anthropic API.

**1. Get your API key:**
→ [console.anthropic.com](https://console.anthropic.com) → API Keys → Create Key

**2. Set it permanently:**
```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

**3. Add credits:**
→ [console.anthropic.com/settings/billing](https://console.anthropic.com/settings/billing)
→ Minimum $5 — lasts ~80 full runs at current batch size

**Cost estimate:** ~$0.06 per full run of 191 MCQs

---

## Review Criteria

The agent checks every MCQ for:

- ✅ **Correct answer accuracy** — is the marked answer actually right?
- ✅ **Non-obviousness** — can a naive user guess it without domain knowledge?
- ✅ **Single correct answer** — no ambiguity, no two options both being right
- ✅ **Content type** — valid syntax for TEXT / MARKDOWN / HTML questions
- ✅ **Option quality** — wrong options must be plausible, not absurd
- ✅ **Technical accuracy** — terminology matches industry standards

---

## Dependencies

```bash
pip install anthropic ollama
```

> Ollama is optional — only needed if switching back to a local model.

---

## Switching Models

In `agent.py`, find this line:
```python
model="claude-haiku-4-5-20251001"
```

| Model | Speed | Cost | Quality |
|---|---|---|---|
| `claude-haiku-4-5-20251001` | ⚡ Fast | $ Low | ✅ Good |
| `claude-sonnet-4-6` | Medium | $$ Medium | 🌟 Best |
| `llama3.2` (local) | 🐌 Slow | Free | Decent |
| `gemma4:e4b` (local) | 🐌 Slow | Free | Good |