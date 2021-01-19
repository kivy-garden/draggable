import pytest


def test_flower():
    from kivy_garden.draggable import (
        KXDraggableBehavior, KXDroppableBehavior, KXReorderableBehavior,
        restore_widget_location, save_widget_location, DragContext,
    )
