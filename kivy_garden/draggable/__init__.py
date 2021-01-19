"""
Draggable
=========

Inspired by:

* `drag_n_drop (Kivy Garden)`_
* Flutter_

This adds a drag and drop functionality to layouts and widgets. There are 3
components used to have drag and drop:

* The :class:`KXDraggableBehavior`. An equivalent of drag_n_drop's
  ``DraggableObjectBehavior``.
* The :class:`KXReorderableBehavior`. An equivalent of drag_n_drop's
  ``DraggableLayoutBehavior``.
* The :class:`KXDroppableBehavior`. An equivalent of Flutter's
  ``DragTarget``.

Main differences from drag_n_drop
---------------------------------

* Drag is triggered by long-press. More precisely, when a finger of the user
  touched inside a draggable widget, if the finger stays for ``drag_timeout``
  milli seconds without traveling more than ``drag_distance`` pixels, it will
  be recognized as a dragging gesture.
* :class:`KXReorderableBehavior` can handle multiple drags simultaneously.
* Drag can be cancelled by calling ``KXDraggableBehavior.drag_cancel()``.
* Nested ``KXReorderableBehavior`` is not officially supported. It may or may
  not work depending on how ``drag_classes`` and ``drag_cls`` are set.

.. _drag_n_drop (Kivy Garden): https://github.com/kivy-garden/drag_n_drop
.. _Flutter: https://api.flutter.dev/flutter/widgets/Draggable-class.html
"""

__all__ = (
    'KXDraggableBehavior', 'KXDroppableBehavior', 'KXReorderableBehavior',
    'save_widget_location', 'restore_widget_location', 'DragContext',
)

from ._version import __version__
from ._impl import (
    KXDraggableBehavior, KXDroppableBehavior, KXReorderableBehavior,
    save_widget_location, restore_widget_location, DragContext,
)
