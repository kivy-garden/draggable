import pytest


@pytest.fixture(scope='module')
def location_factory():
    from copy import deepcopy
    loc = {
        'x': 2, 'y': 2, 'width': 2, 'height': 2,
        'size_hint_x': 2, 'size_hint_y': 2,
        'pos_hint': {'center': [2, 2, ], },
        'size_hint_min_x': 2, 'size_hint_min_y': 2,
        'size_hint_max_x': 2, 'size_hint_max_y': 2,
    }
    return lambda: deepcopy(loc)


@pytest.mark.parametrize('ignore_parent', (True, False, ))
def test_sizing_info(location_factory, ignore_parent):
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import restore_widget_location
    w = Widget()
    loc = location_factory()
    restore_widget_location(w, loc, ignore_parent=ignore_parent)
    loc['width'] = 0
    loc['x'] = 0
    loc['size_hint_x'] = 0
    loc['pos_hint']['center'][0] = 0
    loc['size_hint_min_x'] = 0
    loc['size_hint_min_y'] = 0
    assert w.size == [2, 2, ]
    assert w.pos == [2, 2, ]
    assert w.size_hint == [2, 2, ]
    assert w.pos_hint == {'center': [2, 2, ], }
    assert w.size_hint_min == [2, 2, ]
    assert w.size_hint_max == [2, 2, ]


@pytest.mark.parametrize('ignore_parent', (True, False, ))
@pytest.mark.parametrize('has_parent', (True, False, ))
def test_weak_parent_is_none(location_factory, ignore_parent, has_parent):
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import restore_widget_location
    loc = location_factory()
    loc['weak_parent'] = None
    w = Widget()
    if has_parent:
        parent = Widget()
        parent.add_widget(w)
    restore_widget_location(w, loc, ignore_parent=ignore_parent)
    if ignore_parent and has_parent:
        assert w.parent is parent
    else:
        assert w.parent is None


@pytest.mark.parametrize('ignore_parent', (True, False, ))
@pytest.mark.parametrize('has_parent', (True, False, ))
def test_weak_parent_not_in_the_keys(
        location_factory, ignore_parent, has_parent):
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import restore_widget_location
    loc = location_factory()
    assert 'weak_parent' not in loc
    w = Widget()
    if has_parent:
        parent = Widget()
        parent.add_widget(w)
    restore_widget_location(w, loc, ignore_parent=ignore_parent)
    if has_parent:
        assert w.parent is parent
    else:
        assert w.parent is None


@pytest.mark.parametrize('ignore_parent', (True, False, ))
@pytest.mark.parametrize('has_parent', (True, False, ))
def test_weak_parent_is_alive(
        location_factory, ignore_parent, has_parent):
    import weakref
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import restore_widget_location
    prev_parent = Widget()
    loc = location_factory()
    loc['weak_parent'] = weakref.ref(prev_parent)
    loc['index'] = 0
    w = Widget()
    if has_parent:
        parent = Widget()
        parent.add_widget(w)
        parent.add_widget(Widget())
        assert parent.children.index(w) == 1
    restore_widget_location(w, loc, ignore_parent=ignore_parent)
    if ignore_parent:
        if has_parent:
            assert w.parent is parent
            assert parent.children.index(w) == 1
        else:
            assert w.parent is None
    else:
        assert w.parent is prev_parent
        assert prev_parent.children.index(w) == 0


@pytest.mark.parametrize('ignore_parent', (True, False, ))
@pytest.mark.parametrize('has_parent', (True, False, ))
def test_weak_parent_is_dead(
        location_factory, ignore_parent, has_parent):
    import gc
    import weakref
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import restore_widget_location
    loc = location_factory()
    loc['weak_parent'] = weakref.ref(Widget())
    loc['index'] = 0
    gc.collect()
    assert loc['weak_parent']() is None
    w = Widget()
    if has_parent:
        parent = Widget()
        parent.add_widget(w)
        parent.add_widget(Widget())
        assert parent.children.index(w) == 1
    if ignore_parent:
        restore_widget_location(w, loc, ignore_parent=True)
    else:
        with pytest.raises(ReferenceError):
            restore_widget_location(w, loc, ignore_parent=False)
    if has_parent:
        assert w.parent is parent
        assert parent.children.index(w) == 1
    else:
        assert w.parent is None
