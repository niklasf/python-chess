#!/bin/sh -e

echo Download ...
choco install wget
wget https://github.com/official-stockfish/Stockfish/releases/download/sf_16/stockfish-windows-x86-64-avx2.zip

echo Unzip ..
7z e stockfish-windows-x86-64-avx2.zip stockfish/stockfish-windows-x86-64-avx2.exe

echo Setup path ...
mv stockfish-windows-x86-64-avx2.exe stockfish.exe
pwd >> $GITHUB_PATH
