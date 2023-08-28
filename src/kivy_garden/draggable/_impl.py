__all__ = (
    'KXDraggableBehavior', 'KXDroppableBehavior', 'KXReorderableBehavior',
    'ongoing_drags',
)
from typing import List, Tuple, Union
from inspect import isawaitable
from dataclasses import dataclass
from contextlib import nullcontext
from functools import cached_property

from kivy.properties import (
    BooleanProperty, ListProperty, StringProperty, NumericProperty, OptionProperty, AliasProperty,
)
from kivy.clock import Clock
from kivy.factory import Factory
import kivy.core.window
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
import asynckivy as ak

from ._utils import (
    temp_transform, _create_spacer,
    save_widget_state, restore_widget_state,
)


@dataclass
class DragContext:
    original_pos_win: tuple = None
    '''(read-only) The position of the draggable at the time the drag has
    started. (window coordinates).
    '''

    original_state: dict = None
    '''
    (read-only) The state of the draggable at the time the drag has started.
    This can be passed to ``restore_widget_state()``.
    '''

    droppable: Union[None, 'KXDroppableBehavior', 'KXReorderableBehavior'] = None
    '''(read-only) The widget where the draggable dropped to. This is always None on_drag_start/on_drag_cancel, and is
    always a widget on_drag_succeed, and can be either on_drag_fail/on_drag_end.'''

    @cached_property
    def original_location(self) -> dict:
        '''
        This exists solely for backward compatibility.
        Use :attr:`original_state` instead.
        '''
        return self.original_state


class KXDraggableBehavior:
    __events__ = (
        'on_drag_start', 'on_drag_end', 'on_drag_succeed', 'on_drag_fail',
        'on_drag_cancel',
    )

    drag_cls = StringProperty()
    '''Same as drag_n_drop's '''

    drag_distance = NumericProperty(ScrollView.scroll_distance.defaultvalue)

    drag_timeout = NumericProperty(ScrollView.scroll_timeout.defaultvalue)

    drag_enabled = BooleanProperty(True)
    '''Indicates whether this draggable can be dragged or not. Changing this
    doesn't affect ongoing drag. Call `drag_cancel()` if you want to do that.
    '''

    drag_state = OptionProperty(None, options=('started', 'succeeded', 'failed', 'cancelled'), allownone=True)
    '''(read-only)'''

    is_being_dragged = AliasProperty(lambda self: self.drag_state is not None, bind=('drag_state', ), cache=True)
    '''(read-only)'''

    def drag_cancel(self):
        '''
        If the draggable is currently being dragged, cancel it.
        '''
        self._drag_task.cancel()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._drag_task = ak.dummy_task
        self.__ud_key = 'KXDraggableBehavior.' + str(self.uid)

    def _is_a_touch_potentially_a_dragging_gesture(self, touch) -> bool:
        return self.collide_point(*touch.opos) \
            and (not touch.is_mouse_scrolling) \
            and (self.__ud_key not in touch.ud) \
            and (touch.time_end == -1)

    @property
    def _can_be_dragged(self) -> bool:
        return self.drag_enabled and (not self.is_being_dragged)

    def on_touch_down(self, touch):
        if self._is_a_touch_potentially_a_dragging_gesture(touch) and self._can_be_dragged:
            touch.ud[self.__ud_key] = None
            if self.drag_timeout:
                ak.start(self._see_if_a_touch_actually_is_a_dragging_gesture(touch))
            else:
                ak.start(self._treat_a_touch_as_a_drag(touch))
            return True
        else:
            touch.ud[self.__ud_key] = None
            return super().on_touch_down(touch)

    async def _see_if_a_touch_actually_is_a_dragging_gesture(self, touch):
        async with ak.wait_any_cm(ak.sleep(self.drag_timeout / 1000.)):  # <- 'trio.move_on_after()' equivalent
            # LOAD_FAST
            abs_ = abs
            drag_distance = self.drag_distance
            ox, oy = touch.opos

            do_touch_up = True
            async with ak.watch_touch(self, touch) as in_progress:
                while await in_progress():
                    dx = abs_(touch.x - ox)
                    dy = abs_(touch.y - oy)
                    if dy > drag_distance or dx > drag_distance:
                        do_touch_up = False
                        break

            # Reaching here means the given touch is not a dragging gesture.
            ak.start(self._simulate_a_normal_touch(touch, do_touch_up=do_touch_up))
            return

        # Reaching here means the given touch is a dragging gesture.
        ak.start(
            self._treat_a_touch_as_a_drag(touch, do_transform=True)
            if self._can_be_dragged else
            self._simulate_a_normal_touch(touch, do_transform=True)
        )

    def start_dragging_from_others_touch(self, receiver: Widget, touch):
        '''
        Arguments
        ---------

        * ``receiver`` ... The widget that received the ``touch``.
        * ``touch`` ... The touch that is going to drag me.
        '''
        if touch.time_end != -1:
            return
        touch.ud[self.__ud_key] = None
        ak.start(self._treat_a_touch_as_a_drag(touch, touch_receiver=receiver))

    async def _treat_a_touch_as_a_drag(self, touch, *, do_transform=False, touch_receiver=None):
        try:
            if touch_receiver is None:
                original_pos_win = self.to_window(*self.pos)
                with temp_transform(touch, self.parent.to_widget) if do_transform else nullcontext():
                    offset_x = touch.ox - self.x
                    offset_y = touch.oy - self.y
            else:
                offset_x = self.width * 0.5
                offset_y = self.height * 0.5
                x, y = touch_receiver.to_window(*touch.opos)
                original_pos_win = (x - offset_x, y - offset_y, )

            # NOTE: I don't know the difference from 'get_root_window()'
            window = self.get_parent_window()
            if window is None:
                from kivy.core.window import Window
                window = Window
            touch_ud = touch.ud
            original_state = save_widget_state(self)
            ctx = DragContext(
                original_pos_win=original_pos_win,
                original_state=original_state,
            )

            # move self under the Window
            if self.parent is not None:
                self.parent.remove_widget(self)
            self.size_hint = (None, None, )
            self.pos_hint = {}
            self.pos = (
                original_pos_win[0] + touch.x - touch.ox,
                original_pos_win[1] + touch.y - touch.oy,
            )
            window.add_widget(self)

            # mark the touch so that other widgets can react to this drag
            touch_ud['kivyx_drag_cls'] = self.drag_cls
            touch_ud['kivyx_draggable'] = self
            touch_ud['kivyx_drag_ctx'] = ctx

            # store the task instance so that the user can cancel it later
            self._drag_task.cancel()
            self._drag_task = await ak.current_task()

            # actual dragging process
            self.dispatch('on_drag_start', touch, ctx)
            self.drag_state = 'started'
            async with ak.watch_touch(self, touch) as is_touch_move:
                while await is_touch_move():
                    self.x = touch.x - offset_x
                    self.y = touch.y - offset_y

            # wait for other widgets to react to 'on_touch_up'
            await ak.sleep(-1)

            ctx.droppable = droppable = touch_ud.get('kivyx_droppable', None)
            if droppable is None or (not droppable.accepts_drag(touch, ctx, self)):
                r = self.dispatch('on_drag_fail', touch, ctx)
                self.drag_state = 'failed'
            else:
                r = self.dispatch('on_drag_succeed', touch, ctx)
                self.drag_state = 'succeeded'
            async with ak.disable_cancellation():
                if isawaitable(r):
                    await r
                await ak.sleep(-1)  # This is necessary in order to work with Magnet iirc.
        except ak.Cancelled:
            self.dispatch('on_drag_cancel', touch, ctx)
            self.drag_state = 'cancelled'
            raise
        finally:
            self.dispatch('on_drag_end', touch, ctx)
            self.drag_state = None
            touch_ud['kivyx_droppable'] = None
            del touch_ud['kivyx_drag_cls']
            del touch_ud['kivyx_draggable']
            del touch_ud['kivyx_drag_ctx']

    async def _simulate_a_normal_touch(self, touch, *, do_transform=False, do_touch_up=False):
        # simulate 'on_touch_down'
        original = touch.grab_current
        try:
            touch.grab_current = None
            with temp_transform(touch, self.parent.to_widget) if do_transform else nullcontext():
                super().on_touch_down(touch)
        finally:
            touch.grab_current = original

        if not do_touch_up:
            return
        await ak.sleep(.1)

        # simulate 'on_touch_up'
        to_widget = self.to_widget if self.parent is None else self.parent.to_widget
        touch.grab_current = None
        with temp_transform(touch, to_widget):
            super().on_touch_up(touch)

        # simulate the grabbed one as well
        for x in tuple(touch.grab_list):
            touch.grab_list.remove(x)
            x = x()
            if x is None:
                continue
            touch.grab_current = x
            with temp_transform(touch, x.parent.to_widget):
                x.dispatch('on_touch_up', touch)

        touch.grab_current = None
        return

    def on_drag_start(self, touch, ctx: DragContext):
        pass

    def on_drag_end(self, touch, ctx: DragContext):
        pass

    def on_drag_succeed(self, touch, ctx: DragContext):
        original_state = ctx.original_state
        self.parent.remove_widget(self)
        self.size_hint_x = original_state['size_hint_x']
        self.size_hint_y = original_state['size_hint_y']
        self.pos_hint = original_state['pos_hint']
        ctx.droppable.add_widget(self, index=touch.ud.get('kivyx_droppable_index', 0))

    async def on_drag_fail(self, touch, ctx: DragContext):
        await ak.animate(
            self, duration=.1,
            x=ctx.original_pos_win[0],
            y=ctx.original_pos_win[1],
        )
        restore_widget_state(self, ctx.original_state)

    def on_drag_cancel(self, touch, ctx: DragContext):
        restore_widget_state(self, ctx.original_state)


def ongoing_drags(*, window=kivy.core.window.Window) -> List[KXDraggableBehavior]:
    '''Returns a list of draggables currently being dragged'''
    return [
        c for c in window.children
        # maybe it's better not to check the type, like:
        # getattr(c, 'is_being_dragged', False)
        if isinstance(c, KXDraggableBehavior) and c.is_being_dragged
    ]


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

    def accepts_drag(self, touch, ctx: DragContext, draggable: KXDraggableBehavior) -> bool:
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

    def __init__(self, **kwargs):
        self._active_spacers = []
        self._inactive_spacers = None
        Clock.schedule_once(self._init_spacers)
        super().__init__(**kwargs)
        self.__ud_key = 'KXReorderableBehavior.' + str(self.uid)

    def accepts_drag(self, touch, ctx: DragContext, draggable: KXDraggableBehavior) -> bool:
        '''Determines whether the reorderable is willing to accept the drag'''
        return True

    def _init_spacers(self, dt):
        if self._inactive_spacers is None:
            self.spacer_widgets.append(_create_spacer())

    def on_spacer_widgets(self, __, spacer_widgets):
        if self._active_spacers:
            raise Exception("Do not change the 'spacer_widgets' when there is an ongoing drag.")
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
        if ud_key not in touch_ud and self._inactive_spacers and self.collide_point(*touch.pos):
            drag_cls = touch_ud.get('kivyx_drag_cls', None)
            if drag_cls is not None:
                touch_ud[ud_key] = None
                if drag_cls in self.drag_classes:
                    ak.start(ak.wait_any(
                        self._watch_touch(touch),
                        ak.event(touch.ud['kivyx_draggable'], 'on_drag_end'),
                    ))
        return super().on_touch_move(touch)

    async def _watch_touch(self, touch):
        spacer = self._inactive_spacers.pop()
        self._active_spacers.append(spacer)

        # LOAD_FAST
        collide_point = self.collide_point
        get_drop_insertion_index_move = self.get_drop_insertion_index_move
        remove_widget = self.remove_widget
        add_widget = self.add_widget
        touch_ud = touch.ud

        try:
            restore_widget_state(
                spacer,
                touch_ud['kivyx_drag_ctx'].original_state,
                ignore_parent=True)
            add_widget(spacer)
            async with ak.watch_touch(self, touch) as in_progress:
                while await in_progress():
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
