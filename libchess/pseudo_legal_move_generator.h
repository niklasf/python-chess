#ifndef LIBCHESS_PSEUDO_LEGAL_MOVE_GENERATOR_H
#define LIBCHESS_PSEUDO_LEGAL_MOVE_GENERATOR_H

#include <boost/shared_ptr.hpp>
#include <queue>

#include "position.h"
#include "move.h"

namespace chess {

    class Position;

    class PseudoLegalMoveGenerator {
    public:
         PseudoLegalMoveGenerator(const Position& position);

         int __len__();
         bool __nonzero__();
         PseudoLegalMoveGenerator __iter__();
         bool __contains__(Move move);

         bool has_more();
         Move next();
         Move python_next();

    protected:
         void generate_from_square(Square square);
         std::queue<Move> m_cache;

    private:
         const boost::shared_ptr<Position> m_position;
         int m_index;
    };

}

#endif
