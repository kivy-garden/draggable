from kivy.utils import reify
from kivy.properties import NumericProperty
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.label import Label
import asynckivy as ak

from kivy_garden.draggable import KXDraggableBehavior, KXDroppableBehavior

KV_CODE = '''
<MyDroppable>:
    text: ''.join(root.drag_classes)
    font_size: 100
    color: 1, .2, 1, .8
    canvas.before:
        Color:
            rgba: 1, 1, 1, self.n_ongoing_drags_inside * 0.12
        Rectangle:
            pos: self.pos
            size: self.size

<MyDraggable>:
    drag_timeout: 0
    font_size: 40
    opacity: .3 if root.is_being_dragged else 1.

<Divider@Widget>:
    canvas:
        Color:
            rgb: 1, 1, 1
        Rectangle:
            pos: self.pos
            size: self.size
<HDivider@Divider>:
    size_hint_y: None
    height: 1
<VDivider@Divider>:
    size_hint_x: None
    width: 1

BoxLayout:
    orientation: 'vertical'
    BoxLayout:
        MyDroppable:
            drag_classes: ['A', ]
        VDivider:
        MyDroppable:
            drag_classes: ['A', 'B', ]
        VDivider:
        MyDroppable:
            drag_classes: ['B', ]
    HDivider:
    BoxLayout:
        MyDraggable:
            drag_cls: 'A'
            text: 'A1'
        MyDraggable:
            drag_cls: 'A'
            text: 'A2'
        MyDraggable:
            drag_cls: 'A'
            text: 'A3'
        MyDraggable:
            drag_cls: 'A'
            text: 'A4'
        MyDraggable:
            drag_cls: 'B'
            text: 'B1'
        MyDraggable:
            drag_cls: 'B'
            text: 'B2'
        MyDraggable:
            drag_cls: 'B'
            text: 'B3'
        MyDraggable:
            drag_cls: 'B'
            text: 'B4'
'''


class MyDraggable(KXDraggableBehavior, Label):
    def on_drag_success(self, touch):
        self.parent.remove_widget(self)


class ReactiveDroppableBehavior(KXDroppableBehavior):
    '''
    ``KXDroppableBehavior`` + leaving/entering events.

    .. note::

        This class probably deserves to be an official component. But not now
        because I'm not sure the word 'reactive' is appropriate to describe
        its behavior.
    '''
    __events__ = ('on_drag_enter', 'on_drag_leave', )

    @reify
    def __ud_key(self):
        return 'ReactiveDroppableBehavior.' + str(self.uid)

    def on_touch_move(self, touch):
        ud_key = self.__ud_key
        touch_ud = touch.ud
        if ud_key not in touch_ud and self.collide_point(*touch.pos):
            drag_cls = touch_ud.get('kivyx_drag_cls', None)
            if drag_cls is not None:
                touch_ud[ud_key] = None
                if drag_cls in self.drag_classes:
                    # Start watching the touch. Use ``ak.or_()`` so that ``_watch_touch()`` will be automatically
                    # cancelled when the drag is cancelled.
                    ak.start(ak.or_(
                        self._watch_touch(touch),
                        ak.event(touch.ud['kivyx_draggable'], 'on_drag_end'),
                    ))
        return super().on_touch_move(touch)

    async def _watch_touch(self, touch):
        draggable = touch.ud['kivyx_draggable']
        collide_point = self.collide_point

        self.dispatch('on_drag_enter', touch, draggable)
        try:
            async for __ in ak.rest_of_touch_moves(self, touch):
                if not collide_point(*touch.pos):
                    return
        finally:
            self.dispatch('on_drag_leave', touch, draggable)
            del touch.ud[self.__ud_key]

    def on_drag_enter(self, touch, draggable):
        pass

    def on_drag_leave(self, touch, draggable):
        pass


class MyDroppable(ReactiveDroppableBehavior, Label):
    n_ongoing_drags_inside = NumericProperty(0)

    def on_drag_enter(self, touch, draggable):
        self.n_ongoing_drags_inside += 1
        print(f"{draggable.text} entered {self.text}.")

    def on_drag_leave(self, touch, draggable):
        self.n_ongoing_drags_inside -= 1
        print(f"{draggable.text} left {self.text}.")


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)


if __name__ == '__main__':
    SampleApp().run()
