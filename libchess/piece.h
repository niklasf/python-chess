#ifndef LIBCHESS_PIECE_H
#define LIBCHESS_PIECE_H

#include <iostream>

namespace chess {

    class Piece {

    public:
        Piece(char symbol);

        char color() const;
        char type() const;
        char symbol() const;

        std::string full_color() const;

        bool operator==(const Piece& other) const;
        bool operator!=(const Piece& other) const;

    private:
        char m_symbol;
    };

    std::ostream& operator<<(std::ostream& out, const Piece& piece);
}

#endif
