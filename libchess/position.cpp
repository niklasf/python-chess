#include "position.h"

namespace chess {

    Position::Position() {
        reset();
    }

    void Position::clear_board() {
        Piece no_piece;

        for (int i = 0; i < 128; i++) {
            m_board[i] = no_piece;
        }
    }

    void Position::reset() {
        clear_board();

        // Setup the white pieces.
        m_board[112] = Piece('R');
        m_board[113] = Piece('N');
        m_board[114] = Piece('B');
        m_board[115] = Piece('Q');
        m_board[116] = Piece('K');
        m_board[117] = Piece('B');
        m_board[118] = Piece('N');
        m_board[119] = Piece('R');

        // Setup the white pawns.
        for (int x88_index = 96; x88_index <= 103; x88_index++) {
            m_board[x88_index] = Piece('P');
        }

        // Setup the black pieces.
        m_board[0] = Piece('r');
        m_board[1] = Piece('n');
        m_board[2] = Piece('b');
        m_board[3] = Piece('q');
        m_board[4] = Piece('k');
        m_board[5] = Piece('b');
        m_board[6] = Piece('n');
        m_board[7] = Piece('r');

        // Setup the black pawns.
        for (int x88_index = 16; x88_index <= 23; x88_index++) {
            m_board[x88_index] = Piece('p');
        }
    }

    Piece Position::get(Square square) const {
        return m_board[square.x88_index()];
    }

    void Position::set(Square square, Piece piece) {
        m_board[square.x88_index()] = piece;
    }

    boost::python::object Position::__getitem__(boost::python::object square_key) const {
        int x88_index = x88_index_from_square_key(square_key);

        if (m_board[x88_index].is_valid()) {
            return boost::python::object(m_board[x88_index]);
        } else {
            return boost::python::object();
        }
    }

    void Position::__setitem__(boost::python::object square_key, boost::python::object piece) {
        int x88_index = x88_index_from_square_key(square_key);

        if (piece.ptr() == Py_None) {
            m_board[x88_index] = Piece();
        } else {
            Piece& p = boost::python::extract<Piece&>(piece);
            m_board[x88_index] = p;
        }
    }

    void Position::__delitem__(boost::python::object square_key) {
        m_board[x88_index_from_square_key(square_key)] = Piece();
    }

    int Position::x88_index_from_square_key(boost::python::object square_key) const {
        boost::python::extract<Square&> extract_square(square_key);
        if (extract_square.check()) {
            Square& square = extract_square();
            return square.x88_index();
        }
        else {
            std::string square_name = boost::python::extract<std::string>(square_key);
            Square square = Square(square_name);
            return square.x88_index();
        }
    }

}
