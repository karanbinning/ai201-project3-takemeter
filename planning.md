# TakeMeter — Planning

A fine-tuned text classifier that measures **discourse quality** on r/nba by sorting comments
into the *kind of discourse act* they perform — reasoning, asserting, or emoting — rather than
judging whether the take is correct.

This document is my working spec: the design decisions made *before and during* annotation. The
README is the polished after-the-fact report; this is the reasoning behind it.

---

## 1. Community

**Choice: [r/nba](https://www.reddit.com/r/nba/).**

It's the largest basketball discussion subreddit (~15M members), and its comment threads are
unusually varied in quality within a single thread: a game thread can hold a film-study
breakdown, a confident hot take, a pure scream of joy, and a pun chain, all replying to the
same post. That spread is exactly what a discourse-quality classifier needs — if every comment
looked the same, there'd be nothing to learn.

It's also a good fit because the community **already talks about take quality in its own slang**:
"hot take" is an insult, "W analysis" is praise, "ratio'd" punishes bad takes. So the labels I
want to predict aren't imposed from outside — they track distinctions r/nba users themselves
make. And the volume is huge, so collecting 200+ varied public comments is trivial.

**What I'm measuring (and not):** not *correctness* (is this take right?) but *discourse act*
(does this comment reason, assert, or emote?). A wrong-but-reasoned comment is still `analysis`;
a correct-but-unargued shout is still `hot_take` or `reaction`.

---

## 2. Labels

Three labels on one axis — **how much reasoning the comment contains**: `analysis` > `hot_take`
> `reaction`. (Three, not two, to avoid a single label swallowing everything; not four, because
a fourth would blur the boundaries.)

### `analysis`
A comment that builds a genuine argument — either backed by specific, verifiable evidence
(stats, historical comparison, tactical/film observation) **or** developed through multi-step
reasoning — where the reasoning *is the point* of the comment.

- *"Draft picks are the lifeblood of a small market team like Milwaukee which struggles to sign
  FAs. You draft a Giannis-tier player or you trade for one. Either way you need as much draft
  capital as you can get. Has this sub learned nothing from watching Sam Presti?"*
- *"It's a lost art because it was always just a bad shot. Three is exactly 50% more than two.
  Pretty much no one hits 50% more shots from 20 feet than from 24, so it's almost always a bad
  idea to take long twos. You don't need advanced models to figure that out."*

### `hot_take`
A bold, confident **evaluative claim, ranking, or prediction asserted without genuine
supporting evidence** — it asserts rather than argues (any stats present are decorative or
cherry-picked, not load-bearing).

- *"He's straight up taken the face of the league. If he wins the Finals he'll be cemented as
  that firmly. It's his NBA now. It's his era."*
- *"Anyone who finds any billionaire actually likable is a gullible rube."*

### `reaction`
An immediate **emotional response to a specific moment** — excitement, despair, celebration,
disbelief, hatred — with little or no standing claim to argue with; the comment expresses a
feeling, not a point.

- *"GLORIOUS HATEWATCH"*
- *"That dunk was majestic. Literally fell to my knees in front of the TV when he did it.
  Basketball nirvana."*

### Decision rules (mutual exclusivity)
- **`analysis` vs `hot_take`** — *evidence/reasoning test:* strip the opinion framing. Is what
  remains a specific, verifiable, load-bearing argument (or a real multi-step chain of
  reasoning)? Yes → `analysis`. Is it a bare assertion, or evidence that's decorative /
  cherry-picked / just-enough-to-sound-credible? → `hot_take`.
- **`hot_take` vs `reaction`** — *claim test:* does it make an evaluative claim you could argue
  with tomorrow ("X is overrated", "they win the title")? → `hot_take`. Is it pure
  moment-tied emotion with no standing claim? → `reaction`.
- **`analysis` vs `reaction`** rarely collide; if they do, reasoning present → `analysis`.

### Things that are *not* discourse (excluded, not labeled)
Puns/memes, song lyrics, off-topic tangents (movies, the Sheboygan/Polka bit), the
LeBron-Constantinople name game, pure logistics ("what channel?"), and single-emoji/link-only
replies. These are excluded at collection time, keeping ≥90% coverage with no catch-all bucket.
In practice they were ~42% of raw comments (see §7) — r/nba banter is heavy.

---

## 3. Hard edge cases

**Anticipated boundary (set before annotating):** the *"analysis-flavored hot take"* — a single
cherry-picked stat wrapped in accusatory framing. The rule: a stat used to *decorate* a
pre-decided verdict is not load-bearing → `hot_take`; it's only `analysis` if the comment
actually reasons *with* the evidence.

**Three real cases that gave me genuine pause during annotation** (these also carry a `notes`
entry in the dataset CSV):

1. **`reaction` vs `hot_take`** — *"THEY REALLY GAVE CHET THE MAX 🤣🤣🤣 Type of guy to shoot 2
   shots in a Game 7. Fucking embarrassing."*
   This is the textbook "single-stat jab" I'd flagged in advance, so I expected `hot_take`. But
   the dominant content is *emotional mockery tied to a just-watched moment* (🤣, "embarrassing"),
   not a standing arguable thesis. **Decision: `reaction`.** Refined rule: a stat-jab that's
   venting about a moment → `reaction`; a stat-jab making a durable evaluative claim (e.g.
   "Embiid is a fraud, 0-for past the 2nd round") → `hot_take`.

2. **`analysis` vs `hot_take`** — *"Except curry is still dropping over 25 in half the games he
   plays — edit: oh yeah and lebron single-handedly beat the rockets in the playoffs."*
   It cites real production, which *looks* like evidence. But the stats are thrown out to
   *dismiss* a narrative rather than to build an argument — decorative and cherry-picked.
   **Decision: `hot_take`.**

3. **`analysis` vs `hot_take`** — *"I kinda respect it as a strategy. If you don't have an actual
   shot at a championship with an aging superstar, your only options are to blow it up or make
   high-risk moves that increase your ceiling, even if you're 90% likely to flop."*
   No statistics at all — by the strict "evidence" reading this could be `hot_take`. But it's a
   genuine multi-step argument (states the constraint, enumerates the options, weighs them).
   **Decision: `analysis`.** This forced an explicit refinement to my Milestone-1 definition
   (see §9).

---

## 4. Data collection plan

- **Source:** public r/nba comment threads only (no auth-gated content). Collected by opening
  threads in the browser and copying the page text, then parsing it into a CSV with a small
  script (`scripts/parse_webdump.py`) that strips Reddit UI chrome, drops non-discourse noise,
  and dedupes. Reddit blocks scripted fetches from my environment, so collection stayed manual.
- **Thread mix (to force class variety):** I deliberately sampled across thread *types* because
  each skews toward a different label —
  - trade-rumor / news threads (LeBron-to-Warriors, Kawhi/Plaschke) → `hot_take` + `analysis`
  - elimination / hatewatch + game threads (OKC eliminated, Spurs G7) → `reaction`
  - analytics / stats arguments (the Jaylen Brown plus-minus debate) → `analysis`
- **Target:** ≥200 usable labeled comments, aiming ≥20% per class.
- **If a label is underrepresented after 200** (anticipated to be `analysis`, which is the
  rarest in the wild): collect *additional threads of the type that produces it* — i.e.
  tactical/stats discussion threads — rather than re-labeling existing comments more
  generously. This is exactly what happened: after the first paste `analysis` was only 36, so I
  added an analytics-heavy thread, which lifted it to 49 (see §7).

---

## 5. Evaluation metrics

Accuracy alone is **not** sufficient here for two concrete reasons: (a) the classes are
imbalanced (`analysis` ≈ 19%, `reaction` ≈ 42%), so a model that ignores `analysis` entirely
could still post ~80% accuracy while being useless for the one class that matters most; and (b)
the *direction* of errors is the whole point of the analysis. So I'll report:

- **Overall accuracy** — headline number, and the thing the fine-tuned model must beat the
  baseline on.
- **Per-class precision, recall, and F1** — F1 is the key per-class number. I care most about
  **`analysis` recall**: in a real community tool the valuable job is *surfacing the good takes*,
  so missing them (low recall) is the costly failure.
- **Macro-averaged F1** — averages the three class F1s equally, so the rare `analysis` class
  counts as much as `reaction`. This is my single headline quality number because it refuses to
  reward majority-class guessing.
- **Confusion matrix** — to read the *direction* of confusion. My hypothesis is the main error
  cell will be (true=`analysis`, pred=`hot_take`): both are "opinion about basketball," and the
  only difference is whether the reasoning is load-bearing — a subtle signal for 200-ish
  examples.
- **Baseline-vs-fine-tuned on the identical locked test set** — the comparison is what gives the
  fine-tuned numbers meaning.

---

## 6. Definition of success

Concrete, checkable thresholds (set now so the verdict at the end is objective, not vibes):

| Criterion | Threshold |
|---|---|
| Beats majority-class baseline (always-predict `reaction` ≈ 42%) | accuracy clearly > 42% |
| Beats the zero-shot Groq baseline | fine-tuned accuracy **and** macro-F1 > baseline's |
| Overall quality | **macro-F1 ≥ 0.65** |
| No dead class | every per-class **F1 ≥ 0.55** |
| Surfaces good takes | **`analysis` recall ≥ 0.60** |

**"Good enough for a real community tool":** macro-F1 ≈ 0.70+ with `analysis` recall ≥ 0.60.
At that level TakeMeter could power a *human-in-the-loop* feature — e.g. auto-flagging likely
`analysis` comments to pin, or letting users filter a thread down to substance — where a
moderator still makes the final call, so occasional misses are tolerable. I would **not** claim
it's good enough to *auto-remove* `hot_take`/`reaction` comments; the boundary is too subjective
and the cost of a false removal too high.

If the fine-tuned model can't clear macro-F1 0.65, the honest read is that 200-ish examples
isn't enough to teach the `analysis`/`hot_take` boundary — a finding worth reporting, not hiding.

---

## 7. Annotation results (Milestone 3)

- **Raw comments parsed:** 444 (across 4 thread topics), after dropping 14 noise items.
- **Usable labeled:** **256** (the other 188 raw comments were non-discourse → excluded).
- **Single labeled file:** `data/takemeter_labeled.csv` (columns: `text`, `label`, `notes`),
  not pre-split — the notebook does the 70/15/15 split.

| Label | Count | Share |
|---|---|---|
| `analysis` | 49 | 19.1% |
| `hot_take` | 100 | 39.1% |
| `reaction` | 107 | 41.8% |
| **total** | **256** | |

Largest class = 41.8%, well under the 70% imbalance limit. `analysis` sits just under the 20%
aspirational floor; I topped it up once (36 → 49) by adding an analytics thread and judged 19.1%
acceptable rather than over-collecting. The split script will be stratified so the test set
isn't starved of `analysis`.

---

## 8. AI Tool Plan

There's no application code to generate here, so AI assistance is concentrated in three places.
An explicit decision is recorded for each.

**A. Label stress-testing — USED.**
Before locking definitions I had the AI generate boundary posts between `analysis`/`hot_take`
and `hot_take`/`reaction` and tried to classify them. The cases it surfaced (single-stat jabs,
unargued historical name-drops) are what produced the refined decision rules in §2–3. Outcome:
tightened "load-bearing vs decorative evidence" and the moment-tied-emotion carve-out.



**C. Failure analysis — PLANNED (Milestone 6).**
After fine-tuning I'll paste the misclassified test examples into an LLM and ask it to find
patterns (label pair confused most, post length, sarcasm, low-information posts). I'll then
**verify each claimed pattern by re-reading the actual examples** before it goes in the report,
and I'll note anything I had to discard as a false pattern.

---

## 9. Operational rules & divergences from Milestone 1

- **Refinement (divergence):** Milestone 1 defined `analysis` strictly as "structured argument
  backed by statistics, historical comparison, or tactical observation." During annotation I hit
  comments with genuine multi-step reasoning but *no* hard stats (case 3 in §3). I widened
  `analysis` to include developed reasoning, not only evidence-citing, and pushed bare assertions
  (even confident ones) to `hot_take`. Documented here so the spec-vs-implementation gap is
  honest.
- **Reaction/hot_take carve-out:** moment-tied emotional jabs that happen to contain a stat are
  `reaction`, not `hot_take`, unless they make a durable arguable claim (§3 case 1).

---

## Milestones 4–6 — TODO
- M4: zero-shot Groq `llama-3.3-70b-versatile` baseline on the locked test set.
- M5: fine-tune `distilbert-base-uncased` (Colab T4).
- M6: evaluation report, README, demo.

*Stretch features intentionally skipped. This file will be updated before starting any.*
