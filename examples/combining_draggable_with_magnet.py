from kivy.app import App
from kivy.lang import Builder
from kivy.factory import Factory
from kivy.clock import Clock
from kivy.properties import (
    NumericProperty, StringProperty, BooleanProperty,
)
import asynckivy as ak

import kivy_garden.draggable


class Magnet(Factory.Widget):
    '''
    Inspired by
    https://github.com/kivy-garden/garden.magnet
    '''
    do_anim = BooleanProperty(True)
    anim_duration = NumericProperty(1)
    anim_transition = StringProperty('out_quad')

    # default value of the instance attributes
    _coro = ak.sleep_forever()

    def __init__(self, **kwargs):
        self._anim_trigger = trigger = Clock.create_trigger(self._start_anim, -1)
        super().__init__(**kwargs)
        self.fbind('pos', trigger)
        self.fbind('size', trigger)

    def add_widget(self, widget, *args, **kwargs):
        if self.children:
            raise ValueError('Magnet can have only one child')
        widget.pos = self.pos
        widget.size = self.size
        return super().add_widget(widget, *args, **kwargs)

    def _start_anim(self, *args):
        if self.children:
            child = self.children[0]
            self._coro.close()
            if not self.do_anim:
                child.pos = self.pos
                child.size = self.size
                return
            self._coro = ak.start(ak.animate(
                child,
                d=self.anim_duration,
                t=self.anim_transition,
                x=self.x, y=self.y, width=self.width, height=self.height,
            ))


KV_CODE = '''
#:import create_spacer kivy_garden.draggable._utils._create_spacer

<ReorderableGridLayout@KXReorderableBehavior+GridLayout>:
<DraggableItem@KXDraggableBehavior+Magnet>:
    do_anim: not self.is_being_dragged
    anim_duration: .2
    drag_cls: 'test'
    drag_timeout: 50
    font_size: 30
    text: ''
    opacity: .5 if self.is_being_dragged else 1.
    size_hint_min: 50, 50
    pos_hint: {'center_x': .5, 'center_y': .5, }
    canvas.after:
        Color:
            rgba: .5, 1, 0, 1 if root.is_being_dragged else .5
        Line:
            width: 2 if root.is_being_dragged else 1
            rectangle: [*self.pos, *self.size, ]
    Label:
        font_size: 30
        text: root.text

<MyButton@Button>:
    font_size: sp(20)
    size_hint_min_x: self.texture_size[0] + dp(10)
    size_hint_min_y: self.texture_size[1] + dp(10)

ReorderableGridLayout:
    spacing: 10
    padding: 10
    drag_classes: ['test', ]
    cols: 6
    spacer_widgets:
        [create_spacer(color=color)
        for color in "#000044 #002200 #440000".split()]
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)

    def on_start(self):
        gl = self.root
        DraggableItem = Factory.DraggableItem
        DraggableItem()
        for i in range(23):
            gl.add_widget(DraggableItem(text=str(i)))


if __name__ == '__main__':
    SampleApp().run()
