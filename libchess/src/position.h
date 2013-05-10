#ifndef LIBCHESS_POSITION_H
#define LIBCHESS_POSITION_H

#include <boost/python.hpp>
#include <stdint.h>

#include "piece.h"
#include "square.h"
#include "attacker_generator.h"
#include "pseudo_legal_move_generator.h"
#include "move_info.h"

namespace chess {

class AttackerGenerator;
class LegalMoveGenerator;
class PseudoLegalMoveGenerator;

/**
 * \brief A chess position.
 */
class Position {
public:

    Position();
    Position(const std::string& fen);
    Position(const Position& position);

    void clear_board();
    void reset();

    Piece get(const Square& square) const;
    void set(const Square& square, const Piece& piece);
    boost::python::object __getitem__(const boost::python::object& square_key) const;
    void __setitem__(const boost::python::object& square_key, const boost::python::object& piece);
    void __delitem__(const boost::python::object& square_key);


    char turn() const;
    void set_turn(char turn);
    void toggle_turn();

    char ep_file() const;
    void set_ep_file(char ep_file);
    boost::python::object python_ep_file() const;
    void python_set_ep_file(const boost::python::object& ep_file);
    Square get_ep_square() const;
    boost::python::object python_get_ep_square() const;

    int half_moves() const;
    void set_half_moves(int half_moves);

    int ply() const;
    void set_ply(int ply);

    std::string fen() const;
    void set_fen(const std::string& fen);

    const PseudoLegalMoveGenerator *get_pseudo_legal_moves() const;
    const LegalMoveGenerator *get_legal_moves() const;
    const AttackerGenerator *get_attackers(char color, Square target) const;

    Square get_king(char color) const;
    boost::python::object python_get_king(char color) const;

    bool is_king_attacked(char color) const;
    bool is_check() const;
    bool is_checkmate() const;
    bool is_stalemate() const;

    bool could_have_kingside_castling_right(char color) const;
    bool could_have_queenside_castling_right(char color) const;
    bool has_kingside_castling_right(char color) const;
    bool has_queenside_castling_right(char color) const;
    void set_kingside_castling_right(char color, bool castle);
    void set_queenside_castling_right(char color, bool castle);

    MoveInfo make_move(const Move& move);
    void make_move_fast(const Move& move);
    Move get_move_from_san(const std::string& san) const;
    MoveInfo make_move_from_san(const std::string& san);

    std::string __repr__() const;
    uint64_t __hash__() const;

    bool operator==(const Position& rhs) const;
    bool operator!=(const Position& rhs) const;

protected:
    MoveInfo make_unvalidated_move_fast(const Move& move);

    Piece m_board[128];
    char m_turn;
    char m_ep_file;
    int m_half_moves;
    int m_ply;
    bool m_white_castle_queenside;
    bool m_white_castle_kingside;
    bool m_black_castle_queenside;
    bool m_black_castle_kingside;

private:
    friend class LegalMoveGenerator;

    int x88_index_from_square_key(const boost::python::object& square_key) const;

};

std::ostream& operator<<(std::ostream& out, const Position& position);

const std::string START_FEN("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");

extern const uint64_t POLYGLOT_RANDOM_ARRAY[];

} // namespace chess

#endif // LIBCHESS_POSITION_H
