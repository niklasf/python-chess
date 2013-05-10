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

#include "polyglot_opening_book_entry.h"

namespace chess {

PolyglotOpeningBookEntry::PolyglotOpeningBookEntry(const Position& key, const Move& move, uint16_t weight, uint32_t learn) {
    m_weight = weight;
    m_learn = learn;

    m_key = key.__hash__();

    m_move = (move.target().file() << 0) |
	     (move.target().rank() << 3) |
	     (move.source().file() << 6) |
	     (move.source().rank() << 9);

    switch (move.promotion()) {
	case 'q':
	    m_move = m_move | (4 << 12);
	    break;
	case 'r':
	    m_move = m_move | (3 << 12);
	    break;
	case 'b':
	    m_move = m_move | (2 << 12);
	    break;
	case 'n':
	    m_move = m_move | (1 << 12);
	    break;
    }

}

PolyglotOpeningBookEntry::PolyglotOpeningBookEntry(uint64_t key, uint16_t move, uint16_t weight, uint32_t learn) {
    m_key = key;
    m_move = move;
    m_weight = weight;
    m_learn = learn;
}

PolyglotOpeningBookEntry::PolyglotOpeningBookEntry(const PolyglotOpeningBookEntry& entry) {
    m_key = entry.m_key;
    m_move = entry.m_move;
    m_weight = entry.m_weight;
    m_learn = entry.m_learn;
}

uint64_t PolyglotOpeningBookEntry::key() const {
    return m_key;
}

uint16_t PolyglotOpeningBookEntry::raw_move() const {
    return m_move;
}

Move PolyglotOpeningBookEntry::move() const {
    // Extract source and target square.
    Square source(
	(((m_move >> 6) & 0x3f) >> 3) & 0x7,
	((m_move >> 6) & 0x3f) & 0x7);
    Square target(
	((m_move & 0x3f) >> 3) & 0x7,
	(m_move & 0x3f) & 0x7);

    // Replace non standard castling moves.
    if (source.name() == "e1") {
	if (target.name() == "h1") {
	    return Move::from_uci("e1g1");
	} else if (target.name() == "a1") {
	    return Move::from_uci("e1c1");
	}
    } else if (source.name() == "e8") {
	if (target.name() == "h8") {
	    return Move::from_uci("e8g8");
	} else if (target.name() == "a8") {
	    return Move::from_uci("e8c8");
	}
    }

    // Extract the promotion type.
    switch ((m_move >> 12) & 0x7) {
       case 4:
	   return Move(source, target, 'q');
       case 3:
	   return Move(source, target, 'r');
       case 2:
	   return Move(source, target, 'b');
       case 1:
	   return Move(source, target, 'n');
       default:
	   return Move(source, target);
    }
}

uint16_t PolyglotOpeningBookEntry::weight() const {
    return m_weight;
}

void PolyglotOpeningBookEntry::set_weight(uint16_t weight) {
    m_weight = weight;
}

uint32_t PolyglotOpeningBookEntry::learn() const {
    return m_learn;
}

void PolyglotOpeningBookEntry::set_learn(uint32_t learn) {
    m_learn = learn;
}

PolyglotOpeningBookEntry& PolyglotOpeningBookEntry::operator=(const PolyglotOpeningBookEntry& rhs) {
    m_key = rhs.m_key;
    m_move = rhs.m_move;
    m_weight = rhs.m_weight;
    m_learn = rhs.m_learn;

    return *this;
}

} // namespace chess
