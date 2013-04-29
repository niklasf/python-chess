#include "pseudo_legal_move_generator.h"

namespace chess {

    PseudoLegalMoveGenerator::PseudoLegalMoveGenerator(const Position& position) : m_position(position) {
        m_index = 0;
    }

    PseudoLegalMoveGenerator PseudoLegalMoveGenerator::__iter__() {
        PseudoLegalMoveGenerator self = *this;
        self.m_index = 0;
        return self;
    }

    void PseudoLegalMoveGenerator::generate_from_square(Square square) {
        // Skip empty square and opposing pieces.
        Piece piece = m_position.get(square);
        if (!piece.is_valid() || piece.color() != m_position.turn()) {
            return;
        }

        // Pawn moves.
        if (piece.type() == 'p') {
            // Single steps forward.
            Square target = Square::from_x88_index(
                square.x88_index() + ((m_position.turn() == 'b') ? 16 : -16));

            if (!m_position.get(target).is_valid()) {
                 if (target.is_backrank()) {
                    // Promotion.
                    m_cache.push(Move(square, target, 'b'));
                    m_cache.push(Move(square, target, 'n'));
                    m_cache.push(Move(square, target, 'r'));
                    m_cache.push(Move(square, target, 'q'));
                } else {
                    m_cache.push(Move(square, target));

                    // Two steps forward.
                    if ((m_position.turn() == 'w' && square.rank() == 1) ||
                        (m_position.turn() == 'b' && square.rank() == 6))
                    {
                        target = Square::from_x88_index(
                            square.x88_index() + ((m_position.turn() == 'b') ? 32 : -32));
                        if (!m_position.get(target).is_valid()) {
                            m_cache.push(Move(square, target));
                         }
                    }
                }
            }

            // Pawn captures.
            const int offsets[] = { 17, 15 };
            for (int i = 0; i < 2; i++) {
                // Ensure the target square is on the board.
                int offset = (m_position.turn() == 'b') ? offsets[i] : - offsets[i];
                int target_index = square.x88_index() + offset;
                if (target_index & 0x88) {
                    continue;
                }
                Square target = Square::from_x88_index(target_index);
                Piece target_piece = m_position.get(target);
                if (target_piece.is_valid() && target_piece.color() != m_position.turn()) {
                    if (target.is_backrank()) {
                        // Promotion.
                        m_cache.push(Move(square, target, 'b'));
                        m_cache.push(Move(square, target, 'n'));
                        m_cache.push(Move(square, target, 'r'));
                        m_cache.push(Move(square, target, 'q'));
                    } else {
                        // Normal capture.
                        m_cache.push(Move(square, target));
                    }
                } else if (target == m_position.get_ep_square()) {
                    // En-passant.
                    m_cache.push(Move(square, target));
                }
            }
        }
    }

    Move PseudoLegalMoveGenerator::next() {
        while (m_index < 64 && m_cache.empty()) {
            generate_from_square(Square(m_index++));
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

    bool PseudoLegalMoveGenerator::__contains__(Move move) {
        // Only need to generate the moves of the source square.
        generate_from_square(move.source());

        // See if the move is among the possible ones.
        while (!m_cache.empty()) {
            Move candidate_move = m_cache.front();
            m_cache.pop();
            if (candidate_move == move) {
                // Found it. Clear the queue.
                while (!m_cache.empty()) {
                    m_cache.pop();
                }
                return true;
            }
        }
        return false;
    }

}
