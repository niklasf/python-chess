#include "piece.h"

namespace chess {

    Piece::Piece(char symbol) {
        m_symbol = symbol;
    }

    char Piece::color() const {
        switch (m_symbol) {
            case 'p':
            case 'n':
            case 'b':
            case 'r':
            case 'q':
            case 'k':
                return 'b';
            default:
                return 'w';
        }
    }

    char Piece::type() const {
        switch (m_symbol) {
            case 'p':
            case 'P':
                return 'p';
            case 'n':
            case 'N':
                return 'n';
            case 'b':
            case 'B':
                return 'b';
            case 'r':
            case 'R':
                return 'r';
            case 'q':
            case 'Q':
                return 'q';
            case 'k':
            case 'K':
                return 'k';
        }
    }

    char Piece::symbol() const {
        return m_symbol;
    }

    std::string Piece::full_color() const {
        if (color() == 'w') {
            return "white";
        } else {
            return "black";
        }
    }

    std::string Piece::full_type() const {
        switch(type()) {
            case 'p':
                return "pawn";
            case 'b':
                return "bishop";
            case 'n':
                return "knight";
            case 'r':
                return "rook";
            case 'k':
                return "king";
            case 'q':
                 return "queen";
        }
    }

    bool Piece::operator==(const Piece& other) const {
        return m_symbol == other.m_symbol;
    }

    bool Piece::operator!=(const Piece& other) const {
        return m_symbol != other.m_symbol;
    }

    std::ostream& operator<<(std::ostream& out, const Piece& piece) {
        out << piece.symbol();
        return out;
    }

}
