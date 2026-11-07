
"""Part A1 — Token specification loader and validator."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .regex_compiler import compile_regex, RegexSyntaxError


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
    """Load and validate a token specification."""

    if isinstance(source, Path):
        try:
            content = source.read_text(encoding="utf-8")
        except Exception as e:
            raise SpecError(f"Failed to read spec file: {e}") from e
    else:
        content = source

    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError) as e:
        raise SpecError(f"Malformed JSON: {e}") from e

    if not isinstance(data, dict) or "tokens" not in data:
        raise SpecError("Missing 'tokens' list in specification")

    tokens_list = data["tokens"]

    if not isinstance(tokens_list, list) or not tokens_list:
        raise SpecError("The 'tokens' list must be a non-empty list")

    token_classes = []
    seen_names = set()

    for item in tokens_list:
        if not isinstance(item, dict):
            raise SpecError("Each token definition must be an object")

        name = item.get("name")
        regex = item.get("regex")
        skip = item.get("skip", False)

        if not isinstance(name, str) or not name:
            raise SpecError("Token definition missing or invalid 'name'")

        if not isinstance(regex, str):
            raise SpecError(f"Token '{name}' missing or invalid 'regex'")

        if name in seen_names:
            raise SpecError(f"Duplicate token name: '{name}'")

        seen_names.add(name)

        if not regex:
            raise SpecError(f"Token '{name}' has an empty regex string")

        if not isinstance(skip, bool):
            raise SpecError(f"Token '{name}' has an invalid 'skip' value")

        try:
            nfa = compile_regex(regex)
        except RegexSyntaxError as e:
            raise SpecError(
                f"Token '{name}': invalid regex: {e}"
            ) from e

        if nfa.simulate(""):
            raise SpecError(
                f"Token '{name}': regex can match the empty string"
            )

        token_classes.append(
            TokenClass(name=name, regex=regex, skip=skip)
        )

    return TokenSpec(tokens=token_classes)
