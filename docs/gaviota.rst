Gaviota endgame tablebase probing
=================================

Gaviota tablebases provide **WDL** (win/draw/loss) and **DTM** (depth to mate)
information for all endgame positions with up to 5 pieces. Positions with
castling rights are not included.

.. autofunction:: chess.gaviota.open_tablebases

.. autoclass:: chess.gaviota.PythonTablebases
    :members:

backports.lzma
--------------

For Python versions before 3.3 you have to install ``backports.lzma`` in order
to use the pure Python probing code.

.. code-block:: shell

    sudo apt-get install liblzma-dev libpython2.7-dev
    pip install backports.lzma

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


.. autofunction:: chess.gaviota.open_tablebases_native

.. autoclass:: chess.gaviota.NativeTablebases
    :members:
