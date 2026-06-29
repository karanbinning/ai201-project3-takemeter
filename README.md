# TakeMeter

A fine-tuned text classifier that measures **discourse quality** on r/nba — sorting comments by
*what kind of discourse act* they perform (reasoning vs. asserting vs. emoting), not by whether
the take is correct.

**Headline result (honest):** the fine-tuned DistilBERT model **underperformed** the zero-shot
Groq baseline (56.4% vs. 64.1% accuracy) and **completely collapsed the `analysis` class** —
predicting it zero times on the test set. This README documents that failure and diagnoses why,
because the failure mode is specific and instructive. Full design notes live in
[planning.md](planning.md).

---

## Community choice and reasoning

[r/nba](https://www.reddit.com/r/nba/) — the largest basketball discussion subreddit (~15M
members). Within a *single* thread its comments range from film-study breakdowns to confident
hot takes to pure screams of joy, which is exactly the quality variance a discourse classifier
needs. The community also polices take quality in its own slang ("hot take" = insult, "W
analysis" = praise), so the labels track distinctions r/nba users already make rather than ones
imposed from outside. Public comments are abundant, so collecting 200+ varied examples is easy.

I measure the **discourse act**, not correctness: a wrong-but-reasoned comment is still
`analysis`; a correct-but-unargued shout is still `hot_take` or `reaction`.

---

## Label taxonomy

Three labels on one axis — how much **reasoning** the comment contains: `analysis` > `hot_take`
> `reaction`.

### `analysis`
A comment that builds a genuine argument — backed by specific, verifiable evidence (stats,
historical comparison, tactical observation) **or** developed through multi-step reasoning —
where the reasoning is the point.
- *"Draft picks are the lifeblood of a small-market team like Milwaukee which struggles to sign FAs. You draft a Giannis-tier player or you trade for one — either way you need as much capital as you can get. Has this sub learned nothing from watching Sam Presti?"*
- *"Three is exactly 50% more than two. Pretty much no one hits 50% more shots from 20 feet than from 24, so taking long twos is almost always a bad idea — you don't need advanced models for that."*

### `hot_take`
A bold, confident evaluative claim, ranking, or prediction **asserted without genuine evidence**
— it asserts rather than argues (any stats are decorative/cherry-picked).
- *"He's straight up taken the face of the league. It's his NBA now. It's his era."*
- *"Anyone who finds any billionaire actually likable is a gullible rube."*

### `reaction`
An immediate **emotional response to a moment** — excitement, despair, celebration, disbelief,
hatred — with little or no standing claim.
- *"GLORIOUS HATEWATCH"*
- *"That dunk was majestic. Literally fell to my knees in front of the TV. Basketball nirvana."*

**Decision rules:** `analysis` vs `hot_take` → strip the opinion; is what remains a
load-bearing argument/real reasoning chain (analysis) or a bare assertion / decorative stat
(hot_take)? `hot_take` vs `reaction` → does it make a claim you could argue with later
(hot_take) or is it pure moment-tied emotion (reaction)?

---

## Data: collection, labeling, distribution

**Source.** Public r/nba comment threads only. Collected by opening threads in the browser,
copying the page text, and parsing it into a CSV with [scripts/parse_webdump.py](scripts/parse_webdump.py)
(strips Reddit UI chrome, drops non-discourse noise, dedupes). Reddit blocks scripted fetches
from the dev environment, so collection was manual.

**Thread mix (to force class variety).** I deliberately sampled across thread types because each
skews toward a different label: trade-rumor/news threads (LeBron-to-Warriors, Kawhi/Plaschke) →
`hot_take`+`analysis`; elimination/hatewatch + game-7 threads (OKC eliminated, Spurs) →
`reaction`; an analytics argument (the Jaylen Brown plus-minus debate) → `analysis`.

**Labeling process.** 444 raw comments were parsed; 188 were non-discourse (puns, memes, song
lyrics, off-topic tangents, logistics) and excluded at collection time — no catch-all bucket.
The remaining **256** were labeled one at a time against the definitions above. Labels were
**produced with AI assistance (Claude)** applying the planning.md definitions — see the
[AI usage](#ai-usage) section for the disclosure and review obligation. The single labeled file
is [data/takemeter_labeled.csv](data/takemeter_labeled.csv) (`text`, `label`, `notes`), not
pre-split — the notebook does the 70/15/15 split.

**Label distribution (256 total):**

| Label | Count | Share |
|---|---|---|
| `analysis` | 49 | 19.1% |
| `hot_take` | 100 | 39.1% |
| `reaction` | 107 | 41.8% |

Largest class 41.8% — well under the 70% imbalance limit. `analysis` is the rare class (this
matters a lot below).

**Three genuinely difficult examples and how I decided them:**

1. *"THEY REALLY GAVE CHET THE MAX 🤣🤣🤣 Type of guy to shoot 2 shots in a Game 7. Fucking embarrassing."* — `reaction` vs `hot_take`. It's the textbook "single-stat jab," but the dominant content is emotional mockery tied to a just-watched moment, not a durable arguable claim. **→ `reaction`.**
2. *"Except curry is still dropping over 25 in half the games — edit: lebron single-handedly beat the rockets."* — `analysis` vs `hot_take`. Cites real production, but as a decorative rebuttal to dismiss a narrative, not as load-bearing reasoning. **→ `hot_take`.**
3. *"I kinda respect it as a strategy. If you don't have a real shot with an aging superstar, your only options are to blow it up or make high-risk moves that raise your ceiling even if you're 90% likely to flop."* — `analysis` vs `hot_take`. No stats at all, but a genuine multi-step argument. **→ `analysis`** (this forced me to widen the `analysis` definition; see [Spec reflection](#spec-reflection)).

---

## Fine-tuning approach

- **Base model:** `distilbert-base-uncased` (HuggingFace), `num_labels=3`.
- **Training setup:** the starter Colab notebook on a free T4 GPU. 70/15/15 train/val/test split
  → ~179 train / 38 val / **39 test**. Standard `Trainer` fine-tuning.
- **Hyperparameters & the decision I made:** I deliberately kept the notebook defaults —
  **3 epochs, learning rate 2e-5, batch size 16** — for this run, so the baseline-vs-fine-tuned
  comparison reflects *out-of-the-box* fine-tuning rather than a tuned pipeline. In hindsight
  this was the wrong call for a dataset this small: **3 epochs over ~179 examples underfit the
  model** (every test confidence landed at 0.37–0.40, barely above the 0.33 random floor — the
  model never developed sharp decision boundaries). The documented fix (not applied here) would
  be more epochs (~8–10) plus **class-weighted loss** to stop the rare `analysis` class from
  being ignored.

---

## Baseline description

A **zero-shot** baseline: Groq `llama-3.3-70b-versatile` classifying each test comment with no
task-specific training. The prompt (Section 5 of the notebook) gives the model the same label
definitions and decision rules a human annotator gets, one example per label, and instructs it
to output **only** the lowercase label string. Results were collected by the notebook's
`classify_with_groq()` over all 39 test examples — **0 unparseable responses** (39/39 parsed),
so the strict-string-match output format held. The full prompt text is in the notebook.

---

## Evaluation report

### Overall accuracy

| Model | Accuracy | Macro-F1 |
|---|---|---|
| Zero-shot baseline (Groq llama-3.3-70b) | **0.641** | 0.63 |
| Fine-tuned DistilBERT | 0.564 | **0.42** |
| Δ (fine-tuned − baseline) | **−0.077** | −0.21 |

The fine-tuned model is **worse on both accuracy and macro-F1**. For reference, a
majority-class guesser (always `reaction`) scores 16/39 ≈ 0.41.

### Per-class metrics — both models

**Zero-shot baseline (Groq):**

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| analysis | 0.55 | 0.75 | 0.63 | 8 |
| hot_take | 0.58 | 0.47 | 0.52 | 15 |
| reaction | 0.75 | 0.75 | 0.75 | 16 |
| **macro avg** | 0.63 | 0.66 | **0.63** | 39 |

**Fine-tuned DistilBERT:**

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| analysis | 0.00 | 0.00 | **0.00** | 8 |
| hot_take | 0.48 | 0.80 | 0.60 | 15 |
| reaction | 0.71 | 0.63 | 0.67 | 16 |
| **macro avg** | 0.40 | 0.48 | **0.42** | 39 |

The single most important number: fine-tuned **`analysis` F1 = 0.00**. The baseline handled
`analysis` *best* of its three classes (F1 0.63); fine-tuning destroyed it.

### Confusion matrix — fine-tuned model (rows = true, cols = predicted)

|  | pred analysis | pred hot_take | pred reaction | total |
|---|---|---|---|---|
| **true analysis** | 0 | 7 | 1 | 8 |
| **true hot_take** | 0 | 12 | 3 | 15 |
| **true reaction** | 0 | 6 | 10 | 16 |
| **total** | **0** | **25** | **14** | 39 |

The `analysis` column is **all zeros** — the model never once predicted `analysis`. All 8 true
`analysis` comments were pushed into `hot_take` (7) or `reaction` (1). The committed image
[confusion_matrix.png](confusion_matrix.png) is the same data.

### Three wrong predictions, analyzed

**Error 1 — `analysis` → `hot_take` (conf 0.38).**
*"The thing about math is that after you do all the crunching, you need to apply sanity to
validate that your answer is correct. If your crunching says the ball travelled at the speed of
light when you dropped it off a building, you did the math wrong…"*
This is unambiguous `analysis` — a developed argument about validating models against reality.
The model called it `hot_take`. **Why:** the `analysis` class is dead (0 predictions), so every
`analysis` example is *forced* into another class; a long, opinionated-sounding comment lands in
`hot_take`. This is **not** a labeling problem (the true label is clearly defensible) — it's a
training problem: ~34 `analysis` training examples + 3 epochs gave the model no separable signal
for the class, and at 0.38 confidence it's essentially guessing.

**Error 2 — `analysis` → `hot_take` (conf 0.37).**
*"Well played from Marks and ESPN. He's sparked a huge controversy… just by misrepresenting what
some analyst told him. It's pretty obvious, if you stop and think…"*
A developed argument about media incentives → predicted `hot_take`. Same root cause as Error 1.
This one *also* sits near the genuine `analysis`/`hot_take` boundary I flagged in planning.md
(its assertive tone — "It's pretty obvious" — surface-resembles a hot take), so it's a hard case
*even for a working model*. But the failure here isn't a close boundary call — the model has no
`analysis` boundary at all.

**Error 3 — `hot_take` → `reaction` (conf 0.40).**
*"A decade of pump-faking star trades got them Giannis. Fair play Pat Riley."*
A `hot_take` (an evaluative claim that Riley's long-game strategy paid off) read as `reaction`.
**Why:** it's short and ends on light praise ("Fair play"), which pattern-matches the emotional
/ celebratory `reaction` class. With no length/structure cue and near-random confidence (0.40),
the model defaulted. This is the **second** confusion axis (`hot_take` ↔ `reaction`), where short
opinion vs. short emotion is genuinely hard — and the model leans on emotional surface words
rather than the claim/feeling distinction.

**The dominant pattern:** the model learned to lean on **surface emotional markers** (caps,
length, celebratory words) to split `hot_take` vs `reaction`, and never learned the
*load-bearing-evidence* concept that defines `analysis`. Errors are directional: `analysis` →
`hot_take` (the reasoning class collapses into the assertion class) and `hot_take` ↔ `reaction`
on short posts.

### Sample classifications (fine-tuned model, with confidence)

All confidences cluster at 0.37–0.40 — the model is near-maximally uncertain on *every* input,
which is itself the diagnosis (it never sharpened its boundaries). Examples:

| Comment (truncated) | Predicted | Confidence | True | Correct? |
|---|---|---|---|---|
| "The Heat have finally done it" | reaction | 0.39 | reaction | ✓ |
| "I doubt his model actually says that. It's an anonymous source probably out of context…" | hot_take | 0.40 | hot_take | ✓ |
| "Game saving play" | hot_take | 0.39 | reaction | ✗ |
| "This can only be explained by watching, literally suffocated all night by Wemby" | hot_take | 0.39 | reaction | ✗ |
| "He plays like a champ. He makes mistakes yeah but he plays with so much effort and physicality." | reaction | 0.38 | hot_take | ✗ |

**Why the correct ones are reasonable.** *"The Heat have finally done it"* → `reaction` is a
sound call: it's a short, moment-tied exclamation at the Giannis-trade news with no standing
claim to argue with — textbook `reaction`. (Caveat: the model likely got there from surface cues
— brevity, no analytical structure — rather than truly grasping "feeling vs. claim," since its
confidence is only 0.39, the same near-random band as its mistakes.) *"I doubt his model
actually says that…"* → `hot_take` is also right: it's a confident, unargued assertion of doubt,
exactly the assert-without-evidence pattern. Notably, **every confidence — right or wrong — sits
at 0.38–0.40**, so the model is no more certain when it's correct than when it's wrong; the
confidence scores carry essentially no signal.

---

## Reflection: what the model learned vs. what I intended

I intended a three-way classifier that separates **reasoning** (`analysis`) from **assertion**
(`hot_take`) from **emotion** (`reaction`). What it actually learned is a *degenerate two-way*
classifier: it discards `analysis` entirely and splits the remaining space using **emotional
surface cues** (length, caps, celebratory words) rather than the discourse-act concept I was
trying to teach.

The gap is sharpest on the concept I cared about most. `analysis` is defined by something
abstract — whether the evidence is *load-bearing* — and that signal is both rare (19% of data,
~34 training examples) and subtle. DistilBERT, given 3 epochs on a small noisy set, took the
path of least resistance: ignore the hard rare class, optimize the two easy ones, and stay
maximally uncertain (every confidence ≈ 0.38). It overfit to the *easiest separable signal*
(emotional tone) and missed the *intended concept* (reasoning quality) completely. Tellingly,
the zero-shot baseline — which gets the concept from its pretraining and my prompt rather than
from 34 examples — handled `analysis` *best*. The lesson: for a subtle, low-frequency semantic
distinction, 200-odd examples isn't enough to beat a strong general model that already
understands the concept.

---

## Spec reflection

**One way the spec helped:** writing concrete success thresholds in planning.md §6 *before*
seeing results made the verdict objective. Instead of hand-waving "56% is okay-ish," I could
state flatly that the model failed every criterion I'd set (didn't beat the baseline; macro-F1
0.42 < 0.65; `analysis` F1 = 0; `analysis` recall = 0). The metrics plan also predicted the exact
failure: planning.md §5 hypothesized the main error cell would be (true=`analysis`,
pred=`hot_take`), and the confusion matrix confirmed it — which turned a mysterious bad score
into a diagnosable mechanism.

**One way the implementation diverged:** my Milestone-1 label spec defined `analysis` strictly as
"argument backed by statistics / historical comparison / tactical observation." During
annotation I hit genuinely-reasoned comments with *no* hard stats (difficult example #3 above),
so I widened `analysis` to include developed multi-step reasoning, and pushed bare-but-confident
assertions to `hot_take`. I documented this in planning.md §9 rather than silently relabeling.
(A second, larger divergence: planning assumed fine-tuning would *beat* the baseline and the open
question was boundary subtlety — in reality fine-tuning lost outright and a whole class died,
which reframed the entire evaluation around "why did the model collapse a class.")

---

## AI usage

1. **Taxonomy design & label stress-testing.** I directed Claude to generate boundary posts
   between `analysis`/`hot_take` and `hot_take`/`reaction` and to pressure-test my definitions.
   It produced the cases that led to the "load-bearing vs. decorative evidence" rule; I overrode
   it by adding the *moment-tied-emotion* carve-out (a stat-jab that's venting is `reaction`,
   not `hot_take`).
2. **Data tooling.** Claude wrote the Reddit web-dump parser and the dataset-builder scripts; I
   directed the exclusion rules (what counts as non-discourse) and verified the output.
3. **Failure-pattern analysis.** Claude examined the misclassification list and surfaced the two
   patterns reported above (the `analysis`→`hot_take` collapse and the flat ~0.38 confidences);
   I verified both directly against the confusion matrix and the raw per-example confidences
   before including them.

---

## Repository structure

```
planning.md                     design spec (6 questions + AI tool plan + hard cases)
data/takemeter_labeled.csv      256 labeled comments (text, label, notes) — single file
data/evaluation_results.json    accuracy summary from Colab
confusion_matrix.png            fine-tuned confusion matrix (image)
scripts/parse_webdump.py        Reddit web-dump -> labelable CSV
scripts/build_dataset.py        -> final takemeter_labeled.csv
```

## Roadmap

- [x] M1 — community + labels
- [x] M2 — planning.md spec
- [x] M3 — 256-comment labeled dataset
- [x] M4 — zero-shot Groq baseline (64.1%)
- [x] M5 — fine-tuned DistilBERT (56.4%, honest negative result)
- [x] M6 — evaluation report (this README) · demo video pending
