from copy import deepcopy

import asynckivy as ak


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
    getattr_ = getattr
    state = {name: getattr_(w, name) for name in _shallow_copyable_property_names}
    state['pos_hint'] = deepcopy(w.pos_hint)
    if ignore_parent:
        return state
    parent = w.parent
    state['parent'] = parent
    if parent is not None:
        state['index'] = parent.children.index(w)
    return state


def restore_widget_state(widget, state: dict, *, ignore_parent=False):
    w = widget.__self__
    setattr_ = setattr
    for name in _shallow_copyable_property_names:
        setattr_(w, name, state[name])
    w.pos_hint = deepcopy(state['pos_hint'])
    if ignore_parent or 'parent' not in state:
        return
    if w.parent is not None:
        w.parent.remove_widget(w)
    parent = state['parent']
    if parent is None:
        return

    # The 'Window.add_widget()' doesn't have the 'index' parameter so we need to check whether the 'parent' is Window
    # or not. The way to do it here is unreliable, and might not work in the future.
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
        rect_inst = Rectangle(size=spacer.size, pos=spacer.pos)
    ak.sync_attr((spacer, "pos"), (rect_inst, "pos")).__enter__()
    ak.sync_attr((spacer, "size"), (rect_inst, "size")).__enter__()
    return spacer
