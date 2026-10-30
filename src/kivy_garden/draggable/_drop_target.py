from functools import partial

import asynckivy as ak

from ._common import DropTags, DEFAULT_DROP_TAGS
from ._utils import noop


def _add_a_dragged_widget_as_a_child(drop_target, touch, drag_tags, dragged_widget):
    drop_target.add_widget(dragged_widget)
    return True


async def enable_drop_target(
    widget, *, drop_tags: DropTags=DEFAULT_DROP_TAGS,
    on_enter=noop, on_leave=noop, on_drop=_add_a_dragged_widget_as_a_child,
):
    '''
    Enables ``widget`` to act as a drop target until the returned coroutine is cancelled.

    :param drop_tags:
        Drag classes accepted by this drop target.

    :param on_enter:
        Called each time a dragged widget enters the drop target.
        See :func:`on_enter` for its parameters.

    :param on_leave:
        Called each time a dragged widget leaves the drop target.
        See :func:`on_leave` for its parameters.

        For every ``on_enter`` call, a corresponding ``on_leave`` call is guaranteed,
        even if the drag is cancelled.

    :param on_drop:
        Called each time a dragged widget is dropped on the drop target.
        See :func:`on_drop` for its parameters.
    '''
    widget = widget.__self__

    async with ak.open_nursery() as nursery:
        def on_touch_xxx(
            widget, touch,
            seen="kivyx.enable_drop_target." + str(widget.uid),
            start=nursery.start,
            watch_for_drop=partial(_watch_for_drop, drop_tags, on_enter, on_leave, on_drop),
        ):
            if seen in touch.ud:
                return
            touch.ud[seen] = True
            if touch.is_mouse_scrolling:
                return
            start(watch_for_drop(widget, touch))

        widget.bind(on_touch_down=on_touch_xxx, on_touch_move=on_touch_xxx)
        try:
            await ak.sleep_forever()
        finally:
            widget.unbind(on_touch_down=on_touch_xxx, on_touch_move=on_touch_xxx)


async def _watch_for_drop(drop_tags, on_enter, on_leave, on_drop, drop_target, touch):
    ud = touch.ud
    async with ak.move_on_when(ud["kivyx_abandon"].wait()):
        tasks = await ak.wait_any(
            ud["kivyx_end"].wait(),
            ud["kivyx_exclusive_access"].wait_for_one_to_claim(),
        )
        if tasks[0].finished:
            return
        match tasks[1].result:
            case ("drag_n_drop", dragged_widget, drag_tags, drop_handlers) if not drop_tags.isdisjoint(drag_tags):
                pass
            case _:
                return

        is_inside = was_inside = False
        try:
            async with (
                ak.move_on_when(touch.ud["kivyx_end"].wait()),
                ak.visibility_aware_touch_movements(drop_target, touch) as on_touch_move,
            ):
                while True:
                    is_inside = await on_touch_move()
                    if is_inside is was_inside:
                        continue
                    if is_inside:
                        on_enter(drop_target, touch, drag_tags, dragged_widget)
                    else:
                        on_leave(drop_target, touch, drag_tags, dragged_widget)
                    was_inside = is_inside
            if is_inside:
                drop_handlers.append(partial(on_drop, drop_target, touch, drag_tags, dragged_widget))
        finally:
            if is_inside:
                on_leave(drop_target, touch, drag_tags, dragged_widget)


def on_enter(drop_target, touch, drag_tags, dragged_widget):
    '''
    :param drop_target:
        The widget that the ``dragged_widget`` entered.

    :param touch:
        The :class:`~kivy.input.motionevent.MotionEvent` that is being used to perform the drag.
        It is represented in window coordinates.

    :param dragged_widget:
        The widget being dragged.
    '''

def on_leave(drop_target, touch, drag_tags, dragged_widget):
    '''
    :param drop_target:
        The widget that the ``dragged_widget`` left.

    :param touch:
        The :class:`~kivy.input.motionevent.MotionEvent` that is being used to perform the drag.
        It is represented in window coordinates.

    :param dragged_widget:
        The widget being dragged.
    '''

def on_drop(drop_target, touch, drag_tags, dragged_widget) -> bool:
    '''
    :return:
        Return True to indicate that the drop was accepted. If False, the caller
        will continue searching for other drop targets.

    :param drop_target:
        The widget that the ``dragged_widget`` was dropped onto.

    :param touch:
        The :class:`~kivy.input.motionevent.MotionEvent` that was used to perform the drag.
        It is represented in window coordinates.

    :param dragged_widget:
        The widget that was dropped.
    '''


