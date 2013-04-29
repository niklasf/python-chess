#include <boost/python.hpp>
#include <boost/format.hpp>

#include "libchess.h"

namespace chess {

    char opposite_color(char color) {
        if (color == 'w') {
            return 'b';
        } else if (color == 'b') {
            return 'w';
        } else {
            throw new std::invalid_argument("color");
        }
    }

    void python_translate_invalid_argument(const std::invalid_argument *e) {
        std::string str = boost::str(
            boost::format("Invalid argument: %1%.") % std::string(e->what()));
        PyErr_SetString(PyExc_ValueError, str.c_str());
    }

    void python_translate_logic_error(const std::logic_error *e) {
        PyErr_SetString(PyExc_RuntimeError, e->what());
    }

}

BOOST_PYTHON_MODULE(libchess)
{
    using namespace boost::python;
    using namespace chess;

    register_exception_translator<std::logic_error *>(&python_translate_logic_error);
    register_exception_translator<std::invalid_argument *>(&python_translate_invalid_argument);

    def("opposite_color", &opposite_color);

    scope().attr("START_FEN") = START_FEN;

    class_<Piece>("Piece", init<char>())
        .add_property("symbol", &Piece::symbol)
        .add_property("color", &Piece::color)
        .add_property("type", &Piece::type)
        .add_property("full_color", &Piece::full_color)
        .add_property("full_type", &Piece::full_type)
        .def(self == other<Piece>())
        .def(self != other<Piece>())
        .def(self_ns::str(self))
        .def("__repr__", &Piece::__repr__)
        .def("__hash__", &Piece::__hash__)
        .def("from_color_and_type", &Piece::from_color_and_type)
        .staticmethod("from_color_and_type");

    class_<Square>("Square", init<std::string>())
        .add_property("rank", &Square::rank)
        .add_property("file", &Square::file)
        .add_property("index", &Square::index)
        .add_property("x88_index", &Square::x88_index)
        .add_property("name", &Square::name)
        .add_property("file_name", &Square::file_name)
        .def("is_dark", &Square::is_dark)
        .def("is_light", &Square::is_light)
        .def("is_backrank", &Square::is_backrank)
        .def("is_seventh", &Square::is_seventh)
        .def(self == other<Square>())
        .def(self != other<Square>())
        .def(self_ns::str(self))
        .def("__repr__", &Square::__repr__)
        .def("__hash__", &Square::__hash__)
        .def("from_rank_and_file", &Square::from_rank_and_file)
        .staticmethod("from_rank_and_file")
        .def("from_index", &Square::from_index)
        .staticmethod("from_index")
        .def("from_x88_index", &Square::from_x88_index)
        .staticmethod("from_x88_index");

    class_<Move>("Move", init<Square, Square>())
        .def(init<Square, Square, char>())
        .add_property("source", &Move::source)
        .add_property("target", &Move::target)
        .add_property("promotion", &Move::promotion)
        .add_property("full_promotion", &Move::full_promotion)
        .add_property("uci", &Move::uci)
        .def("is_promotion", &Move::is_promotion)
        .def(self == other<Move>())
        .def(self != other<Move>())
        .def(self_ns::str(self))
        .def("__repr__", &Move::__repr__)
        .def("__hash__", &Move::__hash__)
        .def("from_uci", &Move::from_uci)
        .staticmethod("from_uci");

    class_<MoveInfo>("MoveInfo", init<Move, Piece, std::string>())
        .add_property("move", &MoveInfo::move, &MoveInfo::set_move)
        .add_property("piece", &MoveInfo::piece, &MoveInfo::set_piece)
        .add_property("captured", &MoveInfo::python_captured, &MoveInfo::python_set_captured)
        .add_property("san", &MoveInfo::san, &MoveInfo::set_san)
        .add_property("is_enpassant", &MoveInfo::is_enpassant, &MoveInfo::set_is_enpassant)
        .add_property("is_kingside_castle", &MoveInfo::is_kingside_castle, &MoveInfo::set_is_kingside_castle)
        .add_property("is_queenside_castle", &MoveInfo::is_queenside_castle, &MoveInfo::set_is_queenside_castle)
        .add_property("is_castle", &MoveInfo::is_castle)
        .add_property("is_check", &MoveInfo::is_check, &MoveInfo::set_is_check)
        .add_property("is_checkmate", &MoveInfo::is_checkmate, &MoveInfo::set_is_checkmate);

    class_<Position>("Position")
        .def(init<std::string>())
        .def("reset", &Position::reset)
        .def("clear_board", &Position::clear_board)
        .add_property("turn", &Position::turn, &Position::set_turn)
        .def("toggle_turn", &Position::toggle_turn)
        .add_property("ep_file", &Position::python_ep_file, &Position::python_set_ep_file)
        .add_property("half_moves", &Position::half_moves, &Position::set_half_moves)
        .add_property("ply", &Position::ply, &Position::set_ply)
        .def("get_ep_square", &Position::python_get_ep_square)
        .def("get_pseudo_legal_moves", &Position::get_pseudo_legal_moves, return_value_policy<manage_new_object>())
        .add_property("fen", &Position::fen, &Position::set_fen)
        .def(self == other<Position>())
        .def(self != other<Position>())
        .def(self_ns::str(self))
        .def("__getitem__", &Position::__getitem__)
        .def("__setitem__", &Position::__setitem__)
        .def("__delitem__", &Position::__delitem__)
        .def("__repr__", &Position::__repr__)
        .def("__hash__", &Position::__hash__);

    class_<PseudoLegalMoveGenerator>("PseudoLegalMoveGenerator", init<Position&>())
        .def("__iter__", &PseudoLegalMoveGenerator::__iter__)
        .def("__contains__", &PseudoLegalMoveGenerator::__contains__)
        .def("__len__", &PseudoLegalMoveGenerator::__len__)
        .def("__nonzero__", &PseudoLegalMoveGenerator::__nonzero__)
        .def("next", &PseudoLegalMoveGenerator::next);
}
