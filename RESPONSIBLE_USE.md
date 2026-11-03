# Responsible use

ShopGuard exists to help people who build AI shopping assistants understand and reduce prompt-injection risk.

## How this study is run

- **Offline only.** Every experiment runs against a synthetic, fictional catalog. No live store is tested, including stores running the authors' own plugins.
- **No real data.** No customer, order or merchant data is used.
- **Inert payloads.** Attack text uses the reserved `.example` domain, so any links point nowhere.
- **Measurement, not tooling.** The attack library is deliberately simple and mirrors patterns already documented in public prompt-injection research. Its purpose is to measure failure rates and test defenses.

## If you use this work

- Test only systems you own or are authorised to test.
- If you find an injection weakness in someone else's product, report it privately to the vendor and allow reasonable time to fix it before publishing.
- When reporting results, include both attack success and the helpfulness cost of any defense.

## Contact

Issues and questions: open a GitHub issue on this repository.
