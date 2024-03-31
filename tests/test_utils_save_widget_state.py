import pytest


@pytest.mark.parametrize('ignore_parent', (True, False, ))
def test_no_parent(ignore_parent):
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import save_widget_state
    w = Widget()
    state = save_widget_state(w, ignore_parent=ignore_parent)
    expectation = {
        'x': 0, 'y': 0, 'width': 100, 'height': 100,
        'size_hint_x': 1, 'size_hint_y': 1, 'pos_hint': {},
        'size_hint_min_x': None, 'size_hint_min_y': None,
        'size_hint_max_x': None, 'size_hint_max_y': None,
        'parent': None,
    }
    if ignore_parent:
        del expectation['parent']
    assert state == expectation


@pytest.mark.parametrize('ignore_parent', (True, False, ))
def test_has_parent(ignore_parent):
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import save_widget_state
    parent = Widget()
    w = Widget()
    parent.add_widget(w)
    parent.add_widget(Widget())
    state = save_widget_state(w, ignore_parent=ignore_parent)
    expectation = {
        'x': 0, 'y': 0, 'width': 100, 'height': 100,
        'size_hint_x': 1, 'size_hint_y': 1, 'pos_hint': {},
        'size_hint_min_x': None, 'size_hint_min_y': None,
        'size_hint_max_x': None, 'size_hint_max_y': None,
        'parent': parent, 'index': 1,
    }
    if ignore_parent:
        del expectation['parent']
        del expectation['index']
    assert state == expectation


@pytest.mark.parametrize('ignore_parent', (True, False, ))
def test_pos_hint_is_deepcopied(ignore_parent):
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import save_widget_state
    w = Widget(pos_hint={'center': [.5, .5, ], })
    state = save_widget_state(w, ignore_parent=ignore_parent)
    state['pos_hint']['center'][0] = 0
    state['pos_hint']['x'] = 0
    assert w.pos_hint == {'center': [.5, .5, ], }
