#ifndef LIBCHESS_PIECE_H
#define LIBCHESS_PIECE_H

#include <iostream>

namespace chess {

    /**
     * \brief An immutable chess piece.
     */
    class Piece {

    public:
        Piece();
        Piece(char symbol);

        char color() const;
        char type() const;
        char symbol() const;
        std::string full_color() const;
        std::string full_type() const;

        std::string __repr__() const;
        int __hash__() const;

        bool is_valid() const;

        bool operator==(const Piece& other) const;
        bool operator!=(const Piece& other) const;

        static Piece from_color_and_type(char color, char type);

    private:
        char m_symbol;
    };

    std::ostream& operator<<(std::ostream& out, const Piece& piece);
}

#endif
