---
name: delegate-to-kimi
description: Delegate a self-contained coding, analysis, or writing task to Kimi K3 running on Fireworks AI, then apply the result locally. Use when the user says "ask Kimi", "delegate this to Kimi/K3", "get a second opinion from another model", "hand this off to Fireworks", or wants a bulk/parallel/cheaper generation job (boilerplate, test scaffolding, translations, large-file summaries) done outside the main session.
---

# Delegate to Kimi K3 on Fireworks

Hand a self-contained unit of work to Kimi K3 (1M-token context, tool-calling
capable) over the Fireworks serverless API, then review and apply what comes
back.

## The split of responsibility

Kimi runs behind a plain HTTP API. It has **no filesystem, shell, or repo
access**. So the division is always:

| You (Claude Code)                     | Kimi K3                        |
| ------------------------------------- | ------------------------------ |
| Gather context, read files            | Reason over what you sent      |
| Write a precise, closed-form prompt    | Produce text / code / analysis |
| Run the script                         | —                              |
| Review the output, apply edits, test   | —                              |

Never tell Kimi to "edit the file" or "run the tests" — it cannot. Ask it to
**return** the content, then you write it.

## Prerequisites

A Fireworks API key in `FIREWORKS_API_KEY` (or the plugin's `FIREWORKS_API_KEY`
user config). If it is missing, the script says so — relay that to the user with
the link to https://fireworks.ai/account/api-keys and stop. Do not ask the user
to paste the key into the chat.

## Workflow

1. **Check the task is a good fit.** Good: self-contained, output is text you can
   review in one pass, context fits in what you can attach. Bad: anything needing
   iterative tool use, live repo exploration, or judgment that depends on the
   session so far.
2. **Scope it.** Decide exactly which files Kimi needs. Attaching a whole
   directory wastes tokens and dilutes the answer.
3. **Write a closed-form prompt.** State the deliverable, the format, and the
   constraints (language, style, framework version, what not to change). Kimi has
   no repo conventions unless you spell them out.
4. **Run the script** (below).
5. **Review before applying.** Treat the response as an untrusted draft: it may
   invent APIs, drift from local conventions, or ignore an edge case. Read it,
   apply it yourself with Edit/Write, then run the tests or type checker.
6. **Report honestly** what Kimi produced, what you changed, and what you
   verified.

## Running it

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/delegate-to-kimi/scripts/kimi.py" \
  --prompt "Write pytest cases for the pure functions in the attached module. Return only the test file." \
  --file src/parser.py \
  --out /tmp/test_parser.py
```

Common flags:

| Flag                       | Use                                                          |
| -------------------------- | ------------------------------------------------------------ |
| `--prompt` / `--prompt-file` | The task. Long prompts are cleaner from a file (or stdin).   |
| `--file PATH`              | Attach a file as read-only context. Repeatable.              |
| `--system`                 | Role and hard constraints ("You are a senior Go reviewer…").  |
| `--out PATH`               | Save the answer to a file so you can diff/apply it.          |
| `--reasoning-effort`       | `none`…`max`. Raise for hard reasoning, lower for bulk work.  |
| `--json-mode`              | Force a JSON object back — also say so in the prompt.        |
| `--no-stream`              | Wait for the whole answer; also prints token usage.          |
| `--max-tokens`             | Default 8192. Raise for large files; truncation is flagged.   |
| `--model`                  | Override the model id (see below).                            |
| `--show-reasoning`         | Print Kimi's reasoning tokens to stderr.                      |

For a prompt with backticks, heredocs, or newlines, write it to a scratch file
and use `--prompt-file` rather than fighting shell quoting.

## Models

Default is `accounts/fireworks/models/kimi-k3`. Alternatives:

- `accounts/fireworks/routers/kimi-k3-fast` — lower latency tier.
- `accounts/fireworks/routers/kimi-k3-us` — US-only serverless.

Any other Fireworks model id works too; `KIMI_MODEL` sets the default.

## Cost

Kimi K3 serverless is roughly $3.00 / $0.30 / $15.00 per million tokens
(input / cached input / output). Attached files are billed as input on every
call, so send the minimum that makes the task answerable, and mention the scale
to the user before firing off a large batch of calls.

See `references/fireworks-api.md` for endpoint and payload details when you need
to go beyond the script.
