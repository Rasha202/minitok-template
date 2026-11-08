
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
    transitions: dict[int, dict[str, set[int]]] = field(
        default_factory=dict
    )
    start: int = 0
    accepts: set[int] = field(default_factory=set)

    def simulate(self, s: str) -> bool:
        """Return True if the NFA accepts the input string."""

        current = eps_closure(self, {self.start})

        for char in s:
            next_states = set()

            for state in current:
                destinations = self.transitions.get(
                    state, {}
                ).get(char, set())

                next_states.update(destinations)

            current = eps_closure(self, next_states)

            if not current:
                return False

        return bool(current & self.accepts)


@dataclass
class DFA:
    states: set[int] = field(default_factory=set)
    alphabet: set[str] = field(default_factory=set)
    transitions: dict[int, dict[str, int]] = field(
        default_factory=dict
    )
    start: int = 0
    accepts: dict[int, str] = field(default_factory=dict)

    def simulate(self, s: str) -> str | None:
        """Return the accepting label or None if rejected."""

        state = self.start

        for char in s:
            if char not in self.alphabet:
                return None

            state = self.transitions.get(
                state, {}
            ).get(char)

            if state is None or state == -1:
                return None

        return self.accepts.get(state)


@dataclass
class Token:
    type: str
    lexeme: str
    position: int


def eps_closure(nfa: NFA, states: set[int]) -> set[int]:
    """Calculate epsilon closure, handling epsilon cycles."""

    closure = set(states)
    stack = list(states)

    while stack:
        state = stack.pop()

        destinations = nfa.transitions.get(
            state, {}
        ).get(EPS, set())

        for destination in destinations:
            if destination not in closure:
                closure.add(destination)
                stack.append(destination)

    return closure


def determinize(
    nfa: NFA,
    label_of: dict[int, str],
    priority: list[str]
) -> DFA:
    """Convert an NFA to a DFA using subset construction."""

    start_subset = frozenset(
        eps_closure(nfa, {nfa.start})
    )

    subsets = {
        start_subset: 0
    }

    queue = [start_subset]

    transitions = {}
    accepts = {}
    states = {0}

    next_id = 1

    priority_order = {
        name: index
        for index, name in enumerate(priority)
    }

    while queue:
        current_subset = queue.pop(0)
        current_id = subsets[current_subset]

        transitions[current_id] = {}

        # Find accepting labels in the current subset.
        matching_labels = {
            label_of[state]
            for state in current_subset
            if state in label_of
        }

        if matching_labels:
            accepts[current_id] = min(
                matching_labels,
                key=lambda name: priority_order.get(
                    name, len(priority_order)
                )
            )

        # Process every symbol in the alphabet.
        for symbol in sorted(nfa.alphabet):
            next_states = set()

            for state in current_subset:
                destinations = nfa.transitions.get(
                    state, {}
                ).get(symbol, set())

                next_states.update(destinations)

            next_closure = frozenset(
                eps_closure(nfa, next_states)
            )

            if next_closure not in subsets:
                subsets[next_closure] = next_id
                states.add(next_id)
                queue.append(next_closure)
                next_id += 1

            transitions[current_id][symbol] = (
                subsets[next_closure]
            )

    # Add a dead state to make the DFA total.
    dead_state = -1
    states.add(dead_state)

    transitions[dead_state] = {
        symbol: dead_state
        for symbol in nfa.alphabet
    }

    for state in list(transitions):
        if state == dead_state:
            continue

        for symbol in nfa.alphabet:
            if symbol not in transitions[state]:
                transitions[state][symbol] = dead_state

    return DFA(
        states=states,
        alphabet=set(nfa.alphabet),
        transitions=transitions,
        start=0,
        accepts=accepts
    )


def build_token_dfa(spec: "TokenSpec") -> DFA:
    """Compile all token classes into one combined DFA."""

    from .regex_compiler import compile_regex

    combined = NFA()

    combined_start = 0
    combined.states.add(combined_start)
    combined.transitions[combined_start] = {}

    label_of = {}
    priority = []

    next_state = 1

    for token_class in spec.tokens:

        nfa = compile_regex(token_class.regex)

        # Give each NFA unique state numbers.
        state_map = {
            state: state + next_state
            for state in nfa.states
        }

        combined.states.update(state_map.values())

        combined.alphabet.update(nfa.alphabet)

        # Copy transitions with remapped state numbers.
        for old_state, edges in nfa.transitions.items():

            new_state = state_map[old_state]

            combined.transitions.setdefault(
                new_state, {}
            )

            for symbol, destinations in edges.items():

                new_destinations = {
                    state_map[destination]
                    for destination in destinations
                }

                combined.transitions[new_state].setdefault(
                    symbol, set()
                ).update(new_destinations)

        # Connect the combined start to this NFA start.
        combined.transitions[combined_start].setdefault(
            EPS, set()
        ).add(state_map[nfa.start])

        # Label accepting states with token names.
        for accept_state in nfa.accepts:
            label_of[state_map[accept_state]] = (
                token_class.name
            )

        priority.append(token_class.name)

        next_state += len(nfa.states)

    return determinize(
        combined,
        label_of,
        priority
    )


def scan(
    dfa: DFA,
    spec: "TokenSpec",
    text: str
) -> list[Token]:
    """Tokenize text using maximal munch and priority."""

    skip_tokens = {
        token.name
        for token in spec.tokens
        if token.skip
    }

    result = []
    position = 0

    while position < len(text):

        state = dfa.start

        last_accept_label = None
        last_accept_length = 0

        current_position = position

        # Walk as far as possible.
        while current_position < len(text):

            char = text[current_position]

            if char not in dfa.alphabet:
                break

            next_state = dfa.transitions.get(
                state, {}
            ).get(char)

            if next_state is None or next_state == -1:
                break

            state = next_state
            current_position += 1

            # Remember the last accepting state.
            if state in dfa.accepts:
                last_accept_label = dfa.accepts[state]
                last_accept_length = (
                    current_position - position
                )

        # No token matched at this position.
        if last_accept_label is None:
            raise ScanError(
                f"No token matches at position {position}",
                position
            )

        lexeme = text[
            position:position + last_accept_length
        ]

        # Skip whitespace or other ignored tokens.
        if last_accept_label not in skip_tokens:
            result.append(
                Token(
                    type=last_accept_label,
                    lexeme=lexeme,
                    position=position
                )
            )

        position += last_accept_length

    return result
