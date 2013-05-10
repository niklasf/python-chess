// This file is part of the python-chess library.
// Copyright (C) 2013 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have recieved a copy of the GNU General Public License
// along with this program. If not, see <http://gnu.org/licenses/>.

#ifndef LIBCHESS_MOVE_INFO_H
#define LIBCHESS_MOVE_INFO_H

#include <boost/python.hpp>

#include "piece.h"
#include "move.h"

namespace chess {

/**
 * \brief Information about a move made in a position.
 */
class MoveInfo {
public:
    MoveInfo(const Move& move, const Piece& piece);
    MoveInfo(const MoveInfo& move_info);

    Move move() const;
    void set_move(const Move& move);

    Piece piece() const;
    void set_piece(const Piece& piece);

    Piece captured() const;
    boost::python::object python_captured() const;
    void set_captured(const Piece& captured);
    void python_set_captured(const boost::python::object& captured);

    bool is_enpassant() const;
    void set_is_enpassant(bool is_enpassant);

    bool is_kingside_castle() const;
    void set_is_kingside_castle(bool is_kingside_castle);

    bool is_queenside_castle() const;
    void set_is_queenside_castle(bool is_queenside_castle);

    bool is_castle() const;

    bool is_check() const;
    void set_is_check(bool is_check);

    bool is_checkmate() const;
    void set_is_checkmate(bool is_checkmate);

    std::string san() const;
    void set_san(const std::string& san);

    MoveInfo& operator=(const MoveInfo& rhs);

private:
    Move m_move;
    Piece m_piece;
    Piece m_captured;
    bool m_is_enpassant;
    bool m_is_kingside_castle;
    bool m_is_queenside_castle;
    bool m_is_check;
    bool m_is_checkmate;
    std::string m_san;
};

} // namespace chess

#endif // LIBCHESS_MOVE_INFO_H
