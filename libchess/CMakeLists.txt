cmake_minimum_required (VERSION 2.8)
enable_testing ()
project (libchess)

find_package (Boost COMPONENTS unit_test_framework python REQUIRED)
find_package (PythonLibs REQUIRED)

include_directories (${PYTHON_INCLUDE_DIRS})
link_directories (${PYTHON_LIBRARIES})
add_library (chess SHARED libchess.cpp piece.cpp)
target_link_libraries (chess ${Boost_PYTHON_LIBRARY} ${PYTHON_LIBRARIES})

add_executable (libchesstest test.cpp)
target_link_libraries (libchesstest ${Boost_UNIT_TEST_FRAMEWORK_LIBRARY})
add_test (libchess libchesstest)
