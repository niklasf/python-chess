#!/usr/bin/env python3

"""Play the immortal game using push_san() from chess.Board()."""

import chess
import timeit


def play_immortal_game() -> None:
    board = chess.Board()

    # 1. e4 e5
    board.push_san("e4")
    board.push_san("e5")

    # 2. f4 exf4
    board.push_san("f4")
    board.push_san("exf4")

    # 3. Bc4 Qh4+
    board.push_san("Bc4")
    board.push_san("Qh4+")

    # 4. Kf1 b5?!
    board.push_san("Kf1")
    board.push_san("b5")

    # 5. Bxb5 Nf6
    board.push_san("Bxb5")
    board.push_san("Nf6")

    # 6. Nf3 Qh6
    board.push_san("Nf3")
    board.push_san("Qh6")

    # 7. d3 Nh5
    board.push_san("d3")
    board.push_san("Nh5")

    # 8. Nh4 Qg5
    board.push_san("Nh4")
    board.push_san("Qg5")

    # 9. Nf5 c6
    board.push_san("Nf5")
    board.push_san("c6")

    # 10. g4 Nf6
    board.push_san("g4")
    board.push_san("Nf6")

    # 11. Rg1! cxb5?
    board.push_san("Rg1")
    board.push_san("cxb5")

    # 12. h4! Qg6
    board.push_san("h4")
    board.push_san("Qg6")

    # 13. h5 Qg5
    board.push_san("h5")
    board.push_san("Qg5")

    # 14. Qf3 Ng8
    board.push_san("Qf3")
    board.push_san("Ng8")

    # 15. Bxf4 Qf6
    board.push_san("Bxf4")
    board.push_san("Qf6")

    # 16. Nc3 Bc5
    board.push_san("Nc3")
    board.push_san("Bc5")

    # 17. Nd5 Qxb2
    board.push_san("Nd5")
    board.push_san("Qxb2")

    # 18. Bd6! Bxg1?
    board.push_san("Bd6")
    board.push_san("Bxg1")

    # 19. e5! Qxa1+
    board.push_san("e5")
    board.push_san("Qxa1+")

    # 20. Ke2 Na6
    board.push_san("Ke2")
    board.push_san("Na6")

    # 21. Nxg7+ Kd8
    board.push_san("Nxg7+")
    board.push_san("Kd8")

    # 22. Qf6+! Nxf6
    board.push_san("Qf6+")
    board.push_san("Nxf6")

    # 23. Be7# 1-0
    board.push_san("Be7#")
    assert board.is_checkmate()


if __name__ == "__main__":
    print(timeit.timeit(
        stmt="play_immortal_game()",
        setup="from __main__ import play_immortal_game",
        number=100))
