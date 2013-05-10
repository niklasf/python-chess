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
    Move(const Square& source, const Square& target, char promotion);
    Move(const Square& source, const Square& target);
    Move(const std::string& uci);
    Move(const Move& move);

    Square source() const;
    Square target() const;
    char promotion() const;
    std::string full_promotion() const;
    std::string uci() const;

    bool is_promotion() const;

    std::string __repr__() const;
    int __hash__() const;

    Move& operator=(const Move& rhs);
    bool operator==(const Move& rhs) const;
    bool operator!=(const Move& rhs) const;

    static Move from_uci(const std::string& uci);

private:
    Square m_source;
    Square m_target;
    char m_promotion;
};

std::ostream& operator<<(std::ostream &out, const Move& move);

} // namespace chess

#endif // LIBCHESS_MOVE_H
