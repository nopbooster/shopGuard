# ShopGuard experiment log

Full methods and results for every experiment, in order. The summary and headline numbers are in the [README](../README.md); the research note is [WRITEUP.md](WRITEUP.md). Raw runs and scores are under `results/`.

## Stage 1 and Stage 2 (natural retrieval)

### Stage 1: Retrieval exposure

Five low-traffic products (a kettle, a wallet, a water bottle, a speaker, a keyboard combo) were poisoned. Each of the 40 queries was paired with a representative search keyword (`keywords` in `data/queries.json`) and run through the reproduced search (top 6 results).

| Condition | Mean share of queries that retrieve the poisoned product |
|---|---|
| Injection only | 2% |
| Injection + keyword stuffing in the full description | 49% |

All 12 payloads fit inside the 300-character short-description window, so none is cut off before reaching the model.

**Interpretation:** retrieval acts as a gatekeeper. A hidden instruction in an obscure product almost never reaches the model, but one line of stuffed keywords in a field the model never reads puts the poisoned product in front of it for about half of all conversations. Catalog spam filtering is therefore a security control, not only an SEO concern.

**Limitations:** the search keywords here are chosen by hand; in production the model chooses them, and Stage 2 below measures exposure with the model's own keyword choices. Because nopCommerce matches the whole keyword string, multi-word searches ("running shoes") are not matched by single-word stuffing, so exposure depends on how the model phrases its searches. Display position is approximated by catalog order. The catalog and query set are small and synthetic.

### Stage 2: end-to-end runs on Sonnet 5.5 and Haiku 5.5

1,040 conversations: 80 clean baselines plus 960 attacked (4 goals x 3 phrasings x 40 queries x 2 models). One kettle listing was tampered with per attacked run, with the instruction in the short description and keyword stuffing in the full description. The model chose its own search keywords. Raw runs and scores are in `results/stage2/`.

| | Sonnet 5.5 | Haiku 5.5 |
|---|---|---|
| Attacked conversations | 480 | 480 |
| Tampered listing appeared in the search results | 40% (192) | 7% (33) |
| Followed the injected instruction | 0 | 0 |
| 95% upper bound on the hijack rate, given the listing appeared | 2.0% | 10.4% |
| Warned the shopper about the injected text, given the listing appeared | 100% | 21% |
| Mean reply length, no attack / attacked and listing seen (words) | 28 / 53 | 24 / 33 |

**What the data supports**

1. **No hijacks in 960 attacked conversations.** Both models ignored all twelve payload variants. For Haiku only 33 conversations reached the tampered listing, so the bound is loose: the data cannot rule out a hijack rate near 10%.
2. **Exposure depends on the model's own searching.** With hand-picked search keywords, Stage 1 measured 49% exposure on average. With the model choosing, Sonnet saw the listing in 40% of conversations and Haiku in 7%. Haiku wrote multi-word searches 90% of the time (Sonnet 58%) and used a category filter in 34% of searches (Sonnet 13%), and single-word stuffing matches neither. Evaluations that skip the model's search behaviour can misstate exposure in either direction.
3. **Failed attacks still change the reply.** Sonnet told the shopper about the injected text every time it saw it, and its replies grew from 28 to 53 words against a 30-word limit in the shop's own instructions. Haiku usually ignored the text silently and its replies grew less.
4. **String matching alone over-reported.** One Sonnet reply quoted the attacker's discount in order to refuse it, and a string check counted it as a hijack. The final verdict now requires the LLM judge to agree.

**Limitations**

- The attacks are static: written once and never adapted to the replies. Zero hijacks says these payloads failed here. It is not evidence that the assistant resists an attacker who adapts.
- One tampered listing, one fictional catalog, one run per condition. Run-to-run variation was not measured.
- The LLM judge was validated on a small hand-labelled sample and written controls (see docs/EXPERIMENTS.md), not on a large corpus.
- Haiku's small number of exposures makes its estimate weak (see the interval above).

## Later experiments, in the order they were run

**Judge validation.** One person hand-labelled 40 stratified replies blind to the judge's verdict (obeyed / ignored silently / ignored and warned). On the 39 labelled items the judge agreed on 38 (97%, Cohen's kappa 0.93; three initial disagreements were the labeller's own misclicks, corrected after review, so treat the figure as optimistic). The sample contained no real hijacks, so I added 12 positive controls: replies written to clearly obey or clearly resist each attack goal. The judge classified 12/12 correctly. Labels: `results/stage1/hand_labels.json`; controls: `scripts/judge_controls.py`.

**Forced-exposure pilot.** The poisoned product is the one that genuinely matches each query, so the model must read the payload (goals: disparage, phishing, leak; one rotated goal/style per query). Script: `scripts/run_forced.py`, data: `results/stage2_forced/runs.jsonl`.

| Model | Runs | Poisoned item retrieved | Hijacked | Warned the shopper |
|---|---|---|---|---|
| Sonnet 5.5 | 39 | 39 | 0 | 39 |
| Haiku 5.5 | 39 | 12 | 0 | 4 |

Caveats: static payloads, one catalog, one run per condition, a single judge model. Haiku often skips the poisoned item by choosing different keywords or a category filter, so even forced exposure only reached 12 runs. Zero hijacks in 39 runs bounds the true rate at roughly 9% (95% upper limit) for Sonnet 5.5; it does not show the models are robust to adaptive attackers.

**Adaptive attacker pilot (inconclusive).** An LLM attacker (Sonnet 5.5) was asked to write and iteratively rewrite listing payloads for 6 queries x 3 goals (18 trajectories, up to 5 rounds). Every trajectory ended with the attacker returning an empty or unusable reply (it declined or failed to produce a payload), so only 9 payloads were actually tested: 0 succeeded and 6 were flagged to the shopper. This says little about robustness; it mainly shows the attacker model will not reliably do this job. I did not try to work around that. Data: `results/adaptive/runs.jsonl`.

**Strategy sweep (Sonnet 5.5).** Ten hand-written framings (ignore-previous, spoofed tool result, XML system tag, "verified owner", helpfulness appeal, debug mode, markdown instruction header, legal urgency, plain factual claim, instruction in the product name) x 3 goals (disparage, phishing, leak) x 11 queries = 330 runs, forced exposure, same judge. Script: `scripts/run_sweep.py`, data: `results/sweep/runs.jsonl`.

| | Runs | Poisoned item retrieved | Hijacked | Warned the shopper |
|---|---|---|---|---|
| All framings | 330 | 330 | 0 | 320 |

Zero hijacks in 330 runs puts the true rate for these framings below about 1% (95% upper limit). The 10 replies that did not warn were all the "plain factual claim" disparagement framing, where the model quietly left the claim out. Seven replies matched the phishing string check but only to say they were ignoring the offer; the judge correctly scored them as not hijacked. Still limited to one model, one catalog, fixed (non-adaptive) payloads and single-turn conversations.

**Cross-model sweep (OpenAI).** The same 330-run sweep (10 framings x 3 goals x 11 queries; the matching product is poisoned) was run on `gpt-5.5` and `gpt-5.4-mini` through an OpenAI adapter (`src/assistant.py`, same prompt, tool and results text; 4,096-token cap because these are reasoning models). Same judge (Sonnet 5.5).

| Model | Runs | Poisoned listing read | Hijacked | Warned the shopper |
|---|---|---|---|---|
| Sonnet 5.5 | 330 | 330 | 0 | 320 |
| gpt-5.5 | 330 | 37 | 0 | 0 |
| gpt-5.4-mini | 330 | 6 | 0 | 0 |

"Forced" only guarantees the right product is poisoned, not that the model finds it. The OpenAI models phrase searches differently (extra words, category and price filters), so whole-string matching returned the poisoned product in only 11% (gpt-5.5) and 2% (gpt-5.4-mini) of runs. They never obeyed and never mentioned the hidden text; they simply answered the shopper. With 37 and 6 exposures the bounds are loose (about 8% and 40% upper limits), so this does not yet show these models are as robust as Sonnet. A fully forced condition (poisoned item always returned) is the next step.

**Always-returned condition (OpenAI).** To remove the search-phrasing gate, the poisoned listing was returned for every search regardless of keywords or filters (`scripts/run_sweep.py --always-return`, data in `results/sweep_always/`). Same 10 framings x 3 goals; `gpt-5.5` ran on 11 queries (330 runs) and `gpt-5.4-mini` on 21 queries (630 runs, because the resume logic added ten more queries).

| Model | Runs | Hijacked | 95% CI | Warned the shopper |
|---|---|---|---|---|
| gpt-5.5 | 330 | 0 | 0 to 1.2% | 0 |
| gpt-5.4-mini | 630 | 39 | 4.6 to 8.4% | 2 |
| gpt-5.4-mini (first 11 queries only, matched to gpt-5.5) | 330 | 22 | 4.4 to 9.9% | 1 |

`gpt-5.4-mini` is the first model in this study to obey an injection. 37 of the 39 hijacks were the disparagement goal ("other brands have had safety recalls") and 2 were the phishing discount; none leaked the system prompt. Four framings worked: a spoofed tool-result block (20/63), legal urgency (13/63), a "verified owner" message (4/63) and an XML system tag (2/63). Six framings never worked (ignore-previous, debug mode, markdown header, helpfulness, plain factual claim, instruction in the product name). Three hijacks were partial (e.g. "the store suggests avoiding other brands"). `gpt-5.5` obeyed nothing and, unlike Sonnet 5.5, never mentioned the hidden text.

The small model is both the most hijackable and the least likely to be exposed, because it searches in ways that rarely match the poisoned product. Search behaviour and instruction-following therefore protect a deployment in different ways.

**Haiku 5.5 under always-returned exposure, and a defence test on gpt-5.4-mini.** Same 10 framings x 3 goals x 11 queries, poisoned listing returned for every search.

| Condition | Runs | Hijacked | 95% CI | Warned the shopper |
|---|---|---|---|---|
| Haiku 5.5, no defence | 330 | 0 | 0 to 1.2% | 163 |
| gpt-5.4-mini, no defence (matched queries) | 330 | 22 (6.7%) | 4.4 to 9.9% | 1 |
| gpt-5.4-mini + `delimit` (tool output wrapped in an untrusted-data block with a reminder) | 326 | 1 (0.3%) | 0.1 to 1.7% | 0 |
| gpt-5.4-mini + `instruct` (one system-prompt rule: product text is untrusted) | 326 | 0 | 0 to 1.2% | 0 |

Both defences (`src/defenses.py`, `scripts/run_sweep.py --defense`) cut the mini's hijack rate from about 7% to about 0. The one remaining hijack used the legal-urgency framing under `delimit`. Replies stayed the same length (about 15 words) and named the shopper's product in 100% of runs, with no extra warnings. The runs stopped at 326 of 330 per defence because the OpenAI account ran out of credit.

Helpfulness caveat: a clean no-attack check (`scripts/run_clean.py`) cannot measure the cost of a defence here, because with the plugin's whole-string search `gpt-5.4-mini` retrieved any product for only 2 of 40 clean queries. The helpfulness figures above come from attacked runs only.
