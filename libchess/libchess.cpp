#include <boost/python.hpp>

#include "piece.h"

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
}
