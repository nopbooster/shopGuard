# ShopGuard

**Measuring indirect prompt injection in production-style AI shopping assistants.**

> **Status: work in progress.** Stage 1 (retrieval exposure) is complete. Stage 2 (model hijack rate) and Stage 3 (defenses) are being built. Results below are preliminary and will be updated as the study progresses.

## Why this exists

AI shopping assistants read product data and recommend items to customers. In many stores, that product data is written by someone other than the store owner: marketplace vendors, supplier feeds, bulk imports. Anyone who can edit a product description can try to place instructions in it that the AI then follows. This is **indirect prompt injection**.

ShopGuard is an offline, reproducible study of this risk, built around the architecture of a real, deployed product: an AI shop assistant plugin for [nopCommerce](https://www.nopcommerce.com/) that uses keyword search to retrieve products and sends them to a language model (Claude by default; the plugin is model-agnostic).

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
| **Attacker controls** | Product name, descriptions, specs |
| **Attacker cannot touch** | System prompt, plugin code, the model |
| **Harms measured** | Ranking manipulation, competitor disparagement, phishing / off-site redirection, system-prompt leakage |

## Design

| Component | File | Description |
|---|---|---|
| Catalog | `data/catalog.json`, `src/catalog.py` | 50 fictional products across 8 categories |
| Queries | `data/queries.json` | 40 realistic shopper questions, including one with no match |
| Retrieval | `src/retrieval.py` | Keyword search approximating the plugin's search step |
| Attacks | `src/attacks.py` | 4 harm goals × 3 phrasing styles (blunt, fake system notice, subtle), with optional keyword stuffing |
| Exposure | `scripts/measure_exposure.py` | Stage 1 measurement, no API calls |

Planned: model runner, LLM-based judge with human spot checks, defense variants (prompt warning, untrusted-data delimiting, output checker, retrieval-level filtering), and a cross-model comparison.

## Preliminary results

### Stage 1: Retrieval exposure

Five low-traffic products (a kettle, a wallet, a water bottle, a speaker, a keyboard combo) were poisoned, and all 40 queries were run through keyword retrieval (top 5 results).

| Condition | Mean share of queries that retrieve the poisoned product |
|---|---|
| Injection only | 4% |
| Injection + keyword stuffing | 72% |

**Interpretation:** for keyword-search assistants, retrieval acts as a gatekeeper. A hidden instruction in an obscure product rarely reaches the model, but one line of stuffed keywords puts it in front of the model for most conversations. Catalog spam filtering is therefore a security control, not only an SEO concern.

**Limitations:** the retrieval module approximates the production plugin and has not yet been validated against it. Exposure depends heavily on which fields are searched; if only product names are searched, description stuffing has no effect and an attacker would target names or tags instead. The catalog and query set are small and synthetic.

## Quick start

```bash
git clone https://github.com/nopbooster/shopguard.git
cd shopguard
python3 src/catalog.py              # regenerate data/catalog.json
python3 scripts/measure_exposure.py # Stage 1, no API key needed
```

Requires Python 3.10+. Stage 1 uses only the standard library. Later stages will need `pip install -r requirements.txt` and an `ANTHROPIC_API_KEY` environment variable.

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
- [ ] Stage 2: model runner and hijack-rate measurement
- [ ] LLM judge with human-labelled validation sample
- [ ] Stage 3: defenses and helpfulness cost
- [ ] Cross-model comparison
- [ ] Extension: injection in an AI product-translation plugin
- [ ] Write-up

## Author

Ayushman Bajracharya, [NopBooster](https://nopbooster.com) / Creatrix Technologies.

## License

MIT. See [LICENSE](LICENSE).
