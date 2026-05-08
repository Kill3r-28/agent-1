# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered CLI tool that reviews Multiple Choice Questions (MCQs) for technical accuracy, clarity, and non-obviousness using the Claude API. It processes MCQs in batches, generates structured review remarks, and outputs corrected CSVs.

## Commands

```bash
# Run the full review agent
python3 agent.py <csv-filename> <subject>
# e.g.: python3 agent.py sql-mcqs.csv sql

# Apply pre-saved remarks without re-reviewing
python3 apply.py <csv-filename>
# e.g.: python3 apply.py sql-mcqs.csv

# Required environment variable
export ANTHROPIC_API_KEY=<your-key>
```

There are no build, lint, or test commands — this project has no test suite or linter configuration.

## Architecture

Three modules with a clear separation of concerns:

- **`agent.py`** — Orchestration loop: loads CSV → batches MCQs → calls Claude → parses responses → saves remarks → applies approved changes
- **`tools.py`** — All CSV/JSON I/O and data transformation (reading, batching, writing, content-type detection)
- **`apply.py`** — Lightweight wrapper that applies pre-saved remarks without re-reviewing (reads CSV + remarks JSON → writes output CSV)

### Data flow

```
input/<name>.csv
  → tools.read_csv()            # enriches rows with content_type, parsed options, correct answer
  → make_batches(mcqs, size=5)  # groups into batches of 5
  → Claude (claude-haiku-4-5)   # batch JSON payload → structured JSON remarks
  → parse_response()            # 3-layer fallback: strip fences → find array boundaries → json.loads
  → review-remarks/<name>-review-remarks.json   # saved for manual editing
  → [user edits JSON manually]
  → tools.save_csv()            # merges changed rows back; unchanged rows preserved
  → output/<name>-reviewed.csv
```

### Subject prompts

Prompts live in `prompts/<subject>.txt`. If no subject-specific file exists, `prompts/default.txt` is used. Each prompt defines the reviewer role, 9 review criteria, few-shot examples, and the required JSON response schema. The response schema must remain consistent across all prompt files — it is parsed by `parse_response()` in `agent.py`.

### Review remarks format

Claude returns (and the agent saves) a JSON array where each flagged item has:
```json
{
  "question_id": "...",
  "question": "original text",
  "content_type": "TEXT|MARKDOWN|HTML",
  "issue": "description",
  "fix": "what to change and why",
  "updated_question": "corrected text",
  "updated_options": [{"option_content": "...", "is_correct_option": 0}]
}
```
Users are expected to open this file, review/edit it, then confirm before changes are applied.

## Key Implementation Details

- **Model:** `claude-haiku-4-5-20251001` (set in `agent.py` lines 93 and 119); change both occurrences to switch models
- **Batch size:** 5 MCQs per API call (configured in `agent.py` via `make_batches(mcqs, batch_size=5)`)
- **Retry:** Failed batches are retried once with adjusted prompting; accumulated changes are merged across all batches
- **Content-type detection:** Regex-based in `tools.detect_content_type()` — checks for HTML tags first, then Markdown indicators, defaults to TEXT
- **Input CSV columns:** `Question ID`, `Question Content`, `Options Data` (Options Data is a JSON array with `option_content` and `is_correct_option` fields)

## Adding a New Subject

1. Create `prompts/<subject>.txt` modeled after `prompts/sql.txt`
2. Keep the response JSON schema identical to the existing format
3. Run: `python3 agent.py <subject>-mcqs.csv <subject>`
