
"""Parts A3/A4 — Finite automata models, determinization, and scanner."""

from __future__ import annotations

from dataclasses import dataclass, field

EPS = ""


class ScanError(ValueError):
    """Raised when no token class matches at the current input position."""

    def __init__(self, message: str, position: int):
        super().__init__(message)
        self.position = position


@dataclass
class NFA:
    states: set[int] = field(default_factory=set)
    alphabet: set[str] = field(default_factory=set)
    transitions: dict[int, dict[str, set[int]]] = field(default_factory=dict)
    start: int = 0
    accepts: set[int] = field(default_factory=set)

    def simulate(self, s: str) -> bool:
        """Return True if the NFA accepts the input string."""

        current_states = eps_closure(self, {self.start})

        for char in s:
            next_states = set()

            for state in current_states:
                edges = self.transitions.get(state, {})
                next_states.update(edges.get(char, set()))

            current_states = eps_closure(self, next_states)

            if not current_states:
                return False

        return bool(current_states & self.accepts)


@dataclass
class DFA:
    states: set[int] = field(default_factory=set)
    alphabet: set[str] = field(default_factory=set)
    transitions: dict[int, dict[str, int]] = field(default_factory=dict)
    start: int = 0
    accepts: dict[int, str] = field(default_factory=dict)

    def simulate(self, s: str) -> str | None:
        """Return the accepting label, or None if rejected."""

        curr = self.start

        for char in s:
            if char not in self.transitions.get(curr, {}):
                return None

            curr = self.transitions[curr][char]

        return self.accepts.get(curr)


@dataclass
class Token:
    type: str
    lexeme: str
    position: int


def eps_closure(nfa: NFA, states: set[int]) -> set[int]:
    """Return the epsilon closure of a set of NFA states."""

    closure = set(states)
    stack = list(states)

    while stack:
        state = stack.pop()

        for next_state in nfa.transitions.get(state, {}).get(EPS, set()):
            if next_state not in closure:
                closure.add(next_state)
                stack.append(next_state)

    return closure


def determinize(
    nfa: NFA,
    label_of: dict[int, str],
    priority: list[str]
) -> DFA:
    """Convert an NFA into a DFA using subset construction."""

    dfa = DFA()
    dfa.alphabet = set(nfa.alphabet)

    priority_map = {
        name: index for index, name in enumerate(priority)
    }

    def get_best_label(states):
        labels = [
            label_of[state]
            for state in states
            if state in label_of
        ]

        if not labels:
            return None

        return min(
            labels,
            key=lambda name: priority_map.get(name, float("inf"))
        )

    start_closure = frozenset(
        eps_closure(nfa, {nfa.start})
    )

    state_mapping = {start_closure: 0}
    dfa.states = {0}
    dfa.start = 0

    start_label = get_best_label(start_closure)

    if start_label is not None:
        dfa.accepts[0] = start_label

    unprocessed = [start_closure]

    while unprocessed:
        current_set = unprocessed.pop()
        current_id = state_mapping[current_set]

        dfa.transitions.setdefault(current_id, {})

        for symbol in dfa.alphabet:
            next_states = set()

            for state in current_set:
                edges = nfa.transitions.get(state, {})
                next_states.update(edges.get(symbol, set()))

            next_closure = frozenset(
                eps_closure(nfa, next_states)
            )

            if next_closure not in state_mapping:
                new_id = len(state_mapping)
                state_mapping[next_closure] = new_id
                dfa.states.add(new_id)
                unprocessed.append(next_closure)

                label = get_best_label(next_closure)

                if label is not None:
                    dfa.accepts[new_id] = label

            dfa.transitions[current_id][symbol] = (
                state_mapping[next_closure]
            )

    return dfa


def build_token_dfa(spec: "TokenSpec") -> DFA:
    """Build one DFA for all token classes in the specification."""

    from .regex_compiler import compile_regex

    combined_nfa = NFA()
    combined_nfa.start = 0
    combined_nfa.states.add(0)

    label_of = {}
    next_state_offset = 1

    for tc in spec.tokens:
        sub_nfa = compile_regex(tc.regex)

        shift = next_state_offset - sub_nfa.start

        shifted_states = {
            state + shift for state in sub_nfa.states
        }

        combined_nfa.states.update(shifted_states)
        combined_nfa.alphabet.update(sub_nfa.alphabet)

        for state, edges in sub_nfa.transitions.items():
            new_state = state + shift

            combined_nfa.transitions[new_state] = {}

            for symbol, destinations in edges.items():
                combined_nfa.transitions[new_state][symbol] = {
                    destination + shift
                    for destination in destinations
                }

        for accept_state in sub_nfa.accepts:
            label_of[accept_state + shift] = tc.name

        combined_nfa.transitions.setdefault(0, {})
        combined_nfa.transitions[0].setdefault(EPS, set())
        combined_nfa.transitions[0][EPS].add(
            sub_nfa.start + shift
        )

        next_state_offset += len(sub_nfa.states)

    priority = [tc.name for tc in spec.tokens]

    return determinize(combined_nfa, label_of, priority)


def scan(dfa: DFA, spec: "TokenSpec", text: str) -> list[Token]:
    """Tokenize input using maximal munch and token priority."""

    skip_classes = {
        tc.name for tc in spec.tokens if tc.skip
    }

    tokens = []
    pos = 0
    n = len(text)

    while pos < n:
        curr = dfa.start
        curr_pos = pos

        last_accept_pos = -1
        last_accept_label = None

        while curr_pos < n:
            char = text[curr_pos]

            if char not in dfa.transitions.get(curr, {}):
                break

            curr = dfa.transitions[curr][char]
            curr_pos += 1

            if curr in dfa.accepts:
                last_accept_pos = curr_pos
                last_accept_label = dfa.accepts[curr]

        if last_accept_pos == -1:
            raise ScanError(
                f"No token at position {pos}",
                position=pos
            )

        lexeme = text[pos:last_accept_pos]

        if last_accept_label not in skip_classes:
            tokens.append(
                Token(
                    type=last_accept_label,
                    lexeme=lexeme,
                    position=pos
                )
            )

        pos = last_accept_pos

    return tokens
