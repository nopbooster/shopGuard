# ShopGuard

**Measuring indirect prompt injection in production-style AI shopping assistants.**

> **Status: work in progress.** Stage 1 (retrieval exposure) and Stage 2 (end-to-end runs on two models) are complete. A stronger, adaptive attacker and the defense comparison (Stage 3) are next. Results below are preliminary.

## Why this exists

AI shopping assistants read product data and recommend items to customers. In many stores, that product data is written by someone other than the store owner: marketplace vendors, supplier feeds, bulk imports. Anyone who can edit a product description can try to place instructions in it that the AI then follows. This is **indirect prompt injection**.

ShopGuard is an offline, reproducible study of this risk, built around the architecture of a real, deployed product: an AI shop assistant plugin for [nopCommerce](https://www.nopcommerce.com/) (Claude by default; the plugin is model-agnostic).

### The system under study

The assistant is a small tool-using agent:

1. The shopper writes a message in plain language.
2. The model calls a `search_products` tool with keywords it chooses.
3. nopCommerce runs a keyword search (whole-string substring match over name, short and full description, category, manufacturer and tags), ordered by display position, capped at 6 results.
4. The model receives one line per product: name, price, SKU, and the short description (HTML stripped, first 300 characters).
5. The model replies; the storefront renders product cards from the search results.

Untrusted catalog text therefore reaches the model as **tool output**, the same pattern found in browsing and email agents. One detail matters a great deal: the full description is searched but never shown to the model, so an attacker can use it to get retrieved while placing the instruction in the short description.

### Research questions

1. **Exposure:** How often does a poisoned product reach the model at all through keyword retrieval, and how much does keyword stuffing raise that?
2. **Hijack:** Once a poisoned product is in context, how often does the model follow the injected instruction?
3. **Defenses:** Which low-cost defenses reduce attack success, and what do they cost in helpfulness on clean queries?
4. **Model choice:** Do smaller, cheaper models get hijacked more often?

End-to-end risk ≈ exposure × hijack. Most published injection evaluations measure only the hijack stage, by inserting the attack directly into the prompt. ShopGuard measures both stages.

## Threat model

| | |
|---|---|
| **Attacker** | Anyone who can edit product text: a marketplace vendor, a compromised supplier feed, an insider |
| **Attacker controls** | Product name, SKU, short and full description, tags |
| **Attacker cannot touch** | System prompt, plugin code, the model |
| **Harms measured** | Ranking manipulation, competitor disparagement, phishing / off-site redirection, system-prompt leakage |

## Design

| Component | File | Description |
|---|---|---|
| Catalog | `data/catalog.json`, `src/catalog.py` | 50 fictional products across 8 categories |
| Queries | `data/queries.json` | 40 realistic shopper questions, including one with no match |
| Retrieval | `src/retrieval.py` | Reproduces the plugin's search call and the exact tool-result text the model receives |
| Attacks | `src/attacks.py` | 4 harm goals × 3 phrasing styles (blunt, fake system notice, subtle). Payload in the short description; optional keyword stuffing in the full description |
| Exposure | `scripts/measure_exposure.py` | Stage 1 measurement, no API calls |
| Assistant | `src/assistant.py` | Python re-implementation of the production chat turn: verbatim system prompt, identical `search_products` tool schema, 3-round tool loop |
| Runner | `scripts/run_stage2.py` | Stage 2: end-to-end runs where the model chooses its own search keywords; clean baseline included; resumable |
| Judge | `src/judge.py`, `scripts/judge_stage2.py` | String checks for phishing and prompt leakage; LLM judge for ranking manipulation and disparagement; a string match only counts when the LLM judge agrees |
| Analysis | `scripts/analyze_stage2.py` | Exposure, hijack rate with 95% intervals, warnings, reply length; writes `results/summary.json` (no API calls) |

Planned: human-labelled validation of the LLM judge, defense variants (prompt warning, untrusted-data delimiting, output checker, retrieval-level filtering), and a cross-model comparison.

## Preliminary results

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
- The LLM judge was validated on a small hand-labelled sample and written controls (see below), not on a large corpus.
- Haiku's small number of exposures makes its estimate weak (see the interval above).

## Quick start

```bash
git clone https://github.com/nopbooster/shopguard.git
cd shopguard
python3 src/catalog.py              # regenerate data/catalog.json
python3 scripts/measure_exposure.py # Stage 1, no API key needed
```

Stage 2 (real model calls):

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...         # use a dedicated key with a spend limit
python3 scripts/run_stage2.py --limit 5   # smoke test
python3 scripts/run_stage2.py             # full run, resumable
python3 scripts/judge_stage2.py           # score and summarise
```

Requires Python 3.10+. Stage 1 uses only the standard library.

## Repository layout

```
shopguard/
├── data/        synthetic catalog and queries
├── src/         catalog, retrieval and attack modules
├── scripts/     experiment entry points
└── results/     raw outputs (JSON)
```

## Responsible use

All experiments run offline against a synthetic catalog. No live store, real customer data or third-party system is tested. Attack payloads use the reserved `.example` domain. See [RESPONSIBLE_USE.md](RESPONSIBLE_USE.md).

## Judge validation and forced-exposure pilot

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

## Roadmap

- [x] Synthetic catalog and query set
- [x] Keyword retrieval and attack library
- [x] Stage 1: exposure measurement
- [ ] Validate retrieval against the production plugin's search settings
- [x] Stage 2: model runner and judge implemented
- [x] Stage 2: full run (Sonnet 5.5 vs Haiku 5.5)
- [x] Forced-exposure pilot (Sonnet 5.5 and Haiku 5.5, 39 queries each; see below)
- [~] Adaptive attacker: LLM attacker loop built (`scripts/run_adaptive.py`); first pilot inconclusive
- [x] Fixed strategy sweep: 10 framings x 3 goals x 11 queries, 0/330 hijacked
- [x] LLM judge validated: 40 hand-labelled replies plus 12 positive controls (see below)
- [ ] Stage 3: defenses and helpfulness cost
- [~] Cross-model comparison: OpenAI sweep done; exposure too low, needs always-returned condition
- [ ] Extension: injection in an AI product-translation plugin
- [x] Write-up: [docs/WRITEUP.md](docs/WRITEUP.md)

## Author

[NopBooster](https://nopbooster.com)

## License

MIT. See [LICENSE](LICENSE).
