"""Scope policy evidence before ranking; never synthesize an answer."""

import re
from dataclasses import asdict, dataclass, fields
from datetime import date
from pathlib import Path

from .model import IntentModel, json_rows, words

DATA = Path(__file__).resolve().parent.parent / "data"

# A keyword hit is not proof the card answers the whole question. The pilot
# recognizes two narrow request types; unexplained content goes to the operator.
COMMON = set("""
a about after agent am an are as at be been before by can could customer customers did do does
for from get has have how i if in is it its look me my need of on one or our please policy
purchase purchased purchases item items product products merchandise parcel package box
delivery delivered receive received shopper shoppers order ordinary regular standard normal
the their them there they this that to us we what s which who with would you your
tell find show give know check explain read rules rule request requests may needed buyer someone
remind kindly hello hi looking up answer asked asks ask asking according to published usual
generally typical typically general normally policies guidance guidelines say says state states
d like once ve re those whose today available permitted allowed goods receiving bought buying
since starting starts start new arrive arrival arrives arrived arriving
""".split())
RETURN = set("return returns returning back".split())
WINDOW = set("window windows limit limits deadline cutoff period timeframe duration latest".split())
TIME = WINDOW | set("days day long length last lasts cut off time frame until when soon within end ends expire expires many much".split())
DAMAGE = set("damage damages damaged breakage broken cracked smashed dented".split())
STEP = set("""
steps step first next now do report reports reporting reported handle handling instructions
procedure process proceed guidance guide should respond deal notify contact action actions
""".split())
RETURN_SCOPE = COMMON | RETURN | TIME | set("""
allowed make start initiate lodge submit requested requesting must send sending bring bringing
go sent making taking take opening open applies applicable again same question should wait
calendar count number maximum allowed permitted latest date dates amount between
initiation initiating started requesting filing file normal normally begins begin following
""".split())
DAMAGE_SCOPE = COMMON | DAMAGE | STEP | set("""
shipment shipping shipped transit during upon came comes
got goods showed shows up just found was were newly noticed unpacked unpacking
supposed follow followup take taking desk usual normally because directions direction handling
""".split())
TOPICS = {"return_window": RETURN | TIME, "damage_steps": DAMAGE | (STEP - COMMON)}


def covered(tokens: set[str], vocabulary: set[str]) -> bool:
    # Accept regular inflections of known words, not arbitrary unmatched nouns.
    def recognized(w):
        stems = {w}
        for suffix in ("s", "ed", "ing"):
            if w.endswith(suffix) and len(w) > len(suffix) + 2:
                root = w[:-len(suffix)]
                stems.update((root, root + "e"))
        return bool(stems & vocabulary)
    return all(recognized(w) for w in tokens)


def iso_day(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("use a calendar date in YYYY-MM-DD format")
    date.fromisoformat(value)
    return value


@dataclass(frozen=True)
class Card:
    id: str
    tenant: str
    topic: str
    version: str
    effective_from: str
    effective_until: str | None
    excerpt: str

    @classmethod
    def parse(cls, row: dict):
        if set(row) != {f.name for f in fields(cls)}:
            raise ValueError("policy card has missing or unrecognized fields")
        for key in ("id", "tenant", "topic", "version", "excerpt"):
            if not isinstance(row[key], str) or not row[key].strip():
                raise ValueError(f"policy card requires non-empty {key}")
        if not re.fullmatch(r"[a-z][a-z0-9-]*", row["tenant"]) or row["topic"] not in TOPICS:
            raise ValueError(f"invalid tenant or topic on {row['id']}")
        start, end = iso_day(row["effective_from"]), row["effective_until"]
        if end is not None and iso_day(end) <= start:
            raise ValueError(f"empty or reversed effective interval on {row['id']}")
        return cls(**row)

    def applies(self, tenant: str, day: str) -> bool:
        return self.tenant == tenant and self.effective_from <= day and (
            self.effective_until is None or day < self.effective_until
        )


def request_topic(tokens: set[str]) -> tuple[str | None, str | None]:
    # "Standard window" is the desk's shorthand for its ordinary return window.
    returns = bool(tokens & RETURN) or {"standard", "window"} <= tokens
    damage = bool(tokens & DAMAGE)
    if returns and damage:
        return None, "multiple_topics"
    boundary = tokens & (WINDOW | {"have", "can", "may", "must", "should", "within", "allowed",
                                    "open", "until", "before", "available", "permitted", "number"})
    if returns and boundary and tokens & TIME and covered(tokens, RETURN_SCOPE):
        return "return_window", None
    if damage and tokens & STEP and covered(tokens, DAMAGE_SCOPE):
        return "damage_steps", None
    return None, "outside_supported_scope"


class Engine:
    def __init__(self, cards: tuple[Card, ...], model: IntentModel):
        self.cards = cards
        self.model = model
        if not cards or len({card.id for card in cards}) != len(cards):
            raise ValueError("policy catalog must be non-empty with unique card IDs")
        self.terms = {
            card.id: (set(words(card.excerpt)) - COMMON) | TOPICS[card.topic] for card in cards
        }

    @classmethod
    def load(cls, data_dir: Path = DATA):
        cards = tuple(Card.parse(row) for row in json_rows(data_dir / "policies.jsonl"))
        examples = list(json_rows(data_dir / "training.jsonl"))
        return cls(cards, IntentModel(examples, set(TOPICS) | {"unsupported"}, COMMON))

    def triage(self, tenant: str, lookup_date: str, question: str, *,
               baseline: bool = False, trace: bool = False) -> dict:
        iso_day(lookup_date)
        if not isinstance(tenant, str) or not tenant.strip():
            raise ValueError("supply a retailer key")
        if not isinstance(question, str) or not 1 <= len(question.strip()) <= 500:
            raise ValueError("supply a question of 1-500 characters")
        tokens = words(question)
        terms = set(tokens) - {tenant}  # Only the supplied retailer can be restated in the text.
        eligible = [card for card in self.cards if card.applies(tenant, lookup_date)]
        ranked = sorted(((len(terms & self.terms[c.id]), c) for c in eligible),
                        key=lambda pair: (-pair[0], pair[1].id))
        details = {"tokens": tokens, "scoped_scores": {c.id: score for score, c in ranked}}

        def result(reason=None, card=None):
            return {
                "tenant": tenant, "lookup_date": lookup_date,
                "disposition": "draft" if card else "handoff", "reason": reason,
                "evidence": asdict(card) if card else None,
                **({"trace": details} if trace else {}),
            }

        if not eligible:
            return result("no_applicable_policy")
        if baseline:
            return result(card=ranked[0][1]) if ranked[0][0] else result("no_lexical_match")
        topic, reason = request_topic(terms)
        if reason:
            return result(reason)
        candidates = [c for c in eligible if c.topic == topic]
        if not candidates:
            return result("no_applicable_policy")
        if len(candidates) > 1:
            return result("overlapping_versions")
        prediction = self.model.predict(tokens)
        (label, score), (_, second) = prediction[:2]
        details["model_scores"] = {name: round(p, 4) for name, p in prediction}
        if label != topic or score < 0.70 or score - second < 0.20:
            return result("uncertain_intent")
        best, card = ranked[0]
        if not best or card != candidates[0] or (len(ranked) > 1 and ranked[1][0] == best):
            return result("uncertain_retrieval")
        return result(card=card)
