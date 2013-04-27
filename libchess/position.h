#ifndef LIBCHESS_POSITION_H
#define LIBCHESS_POSITION_H

#include <boost/python.hpp>

#include "piece.h"
#include "square.h"

namespace chess {

    class Position {
    public:

        Position();

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

}

#endif
