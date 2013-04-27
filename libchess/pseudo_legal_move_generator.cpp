#include "pseudo_legal_move_generator.h"

namespace chess {

    PseudoLegalMoveGenerator::PseudoLegalMoveGenerator(Position& position) : m_position(position) {
        m_index = 0;
        m_promotion = 0;
    }

    PseudoLegalMoveGenerator PseudoLegalMoveGenerator::__iter__() {
        return *this;
    }

    Move PseudoLegalMoveGenerator::next() {
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
                        switch (m_promotion) {
                            case 0:
                                m_promotion++;
                                m_index--;
                                return Move(square, target, 'b');
                            case 1:
                                m_promotion++;
                                m_index--;
                                return Move(square, target, 'n');
                            case 2:
                                m_promotion++;
                                m_index--;
                                return Move(square, target, 'r');
                            case 3:
                                m_promotion = 0;
                                return Move(square, target, 'q');
                        }
                    } else {
                        return Move(square, target);
                    }
                }
            }
        }

        PyErr_SetNone(PyExc_StopIteration);
        throw boost::python::error_already_set();
    }

}
