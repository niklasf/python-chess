#!/usr/bin/python

import ctypes
import ctypes.util
import chess
import chess.syzygy

class Tablebases(object):
    def __init__(self, libgtb=None, LibraryLoader=ctypes.cdll):
        if libgtb is None:
            libgtb = ctypes.util.find_library("gtb")

        self.libgtb = LibraryLoader.LoadLibrary(libgtb)

        self.libgtb.tb_init.restype = ctypes.c_char_p

    def tb_init(self, verbosity, compression_scheme, paths):
        """
        verbosity - 0 non-verbose, 1 verbose
        scheme    - for example tb_CP4
        """
        c_paths = (ctypes.c_char_p * len(paths))()
        c_paths[:] = [bytes(path, "utf-8") for path in paths]

        ret = self.libgtb.tb_init(
                ctypes.c_int(verbosity),
                ctypes.c_int(compression_scheme),
                ctypes.byref(c_paths))

        if verbosity:
            return str(ret.decode("utf-8"))
        else:
            return 0

    def tbcache_init(self, cache_mem, wdl_fraction):
        return self.libgtb.tbcache_init(ctypes.c_size_t(cache_mem), ctypes.c_int(wdl_fraction))

    def probe_dtm(self, board):
        if chess.pop_count(board.occupied_co[chess.WHITE]) > 16:
            return None
        if chess.pop_count(board.occupied_co[chess.BLACK]) > 16:
            return None

        if board.castling_rights:
            return None

        stm = ctypes.c_uint(0 if board.turn == chess.WHITE else 1)
        ep_square = ctypes.c_uint(board.ep_square if board.ep_square else 64)
        castling = ctypes.c_uint(0)

        c_ws = (ctypes.c_uint * 17)()
        c_wp = (ctypes.c_ubyte * 17)()

        for i, square in enumerate(chess.SquareSet(board.occupied_co[chess.WHITE])):
            c_ws[i] = square
            c_wp[i] = board.piece_type_at(square)

        c_ws[i + 1] = 64
        c_wp[i + 1] = chess.NONE

        c_bs = (ctypes.c_uint * 17)()
        c_bp = (ctypes.c_ubyte * 17)()

        for i, square in enumerate(chess.SquareSet(board.occupied_co[chess.BLACK])):
            c_bs[i] = square
            c_bp[i] = board.piece_type_at(square)

        c_bs[i + 1] = 64
        c_bp[i + 1] = chess.NONE

        # Do a hard probe.
        info = ctypes.c_uint()
        pliestomate = ctypes.c_uint()
        ret = self.libgtb.tb_probe_hard(stm, ep_square, castling, c_ws, c_bs, c_wp, c_bp, ctypes.byref(info), ctypes.byref(pliestomate))

        # Probe failed, forbidding or unknown.
        if not ret or info.value == 3 or info.value == 7:
            return None

        # Draw.
        if info.value == 0:
            return 0

        dtm = pliestomate.value

        # White mates.
        if info.value == 1:
            return dtm if board.turn == chess.WHITE else -dtm

        # Black mates.
        if info.value == 2:
            return dtm if board.turn == chess.BLACK else -dtm

    def tb_done(self):
        return self.libgtb.tb_done()

if __name__ == "__main__":
    libgtb = Tablebases()
    syzygy = chess.syzygy.Tablebases("data/syzygy")
    print("tb_init:", libgtb.tb_init(1, 4, ["data/gaviota"]))
    print("tbcache_init:", libgtb.tbcache_init(32 * 1024 * 1024, 96))
    print("---")

    board = chess.Board("8/8/8/8/8/8/8/K2kr3 w - - 0 1")
    while True:
        print(board)
        print("DTM:", libgtb.probe_dtm(board), "DTZ:", syzygy.probe_dtz(board))

        for move in board.legal_moves:
            san = board.san(move)
            board.push(move)
            print(san, libgtb.probe_dtm(board), syzygy.probe_dtz(board))
            board.pop()

        print()
        move = input("Move: ")
        board.push_san(move)

    print("tb_done:", libgtb.tb_done())
