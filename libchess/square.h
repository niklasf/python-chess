#ifndef LIBCHESS_SQUARE_H
#define LIBCHESS_SQUARE_H

#include <iostream>

namespace chess {

    class Square {

    public:
        Square(int index);
        Square(const std::string& name);
        Square(int rank, int file);

        int rank() const;
        int file() const;
        int index() const;
        std::string name() const;
        char file_name() const;

        bool is_dark() const;
        bool is_light() const;
        bool is_backrank() const;
        bool is_seventh() const;

        std::string __repr__() const;
        int __hash__() const;

        operator int() const;
        bool operator==(const Square& other) const;
        bool operator!=(const Square& other) const;

        static Square from_rank_and_file(int rank, int file);
        static Square from_index(int index);

    private:
        int m_index;

    };

    std::ostream& operator<<(std::ostream& out, const Square& square);

}

#endif
