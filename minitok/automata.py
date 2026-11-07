"""Parts A3/A4 — Finite automata models, determinization, and the scanner.

Data model (plain Python, no external deps):

  - An NFA is a set of states with transitions
        nfa.transitions[state][symbol] -> set of states
    symbol is a single character, or EPS (epsilon).
  - A DFA has a total transition function
        dfa.transitions[state][symbol] -> state
  - Accepting states of a tokenizer DFA are *labeled* with the token-class
    name they recognize (dfa.accepts[state] == "IDENT"), because one DFA
    serves the whole token specification.

The scanner performs MAXIMAL MUNCH (longest match wins) with PRIORITY
tie-breaking: among equally-long matches at the same position, the token
class declared earliest in the spec wins.
"""

from __future__ import annotations

from dataclasses import dataclass, field

EPS = ""  # epsilon-transition marker


class ScanError(ValueError):
    """Raised when no token class matches at the current input position.

    `position` is the 0-based character offset of the failure."""

    def __init__(self, message: str, position: int):
        super().__init__(message)
        self.position = position


@dataclass
class NFA:
    states: set[int] = field(default_factory=set)
    alphabet: set[str] = field(default_factory=set)  # excludes EPS
    transitions: dict[int, dict[str, set[int]]] = field(default_factory=dict)
    start: int = 0
    accepts: set[int] = field(default_factory=set)

    def simulate(self, s: str) -> bool:
        """True iff this NFA accepts string s (on-the-fly subset simulation
        with epsilon closures). Must handle epsilon cycles."""
        # TODO(PART A2/A3): implement
        current_states = eps_closure(self, {self.start})
        for char in s:
            next_states = set()
            for state in current_states:
                if state in self.transitions and char in self.transitions[state]:
                    next_states.update(self.transitions[state][char])
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
    # tokenizer DFAs label accepting states with token-class names:
    accepts: dict[int, str] = field(default_factory=dict)

    def simulate(self, s: str) -> str | None:
        """Return the accepting label for s, or None if rejected/incomplete."""
        # TODO(PART A3): implement
        curr = self.start
        for char in s:
            if curr in self.transitions and char in self.transitions[curr]:
                curr = self.transitions[curr][char]
            else:
                return None
        return self.accepts.get(curr)


@dataclass
class Token:
    type: str
    lexeme: str
    position: int  # 0-based offset of the first character of the lexeme


def eps_closure(nfa: NFA, states: set[int]) -> set[int]:
    """Epsilon closure of a set of NFA states."""
    # TODO(PART A2/A3): implement
    closure = set(states)
    stack = list(states)
    while stack:
        state = stack.pop()
        if state in nfa.transitions and EPS in nfa.transitions[state]:
            for next_state in nfa.transitions[state][EPS]:
                if next_state not in closure:
                    closure.add(next_state)
                    stack.append(next_state)
    return closure


def determinize(nfa: NFA, label_of: dict[int, str], priority: list[str]) -> DFA:
    """Subset construction (Sipser §1.2) producing a tokenizer DFA.

    label_of: NFA accept state -> token-class name.
    priority: token-class names from highest to lowest priority; when a
    DFA state contains several labeled NFA accept states, keep the label
    with the highest priority (this implements tie-breaking).
    Transitions must be total over `nfa.alphabet` (use a dead state -1 or
    omit transitions to it consistently and document your choice).
    """
    # TODO(PART A3): implement
    dfa = DFA()
    dfa.alphabet = set(nfa.alphabet)
    
    # Priority mapping for tie-breaking
    priority_map = {name: i for i, name in enumerate(priority)}

    def get_best_label(nfa_states: set[int]) -> str | None:
        best_label = None
        best_prio = float('inf')
        for st in nfa_states:
            if st in label_of:
                lbl = label_of[st]
                prio = priority_map.get(lbl, float('inf'))
                if prio < best_prio:
                    best_prio = prio
                    best_label = lbl
        return best_label

    start_closure = frozenset(eps_closure(nfa, {nfa.start}))
    state_mapping: dict[frozenset[int], int] = {start_closure: 0}
    dfa.states = {0}
    dfa.start = 0

    if (lbl := get_best_label(set(start_closure))) is not None:
        dfa.accepts[0] = lbl

    unprocessed = [start_closure]
    
    while unprocessed:
        curr_set = unprocessed.pop()
        curr_id = state_mapping[curr_set]

        if curr_id not in dfa.transitions:
            dfa.transitions[curr_id] = {}

        for symbol in dfa.alphabet:
            next_nfa_states = set()
            for st in curr_set:
                if st in nfa.transitions and symbol in nfa.transitions[st]:
                    next_nfa_states.update(nfa.transitions[st][symbol])
            
            if not next_nfa_states:
                continue

            closure = frozenset(eps_closure(nfa, next_nfa_states))
            if not closure:
                continue

            if closure not in state_mapping:
                new_id = len(state_mapping)
                state_mapping[closure] = new_id
                dfa.states.add(new_id)
                unprocessed.append(closure)
                if (lbl := get_best_label(set(closure))) is not None:
                    dfa.accepts[new_id] = lbl

            dfa.transitions[curr_id][symbol] = state_mapping[closure]

    return dfa


def build_token_dfa(spec: "TokenSpec") -> DFA:
    """Compile every token class of the spec into one combined DFA.

    Steps: compile each class regex to an NFA (regex_compiler), union the
    NFAs with a new start state and epsilon edges, then determinize with
    per-class labels and spec-order priority.
    """
    # TODO(PART A3): implement
    from .regex import compile_regex

    combined_nfa = NFA()
    combined_nfa.start = 0
    combined_nfa.states.add(0)
    
    label_of = {}
    next_state_offset = 1

    for tc in spec.classes:
        sub_nfa = compile_regex(tc.pattern)
        
        # Shift sub_nfa states to avoid collisions
        shift = next_state_offset - sub_nfa.start
        shifted_states = {st + shift for st in sub_nfa.states}
        shifted_accepts = {st + shift for st in sub_nfa.accepts}
        
        shifted_transitions = {}
        for st, trans in sub_nfa.transitions.items():
            shifted_transitions[st + shift] = {
                sym: {dst + shift for dst in dests}
                for sym, dests in trans.items()
            }
        
        combined_nfa.states.update(shifted_states)
        combined_nfa.alphabet.update(sub_nfa.alphabet)
        combined_nfa.transitions.update(shifted_transitions)
        
        for acc in shifted_accepts:
            label_of[acc] = tc.name
        
        # Connect combined start to sub_nfa start via epsilon
        if 0 not in combined_nfa.transitions:
            combined_nfa.transitions[0] = {}
        if EPS not in combined_nfa.transitions[0]:
            combined_nfa.transitions[0][EPS] = set()
        combined_nfa.transitions[0][EPS].add(sub_nfa.start + shift)
        
        next_state_offset += len(sub_nfa.states)

    priority = [tc.name for tc in spec.classes]
    
    return determinize(combined_nfa, label_of, priority)


def scan(dfa: DFA, spec: "TokenSpec", text: str) -> list[Token]:
    """Tokenize `text` by repeated maximal munch from the DFA start state.

    At each position: walk the DFA as far as possible, remember the last
    accepting label seen and its length; emit that Token (longest match);
    if the class has skip=true, discard instead. On no match, raise
    ScanError with the failing position. Must handle end-of-input while
    inside a token (e.g. text ending in an identifier).
    """
    # TODO(PART A4): implement
    skip_classes = {tc.name for tc in spec.classes if tc.skip}
    tokens = []
    pos = 0
    n = len(text)

    while pos < n:
        curr = dfa.start
        last_accept_pos = -1
        last_accept_label = None
        
        # Maximal Munch exploration
        curr_pos = pos
        while curr_pos < n:
            char = text[curr_pos]
            if curr in dfa.transitions and char in dfa.transitions[curr]:
                curr = dfa.transitions[curr][char]
                curr_pos += 1
                if curr in dfa.accepts:
                    last_accept_pos = curr_pos
                    last_accept_label = dfa.accepts[curr]
            else:
                break

        if last_accept_pos != -1:
            lexeme = text[pos:last_accept_pos]
            if last_accept_label not in skip_classes:
                tokens.append(Token(type=last_accept_label, lexeme=lexeme, position=pos))
            pos = last_accept_pos
        else:
            raise ScanError(f"no token at position {pos}", position=pos)

    return tokens
