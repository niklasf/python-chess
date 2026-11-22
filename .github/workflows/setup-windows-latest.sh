#!/usr/bin/env bash
set -euo pipefail

download() {
    # Usage: download URL OUTPUT SHA256
    curl -fsSL --retry 3 -o "$2" "$1"
    echo "$3  $2" | sha256sum -c -
}

echo "::group::Stockfish"
download https://github.com/official-stockfish/Stockfish/releases/download/sf_19/stockfish-windows-x86-64-universal.zip \
    stockfish.zip 3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7
7z e -y stockfish.zip stockfish/stockfish-windows-x86-64-universal.exe
mv stockfish-windows-x86-64-universal.exe stockfish.exe
rm stockfish.zip
echo "::endgroup::"

echo "::group::Fairy-Stockfish"
download https://github.com/fairy-stockfish/Fairy-Stockfish/releases/download/fairy_sf_14/fairy-stockfish-largeboard_x86-64.exe \
    fairy-stockfish.exe 2fe12ff0fcad0295482cab7660e1fcc24259cebc4ef164839fb16c9f9cabfc99
echo "::endgroup::"

# Sanity check, because the test suite silently skips missing engines
echo quit | ./stockfish.exe
echo quit | ./fairy-stockfish.exe

cygpath -w "$PWD" >> "$GITHUB_PATH"
