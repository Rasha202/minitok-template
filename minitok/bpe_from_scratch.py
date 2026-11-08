
"""BONUS — Byte-Pair Encoding from scratch (+2% course-total bonus).

Standard library ONLY in this module.
"""

from __future__ import annotations


def _merge_pair(
    tokens: list[str],
    pair: tuple[str, str]
) -> list[str]:
    """Merge adjacent occurrences of a pair."""

    result = []
    i = 0

    while i < len(tokens):
        if (
            i + 1 < len(tokens)
            and tokens[i] == pair[0]
            and tokens[i + 1] == pair[1]
        ):
            result.append(pair[0] + pair[1])
            i += 2
        else:
            result.append(tokens[i])
            i += 1

    return result


def train_bpe(
    corpus: str,
    num_merges: int
) -> list[tuple[str, str]]:
    """Learn BPE merge rules from the corpus."""

    if not isinstance(corpus, str):
        raise TypeError("corpus must be a string")

    if not isinstance(num_merges, int) or isinstance(num_merges, bool):
        raise TypeError("num_merges must be an integer")

    if num_merges < 0:
        raise ValueError("num_merges cannot be negative")

    tokens = list(corpus)
    merges = []

    for _ in range(num_merges):

        pair_counts = {}

        for i in range(len(tokens) - 1):
            pair = (tokens[i], tokens[i + 1])

            pair_counts[pair] = pair_counts.get(pair, 0) + 1

        if not pair_counts:
            break

        max_frequency = max(pair_counts.values())

        best_pair = min(
            pair
            for pair, count in pair_counts.items()
            if count == max_frequency
        )

        merges.append(best_pair)

        tokens = _merge_pair(tokens, best_pair)

    return merges


def encode(
    text: str,
    merges: list[tuple[str, str]]
) -> list[str]:
    """Apply merge rules in training order."""

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    tokens = list(text)

    for pair in merges:

        if (
            not isinstance(pair, tuple)
            or len(pair) != 2
            or not all(isinstance(x, str) for x in pair)
        ):
            raise ValueError(
                "Each merge must be a pair of strings"
            )

        tokens = _merge_pair(tokens, pair)

    return tokens


def decode(tokens: list[str]) -> str:
    """Decode tokens back into the original text."""

    if not all(isinstance(token, str) for token in tokens):
        raise TypeError("All tokens must be strings")

    return "".join(tokens)
