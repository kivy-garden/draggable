'''Alternative version of 'customizing_animation.py'. This one adds graphics instructions only while they're needed,
requires less bindings, thus probably more efficient.
'''

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.graphics import Rotate, Scale

import asynckivy as ak
from asynckivy import vanim
from asynckivy.utils import transform

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

GridLayout:
    id: board
    cols: 3
    rows: 3
    spacing: 20
    padding: 20
'''


class MyDraggable(KXDraggableBehavior, Label):
    async def on_drag_fail(self, touch, ctx):
        with transform(self) as ig:
            ig.add(rotate := Rotate(origin=self.center))
            async for p in vanim.progress(duration=.4):
                rotate.angle = p * 720.
                self.opacity = 1. - p
            self.parent.remove_widget(self)

    async def on_drag_succeed(self, touch, ctx):
        self.parent.remove_widget(self)
        ctx.droppable.add_widget(self)
        await ak.sleep(0)  # wait for the layout to complete
        abs_ = abs
        with transform(self) as ig:
            ig.add(scale := Scale(origin=self.center))
            async for p in vanim.progress(duration=.2):
                scale.x = scale.y = abs_(p * .8 - .4) + .6


class Cell(KXDroppableBehavior, FloatLayout):
    def accepts_drag(self, touch, ctx, draggable) -> bool:
        return not self.children

    def add_widget(self, widget, *args, **kwargs):
        widget.size_hint = (1, 1, )
        widget.pos_hint = {'x': 0, 'y': 0, }
        return super().add_widget(widget, *args, **kwargs)


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)

    def on_start(self):
        board = self.root
        for __ in range(board.cols * board.rows):
            board.add_widget(Cell())
        cells = board.children
        for cell, i in zip(cells, range(4)):
            cell.add_widget(MyDraggable(text=str(i)))


if __name__ == '__main__':
    SampleApp().run()
