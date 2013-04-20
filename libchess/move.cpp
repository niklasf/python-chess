#include "move.h"

#include <boost/format.hpp>

namespace chess {

    Move::Move(Square source, Square target, char promotion) : m_source(source), m_target(target) {
        switch (promotion) {
            case 'r':
            case 'n':
            case 'b':
            case 'q':
                m_promotion = promotion;
                break;
            default:
                throw new std::invalid_argument("promotion");
        }
    }

    Move::Move(Square source, Square target) : m_source(source), m_target(target) {
        m_promotion = 0;
    }

    Move::Move(std::string uci) : m_source(Square(0)), m_target(Square(0)) {
        if (uci.length() == 4 || uci.length() == 5) {
            m_source = Square(uci.substr(0, 2));
            m_target = Square(uci.substr(2, 2));
            if (uci.length() == 5) {
                m_promotion = uci.at(4);
                switch (m_promotion) {
                    case 'r':
                    case 'n':
                    case 'b':
                    case 'q':
                        break;
                    default:
                        throw new std::invalid_argument("uci");
                }
            }
        }
        else {
            throw new std::invalid_argument("uci");
        }
    }

    Square Move::source() const {
        return m_source;
    }

    Square Move::target() const {
        return m_target;
    }

    char Move::promotion() const {
        return m_promotion;
    }

    std::string Move::full_promotion() const {
        switch (m_promotion) {
            case 'r':
                return "rook";
            case 'b':
                return "bishop";
            case 'n':
                return "knight";
            case 'q':
                return "queen";
        }
    }

    std::string Move::uci() const {
        if (m_promotion) {
            return m_source.name() + m_target.name() + m_promotion;
        } else {
            return m_source.name() + m_target.name();
        }
    }

    bool Move::is_promotion() const {
        return m_promotion != 0;
    }

    std::string Move::__repr__() const {
        return boost::str(boost::format("Move.from_uci('%s')") % uci());
    }

    int Move::__hash__() const {
        return m_source.__hash__() + 100 * m_target.__hash__() + 10000 * m_promotion;
    }

    bool Move::operator==(const Move& other) const {
        return m_source == other.m_source && m_target == other.m_target && m_promotion == other.m_promotion;
    }

    bool Move::operator!=(const Move& other) const {
        return m_source != other.m_source || m_target != other.m_target || m_promotion != other.m_promotion;
    }

    Move Move::from_uci(std::string uci) {
        return Move(uci);
    }

    std::ostream& operator<<(std::ostream& out, const Move& move) {
        out << move.uci();
        return out;
    }

}
