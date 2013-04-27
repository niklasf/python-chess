#ifndef LIBCHESS_PSEUDO_LEGAL_MOVE_GENERATOR_H
#define LIBCHESS_PSEUDO_LEGAL_MOVE_GENERATOR_H

#include "position.h"
#include "move.h"

namespace chess {

    class PseudoLegalMoveGenerator {
    public:
         PseudoLegalMoveGenerator(Position& position);

         PseudoLegalMoveGenerator __iter__();
         Move next();

    private:
         Position m_position;
         int m_index;
         int m_promotion;
    };

}

#endif
