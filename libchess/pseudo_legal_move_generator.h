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

    private:
         const Position& m_position;
         int m_index;
         std::queue<Move> m_cache;
    };

}

#endif
