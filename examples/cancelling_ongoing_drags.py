'''
An examples of cancelling ongoing drags.
'''

from kivy.app import App
from kivy.lang import Builder
from kivy.factory import Factory

from kivy_garden.draggable import (
    KXDraggableBehavior, restore_widget_location,
)


KV_CODE = '''
<ReorderableGridLayout@KXReorderableBehavior+GridLayout>:
<DraggableItem@KXDraggableBehavior+Label>:
    drag_cls: 'test'
    drag_timeout: 50
    font_size: 30
    opacity: .5 if self.is_being_dragged else 1.
    size_hint_min: 50, 50
    pos_hint: {'center_x': .5, 'center_y': .5, }
    canvas.after:
        Color:
            rgba: .5, 1, 0, 1 if root.is_being_dragged else .5
        Line:
            width: 2 if root.is_being_dragged else 1
            rectangle: [*self.pos, *self.size, ]
<MyButton@Button>:
    font_size: sp(20)
    size_hint_min_x: self.texture_size[0] + dp(10)
    size_hint_min_y: self.texture_size[1] + dp(10)

BoxLayout:
    spacing: 10
    padding: 10
    orientation: 'vertical'
    ReorderableGridLayout:
        id: gl
        spacing: 10
        drag_classes: ['test', ]
        cols: 6
        spacer_widgets:
            [self.create_spacer(color=color)
            for color in "#000044 #002200 #440000".split()]
    BoxLayout:
        spacing: 10
        orientation: 'vertical'
        size_hint_y: None
        height: self.minimum_height
        MyButton:
            text: 'cancel all ongoing drags'
            on_press: app.cancel_ongoing_drags()
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)

    def on_start(self):
        gl = self.root.ids.gl
        DraggableItem = Factory.DraggableItem
        for i in range(23):
            gl.add_widget(DraggableItem(text=str(i)))

    def cancel_ongoing_drags(self):
        # The tuple here is needed for the same reason as you need to
        # duplicate 'children' in the code below.
        #
        # for c in widget.children[:]:
        #     widget.remove_widget(c)
        #
        for draggable in tuple(KXDraggableBehavior.ongoing_drags()):
            draggable.drag_cancel()


if __name__ == '__main__':
    SampleApp().run()
