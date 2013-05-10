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

#ifndef LIBCHESS_LEGAL_MOVE_GENERATOR_H
#define LIBCHESS_LEGAL_MOVE_GENERATOR_H

#include <boost/shared_ptr.hpp>

#include "position.h"
#include "pseudo_legal_move_generator.h"

namespace chess {

class Position;

/**
 * \brief Enumerates legal moves in a given position.
 */
class LegalMoveGenerator : boost::noncopyable {
public:
    LegalMoveGenerator(const Position& position);
    ~LegalMoveGenerator();

    int __len__();
    bool __nonzero__();
    LegalMoveGenerator& __iter__();
    bool __contains__(const Move& move);

    Move next();
    Move python_next();
    bool has_more();

private:
    bool would_be_valid_if_pseudo_legal(const Move& move) const;

    Position* m_position;
    PseudoLegalMoveGenerator* m_pseudo_legal_moves;
    int m_len;
    int m_current;
};

} // namespace chess

#endif // LIBCHESS_LEGAL_MOVE_GENERATOR_H
