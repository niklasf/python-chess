#!/usr/bin/env python

import argparse
import chess
import json
import sys

def read_eco(source):
    result = { }

    tokens = [ ]

    eco = None
    name = None
    position = chess.Position()
    state = 0

    for lineno, unstripped_line in enumerate(source):
        # Skip emtpy lines and comments.
        line = unstripped_line.strip()
        if not line or line.startswith("#"):
            continue

        # Split line into tokens.
        tokens += line.split()

        # Consume tokens on the fly.
        while tokens:
            try:
                token = tokens.pop(0)

                if state == 0:
                    # State 0: Expecting ECO code.
                    eco = token
                    if eco in result:
                        state = 4
                    else:
                        state = 1
                elif state == 1:
                    # State 1: Expecting variation name.
                    if not token.startswith("\""):
                        name = token
                        state = 3
                    name = token[1:]
                    state = 2
                elif state == 2:
                    # State 2: Expecting rest of a quoted name.
                    if not token.endswith("\""):
                        name += " " + token
                    else:
                        name += " " + token[:-1]
                        state = 3
                elif state == 3:
                    # State 3: Expecting moves.
                    if token == "*":
                        result[eco] = {
                            "eco": eco,
                            "fen": position.fen,
                            "hash": position.__hash__(),
                            "name": name,
                        }
                        state = 0
                        eco = None
                        name = None
                        position = chess.Position()
                    else:
                        san = token.split(".")[-1]
                        if san in ["0-0", "O-O"]:
                            san = "o-o"
                        elif san in ["0-0-0", "O-O-O"]:
                            san = "o-o-o"
                        position.make_move_from_san(san)
                elif state == 4:
                    # State 4: Waiting for end of record.
                    if token == "*":
                        state = 0
            except:
                # Dump last line and token.
                sys.stderr.write("Line %d:\n" % (lineno + 1, ))
                sys.stderr.write("  ")
                sys.stderr.write(unstripped_line)
                sys.stderr.write("  ")
                sys.stderr.write(" " * unstripped_line.index(token))
                sys.stderr.write("^" * len(token))
                sys.stderr.write("\n")

                # Dump current variables.
                sys.stderr.write("State: %d\n" % state)
                sys.stderr.write("ECO: %s\n" % eco)
                sys.stderr.write("FEN: %s\n" % position.fen)
                sys.stderr.write("Name: %s\n" % name)
                sys.stderr.flush()
                raise


    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compiles ECO files to JSON for faster lookups.")

    parser.add_argument("source",
        type=argparse.FileType("r"),
        nargs="?",
        default=sys.stdin,
        help="The input ECO file.")

    args = parser.parse_args()

    json.dump(read_eco(args.source), sys.stdout,
        ensure_ascii=False,
        indent=4,
        separators=(",", ": "),
        sort_keys=True)
