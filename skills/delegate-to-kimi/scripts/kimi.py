#!/usr/bin/env python3
"""Delegate a self-contained task to Kimi K3 on Fireworks AI.

Reads a prompt (argument, file, or stdin), optionally attaches file contents as
context, and calls the Fireworks chat completions API. Stdlib only.

Auth: FIREWORKS_API_KEY, or CLAUDE_PLUGIN_OPTION_FIREWORKS_API_KEY when set as
plugin user config.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
DEFAULT_MODEL = "accounts/fireworks/models/kimi-k3"


def die(msg: str, code: int = 1) -> None:
    print(f"kimi.py: {msg}", file=sys.stderr)
    sys.exit(code)


def api_key() -> str:
    for var in ("FIREWORKS_API_KEY", "CLAUDE_PLUGIN_OPTION_FIREWORKS_API_KEY"):
        key = os.environ.get(var, "").strip()
        if key:
            return key
    die(
        "no API key found. Set FIREWORKS_API_KEY (get one at "
        "https://fireworks.ai/account/api-keys), or configure the plugin's "
        "FIREWORKS_API_KEY user config."
    )
    raise AssertionError  # unreachable


def read_prompt(args: argparse.Namespace) -> str:
    parts = []
    if args.prompt:
        parts.append(args.prompt)
    if args.prompt_file:
        parts.append(read_text(args.prompt_file))
    if not parts and not sys.stdin.isatty():
        stdin = sys.stdin.read().strip()
        if stdin:
            parts.append(stdin)
    if not parts:
        die("no prompt given. Use --prompt, --prompt-file, or pipe text on stdin.")
    return "\n\n".join(parts)


def read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError as exc:
        die(f"cannot read {path}: {exc}")
        raise AssertionError  # unreachable


def attach_files(paths: list[str]) -> str:
    blocks = []
    for path in paths:
        body = read_text(path)
        blocks.append(f"<file path=\"{path}\">\n{body}\n</file>")
    return "\n\n".join(blocks)


def build_messages(args: argparse.Namespace) -> list[dict]:
    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    user = read_prompt(args)
    if args.file:
        user = (
            f"{user}\n\n"
            "Reference files (read-only context; you cannot edit them directly):\n\n"
            f"{attach_files(args.file)}"
        )
    messages.append({"role": "user", "content": user})
    return messages


def build_payload(args: argparse.Namespace) -> dict:
    payload = {
        "model": args.model,
        "messages": build_messages(args),
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "stream": args.stream,
    }
    if args.reasoning_effort:
        payload["reasoning_effort"] = args.reasoning_effort
    if args.json_mode:
        payload["response_format"] = {"type": "json_object"}
    return payload


def request(payload: dict, timeout: int):
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key()}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if payload.get("stream") else "application/json",
        },
        method="POST",
    )
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        hint = ""
        if exc.code == 401:
            hint = " (check that FIREWORKS_API_KEY is valid)"
        elif exc.code == 404:
            hint = f" (check that the model id '{payload['model']}' exists)"
        elif exc.code == 429:
            hint = " (rate limited; retry or use a dedicated deployment)"
        die(f"HTTP {exc.code} from Fireworks{hint}: {detail}", code=2)
    except urllib.error.URLError as exc:
        die(f"network error contacting Fireworks: {exc.reason}", code=2)
    raise AssertionError  # unreachable


def run_stream(payload: dict, args: argparse.Namespace) -> str:
    out: list[str] = []
    reasoning_open = False
    with request(payload, args.timeout) as resp:
        for raw in resp:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[len("data:") :].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            thought = delta.get("reasoning_content")
            if thought and args.show_reasoning:
                if not reasoning_open:
                    print("--- reasoning ---", file=sys.stderr)
                    reasoning_open = True
                print(thought, end="", file=sys.stderr, flush=True)
            text = delta.get("content")
            if text:
                if reasoning_open:
                    print("\n--- answer ---", file=sys.stderr)
                    reasoning_open = False
                out.append(text)
                print(text, end="", flush=True)
    print()
    return "".join(out)


def run_blocking(payload: dict, args: argparse.Namespace) -> str:
    with request(payload, args.timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    choices = body.get("choices") or []
    if not choices:
        die(f"no choices in response: {json.dumps(body)[:500]}", code=2)
    message = choices[0].get("message") or {}
    thought = message.get("reasoning_content")
    if thought and args.show_reasoning:
        print(f"--- reasoning ---\n{thought}\n--- answer ---", file=sys.stderr)
    text = message.get("content") or ""
    print(text)
    usage = body.get("usage") or {}
    if usage:
        print(
            "\n[usage] prompt={} completion={} total={}".format(
                usage.get("prompt_tokens", "?"),
                usage.get("completion_tokens", "?"),
                usage.get("total_tokens", "?"),
            ),
            file=sys.stderr,
        )
    finish = choices[0].get("finish_reason")
    if finish == "length":
        print(
            "[warning] output truncated at max_tokens; rerun with a larger --max-tokens",
            file=sys.stderr,
        )
    return text


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kimi.py",
        description="Delegate a self-contained task to Kimi K3 on Fireworks AI.",
    )
    parser.add_argument("--prompt", help="The task to delegate.")
    parser.add_argument("--prompt-file", help="File containing the task prompt.")
    parser.add_argument(
        "--file",
        action="append",
        default=[],
        metavar="PATH",
        help="Attach a file as read-only context. Repeatable.",
    )
    parser.add_argument("--system", help="System prompt (role/constraints for Kimi).")
    parser.add_argument(
        "--model",
        default=os.environ.get("KIMI_MODEL", DEFAULT_MODEL),
        help=f"Fireworks model id (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument(
        "--reasoning-effort",
        choices=["none", "low", "medium", "high", "max"],
        help="Reasoning budget for models that support it.",
    )
    parser.add_argument(
        "--json-mode",
        action="store_true",
        help="Ask for a JSON object response (also say so in the prompt).",
    )
    parser.add_argument(
        "--show-reasoning",
        action="store_true",
        help="Print reasoning tokens to stderr.",
    )
    parser.add_argument(
        "--no-stream",
        dest="stream",
        action="store_false",
        help="Wait for the full response instead of streaming.",
    )
    parser.add_argument("--out", metavar="PATH", help="Also write the answer to this file.")
    parser.add_argument("--timeout", type=int, default=600, help="Seconds (default: 600).")
    parser.set_defaults(stream=True)
    args = parser.parse_args()

    api_key()  # fail fast before reading context files
    payload = build_payload(args)
    text = run_stream(payload, args) if args.stream else run_blocking(payload, args)

    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(text)
        except OSError as exc:
            die(f"cannot write {args.out}: {exc}")
        print(f"[saved] {args.out}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
