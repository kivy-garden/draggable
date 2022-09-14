from kivy.properties import ObjectProperty
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout

from kivy_garden.draggable import KXDroppableBehavior, KXDraggableBehavior

KV_CODE = '''
#:import ascii_uppercase string.ascii_uppercase

<Cell>:
    drag_classes: ['card', ]
    canvas.before:
        Color:
            rgba: .1, .1, .1, 1
        Rectangle:
            pos: self.pos
            size: self.size
<Card>:
    drag_cls: 'card'
    drag_timeout: 0
    font_size: 100
    opacity: .3 if self.is_being_dragged else 1.
    canvas.after:
        Color:
            rgba: 1, 1, 1, 1
        Line:
            rectangle: [*self.pos, *self.size, ]
<Deck>:
    canvas.after:
        Color:
            rgba: 1, 1, 1, 1
        Line:
            rectangle: [*self.pos, *self.size, ]

BoxLayout:
    Widget:
        size_hint_x: .1

    # Put the board inside a RelativeLayout just to confirm the coordinates are properly transformed.
    # It's not necessary for this example to work though.
    RelativeLayout:
        GridLayout:
            id: board
            cols: 4
            rows: 4
            spacing: 10
            padding: 10

    BoxLayout:
        orientation: 'vertical'
        size_hint_x: .2
        padding: '20dp', '40dp'
        spacing: '80dp'
        RelativeLayout:  # Put a deck inside a RelativeLayout just ...
            Deck:
                board: board
                text: 'numbers'
                font_size: '20sp'
                text_iter: (str(i) for i in range(10))
        Deck:
            board: board
            text: 'letters'
            font_size: '20sp'
            text_iter: iter(ascii_uppercase)
'''


class Cell(KXDroppableBehavior, FloatLayout):
    def accepts_drag(self, touch, ctx, draggable) -> bool:
        return not self.children

    def add_widget(self, widget, *args, **kwargs):
        widget.size_hint = (1, 1, )
        widget.pos_hint = {'x': 0, 'y': 0, }
        return super().add_widget(widget, *args, **kwargs)


class Card(KXDraggableBehavior, Label):
    pass


class Deck(Label):
    text_iter = ObjectProperty()
    board = ObjectProperty()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.opos):
            if (text := next(self.text_iter, None)) is not None:
                card = Card(text=text, size=self.board.children[0].size)
                card.start_dragging_from_others_touch(self, touch)
            return True


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)

    def on_start(self):
        board = self.root.ids.board
        for __ in range(board.cols * board.rows):
            board.add_widget(Cell())


if __name__ == '__main__':
    SampleApp().run()
