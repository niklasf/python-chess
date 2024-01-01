#!/bin/sh -e

# Stockfish
sudo apt-get install -y stockfish

# Crafty
sudo apt-get install -y crafty

# Gaviota libgtb
git clone https://github.com/michiguel/Gaviota-Tablebases.git --depth 1
cd Gaviota-Tablebases
make
echo "LD_LIBRARY_PATH=`pwd`:${LD_LIBRARY_PATH}" >> $GITHUB_ENV
cd ..
