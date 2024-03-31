'''
This example shows how to achieve the same functionality as Flutter one's
'child', 'feedback' and 'childWhenDragging'.
https://api.flutter.dev/flutter/widgets/Draggable-class.html
'''

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout

from kivy_garden.draggable import KXDroppableBehavior, KXDraggableBehavior, restore_widget_state

KV_CODE = '''
<Cell>:
    drag_classes: ['test', ]
    canvas.before:
        Color:
            rgba: .1, .1, .1, 1
        Rectangle:
            pos: self.pos
            size: self.size

<FlutterStyleDraggable>:
    drag_cls: 'test'
    drag_timeout: 0
    Label:
        id: child
        text: 'child'
        bold: True
    Label:
        id: childWhenDragging
        text: 'childWhenDragging'
        bold: True
        color: 1, 0, 1, 1
    Label:
        id: feedback
        text: 'feedback'
        bold: True
        color: 1, 1, 0, 1

GridLayout:
    id: board
    cols: 4
    rows: 4
    spacing: 10
    padding: 10
'''


class FlutterStyleDraggable(KXDraggableBehavior, RelativeLayout):

    def on_kv_post(self, *args, **kwargs):
        super().on_kv_post(*args, **kwargs)
        self._widgets = ws = {
            name: self.ids[name].__self__
            for name in ('child', 'childWhenDragging', 'feedback', )
        }
        self.clear_widgets()
        self.add_widget(ws['child'])

    def on_drag_start(self, touch, ctx):
        ws = self._widgets
        self.remove_widget(ws['child'])
        self.add_widget(ws['feedback'])
        restore_widget_state(ws['childWhenDragging'], ctx.original_state)
        return super().on_drag_start(touch, ctx)

    def on_drag_end(self, touch, ctx):
        ws = self._widgets
        w = ws['childWhenDragging']
        w.parent.remove_widget(w)
        self.remove_widget(ws['feedback'])
        self.add_widget(ws['child'])
        return super().on_drag_end(touch, ctx)


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
        for cell, __ in zip(cells, range(4)):
            cell.add_widget(FlutterStyleDraggable())


if __name__ == '__main__':
    SampleApp().run()
