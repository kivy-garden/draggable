import pytest


@pytest.fixture(scope='module')
def state_factory():
    from copy import deepcopy
    state = {
        'x': 2, 'y': 2, 'width': 2, 'height': 2,
        'size_hint_x': 2, 'size_hint_y': 2,
        'pos_hint': {'center': [2, 2, ], },
        'size_hint_min_x': 2, 'size_hint_min_y': 2,
        'size_hint_max_x': 2, 'size_hint_max_y': 2,
    }
    return lambda: deepcopy(state)


@pytest.mark.parametrize('ignore_parent', (True, False, ))
def test_sizing_info(state_factory, ignore_parent):
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import restore_widget_state
    w = Widget()
    state = state_factory()
    restore_widget_state(w, state, ignore_parent=ignore_parent)
    state['width'] = 0
    state['x'] = 0
    state['size_hint_x'] = 0
    state['pos_hint']['center'][0] = 0
    state['size_hint_min_x'] = 0
    state['size_hint_min_y'] = 0
    assert w.size == [2, 2, ]
    assert w.pos == [2, 2, ]
    assert w.size_hint == [2, 2, ]
    assert w.pos_hint == {'center': [2, 2, ], }
    assert w.size_hint_min == [2, 2, ]
    assert w.size_hint_max == [2, 2, ]


@pytest.mark.parametrize('ignore_parent', (True, False, ))
@pytest.mark.parametrize('has_parent', (True, False, ))
def test_parent_is_none(state_factory, ignore_parent, has_parent):
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import restore_widget_state
    state = state_factory()
    state['parent'] = None
    w = Widget()
    if has_parent:
        parent = Widget()
        parent.add_widget(w)
    restore_widget_state(w, state, ignore_parent=ignore_parent)
    if ignore_parent and has_parent:
        assert w.parent is parent
    else:
        assert w.parent is None


@pytest.mark.parametrize('ignore_parent', (True, False, ))
@pytest.mark.parametrize('has_parent', (True, False, ))
def test_parent_not_in_the_dict(state_factory, ignore_parent, has_parent):
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import restore_widget_state
    state = state_factory()
    assert 'parent' not in state
    w = Widget()
    if has_parent:
        parent = Widget()
        parent.add_widget(w)
    restore_widget_state(w, state, ignore_parent=ignore_parent)
    if has_parent:
        assert w.parent is parent
    else:
        assert w.parent is None


@pytest.mark.parametrize('ignore_parent', (True, False, ))
@pytest.mark.parametrize('has_parent', (True, False, ))
def test_parent_is_not_none(state_factory, ignore_parent, has_parent):
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import restore_widget_state
    prev_parent = Widget()
    state = state_factory()
    state['parent'] = prev_parent
    state['index'] = 0
    w = Widget()
    if has_parent:
        parent = Widget()
        parent.add_widget(w)
        parent.add_widget(Widget())
        assert parent.children.index(w) == 1
    restore_widget_state(w, state, ignore_parent=ignore_parent)
    if ignore_parent:
        if has_parent:
            assert w.parent is parent
            assert parent.children.index(w) == 1
        else:
            assert w.parent is None
    else:
        assert w.parent is prev_parent
        assert prev_parent.children.index(w) == 0
