#include "piece.h"

#include <boost/format.hpp>
#include <stdlib.h>

namespace chess {

    Piece::Piece(char symbol) {
        switch (tolower(symbol)) {
            case 'p':
            case 'n':
            case 'b':
            case 'r':
            case 'q':
            case 'k':
                m_symbol = symbol;
                break;
            default:
                throw new std::invalid_argument("symbol");
        }
    }

    char Piece::color() const {
        if (m_symbol == toupper(m_symbol)) {
            return 'w';
        } else {
            return 'b';
        }
    }

    char Piece::type() const {
        return tolower(m_symbol);
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

    std::string Piece::__repr__() const {
        return str(boost::format("Piece('%1%')") % m_symbol);
    }

    int Piece::__hash__() const {
        return m_symbol;
    }

    bool Piece::operator==(const Piece& other) const {
        return m_symbol == other.m_symbol;
    }

    bool Piece::operator!=(const Piece& other) const {
        return m_symbol != other.m_symbol;
    }

    Piece Piece::from_color_and_type(char color, char type) {
        if (color == 'w') {
            return Piece(toupper(type));
        } else if (color == 'b') {
            return Piece(tolower(type));
        } else {
            throw new std::invalid_argument("color");
        }
    }

    std::ostream& operator<<(std::ostream& out, const Piece& piece) {
        out << piece.symbol();
        return out;
    }

}
