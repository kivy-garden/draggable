__all__ = (
    'temp_transform',
    'save_widget_state', 'restore_widget_state',
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


_shallow_copyable_property_names = (
    'x', 'y', 'width', 'height',
    'size_hint_x', 'size_hint_y',
    'size_hint_min_x', 'size_hint_min_y',
    'size_hint_max_x', 'size_hint_max_y',
)


def save_widget_state(widget, *, ignore_parent=False) -> dict:
    w = widget.__self__
    state = {name: getattr(w, name) for name in _shallow_copyable_property_names}
    state['pos_hint'] = deepcopy(w.pos_hint)
    if ignore_parent:
        return state
    parent = w.parent
    if parent is None:
        state['weak_parent'] = None
    else:
        state['weak_parent'] = ref(parent)
        state['index'] = parent.children.index(w)
    return state


def restore_widget_state(widget, state: dict, *, ignore_parent=False):
    w = widget.__self__
    for name in _shallow_copyable_property_names:
        setattr(w, name, state[name])
    w.pos_hint = deepcopy(state['pos_hint'])
    if ignore_parent or 'weak_parent' not in state:
        return
    weak_parent = state['weak_parent']
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
        parent.add_widget(w, index=state['index'])


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


# leave the old names for backward compatibility
save_widget_location = save_widget_state
restore_widget_location = restore_widget_state
