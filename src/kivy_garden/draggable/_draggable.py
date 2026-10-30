from typing import Literal, Any
from collections.abc import Callable
from functools import partial
from contextlib import ExitStack

from kivy import metrics
from kivy.graphics import PushMatrix, PopMatrix, Translate, InstructionGroup
from kivy.input.motionevent import MotionEvent
from kivy.core.window import Window
from kivy.uix.widget import Widget
import asynckivy as ak

from ._common import DragTags, DEFAULT_DRAG_TAGS
from ._utils import noop, is_colliding_and_not_wheel, find_child_at, transform_2d

type DragResult = Literal["succeeded", "failed", "cancelled"]
type OnDragStart = Callable[[Widget, MotionEvent, DragTags], Any]
type OnDragEnd = Callable[[Widget, MotionEvent, DragTags, DragResult], Any]


async def perform_drag(widget, touch, *, drag_tags: DragTags=DEFAULT_DRAG_TAGS, include_pre_drag_distance=True):
    '''
    Drags ``widget`` with ``touch`` until it is released.

    .. code-block::

        success = await perform_drag(widget, touch)

    :return:
        Whether the dragged widget was accepted by a drop target.

    :param widget:
        The widget to be dragged.

    :param touch:
        The touch to drag with. Exclusive access to this touch must not have been claimed.

    :param include_pre_drag_distance:
        Whether to apply the distance already traveled by the touch since its
        ``on_touch_down`` event to the initial offset of the drag.
    '''
    if include_pre_drag_distance:
        initial_offset = widget.to_window(touch.x - touch.ox, touch.y - touch.oy)
    else:
        initial_offset = widget.to_window(0, 0)
    parent = widget.parent
    if parent is None:
        restore_original_placement = noop
    else:
        restore_original_placement = partial(parent.add_widget, widget, index=parent.children.index(widget))

    drop_handlers = []
    touch.ud["kivyx_exclusive_access"].claim("drag_n_drop", widget, drag_tags, drop_handlers)
    if parent is not None:
        parent.remove_widget(widget)

    async with ak.move_on_when(touch.ud["kivyx_abandon"].wait()):
        accepted = False
        try:
            with ExitStack() as stack:
                defer = stack.callback

                overlay = InstructionGroup()
                defer(overlay.clear)
                add = overlay.add
                add(PushMatrix())
                add(translation := Translate(*initial_offset))
                add(widget.canvas)
                add(PopMatrix())

                Window.canvas.add(overlay)
                defer(Window.canvas.remove, overlay)

                async with (
                    ak.move_on_when(touch.ud["kivyx_end"].wait()),
                    ak.event_freq(Window, "on_touch_move", filter=lambda w, t, touch=touch: t is touch) as on_touch_move,
                ):
                    offset_x, offset_y = initial_offset
                    while True:
                        await on_touch_move()
                        offset_x += touch.dx
                        offset_y += touch.dy
                        translation.xy = (offset_x, offset_y)

                # Wait for other widgets to respond to the `on_touch_up` event.
                # This populates the `drop_handlers` list with handlers from widgets that declared to accept the drop.
                await ak.sleep(-1)

                overlay.remove(widget.canvas)
                for f in drop_handlers:
                    if f():
                        accepted = True
                        break
                if not accepted:
                    # No one accepted the drop, but we cannot call `restore_original_placement`
                    # yet because `widget.canvas` is still in `Window.canvas``.
                    overlay.insert(2, widget.canvas)
                    await ak.anim_attrs(translation, duration=.1, xy=initial_offset)
        finally:
            if not accepted:
                restore_original_placement()

        return accepted


async def _watch_for_drag_start(
    target: Widget, touch: MotionEvent, *,
    drag_tags: DragTags,
    start_timeout: float,
    max_start_distance: float,
    on_start: OnDragStart,
    on_end: OnDragEnd,
    _active_targets=[],
):
    '''
    Monitors ``touch`` and starts dragging ``target`` when ``touch`` stays for
    ``start_timeout`` seconds without traveling more than ``max_start_distance`` pixels.
    '''
    ud = touch.ud
    async with ak.move_on_when(ud["kivyx_abandon"].wait()):
        async with (
            ak.move_on_when(ak.wait_any(
                timeout_tracker := ak.Task(ak.sleep(start_timeout)),
                ud["kivyx_end"].wait(),
                ud["kivyx_exclusive_access"].wait_for_one_to_claim(),
            )),
            ak.event_freq(Window, "on_touch_move", filter=lambda w, t, touch=touch: t is touch) as on_touch_move,
        ):
            dx = dy = 0.
            while True:
                await on_touch_move()
                dx += touch.dx
                dy += touch.dy
                if dy > max_start_distance or dx > max_start_distance:
                    break
        if timeout_tracker.cancelled or target in _active_targets:
            ak.managed_start(_emulate_a_regular_touch(target, touch))
            return
        on_start(target, touch, drag_tags)
        result = "cancelled"
        _active_targets.append(target)
        try:
            if await perform_drag(target, touch, drag_tags=drag_tags):
                result = "succeeded"
            else:
                result = "failed"
        finally:
            _active_targets.remove(target)
            on_end(target, touch, drag_tags, result)


async def enable_drag(
    widget, *,
    touch_filter: Callable[[Widget, MotionEvent], bool]=is_colliding_and_not_wheel,
    start_timeout=0.2,
    max_start_distance: float=metrics.dp(20),
    on_start: OnDragStart=noop,
    on_end: OnDragEnd=noop,
    drag_tags: DragTags=DEFAULT_DRAG_TAGS,
):
    '''
    Makes ``widget`` draggable until the returned coroutine is cancelled.

    See :func:`enable_drag_for_children` for the parameters.
    '''
    widget = widget.__self__
    on_touch_down = partial(ak.event, widget, "on_touch_down", filter=touch_filter, stop_dispatching=True)
    watch_for_drag_start = partial(
        _watch_for_drag_start, drag_tags=drag_tags, start_timeout=start_timeout,
        max_start_distance=max_start_distance, on_start=on_start, on_end=on_end,
    )

    with ak.suppress_event(widget, "on_touch_down", filter=touch_filter):
        while True:
            __, touch = await on_touch_down()
            await watch_for_drag_start(widget, touch)


async def enable_drag_for_children(
    layout, *,
    touch_filter: Callable[[Widget, MotionEvent], bool]=is_colliding_and_not_wheel,
    start_timeout=0.2,
    max_start_distance: float=metrics.dp(20),
    track_multiple_touches: bool=False,
    on_start: OnDragStart=noop,
    on_end: OnDragEnd=noop,
    drag_tags: DragTags=DEFAULT_DRAG_TAGS,
):
    '''
    Makes ``layout``'s children draggable until the returned coroutine is cancelled.

    :param touch_filter:
        Any touch whose ``on_touch_down`` event does not pass this filter is ignored.

    :param start_timeout:
        Maximum time to wait for a drag to start after a touch down.

    :param max_start_distance:
        Maximum distance the touch can move before the drag is considered to have failed.

    :param track_multiple_touches:
        Whether to track multiple touches simultaneously (multi-touch). If False (the default),
        once a touch starts being tracked, subsequent touches are ignored until the tracked touch ends.

    :param on_start:
        Called each time a drag starts.
        See :func:`on_start` for the callback parameters.

    :param on_end:
        Called each time a drag ends.
        See :func:`on_end` for the callback parameters.
    '''
    layout = layout.__self__
    children = layout.children
    to_local = layout.to_local
    on_touch_down = partial(ak.event, layout, "on_touch_down", filter=touch_filter, stop_dispatching=True)
    watch_for_drag_start = partial(
        _watch_for_drag_start, drag_tags=drag_tags, start_timeout=start_timeout,
        max_start_distance=max_start_distance, on_start=on_start, on_end=on_end,
    )
    find_child_at_ = find_child_at

    with ak.suppress_event(layout, "on_touch_down", filter=touch_filter):
        if track_multiple_touches:
            async with ak.open_nursery() as nursery:
                while True:
                    __, touch = await on_touch_down()
                    child = find_child_at_(children, *to_local(*touch.pos))
                    if child is not None:
                        nursery.start(watch_for_drag_start(child, touch))
        else:
            while True:
                __, touch = await on_touch_down()
                child = find_child_at_(children, *to_local(*touch.pos))
                if child is not None:
                    await watch_for_drag_start(child, touch)


def on_start(widget, touch, drag_tags: DragTags):
    '''
    :param widget:
        The widget to be dragged.

    :param touch:
        The :class:`~kivy.input.motionevent.MotionEvent` that triggered the drag,
        represented in window coordinates.
    '''


def on_end(widget, touch, drag_tags: DragTags, result: DragResult):
    '''
    :param widget:
        The widget that was being dragged.

    :param touch:
        The :class:`~kivy.input.motionevent.MotionEvent` that triggered the drag,
        represented in window coordinates.
    '''


async def _emulate_a_regular_touch(widget, touch):
    # emulate 'on_touch_down'
    original = touch.grab_current
    touch.grab_current = None
    with transform_2d(touch, widget.parent.to_widget):
        super(widget.__class__, widget).on_touch_down(touch)
    touch.grab_current = original

    #
    if not touch.ud["kivyx_end"].is_fired:
        return
    await ak.sleep(.1)

    # emulate 'on_touch_up'
    touch.grab_current = None
    with transform_2d(touch, widget.to_widget if widget.parent is None else widget.parent.to_widget):
        super(widget.__class__, widget).on_touch_up(touch)

    # emulate the grabbed one as well
    for x in tuple(touch.grab_list):
        touch.grab_list.remove(x)
        x = x()
        if x is None:
            continue
        touch.grab_current = x
        with transform_2d(touch, x.parent.to_widget):
            x.dispatch("on_touch_up", touch)
    touch.grab_current = None
