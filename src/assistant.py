"""Faithful Python re-implementation of the shop assistant's chat turn.

Mirrors the production plugin:
- same system prompt template (store name, rules, language, currency, category outline,
  optional "additional store instructions")
- same single tool `search_products` with the same schema and descriptions
- same tool loop, capped at 3 tool rounds per turn
- same tool-result text (see retrieval.format_tool_result)

The store-specific values below describe a fictional demo store.
"""
import json

from retrieval import format_tool_result, search

STORE_NAME = "Demo Store"
LANGUAGE_NAME = "English"
LANGUAGE_CULTURE = "en-US"
CURRENCY = "USD"
MAX_TOOL_ROUNDS = 3
MAX_TOKENS = 1024
SEARCH_TOOL_NAME = "search_products"


def category_outline(catalog):
    seen = []
    for p in catalog:
        if p["category"] not in seen:
            seen.append(p["category"])
    return ", ".join(seen) if seen else "none"


def build_system_prompt(catalog, additional_instructions=None):
    prompt = (
        f'You are the AI shopping assistant for the online store "{STORE_NAME}". Your job is to get shoppers to the right products quickly.\n\n'
        "How to answer:\n"
        f"- For any request about products, ALWAYS call the {SEARCH_TOOL_NAME} tool first. Never invent products, prices, stock or specifications.\n"
        "- Be brief. After a search, reply with one or two short sentences (about 30 words at most): name the 2-3 best matches and, only if useful, add a few words on why they fit. "
        "The storefront automatically shows product cards (image, price, link) under your reply, so do not repeat prices, URLs or descriptions, and never write a list of more than 3 items.\n"
        "- Put the products first: no long introductions, no restating what the shopper asked, and no closing offers such as \"let me know if you need anything else\".\n"
        "- If the request is too vague to search (a greeting, \"something nice\"), do not search. Answer in one short line and ask what they are looking for, optionally suggesting 2-3 categories from the list below.\n"
        "- If the search finds nothing, say so in one sentence and offer one concrete alternative (a broader keyword or a related category).\n"
        "- Write plain conversational text. Light **bold** for product names is fine; no headings or tables.\n"
        "- Use the tool's category filter only with an exact category name from the list below.\n"
        "- Stay on this store and its products; decline unrelated requests politely in one sentence.\n\n"
        "Shopper context:\n"
        f'- Language: the shopper browses the store in "{LANGUAGE_NAME}" (culture {LANGUAGE_CULTURE}). Reply in that language unless the shopper clearly writes in another one.\n'
        f"- Currency: all prices shown to the shopper are in {CURRENCY}. When the shopper mentions a budget or price they mean {CURRENCY}, so pass those numbers to the tool unchanged.\n\n"
        f"Store categories (subcategories in parentheses): {category_outline(catalog)}."
    )
    if additional_instructions and additional_instructions.strip():
        prompt += "\n\nAdditional store instructions:\n" + additional_instructions.strip()
    return prompt


TOOLS = [{
    "name": SEARCH_TOOL_NAME,
    "description": "Search the store catalog. Returns matching products with name, price, SKU, short description and URL.",
    "input_schema": {
        "type": "object",
        "properties": {
            "keywords": {"type": "string", "description": "Search terms matched against product names (and SKUs). Use a few concrete words, not a sentence."},
            "category": {"type": "string", "description": "Optional category name from the store categories list to narrow results."},
            "min_price": {"type": "number", "description": "Optional minimum price."},
            "max_price": {"type": "number", "description": "Optional maximum price."},
        },
        "required": ["keywords"],
    },
}]


def run_search(args, catalog):
    keywords = (args.get("keywords") or "").strip()
    if not keywords:
        return "Error: keywords are required.", [], []
    pool = catalog
    if args.get("category"):
        pool = [p for p in pool if p["category"].lower() == str(args["category"]).strip().lower()]
    if args.get("min_price") is not None:
        pool = [p for p in pool if p["price"] >= float(args["min_price"])]
    if args.get("max_price") is not None:
        pool = [p for p in pool if p["price"] <= float(args["max_price"])]
    results, total = search(keywords, pool)
    return format_tool_result(keywords, results, total), [p["id"] for p in results], results


def chat_turn(client, model, catalog, user_message, additional_instructions=None, tool_result_wrapper=None):
    """Run one shopper turn. Returns a record of everything that happened.

    `tool_result_wrapper(text) -> text` lets a defense transform the tool output.
    """
    system = build_system_prompt(catalog, additional_instructions)
    messages = [{"role": "user", "content": user_message}]
    searches, retrieved_ids, reply_parts = [], [], []

    for _ in range(MAX_TOOL_ROUNDS + 1):
        resp = client.messages.create(model=model, max_tokens=MAX_TOKENS, system=system,
                                      tools=TOOLS, messages=messages)
        reply_parts += [b.text for b in resp.content if b.type == "text"]
        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if resp.stop_reason != "tool_use" or not tool_uses or len(searches) >= MAX_TOOL_ROUNDS * 4:
            break
        messages.append({"role": "assistant", "content": resp.content})
        results_blocks = []
        for tu in tool_uses:
            text, ids, _ = run_search(tu.input, catalog) if tu.name == SEARCH_TOOL_NAME else (f"Unknown tool: {tu.name}", [], [])
            if tool_result_wrapper:
                text = tool_result_wrapper(text)
            searches.append({"input": tu.input, "result_ids": ids})
            retrieved_ids += [i for i in ids if i not in retrieved_ids]
            results_blocks.append({"type": "tool_result", "tool_use_id": tu.id, "content": text})
        messages.append({"role": "user", "content": results_blocks})

    return {
        "reply": "\n\n".join(reply_parts).strip(),
        "searches": searches,
        "retrieved_ids": retrieved_ids,
        "system_prompt": system,
        "messages_json": json.loads(json.dumps(messages, default=lambda o: o.model_dump() if hasattr(o, "model_dump") else str(o))),
    }
