#ifndef LIBCHESS_POSITION_H
#define LIBCHESS_POSITION_H

#include <boost/python.hpp>
#include <stdint.h>

#include "piece.h"
#include "square.h"
#include "attacker_generator.h"
#include "pseudo_legal_move_generator.h"
#include "move_info.h"

namespace chess {

    class AttackerGenerator;
    class LegalMoveGenerator;
    class PseudoLegalMoveGenerator;

    class Position {
    public:

        Position();
        Position(std::string fen);
        Position(const Position& other);

        void clear_board();
        void reset();

        Piece get(Square square) const;
        void set(Square square, Piece piece);
        boost::python::object __getitem__(boost::python::object square_key) const;
        void __setitem__(boost::python::object square_key, boost::python::object piece);
        void __delitem__(boost::python::object square_key);

        char turn() const;
        void set_turn(char turn);
        void toggle_turn();

        char ep_file() const;
        void set_ep_file(char ep_file);
        boost::python::object python_ep_file() const;
        void python_set_ep_file(boost::python::object ep_file);
        Square get_ep_square() const;
        boost::python::object python_get_ep_square() const;

        int half_moves() const;
        void set_half_moves(int half_moves);

        int ply() const;
        void set_ply(int ply);

        std::string fen() const;
        void set_fen(std::string fen);

        const PseudoLegalMoveGenerator *get_pseudo_legal_moves() const;
        const LegalMoveGenerator *get_legal_moves() const;
        const AttackerGenerator *get_attackers(char color, Square target) const;

        Square get_king(char color) const;
        boost::python::object python_get_king(char color) const;

        bool is_king_attacked(char color) const;
        bool is_check() const;
        bool is_checkmate() const;
        bool is_stalemate() const;

        MoveInfo make_unvalidated_move_fast(Move move);
        MoveInfo make_unvalidated_move(Move move);

        std::string __repr__() const;
        uint64_t __hash__() const;

        bool operator==(const Position& other) const;
        bool operator!=(const Position& other) const;

    protected:
        Piece m_board[128];
        char m_turn;
        char m_ep_file;
        int m_half_moves;
        int m_ply;
        bool m_white_castle_queenside;
        bool m_white_castle_kingside;
        bool m_black_castle_queenside;
        bool m_black_castle_kingside;

    private:
        int x88_index_from_square_key(boost::python::object square_key) const;

    };

    std::ostream& operator<<(std::ostream& out, const Position& position);

    const std::string START_FEN("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");

    extern const uint64_t POLYGLOT_RANDOM_ARRAY[];

}

#endif
