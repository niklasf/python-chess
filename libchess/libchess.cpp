#include <boost/python.hpp>

#include "piece.h"
#include "square.h"

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
        .staticmethod("from_index");
}
