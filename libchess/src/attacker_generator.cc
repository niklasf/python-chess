#include "attacker_generator.h"

namespace chess {

AttackerGenerator::AttackerGenerator(const Position& position, char color, const Square& target)
    : m_target(target)
{
    if (!target.is_valid()) {
	throw new std::invalid_argument("target");
    }

    if (color != 'b' && color != 'w') {
	throw new std::invalid_argument("color");
    }

    m_position = new Position(position);
    m_color = color;
    m_source_index = 0;
}

AttackerGenerator::~AttackerGenerator() {
    delete m_position;
}

int AttackerGenerator::__len__() {
    int count = 0;
    for (int index = 0; index < 64; index++) {
	if (__contains__(Square(index))) {
	    count++;
	}
    }
    return count;
}

bool AttackerGenerator::__nonzero__() {
    // Generate attackers until one is found.
    for (int index = 0; index < 64; index++) {
	if (__contains__(Square(index))) {
	    return true;
	}
    }
    return false;
}

AttackerGenerator& AttackerGenerator::__iter__() {
    m_source_index = 0;
    return *this;
}

bool AttackerGenerator::__contains__(const Square& source) {
    Piece piece = m_position->get(source);
    if (!piece.is_valid() || piece.color() != m_color) {
	return false;
    }

    const int attacks[] = {
	20, 0, 0, 0, 0, 0, 0, 24, 0, 0, 0, 0, 0, 0, 20, 0,
	0, 20, 0, 0, 0, 0, 0, 24, 0, 0, 0, 0, 0, 20, 0, 0,
	0, 0, 20, 0, 0, 0, 0, 24, 0, 0, 0, 0, 20, 0, 0, 0,
	0, 0, 0, 20, 0, 0, 0, 24, 0, 0, 0, 20, 0, 0, 0, 0,
	0, 0, 0, 0, 20, 0, 0, 24, 0, 0, 20, 0, 0, 0, 0, 0,
	0, 0, 0, 0, 0, 20, 2, 24, 2, 20, 0, 0, 0, 0, 0, 0,
	0, 0, 0, 0, 0, 2, 53, 56, 53, 2, 0, 0, 0, 0, 0, 0,
	24, 24, 24, 24, 24, 24, 56, 0, 56, 24, 24, 24, 24, 24, 24, 0,
	0, 0, 0, 0, 0, 2, 53, 56, 53, 2, 0, 0, 0, 0, 0, 0,
	0, 0, 0, 0, 0, 20, 2, 24, 2, 20, 0, 0, 0, 0, 0, 0,
	0, 0, 0, 0, 20, 0, 0, 24, 0, 0, 20, 0, 0, 0, 0, 0,
	0, 0, 0, 20, 0, 0, 0, 24, 0, 0, 0, 20, 0, 0, 0, 0,
	0, 0, 20, 0, 0, 0, 0, 24, 0, 0, 0, 0, 20, 0, 0, 0,
	0, 20, 0, 0, 0, 0, 0, 24, 0, 0, 0, 0, 0, 20, 0, 0,
	20, 0, 0, 0, 0, 0, 0, 24, 0, 0, 0, 0, 0, 0, 20
    };

    const int rays[] = {
	17, 0, 0, 0, 0, 0, 0, 16, 0, 0, 0, 0, 0, 0, 15, 0,
	0, 17, 0, 0, 0, 0, 0, 16, 0, 0, 0, 0, 0, 15, 0, 0,
	0, 0, 17, 0, 0, 0, 0, 16, 0, 0, 0, 0, 15, 0, 0, 0,
	0, 0, 0, 17, 0, 0, 0, 16, 0, 0, 0, 15, 0, 0, 0, 0,
	0, 0, 0, 0, 17, 0, 0, 16, 0, 0, 15, 0, 0, 0, 0, 0,
	0, 0, 0, 0, 0, 17, 0, 16, 0, 15, 0, 0, 0, 0, 0, 0,
	0, 0, 0, 0, 0, 0, 17, 16, 15, 0, 0, 0, 0, 0, 0, 0,
	1, 1, 1, 1, 1, 1, 1, 0, -1, -1, -1, -1, -1, -1, -1, 0,
	0, 0, 0, 0, 0, 0, -15, -16, -17, 0, 0, 0, 0, 0, 0, 0,
	0, 0, 0, 0, 0, -15, 0, -16, 0, -17, 0, 0, 0, 0, 0, 0,
	0, 0, 0, 0, -15, 0, 0, -16, 0, 0, -17, 0, 0, 0, 0, 0,
	0, 0, 0, -15, 0, 0, 0, -16, 0, 0, 0, -17, 0, 0, 0, 0,
	0, 0, -15, 0, 0, 0, 0, -16, 0, 0, 0, 0, -17, 0, 0, 0,
	0, -15, 0, 0, 0, 0, 0, -16, 0, 0, 0, 0, 0, -17, 0, 0,
	-15, 0, 0, 0, 0, 0, 0, -16, 0, 0, 0, 0, 0, 0, -17
    };

    int shift;
    switch (piece.type()) {
	case 'p':
	    shift = 0;
	    break;
	case 'n':
	    shift = 1;
	    break;
	case 'b':
	    shift = 2;
	    break;
	case 'r':
	    shift = 3;
	    break;
	case 'q':
	    shift = 4;
	    break;
	case 'k':
	    shift = 5;
	    break;
    }

    int difference = source.x88_index() - m_target.x88_index();
    int index = difference + 119;

    if (attacks[index] & (1 << shift)) {
	// Handle pawns.
	if (piece.type() == 'p') {
	    if (difference > 0) {
		if (piece.color() == 'w') {
		    return true;
		}
	    } else {
		if (piece.color() == 'b') {
		    return true;
		}
	    }
	    return false;
	}

	// Handle knights and king.
	if (piece.type() == 'n' || piece.type() == 'k') {
	    return true;
	}

	// Handle the others.
	int offset = rays[index];
	int j = source.x88_index() + offset;
	bool blocked = false;
	while (j != m_target.x88_index()) {
	    if (m_position->get(Square::from_x88_index(j)).is_valid()) {
		blocked = true;
	    }
	    j += offset;
	}
	return !blocked;
    }

    return false;
}

bool AttackerGenerator::has_more() {
    for (int i = m_source_index; i < 64; i++) {
	if (__contains__(Square(i))) {
	    return true;
	}
    }
    return false;
}

Square AttackerGenerator::next() {
    while (m_source_index < 64) {
	Square square(m_source_index++);
	if (__contains__(square)) {
	    return square;
	}
    }

    throw std::logic_error("Called AttackerGenerator::next() although there are no more attacks.");
}

Square AttackerGenerator::python_next() {
    while (m_source_index < 64) {
	Square square(m_source_index++);
	if (__contains__(square)) {
	    return square;
	}
    }

    PyErr_SetNone(PyExc_StopIteration);
    throw boost::python::error_already_set();
}

} // namespace chess
