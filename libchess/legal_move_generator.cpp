#include "legal_move_generator.h"

namespace chess {

    LegalMoveGenerator::LegalMoveGenerator(const Position& position)
        : m_position(position)
    {
        m_pseudo_legal_moves = new PseudoLegalMoveGenerator(position);
    }

    int LegalMoveGenerator::__len__() {
        m_pseudo_legal_moves->__iter__();

        int counter = 0;
        while (m_pseudo_legal_moves->has_more()) {
            if (would_be_valid_if_pseudo_legal(m_pseudo_legal_moves->next())) {
               counter++;
            }
        }
        return counter;
    }

    bool LegalMoveGenerator::__nonzero__() {
        m_pseudo_legal_moves->__iter__();

        while (m_pseudo_legal_moves->has_more()) {
            if (would_be_valid_if_pseudo_legal(m_pseudo_legal_moves->next())) {
                return true;
            }
        }

        return false;
    }

    LegalMoveGenerator LegalMoveGenerator::__iter__() {
        m_pseudo_legal_moves->__iter__();
        return *this;
    }

    bool LegalMoveGenerator::__contains__(Move move) {
        if (!m_pseudo_legal_moves->__contains__(move)) {
            return false;
        } else {
            return would_be_valid_if_pseudo_legal(move);
        }
    }

    Move LegalMoveGenerator::python_next() {
        while (true) {
            Move move = m_pseudo_legal_moves->python_next();
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
