/**
 * \mainpage
 * libchess is a high level C++ and Python chess library.
 * https://github.com/niklasf/libchess
 *
 * \section Introduction
 * This is the scholars mate in libchess:
 * \code{.py}
 * pos = libchess.Position()
 * pos.make_move_from_san("e4")
 * pos.make_move_from_san("e5")
 * pos.make_move_from_san("Qh5")
 * pos.make_move_from_san("Nc6")
 * pos.make_move_from_san("Nf6")
 * pos.make_move_from_san("Qxf7")
 * assert pos.is_checkmate()
 * \endcode
 *
 * \section Features
 * - Legal move generator and move validation.
 *   \code{.py}
 *   assert not libchess.Move.from_uci("e8a1") in pos.get_legal_moves()
 *   \endcode
 * - Detects checkmates and stalemates.
 *   \code{.py}
 *   assert not pos.is_stalemate()
 *   \endcode
 * - Detects checks and can enumerate attackers and defenders of a square.
 *   \code{.py}
 *   assert pos.is_check()
 *   assert libchess.Square("f7") in pos.get_attackers("w", libchess.Square("e8"))
 *   \endcode
 * - Parses and creates SAN representation of moves.
 *   \code{.py}
 *   pos = libchess.Position()
 *   move_info = pos.make_move(libchess.Move.from_uci("e2e4"))
 *   assert "e4" == move_info.san
 *   \endcode
 * - Parses and creates FENs.
 *   \code{.py}
 *   pos = libchess.Position()
 *   assert pos.fen == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
 *
 *   pos = libchess.Position("8/8/8/2k5/4K3/8/8/8 w - - 4 45")
 *   assert pos["c5"] == libchess.Piece("k")
 *   \endcode
 *
 * \section Building
 * cmake, libboost-regex-dev and libboost-python-dev are required.
 * \code
 * cmake .
 * make
 * sudo python setup.py install
 * \endcode
 *
 * \section Performance
 * libchess is not intended to be used by chess engines where performanc is
 * critical. The goal is rather to create a simple and high level chess
 * library.
 * That said: Large parts are in C++ for a reason. libchess generates,
 * validates and plays moves about 50 times faster than
 * https://github.com/niklasf/python-chess/.
 *
 * \section License
 * libchess is licensed under the GPL3. See the LICENSE file for the full
 * copyright and license information.
 */

#ifndef LIBCHESS_LIBCHESS_H
#define LIBCHESS_LIBCHESS_H

#include "piece.h"
#include "square.h"
#include "move.h"
#include "move_info.h"
#include "attacker_generator.h"
#include "legal_move_generator.h"
#include "pseudo_legal_move_generator.h"
#include "position.h"
#include "polyglot_opening_book_entry.h"

namespace chess {

    char opposite_color(char color);

}

#endif
