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

#include "legal_move_generator.h"

namespace chess {

LegalMoveGenerator::LegalMoveGenerator(const Position& position) {
    m_position = new Position(position);
    m_pseudo_legal_moves = m_position->get_pseudo_legal_moves();
    m_len = -1;
    m_current = 0;
}

LegalMoveGenerator::~LegalMoveGenerator() {
    delete m_position;
    delete m_pseudo_legal_moves;
}

int LegalMoveGenerator::__len__() {
    if (m_len == -1) {
	m_pseudo_legal_moves->__iter__();

	int counter = 0;
	while (m_pseudo_legal_moves->has_more()) {
	    if (would_be_valid_if_pseudo_legal(m_pseudo_legal_moves->next())) {
		counter++;
	    }
	}
	m_len = counter;

	m_pseudo_legal_moves->__iter__();
    }
    return m_len;
}

bool LegalMoveGenerator::__nonzero__() {
    if (m_len == 0) {
	return false;
    }

    m_pseudo_legal_moves->__iter__();

    while (m_pseudo_legal_moves->has_more()) {
	if (would_be_valid_if_pseudo_legal(m_pseudo_legal_moves->next())) {
	    return true;
	}
    }

    m_len = 0;
    return false;
}

LegalMoveGenerator& LegalMoveGenerator::__iter__() {
    m_current = 0;
    m_pseudo_legal_moves->__iter__();
    return *this;
}

bool LegalMoveGenerator::__contains__(const Move& move) {
    if (!m_pseudo_legal_moves->__contains__(move)) {
	return false;
    } else {
	return would_be_valid_if_pseudo_legal(move);
    }
}

Move LegalMoveGenerator::next() {
    while (true) {
	Move move = m_pseudo_legal_moves->next();
	if (would_be_valid_if_pseudo_legal(move)) {
	   m_current++;
	   return move;
	}
    }
}

Move LegalMoveGenerator::python_next() {
    while (true) {
	Move move = m_pseudo_legal_moves->python_next();
	if (would_be_valid_if_pseudo_legal(move)) {
	    m_current++;
	    return move;
	}
    }
}

bool LegalMoveGenerator::has_more() {
    return m_current < __len__();
}

bool LegalMoveGenerator::would_be_valid_if_pseudo_legal(const Move& move) const {
    Position position = Position(*m_position);
    position.make_unvalidated_move_fast(move);
    return !position.is_king_attacked(m_position->turn());
}

} // namespace chess
