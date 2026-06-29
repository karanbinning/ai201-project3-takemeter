# TakeMeter — Demo Video Script (~4 min)

Target length 3–5 min. Have two things open and switch between them:
- **Window A:** your Colab notebook (the demo cell below, ready to run)
- **Window B:** `README.md` rendered on GitHub (scrolled to the Evaluation report)

Required moments this script covers: ✅ 3–5 posts classified with label + confidence ·
✅ one correct prediction narrated · ✅ one incorrect prediction narrated · ✅ walkthrough of
the evaluation report.

---

## 0:00 – 0:30 — Intro (talking head or slide)

> "Hi, this is TakeMeter — a text classifier that measures *discourse quality* on the r/nba
> subreddit. Instead of judging whether a take is right, it sorts each comment into one of three
> discourse acts: **analysis** — a reasoned argument; **hot_take** — a confident claim asserted
> without evidence; and **reaction** — pure emotional response to a moment.
> I fine-tuned DistilBERT on 256 hand-labeled comments and compared it against a zero-shot Groq
> baseline. Spoiler: the result is not a success story — and that turned out to be the
> interesting part. Let me show you."

---

## 0:30 – 1:45 — Live classification (Window A: Colab)

Paste and run this cell on camera (model + tokenizer must still be loaded from training):

```python
# === TakeMeter live demo: classify posts with confidence ===
import torch, torch.nn.functional as F
ID2LABEL = {0: "analysis", 1: "hot_take", 2: "reaction"}

demo_posts = [
    ("The Heat have finally done it", "reaction"),
    ("I doubt his model actually says that. It's an anonymous source probably out of context.", "hot_take"),
    ("The thing about math is that after you crunch the numbers you have to apply sanity. If your model says one of the best players on a team was its least productive, the model is wrong.", "analysis"),
    ("A decade of pump faking star trades got them Giannis. Fair play Pat Riley.", "hot_take"),
    ("Game saving play", "reaction"),
]

model.eval(); device = next(model.parameters()).device
print(f"{'PREDICTED':<11}{'CONF':<7}{'TRUE':<10}POST")
print("-" * 90)
for text, true in demo_posts:
    enc = tokenizer(text, return_tensors="pt", truncation=True, padding=True).to(device)
    with torch.no_grad():
        probs = F.softmax(model(**enc).logits, dim=-1)[0]
    pid = int(probs.argmax())
    mark = "OK " if ID2LABEL[pid] == true else "XX "
    print(f"{ID2LABEL[pid]:<11}{float(probs[pid]):<7.2f}{true:<10}{mark}{text[:55]}")
```

> "Here are five real r/nba comments going through the fine-tuned model. Each row shows the
> predicted label, the model's confidence, and the true label I annotated.
> The first thing to notice — look at the **confidence column**. Every single prediction is around
> **0.38 to 0.40**. On a three-class problem, random guessing is 0.33. So the model is barely more
> confident than a coin flip on *everything* — that's a red flag we'll come back to."

---

## 1:45 – 2:20 — One CORRECT prediction (narrate)

Point at the **"The Heat have finally done it"** row (predicted `reaction`, ~0.39, correct).

> "This one it gets right: *'The Heat have finally done it'* → **reaction**. And that's the right
> call — it's a short, in-the-moment exclamation reacting to a trade going through, with no claim
> you could actually argue with. That's the definition of a reaction.
> But notice the confidence is still only 0.39 — so even when it's correct, it's not *sure*. It
> likely landed here off surface cues — the comment is short and has no analytical structure —
> rather than truly understanding 'feeling versus claim.'"

---

## 2:20 – 3:10 — One INCORRECT prediction (narrate)

Point at the **"The thing about math..."** row (true `analysis`, predicted `hot_take`, ~0.38).

> "Now the failure. This comment — *'after you crunch the numbers you have to apply sanity; if
> your model says one of the best players was the least productive, the model is wrong'* — is a
> textbook **analysis**: it's a developed argument about validating models against reality.
> But the model predicts **hot_take**. And here's the key finding: the model predicted `analysis`
> **zero times** across the entire test set. It never learned that class at all.
> Why? `analysis` was my rarest label — only about 34 training examples — and with the default 3
> training epochs, DistilBERT took the easy path: ignore the hard rare class and just split the
> two big ones. So every real analysis comment gets forced into hot_take or reaction. This isn't a
> labeling mistake — the label is clearly correct — it's the model underfitting a small,
> imbalanced dataset."

---

## 3:10 – 4:00 — Evaluation report walkthrough (Window B: README on GitHub)

Scroll to **Evaluation report**. Point to each table as you talk.

> "Here's the full evaluation. Top table — the **zero-shot Groq baseline scored 64%**, and the
> **fine-tuned model only 56%**. Fine-tuning made it *worse*.
> Per-class metrics tell the real story: the baseline's `analysis` F1 was 0.63 — its best class —
> while the fine-tuned model's `analysis` F1 is **zero**.
> The confusion matrix makes it visual: this entire **analysis column is zeros** — the model never
> predicts it. The errors are directional — analysis collapses into hot_take, and short hot_takes
> and reactions get confused with each other.
> So what did the model actually learn versus what I intended? I wanted it to detect *reasoning
> quality*. What it actually learned was to lean on surface emotional cues, and it missed the
> reasoning concept entirely. The honest lesson: for a subtle, low-frequency distinction like
> this, 256 examples wasn't enough to beat a large model that already understands the concept from
> pretraining. The documented fix would be more epochs and a class-weighted loss to rescue the
> analysis class."

---

## 4:00 – 4:20 — Close

> "So TakeMeter is a documented negative result with a specific, diagnosable cause — a dead
> minority class from underfitting a small imbalanced dataset. The full design rationale,
> dataset, and analysis are in the repo's planning.md and README. Thanks for watching."

---

### Recording tips
- Run the demo cell **once before recording** to confirm it prints cleanly (and that `model` /
  `tokenizer` are still in memory — if the runtime reset, re-run Sections 1–3 first).
- Zoom the Colab font up (Ctrl/Cmd +) so the label/confidence columns are readable on video.
- If you go long, cut the close to one sentence — the four required moments are 0:30–4:00.
