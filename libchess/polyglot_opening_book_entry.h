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
