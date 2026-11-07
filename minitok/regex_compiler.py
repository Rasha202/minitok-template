"""Part A2 — Regular-expression compiler: regex -> NFA (Thompson's construction).

Grammar you must support (see spec.py for the surface syntax):

    union   := concat ('|' concat)*
    concat  := star+
    star    := atom '*'*
    atom    := LITERAL | CLASS | '(' union ')'
    CLASS   := '<letter>' | '<digit>'
    LITERAL := alnum | escaped operator char | space | '_' | '.' etc.

Design guidance:
  - Parse to an AST (or postfix) with correct precedence (* > concat > |).
  - Compile each AST node to an NFA fragment following Sipser's inductive
    construction (§1.3): one start state, one accept state per fragment.
  - Remember: postfix '*' in THIS spec means "one or more" (a+), so
    `a*` compiles as concat(a, closure(a)). Empty matches must be impossible.
"""

from __future__ import annotations

from dataclasses import dataclass

from minitok.automata import NFA, EPS


class RegexSyntaxError(ValueError):
    """Raised for malformed regular expressions."""


@dataclass
class _Node:
    """Suggested AST node. You may use your own representation."""

    kind: str  # 'literal' | 'class' | 'union' | 'concat' | 'plus'
    value: str = ""
    children: list["_Node"] | None = None


def parse(regex: str) -> _Node:
    """Parse a regex string into an AST. Raise RegexSyntaxError on bad input."""
    tokens = []
    i = 0
    n = len(regex)
    
    while i < n:
        c = regex[i]
        if c == '\\':
            if i + 1 >= n:
                raise RegexSyntaxError("Trailing backslash in regex")
            tokens.append(regex[i:i+2])
            i += 2
        elif c == '<':
            end = regex.find('>', i)
            if end == -1:
                raise RegexSyntaxError("Unterminated character class")
            tokens.append(regex[i:end+1])
            i = end + 1
        else:
            tokens.append(c)
            i += 1

    # Insert explicit concatenation tokens where needed
    explicit_tokens = []
    for idx, tok in enumerate(tokens):
        if idx > 0:
            prev = tokens[idx - 1]
            prev_is_op_or_open = prev == '|' or prev == '('
            curr_is_op_or_close = tok == '|' or tok == '*' or tok == ')'
            if not prev_is_op_or_open and not curr_is_op_or_close:
                explicit_tokens.append('.')
        explicit_tokens.append(tok)

    # Shunting-yard algorithm to convert infix to postfix (AST)
    # Precedence: '*' (unary postfix) > '.' (concat) > '|' (union)
    precedence = {'*': 3, '.': 2, '|': 1}
    output = []
    operators = []

    for tok in explicit_tokens:
        if tok == '(':
            operators.append(tok)
        elif tok == ')':
            while operators and operators[-1] != '(':
                output.append(operators.pop())
            if not operators:
                raise RegexSyntaxError("Mismatched parentheses")
            operators.pop()  # pop '('
        elif tok in precedence:
            while (operators and operators[-1] != '(' and 
                   precedence.get(operators[-1], 0) >= precedence[tok]):
                output.append(operators.pop())
            operators.append(tok)
        else:
            output.append(tok)

    while operators:
        op = operators.pop()
        if op == '(' or op == ')':
            raise RegexSyntaxError("Mismatched parentheses")
        output.append(op)

    # Build AST from postfix expression
    stack = []
    for tok in output:
        if tok in precedence:
            if tok == '*':
                if not stack:
                    raise RegexSyntaxError("Invalid operator placement '*'")
                child = stack.pop()
                stack.append(_Node(kind='plus', children=[child]))
            else:
                if len(stack) < 2:
                    raise RegexSyntaxError(f"Invalid operator placement '{tok}'")
                right = stack.pop()
                left = stack.pop()
                kind = 'union' if tok == '|' else 'concat'
                stack.append(_Node(kind=kind, children=[left, right]))
        else:
            if tok.startswith('<') and tok.endswith('>'):
                stack.append(_Node(kind='class', value=tok))
            elif tok.startswith('\\'):
                stack.append(_Node(kind='literal', value=tok[1]))
            else:
                stack.append(_Node(kind='literal', value=tok))

    if len(stack) != 1:
        raise RegexSyntaxError("Invalid regex structure")
    return stack[0]


def compile_regex(regex: str) -> NFA:
    """Compile a regex string to an NFA (see automata.NFA for the model).

    The returned NFA must accept exactly the (non-empty) language of the
    regex, have exactly one start state and one accept state, and use
    epsilon transitions as needed (automata.EPS).
    """
    ast = parse(regex)
    state_counter = 0

    def new_state() -> int:
        nonlocal state_counter
        s = state_counter
        state_counter += 1
        return s

    def _build_nfa(node: _Node) -> NFA:
        if node.kind == 'literal':
            s = new_state()
            a = new_state()
            char = node.value
            return NFA(
                states={s, a},
                alphabet={char},
                transitions={s: {char: {a}}},
                start=s,
                accepts={a}
            )
        elif node.kind == 'class':
            s = new_state()
            a = new_state()
            if node.value == '<letter>':
                chars = {chr(c) for c in range(ord('a'), ord('z')+1)} | {chr(c) for c in range(ord('A'), ord('Z')+1)}
            elif node.value == '<digit>':
                chars = {chr(c) for c in range(ord('0'), ord('9')+1)}
            else:
                chars = set()
            return NFA(
                states={s, a},
                alphabet=set(chars),
                transitions={s: {c: {a} for c in chars}},
                start=s,
                accepts={a}
            )
        elif node.kind == 'concat':
            nfa1 = _build_nfa(node.children[0])
            nfa2 = _build_nfa(node.children[1])
            acc1 = list(nfa1.accepts)[0]
            
            transitions = dict(nfa1.transitions)
            for st, trans in nfa2.transitions.items():
                transitions[st] = dict(trans)
            
            if acc1 not in transitions:
                transitions[acc1] = {}
            if EPS not in transitions[acc1]:
                transitions[acc1][EPS] = set()
            transitions[acc1][EPS].add(nfa2.start)
            
            return NFA(
                states=nfa1.states | nfa2.states,
                alphabet=nfa1.alphabet | nfa2.alphabet,
                transitions=transitions,
                start=nfa1.start,
                accepts=nfa2.accepts
            )
        elif node.kind == 'union':
            nfa1 = _build_nfa(node.children[0])
            nfa2 = _build_nfa(node.children[1])
            s = new_state()
            a = new_state()
            
            transitions = dict(nfa1.transitions)
            for st, trans in nfa2.transitions.items():
                transitions[st] = dict(trans)
            
            transitions[s] = {EPS: {nfa1.start, nfa2.start}}
            
            acc1 = list(nfa1.accepts)[0]
            acc2 = list(nfa2.accepts)[0]
            
            if acc1 not in transitions:
                transitions[acc1] = {}
            if EPS not in transitions[acc1]:
                transitions[acc1][EPS] = set()
            transitions[acc1][EPS].add(a)
            
            if acc2 not in transitions:
                transitions[acc2] = {}
            if EPS not in transitions[acc2]:
                transitions[acc2][EPS] = set()
            transitions[acc2][EPS].add(a)
            
            return NFA(
                states=nfa1.states | nfa2.states | {s, a},
                alphabet=nfa1.alphabet | nfa2.alphabet,
                transitions=transitions,
                start=s,
                accepts={a}
            )
        elif node.kind == 'plus':
            child = node.children[0]
            nfa_base = _build_nfa(child)
            
            nfa_star = _build_nfa(child)
            s_star = new_state()
            a_star = new_state()
            
            transitions = dict(nfa_star.transitions)
            transitions[s_star] = {EPS: {nfa_star.start, a_star}}
            acc_star = list(nfa_star.accepts)[0]
            if acc_star not in transitions:
                transitions[acc_star] = {}
            if EPS not in transitions[acc_star]:
                transitions[acc_star][EPS] = set()
            transitions[acc_star][EPS].update({nfa_star.start, a_star})
            
            star_nfa = NFA(
                states=nfa_star.states | {s_star, a_star},
                alphabet=nfa_star.alphabet,
                transitions=transitions,
                start=s_star,
                accepts={a_star}
            )
            
            acc_base = list(nfa_base.accepts)[0]
            final_transitions = dict(nfa_base.transitions)
            for st, trans in star_nfa.transitions.items():
                final_transitions[st] = dict(trans)
            
            if acc_base not in final_transitions:
                final_transitions[acc_base] = {}
            if EPS not in final_transitions[acc_base]:
                final_transitions[acc_base][EPS] = set()
            final_transitions[acc_base][EPS].add(star_nfa.start)
            
            return NFA(
                states=nfa_base.states | star_nfa.states,
                alphabet=nfa_base.alphabet | star_nfa.alphabet,
                transitions=final_transitions,
                start=nfa_base.start,
                accepts=star_nfa.accepts
            )
        return NFA()

    return _build_nfa(ast)
