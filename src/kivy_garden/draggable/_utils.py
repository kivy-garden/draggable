__all__ = (
    'temp_transform', 'temp_grab_current',
    'save_widget_location', 'restore_widget_location',
)

from weakref import ref
from copy import deepcopy


class temp_transform:
    __slots__ = ('_touch', '_func')

    def __init__(self, touch, func):
        self._touch = touch
        self._func = func

    def __enter__(self):
        t = self._touch
        t.push()
        t.apply_transform_2d(self._func)

    def __exit__(self, *args):
        self._touch.pop()


class temp_grab_current:
    __slots__ = ('_touch', '_original', )

    def __init__(self, touch):
        self._touch = touch
        self._original = touch.grab_current

    def __enter__(self):
        pass

    def __exit__(self, *args):
        self._touch.grab_current = self._original


_shallow_copyable_property_names = (
    'x', 'y', 'width', 'height',
    'size_hint_x', 'size_hint_y',
    'size_hint_min_x', 'size_hint_min_y',
    'size_hint_max_x', 'size_hint_max_y',
)


def save_widget_location(widget, *, ignore_parent=False) -> dict:
    w = widget.__self__
    location = {name: getattr(w, name) for name in _shallow_copyable_property_names}
    location['pos_hint'] = deepcopy(w.pos_hint)
    if ignore_parent:
        return location
    parent = w.parent
    if parent is None:
        location['weak_parent'] = None
    else:
        location['weak_parent'] = ref(parent)
        location['index'] = parent.children.index(w)
    return location


def restore_widget_location(widget, location: dict, *, ignore_parent=False):
    w = widget.__self__
    for name in _shallow_copyable_property_names:
        setattr(w, name, location[name])
    w.pos_hint = deepcopy(location['pos_hint'])
    if ignore_parent or 'weak_parent' not in location:
        return
    weak_parent = location['weak_parent']
    if weak_parent is None:
        parent = None
    else:
        parent = weak_parent()
        if parent is None:
            raise ReferenceError("weakly-referenced parent no longer exists")
    if w.parent is not None:
        w.parent.remove_widget(w)
    if parent is None:
        return

    # 'Window.add_widget()' doesn't take 'index' so we need to check if the
    # 'parent' is Window or not. The way to do it here is weird, and I'm not
    # sure this is correct or not.
    if parent.parent is parent:
        parent.add_widget(w)
    else:
        parent.add_widget(w, index=location['index'])


def _create_spacer(**kwargs):
    '''(internal)'''
    from kivy.uix.widget import Widget
    from kivy.utils import rgba
    from kivy.graphics import Color, Rectangle
    spacer = Widget(size_hint_min=('50dp', '50dp'))
    with spacer.canvas:
        color = kwargs.get('color', None)
        if color is None:
            Color(.2, .2, .2, .7)
        else:
            Color(*rgba(color))
        rect_inst = Rectangle(size=spacer.size)
    spacer.bind(
        pos=lambda __, value: setattr(rect_inst, 'pos', value),
        size=lambda __, value: setattr(rect_inst, 'size', value),
    )
    return spacer
