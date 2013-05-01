#ifndef LIBCHESS_MOVE_H
#define LIBCHESS_MOVE_H

#include "square.h"

#include <iostream>

namespace chess {

    /**
     * \brief An immutable move.
     */
    class Move {

    public:
        Move(Square source, Square target, char promotion);
        Move(Square source, Square target);
        Move(std::string uci);

        Square source() const;
        Square target() const;
        char promotion() const;
        std::string full_promotion() const;
        std::string uci() const;

        bool is_promotion() const;

        std::string __repr__() const;
        int __hash__() const;

        bool operator==(const Move& other) const;
        bool operator!=(const Move& other) const;

        static Move from_uci(std::string uci);

    private:
        Square m_source;
        Square m_target;
        char m_promotion;
    };

    std::ostream& operator<<(std::ostream &out, const Move& move);

}

#endif
