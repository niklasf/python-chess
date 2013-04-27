#ifndef LIBCHESS_POSITION_H
#define LIBCHESS_POSITION_H

#include <boost/python.hpp>

#include "piece.h"
#include "square.h"

namespace chess {

    class Position {
    public:

        Position();

        Piece get(Square square) const;
        void set(Square square, Piece piece);

        boost::python::object __getitem__(boost::python::object square_key) const;
        void __setitem__(boost::python::object square_key, boost::python::object piece);
        void __delitem__(boost::python::object square_key);

    private:
        Piece m_board[128];

        int x88_index_from_square_key(boost::python::object square_key) const;

    };

}

#endif
