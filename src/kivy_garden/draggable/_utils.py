from copy import deepcopy

from kivy.uix.widget import Widget
from kivy.input.motionevent import MotionEvent
from kivy.base import EventLoop
from kivy_garden.draggable._common import DragTags


def noop(*args, **kwargs):
    pass


def is_colliding_and_not_wheel(w, t):
    return w.collide_point(*t.pos) and (not t.is_mouse_scrolling)


def get_active_drags() -> list[tuple[Widget, MotionEvent, DragTags]]:
    '''
    Returns a list of ``(dragged_widget, touch, drag_tags)`` tuples for all ongoing drags.
    '''
    result = []
    for t in EventLoop.touches:
        try:
            ex_access = t.ud["kivyx_exclusive_access"]
        except KeyError:
            continue
        if (not ex_access.has_been_claimed) or t.ud["kivyx_abandon"].is_fired:
            continue
        match ex_access.params:
            case "drag_n_drop", dragged_widget, drag_tags, _:
                result.append((dragged_widget, t, drag_tags))
    return result


def cancel_drag(touch):
    '''
    Cancels the ongoing drag associated with the given touch.
    '''
    try:
        ex_access = touch.ud["kivyx_exclusive_access"]
    except KeyError:
        return
    match ex_access.params:
        case "drag_n_drop", *_:
            touch.ud["kivyx_abandon"].fire()


def cancel_active_drags():
    '''
    Cancels all ongoing drags.
    '''
    for t in EventLoop.touches:
        try:
            ex_access = t.ud["kivyx_exclusive_access"]
        except KeyError:
            continue
        match ex_access.params:
            case "drag_n_drop", *_:
                t.ud["kivyx_abandon"].fire()


_shallow_copyable_layout_property_names = (
    "x", "y", "width", "height",
    "size_hint_x", "size_hint_y",
    "size_hint_min_x", "size_hint_min_y",
    "size_hint_max_x", "size_hint_max_y",
)


def copy_layout_state(from_, to_):
    '''
    Copies the layout-related properties from one to another.

    .. code-block::

        to_.x = from_.x
        to_.y = from_.y
        to_.width = from_.width
        ...
        to_.pos_hint = deepcopy(from_.pos_hint)
    '''
    setattr_ = setattr
    getattr_ = getattr
    for name in _shallow_copyable_layout_property_names:
        setattr_(to_, name, getattr_(from_, name))
    setattr_(to_, "pos_hint", deepcopy(getattr_(from_, "pos_hint")))


class transform_2d:
    '''
    .. code-block::

        with transform_2d(touch, transform_func):
            ...
    '''
    __slots__ = ("_touch", "_func")

    def __init__(self, touch, func):
        self._touch = touch
        self._func = func

    def __enter__(self):
        t = self._touch
        t.push()
        t.apply_transform_2d(self._func)

    def __exit__(self, *args):
        self._touch.pop()


def find_child_at(children, x, y) -> Widget | None:
    '''
    Returns the child widget at the given position, or ``None`` if no child is found.
    '''
    for c in children:
        if c.collide_point(x, y):
            return c
    return None


def find_child_with_index_at(children, x, y) -> tuple[Widget, int] | tuple[None, None]:
    '''
    Returns a tuple ``(widget, index)`` for the child widget at the given position,
     or ``(None, None)`` if no child is found.
    '''
    for i, child in enumerate(children):
        if child.collide_point(x, y):
            return (child, i)
    return (None, None)
