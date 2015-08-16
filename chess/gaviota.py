#!/usr/bin/python

import ctypes
import ctypes.util
import chess

class Libgtb(object):
    def __init__(self, libname="libgtb.so.1.0.1"):
        self.lib = ctypes.cdll.LoadLibrary(libname)
        self.libc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("c"))

        #self.lib.tb_init.argtypes = [
        #    ctypes.c_int,
        #    ctypes.c_int,
        #    ctypes.POINTER(ctypes.POINTER(ctypes.c_char))]
        #self.lib.tb_init.rettype = ctypes.POINTER(ctypes.c_char)

        self.lib.tb_init.restype = ctypes.c_char_p

    def tb_init(self, verbosity, compression_scheme, paths):
        """
        verbosity - 0 non-verbose, 1 verbose
        scheme    - for example tb_CP4
        """
        c_paths = (ctypes.c_char_p * len(paths))()
        c_paths[:] = [bytes(path, "utf-8") for path in paths]

        ret = self.lib.tb_init(
                ctypes.c_int(verbosity),
                ctypes.c_int(compression_scheme),
                ctypes.byref(c_paths))

        return str(ret.decode("utf-8"))

    def tbcache_init(self, cache_mem, wdl_fraction):
        return self.lib.tbcache_init(ctypes.c_size_t(cache_mem), ctypes.c_int(wdl_fraction))

    def tb_probe_hard(self, board):
        stm = ctypes.c_uint(0 if board.turn == chess.WHITE else 1)
        epsquare = ctypes.c_uint(board.ep_square if board.ep_square else 64)
        assert board.castling_rights == 0 # XXX
        castling = ctypes.c_uint(0)

        c_ws = (ctypes.c_uint * 17)()
        c_ws[0] = chess.A1
        c_ws[1] = chess.B1
        c_ws[2] = 64

        c_wp = (ctypes.c_ubyte * 17)()
        c_wp[0] = chess.KING
        c_wp[1] = chess.ROOK
        c_wp[2] = chess.NONE

        c_bs = (ctypes.c_uint * 17)()
        c_bs[0] = chess.E5
        c_bs[1] = 64

        c_bp = (ctypes.c_ubyte * 17)()
        c_bp[0] = chess.KING
        c_bp[1] = chess.NONE

        info = ctypes.c_uint()
        pliestomate = ctypes.c_uint()

        ret = self.lib.tb_probe_hard(stm, epsquare, castling, c_ws, c_bs, c_wp, c_bp, ctypes.byref(info), ctypes.byref(pliestomate))

        print("info: ", info)
        print("pliestomate: ", pliestomate)
        return ret

    def tb_done(self):
        return self.lib.tb_done()

if __name__ == "__main__":
    libgtb = Libgtb()
    print("tb_init: ", libgtb.tb_init(1, 4, ["data/gaviota"]))
    print("tbcache_init: ", libgtb.tbcache_init(32 * 1024 * 1024, 96))

    board = chess.Board("8/8/8/8/8/8/8/K2kr3 w - - 0 1")
    print(board)
    print("tb_probe_hard: ", libgtb.tb_probe_hard(board))

    #print("tb_done: ", libgtb.tb_done())

    libgtb2 = Libgtb()
    print("tb_probe_hard2: ", libgtb2.tb_probe_hard(board))

# tb_init(int verbosity, int compression_scheme, const char **paths)

# tb_done()
