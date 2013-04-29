#ifndef LIBCHESS_LEGAL_MOVE_GENERATOR_H
#define LIBCHESS_LEGAL_MOVE_GENERATOR_H

#include "position.h"
#include "pseudo_legal_move_generator.h"

namespace chess {

    class Position;

    class LegalMoveGenerator {
    public:
        LegalMoveGenerator(const Position& position);
        ~LegalMoveGenerator();

        int __len__();
        bool __nonzero__();
        LegalMoveGenerator __iter__();
        bool __contains__(Move move);

        Move python_next();

    private:
        bool would_be_valid_if_pseudo_legal(const Move& move) const;

        const Position& m_position;
        PseudoLegalMoveGenerator *m_pseudo_legal_moves;
    };

}

#endif
