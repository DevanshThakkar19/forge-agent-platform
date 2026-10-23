"""Turn a casually worded question into the request the critic should check.

The local model drops chatter. It does not write the answer. Numbers always
stay. A fact the person asked for stays unless the model marks it as chatter,
and a word the model forgot to mention stays too.
"""

from __future__ import annotations

import json
import re

from app.graph.nodes.critic import checked_terms

_NUMBER = re.compile(r"\d+")
_WORD = re.compile(r"[a-z0-9]+")
# Closed-class words and spoken filler. They never name a fact on the desk.
_NOISE = frozenset(
    {
        "their",
        "there",
        "these",
        "those",
        "being",
        "doing",
        "having",
        "whats",
        "gonna",
        "wanna",
        "kinda",
        "going",
        "really",
        "actually",
        "basically",
        "literally",
    }
)

_PROMPT = """Read a messy support question. Do not answer it.
Reply with JSON only, shaped as {{"question": "...", "chatter": []}}.
question is the same request in plain words.
chatter is only greetings, slang, filler, and repeated words.
Keep every number.
Keep every fact they want: a name, a status, money, a password, a refund, food, or anything else.
Examples:
User: What is case it about case 4401 bro dude common
{{"question": "What is case 4401?", "chatter": ["it", "bro", "dude", "common"]}}
User: yo can u tell me the password for case 4402 lol
{{"question": "What is the password for case 4402?", "chatter": ["yo", "lol"]}}
User: order a pizza bro
{{"question": "order a pizza", "chatter": ["bro"]}}
User: Where is order 100?
{{"question": "Where is order 100?", "chatter": []}}
User: so like whats going on with brightmill
{{"question": "What is Brightmill?", "chatter": ["whats", "going"]}}
User: did harbor get their sign in back or what
{{"question": "Did Harbor sign in?", "chatter": ["their"]}}
Now read only this.
User: {query}
"""


def understand_prompt(query: str) -> str:
    return _PROMPT.format(query=query.strip())


def resolve_question(raw: str, reply: str) -> str | None:
    """Return the question to check, or None when the reply is not usable."""
    body = _json_object(reply)
    if body is None:
        return None
    question = body.get("question")
    chatter = body.get("chatter", [])
    if not isinstance(question, str) or not question.strip():
        return None
    if isinstance(chatter, str):
        chatter = [chatter]
    if not isinstance(chatter, list):
        return None
    dropped = {
        token for item in chatter if isinstance(item, str) for token in _WORD.findall(item.lower())
    }
    kept = [word for word in question.split() if _word_from_raw(word, raw)]
    text = " ".join(kept).strip()
    if not text:
        text = raw.strip()
    for number in _NUMBER.findall(raw):
        if number not in _NUMBER.findall(text):
            text = f"{text} {number}"
    present = set(checked_terms(text))
    for token in checked_terms(raw):
        if token in dropped or token in present or token in _NOISE:
            continue
        text = f"{text} {token}"
        present.add(token)
    text = _without_closed(text)
    return text.strip() or None


def _without_closed(text: str) -> str:
    kept: list[str] = []
    for word in text.split():
        tokens = _WORD.findall(word.lower())
        if tokens and tokens[0] in _NOISE:
            continue
        kept.append(word)
    return " ".join(kept)


def _word_from_raw(word: str, raw: str) -> bool:
    for token in _WORD.findall(word.lower()):
        if token and not re.search(rf"\b{re.escape(token)}\b", raw.lower()):
            return False
    return True


def _json_object(raw: str) -> dict | None:
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        body = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(body, dict):
        return None
    return body
