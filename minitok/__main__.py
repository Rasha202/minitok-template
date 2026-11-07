
"""Command-line interface (Part A4).

    python -m minitok tokenize SPEC INPUT

SPEC   path to a token-spec JSON file
INPUT  path to a UTF-8 source file to tokenize

Output: one token per line:
TYPE<TAB>lexeme<TAB>position
"""

from __future__ import annotations

import sys
from pathlib import Path

from .automata import ScanError, build_token_dfa, scan
from .spec import SpecError, load_spec


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if len(argv) != 3 or argv[0] != "tokenize":
        print(
            "usage: python -m minitok tokenize SPEC INPUT",
            file=sys.stderr
        )
        return 2

    spec_path, input_path = argv[1], argv[2]

    try:
        spec = load_spec(Path(spec_path))
        dfa = build_token_dfa(spec)

        with open(input_path, encoding="utf-8") as fh:
            text = fh.read()

        tokens = scan(dfa, spec, text)

    except ScanError as exc:
        print(
            f"error: no token at position {exc.position}",
            file=sys.stderr
        )
        return 1

    except (SpecError, OSError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    for tok in tokens:
        print(f"{tok.type}\t{tok.lexeme}\t{tok.position}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
