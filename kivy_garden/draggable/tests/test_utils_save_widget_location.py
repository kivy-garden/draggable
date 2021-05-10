import pytest


@pytest.mark.parametrize('ignore_parent', (True, False, ))
def test_no_parent(ignore_parent):
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import save_widget_location
    w = Widget()
    location = save_widget_location(w, ignore_parent=ignore_parent)
    expectation = {
        'x': 0, 'y': 0, 'width': 100, 'height': 100,
        'size_hint_x': 1, 'size_hint_y': 1, 'pos_hint': {},
        'size_hint_min_x': None, 'size_hint_min_y': None,
        'size_hint_max_x': None, 'size_hint_max_y': None,
        'weak_parent': None,
    }
    if ignore_parent:
        del expectation['weak_parent']
    assert location == expectation


@pytest.mark.parametrize('ignore_parent', (True, False, ))
def test_has_parent(ignore_parent):
    import weakref
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import save_widget_location
    parent = Widget()
    w = Widget()
    parent.add_widget(w)
    parent.add_widget(Widget())
    location = save_widget_location(w, ignore_parent=ignore_parent)
    expectation = {
        'x': 0, 'y': 0, 'width': 100, 'height': 100,
        'size_hint_x': 1, 'size_hint_y': 1, 'pos_hint': {},
        'size_hint_min_x': None, 'size_hint_min_y': None,
        'size_hint_max_x': None, 'size_hint_max_y': None,
        'weak_parent': weakref.ref(parent), 'index': 1,
    }
    if ignore_parent:
        del expectation['weak_parent']
        del expectation['index']
    assert location == expectation


@pytest.mark.parametrize('ignore_parent', (True, False, ))
def test_pos_hint_is_deepcopied(ignore_parent):
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import save_widget_location
    w = Widget(pos_hint={'center': [.5, .5, ], })
    location = save_widget_location(w, ignore_parent=ignore_parent)
    location['pos_hint']['center'][0] = 0
    location['pos_hint']['x'] = 0
    assert w.pos_hint == {'center': [.5, .5, ], }
