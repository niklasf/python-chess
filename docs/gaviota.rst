Gaviota endgame tablebase probing
=================================

Gaviota tablebases provide **WDL** (win/draw/loss) and **DTM** (depth to mate)
information for all endgame positions with up to 5 pieces. Positions with
castling rights are not included.

.. warning::
    Ensure tablebase files match the known checksums. Maliciously crafted
    tablebase files may cause denial of service with
    :class:`~chess.gaviota.PythonTablebase` and memory unsafety with
    :class:`~chess.gaviota.NativeTablebase`.

.. autofunction:: chess.gaviota.open_tablebase

.. autoclass:: chess.gaviota.PythonTablebase
    :members:

libgtb
------

For faster access you can build and install
a `shared library <https://github.com/michiguel/Gaviota-Tablebases>`_.
Otherwise the pure Python probing code is used.

.. code-block:: shell

    git clone https://github.com/michiguel/Gaviota-Tablebases.git
    cd Gaviota-Tablebases
    make
    sudo make install


.. autofunction:: chess.gaviota.open_tablebase_native

.. autoclass:: chess.gaviota.NativeTablebase
    :members:
