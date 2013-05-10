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

#ifndef LIBCHESS_POLYGLOT_OPENING_BOOK_ENTRY_H
#define LIBCHESS_POLYGLOT_OPENING_BOOK_ENTRY_H

#include "position.h"
#include "move.h"

namespace chess {

/**
 * \brief An entry from a Polyglot opening book.
 */
class PolyglotOpeningBookEntry {
public:
    PolyglotOpeningBookEntry(const Position& key, const Move& move, uint16_t weight, uint32_t learn);
    PolyglotOpeningBookEntry(uint64_t key, uint16_t move, uint16_t weight, uint32_t learn);
    PolyglotOpeningBookEntry(const PolyglotOpeningBookEntry& entry);

    uint64_t key() const;
    uint16_t raw_move() const;
    Move move() const;

    uint16_t weight() const;
    void set_weight(uint16_t weight);

    uint32_t learn() const;
    void set_learn(uint32_t learn);

    PolyglotOpeningBookEntry& operator=(const PolyglotOpeningBookEntry &rhs);

private:
    uint64_t m_key;
    uint16_t m_move;
    uint16_t m_weight;
    uint32_t m_learn;
};

} // namespace chess

#endif // LIBCHESS_POLYGLOT_OPENING_BOOK_ENTRY_H
