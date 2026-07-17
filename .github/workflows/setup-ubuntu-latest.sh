#!/bin/sh -e

# Refresh the package index: the runner image's baked-in lists can reference
# package versions the mirrors no longer carry (404).
sudo apt-get update

# Stockfish
sudo apt-get install -y stockfish

# Crafty
sudo apt-get install -y crafty

# Fairy-stockfish
sudo apt-get install -y fairy-stockfish

# Gaviota libgtb
git clone https://github.com/michiguel/Gaviota-Tablebases.git --depth 1
cd Gaviota-Tablebases
make
echo "LD_LIBRARY_PATH=`pwd`:${LD_LIBRARY_PATH}" >> $GITHUB_ENV
cd ..
