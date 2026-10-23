"""Token rules shared by the embedder, the ranker, and the critic."""

from __future__ import annotations

import re

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    {
        "the",
        "and",
        "from",
        "for",
        "with",
        "about",
        "that",
        "this",
        "are",
        "was",
        "its",
        "into",
        "over",
        "than",
        "then",
        "them",
        "they",
        "have",
        "has",
        "not",
        "but",
        "you",
        "your",
    }
)
# Tool words that show up in almost every doc. They must not count as support.
_GENERIC = frozenset(
    {
        "sql",
        "http",
        "api",
        "table",
        "tool",
        "tools",
        "query",
        "read",
        "demo",
        "select",
    }
)


def tokenize(text: str) -> list[str]:
    return [
        token for token in _TOKEN.findall(text.lower()) if len(token) >= 3 and token not in _STOP
    ]


def support_tokens(text: str) -> set[str]:
    return {token for token in tokenize(text) if token not in _GENERIC}


def shares_support(query: str, content: str) -> bool:
    needed = support_tokens(query)
    if not needed:
        return False
    return bool(needed & support_tokens(content))
