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

#ifndef LIBCHESS_ATTACKER_GENERATOR_H
#define LIBCHESS_ATTACKER_GENERATOR_H

#include "position.h"

namespace chess {

class Position;

/**
 * \brief Enumerates attackers of a given side on a specific square of the
 *   given position.
 */
class AttackerGenerator : boost::noncopyable {
public:
    AttackerGenerator(const Position& position, char color, const Square& target);
    ~AttackerGenerator();

    int __len__();
    bool __nonzero__();
    AttackerGenerator& __iter__();
    bool __contains__(const Square& square);

    bool has_more();
    Square next();
    Square python_next();

private:
    char m_color;
    Position* m_position;
    Square m_target;
    int m_source_index;
};

} // namespace chess

#endif // LIBCHESS_ATTACKER_GENERATOR_H
