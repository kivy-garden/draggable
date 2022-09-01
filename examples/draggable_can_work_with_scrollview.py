'''
Nothing special. Just an example of re-orderable BoxLayout.
'''

from kivy.app import App
from kivy.lang import Builder
from kivy.factory import Factory
import kivy_garden.draggable

KV_CODE = '''
#:import Label kivy.uix.label.Label

<DraggableItem@KXDraggableBehavior+Button>:
    drag_cls: 'test'
    opacity: .5 if self.is_being_dragged else 1.
    size_hint_min_y: sp(50)
    canvas.after:
        Color:
            rgba: 0, 1, 0, 1 if root.is_being_dragged else 0
        Line:
            width: 2
            rectangle: [*self.pos, *self.size, ]

<ReorderableBoxLayout@KXReorderableBehavior+BoxLayout>:

ScrollView:
    do_scroll_x: False
    ReorderableBoxLayout:
        id: boxlayout
        drag_classes: ['test', ]
        spacer_widgets:
            [
            Label(text='3rd spacer', font_size=40, size_hint_min_y='50sp'),
            Label(text='2nd spacer', font_size=40, size_hint_min_y='50sp'),
            Label(text='1st spacer', font_size=40, size_hint_min_y='50sp'),
            ]
        orientation: 'vertical'
        padding: 10
        size_hint_min_y: self.minimum_height
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)

    def on_start(self):
        DraggableItem = Factory.DraggableItem
        add_widget = self.root.ids.boxlayout.add_widget
        for i in range(100):
            add_widget(DraggableItem(text=str(i)))


if __name__ == '__main__':
    SampleApp().run()
