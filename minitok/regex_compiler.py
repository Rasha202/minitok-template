
"""Part A2 — Regular-expression compiler: regex -> NFA."""

from __future__ import annotations

from dataclasses import dataclass

from .automata import NFA, EPS


class RegexSyntaxError(ValueError):
    """Raised for malformed regular expressions."""


@dataclass
class _Node:
    """AST node."""

    kind: str
    value: str = ""
    children: list["_Node"] | None = None


def _tokenize(regex: str) -> list[tuple[str, str]]:
    if not isinstance(regex, str) or not regex:
        raise RegexSyntaxError("Regex cannot be empty")

    tokens = []
    i = 0

    while i < len(regex):
        c = regex[i]

        if c == '\\':
            if i + 1 >= len(regex):
                raise RegexSyntaxError("Trailing escape character")

            tokens.append(("LITERAL", regex[i + 1]))
            i += 2

        elif c == '<':
            end = regex.find('>', i)

            if end != -1:
                name = regex[i + 1:end]

                if name in ("letter", "digit"):
                    tokens.append(("CLASS", name))
                    i = end + 1
                elif name.isidentifier():
                    raise RegexSyntaxError(
                        f"Unknown shorthand class: <{name}>"
                    )
                else:
                    tokens.append(("LITERAL", '<'))
                    i += 1
            else:
                tokens.append(("LITERAL", '<'))
                i += 1

        elif c in ('|', '*', '(', ')'):
            tokens.append(("OP", c))
            i += 1

        else:
            tokens.append(("LITERAL", c))
            i += 1

    return tokens


def parse(regex: str) -> _Node:
    """Parse a regex string into an AST."""

    try:
        tokens = _tokenize(regex)
    except RegexSyntaxError:
        raise

    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def consume():
        nonlocal pos

        if pos >= len(tokens):
            raise RegexSyntaxError("Unexpected end of regex")

        token = tokens[pos]
        pos += 1
        return token

    def parse_union():
        node = parse_concat()

        while peek() == ("OP", "|"):
            consume()
            right = parse_concat()

            node = _Node(
                "union",
                children=[node, right]
            )

        return node

    def parse_concat():
        if peek() is None or peek() in (
            ("OP", "|"),
            ("OP", ")")
        ):
            raise RegexSyntaxError("Empty concatenation")

        node = parse_star()

        while peek() is not None and peek() not in (
            ("OP", "|"),
            ("OP", ")")
        ):
            right = parse_star()

            node = _Node(
                "concat",
                children=[node, right]
            )

        return node

    def parse_star():
        node = parse_atom()

        while peek() == ("OP", "*"):
            consume()

            node = _Node(
                "plus",
                children=[node]
            )

        return node

    def parse_atom():
        token = peek()

        if token is None:
            raise RegexSyntaxError("Unexpected end of regex")

        if token[0] == "LITERAL":
            consume()
            return _Node("literal", value=token[1])

        if token[0] == "CLASS":
            consume()
            return _Node("class", value=token[1])

        if token == ("OP", "("):
            consume()

            node = parse_union()

            if peek() != ("OP", ")"):
                raise RegexSyntaxError(
                    "Unbalanced parentheses"
                )

            consume()
            return node

        raise RegexSyntaxError(
            f"Unexpected token: {token}"
        )

    root = parse_union()

    if pos != len(tokens):
        raise RegexSyntaxError(
            f"Unexpected token: {tokens[pos]}"
        )

    return root


def compile_regex(regex: str) -> NFA:
    """Compile a regex into an NFA using Thompson's construction."""

    try:
        root = parse(regex)
    except RegexSyntaxError:
        raise
    except Exception as e:
        raise RegexSyntaxError(str(e)) from e

    states = set()
    alphabet = set()
    transitions = {}

    next_state = 0

    def new_state():
        nonlocal next_state

        state = next_state
        next_state += 1

        states.add(state)
        transitions[state] = {}

        return state

    def add_transition(source, symbol, destination):
        transitions[source].setdefault(
            symbol, set()
        ).add(destination)

    def compile_node(node: _Node):
        kind = node.kind

        # LITERAL
        if kind == "literal":
            start = new_state()
            accept = new_state()

            symbol = node.value
            alphabet.add(symbol)

            add_transition(
                start, symbol, accept
            )

            return start, accept

        # CLASS
        if kind == "class":
            start = new_state()
            accept = new_state()

            if node.value == "letter":
                characters = (
                    "abcdefghijklmnopqrstuvwxyz"
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                )

            elif node.value == "digit":
                characters = "0123456789"

            else:
                raise RegexSyntaxError(
                    f"Unknown class: {node.value}"
                )

            for char in characters:
                alphabet.add(char)

                add_transition(
                    start, char, accept
                )

            return start, accept

        # CONCATENATION
        if kind == "concat":
            left_start, left_accept = compile_node(
                node.children[0]
            )

            right_start, right_accept = compile_node(
                node.children[1]
            )

            add_transition(
                left_accept,
                EPS,
                right_start
            )

            return left_start, right_accept

        # UNION
        if kind == "union":
            start = new_state()
            accept = new_state()

            left_start, left_accept = compile_node(
                node.children[0]
            )

            right_start, right_accept = compile_node(
                node.children[1]
            )

            add_transition(
                start, EPS, left_start
            )

            add_transition(
                start, EPS, right_start
            )

            add_transition(
                left_accept, EPS, accept
            )

            add_transition(
                right_accept, EPS, accept
            )

            return start, accept

        # PLUS (ONE OR MORE)
        if kind == "plus":
            start = new_state()
            accept = new_state()

            inner_start, inner_accept = compile_node(
                node.children[0]
            )

            add_transition(
                start, EPS, inner_start
            )

            add_transition(
                inner_accept, EPS, inner_start
            )

            add_transition(
                inner_accept, EPS, accept
            )

            return start, accept

        raise RegexSyntaxError(
            f"Unknown AST node type: {kind}"
        )

    start, accept = compile_node(root)

    return NFA(
        states=states,
        alphabet=alphabet,
        transitions=transitions,
        start=start,
        accepts={accept}
    )
