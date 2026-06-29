#!/usr/bin/env python3
"""Build the final labeled dataset the notebook consumes.

Reads data/comments_to_label.csv (id, score, text, label), drops EXCLUDE rows,
cleans a few stray flair tokens that leaked into bodies, attaches notes to the
documented hard-to-label cases, and writes data/takemeter_labeled.csv with the
columns the spec asks for: text, label, notes  (single file, NOT pre-split).
"""
import csv
import re
from collections import Counter
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "data" / "comments_to_label.csv"
OUT = Path(__file__).resolve().parent.parent / "data" / "takemeter_labeled.csv"

# bare flair tokens that occasionally lead a body (nationality flairs render
# without the "emoji:" prefix in some pastes)
LEADING_FLAIR = ["Australia", "Canada", "United States", "New Zealand", "Lebanon",
                 "Slovenia", "France", "USA"]

# notes for the comments called out as genuinely hard during annotation
NOTES = {
    "c0116": "HARD: reaction vs hot_take. Single-stat jab ('2 shots in a G7') looks "
             "like the planning.md 'analysis-flavored hot take', but framing is pure "
             "emotional mockery tied to a just-watched moment -> reaction.",
    "c0007": "HARD: analysis vs hot_take. Cites real production (25+ ppg, beat Rockets) "
             "but as a decorative/cherry-picked rebuttal, not developed reasoning -> hot_take.",
    "c0029": "HARD: analysis vs hot_take. No statistics, but a genuine multi-step "
             "argument (lays out the strategic options + logic) -> analysis.",
    "c0394": "HARD: hot_take vs analysis. Lists GOATs (LeBron/Kobe/MJ) but the "
             "comparison is decorative hype, not an argued claim -> hot_take.",
    "c0339": "Clear analysis: load-bearing on/off + ppp numbers with reasoning.",
}


def clean(text: str) -> str:
    for flair in LEADING_FLAIR:
        if text.startswith(flair + " "):
            text = text[len(flair) + 1:]
    return re.sub(r"\s+", " ", text).strip()


rows = list(csv.DictReader(SRC.open(encoding="utf-8")))
out_rows = []
for r in rows:
    if r["label"] == "EXCLUDE":
        continue
    out_rows.append({
        "text": clean(r["text"]),
        "label": r["label"],
        "notes": NOTES.get(r["id"], ""),
    })

with OUT.open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["text", "label", "notes"])
    w.writeheader()
    w.writerows(out_rows)

c = Counter(r["label"] for r in out_rows)
total = len(out_rows)
print(f"wrote {total} labeled rows -> {OUT}")
for lab in ("analysis", "hot_take", "reaction"):
    print(f"  {lab:9s}: {c[lab]:3d}  ({100*c[lab]/total:.1f}%)")
top = max(c.values()) / total
print(f"largest class share: {100*top:.1f}%  ({'OK <70%' if top < 0.70 else 'IMBALANCE'})")
print(f"rows with notes: {sum(1 for r in out_rows if r['notes'])}")
