
"""Part A2 — Regular-expression compiler: regex -> NFA."""

from __future__ import annotations

from dataclasses import dataclass

from .automata import NFA, EPS


class RegexSyntaxError(ValueError):
    """Raised for malformed regular expressions."""


@dataclass
class _Node:
    kind: str
    value: str = ""
    children: list["_Node"] | None = None


def parse(regex: str) -> _Node:
    tokens = []
    i = 0

    while i < len(regex):
        c = regex[i]

        if c == "\\":
            if i + 1 >= len(regex):
                raise RegexSyntaxError("Trailing backslash in regex")
            tokens.append(("literal", regex[i + 1]))
            i += 2

        elif regex.startswith("<letter>", i):
            tokens.append(("class", "<letter>"))
            i += len("<letter>")

        elif regex.startswith("<digit>", i):
            tokens.append(("class", "<digit>"))
            i += len("<digit>")

        elif c in ("|", "*", "(", ")"):
            tokens.append(("operator", c))
            i += 1

        else:
            tokens.append(("literal", c))
            i += 1

    pos = 0

    def parse_union():
        nonlocal pos
        left = parse_concat()

        while pos < len(tokens) and tokens[pos] == ("operator", "|"):
            pos += 1
            right = parse_concat()
            left = _Node("union", children=[left, right])

        return left

    def parse_concat():
        nonlocal pos

        if pos >= len(tokens):
            raise RegexSyntaxError("Missing expression")

        if tokens[pos] in (
            ("operator", "|"),
            ("operator", ")"),
        ):
            raise RegexSyntaxError("Invalid concatenation")

        left = parse_star()

        while pos < len(tokens):
            if tokens[pos][0] == "operator" and tokens[pos][1] in ("|", ")"):
                break

            right = parse_star()
            left = _Node("concat", children=[left, right])

        return left

    def parse_star():
        nonlocal pos
        node = parse_atom()

        while pos < len(tokens) and tokens[pos] == ("operator", "*"):
            pos += 1
            node = _Node("plus", children=[node])

        return node

    def parse_atom():
        nonlocal pos

        if pos >= len(tokens):
            raise RegexSyntaxError("Missing expression")

        kind, value = tokens[pos]

        if kind == "literal":
            pos += 1
            return _Node("literal", value=value)

        if kind == "class":
            pos += 1
            return _Node("class", value=value)

        if kind == "operator" and value == "(":
            pos += 1
            node = parse_union()

            if pos >= len(tokens) or tokens[pos] != ("operator", ")"):
                raise RegexSyntaxError("Mismatched parentheses")

            pos += 1
            return node

        raise RegexSyntaxError(f"Invalid atom: {value}")

    if not tokens:
        raise RegexSyntaxError("Empty regex")

    result = parse_union()

    if pos != len(tokens):
        raise RegexSyntaxError("Invalid regex structure")

    return result


def compile_regex(regex: str) -> NFA:
    """Compile a regex into an NFA using Thompson's construction."""

    ast = parse(regex)
    state_counter = 0

    def new_state():
        nonlocal state_counter
        state = state_counter
        state_counter += 1
        return state

    def add_epsilon(transitions, source, destination):
        transitions.setdefault(source, {})
        transitions[source].setdefault(EPS, set())
        transitions[source][EPS].add(destination)

    def build(node):
        if node.kind == "literal":
            start = new_state()
            accept = new_state()

            return NFA(
                states={start, accept},
                alphabet={node.value},
                transitions={start: {node.value: {accept}}},
                start=start,
                accepts={accept}
            )

        if node.kind == "class":
            start = new_state()
            accept = new_state()

            if node.value == "<letter>":
                chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
            else:
                chars = set("0123456789")

            return NFA(
                states={start, accept},
                alphabet=chars,
                transitions={
                    start: {char: {accept} for char in chars}
                },
                start=start,
                accepts={accept}
            )

        if node.kind == "concat":
            left = build(node.children[0])
            right = build(node.children[1])

            transitions = {
                state: {
                    symbol: set(destinations)
                    for symbol, destinations in edges.items()
                }
                for state, edges in left.transitions.items()
            }

            for state, edges in right.transitions.items():
                transitions[state] = {
                    symbol: set(destinations)
                    for symbol, destinations in edges.items()
                }

            for accept in left.accepts:
                add_epsilon(transitions, accept, right.start)

            return NFA(
                states=left.states | right.states,
                alphabet=left.alphabet | right.alphabet,
                transitions=transitions,
                start=left.start,
                accepts=set(right.accepts)
            )

        if node.kind == "union":
            left = build(node.children[0])
            right = build(node.children[1])

            start = new_state()
            accept = new_state()

            transitions = {
                state: {
                    symbol: set(destinations)
                    for symbol, destinations in edges.items()
                }
                for state, edges in left.transitions.items()
            }

            for state, edges in right.transitions.items():
                transitions[state] = {
                    symbol: set(destinations)
                    for symbol, destinations in edges.items()
                }

            add_epsilon(transitions, start, left.start)
            add_epsilon(transitions, start, right.start)

            for state in left.accepts | right.accepts:
                add_epsilon(transitions, state, accept)

            return NFA(
                states=left.states | right.states | {start, accept},
                alphabet=left.alphabet | right.alphabet,
                transitions=transitions,
                start=start,
                accepts={accept}
            )

        if node.kind == "plus":
            child = build(node.children[0])

            transitions = {
                state: {
                    symbol: set(destinations)
                    for symbol, destinations in edges.items()
                }
                for state, edges in child.transitions.items()
            }

            for accept in child.accepts:
                add_epsilon(transitions, accept, child.start)

            return NFA(
                states=set(child.states),
                alphabet=set(child.alphabet),
                transitions=transitions,
                start=child.start,
                accepts=set(child.accepts)
            )

        raise RegexSyntaxError(f"Unknown node type: {node.kind}")

    return build(ast)
