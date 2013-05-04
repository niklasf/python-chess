#include "polyglot_opening_book_entry.h"

namespace chess {

    PolyglotOpeningBookEntry::PolyglotOpeningBookEntry(Position key, Move move, uint16_t weight, uint32_t learn) {
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

        m_weight = weight;
        m_learn = learn;
    }

    PolyglotOpeningBookEntry::PolyglotOpeningBookEntry(uint64_t key, uint16_t move, uint16_t weight, uint32_t learn) {
        m_key = key;
        m_move = move;
        m_weight = weight;
        m_learn = learn;
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

        // Some moves are reserved for castling.
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

    uint32_t PolyglotOpeningBookEntry::learn() const {
        return m_learn;
    }

}
