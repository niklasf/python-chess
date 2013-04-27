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

        boost::python::object __getitem__(Square square) const;
        void __setitem__(Square square, boost::python::object piece);

    private:
        Piece m_board[128];

    };

}

#endif
