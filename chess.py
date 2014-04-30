import sys
import time


COLORS = [ WHITE, BLACK ] = range(0, 2)

PIECE_TYPES = [ NONE, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING ] = range(0, 7)


SQUARES = [
    A1, B1, C1, D1, E1, F1, G1, H1,
    A2, B2, C2, D2, E2, F2, G2, H2,
    A3, B3, C3, D3, E3, F3, G3, H3,
    A4, B4, C4, D4, E4, F4, G4, H4,
    A5, B5, C5, D5, E5, F5, G5, H5,
    A6, B6, C6, D6, E6, F6, G6, H6,
    A7, B7, C7, D7, E7, F7, G7, H7,
    A8, B8, C8, D8, E8, F8, G8, H8 ] = range(0, 64)

SQUARE_NAMES = [
    "a1", "b1", "c1", "d1", "e1", "f1", "g1", "h1",
    "a2", "b2", "c2", "d2", "e2", "f2", "g2", "h2",
    "a3", "b3", "c3", "d3", "e3", "f3", "g3", "h3",
    "a4", "b4", "c4", "d4", "e4", "f4", "g4", "h4",
    "a5", "b5", "c5", "d5", "e5", "f5", "g5", "h5",
    "a6", "b6", "c6", "d6", "e6", "f6", "g6", "h6",
    "a7", "b7", "c7", "d7", "e7", "f7", "g7", "h7",
    "a8", "b8", "c8", "d8", "e8", "f8", "g8", "h8" ]

def file_index(square):
    return square & 7

def rank_index(square):
    return square >> 3

SQUARES_L90 = [
    H1, H2, H3, H4, H5, H6, H7, H8,
    G1, G2, G3, G4, G5, G6, G7, G8,
    F1, F2, F3, F4, F5, F6, F7, F8,
    E1, E2, E3, E4, E5, E6, E7, E8,
    D1, D2, D3, D4, D5, D6, D7, D8,
    C1, C2, C3, C4, C5, C6, C7, C8,
    B1, B2, B3, B4, B5, B6, B7, B8,
    A1, A2, A3, A4, A5, A6, A7, A8 ]

SQUARES_R45 = [
    A1, B8, C7, D6, E5, F4, G3, H2,
    A2, B1, C8, D7, E6, F5, G4, H3,
    A3, B2, C1, D8, E7, F6, G5, H4,
    A4, B3, C2, D1, E8, F7, G6, H5,
    A5, B4, C3, D2, E1, F8, G7, H6,
    A6, B5, C4, D3, E2, F1, G8, H7,
    A7, B6, C5, D4, E3, F2, G1, H8,
    A8, B7, C6, D5, E4, F3, G2, H1 ]

SQUARES_L45 = [
    A2, B3, C4, D5, E6, F7, G8, H1,
    A3, B4, C5, D6, E7, F8, G1, H2,
    A4, B5, C6, D7, E8, F1, G2, H3,
    A5, B6, C7, D8, E1, F2, G3, H4,
    A6, B7, C8, D1, E2, F3, G4, H5,
    A7, B8, C1, D2, E3, F4, G5, H6,
    A8, B1, C2, D3, E4, F5, G6, H7,
    A1, B2, C3, D4, E5, F6, G7, H8 ]

BB_VOID = 0x0000000000000000L

BB_ALL = 0xffffffffffffffffL

BB_SQUARES = [
    BB_A1, BB_B1, BB_C1, BB_D1, BB_E1, BB_F1, BB_G1, BB_H1,
    BB_A2, BB_B2, BB_C2, BB_D2, BB_E2, BB_F2, BB_G2, BB_H2,
    BB_A3, BB_B3, BB_C3, BB_D3, BB_E3, BB_F3, BB_G3, BB_H3,
    BB_A4, BB_B4, BB_C4, BB_D4, BB_E4, BB_F4, BB_G4, BB_H4,
    BB_A5, BB_B5, BB_C5, BB_D5, BB_E5, BB_F5, BB_G5, BB_H5,
    BB_A6, BB_B6, BB_C6, BB_D6, BB_E6, BB_F6, BB_G6, BB_H6,
    BB_A7, BB_B7, BB_C7, BB_D7, BB_E7, BB_F7, BB_G7, BB_H7,
    BB_A8, BB_B8, BB_C8, BB_D8, BB_E8, BB_F8, BB_G8, BB_H8
] = [ 1L << i for i in SQUARES ]

BB_SQUARES_L90 = [ BB_SQUARES[SQUARES_L90[square]] for square in SQUARES ]

BB_SQUARES_L45 = [ BB_SQUARES[SQUARES_L45[square]] for square in SQUARES ]

BB_SQUARES_R45 = [ BB_SQUARES[SQUARES_R45[square]] for square in SQUARES ]

BB_FILES = [
    BB_FILE_A,
    BB_FILE_B,
    BB_FILE_C,
    BB_FILE_D,
    BB_FILE_E,
    BB_FILE_F,
    BB_FILE_G,
    BB_FILE_H
] = [
    BB_A1 | BB_A2 | BB_A3 | BB_A4 | BB_A5 | BB_A6 | BB_A7 | BB_A8,
    BB_B1 | BB_B2 | BB_B3 | BB_B4 | BB_B5 | BB_B6 | BB_B7 | BB_B8,
    BB_C1 | BB_C2 | BB_C3 | BB_C4 | BB_C5 | BB_C6 | BB_C7 | BB_C8,
    BB_D1 | BB_D2 | BB_D3 | BB_D4 | BB_D5 | BB_D6 | BB_D7 | BB_D8,
    BB_E1 | BB_E2 | BB_E3 | BB_E4 | BB_E5 | BB_E6 | BB_E7 | BB_E8,
    BB_F1 | BB_F2 | BB_F3 | BB_F4 | BB_F5 | BB_F6 | BB_F7 | BB_F8,
    BB_G1 | BB_G2 | BB_G3 | BB_G4 | BB_G5 | BB_G6 | BB_G7 | BB_G8,
    BB_H1 | BB_H2 | BB_H3 | BB_H4 | BB_H5 | BB_H6 | BB_H7 | BB_H8
]

BB_RANKS = [
    BB_RANK_1,
    BB_RANK_2,
    BB_RANK_3,
    BB_RANK_4,
    BB_RANK_5,
    BB_RANK_6,
    BB_RANK_7,
    BB_RANK_8
] = [
    BB_A1 | BB_B1 | BB_C1 | BB_D1 | BB_E1 | BB_F1 | BB_G1 | BB_H1,
    BB_A2 | BB_B2 | BB_C2 | BB_D2 | BB_E2 | BB_F2 | BB_G2 | BB_H2,
    BB_A3 | BB_B3 | BB_C3 | BB_D3 | BB_E3 | BB_F3 | BB_G3 | BB_H3,
    BB_A4 | BB_B4 | BB_C4 | BB_D4 | BB_E4 | BB_F4 | BB_G4 | BB_H4,
    BB_A5 | BB_B5 | BB_C5 | BB_D5 | BB_E5 | BB_F5 | BB_G5 | BB_H5,
    BB_A6 | BB_B6 | BB_C6 | BB_D6 | BB_E6 | BB_F6 | BB_G6 | BB_H6,
    BB_A7 | BB_B7 | BB_C7 | BB_D7 | BB_E7 | BB_F7 | BB_G7 | BB_H7,
    BB_A8 | BB_B8 | BB_C8 | BB_D8 | BB_E8 | BB_F8 | BB_G8 | BB_H8
]


def shift_down(b):
    return b >> 8

def shift_2_down(b):
    return b >> 16

def shift_up(b):
    return (b << 8) & BB_ALL

def shift_2_up(b):
    return (b << 16) & BB_ALL

def shift_right(b):
    return (b << 1) & ~BB_FILE_A

def shift_2_right(b):
    return (b << 2) & ~BB_FILE_A & ~BB_FILE_B

def shift_left(b):
    return (b >> 1) & ~BB_FILE_H

def shift_2_left(b):
    return (b >> 2) & ~BB_FILE_G & ~BB_FILE_H

def shift_up_left(b):
    return (b << 7) & ~BB_FILE_H

def shift_up_right(b):
    return (b << 9) & ~BB_FILE_A

def shift_down_left(b):
    return (b >> 9) & ~BB_FILE_H

def shift_down_right(b):
    return (b >> 7) & ~BB_FILE_A

def l90(b):
    mask = BB_VOID

    for i in range(0, 64):
        if BB_SQUARES[i] & b:
            mask |= SQUARES_L90[i]




BB_KNIGHT_ATTACKS = []

for bb_square in BB_SQUARES:
    mask = BB_VOID
    mask |= shift_left(shift_2_up(bb_square))
    mask |= shift_right(shift_2_up(bb_square))
    mask |= shift_left(shift_2_down(bb_square))
    mask |= shift_right(shift_2_down(bb_square))
    mask |= shift_2_left(shift_up(bb_square))
    mask |= shift_2_right(shift_up(bb_square))
    mask |= shift_2_left(shift_down(bb_square))
    mask |= shift_2_right(shift_down(bb_square))
    BB_KNIGHT_ATTACKS.append(mask)


BB_KING_ATTACKS = []

for bb_square in BB_SQUARES:
    mask = BB_VOID
    mask |= shift_left(bb_square)
    mask |= shift_right(bb_square)
    mask |= shift_up(bb_square)
    mask |= shift_down(bb_square)
    mask |= shift_up_left(bb_square)
    mask |= shift_up_right(bb_square)
    mask |= shift_down_left(bb_square)
    mask |= shift_down_right(bb_square)
    BB_KING_ATTACKS.append(mask)


BB_RANK_ATTACKS = [ [ BB_VOID for i in range(0, 64) ] for k in range(0, 64) ]

BB_FILE_ATTACKS = [ [ BB_VOID for i in range(0, 64) ] for k in range(0, 64) ]

for square in SQUARES:
    for bitrow in range(0, 64):
        f = file_index(square) + 1
        q = square + 1
        while f < 8:
            BB_RANK_ATTACKS[square][bitrow] |= BB_SQUARES[q]
            if (1 << f) & (bitrow << 1):
                break
            q += 1
            f += 1

        f = file_index(square) - 1
        q = square - 1
        while f >= 0:
            BB_RANK_ATTACKS[square][bitrow] |= BB_SQUARES[q]
            if (1 << f) & (bitrow << 1):
                break
            q -= 1
            f -= 1

        r = rank_index(square) + 1
        q = square + 8
        while r < 8:
            BB_FILE_ATTACKS[square][bitrow] |= BB_SQUARES[q]
            if (1 << (7 - r)) & (bitrow << 1):
                break
            q += 8
            r += 1

        r = rank_index(square) - 1
        q = square - 8
        while r >= 0:
            BB_FILE_ATTACKS[square][bitrow] |= BB_SQUARES[q]
            if (1 << (7 - r)) & (bitrow << 1):
                break
            q -= 8
            r -= 1

BB_SHIFT_R45 = [
    1, 58, 51, 44, 37, 30, 23, 16,
    9, 1, 58, 51, 44, 37, 30, 23,
    17, 9, 1, 58, 51, 44, 37, 30,
    25, 17, 9, 1, 58, 51, 44, 37,
    33, 25, 17, 9, 1, 58, 51, 44,
    41, 33, 25, 17, 9, 1, 58, 51,
    49, 41, 33, 25, 17, 9, 1, 58,
    57, 49, 41, 33, 25, 17, 9, 1 ]

BB_SHIFT_L45 = [
    9, 17, 25, 33, 41, 49, 57, 1,
    17, 25, 33, 41, 49, 57, 1, 10,
    25, 33, 41, 49, 57, 1, 10, 19,
    33, 41, 49, 57, 1, 10, 19, 28,
    41, 49, 57, 1, 10, 19, 28, 37,
    49, 57, 1, 10, 19, 28, 37, 46,
    57, 1, 10, 19, 28, 37, 46, 55,
    1, 10, 19, 28, 37, 46, 55, 64 ]


BB_L45_ATTACKS = [ [ BB_VOID for i in range(0, 64) ] for k in range(0, 64) ]

BB_R45_ATTACKS = [ [ BB_VOID for i in range(0, 64) ] for k in range(0, 64) ]

for s in SQUARES:
    for b in range(0, 64):
        mask = BB_VOID

        q = s
        while file_index(q) > 0 and rank_index(q) < 7:
            q += 7
            mask |= BB_SQUARES[q]
            if b & (BB_SQUARES_L45[q] >> BB_SHIFT_L45[s]):
                break

        q = s
        while file_index(q) < 7 and rank_index(q) > 0:
            q -= 7
            mask |= BB_SQUARES[q]
            if b & (BB_SQUARES_L45[q] >> BB_SHIFT_L45[s]):
                break

        BB_L45_ATTACKS[s][b] = mask

        mask = BB_VOID

        q = s
        while file_index(q) < 7 and rank_index(q) < 7:
            q += 9
            mask |= BB_SQUARES[q]
            if b & (BB_SQUARES_R45[q] >> BB_SHIFT_R45[s]):
                break

        q = s
        while file_index(q) > 0 and rank_index(q) > 0:
            q -= 9
            mask |= BB_SQUARES[q]
            if b & (BB_SQUARES_R45[q] >> BB_SHIFT_R45[s]):
                break

        BB_R45_ATTACKS[s][b] = mask


BB_PAWN_ATTACKS = [
    [ shift_up_left(s) | shift_up_right(s) for s in BB_SQUARES ],
    [ shift_down_left(s) | shift_down_right(s) for s in BB_SQUARES ]
]

BB_PAWN_F1 = [
    [ shift_up(s) for s in BB_SQUARES ],
    [ shift_down(s) for s in BB_SQUARES ]
]

BB_PAWN_F2 = [
    [ shift_2_up(s) for s in BB_SQUARES ],
    [ shift_2_down(s) for s in BB_SQUARES ]
]

BB_PAWN_ALL = [
    [ BB_PAWN_ATTACKS[0][i] | BB_PAWN_F1[0][i] | BB_PAWN_F2[0][i] for i in SQUARES ],
    [ BB_PAWN_ATTACKS[1][i] | BB_PAWN_F1[1][i] | BB_PAWN_F2[1][i] for i in SQUARES ]
]


def knight_attacks_from(square):
    return BB_KNIGHT_ATTACKS[square]

def king_attacks_from(square):
    return BB_KING_ATTACKS[square]

def rook_attacks_from(square, occupied, occupied_l90):
    return (BB_RANK_ATTACKS[square][(occupied >> ((square & ~7) + 1)) & 63] |
            BB_FILE_ATTACKS[square][(occupied_l90 >> (((square & 7) << 3) + 1)) & 63])

def bishop_attacks_from(square, occupied_r45, occupied_l45):
    return (BB_R45_ATTACKS[square][(occupied_r45 >> BB_SHIFT_R45[square]) & 63] |
            BB_L45_ATTACKS[square][(occupied_l45 >> BB_SHIFT_L45[square]) & 63])

def queen_attacks_from(square, occupied, occupied_l90, occupied_r45, occupied_l45):
    return (rook_attacks_from(square, occupied, occupied_l90) |
            bishop_attacks_from(square, occupied_r45, occupied_l45))


def next_bit(b):
    x = b & -b
    b ^= x

    r = 0

    if not x & 0xffffffff:
        x >>= 32
        r |= 32

    if not x & 0xffff:
        x >>= 16
        r |= 16

    if not x & 0xff:
        x >>= 8
        r |= 8

    if not x & 0xf:
        x >>= 4
        r |= 4

    if not x & 0x3:
        x >>= 2
        r |= 2

    if not x & 0x1:
        r |= 1

    return r, b


def sparse_pop_count(b):
    count = 0

    while b:
        count += 1
        b &= b - 1

    return count

BYTE_POP_COUNT = [ sparse_pop_count(i) for i in range(256) ]

def pop_count(b):
    return (BYTE_POP_COUNT[  b        & 0xff ] +
            BYTE_POP_COUNT[ (b >>  8) & 0xff ] +
            BYTE_POP_COUNT[ (b >> 16) & 0xff ] +
            BYTE_POP_COUNT[ (b >> 24) & 0xff ] +
            BYTE_POP_COUNT[ (b >> 32) & 0xff ] +
            BYTE_POP_COUNT[ (b >> 40) & 0xff ] +
            BYTE_POP_COUNT[ (b >> 48) & 0xff ] +
            BYTE_POP_COUNT[ (b >> 56) & 0xff ])


def visualize(bb):
    for i, square in enumerate(BB_SQUARES):
        if bb & square:
            sys.stdout.write("[X]")
        else:
            sys.stdout.write("[ ]")
        if i % 8 == 7:
            sys.stdout.write("\n")
    sys.stdout.flush()


class Bitboard:

    def __init__(self):
        self.pawns = BB_RANK_2 | BB_RANK_7
        self.knights = BB_B1 | BB_G1 | BB_B8 | BB_G8
        self.bishops = BB_C1 | BB_F1 | BB_C8 | BB_F8
        self.rooks = BB_A1 | BB_H1 | BB_A8 | BB_H8
        self.queens = BB_D1 | BB_D8
        self.kings = BB_E1 | BB_E8

        self.occupied_co = [ BB_RANK_1 | BB_RANK_2, BB_RANK_7 | BB_RANK_8 ]
        self.occupied = BB_RANK_1 | BB_RANK_2 | BB_RANK_7 | BB_RANK_8

        self.occupied_l90 = BB_VOID
        self.occupied_l45 = BB_VOID
        self.occupied_r45 = BB_VOID

        self.side_to_move = WHITE

        for i in range(64):
            if BB_SQUARES[i] & self.occupied:
                self.occupied_l90 |= BB_SQUARES_L90[i]
                self.occupied_r45 |= BB_SQUARES_R45[i]
                self.occupied_l45 |= BB_SQUARES_L45[i]


    def generate_pseudo_legal_moves(self):
        # TODO: Implement black side.

        if True:
            movers = self.pawns & self.occupied_co[WHITE]

            # TODO: Castling.

            # TODO: En passant.

            # Pawn captures.
            moves = shift_up_right(movers) & self.occupied_co[BLACK]
            while moves:
                to_square, moves = next_bit(moves)
                from_square = to_square - 9
                if rank_index(to_square) != 7:
                    pass
                else:
                    pass

            moves = shift_up_left(movers) & self.occupied_co[BLACK]
            while moves:
                to_square, moves = next_bit(moves)
                from_square = to_square - 7
                if rank_index(to_square) != 7:
                    pass
                else:
                    pass

            # Pawns one forward.
            moves = shift_up(movers) & ~self.occupied
            movers = moves
            while moves:
                to_square, moves = next_bit(moves)
                from_square = to_square - 8
                if rank_index(to_square) != 7:
                    pass
                else:
                    pass

            # Pawns two forward.
            moves = shift_up(movers) & BB_RANK_4 & ~self.occupied
            while moves:
                to_square, moves = next_bit(moves)
                from_square = to_square - 16
                pass


        movers = self.knights & self.occupied_co[WHITE]
        while movers:
            from_square, movers = next_bit(movers)
            moves = knight_attacks_from(from_square) & ~self.occupied_co[WHITE]
            while moves:
                to_square, moves = next_bit(moves)
                pass

        movers = self.bishops & self.occupied_co[WHITE]
        while movers:
            from_square, movers = next_bit(movers)
            moves = bishop_attacks_from(from_square, self.occupied_r45, self.occupied_l45) & ~self.occupied_co[WHITE]
            while moves:
                to_square, moves = next_bit(moves)
                pass

        movers = self.rooks & self.occupied_co[WHITE]
        while movers:
            from_square, movers = next_bit(movers)
            moves = rook_attacks_from(from_square, self.occupied, self.occupied_l90) & ~self.occupied_co[WHITE]
            while moves:
                to_square, moves = next_bit(moves)
                pass

        movers = self.queens & self.occupied_co[WHITE]
        while movers:
            from_square, movers = next_bit(movers)
            moves = queen_attacks_from(from_square, self.occupied, self.occupied_l90, self.occupied_r45, self.occupied_l45) & ~self.occupied_co[WHITE]
            while moves:
                to_square, moves = next_bit(moves)
                pass

        # TODO: Use king square directly.
        movers = self.kings & self.occupied_co[WHITE]
        while movers:
            from_square, movers = next_bit(movers)
            moves = king_attacks_from(from_square) & ~self.occupied_co[WHITE]
            while moves:
                to_square, moves = next_bit(moves)

    def is_attacked_by(self, color, square):
        if BB_PAWN_ATTACKS[color ^ 1][square] & (self.pawns | self.bishops) & self.occupied_co[color]:
            return True

        if knight_attacks_from(square) & self.knights & self.occupied_co[color]:
            return True

        if bishop_attacks_from(square, self.occupied_r45, self.occupied_l45) & (self.bishops | self.queens) & self.occupied_co[color]:
            return True

        if rook_attacks_from(square, self.occupied, self.occupied_l90) & (self.rooks | self.queens) & self.occupied_co[color]:
            return True

        if king_attacks_from(square) & (self.kings | self.queens) & self.occupied_co[color]:
            return True

        return False

    def pawn_moves_from(self, square):
        targets = BB_PAWN_F1[self.side_to_move][square] & ~self.occupied

        if targets:
            targets |= BB_PAWN_F2[self.side_to_move][square] & ~self.occupied

        if not False:
            targets |= BB_PAWN_ATTACKS[self.side_to_move][square] & self.occupied_co[self.side_to_move ^ 1]
        else:
            # TODO: En-passant.
            pass

        return targets



board = Bitboard()
t = time.time()
board.generate_pseudo_legal_moves()
print time.time() - t

print board.is_attacked_by(WHITE, D4)

visualize(board.pawn_moves_from(E2))
print board.is_attacked_by(WHITE, E3)
print board.is_attacked_by(WHITE, E4)

print sparse_pop_count(board.pawns)
