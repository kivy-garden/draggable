'''
This example shows how to achive the same functionality as Flutter one's
'child', 'feedback' and 'childWhenDragging'.
https://api.flutter.dev/flutter/widgets/Draggable-class.html
'''

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import ScreenManager, NoTransition

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
    # current: 'feedback' if self.is_being_dragged else 'child'
    Screen:
        name: 'child'
        Label:
            text: 'child'
            bold: True
    Screen:
        name: 'childWhenDragging'
        Label:
            text: 'childWhenDragging'
            bold: True
            color: 1, 0, 1, 1
    Screen:
        name: 'feedback'
        Label:
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


class FlutterStyleDraggable(KXDraggableBehavior, ScreenManager):
    def on_kv_post(self, *args, **kwargs):
        super().on_kv_post(*args, **kwargs)
        self.transition = NoTransition()
        self.current = 'child'
        self.fbind('is_being_dragged', FlutterStyleDraggable.__on_is_being_dragged)

    def __on_is_being_dragged(self, value):
        self.current = 'feedback' if value else 'child'

    def on_drag_start(self, touch, ctx):
        if self.has_screen('childWhenDragging'):
            restore_widget_state(
                self.get_screen('childWhenDragging'),
                ctx.original_state,
            )
        return super().on_drag_start(touch, ctx)

    def on_drag_fail(self, touch, ctx):
        if self.has_screen('childWhenDragging'):
            w = self.get_screen('childWhenDragging')
            if w.parent is not None:
                w.parent.remove_widget(w)
        return super().on_drag_fail(touch, ctx)

    def on_drag_succeed(self, touch, ctx):
        if self.has_screen('childWhenDragging'):
            w = self.get_screen('childWhenDragging')
            if w.parent is not None:
                w.parent.remove_widget(w)
        return super().on_drag_succeed(touch, ctx)


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
