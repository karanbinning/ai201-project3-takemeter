#!/usr/bin/env python3
"""
TakeMeter — parse saved Reddit thread JSON into a labelable CSV.

Usage:
    python scripts/parse_reddit.py

Reads every *.json file in data/raw/ (saved from your browser by appending
`.json?limit=500` to a thread URL), flattens all comments, drops non-discourse
noise, dedupes, and writes data/comments_to_label.csv with an empty `label`
column ready for annotation.

Stdlib only — no pip installs needed.
"""

import csv
import html
import json
import re
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT_CSV = Path(__file__).resolve().parent.parent / "data" / "comments_to_label.csv"

# --- filters for "not discourse" (excluded at collection, per planning.md) ---
MIN_CHARS = 20            # too short to be a take or a real reaction
MAX_CHARS = 1500          # giant copypastas / bot posts
URL_RE = re.compile(r"https?://\S+")
BOT_MARKERS = ("i am a bot", "this action was performed automatically",
               "^^^this", "beep boop")


def clean_text(body: str) -> str:
    body = html.unescape(body or "")
    body = body.replace("\n", " ").replace("\r", " ")
    body = re.sub(r"\s+", " ", body).strip()
    return body


def is_noise(text: str) -> bool:
    low = text.lower()
    if any(m in low for m in BOT_MARKERS):
        return True
    if len(text) < MIN_CHARS or len(text) > MAX_CHARS:
        return True
    # link-only / mostly-link
    stripped = URL_RE.sub("", text).strip()
    if len(stripped) < MIN_CHARS:
        return True
    # emoji/punctuation-only-ish: needs some letters
    if not re.search(r"[a-zA-Z]", stripped):
        return True
    return False


def walk_comments(node, out):
    """Recursively pull comment bodies out of Reddit's listing JSON."""
    if isinstance(node, dict):
        kind = node.get("kind")
        data = node.get("data", {})
        if kind == "t1":  # a comment
            body = data.get("body")
            if body and body not in ("[deleted]", "[removed]"):
                out.append({
                    "id": data.get("id", ""),
                    "author": data.get("author", ""),
                    "score": data.get("score", 0),
                    "body": body,
                })
            # recurse into replies
            replies = data.get("replies")
            if isinstance(replies, dict):
                walk_comments(replies, out)
        else:
            children = data.get("children")
            if isinstance(children, list):
                for c in children:
                    walk_comments(c, out)
    elif isinstance(node, list):
        for c in node:
            walk_comments(c, out)


def main():
    raw_files = sorted(RAW_DIR.glob("*.json"))
    if not raw_files:
        print(f"No .json files found in {RAW_DIR}. Save thread JSON there first.")
        return

    raw_comments = []
    for f in raw_files:
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  ! skipped {f.name}: {e}")
            continue
        before = len(raw_comments)
        walk_comments(doc, raw_comments)
        print(f"  {f.name}: +{len(raw_comments) - before} comments")

    # dedupe by id, then by text
    seen_ids, seen_text, rows = set(), set(), []
    dropped_noise = dropped_dup = 0
    for c in raw_comments:
        if c["id"] and c["id"] in seen_ids:
            dropped_dup += 1
            continue
        text = clean_text(c["body"])
        if is_noise(text):
            dropped_noise += 1
            continue
        if text.lower() in seen_text:
            dropped_dup += 1
            continue
        seen_ids.add(c["id"])
        seen_text.add(text.lower())
        rows.append({"id": c["id"], "score": c["score"], "text": text, "label": ""})

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "score", "text", "label"])
        w.writeheader()
        w.writerows(rows)

    print(f"\nRaw comments parsed : {len(raw_comments)}")
    print(f"Dropped (noise)     : {dropped_noise}")
    print(f"Dropped (duplicate) : {dropped_dup}")
    print(f"Written to label    : {len(rows)} -> {OUT_CSV}")
    if len(rows) < 250:
        print("\n  Tip: under 250 — save a couple more threads into data/raw/ for margin.")


if __name__ == "__main__":
    main()
