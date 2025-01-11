#!/usr/bin/env python3

import logging
import sys
import unittest

from . import *

class RaiseLogHandler(logging.StreamHandler):
    def handle(self, record):
        super().handle(record)
        raise RuntimeError("was expecting no log messages")

if __name__ == "__main__":
    verbosity = sum(arg.count("v") for arg in sys.argv if all(c == "v" for c in arg.lstrip("-")))
    verbosity += sys.argv.count("--verbose")

    if verbosity >= 2:
        logging.basicConfig(level=logging.DEBUG)

    raise_log_handler = RaiseLogHandler()
    raise_log_handler.setLevel(logging.ERROR)
    logging.getLogger().addHandler(raise_log_handler)

    unittest.main()
