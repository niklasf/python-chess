#include <boost/python.hpp>

#include "piece.h"

const char *yay() {
    return "yay";
}

BOOST_PYTHON_MODULE(libchess)
{
    using namespace boost::python;
    using namespace chess;

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
        .def("__hash__", &Piece::__hash__);
}
