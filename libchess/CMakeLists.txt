cmake_minimum_required (VERSION 2.8)
enable_testing ()
project (libchess)

find_package (Boost)
find_package (Boost COMPONENTS python REQUIRED)
find_package (PythonLibs REQUIRED)

set (Boost_USE_STATIC_LIBS OFF)
set (Boost_USE_MULTITHREADED ON)

include_directories (${PYTHON_INCLUDE_DIRS})
link_directories (${PYTHON_LIBRARIES})
add_library (chess SHARED libchess.cpp piece.cpp)
target_link_libraries (chess
    ${Boost_PYTHON_LIBRARY}
    ${PYTHON_LIBRARIES})

add_test (libchess ./test.py)
