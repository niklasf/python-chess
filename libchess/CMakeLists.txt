cmake_minimum_required (VERSION 2.8)
enable_testing ()
project (libchess)

find_package (Boost COMPONENTS unit_test_framework REQUIRED)

add_executable (libchesstest test.cpp)
target_link_libraries (libchesstest ${Boost_UNIT_TEST_FRAMEWORK_LIBRARY})
add_test (libchess libchesstest)
