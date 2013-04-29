#include "pseudo_legal_move_generator.h"

namespace chess {

    PseudoLegalMoveGenerator::PseudoLegalMoveGenerator(const Position& position) : m_position(position) {
        m_index = 0;
    }

    PseudoLegalMoveGenerator PseudoLegalMoveGenerator::__iter__() {
        return *this;
    }

    Move PseudoLegalMoveGenerator::next() {
        if (!m_cache.empty()) {
            Move move = m_cache.front();
            m_cache.pop();
            return move;
        }

        while (m_index < 64) {
            // Skip empty square and opposing pieces.
            Square square(m_index++);
            Piece piece = m_position.get(square);
            if (!piece.is_valid() || piece.color() != m_position.turn()) {
                continue;
            }

            // Pawn moves.
            if (piece.type() == 'p') {
                Square target = Square::from_x88_index(
                    square.x88_index() + ((m_position.turn() == 'b') ? 16 : -16));

                if (!m_position.get(target).is_valid()) {
                    if (target.is_backrank()) {
                        // Promotion.
                        m_cache.push(Move(square, target, 'b'));
                        m_cache.push(Move(square, target, 'n'));
                        m_cache.push(Move(square, target, 'r'));
                        m_cache.push(Move(square, target, 'q'));
                        break;
                    } else {
                        m_cache.push(Move(square, target));
                        break;
                    }
                }
            }
        }

        if (m_cache.empty()) {
            PyErr_SetNone(PyExc_StopIteration);
            throw boost::python::error_already_set();
        } else {
            Move move = m_cache.front();
            m_cache.pop();
            return move;
        }
    }

}
