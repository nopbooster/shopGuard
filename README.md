# ShopGuard

**Measuring indirect prompt injection in production-style AI shopping assistants.**

> **Status: work in progress.** Stage 1 (retrieval exposure) is complete. Stage 2 (model hijack rate) and Stage 3 (defenses) are being built. Results below are preliminary and will be updated as the study progresses.

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
| Judge | `src/judge.py`, `scripts/judge_stage2.py` | String checks for phishing and prompt leakage; LLM judge for ranking manipulation and disparagement; summary tables |

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

**Limitations:** the search keywords here are chosen by hand; in production the model chooses them, and Stage 2 will measure exposure with the model's own keyword choices. Because nopCommerce matches the whole keyword string, multi-word searches ("running shoes") are not matched by single-word stuffing, so exposure depends on how the model phrases its searches. Display position is approximated by catalog order. The catalog and query set are small and synthetic.

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

## Roadmap

- [x] Synthetic catalog and query set
- [x] Keyword retrieval and attack library
- [x] Stage 1: exposure measurement
- [ ] Validate retrieval against the production plugin's search settings
- [x] Stage 2: model runner and judge implemented
- [ ] Stage 2: full run (Sonnet 5.5 vs Haiku 5.5)
- [ ] LLM judge validated against a human-labelled sample
- [ ] Stage 3: defenses and helpfulness cost
- [ ] Cross-model comparison
- [ ] Extension: injection in an AI product-translation plugin
- [ ] Write-up

## Author

[NopBooster](https://nopbooster.com)

## License

MIT. See [LICENSE](LICENSE).
