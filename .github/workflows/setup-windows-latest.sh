#!/bin/sh -e

echo Download stockfish ...
choco install wget
wget https://github.com/official-stockfish/Stockfish/releases/download/sf_16/stockfish-windows-x86-64-avx2.zip

echo Unzip ..
7z e stockfish-windows-x86-64-avx2.zip stockfish/stockfish-windows-x86-64-avx2.exe

echo Setup path ...
mv stockfish-windows-x86-64-avx2.exe stockfish.exe
pwd >> $GITHUB_PATH

echo Download fairy-stockfish ...
wget https://github.com/fairy-stockfish/Fairy-Stockfish/releases/latest/download/fairy-stockfish-largeboard_x86-64.exe
mv fairy-stockfish-largeboard_x86-64.exe fairy-stockfish.exe
