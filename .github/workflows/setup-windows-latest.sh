#!/bin/sh -e

wget https://stockfishchess.org/files/stockfish-11-win.zip
unzip stockfish-11-win.zip
mv stockfish-11-win/Windows/stockfish_20011801_x64_bmi2.exe stockfish.exe
pwd >> $GITHUB_PATH
