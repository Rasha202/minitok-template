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
    # TODO(PART A1): implement
    if isinstance(source, Path):
        try:
            content = source.read_text(encoding="utf-8")
        except Exception as e:
            raise SpecError(f"Failed to read spec file: {e}") from e
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise SpecError(f"Malformed JSON: {e}") from e
    else:
        try:
            data = json.loads(source)
        except json.JSONDecodeError as e:
            raise SpecError(f"Malformed JSON: {e}") from e

    if not isinstance(data, dict) or "tokens" not in data:
        raise SpecError("Missing 'tokens' list in specification")

    tokens_list = data["tokens"]
    if not isinstance(tokens_list, list) or len(tokens_list) == 0:
        raise SpecError("The 'tokens' list must be a non-empty list")

    token_classes = []
    seen_names = set()

    for item in tokens_list:
        if not isinstance(item, dict):
            raise SpecError("Each token definition must be an object")
        
        name = item.get("name")
        regex = item.get("regex")
        skip = item.get("skip", False)

        if not name or not isinstance(name, str):
            raise SpecError("Token definition missing or invalid 'name'")
        if regex is None or not isinstance(regex, str):
            raise SpecError(f"Token '{name}' missing or invalid 'regex'")
        
        if name in seen_names:
            raise SpecError(f"Duplicate token name: '{name}'")
        seen_names.add(name)

        if not regex:
            raise SpecError(f"Token '{name}' has an empty regex string")

        # Validate syntax, parentheses balance, and shorthand classes
        _validate_regex_syntax(regex, name)

        token_classes.append(TokenClass(name=name, regex=regex, skip=bool(skip)))

    return TokenSpec(tokens=token_classes)


def _validate_regex_syntax(regex: str, token_name: str) -> None:
    """Helper to validate regex structure, balancing, shorthands, and non-empty matching."""
    # Check parentheses balance and unknown shorthand classes
    paren_count = 0
    i = 0
    n = len(regex)
    
    while i < n:
        c = regex[i]
        if c == '\\':
            if i + 1 >= n:
                raise SpecError(f"Token '{token_name}': trailing backslash in regex")
            i += 2
        elif c == '<':
            end = regex.find('>', i)
            if end == -1:
                raise SpecError(f"Token '{token_name}': unterminated character class '<'")
            shorthand = regex[i:end+1]
            if shorthand not in {"<letter>", "<digit>"}:
                raise SpecError(f"Token '{token_name}': unknown shorthand class '{shorthand}'")
            i = end + 1
        elif c == '(':
            paren_count += 1
            i += 1
        elif c == ')':
            paren_count -= 1
            if paren_count < 0:
                raise SpecError(f"Token '{token_name}': unbalanced parentheses")
            i += 1
        else:
            i += 1

    if paren_count != 0:
        raise SpecError(f"Token '{token_name}': unbalanced parentheses")

    # Check if the regex can trivially match empty string (e.g. ends with unescaped '*' where previous can be empty or explicit empty patterns)
    # In minitok spec, '*' means one or more repetitions, but if someone puts something that evaluates to empty or invalid, catch it.
    # Also, we can test compilation or check if the compiled NFA can accept empty string.
    try:
        from .regex import compile_regex
        nfa = compile_regex(regex)
        if nfa.simulate(""):
            raise SpecError(f"Token '{token_name}': regex can match the empty string")
    except SpecError:
        raise
    except Exception:
        # If compilation fails due to general syntax error, let regex compiler raise it or handle here
        pass
