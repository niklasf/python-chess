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
    from ipywidgets import Button, GridBox, Layout, HTML, Output
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
            raise NotJupyter("The interactive viewer only runs in jupyter shell")
        return object.__new__(cls)

    def __init__(self, game):
        self.game = game
        self.__board = game.board()
        self.__moves = list(game.mainline_moves())
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
        next_move.on_click(self.__next_click)
        prev_move.on_click(self.__prev_click)
        reset.on_click(self.__reset_click)

        with self.__out:
            grid_box = GridBox(
                children=[next_move, prev_move, reset, self.svg],
                layout=Layout(
                    width="395px",
                    grid_template_rows="90% 10%",
                    grid_template_areas="""
                                "top top top top top"
                                ". left middle right ."
                                """,
                ),
            )
            clear_output()
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
