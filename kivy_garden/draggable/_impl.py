'''
notes for maintainers
---------------------

KXDraggableBehaviorがTaskを作る際に

.. code-block::

   self._drag_task = ak.start(Task(...))

ではなく

.. code-block::

   self._drag_task = ak.Task(...)
   ak.start(self._drag_task)

としているのは、前者だと ``on_drag_start`` event 時にdraggable.cancel()が呼ばれると
代入前の古い ``self._drag_task`` への操作になってしまう為。
'''

__all__ = (
    'KXDraggableBehavior', 'KXDroppableBehavior', 'KXReorderableBehavior',
    'save_widget_location', 'restore_widget_location', 'DragContext',
)
from typing import Tuple, Union, Iterator
from contextlib import contextmanager
from inspect import isawaitable
from dataclasses import dataclass

from kivy.config import Config
from kivy.properties import (
    BooleanProperty, ListProperty, StringProperty, NumericProperty,
)
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.uix.widget import Widget
import asynckivy as ak

from ._utils import (
    temp_transform, temp_grab_current, _create_spacer,
    save_widget_location, restore_widget_location,
)


# When we are generating documentation, Config doesn't exist
_scroll_timeout = _scroll_distance = 0
if Config:
    _scroll_timeout = Config.getint('widgets', 'scroll_timeout')
    _scroll_distance = Config.get('widgets', 'scroll_distance') + 'sp'


@dataclass
class DragContext:
    original_pos_win: tuple = None
    '''(read-only) The position of the draggable at the time the drag has
    started. (window coordinates).
    '''

    original_location: dict = None
    '''(read-only) Where the draggable came from. Can be passed to
    ``restore_widget_location()``.
    '''

    droppable: Union[None, 'KXDroppableBehavior', 'KXReorderableBehavior'] \
        = None
    '''(read-only) The widget where the draggable dropped to.'''

    state: str = 'started'
    '''(read-only) The current state of the drag. One of the following:
    'started', 'succeeded', 'failed' or 'cancelled'.
    '''

    @property
    def cancelled(self) -> bool:
        return self.state == 'cancelled'
    '''This property exists just for backward compatibility.
    Use ``state`` instead.
    '''


class KXDraggableBehavior:
    __events__ = (
        'on_drag_start', 'on_drag_end', 'on_drag_success', 'on_drag_fail',
        'on_drag_cancel',
    )

    drag_cls = StringProperty()
    '''Same as drag_n_drop's '''

    drag_distance = NumericProperty(_scroll_distance)

    drag_timeout = NumericProperty(_scroll_timeout)

    drag_enabled = BooleanProperty(True)
    '''Indicates whether this draggable can be dragged or not. Changing this
    doesn't affect ongoing drag.
    '''

    is_being_dragged = BooleanProperty(False)
    '''(read-only)'''

    # default value of the instance attributes
    _drag_task = ak.Task(
        ak.sleep_forever(),
        name=r"KXDraggableBehavior's dummy task",
    )

    @staticmethod
    def ongoing_drags(*, window=None) -> Iterator['KXDraggableBehavior']:
        if window is None:
            from kivy.core.window import Window
            window = Window
        return (
            c for c in window.children
            if isinstance(c, KXDraggableBehavior) and c.is_being_dragged
        )

    @property
    def drag_context(self) -> Union[None, DragContext]:
        return self._drag_ctx

    def drag_cancel(self):
        '''Cancels drag as soon as possible. Does nothing if the draggable is
        not being dragged
        '''
        self._drag_task.cancel()

    def __init__(self, **kwargs):
        self._drag_ctx = None
        super().__init__(**kwargs)
        self.__ud_key = 'KXDraggableBehavior.' + str(self.uid)

    def _is_a_touch_potentially_a_drag(self, touch) -> bool:
        return self.collide_point(*touch.opos) \
            and self.drag_enabled \
            and (not self.is_being_dragged) \
            and (not touch.is_mouse_scrolling) \
            and (self.__ud_key not in touch.ud) \
            and (touch.time_end == -1)

    def on_touch_down(self, touch):
        if self._is_a_touch_potentially_a_drag(touch):
            touch.ud[self.__ud_key] = None
            if self.drag_timeout:
                ak.start(self._see_if_a_touch_can_be_treated_as_a_drag(touch))
            else:
                self._drag_task.cancel()
                self._drag_task = ak.Task(self._treat_a_touch_as_a_drag(touch))
                ak.start(self._drag_task)
            return True
        else:
            touch.ud[self.__ud_key] = None
            return super().on_touch_down(touch)

    async def _see_if_a_touch_can_be_treated_as_a_drag(self, touch):
        tasks = await ak.or_(
            ak.sleep(self.drag_timeout / 1000.),
            self._true_when_a_touch_ended_false_when_it_moved_too_much(touch),
        )
        if tasks[0].done:
            # The given touch is a dragging gesture.
            if self.is_being_dragged or (not self.drag_enabled):
                ak.start(self._simulate_a_normal_touch(
                    touch, do_transform=True))
            else:
                self._drag_task.cancel()
                self._drag_task = ak.Task(
                    self._treat_a_touch_as_a_drag(touch, do_transform=True))
                ak.start(self._drag_task)
        else:
            # The given touch is not a dragging gesture.
            ak.start(self._simulate_a_normal_touch(
                touch, do_touch_up=tasks[1].result))

    async def _true_when_a_touch_ended_false_when_it_moved_too_much(
            self, touch):
        drag_distance = self.drag_distance
        ox, oy = touch.opos
        async for __ in ak.rest_of_touch_moves(self, touch):
            dx = abs(touch.x - ox)
            dy = abs(touch.y - oy)
            if dy > drag_distance or dx > drag_distance:
                return False
        return True

    def drag_start_from_other_widget(self, drag_from: Widget, touch):
        '''
        Starts dragging as if the draggable existed where ``drag_from`` is.

        * Sizing/Positioning properties will be overwritten by ``drag_from``'s.
        * The draggable shouldn't have a parent.
        * This method should be called from ``drag_from``'s touch events.
        '''
        if self.parent is not None:
            raise ak.InvalidStateError("Draggable shouldn't have a parent")
        if touch.time_end != -1:
            return
        touch.ud[self.__ud_key] = None
        self._drag_task = ak.Task(
            self._treat_a_touch_as_a_drag(touch, drag_from=drag_from))
        ak.start(self._drag_task)

    async def _treat_a_touch_as_a_drag(
            self, touch, *, do_transform=False, drag_from=None):
        if drag_from is None:
            drag_from = self
        self.is_being_dragged = True
        try:
            # NOTE: I don't know the difference from 'get_root_window()'
            window = drag_from.get_parent_window()
            touch_ud = touch.ud
            original_pos_win = drag_from.to_window(*drag_from.pos)
            original_location = save_widget_location(
                drag_from, ignore_parent=(drag_from is not self))
            original_location.setdefault('weak_parent', None)
            self._drag_ctx = ctx = DragContext(
                original_pos_win=original_pos_win,
                original_location=original_location,
            )

            if do_transform:
                touch.push()
                touch.apply_transform_2d(drag_from.parent.to_widget)
            offset_x = touch.ox - drag_from.x
            offset_y = touch.oy - drag_from.y
            if do_transform:
                touch.pop()

            # move self under the Window
            if self.parent is None:  # more like (drag_from is not self)
                restore_widget_location(
                    self, original_location, ignore_parent=True)
            else:
                self.parent.remove_widget(self)
            self.size_hint = (None, None, )
            self.pos_hint = {}
            self.pos = (
                original_pos_win[0] + touch.x - touch.ox,
                original_pos_win[1] + touch.y - touch.oy,
            )
            window.add_widget(self)

            # mark the touch so that the other widgets can react to the drag
            touch_ud['kivyx_drag_cls'] = self.drag_cls
            touch_ud['kivyx_draggable'] = self

            self.dispatch('on_drag_start', touch)
            async for __ in ak.rest_of_touch_moves(self, touch):
                self.x = touch.x - offset_x
                self.y = touch.y - offset_y

            # we need to give the other widgets the time to react to
            # 'on_touch_up'
            await ak.sleep(-1)

            ctx.droppable = droppable = touch_ud.get('kivyx_droppable', None)
            if droppable is None or (not droppable.accepts_drag(touch, self)):
                ctx.state = 'failed'
                r = self.dispatch('on_drag_fail', touch)
            else:
                ctx.state = 'succeeded'
                r = self.dispatch('on_drag_success', touch)
            async with ak.cancel_protection():
                if isawaitable(r):
                    await r
                # I cannot remember why this 'ak.sleep()' exists.
                # It might be unnecessary.
                await ak.sleep(-1)
        except GeneratorExit:
            ctx.state = 'cancelled'
            self.dispatch('on_drag_cancel', touch)
            raise
        finally:
            self.dispatch('on_drag_end', touch)
            self.is_being_dragged = False
            self._drag_ctx = None
            touch_ud['kivyx_droppable'] = None
            del touch_ud['kivyx_drag_cls']
            del touch_ud['kivyx_draggable']

    async def _simulate_a_normal_touch(
            self, touch, *, do_transform=False, do_touch_up=False):
        # simulate 'on_touch_down'
        with temp_grab_current(touch):
            touch.grab_current = None
            if do_transform:
                touch.push()
                touch.apply_transform_2d(self.parent.to_widget)
            super().on_touch_down(touch)
            if do_transform:
                touch.pop()

        if not do_touch_up:
            return
        await ak.sleep(.1)

        # simulate 'on_touch_up'
        to_widget = self.to_widget if self.parent is None \
            else self.parent.to_widget
        touch.grab_current = None
        with temp_transform(touch):
            touch.apply_transform_2d(to_widget)
            super().on_touch_up(touch)

        # simulate the grabbed one as well
        for x in tuple(touch.grab_list):
            touch.grab_list.remove(x)
            x = x()
            if x is None:
                continue
            touch.grab_current = x
            with temp_transform(touch):
                touch.apply_transform_2d(x.parent.to_widget)
                x.dispatch('on_touch_up', touch)

        touch.grab_current = None
        return

    def on_drag_start(self, touch):
        pass

    def on_drag_end(self, touch):
        pass

    def on_drag_success(self, touch):
        ctx = self._drag_ctx
        original_location = ctx.original_location
        self.parent.remove_widget(self)
        self.size_hint_x = original_location['size_hint_x']
        self.size_hint_y = original_location['size_hint_y']
        self.pos_hint = original_location['pos_hint']
        ctx.droppable.add_widget(
            self, index=touch.ud.get('kivyx_droppable_index', 0))

    async def on_drag_fail(self, touch):
        ctx = self._drag_ctx
        await ak.animate(
            self, d=.1,
            x=ctx.original_pos_win[0],
            y=ctx.original_pos_win[1],
        )
        restore_widget_location(self, ctx.original_location)

    def on_drag_cancel(self, touch):
        restore_widget_location(self, self._drag_ctx.original_location)


class KXDroppableBehavior:
    drag_classes = ListProperty([])
    '''Same as drag_n_drop's '''

    def on_touch_up(self, touch):
        r = super().on_touch_up(touch)
        touch_ud = touch.ud
        if touch_ud.get('kivyx_drag_cls', None) in self.drag_classes:
            if self.collide_point(*touch.pos):
                touch_ud.setdefault('kivyx_droppable', self)
        return r

    def accepts_drag(self, touch, draggable) -> bool:
        '''Determines whether the droppable is willing to accept the drag'''
        return True


class KXReorderableBehavior:
    drag_classes = ListProperty([])
    '''Same as drag_n_drop's '''

    spacer_widgets = ListProperty([])
    '''A list of spacer widgets. The number of them will be the
    maximum number of simultaneous drags ``KXReorderableBehavior`` can handle.

    This property can be changed only when there is no ongoing drag.
    '''

    @classmethod
    def create_spacer(cls, **kwargs):
        import warnings
        warnings.warn(
            r"KXReorderableBehavior.create_spacer() is deprecated, "
            r"and will be removed in the future.")
        return _create_spacer(**kwargs)

    def __init__(self, **kwargs):
        self._active_spacers = []
        self._inactive_spacers = None
        Clock.schedule_once(self._init_spacers)
        super().__init__(**kwargs)
        self.__ud_key = 'KXReorderableBehavior.' + str(self.uid)

    def accepts_drag(self, touch, draggable) -> bool:
        '''Determines whether the reorderable is willing to accept the drag'''
        return True

    def _init_spacers(self, dt):
        if self._inactive_spacers is None:
            self.spacer_widgets.append(_create_spacer())

    def on_spacer_widgets(self, __, spacer_widgets):
        if self._active_spacers:
            raise ak.InvalidStateError(
                "Do not change the 'spacer_widgets' when there is an ongoing"
                " drag.")
        self._inactive_spacers = [w.__self__ for w in spacer_widgets]

    def get_widget_under_drag(self, x, y) -> Tuple[Widget, int]:
        """Returns a tuple of the widget in children that is under the
        given position and its index. Returns (None, None) if there is no
        widget under that position.
        """
        x, y = self.to_local(x, y)
        for index, widget in enumerate(self.children):
            if widget.collide_point(x, y):
                return (widget, index)
        return (None, None)

    def get_drop_insertion_index_move(self, x, y, spacer):
        widget, idx = self.get_widget_under_drag(x, y)
        if widget is spacer:
            return None
        if widget is None:
            return None if self.children else 0
        return idx

    def on_touch_move(self, touch):
        ud_key = self.__ud_key
        touch_ud = touch.ud
        if ud_key not in touch_ud and self._inactive_spacers \
                and self.collide_point(*touch.pos):
            drag_cls = touch_ud.get('kivyx_drag_cls', None)
            if drag_cls is not None:
                touch_ud[ud_key] = None
                if drag_cls in self.drag_classes:
                    # Watches 'is_being_dragged' as well, so that the
                    # '_watch_touch()' will be automatically cancelled when
                    # the drag is cancelled.
                    ak.start(ak.or_(
                        self._watch_touch(touch),
                        ak.event(
                            touch.ud['kivyx_draggable'], 'is_being_dragged'),
                    ))
        return super().on_touch_move(touch)

    async def _watch_touch(self, touch):
        spacer = self._inactive_spacers.pop()
        self._active_spacers.append(spacer)

        # assigning to a local variable might improve performance
        collide_point = self.collide_point
        get_drop_insertion_index_move = self.get_drop_insertion_index_move
        remove_widget = self.remove_widget
        add_widget = self.add_widget
        touch_ud = touch.ud

        try:
            restore_widget_location(
                spacer,
                touch_ud['kivyx_draggable'].drag_context.original_location,
                ignore_parent=True)
            add_widget(spacer)
            async for __ in ak.rest_of_touch_moves(self, touch):
                x, y = touch.pos
                if collide_point(x, y):
                    new_idx = get_drop_insertion_index_move(x, y, spacer)
                    if new_idx is not None:
                        remove_widget(spacer)
                        add_widget(spacer, index=new_idx)
                else:
                    del touch_ud[self.__ud_key]
                    return
            if 'kivyx_droppable' not in touch_ud:
                touch_ud['kivyx_droppable'] = self
                touch_ud['kivyx_droppable_index'] = self.children.index(spacer)
        finally:
            self.remove_widget(spacer)
            self._inactive_spacers.append(spacer)
            self._active_spacers.remove(spacer)


r = Factory.register
r('KXDraggableBehavior', cls=KXDraggableBehavior)
r('KXDroppableBehavior', cls=KXDroppableBehavior)
r('KXReorderableBehavior', cls=KXReorderableBehavior)
