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

#ifndef LIBCHESS_PIECE_H
#define LIBCHESS_PIECE_H

#include <iostream>

namespace chess {

/**
 * \brief An immutable chess piece.
 */
class Piece {
public:
    Piece();
    Piece(char symbol);
    Piece(const Piece& piece);

    char color() const;
    char type() const;
    char symbol() const;
    std::string full_color() const;
    std::string full_type() const;

    std::string __repr__() const;
    int __hash__() const;

    bool is_valid() const;

    Piece& operator=(const Piece& rhs);
    bool operator==(const Piece& rhs) const;
    bool operator!=(const Piece& rhs) const;

    static Piece from_color_and_type(char color, char type);

private:
    char m_symbol;
};

std::ostream& operator<<(std::ostream& out, const Piece& piece);

} // namespace chess

#endif // LIBCHESS_PIECE_H
