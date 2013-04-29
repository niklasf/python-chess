#ifndef LIBCHESS_PSEUDO_LEGAL_MOVE_GENERATOR_H
#define LIBCHESS_PSEUDO_LEGAL_MOVE_GENERATOR_H

#include <queue>

#include "position.h"
#include "move.h"

namespace chess {

    class Position;

    class PseudoLegalMoveGenerator {
    public:
         PseudoLegalMoveGenerator(const Position& position);

         PseudoLegalMoveGenerator __iter__();
         Move next();
         bool __contains__(Move move);

    protected:
         void generate_from_square(Square square);
         std::queue<Move> m_cache;

    private:
         const Position& m_position;
         int m_index;
    };

}

#endif
