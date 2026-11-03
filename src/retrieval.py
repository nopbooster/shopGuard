"""Keyword retrieval that approximates the shop assistant's search step.

The real plugin uses keyword search over the nopCommerce catalog and sends
the matching products to the model. This module mimics that: tokenise the
query, drop stop words, score each product by how many query terms appear in
its text, and return the top-k.

ASSUMPTION TO VERIFY against the real plugin: which fields are searched
(name only vs. descriptions too) and how many products are sent (top_k).
"""
import re

STOP_WORDS = {
    "a", "an", "the", "for", "to", "of", "and", "or", "with", "i", "my", "me",
    "need", "want", "that", "can", "on", "in", "is", "it", "do", "you", "sell",
    "good", "not", "too", "something", "some", "make", "at", "home", "without",
    "much", "way", "all", "day", "as", "year", "old", "doesn't", "have", "am",
    "looking", "best", "cheap", "this", "which", "what",
}


def tokenize(text):
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP_WORDS and len(t) > 1]


def product_text(p, fields=("name", "short_description", "full_description")):
    parts = [str(p.get(f, "")) for f in fields]
    if "specs" in p:
        parts.append(" ".join(f"{k} {v}" for k, v in p["specs"].items()))
    return " ".join(parts)


def stem(t):
    # Crude plural stripping so "laptops" matches "laptop".
    return t[:-1] if len(t) > 3 and t.endswith("s") else t


def search(query, catalog, top_k=5):
    q_terms = {stem(t) for t in tokenize(query)}
    if not q_terms:
        return []
    scored = []
    for p in catalog:
        p_terms = {stem(t) for t in tokenize(product_text(p))}
        overlap = q_terms & p_terms
        if overlap:
            # Name matches count double, like a typical relevance boost.
            name_terms = {stem(t) for t in tokenize(p["name"])}
            score = len(overlap) + len(q_terms & name_terms)
            scored.append((score, p["id"], p))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [p for _, _, p in scored[:top_k]]
