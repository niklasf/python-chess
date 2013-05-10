// This file is part of the python-chess library.
// Copyright (C) 2013 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have recieved a copy of the GNU General Public License
// along with this program. If not, see <http://gnu.org/licenses/>.

#ifndef LIBCHESS_SQUARE_H
#define LIBCHESS_SQUARE_H

#include <iostream>

namespace chess {

/**
 * \brief The immutable coordinates of a square on the board.
 */
class Square {
public:
    Square();
    Square(int index);
    Square(const std::string& name);
    Square(const Square& square);
    Square(int rank, int file);

    int rank() const;
    int file() const;
    int index() const;
    int x88_index() const;
    std::string name() const;
    char file_name() const;
    char rank_name() const;

    bool is_dark() const;
    bool is_light() const;
    bool is_backrank() const;
    bool is_seventh() const;

    bool is_valid() const;

    std::string __repr__() const;
    int __hash__() const;

    Square& operator=(const Square& rhs);
    bool operator==(const Square& rhs) const;
    bool operator!=(const Square& rhs) const;

    static Square from_rank_and_file(int rank, int file);
    static Square from_index(int index);
    static Square from_x88_index(int x88_index);

private:
    int m_index;
};

std::ostream& operator<<(std::ostream& out, const Square& square);

} // namespace chess

#endif // LIBCHESS_SQUARE_H
