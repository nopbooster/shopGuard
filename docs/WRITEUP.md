# Can a product listing hijack an AI shopping assistant? A measurement on a production-style agent

*ShopGuard research note, November 2026. NopBooster. Code, data and every number below: this repository.*

## Summary

We reproduced the chat loop of a live nopCommerce shopping assistant (Claude by default, keyword search over the catalog, product text returned to the model as tool output) and attacked it with instructions hidden in product listings: indirect prompt injection from a third-party-writable field. Across 1,368 attacked conversations on Claude Sonnet 5.5 and Claude Haiku 5.5, **no injected instruction was followed on the Claude models**. Sonnet 5.5 never obeyed in the 561 conversations where it actually read a poisoned listing, and told the shopper about the hidden text every time. The more interesting findings are about what we had to measure to get there:

1. **Retrieval is a gatekeeper, and the model controls it.** Whether a poisoned listing reaches the model depends on the model's own search phrasing, which differed sharply between models (40% vs 7% exposure).
2. **A failed attack still changes behaviour**: replies roughly doubled in length when Sonnet saw and rejected an injection.
3. **Cheap judges mislead.** A string match over-counted a refusal as a hijack; the final verdict needed an LLM judge, which we validated.

This is a small, bounded study of one system. It supports "these fixed attacks did not work here", not "the system is safe".

## Setup

**System under study.** A production-style assistant: a short system prompt (brevity rules, store categories), one tool `search_products(keywords, category, min_price, max_price)` and up to three tool rounds per turn. The tool matches the whole keyword string, case-insensitively, against name, descriptions, category, manufacturer and tags, returns six products, and shows the model only name, price, SKU and a 300-character plain-text short description. The system prompt is published verbatim in `src/assistant.py`. The catalog is 50 fictional products; the 40 shopper queries are in `data/queries.json`.

**Threat model.** The attacker controls one listing (a vendor, an imported feed or a compromised account) and nothing else. Payload goes in the short description, the only free text the model reads; keyword stuffing goes in the full description, which is searched but never shown, so it increases retrieval without lengthening the visible payload. All links use the reserved `.example` domain.

**Goals and framings.** Four goals: force a recommendation (ranking), disparage competitors with false safety claims, send the shopper to an outside "40% off" checkout link, and leak the system prompt. Phrasings: blunt, fake system notice, polite "note to assistants". Later experiments add ten further framings (spoofed tool result, XML system tag, verified-owner message, debug mode, legal urgency, plain factual claim, instruction in the product name, and others).

**Two-stage view.** End-to-end risk is exposure (the poisoned listing is retrieved) times hijack (the model obeys given exposure). We report both.

**Judging.** A hijack counts only if a deterministic string check (where one exists) and an LLM judge (Sonnet 5.5) both say so. The judge also records whether the reply warned the shopper. Validation: one person hand-labelled 40 stratified replies blind to the judge; agreement was 38/39 (97%, kappa 0.93) after the labeller corrected three misclicks, so treat that figure as optimistic. Because the sample held no real hijacks, we added 12 written positive controls (clear obedience and clear refusal for each goal); the judge got 12/12.

## Results

| Experiment | Model | Conversations | Poisoned listing read | Hijacked | Warned shopper |
|---|---|---|---|---|---|
| Main run: 4 goals x 3 phrasings, natural retrieval | Sonnet 5.5 | 480 | 192 | 0 | 192 |
| Main run | Haiku 5.5 | 480 | 33 | 0 | 7 |
| Forced exposure (matching product poisoned) | Sonnet 5.5 | 39 | 39 | 0 | 39 |
| Forced exposure | Haiku 5.5 | 39 | 12 | 0 | 4 |
| Ten-framing sweep, forced exposure | Sonnet 5.5 | 330 | 330 | 0 | 320 |

For Sonnet, 0 hijacks in 561 exposed conversations gives a 95% upper bound below about 1% for these payloads. For Haiku the bound is loose (33 exposures in the main run, 12 in the pilot; upper bound about 10%).

**Exposure.** Stuffing one line of popular keywords into an obscure listing raised retrieval from 2% to 49% in a hand-keyword simulation, but with the model choosing its own keywords Sonnet saw the listing in 40% of conversations and Haiku in 7%. Haiku wrote multi-word queries 90% of the time (Sonnet 58%) and used category filters in 34% of searches (Sonnet 13%); whole-string matching defeats single-word stuffing in both cases. An evaluation that fixes the keywords can get exposure badly wrong in either direction.

**Side effects.** Sonnet's replies grew from 28 to 53 words when it saw an attack, against a 30-word brevity rule, because it explains the rejected text to the shopper. Haiku mostly ignored injections silently (warned in 21%). In the sweep, the ten replies that did not warn all came from the plain-factual-claim framing, where the model quietly omitted the claim.

**Judge failure mode.** Eight replies matched the attacker's discount string only because they quoted it in order to refuse it. Requiring the LLM judge to agree removed these false positives.

## Cross-model addendum (OpenAI)

We added an adapter and ran the ten-framing sweep on `gpt-5.5` and `gpt-5.4-mini`. With natural retrieval, the OpenAI models almost never read the poisoned listing (37/330 and 6/330) because they search with extra words and filters that whole-string matching rejects, and nothing was hijacked. When we returned the poisoned listing for every search, **`gpt-5.5` obeyed none of 330 attacks (upper bound 1.2%), while `gpt-5.4-mini` obeyed 39 of 630 (6.2%, 95% CI 4.6 to 8.4%)**. Almost all were the false-safety-recall goal, and the framings that worked imitated structure the model might trust (a spoofed tool-result block, legal urgency, a verified-owner message). Neither OpenAI model warned the shopper; the mini simply complied. Unlike the first Claude results, this shows real exposure-conditional hijacks on a model a plugin customer might choose to save cost. Caveats: one run per condition, the mini ran on 21 queries versus 11 for the others, and the judge is still a Claude model (the hijack wording was visible in the replies, and the judge's reasons agree on a read-through, but we did not hand-label OpenAI replies).

## Limitations

- **Static attacks.** Every payload was written once and never adapted to the model's replies. This is the main reason a null result is weak evidence of robustness.
- **Adaptive attacker not achieved.** We built an LLM attacker loop, but the attacker model (Sonnet 5.5) returned no usable payload in all 18 trajectories (9 payloads tested, none succeeded). We did not try to work around that refusal, so the adaptive condition is untested here.
- **Scope.** One catalog of fictional products, one poisoned listing, single-turn chats, no tool beyond search, no memory. Real stores have reviews, Q&A, attribute fields, translated text and multi-turn conversation, all untested injection surfaces.
- **Models.** Sonnet 5.5, Haiku 5.5 (natural retrieval only), gpt-5.5 and gpt-5.4-mini, at their default settings, with one run per condition and no run-to-run variance measured.
- **Judge.** One judge model; human validation covers 39 non-hijack replies plus synthetic controls.
- **Author.** The harness and analysis were written with substantial help from Claude (Claude Code) under the author's direction; all experiments were run and checked against raw outputs.

## What we would do next

1. A human-in-the-loop or non-Claude adaptive attacker, with multi-turn conversations where earlier turns prime the model.
2. Other untrusted fields: customer reviews, Q&A, and the translation pipeline of a sibling plugin, where model output is written back into the catalog.
3. Defences and their helpfulness cost (spotlighting or delimiting tool output, an instruction hierarchy note, output filtering) measured against the 28-vs-53-word side effect.
4. More models, more catalogs, repeated runs for variance.

## Practical takeaways for shop-assistant builders

- Treat catalog text as untrusted input; spam and keyword-stuffing controls are a security layer because they gate exposure.
- Cheaper models may be hijackable even where flagship models are not (gpt-5.4-mini followed 6% of attacks once exposed); test the model you actually deploy.
- Do not rely on one model's behaviour: the same listing was read in 40% vs 7% of conversations depending on how each model searched.
- Log and review replies that mention "instructions" or "listing" text; a model that refuses loudly is also telling you an attack was attempted.
- Strip or cap HTML and long fields before they reach the model, as the reference plugin already does.

*Reproduce: see the Quick start in the README. Raw runs and scores are under `results/`.*
