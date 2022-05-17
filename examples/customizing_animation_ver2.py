'''Alternative version of 'customizing_animation.py'. This one adds graphics instructions only while they're needed,
requires less bindings. Thus probably more efficient.
'''


from kivy.app import runTouchApp
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

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
        from kivy.graphics import PushMatrix, PopMatrix, Rotate
        import asynckivy as ak
        push_mat = PushMatrix()
        rotate = Rotate(origin=self.center)
        pop_mat = PopMatrix()
        cb = self.canvas.before
        ca = self.canvas.after
        try:
            cb.add(push_mat)
            cb.add(rotate)
            ca.add(pop_mat)
            await ak.and_(
                ak.animate(rotate, d=.4, angle=720.),
                ak.animate(self, d=.4, opacity=0.),
            )
            self.parent.remove_widget(self)
        finally:
            cb.remove(push_mat)
            cb.remove(rotate)
            ca.remove(pop_mat)

    async def on_drag_succeed(self, touch, ctx):
        from kivy.graphics import PushMatrix, PopMatrix, Scale
        import asynckivy as ak
        push_mat = PushMatrix()
        scale = Scale()
        pop_mat = PopMatrix()
        cb = self.canvas.before
        ca = self.canvas.after
        try:
            cb.add(push_mat)
            cb.add(scale)
            ca.add(pop_mat)
            self.parent.remove_widget(self)
            ctx.droppable.add_widget(self)
            await ak.sleep(0)  # wait for the layout to complete
            scale.origin = self.center
            await ak.animate(scale, d=.1, x=.6, y=.6)
            await ak.animate(scale, d=.1, x=1., y=1.)
        finally:
            cb.remove(push_mat)
            cb.remove(scale)
            ca.remove(pop_mat)


class Cell(KXDroppableBehavior, FloatLayout):
    def accepts_drag(self, touch, ctx, draggable) -> bool:
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
