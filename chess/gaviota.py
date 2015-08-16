#!/usr/bin/python

import ctypes
import ctypes.util
import logging
import chess
import chess.syzygy


class Tablebases(object):
    def __init__(self, directory=None, libgtb=None, LibraryLoader=ctypes.cdll):
        if libgtb is None:
            libgtb = ctypes.util.find_library("gtb")

        self.libgtb = LibraryLoader.LoadLibrary(libgtb)
        self.libgtb.tb_init.restype = ctypes.c_char_p
        self.libgtb.tb_restart.restype = ctypes.c_char_p

        if self.libgtb.tb_is_initialized():
            raise RuntimeError("only one gaviota instance can be initialized at a time")

        self.paths = []
        if directory is not None:
            self.open_directory(directory)

        self._tbcache_restart(1024 * 1024, 50)

    def open_directory(self, directory):
        self.paths.append(directory)
        self._tb_restart()

    def _tb_restart(self):
        c_paths = (ctypes.c_char_p * len(self.paths))()
        c_paths[:] = [bytes(path, "utf-8") for path in self.paths]

        verbosity = ctypes.c_int(1)
        compression_scheme = ctypes.c_int(4)

        ret = self.libgtb.tb_restart(verbosity, compression_scheme, c_paths)
        if ret:
            logging.debug(ret.decode("utf-8"))

    def _tbcache_restart(self, cache_mem, wdl_fraction):
        self.libgtb.tbcache_restart(ctypes.c_size_t(cache_mem), ctypes.c_int(wdl_fraction))

    def probe_dtm(self, board):
        return self._probe_hard(board)

    def probe_wdl(self, board):
        return self._probe_hard(board, wdl_only=True)

    def _probe_hard(self, board, wdl_only=False):
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
        if not wdl_only:
            ret = self.libgtb.tb_probe_hard(stm, ep_square, castling, c_ws, c_bs, c_wp, c_bp, ctypes.byref(info), ctypes.byref(pliestomate))
            dtm = pliestomate.value
        else:
            ret = self.libgtb.tb_probe_WDL_hard(stm, ep_square, castling, c_ws, c_bs, c_wp, c_bp, ctypes.byref(info))
            dtm = 1

        # Probe failed, forbidden or unknown.
        if not ret or info.value == 3 or info.value == 7:
            return None

        # Draw.
        if info.value == 0:
            return 0

        # White mates.
        if info.value == 1:
            return dtm if board.turn == chess.WHITE else -dtm

        # Black mates.
        if info.value == 2:
            return dtm if board.turn == chess.BLACK else -dtm

    def close(self):
        if self.libgtb.tb_is_initialized():
            self.libgtb.tbcache_done()
            self.libgtb.tb_done()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    syzygy = chess.syzygy.Tablebases("data/syzygy")
    gaviota = Tablebases("data/gaviota")

    board = chess.Board("8/8/8/8/8/8/8/K2kr3 w - - 0 1")

    while True:
        print(board)
        print("DTM:", gaviota.probe_dtm(board), "\t|DTZ:", syzygy.probe_dtz(board), "\t|WDL:", gaviota.probe_wdl(board))

        for move in board.legal_moves:
            san = board.san(move)
            board.push(move)
            print(san, gaviota.probe_dtm(board), "\t|", syzygy.probe_dtz(board), "\t|", gaviota.probe_wdl(board))
            board.pop()

        print()
        move = input("Move: ")
        board.push_san(move)

    print("tb_done:", gaviota.tb_done())
