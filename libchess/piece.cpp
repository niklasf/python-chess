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

    bool Piece::operator==(const Piece& other) const {
        return m_symbol == other.m_symbol;
    }

    bool Piece::operator!=(const Piece& other) const {
        return m_symbol != other.m_symbol;
    }

}
