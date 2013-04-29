#include "legal_move_generator.h"

namespace chess {

    LegalMoveGenerator::LegalMoveGenerator(const Position& position)
        : m_position(position)
    {
        m_pseudo_legal_moves = new PseudoLegalMoveGenerator(position);
    }

    int LegalMoveGenerator::__len__() {
        int counter = 0;
        // TODO: Implement and use a better C++ side iterating API.
        int pseudo_legal_len = m_pseudo_legal_moves->__len__();
        for (int i = 0; i < pseudo_legal_len; i++) {
            if (would_be_valid_if_pseudo_legal(m_pseudo_legal_moves->next())) {
               counter++;
            }
        }
        return counter;
    }

    bool LegalMoveGenerator::__nonzero__() {
        // TODO: Implement.
        return false;
    }

    LegalMoveGenerator LegalMoveGenerator::__iter__() {
        LegalMoveGenerator self = *this;
        m_pseudo_legal_moves->__iter__();
        return self;
    }

    bool LegalMoveGenerator::__contains__(Move move) {
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
                return move;
            }
        }
    }

    bool LegalMoveGenerator::would_be_valid_if_pseudo_legal(const Move& move) const {
        Position position = m_position;
        position.make_unvalidated_move_fast(move);
        return !position.is_king_attacked(m_position.turn());
    }

    LegalMoveGenerator::~LegalMoveGenerator() {
        delete m_pseudo_legal_moves;
    }
}
