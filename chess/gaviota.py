# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2012-2015 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import ctypes
import ctypes.util
import os.path
import logging
import chess


class NativeTablebases(object):
    """Provides access to Gaviota tablebases via the shared library libgtb."""

    def __init__(self, directory, libgtb):
        self.libgtb = libgtb
        self.libgtb.tb_init.restype = ctypes.c_char_p
        self.libgtb.tb_restart.restype = ctypes.c_char_p
        self.libgtb.tbpaths_getmain.restype = ctypes.c_char_p
        self.libgtb.tb_probe_hard.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_ubyte), ctypes.POINTER(ctypes.c_ubyte), ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint)]

        if self.libgtb.tb_is_initialized():
            raise RuntimeError("only one gaviota instance can be initialized at a time")

        self.paths = []
        if directory is not None:
            self.open_directory(directory)

        self._tbcache_restart(1024 * 1024, 50)

    def open_directory(self, directory):
        """Loads *.gtb.cp4* tables from a directory."""
        if not os.path.isdir(directory):
            raise IOError("not a tablebase directory: {0}".format(repr(directory)))

        self.paths.append(directory)
        self._tb_restart()

    def _tb_restart(self):
        self.c_paths = (ctypes.c_char_p * len(self.paths))()
        self.c_paths[:] = [path.encode("utf-8") for path in self.paths]

        verbosity = ctypes.c_int(1)
        compression_scheme = ctypes.c_int(4)

        ret = self.libgtb.tb_restart(verbosity, compression_scheme, self.c_paths)
        if ret:
            logging.debug(ret.decode("utf-8"))

        logging.debug("Main path has been set to %s", self.libgtb.tbpaths_getmain().decode("utf-8"))

        av = self.libgtb.tb_availability()
        if av & 1:
            logging.debug("Some 3 piece tablebases available")
        if av & 2:
            logging.debug("All 3 piece tablebases complete")
        if av & 4:
            logging.debug("Some 4 piece tablebases available")
        if av & 8:
            logging.debug("All 4 piece tablebases complete")
        if av & 16:
            logging.debug("Some 5 piece tablebases available")
        if av & 32:
            logging.debug("All 5 piece tablebases complete")

    def _tbcache_restart(self, cache_mem, wdl_fraction):
        self.libgtb.tbcache_restart(ctypes.c_size_t(cache_mem), ctypes.c_int(wdl_fraction))

    def probe_dtm(self, board):
        """
        Probes for depth to mate information.

        Returns ``None`` if the position was not found in any of the tables.

        Otherwise the absolute value is the number of half moves until
        forced mate. The value is positive if the side to move is winning,
        otherwise it is negative.

        In the example position white to move will get mated in 10 half moves:

        >>> with chess.gaviota.open_tablebases("data/gaviota") as tablebases:
        ...     tablebases.probe_dtm(chess.Board("8/8/8/8/8/8/8/K2kr3 w - - 0 1"))
        ...
        -10
        """
        return self._probe_hard(board)

    def probe_wdl(self, board):
        """
        Probes for win/draw/loss-information.

        Returns ``None`` if the position was not found in any of the tables.

        Returns ``1`` if the side to move is winning, ``0`` if it is a draw,
        and ``-1`` if the side to move is losing.

        >>> with chess.gaviota.open_tablebases("data/gaviota") as tablebases:
        ...     tablebases.probe_wdl(chess.Board("4k3/8/B7/8/8/8/4K3 w - 0 1"))
        ...
        0
        """
        return self._probe_hard(board, wdl_only=True)

    def _probe_hard(self, board, wdl_only=False):
        if chess.pop_count(board.occupied_co[chess.WHITE]) > 16:
            return None
        if chess.pop_count(board.occupied_co[chess.BLACK]) > 16:
            return None

        if board.is_insufficient_material():
            return 0

        if board.castling_rights:
            return None

        stm = ctypes.c_uint(0 if board.turn == chess.WHITE else 1)
        ep_square = ctypes.c_uint(board.ep_square if board.ep_square else 64)
        castling = ctypes.c_uint(0)

        c_ws = (ctypes.c_uint * 17)()
        c_wp = (ctypes.c_ubyte * 17)()

        i = -1
        for i, square in enumerate(chess.SquareSet(board.occupied_co[chess.WHITE])):
            c_ws[i] = square
            c_wp[i] = board.piece_type_at(square)

        c_ws[i + 1] = 64
        c_wp[i + 1] = 0

        c_bs = (ctypes.c_uint * 17)()
        c_bp = (ctypes.c_ubyte * 17)()

        i = -1
        for i, square in enumerate(chess.SquareSet(board.occupied_co[chess.BLACK])):
            c_bs[i] = square
            c_bp[i] = board.piece_type_at(square)

        c_bs[i + 1] = 64
        c_bp[i + 1] = 0

        # Do a hard probe.
        info = ctypes.c_uint()
        pliestomate = ctypes.c_uint()
        if not wdl_only:
            ret = self.libgtb.tb_probe_hard(stm, ep_square, castling, c_ws, c_bs, c_wp, c_bp, ctypes.byref(info), ctypes.byref(pliestomate))
            dtm = int(pliestomate.value)
        else:
            ret = self.libgtb.tb_probe_WDL_hard(stm, ep_square, castling, c_ws, c_bs, c_wp, c_bp, ctypes.byref(info))
            dtm = 1

        # Probe forbidden.
        if info.value == 3:
            logging.warning("Tablebase for %s marked as forbidden", board.fen())
            return None

        # Probe failed or unknown.
        if not ret or info.value == 7:
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
        """Closes all loaded tables and clears all caches."""
        if self.libgtb.tb_is_initialized():
            self.libgtb.tbcache_done()
            self.libgtb.tb_done()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def open_tablebases(directory=None, libgtb=None, LibraryLoader=ctypes.cdll):
    """
    Opens a collection of tablebases for probing.

    Currently the only access method is via the shared library libgtb.
    You can optionally provide a specific library name or a library loader.
    The shared library has global state and caches, so only one instance can
    be open at a time.
    """
    if LibraryLoader:
        libgtb = libgtb or ctypes.util.find_library("gtb") or "libgtb.so.1.0.1"
        return NativeTablebases(directory, LibraryLoader.LoadLibrary(libgtb))
    else:
        raise RuntimeError("need a library loader for libgtb")
