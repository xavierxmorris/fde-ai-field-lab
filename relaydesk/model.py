"""Train a small multinomial naive Bayes model on local synthetic examples."""

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


def words(text: str) -> list[str]:
    # Keep digits and non-English words: the scope gate must not silently drop them.
    return re.findall(r"\w+", text.casefold())


def json_rows(path: Path):
    with path.open(encoding="utf-8") as source:
        for line_num, line in enumerate(source, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path.name}:{line_num}: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path.name}:{line_num}: expected a JSON object")
            yield row


class IntentModel:
    def __init__(self, examples: list[dict], labels: set[str], stop_words=frozenset()):
        documents = Counter()
        counts = defaultdict(Counter)
        for row in examples:
            label, text = row.get("label"), row.get("text")
            if not isinstance(label, str) or label not in labels or not isinstance(text, str) or not words(text):
                raise ValueError("training requires a known label and non-empty text")
            documents[label] += 1
            counts[label].update(word for word in words(text) if word not in stop_words)
        if set(documents) != labels:
            raise ValueError("training must contain examples for every label")
        self.vocab = {word for terms in counts.values() for word in terms}
        self.priors = {label: math.log(n / len(examples)) for label, n in documents.items()}
        self.likelihood = {}
        for label, terms in counts.items():
            denominator = sum(terms.values()) + len(self.vocab)
            self.likelihood[label] = {
                word: math.log((terms[word] + 1) / denominator) for word in self.vocab
            }

    def predict(self, tokens: list[str]) -> list[tuple[str, float]]:
        known = [word for word in tokens if word in self.vocab]
        scores = {
            label: prior + sum(self.likelihood[label][word] for word in known)
            for label, prior in self.priors.items()
        }
        peak = max(scores.values())
        weights = {label: math.exp(score - peak) for label, score in scores.items()}
        total = sum(weights.values())
        return sorted(((label, w / total) for label, w in weights.items()), key=lambda pair: -pair[1])
