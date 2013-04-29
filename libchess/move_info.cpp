#include "move_info.h"

namespace chess {

    MoveInfo::MoveInfo(Move move, Piece piece, std::string san) : m_move(move), m_piece(piece), m_san(san) {
        if (!piece.is_valid()) {
            throw new std::invalid_argument("piece");
        }

        m_captured = Piece();
        m_is_enpassant = false;
        m_is_kingside_castle = false;
        m_is_queenside_castle = false;
        m_is_check = false;
        m_is_checkmate = false;
    }

    Move MoveInfo::move() const {
        return m_move;
    }

    void MoveInfo::set_move(Move move) {
        m_move = move;
    }

    Piece MoveInfo::piece() const {
        return m_piece;
    }

    void MoveInfo::set_piece(Piece piece) {
         m_piece = piece;
    }

    Piece MoveInfo::captured() const {
        return m_captured;
    }

    boost::python::object MoveInfo::python_captured() const {
        if (m_captured.is_valid()) {
            return boost::python::object(m_captured);
        } else {
            return boost::python::object();
        }
    }

    void MoveInfo::set_captured(Piece captured) {
        m_captured = captured;
    }

    void MoveInfo::python_set_captured(boost::python::object captured) {
        if (captured.ptr() == Py_None) {
            m_captured = Piece();
        } else {
            m_captured = boost::python::extract<Piece>(captured);
        }
    }

    std::string MoveInfo::san() const {
        return m_san;
    }

    void MoveInfo::set_san(std::string san) {
        m_san = san;
    }

    bool MoveInfo::is_enpassant() const {
        return m_is_enpassant;
    }

    void MoveInfo::set_is_enpassant(bool is_enpassant) {
        m_is_enpassant = is_enpassant;
    }

    bool MoveInfo::is_kingside_castle() const {
        return m_is_kingside_castle;
    }

    void MoveInfo::set_is_kingside_castle(bool is_kingside_castle) {
        m_is_kingside_castle = is_kingside_castle;
    }

    bool MoveInfo::is_queenside_castle() const {
        return m_is_queenside_castle;
    }

    void MoveInfo::set_is_queenside_castle(bool is_queenside_castle) {
        m_is_queenside_castle = is_queenside_castle;
    }

    bool MoveInfo::is_castle() const {
        return m_is_kingside_castle || m_is_kingside_castle;
    }

    bool MoveInfo::is_check() const {
        return m_is_check;
    }

    void MoveInfo::set_is_check(bool is_check) {
        m_is_check = is_check;
    }

    bool MoveInfo::is_checkmate() const {
        return m_is_checkmate;
    }

    void MoveInfo::set_is_checkmate(bool is_checkmate) {
        m_is_checkmate = is_checkmate;
    }

}
