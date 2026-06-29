#!/usr/bin/env python3
"""
TakeMeter — parse a raw Reddit *web-page* text dump into a labelable CSV.

When you select-all + copy a Reddit thread in the browser, each comment lands as:

    u/username avatar          (sometimes just the username)
    username
    •
    4h ago
    [• / Edited 3h ago]        (optional, if edited)
    [flair line]               (optional: "emoji:gsw-1: Warriors", "Lakers", "[BOS] X")
    [Profile Badge ...]        (optional)
    <COMMENT BODY>             (one or more lines / paragraphs)

    Upvote
    <score e.g. 6.5K>

    Downvote
    ...

This script anchors on the `... <timestamp> ... <body> ... Upvote` shape: the body is
everything between a comment's timestamp line and its `Upvote` line, with flair/badge
chrome stripped. Post bodies (terminated by "Go to comments") are skipped.

Reads every *.txt file in data/raw/, dedupes, applies noise filters, and writes
data/comments_to_label.csv with an empty `label` column. Stdlib only.
"""

import csv
import html
import re
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT_CSV = Path(__file__).resolve().parent.parent / "data" / "comments_to_label.csv"

MIN_CHARS = 12          # keep short genuine reactions ("yeah dunk that shit") ...
MAX_CHARS = 1200        # ... but drop pasted articles / copypastas
URL_RE = re.compile(r"https?://\S+")
TS_RE = re.compile(r"^(?:Edited\s+)?\d+\s*(?:mo|h|d|w|y|m|s)\s*ago$", re.IGNORECASE)
SCORE_RE = re.compile(r"^[\d.,]+\s*[KM]?$")
BOT_MARKERS = ("i am a bot", "this action was performed automatically", "beep boop")

# bare team/flair words that appear as a flair line right after the timestamp
TEAM_FLAIR = {
    "hawks", "celtics", "nets", "hornets", "bulls", "cavaliers", "mavericks",
    "nuggets", "pistons", "warriors", "rockets", "pacers", "clippers", "lakers",
    "grizzlies", "heat", "bucks", "timberwolves", "pelicans", "knicks", "thunder",
    "magic", "76ers", "sixers", "suns", "trail blazers", "blazers", "kings", "spurs",
    "raptors", "jazz", "wizards", "nba", "west", "east", "supersonics", "sonics",
    "san francisco warriors", "san diego clippers", "promoted",
}


def is_chrome(line: str) -> bool:
    """Header chrome that can sit between the timestamp and the body."""
    s = line.strip()
    if not s:
        return False
    low = s.lower()
    if s == "•":
        return True
    if s.startswith("emoji:"):
        return True
    if re.match(r"^\[[A-Z]{2,5}\]", s):          # historic player flair: "[BOS] Marcus Smart"
        return True
    if low.startswith("profile badge for the achievement"):
        return True
    if low.startswith("edited") and low.endswith("ago"):
        return True
    if low in TEAM_FLAIR:
        return True
    return False


def clean(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


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


def parse_file(lines):
    """Yield (score, body) for every comment in one web-dump file."""
    n = len(lines)
    upvote_idxs = [i for i, ln in enumerate(lines) if ln.strip() == "Upvote"]
    for u in upvote_idxs:
        # skip POST bodies (the "Upvote / score / Downvote / N / Go to comments" shape)
        lookahead = " ".join(lines[u + 1:u + 8]).lower()
        if "go to comments" in lookahead:
            continue
        score = ""
        if u + 1 < n and SCORE_RE.match(lines[u + 1].strip()):
            score = lines[u + 1].strip()

        # find this comment's timestamp line by walking up
        ts = u - 1
        while ts >= 0 and not TS_RE.match(lines[ts].strip()):
            ts -= 1
            # don't cross into the previous comment's Upvote block
            if ts >= 0 and lines[ts].strip() == "Upvote":
                ts = -1
                break
        if ts < 0:
            continue

        region = lines[ts + 1:u]
        # strip leading chrome (flair / badge / bullets), then leading blanks
        start = 0
        while start < len(region) and (is_chrome(region[start]) or not region[start].strip()):
            start += 1
        body_lines = [ln for ln in region[start:]]
        body = clean(" ".join(body_lines))
        if body:
            yield score, body


def main():
    txt_files = sorted(RAW_DIR.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {RAW_DIR}.")
        return

    seen, rows = set(), []
    parsed = dropped_noise = dropped_dup = 0
    for f in txt_files:
        lines = f.read_text(encoding="utf-8").splitlines()
        before = len(rows)
        for score, body in parse_file(lines):
            parsed += 1
            if is_noise(body):
                dropped_noise += 1
                continue
            key = body.lower()
            if key in seen:
                dropped_dup += 1
                continue
            seen.add(key)
            rows.append({"id": f"c{len(rows)+1:04d}", "score": score,
                         "text": body, "label": ""})
        print(f"  {f.name}: +{len(rows) - before} comments")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "score", "text", "label"])
        w.writeheader()
        w.writerows(rows)

    print(f"\nComments parsed     : {parsed}")
    print(f"Dropped (noise)     : {dropped_noise}")
    print(f"Dropped (duplicate) : {dropped_dup}")
    print(f"Written to label    : {len(rows)} -> {OUT_CSV}")
    if len(rows) < 250:
        print("\n  Tip: under 250 — paste a couple more threads into data/raw/ for margin.")


if __name__ == "__main__":
    main()
