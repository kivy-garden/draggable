import pytest


def test_flower():
    from kivy_garden.draggable import (
        DragContext,
        KXDraggableBehavior, KXDroppableBehavior, KXReorderableBehavior,
        restore_widget_state, save_widget_state,
        restore_widget_location, save_widget_location, ongoing_drags,
    )
