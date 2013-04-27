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

        // Reset properties.
        m_turn = 'w';
        m_ep_file = 0;
        m_half_moves = 0;
        m_ply = 1;
        m_white_castle_queenside = true;
        m_white_castle_kingside = true;
        m_black_castle_queenside = true;
        m_black_castle_kingside = true;

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


    char Position::turn() const {
        return m_turn;
    }

    void Position::set_turn(char turn) {
        if (turn == 'w' || turn == 'b') {
            m_turn = turn;
        } else {
            throw new std::invalid_argument("turn");
        }
    }

    void Position::toggle_turn() {
        if (m_turn == 'w') {
            m_turn = 'b';
        } else {
            m_turn = 'w';
        }
    }

    char Position::ep_file() const {
        return m_ep_file;
    }

    boost::python::object Position::python_ep_file() const {
        if (m_ep_file) {
            return boost::python::object(m_ep_file);
        } else {
            return boost::python::object();
        }
    }

    void Position::set_ep_file(char ep_file) {
        switch (ep_file) {
            case 'a':
            case 'b':
            case 'c':
            case 'd':
            case 'e':
            case 'f':
            case 'g':
            case 'h':
                m_ep_file = ep_file;
                break;
            case '-':
            case 0:
                m_ep_file = 0;
            default:
                throw new std::invalid_argument("ep_file");
        }
    }

    void Position::python_set_ep_file(boost::python::object ep_file) {
        if (ep_file.ptr() == Py_None) {
            m_ep_file = 0;
        } else {
            set_ep_file(boost::python::extract<char>(ep_file));
        }
    }

    Square Position::get_ep_square() const {
        if (m_ep_file) {
            int rank = (m_turn == 'b') ? 2 : 5;
            int pawn_rank = (m_turn == 'b') ? 3 : 4;
            int file = m_ep_file - 'a';

            // Ensure the square is empty.
            Square square(rank, file);
            if (get(square).is_valid()) {
                return Square();
            }

            // Ensure a pawn is above the square.
            Square pawn_square(pawn_rank, file);
            Piece pawn_square_piece = get(pawn_square);
            if (!pawn_square_piece.is_valid()) {
                return Square();
            }
            if (pawn_square_piece.type() != 'p') {
                return Square();
            }

            return square;
        } else {
            return Square();
        }
    }

    boost::python::object Position::python_get_ep_square() const {
        Square ep_square = get_ep_square();
        if (ep_square.is_valid()) {
            return boost::python::object(ep_square);
        } else {
            return boost::python::object();
        }
    }

    int Position::half_moves() const {
        return m_half_moves;
    }

    void Position::set_half_moves(int half_moves) {
        if (half_moves < 0) {
            throw new std::invalid_argument("half_moves");
        } else {
            m_half_moves = half_moves;
        }
    }

    int Position::ply() const {
        return m_ply;
    }

    void Position::set_ply(int ply) {
        if (ply < 1) {
            throw new std::invalid_argument("ply");
        } else {
            m_ply = ply;
        }
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
