#!/usr/bin/env python3
"""
TakeMeter — parse pasted Reddit comments into a labelable CSV.

Usage:
    python scripts/parse_pasted.py

Reads every *.txt file in data/raw/. Each comment is one block of text
separated from the next by a BLANK LINE (you can also separate with a line
of `---`). Applies the same noise filters as parse_reddit.py, dedupes, and
writes data/comments_to_label.csv with an empty `label` column for annotation.

Stdlib only.
"""

import csv
import html
import re
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT_CSV = Path(__file__).resolve().parent.parent / "data" / "comments_to_label.csv"

MIN_CHARS = 20
MAX_CHARS = 1500
URL_RE = re.compile(r"https?://\S+")
BOT_MARKERS = ("i am a bot", "this action was performed automatically",
               "beep boop")
# common Reddit UI chrome that sneaks in when selecting comments
CHROME_RE = re.compile(
    r"^(reply|share|report|save|hide|give award|\d+\s*(points?|pts)|"
    r"level \d+|·|edited|\d+[hdm] ago|permalink).*$",
    re.IGNORECASE,
)


def clean_text(body: str) -> str:
    body = html.unescape(body or "")
    body = body.replace("\r", " ")
    body = re.sub(r"[ \t]+", " ", body).strip()
    return body


def is_noise(text: str) -> bool:
    low = text.lower()
    if any(m in low for m in BOT_MARKERS):
        return True
    if len(text) < MIN_CHARS or len(text) > MAX_CHARS:
        return True
    stripped = URL_RE.sub("", text).strip()
    if len(stripped) < MIN_CHARS:
        return True
    if not re.search(r"[a-zA-Z]", stripped):
        return True
    return False


def split_blocks(raw: str):
    # normalize an explicit --- delimiter to blank-line separation
    raw = re.sub(r"\n-{3,}\n", "\n\n", raw)
    blocks = re.split(r"\n\s*\n", raw)
    for b in blocks:
        # drop obvious UI-chrome lines, keep real comment lines
        lines = [ln for ln in b.splitlines() if not CHROME_RE.match(ln.strip())]
        text = clean_text(" ".join(lines))
        if text:
            yield text


def main():
    txt_files = sorted(RAW_DIR.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {RAW_DIR}. Paste comments into "
              f"data/raw/pasted.txt (one per block, blank line between).")
        return

    seen_text, rows = set(), []
    parsed = dropped_noise = dropped_dup = 0
    for f in txt_files:
        raw = f.read_text(encoding="utf-8")
        n_before = len(rows)
        for text in split_blocks(raw):
            parsed += 1
            if is_noise(text):
                dropped_noise += 1
                continue
            if text.lower() in seen_text:
                dropped_dup += 1
                continue
            seen_text.add(text.lower())
            rows.append({"id": f"p{len(rows)+1:04d}", "score": "", "text": text, "label": ""})
        print(f"  {f.name}: +{len(rows) - n_before} comments")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "score", "text", "label"])
        w.writeheader()
        w.writerows(rows)

    print(f"\nBlocks parsed       : {parsed}")
    print(f"Dropped (noise)     : {dropped_noise}")
    print(f"Dropped (duplicate) : {dropped_dup}")
    print(f"Written to label    : {len(rows)} -> {OUT_CSV}")
    if len(rows) < 250:
        print("\n  Tip: under 250 — paste more comments for labeling margin.")


if __name__ == "__main__":
    main()
