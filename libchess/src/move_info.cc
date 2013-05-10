#include "move_info.h"

namespace chess {

MoveInfo::MoveInfo(const Move& move, const Piece& piece) : m_move(move), m_piece(piece), m_san("") {
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

MoveInfo::MoveInfo(const MoveInfo& move_info) : m_move(move_info.m_move), m_piece(move_info.m_piece), m_captured(move_info.m_captured), m_san(move_info.m_san) {
    m_is_enpassant = move_info.m_is_enpassant;
    m_is_kingside_castle = move_info.m_is_kingside_castle;
    m_is_queenside_castle = move_info.m_is_queenside_castle;
    m_is_check = move_info.m_is_check;
    m_is_checkmate = move_info.m_is_checkmate;
}

Move MoveInfo::move() const {
    return m_move;
}

void MoveInfo::set_move(const Move& move) {
    m_move = move;
}

Piece MoveInfo::piece() const {
    return m_piece;
}

void MoveInfo::set_piece(const Piece& piece) {
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

void MoveInfo::set_captured(const Piece& captured) {
    m_captured = captured;
}

void MoveInfo::python_set_captured(const boost::python::object& captured) {
    if (captured.ptr() == Py_None) {
	m_captured = Piece();
    } else {
	m_captured = boost::python::extract<Piece>(captured);
    }
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

std::string MoveInfo::san() const {
    return m_san;
}

void MoveInfo::set_san(const std::string& san) {
    m_san = san;
}

MoveInfo& MoveInfo::operator=(const MoveInfo& rhs) {
    m_move = rhs.m_move;
    m_piece = rhs.m_piece;
    m_captured = rhs.m_captured;
    m_is_enpassant = rhs.m_is_enpassant;
    m_is_kingside_castle = rhs.m_is_kingside_castle;
    m_is_queenside_castle = rhs.m_is_queenside_castle;
    m_is_check = rhs.m_is_check;
    m_is_checkmate = rhs.m_is_checkmate;
    m_san = rhs.m_san;

    return *this;
}

} // namespace chess
