r"""Part A1 — Token specification loader and validator.

A token specification is a JSON object:

{
  "tokens": [
    {"name": "WS",    "regex": "( |\t|\n)*",        "skip": true},
    {"name": "FLOAT", "regex": "<digit>*.<digit>*", "skip": false},
    {"name": "INT",   "regex": "<digit>*",          "skip": false},
    {"name": "IDENT", "regex": "<letter>(<letter>|<digit>|_)*", "skip": false},
    {"name": "OP",    "regex": "==|=|\+|-|\*|/|<|>", "skip": false}
  ]
}

Regex syntax (a small extension of Sipser §1.3):
  literals          letters, digits, and the operator characters + - * / < > =
                    when they are NOT acting as operators (use \\ to escape
                    operator chars: \\* means literal asterisk)
  <letter>          shorthand class: a-z A-Z
  <digit>           shorthand class: 0-9
  a|b               union
  ab                concatenation
  a*                Kleene star (in this spec: ONE or more repetitions, i.e.
                    the regular operation a(a)*  — "plus" — because a token
                    must be non-empty; see README §A2)
  ( ... )           grouping
  Precedence: * > concatenation > |

`skip: true` token classes (typically whitespace/comments) are recognized
and discarded by the scanner instead of being emitted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


class SpecError(ValueError):
    """Raised when a token specification is invalid."""


@dataclass
class TokenClass:
    name: str
    regex: str
    skip: bool = False


@dataclass
class TokenSpec:
    tokens: list[TokenClass] = field(default_factory=list)

    @property
    def names(self) -> list[str]:
        return [t.name for t in self.tokens]


def load_spec(source: str | Path) -> TokenSpec:
    """Load and validate a token specification from a JSON file path or a
    JSON string.

    Must raise SpecError (with a helpful message) for:
      - malformed JSON
      - missing/empty "tokens" list
      - duplicate token names
      - empty regex strings
      - regexes that can match the empty string (tokens must be non-empty)
      - unknown shorthand classes or unbalanced parentheses

    Returns a TokenSpec preserving the declared order (order defines
    priority for maximal-munch tie-breaking: earlier = higher priority).
    """
      if isinstance(source, Path):
        data = json.loads(source.read_text(encoding="utf-8"))
    else:
        try:
            data = json.loads(source)
        except json.JSONDecodeError as e:
            raise SpecError(f"Invalid JSON: {e}") from e
