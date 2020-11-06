#!/bin/sh -e

echo Download ...
choco install wget
wget https://stockfishchess.org/files/stockfish-11-win.zip

echo Unzip ..
7z e stockfish-11-win.zip stockfish-11-win/Windows/*.exe

echo Setup path ...
mv stockfish_20011801_x64_bmi2.exe stockfish.exe
pwd >> $GITHUB_PATH
