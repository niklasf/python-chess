#include "square.h"

#include <boost/format.hpp>

namespace chess {

    Square::Square(int index) {
        if (index < 0 || index >= 64) {
            throw new std::invalid_argument("index");
        }
        m_index = index;
    }

    Square::Square(const std::string& name) {
        if (name.length() != 2) {
            throw new std::invalid_argument("name");
        }

        int file = name.at(0) - 'a';
        int rank = name.at(1) - '1';
        if (file < 0 || file >= 8 || rank < 0 || rank >= 8) {
            throw new std::invalid_argument("name");
        }

        m_index = rank * 8 + file;
    }

    Square::Square(int rank, int file) {
        if (file < 0 || file >= 8) {
            throw new std::invalid_argument("file");
        }
        if (rank < 0 || rank >= 8) {
            throw new std::invalid_argument("rank");
        }

        m_index = rank * 8 + file;
    }

    int Square::rank() const {
        return m_index / 8;
    }

    int Square::file() const {
        return m_index % 8;
    }

    int Square::index() const {
        return m_index;
    }

    std::string Square::name() const {
        std::string name;
        name += (file() + 'a');
        name += (rank() + '1');
        return name;
    }

    char Square::file_name() const {
        return file() + 'a';
    }

    bool Square::is_dark() const {
        return m_index % 2 == 0;
    }

    bool Square::is_light() const {
        return m_index % 2 == 1;
    }

    bool Square::is_backrank() const {
        return rank() == 0 || rank() == 7;
    }

    bool Square::is_seventh() const {
        return rank() == 1 || rank() == 6;
    }

    std::string Square::__repr__() const {
        return boost::str(boost::format("Square('%1%')") % name());
    }

    int Square::__hash__() const {
        return m_index;
    }

    Square::operator int() const {
        return m_index;
    }

    bool Square::operator==(const Square& other) const {
        return m_index == other.m_index;
    }

    bool Square::operator!=(const Square& other) const {
        return m_index != other.m_index;
    }

    Square Square::from_rank_and_file(int rank, int file) {
        return Square(rank, file);
    }

    Square Square::from_index(int index) {
        return Square(index);
    }

    std::ostream& operator<<(std::ostream& out, const Square& square) {
        out << square.name();
        return out;
    }

}
