#!/usr/bin/env bash
set -euo pipefail

# Stockfish, Crafty, Fairy-Stockfish
sudo apt-get update
sudo apt-get install -y --no-install-recommends stockfish crafty fairy-stockfish

# Sanity check, because the test suite silently skips missing engines
command -v stockfish crafty fairy-stockfish

# Gaviota libgtb
GAVIOTA_REV=981472cc83e3a8b6e996191e564295609ea4ce30
git init -q Gaviota-Tablebases
git -C Gaviota-Tablebases fetch -q --depth 1 https://github.com/michiguel/Gaviota-Tablebases.git "$GAVIOTA_REV"
git -C Gaviota-Tablebases checkout -q FETCH_HEAD
make -C Gaviota-Tablebases
echo "LD_LIBRARY_PATH=$PWD/Gaviota-Tablebases${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" >> "$GITHUB_ENV"
