#include <boost/python.hpp>

const char *yay() {
    return "yay";
}

BOOST_PYTHON_MODULE(chess)
{
    using namespace boost::python;
    def("yay", yay);
}
