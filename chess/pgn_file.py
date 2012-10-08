class PgnFile(object):
    def __init__(self):
        self._games = []

    def add_game(self, game):
        self._games.append(game)

    @classmethod
    def open(cls, path):
        tag_regex = re.compile("\\[([A-Za-z0-9]+)\\s+\"(.*)\"\\]")

        pgn_file = PgnFile()
        current_game = None
        in_tags = False

        for line in open(path, 'r'):
            # Decode and strip the line.
            line = line.decode('latin-1').strip()

            # Skip empty lines and comments.
            if not line or line.startswith("%"):
                continue

            # Check for tag lines.
            tag_match = tag_regex.match(line)
            if tag_match:
                tag_name = tag_match.group(1)
                tag_value = tag_match.group(2).replace("\\\\", "\\").replace("\\[", "]").replace("\\\"", "\"")
                if current_game:
                    if in_tags:
                        current_game.set_header(tag_name, tag_value)
                    else:
                        pgn_file.add_game(current_game)
                        current_game = None
                if not current_game:
                    current_game = chess.Game()
                    current_game.set_header(tag_name, tag_value)
            # Parse movetext lines.
            else:
                if current_game:
                    # TODO: Parse the actual movetext.
                else:
                    raise PgnError("Invalid PGN. Expected header before movetext: %s", repr(line))

        if current_game:
            pgn_file.add_game(current_game)

        return pgn_file
