cmake_minimum_required (VERSION 2.8)
enable_testing ()
project (libchess)

find_package (Boost)
find_package (Boost COMPONENTS python regex REQUIRED)
find_package (PythonLibs REQUIRED)

set(CMAKE_CXX_FLAGS "-g -Wall")

set (Boost_USE_STATIC_LIBS OFF)
set (Boost_USE_MULTITHREADED ON)

include_directories (${Boost_INCLUDE_DIRS} ${PYTHON_INCLUDE_DIRS})
link_directories (${PYTHON_LIBRARIES})
add_library (chess SHARED
    libchess.cpp
    piece.cpp
    square.cpp
    move.cpp
    move_info.cpp
    position.cpp
    attacker_generator.cpp
    legal_move_generator.cpp
    pseudo_legal_move_generator.cpp
    polyglot_opening_book_entry.cpp)
target_link_libraries (chess
    ${Boost_LIBRARIES}
    ${PYTHON_LIBRARIES})

get_property(libchess_LOCATION TARGET chess PROPERTY LOCATION)
configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/setup.py.in
    ${CMAKE_CURRENT_SOURCE_DIR}/setup.py)

add_test (libchess ./test.py)
