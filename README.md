# Draggable

![](http://img.youtube.com/vi/CjiRZjiSqgA/0.jpg)  
[Youtube][youtube]  
[README(Japanese)](README_jp.md)  

Inspired by:

* [drag_n_drop][drag_n_drop] (`Draggable` is based on this, so reading its documentation may help you understand `Draggable`)
* [Flutter][flutter]

This flower adds a drag and drop functionality to layouts and widgets. There are 3
main components used to have drag and drop:

- The `KXDraggableBehavior`. An equivalent of drag_n_drop's
  `DraggableObjectBehavior`.
- The `KXReorderableBehavior`. An equivalent of drag_n_drop's
  `DraggableLayoutBehavior`.
- The `KXDroppableBehavior`. An equivalent of Flutter's `DragTarget`.

From now on, I use the term `droppable` to refer both `KXReorderableBehavior` and `KXDroppableBehavior`, and use the term `draggable` to refer `KXDraggableBehavior`.

## Installation

Pin the minor version.

```
poetry add kivy_garden.draggable@~0.2
pip install "kivy_garden.draggable>=0.2,<0.3"
```

## Main differences from drag_n_drop

- Drag is triggered by a long-press. More precisely, when a finger of the user
  dropped inside a draggable, if the finger stays for `draggable.drag_timeout`
  milli seconds without traveling more than `draggable.drag_distance` pixels, it will
  be recognized as a dragging gesture.
- Droppables can handle multiple drags simultaneously.
- Drag can be canceled by calling `draggable.drag_cancel()`.
- Nested `KXReorderableBehavior` is not officially supported. It may or may
  not work depending on how `drag_classes` and `drag_cls` are set.

## Flow

Once a drag has started, it will go through the following path.

```mermaid
stateDiagram-v2
    state cancelled? <<choice>>
    state on_a_droppable? <<choice>>
    state listed? <<choice>>
    state accepted? <<choice>>

    [*] --> on_drag_start
    on_drag_start --> cancelled?
    cancelled? --> on_a_droppable?: User lifted their finger up
    cancelled? --> on_drag_cancel: 'draggable.cancel()' was called before the user lifts their finger up

    on_a_droppable? --> listed?: Finger was on a droppable
    on_a_droppable? --> on_drag_fail: not on a droppable

    droppable_is_set: 'ctx.droppable' is set to the droppable
    listed? --> droppable_is_set: 'draggable.drag_cls' was listed in the 'droppable.drag_classes'
    listed? --> on_drag_fail: not listed

    droppable_is_set --> accepted?
    accepted? --> on_drag_succeed: Droppable accepted the drag ('droppable.accepts_drag()' returned True.)
    accepted? --> on_drag_fail

    on_drag_cancel --> on_drag_end
    on_drag_fail --> on_drag_end
    on_drag_succeed --> on_drag_end

    on_drag_end --> [*]
```

## Cancellation

When your app changes scenes, you might want to cancel all ongoing drags.
For this, you can use `ongoing_drags()` and `draggable.drag_cancel()`.

```python
from kivy_garden.draggable import ongoing_drags

def cancel_all_ongoing_drags():
    for draggable in ongoing_drags():
        draggable.drag_cancel()
```

## Using other widgets as emitters

Imagine you're creating a card game, and there's a deck on the screen.
Suppose you want the deck to emit a card when the user places a finger on it, and you want the card to follow the finger until the user lifts it.
In this scenario, the widget that triggers the drag and the widget being dragged are distinct.
Here's how you can implement it:

```python
class Card(KXDraggableBehavior, Widget):
    pass


class Deck(Widget):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.opos):
            Card(...).start_dragging_from_others_touch(self, touch)
```

## Customization

The behavior of `on_drag_succeed`, `on_drag_fail`, and `on_drag_cancel` for draggables is fully customizable.
For instance, by default, when a drag fails, the draggable returns to its original position with a brief animation.
This happens because the default handler for `on_drag_fail` is implemented as follows:

```python
class KXDraggableBehavior:
    async def on_drag_fail(self, touch, ctx):
        await ak.anim_attrs(
            self, duration=.1,
            x=ctx.original_pos_win[0],
            y=ctx.original_pos_win[1],
        )
        restore_widget_state(self, ctx.original_state)
```

If you don't need the animation and want the draggable to return instantly, you can override the handler like this:

```python
class MyDraggable(KXDraggableBehavior, Widget):
    def on_drag_fail(self, touch, ctx):
        restore_widget_state(self, ctx.original_state)
```

Or, if you'd prefer the draggable to stay in its current position and not return at all, override the handler as follows:

```python
class MyDraggable(KXDraggableBehavior, Widget):
    def on_drag_fail(self, touch, ctx):
        pass
```

Another example: by default, when a drag succeeds, the draggable becomes a child of the droppable.
If you don't like this behavior and prefer the draggable to fade out instead, you can override the handler like this:

```python
class MyDraggable(KXDraggableBehavior, Widget):
    async def on_drag_succeed(self, touch, ctx):
        import asynckivy
        await asynckivy.anim_attrs(self, opacity=0)
        self.parent.remove_widget(self)
```

As you can see, you have full control to customize these behaviors.
However, note that only the default handlers for `on_drag_succeed` and `on_drag_fail` can be async functions—just those two.

You might wonder, "Why implement a default handler as an async function when you can simply launch tasks from a regular function using `asynckivy.start()`?"
The key difference is that tasks started with `asynckivy.start()` run independently of the dragging process.
This means the draggable might trigger `on_drag_end` and even start another drag while the task is still running.
In contrast, if the default handler is an async function, its code is integrated into the dragging process and is guaranteed to finish before `on_drag_end` is triggered.

## License

MIT

[drag_n_drop]:https://github.com/kivy-garden/drag_n_drop
[flutter]:https://api.flutter.dev/flutter/widgets/Draggable-class.html
[youtube]:https://www.youtube.com/playlist?list=PLNdhqAjzeEGiepWKfP43Dh7IWqn3cQtpQ
