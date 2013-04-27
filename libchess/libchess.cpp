#include <boost/python.hpp>

#include "piece.h"
#include "square.h"
#include "move.h"
#include "position.h"

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

}

BOOST_PYTHON_MODULE(libchess)
{
    using namespace boost::python;
    using namespace chess;

    def("opposite_color", &opposite_color);

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

    class_<Position>("Position")
        .def("__getitem__", &Position::__getitem__)
        .def("__setitem__", &Position::__setitem__)
        .def("__delitem__", &Position::__delitem__);
}
