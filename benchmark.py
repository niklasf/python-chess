#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2012-2014 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import chess
import timeit

def play_immortal_game():
    bitboard = chess.Bitboard()

    # 1.e4 e5
    bitboard.push_san("e4")
    bitboard.push_san("e5")

    # 2.f4 exf4
    bitboard.push_san("f4")
    bitboard.push_san("exf4")

    # 3.Bc4 Qh4+
    bitboard.push_san("Bc4")
    bitboard.push_san("Qh4+")

    # 4.Kf1 b5?!
    bitboard.push_san("Kf1")
    bitboard.push_san("b5")

    # 5.Bxb5 Nf6
    bitboard.push_san("Bxb5")
    bitboard.push_san("Nf6")

    # 6.Nf3 Qh6
    bitboard.push_san("Nf3")
    bitboard.push_san("Qh6")

    # 7.d3 Nh5
    bitboard.push_san("d3")
    bitboard.push_san("Nh5")

    # 8.Nh4 Qg5
    bitboard.push_san("Nh4")
    bitboard.push_san("Qg5")

    # 9.Nf5 c6
    bitboard.push_san("Nf5")
    bitboard.push_san("c6")

    # 10.g4 Nf6
    bitboard.push_san("g4")
    bitboard.push_san("Nf6")

    # 11.Rg1! cxb5?
    bitboard.push_san("Rg1")
    bitboard.push_san("cxb5")

    # 12.h4! Qg6
    bitboard.push_san("h4")
    bitboard.push_san("Qg6")

    # 13.h5 Qg5
    bitboard.push_san("h5")
    bitboard.push_san("Qg5")

    # 14.Qf3 Ng8
    bitboard.push_san("Qf3")
    bitboard.push_san("Ng8")

    # 15.Bxf4 Qf6
    bitboard.push_san("Bxf4")
    bitboard.push_san("Qf6")

    # 16.Nc3 Bc5
    bitboard.push_san("Nc3")
    bitboard.push_san("Bc5")

    # 17.Nd5 Qxb2
    bitboard.push_san("Nd5")
    bitboard.push_san("Qxb2")

    # 18.Bd6! Bxg1?
    bitboard.push_san("Bd6")
    bitboard.push_san("Bxg1")

    # 19.e5! Qxa1+
    bitboard.push_san("e5")
    bitboard.push_san("Qxa1+")

    # 20.Ke2 Na6
    bitboard.push_san("Ke2")
    bitboard.push_san("Na6")

    # 21.Nxg7+ Kd8
    bitboard.push_san("Nxg7+")
    bitboard.push_san("Kd8")

    # 22.Qf6+! Nxf6
    bitboard.push_san("Qf6+")
    bitboard.push_san("Nxf6")

    # 23.Be7# 1-0
    bitboard.push_san("Be7#")
    assert bitboard.is_checkmate()

if __name__ == "__main__":
    print(timeit.timeit(
        stmt="play_immortal_game()",
        setup="from __main__ import play_immortal_game",
        number=100))
