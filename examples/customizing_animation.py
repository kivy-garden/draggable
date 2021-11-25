'''This example shows how to customize animations by overwriting
``on_drag_fail()`` and ``on_drag_success()``.
'''


from kivy.app import runTouchApp
from kivy.lang import Builder
from kivy.properties import NumericProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
import asynckivy as ak

from kivy_garden.draggable import KXDroppableBehavior, KXDraggableBehavior

KV_CODE = '''
<Cell>:
    drag_classes: ['test', ]
    canvas.before:
        Color:
            rgba: .1, .1, .1, 1
        Rectangle:
            pos: self.pos
            size: self.size

<MyDraggable>:
    drag_cls: 'test'
    drag_timeout: 0
    font_size: 50
    canvas.before:
        Color:
            rgba: .4, 1, .2, 1 if self.is_being_dragged else 0
        Line:
            width: 2
            rectangle: [*self.pos, *self.size, ]
        PushMatrix:
        Rotate:
            origin: self.center
            angle: self._angle
        Scale:
            origin: self.center
            xyz: self._scale, self._scale, 1.
    canvas.after:
        PopMatrix:

GridLayout:
    id: board
    cols: 3
    rows: 3
    spacing: 20
    padding: 20
'''


class MyDraggable(KXDraggableBehavior, Label):
    _angle = NumericProperty()
    _scale = NumericProperty(1.)

    async def on_drag_fail(self, touch):
        await ak.animate(self, d=.4, _angle=720, opacity=0)
        self.parent.remove_widget(self)

    async def on_drag_success(self, touch):
        ctx = self.drag_context
        self.parent.remove_widget(self)
        ctx.droppable.add_widget(self)
        await ak.animate(self, d=.1, _scale=.6)
        await ak.animate(self, d=.1, _scale=1)


class Cell(KXDroppableBehavior, FloatLayout):
    def accepts_drag(self, touch, draggable) -> bool:
        return not self.children

    def add_widget(self, widget, *args, **kwargs):
        widget.size_hint = (1, 1, )
        widget.pos_hint = {'x': 0, 'y': 0, }
        return super().add_widget(widget, *args, **kwargs)


root = Builder.load_string(KV_CODE)
board = root
for __ in range(board.cols * board.rows):
    board.add_widget(Cell())
cells = board.children
for cell, i in zip(cells, range(4)):
    cell.add_widget(MyDraggable(text=str(i)))

runTouchApp(root)
