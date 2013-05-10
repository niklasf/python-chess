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

#ifndef LIBCHESS_PSEUDO_LEGAL_MOVE_GENERATOR_H
#define LIBCHESS_PSEUDO_LEGAL_MOVE_GENERATOR_H

#include <boost/shared_ptr.hpp>
#include <queue>

#include "position.h"
#include "move.h"

namespace chess {

class Position;

/**
 * \brief Enumerates pseudo legal moves in a given position.
 */
class PseudoLegalMoveGenerator : boost::noncopyable {
public:
     PseudoLegalMoveGenerator(const Position& position);
     ~PseudoLegalMoveGenerator();

     int __len__();
     bool __nonzero__();
     PseudoLegalMoveGenerator& __iter__();
     bool __contains__(const Move& move);

     bool has_more();
     Move next();
     Move python_next();

protected:
     void generate_from_square(const Square& square);
     std::queue<Move> m_cache;

private:
     Position* m_position;
     int m_index;
};

} // namespace chess

#endif // LIBCHESS_PSEUDO_LEGAL_MOVE_GENERATOR_H
