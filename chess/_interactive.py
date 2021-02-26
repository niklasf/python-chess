# TODO: Fix typing in this file.
# mypy: ignore-errors

import chess.svg


class WidgetError(Exception):
    """
    raised when ipywidgets is not installed
    """


class NotJupyter(Exception):
    """
    raised when InteractiveViewer is instantiated from a non jupyter shell
    """


try:
    from ipywidgets import Button, GridBox, Layout, HTML, Output, HBox, Select
    from IPython.display import display, clear_output
except ModuleNotFoundError:
    raise WidgetError("You need to have ipywidgets installed and running from Jupyter")


class InteractiveViewer:
    def __new__(cls, game):
        jupyter = True
        try:
            if get_ipython().__class__.__name__ != "ZMQInteractiveShell":
                jupyter = False
        except NameError:
            jupyter = False

        if not jupyter:
            raise NotJupyter("The interactive viewer only runs in Jupyter shell")

        return object.__new__(cls)

    def __init__(self, game):
        self.game = game
        self.__board = game.board()
        self.__moves = list(game.mainline_moves())
        self.__white_moves = [str(move) for (i, move) in enumerate(self.__moves) if i % 2 == 0]
        self.__black_moves = [str(move) for (i, move) in enumerate(self.__moves) if i % 2 == 1]
        self.__move_list_len = len(self.__white_moves)
        self.__num_moves = len(self.__moves)
        self.__next_move = 0 if self.__moves else None
        self.__out = Output()

    def __next_click(self, _):
        move = self.__moves[self.__next_move]
        self.__next_move += 1
        self.__board.push(move)
        self.show()

    def __prev_click(self, _):
        self.__board.pop()
        self.__next_move -= 1
        self.show()

    def __reset_click(self, _):
        self.__board.reset()
        self.__next_move = 0
        self.show()

    def __white_select_change(self, change):
        new = change["new"]
        if (isinstance(new, dict)) and ("index" in new):
            target = new["index"] * 2
            self.__seek(target)
            self.show()

    def __black_select_change(self, change):
        new = change["new"]
        if (isinstance(new, dict)) and ("index" in new):
            target = new["index"] * 2 + 1
            self.__seek(target)
            self.show()

    def __seek(self, target):
        while self.__next_move <= target:
            move = self.__moves[self.__next_move]
            self.__next_move += 1
            self.__board.push(move)

        while self.__next_move > target + 1:
            self.__board.pop()
            self.__next_move -= 1

    def show(self):
        display(self.__out)
        next_move = Button(
            icon="step-forward",
            layout=Layout(width="60px", grid_area="right"),
            disabled=self.__next_move >= self.__num_moves,
        )

        prev_move = Button(
            icon="step-backward",
            layout=Layout(width="60px", grid_area="left"),
            disabled=self.__next_move == 0,
        )

        reset = Button(
            icon="stop",
            layout=Layout(width="60px", grid_area="middle"),
            disabled=self.__next_move == 0,
        )

        if self.__next_move == 0:
            white_move = None
            black_move = None
        else:
            white_move = (
                self.__white_moves[self.__next_move // 2]
                if (self.__next_move % 2) == 1
                else None
            )
            black_move = (
                self.__black_moves[self.__next_move // 2 - 1]
                if (self.__next_move % 2) == 0
                else None
            )

        white_move_list = Select(
            options=self.__white_moves,
            value=white_move,
            rows=max(self.__move_list_len, 24),
            disabled=False,
            layout=Layout(width="80px"),
        )

        black_move_list = Select(
            options=self.__black_moves,
            value=black_move,
            rows=max(self.__move_list_len, 24),
            disabled=False,
            layout=Layout(width="80px"),
        )

        white_move_list.observe(self.__white_select_change)
        black_move_list.observe(self.__black_select_change)

        move_number_width = 3 + len(str(self.__move_list_len)) * 10

        move_number = Select(
            options=range(1, self.__move_list_len + 1),
            value=None,
            disabled=True,
            rows=max(self.__move_list_len, 24),
            layout=Layout(width=f"{move_number_width}px"),
        )

        move_list = HBox(
            [move_number, white_move_list, black_move_list],
            layout=Layout(height="407px", grid_area="moves"),
        )

        next_move.on_click(self.__next_click)
        prev_move.on_click(self.__prev_click)
        reset.on_click(self.__reset_click)

        with self.__out:
            grid_box = GridBox(
                children=[next_move, prev_move, reset, self.svg, move_list],
                layout=Layout(
                    width=f"{390+move_number_width+160}px",
                    grid_template_rows="90% 10%",
                    grid_template_areas="""
                                "top top top top top moves"
                                ". left middle right . moves"
                                """,
                ),
            )
            clear_output(wait=True)
            display(grid_box)

    @property
    def svg(self) -> HTML:
        svg = chess.svg.board(
            board=self.__board,
            size=390,
            lastmove=self.__board.peek() if self.__board.move_stack else None,
            check=self.__board.king(self.__board.turn)
            if self.__board.is_check()
            else None,
        )
        svg_widget = HTML(value=svg, layout=Layout(grid_area="top"))
        return svg_widget
