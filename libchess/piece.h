#ifndef LIBCHESS_PIECE_H
#define LIBCHESS_PIECE_H

namespace chess {

    class Piece {

    public:
        Piece(char symbol);

        char color() const;
        char type() const;
        char symbol() const;

        bool operator==(const Piece& other) const;
        bool operator!=(const Piece& other) const;

    private:
        char m_symbol;
    };

}

#endif
