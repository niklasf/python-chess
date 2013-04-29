#ifndef LIBCHESS_MOVE_INFO_H
#define LIBCHESS_MOVE_INFO_H

#include <boost/python.hpp>

#include "piece.h"
#include "move.h"

namespace chess {

    class MoveInfo {
        public:
            MoveInfo(Move move, Piece piece) : m_move(move), m_piece(piece) { }

            Move move() const;
            void set_move(Move move);

            Piece piece() const;
            void set_piece(Piece piece);

            Piece captured() const;
            boost::python::object python_captured() const;
            void set_captured(Piece captured);
            void python_set_captured(boost::python::object captured);

            std::string san() const;
            void set_san(std::string san);

            bool is_enpassant() const;
            void set_is_enpassant(bool is_enpassant);

            bool is_kingside_castle() const;
            void set_is_kingside_castle(bool is_kingside_castle);

            bool is_queenside_castle() const;
            void set_is_queenside_castle(bool is_queenside_castle);

            bool is_castle() const;

            bool is_check() const;
            void set_is_check(bool is_check);

            bool is_checkmate() const;
            void set_is_checkmate(bool is_checkmate);

        private:
            Move m_move;
            Piece m_piece;
            Piece m_captured;
            std::string m_san;
            bool m_is_enpassant;
            bool m_is_kingside_castle;
            bool m_is_queenside_castle;
            bool m_is_check;
            bool m_is_checkmate;
    };
}

#endif
