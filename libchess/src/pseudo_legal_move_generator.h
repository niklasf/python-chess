#ifndef LIBCHESS_PSEUDO_LEGAL_MOVE_GENERATOR_H
#define LIBCHESS_PSEUDO_LEGAL_MOVE_GENERATOR_H

#include <boost/shared_ptr.hpp>
#include <queue>

#include "position.h"
#include "move.h"

namespace chess {

class Position;

/**
 * \brief Enumerates pseudo legal moves in a given position.
 */
class PseudoLegalMoveGenerator : boost::noncopyable {
public:
     PseudoLegalMoveGenerator(const Position& position);
     ~PseudoLegalMoveGenerator();

     int __len__();
     bool __nonzero__();
     PseudoLegalMoveGenerator& __iter__();
     bool __contains__(const Move& move);

     bool has_more();
     Move next();
     Move python_next();

protected:
     void generate_from_square(const Square& square);
     std::queue<Move> m_cache;

private:
     Position* m_position;
     int m_index;
};

} // namespace chess

#endif // LIBCHESS_PSEUDO_LEGAL_MOVE_GENERATOR_H
