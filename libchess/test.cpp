#define BOOST_TEST_MODULE libchess
#define BOOST_TEST_DYN_LINK
#include <boost/test/unit_test.hpp>

BOOST_AUTO_TEST_SUITE(libchess)

BOOST_AUTO_TEST_CASE(foo)
{
    BOOST_CHECK(1 == 1);
}

BOOST_AUTO_TEST_SUITE_END()
