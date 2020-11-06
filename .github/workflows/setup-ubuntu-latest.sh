#!/bin/sh -e

# Stockfish
wget https://stockfish.s3.amazonaws.com/stockfish-11-linux.zip
unzip stockfish-11-linux.zip
mkdir -p bin
cp stockfish-11-linux/Linux/stockfish_20011801_x64_bmi2 bin/stockfish
chmod +x bin/stockfish
echo "`pwd`/bin" >> $GITHUB_PATH

# Crafty
git clone https://github.com/lazydroid/crafty-chess --depth 1
cd crafty-chess
make unix-gcc
pwd >> $GITHUB_PATH
cd ..

# Gaviota libgtb
git clone https://github.com/michiguel/Gaviota-Tablebases.git --depth 1
cd Gaviota-Tablebases
make
echo "LD_LIBRARY_PATH=`pwd`:${LD_LIBRARY_PATH}" >> $GITHUB_ENV
cd ..
