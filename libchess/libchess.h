#ifndef LIBCHESS_LIBCHESS_H
#define LIBCHESS_LIBCHESS_H

#include "piece.h"
#include "square.h"
#include "move.h"
#include "position.h"
#include "pseudo_legal_move_generator.h"

namespace chess {

    char opposite_color(char color);

}

#endif
