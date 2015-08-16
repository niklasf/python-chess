#!/usr/bin/python

import ctypes
import ctypes.util
import chess

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

    def tb_probe_hard(self, board):
        stm = ctypes.c_uint(0 if board.turn == chess.WHITE else 1)
        epsquare = ctypes.c_uint(board.ep_square if board.ep_square else 64)
        assert board.castling_rights == 0 # XXX
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

        info = ctypes.c_uint()
        pliestomate = ctypes.c_uint()

        ret = self.libgtb.tb_probe_hard(stm, epsquare, castling, c_ws, c_bs, c_wp, c_bp, ctypes.byref(info), ctypes.byref(pliestomate))

        print("info:", info)
        print("pliestomate:", pliestomate)
        return ret

    def tb_done(self):
        return self.libgtb.tb_done()

if __name__ == "__main__":
    libgtb = Tablebases()
    print("tb_init: ", libgtb.tb_init(1, 4, ["data/gaviota"]))
    print("tbcache_init: ", libgtb.tbcache_init(32 * 1024 * 1024, 96))

    board = chess.Board("8/8/8/8/8/8/8/K2kr3 w - - 0 1")
    print(board)
    print("tb_probe_hard: ", libgtb.tb_probe_hard(board))

    print("tb_done:", libgtb.tb_done())
