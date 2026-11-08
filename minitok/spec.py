
r"""Part A1 — Token specification loader and validator."""

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


class ASTNode:
    pass


class Literal(ASTNode):
    def __init__(self, char: str):
        self.char = char


class Shorthand(ASTNode):
    def __init__(self, name: str):
        self.name = name


class Concat(ASTNode):
    def __init__(self, left: ASTNode, right: ASTNode):
        self.left = left
        self.right = right


class Union(ASTNode):
    def __init__(self, left: ASTNode, right: ASTNode):
        self.left = left
        self.right = right


class Star(ASTNode):
    """In this specification, '*' means one-or-more."""

    def __init__(self, expr: ASTNode):
        self.expr = expr


def tokenize_regex(regex_str: str) -> list[tuple[str, str]]:
    tokens = []
    i = 0
    n = len(regex_str)
    paren_depth = 0

    while i < n:
        c = regex_str[i]

        if c == '\\':
            if i + 1 >= n:
                raise SpecError("Trailing escape character in regex")

            tokens.append(('LITERAL', regex_str[i + 1]))
            i += 2

        elif c == '<':
            end = regex_str.find('>', i)

            if end != -1:
                content = regex_str[i + 1:end]

                if content.isidentifier():
                    if content not in ('letter', 'digit'):
                        raise SpecError(
                            f"Unknown shorthand class: <{content}>"
                        )

                    tokens.append(('SHORTHAND', content))
                    i = end + 1
                else:
                    tokens.append(('LITERAL', '<'))
                    i += 1
            else:
                tokens.append(('LITERAL', '<'))
                i += 1

        elif c == '>':
            tokens.append(('LITERAL', '>'))
            i += 1

        elif c in ('|', '*', '(', ')'):
            if c == '(':
                paren_depth += 1

            elif c == ')':
                paren_depth -= 1

                if paren_depth < 0:
                    raise SpecError("Unbalanced parentheses in regex")

            tokens.append(('OP', c))
            i += 1

        else:
            tokens.append(('LITERAL', c))
            i += 1

    if paren_depth != 0:
        raise SpecError("Unbalanced parentheses in regex")

    return tokens


def parse_tokens_to_ast(tokens: list[tuple[str, str]]) -> ASTNode:
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def consume(expected_type=None, expected_val=None):
        nonlocal pos

        t = peek()

        if t is None:
            raise SpecError("Unexpected end of regex")

        if expected_type is not None and t[0] != expected_type:
            raise SpecError(
                f"Expected token type {expected_type}, got {t[0]}"
            )

        if expected_val is not None and t[1] != expected_val:
            raise SpecError(
                f"Expected token value {expected_val}, got {t[1]}"
            )

        pos += 1
        return t

    def parse_expr():
        node = parse_term()

        while peek() == ('OP', '|'):
            consume('OP', '|')
            right = parse_term()
            node = Union(node, right)

        return node

    def parse_term():
        t = peek()

        if t is None or t in (('OP', '|'), ('OP', ')')):
            raise SpecError("Empty term or unexpected operator")

        node = parse_factor()

        while True:
            nxt = peek()

            if nxt is None or nxt in (('OP', '|'), ('OP', ')')):
                break

            right = parse_factor()
            node = Concat(node, right)

        return node

    def parse_factor():
        node = parse_base()

        while peek() == ('OP', '*'):
            consume('OP', '*')
            node = Star(node)

        return node

    def parse_base():
        t = peek()

        if t is None:
            raise SpecError("Unexpected end of regex")

        if t[0] == 'LITERAL':
            consume()
            return Literal(t[1])

        if t[0] == 'SHORTHAND':
            consume()
            return Shorthand(t[1])

        if t == ('OP', '('):
            consume('OP', '(')
            node = parse_expr()
            consume('OP', ')')
            return node

        raise SpecError(f"Unexpected token in regex: {t}")

    if not tokens:
        raise SpecError("Regex cannot be empty")

    node = parse_expr()

    if pos < len(tokens):
        raise SpecError(
            f"Extra tokens at end of regex starting at {tokens[pos]}"
        )

    return node


def check_nullable(node: ASTNode) -> bool:
    """Return True if the regex can match an empty string."""

    if isinstance(node, (Literal, Shorthand)):
        return False

    if isinstance(node, Concat):
        return (
            check_nullable(node.left)
            and check_nullable(node.right)
        )

    if isinstance(node, Union):
        return (
            check_nullable(node.left)
            or check_nullable(node.right)
        )

    if isinstance(node, Star):
        # Star means one-or-more in this project.
        return check_nullable(node.expr)

    return False


def parse_and_validate_regex(regex_str: str) -> ASTNode:
    if not isinstance(regex_str, str) or regex_str == "":
        raise SpecError("Regex string cannot be empty")

    tokens = tokenize_regex(regex_str)
    ast = parse_tokens_to_ast(tokens)

    if check_nullable(ast):
        raise SpecError("Regex can match the empty string")

    return ast


def load_spec(source: str | Path) -> TokenSpec:
    """Load and validate a token specification.

    Accepts a JSON file path or a JSON string.

    Raises SpecError for invalid specifications.
    """

    if isinstance(source, Path):
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as e:
            raise SpecError(
                f"Cannot read file {source}: {e}"
            ) from e

    elif isinstance(source, str):
        try:
            path = Path(source)
            is_file = path.is_file()
        except (OSError, ValueError):
            is_file = False

        if is_file:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as e:
                raise SpecError(
                    f"Cannot read file {source}: {e}"
                ) from e
        else:
            text = source

    else:
        raise SpecError("Source must be a file path or JSON string")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise SpecError(f"Malformed JSON: {e}") from e

    if not isinstance(data, dict):
        raise SpecError(
            "JSON specification root must be an object"
        )

    if "tokens" not in data:
        raise SpecError(
            "Missing 'tokens' key in specification"
        )

    tokens_list = data["tokens"]

    if not isinstance(tokens_list, list) or not tokens_list:
        raise SpecError(
            "'tokens' must be a non-empty list"
        )

    token_classes = []
    seen_names = set()

    for item in tokens_list:

        if not isinstance(item, dict):
            raise SpecError(
                "Token specification entry must be an object"
            )

        if "name" not in item or "regex" not in item:
            raise SpecError(
                "Token entry must have 'name' and 'regex' fields"
            )

        name = item["name"]
        regex = item["regex"]
        skip = item.get("skip", False)

        if not isinstance(name, str) or not name.strip():
            raise SpecError(
                "Token name must be a non-empty string"
            )

        if not isinstance(regex, str):
            raise SpecError(
                "Token regex must be a string"
            )

        if not isinstance(skip, bool):
            raise SpecError(
                "Token 'skip' must be a boolean"
            )

        if name in seen_names:
            raise SpecError(
                f"Duplicate token name: '{name}'"
            )

        seen_names.add(name)

        if regex == "":
            raise SpecError(
                f"Empty regex string for token '{name}'"
            )

        try:
            parse_and_validate_regex(regex)

        except SpecError as e:
            raise SpecError(
                f"Token '{name}': {e}"
            ) from e

        token_classes.append(
            TokenClass(
                name=name,
                regex=regex,
                skip=skip
            )
        )

    return TokenSpec(tokens=token_classes)
