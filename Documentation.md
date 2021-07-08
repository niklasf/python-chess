# Introduction
python-chess is library for Python , help developer to create a chess game applications , it is contain tow playing mode : user mode and bot mode , and there is a lot of useful method to organize strong game

# Installing 
- using pip
    - `pip install chess`
- using git 
    - `git clone https://github.com/HamzhSuilik/python-chess.git`
- using npm
    `npm install chess`


# Requirements
- Supports Python 3.7+. Includes mypy typings.

# starting with chess library
- importing chess library 
    - first check that chess is already installed : `chess --version`
    - `import chess`
- create Board object :
    - `board = chess.Board()`
- then you can check the Board method to start playing

# Board methods 
- legal_moves() : A dynamic list of legal moves.
- pseudo_legal_moves : A dynamic list of pseudo-legal moves, much like the legal move list
- reset : Restores the starting position.
- reset_board : Resets only pieces to the starting position
    def clear(self) -> None:
- clear : Clears the board.
- ply : Returns the number of half-moves since the start of the game
- is_variant_end : Checks if the game is over due to a special variant end condition.
- is_variant_loss : Checks if the current side to move won due to a variant-specific condition.
- is_variant_draw : Checks if a variant-specific drawing condition is fulfilled
- is_checkmate : Checks if the current position is a checkmate.
- is_stalemate : Checks if the current position is a stalemate.
- is_insufficient_material : Checks if neither side has sufficient winning material
- has_insufficient_material : 
- can_claim_draw : Checks if the player to move can claim a draw by the fifty-move rule or by threefold repetition
- can_claim_fifty_moves :  Checks if the player to move can claim a draw by the fifty-move rule 
- is_repetition : Checks if the current position has repeated 3 (or a given number of) times.
- find_move : Finds a matching legal move for an origin square, a target square, and an optional promotion piece type

# How To Contribute
- Fork the project
- Create a new topic branch on your local forked copy
- Push your topic branch up to your fork
- Create a pen demonstrating what your change will do.
- Open a Pull Request with a clear title and description against the main branch.
