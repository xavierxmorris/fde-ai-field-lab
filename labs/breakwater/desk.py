"""Breakwater: a read-only, one-incident, one-UTC-day teaching baseline."""
import argparse
import json
import math
import re
from collections import Counter
from datetime import date
from pathlib import Path


SOURCE = {"start": "payments-control", "end": "payments-control",
          "loss": "reconciliation", "batch": "fallback-control"}


def load_case():
    return json.loads(Path(__file__).with_name("case.json").read_text(encoding="utf-8"))


def minute(clock):
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", clock):
        raise ValueError(f"Expected a UTC clock in HH:MM format, got {clock!r}")
    h, m = map(int, clock.split(":"))
    return 60 * h + m


def visible(case, at):
    limit = minute(at)
    return [card for card in case["cards"]
            if all(card[k] == v for k, v in case["scope"].items())
            and max(minute(card["observed"]), minute(card["received"])) <= limit]


def search(case, at, query):
    """Rank the visible archive, including historical notes, not just active facts."""
    cards = visible(case, at)
    words = lambda text: Counter(re.findall(r"[a-z0-9]+", text.lower()))
    docs = [words(card["text"]) for card in cards]
    df = Counter(term for doc in docs for term in doc)
    idf = {term: 1 + math.log((1 + len(docs)) / (1 + n)) for term, n in df.items()}

    def vector(counts):
        raw = {t: count * idf[t] for t, count in counts.items() if t in idf}
        norm = math.sqrt(sum(w * w for w in raw.values())) or 1
        return {t: w / norm for t, w in raw.items()}

    q = vector(words(query))
    hits = []
    for card, doc in zip(cards, docs):
        score = sum(q.get(term, 0) * w for term, w in vector(doc).items())
        if score:
            hits.append((score, card))
    return [{"id": c["id"], "received": c["received"], "source": c["source"],
             "text": c["text"]} for _, c in sorted(hits, key=lambda x: (-x[0], x[1]["id"]))[:3]]


def fact(cards, kind):
    rows = [c for c in cards if c["kind"] == kind and c["source"] == SOURCE[kind]
            and (kind != "batch" or c.get("batch") == "FB-1")]
    by_id = {c["id"]: c for c in rows}
    if len(by_id) != len(rows):
        return None, "duplicate evidence ID"
    retired = set()
    for c in rows:
        if "supersedes" not in c:
            continue
        previous = by_id.get(c["supersedes"])
        if previous is None or minute(previous["received"]) >= minute(c["received"]):
            return None, "correction chain unresolved"
        retired.add(previous["id"])
    live = [c for c in rows if c["id"] not in retired]
    if len(live) == 1:
        return live[0], ""
    return None, "competing authoritative receipts" if live else "awaiting authoritative receipt"


def unknown(reason, owner, *evidence):
    return {"status": "UNKNOWN", "reason": reason, "owner": owner, "evidence": list(evidence)}


def comparison(value, threshold, within, *evidence):
    return {"status": "WITHIN" if within else "OUTSIDE", "value": value,
            "threshold": threshold, "evidence": list(evidence)}


def brief(case, at):
    cards = visible(case, at)
    day = date.fromisoformat(case["date"])
    register = [p for p in case["register"]
                if p["entity"] == case["scope"]["entity"] and p["operation"] == case["operation"]
                and date.fromisoformat(p["published"]) <= day
                and date.fromisoformat(p["from"]) <= day
                and (p["until"] is None or day < date.fromisoformat(p["until"]))]
    result = {**case["scope"], "as_of_utc": f"{day}T{at}:00Z", "policy": None,
              "state": "INCOMPLETE", "human_review_required": True}
    if len(register) != 1:
        return {**result, "reason": "no unique effective approved policy", "owner": "operational-risk"}
    p = register[0]
    result["policy"] = p["id"]
    start, start_reason = fact(cards, "start")
    end, end_reason = fact(cards, "end")
    if start and end and minute(end["observed"]) >= minute(start["observed"]):
        duration = minute(end["observed"]) - minute(start["observed"])
        duration_row = comparison(f"{duration} min", f"<= {p['max_minutes']} min",
                                  duration <= p["max_minutes"], start["id"], end["id"])
    else:
        duration_row = unknown(start_reason or end_reason or "inconsistent incident clocks",
                               "payments-control", *(c["id"] for c in (start, end) if c))
    loss, reason = fact(cards, "loss")
    if loss and type(loss.get("lost")) is int and loss["lost"] >= 0:
        loss_row = comparison(f"{loss['lost']} instructions", f"<= {p['max_lost']} instructions",
                              loss["lost"] <= p["max_lost"], loss["id"])
    else:
        loss_row = unknown(reason or "invalid final count", "reconciliation")
    batch, reason = fact(cards, "batch")
    if (batch and type(batch.get("accepted")) is int and type(batch.get("eligible")) is int
            and 0 <= batch["accepted"] <= batch["eligible"] and batch["eligible"] > 0):
        a, n = batch["accepted"], batch["eligible"]
        service_row = comparison(f"{a}/{n} eligible FB-1 instructions", f">= {p['min_percent']}%",
                                 100 * a >= p["min_percent"] * n, batch["id"])
    else:
        service_row = unknown(reason or "invalid cohort or denominator", "fallback-control")
    measures = {"duration": duration_row, "loss": loss_row, "fallback_service": service_row}
    statuses = {row["status"] for row in measures.values()}
    if "OUTSIDE" in statuses:
        result["state"] = "FLAG_FOR_REVIEW"
    elif "UNKNOWN" not in statuses:
        result["state"] = "READY_FOR_REVIEW"
    result["measures"] = measures
    return result


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cmd = cli.add_subparsers(dest="command", required=True)
    cmd.add_parser("brief", help="draft comparisons for the synthetic ops desk").add_argument("at")
    lookup = cmd.add_parser("search", help="rank eligible notes; matches do not establish authority")
    lookup.add_argument("at", help="UTC cutoff HH:MM")
    lookup.add_argument("query")
    args = cli.parse_args()
    try:
        minute(args.at)
    except ValueError as err:
        cli.error(str(err))
    scenario = load_case()
    packet = brief(scenario, args.at) if args.command == "brief" else search(scenario, args.at, args.query)
    print(json.dumps(packet, indent=2))
