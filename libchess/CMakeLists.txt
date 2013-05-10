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
    src/libchess.cc
    src/piece.cc
    src/square.cc
    src/move.cc
    src/move_info.cc
    src/position.cc
    src/attacker_generator.cc
    src/legal_move_generator.cc
    src/pseudo_legal_move_generator.cc
    src/polyglot_opening_book_entry.cc)
target_link_libraries (chess
    ${Boost_LIBRARIES}
    ${PYTHON_LIBRARIES})

get_property(libchess_LOCATION TARGET chess PROPERTY LOCATION)
configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/setup.py.in
    ${CMAKE_CURRENT_SOURCE_DIR}/setup.py)

add_test (libchess ./test.py)
