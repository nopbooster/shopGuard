"""Catalog search that reproduces the shop assistant plugin's search step.

How the real plugin works (Nop.Plugin.Widgets.AiAssistant, nopCommerce 4.90):

1. The model does not see the catalog directly. It calls a `search_products`
   tool with a short keyword string it chooses itself (e.g. "laptop").
2. The plugin calls nopCommerce's IProductService.SearchProductsAsync with
   searchDescriptions=true. With no external search provider, nopCommerce
   matches the WHOLE keyword string as a case-insensitive substring
   (SQL LIKE '%keywords%') against product name, short description, full
   description, category name, manufacturer name and product tags.
3. Results are ordered by display position and capped at MaxProductsPerSearch
   (default 6).
4. For each result the model receives ONE line:
       - {name} | price: {price} | sku: {sku} | {short description, HTML stripped, max 300 chars}
   The FULL description is searched but never shown to the model.

Point 4 shapes the whole attack surface: an attacker who wants the model to
read an instruction must place it in the name, SKU or the first 300 characters
of the short description. The full description is useful to an attacker only
for getting retrieved.
"""

DEFAULT_PAGE_SIZE = 6
SHORT_DESC_LIMIT = 300

SEARCHED_FIELDS = ("name", "short_description", "full_description", "category", "brand")


def matches(product, keywords):
    kw = keywords.strip().lower()
    if not kw:
        return False
    haystacks = [str(product.get(f, "")) for f in SEARCHED_FIELDS]
    haystacks += product.get("tags", [])
    return any(kw in h.lower() for h in haystacks)


def search(keywords, catalog, page_size=DEFAULT_PAGE_SIZE):
    """Return up to `page_size` products whose text contains `keywords`.

    Display position is approximated by product id (catalog order).
    """
    hits = [p for p in catalog if matches(p, keywords)]
    hits.sort(key=lambda p: p.get("display_order", p["id"]))
    return hits[:page_size], len(hits)


def truncate_short_description(text, limit=SHORT_DESC_LIMIT):
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit] + "…"


def format_tool_result(keywords, products, total):
    """Exactly the text the model receives as the tool result."""
    if not products:
        return f'No products found for "{keywords}".'
    lines = [f'Found {total} product(s) for "{keywords}" (showing {len(products)}):']
    for p in products:
        sku = p.get("sku") or "n/a"
        lines.append(
            f"- {p['name']} | price: ${p['price']:.2f} | sku: {sku} | "
            f"{truncate_short_description(p.get('short_description', ''))}"
        )
    return "\n".join(lines)
