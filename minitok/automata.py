
"""Parts A3/A4 — Finite automata models, determinization, and the scanner."""

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
        current = eps_closure(self, {self.start})

        for char in s:
            next_states = set()

            for state in current:
                next_states.update(
                    self.transitions.get(state, {}).get(char, set())
                )

            current = eps_closure(self, next_states)

            if not current:
                return False

        return bool(current & self.accepts)


@dataclass
class DFA:
    states: set[int] = field(default_factory=set)
    alphabet: set[str] = field(default_factory=set)
    transitions: dict[int, dict[str, int]] = field(default_factory=dict)
    start: int = 0
    accepts: dict[int, str] = field(default_factory=dict)

    def simulate(self, s: str) -> str | None:
        state = self.start

        for char in s:
            if char not in self.transitions.get(state, {}):
                return None

            state = self.transitions[state][char]

        return self.accepts.get(state)


@dataclass
class Token:
    type: str
    lexeme: str
    position: int


def eps_closure(nfa: NFA, states: set[int]) -> set[int]:
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
    start_set = frozenset(eps_closure(nfa, {nfa.start}))

    state_map = {start_set: 0}
    queue = [start_set]

    dfa = DFA(
        states={0},
        alphabet=set(nfa.alphabet),
        transitions={0: {}},
        start=0,
        accepts={}
    )

    priority_order = {name: i for i, name in enumerate(priority)}

    def get_label(subset):
        labels = [
            label_of[state]
            for state in subset
            if state in label_of
        ]

        if not labels:
            return None

        return min(
            labels,
            key=lambda name: priority_order.get(name, len(priority_order))
        )

    label = get_label(start_set)
    if label is not None:
        dfa.accepts[0] = label

    while queue:
        current = queue.pop(0)
        current_id = state_map[current]

        for symbol in sorted(nfa.alphabet):
            next_set = set()

            for state in current:
                next_set.update(
                    nfa.transitions.get(state, {}).get(symbol, set())
                )

            next_set = frozenset(eps_closure(nfa, next_set))

            if next_set not in state_map:
                new_id = len(state_map)
                state_map[next_set] = new_id
                dfa.states.add(new_id)
                dfa.transitions[new_id] = {}
                queue.append(next_set)

                label = get_label(next_set)
                if label is not None:
                    dfa.accepts[new_id] = label

            dfa.transitions[current_id][symbol] = state_map[next_set]

    return dfa


def build_token_dfa(spec: "TokenSpec") -> DFA:
    from .regex_compiler import compile_regex

    combined = NFA()
    combined.start = 0
    combined.states.add(0)

    label_of = {}
    priority = []
    next_state = 1

    for token_class in spec.tokens:
        name = token_class.name
        regex = token_class.regex

        nfa = compile_regex(regex)

        mapping = {
            state: next_state + i
            for i, state in enumerate(sorted(nfa.states))
        }

        next_state += len(mapping)

        combined.states.update(mapping.values())
        combined.alphabet.update(nfa.alphabet)

        combined.transitions.setdefault(0, {}).setdefault(EPS, set()).add(
            mapping[nfa.start]
        )

        for state, transitions in nfa.transitions.items():
            new_state = mapping[state]

            combined.transitions.setdefault(new_state, {})

            for symbol, destinations in transitions.items():
                combined.transitions[new_state].setdefault(symbol, set()).update(
                    mapping[destination] for destination in destinations
                )

        for accept_state in nfa.accepts:
            label_of[mapping[accept_state]] = name

        priority.append(name)

    return determinize(combined, label_of, priority)


def scan(dfa: DFA, spec: "TokenSpec", text: str) -> list[Token]:
    tokens = []
    token_map = {
        token.name: token
        for token in spec.tokens
    }

    position = 0

    while position < len(text):
        state = dfa.start
        current = position

        last_accept = None
        last_end = position

        while current < len(text):
            char = text[current]

            if char not in dfa.transitions.get(state, {}):
                break

            state = dfa.transitions[state][char]
            current += 1

            if state in dfa.accepts:
                last_accept = dfa.accepts[state]
                last_end = current

        if last_accept is None:
            raise ScanError(
                f"No token matches at position {position}",
                position
            )

        lexeme = text[position:last_end]
        token_class = token_map[last_accept]

        if not token_class.skip:
            tokens.append(
                Token(
                    type=last_accept,
                    lexeme=lexeme,
                    position=position
                )
            )

        position = last_end

    return tokens
