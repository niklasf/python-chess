#include "pseudo_legal_move_generator.h"

namespace chess {

    PseudoLegalMoveGenerator::PseudoLegalMoveGenerator(const Position& position) : m_position(new Position(position)) {
        m_index = 0;
    }

    PseudoLegalMoveGenerator PseudoLegalMoveGenerator::__iter__() {
        // Rewind.
        m_index = 0;
        while (!m_cache.empty()) {
            m_cache.pop();
        }
        return *this;
    }

    void PseudoLegalMoveGenerator::generate_from_square(Square square) {
        // Skip empty square and opposing pieces.
        Piece piece = m_position->get(square);
        if (!piece.is_valid() || piece.color() != m_position->turn()) {
            return;
        }

        if (piece.type() == 'p') {
            // Pawn moves: Single steps forward.
            Square target = Square::from_x88_index(
                square.x88_index() + ((m_position->turn() == 'b') ? 16 : -16));

            if (!m_position->get(target).is_valid()) {
                 if (target.is_backrank()) {
                    // Promotion.
                    m_cache.push(Move(square, target, 'b'));
                    m_cache.push(Move(square, target, 'n'));
                    m_cache.push(Move(square, target, 'r'));
                    m_cache.push(Move(square, target, 'q'));
                } else {
                    m_cache.push(Move(square, target));

                    // Two steps forward.
                    if ((m_position->turn() == 'w' && square.rank() == 1) ||
                        (m_position->turn() == 'b' && square.rank() == 6))
                    {
                        target = Square::from_x88_index(
                            square.x88_index() + ((m_position->turn() == 'b') ? 32 : -32));
                        if (!m_position->get(target).is_valid()) {
                            m_cache.push(Move(square, target));
                         }
                    }
                }
            }

            // Pawn captures.
            const int offsets[] = { 17, 15 };
            for (int i = 0; i < 2; i++) {
                // Ensure the target square is on the board.
                int offset = (m_position->turn() == 'b') ? offsets[i] : - offsets[i];
                int target_index = square.x88_index() + offset;
                if (target_index & 0x88) {
                    continue;
                }
                Square target = Square::from_x88_index(target_index);
                Piece target_piece = m_position->get(target);
                if (target_piece.is_valid() && target_piece.color() != m_position->turn()) {
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
                } else if (target == m_position->get_ep_square()) {
                    // En-passant.
                    m_cache.push(Move(square, target));
                }
            }
        } else {
            // Other pieces.
            const int offsets[5][9] = {
                { -18, -33, -31, -14, 18, 33, 31, 14, 0 }, // Knight
                { -17, -15, 17, 15, 0 }, // Bishop
                { -16, 1, 16, -1, 0 }, // Rook
                { -17, -16, -15, 1, 17, 16, 15, -1, 0 }, // Queen
                { -17, -16, -15, 1, 17, 16, 15, -1, 0 } }; // King

            // Get the index of the piece in the offset table.
            int piece_index;
            switch (piece.type()) {
                case 'n':
                    piece_index = 0;
                    break;
                case 'b':
                    piece_index = 1;
                    break;
                case 'r':
                    piece_index = 2;
                    break;
                case 'q':
                    piece_index = 3;
                    break;
                case 'k':
                    piece_index = 4;
                    break;
            }

            // Generate the moves.
            for (int i = 0; offsets[piece_index][i] != 0; i++) {
                int target_index = square.x88_index();
                while (true) {
                    target_index += offsets[piece_index][i];
                    if (target_index & 0x88) {
                        break;
                    }

                    Square target = Square::from_x88_index(target_index);
                    Piece target_piece = m_position->get(target);
                    if (target_piece.is_valid()) {
                        // Captures.
                        if (target_piece.color() != m_position->turn()) {
                            m_cache.push(Move(square, target));
                        }
                        break;
                    } else {
                        m_cache.push(Move(square, target));
                    }

                    // Knight and king do not go multiple times in their
                    // direction.
                    if (piece.type() == 'k' || piece.type() == 'n') {
                        break;
                    }
                }
            }

        }

        if (piece.type() == 'k') {
            int backrank = m_position->turn() == 'b' ? 7 : 0;

            // King-side castling.
            if (m_position->has_kingside_castling_right(m_position->turn())) {
                Square bishop_square(backrank, 5);
                Square knight_square(backrank, 6);
                if (!m_position->get(bishop_square).is_valid() && !m_position->get(knight_square).is_valid()) {
                    AttackerGenerator attacks(*m_position, opposite_color(m_position->turn()), bishop_square);
                    if (!attacks.__nonzero__()) {
                        m_cache.push(Move(Square(backrank, 4), knight_square));
                    }
                }
            }

            // Queen-side castling.
            if (m_position->has_queenside_castling_right(m_position->turn())) {
                Square knight_square(backrank, 1);
                Square bishop_square(backrank, 2);
                Square queen_square(backrank, 3);
                if (!m_position->get(knight_square).is_valid() &&
                    !m_position->get(bishop_square).is_valid() &&
                    !m_position->get(queen_square).is_valid())
                {
                    AttackerGenerator attacks(*m_position, opposite_color(m_position>turn()), queen_square);
                    if (!attacks.__nonzero__()) {
                        m_cache.push(Move(Square(backrank, 4), bishop_square));
                    }
                }
            }
        }
    }

    Move PseudoLegalMoveGenerator::next() {
        if (has_more()) {
            Move move = m_cache.front();
            m_cache.pop();
            return move;
        } else {
            throw std::logic_error("Called next() altough there are no more pseudo legal moves.");
        }
    }

    Move PseudoLegalMoveGenerator::python_next() {
        if (has_more()) {
            return next();
        } else {
            PyErr_SetNone(PyExc_StopIteration);
            throw boost::python::error_already_set();
        }
    }

    bool PseudoLegalMoveGenerator::has_more() {
        while(m_index < 64 && m_cache.empty()) {
            generate_from_square(Square(m_index++));
        }

        return !m_cache.empty();
    }

    bool PseudoLegalMoveGenerator::__contains__(Move move) {
        // Only need to generate the moves of the source square.
        generate_from_square(move.source());

        // See if the move is among the possible ones.
        while (!m_cache.empty()) {
            Move candidate_move = m_cache.front();
            m_cache.pop();
            if (candidate_move == move) {
                return true;
            }
        }
        return false;
    }

    bool PseudoLegalMoveGenerator::__nonzero__() {
        // Generate moves until on is found.
        int index = 0;
        while (index < 64) {
            generate_from_square(Square(index++));
            if (!m_cache.empty()) {
                 return true;
            }
        }
        return false;
    }

    int PseudoLegalMoveGenerator::__len__() {
        // Clear the cache.
        while (!m_cache.empty()) {
            m_cache.pop();
        }

        // Generate all moves.
        int index = 0;
        while (index < 64) {
            generate_from_square(Square(index++));
        }

        return m_cache.size();
    }

}
