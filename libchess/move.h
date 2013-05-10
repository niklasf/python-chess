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

#ifndef LIBCHESS_MOVE_H
#define LIBCHESS_MOVE_H

#include "square.h"

#include <iostream>

namespace chess {

/**
 * \brief An immutable move.
 */
class Move {
public:
    Move(const Square& source, const Square& target, char promotion);
    Move(const Square& source, const Square& target);
    Move(const std::string& uci);
    Move(const Move& move);

    Square source() const;
    Square target() const;
    char promotion() const;
    std::string full_promotion() const;
    std::string uci() const;

    bool is_promotion() const;

    std::string __repr__() const;
    int __hash__() const;

    Move& operator=(const Move& rhs);
    bool operator==(const Move& rhs) const;
    bool operator!=(const Move& rhs) const;

    static Move from_uci(const std::string& uci);

private:
    Square m_source;
    Square m_target;
    char m_promotion;
};

std::ostream& operator<<(std::ostream &out, const Move& move);

} // namespace chess

#endif // LIBCHESS_MOVE_H
