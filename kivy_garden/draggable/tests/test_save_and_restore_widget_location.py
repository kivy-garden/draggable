def test_no_parent():
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import \
        save_widget_location, restore_widget_location
    w = Widget()
    location = save_widget_location(w)
    assert location == {
        'x': 0, 'y': 0, 'width': 100, 'height': 100,
        'size_hint_x': 1, 'size_hint_y': 1,
        'pos_hint': {},
        'size_hint_min_x': None, 'size_hint_min_y': None,
        'size_hint_max_x': None, 'size_hint_max_y': None,
    }
    w.pos = [20, 20, ]
    w.size = [40, 40, ]
    w.size_hint = [None, None, ]
    w.pos_hint = {'x': 1, 'top': .5, }
    w.size_hint_min = [30, 30, ]
    w.size_hint_max = [70, 70, ]
    restore_widget_location(w, location)
    assert w.size == [100, 100, ]
    assert w.pos == [0, 0, ]
    assert w.size_hint == [1, 1, ]
    assert w.pos_hint == {}
    assert w.size_hint_min == [None, None, ]
    assert w.size_hint_max == [None, None, ]


def test_parent_is_alive():
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import \
        save_widget_location, restore_widget_location
    parent = Widget()
    parent.add_widget(Widget())
    parent.add_widget(Widget())
    w = Widget()
    parent.add_widget(w)
    parent.add_widget(Widget())
    location = save_widget_location(w)
    assert location['index'] == 1
    assert location['weak_parent']() is parent
    parent.remove_widget(w)
    restore_widget_location(w, location)
    assert w.parent is parent
    assert parent.children.index(w) == 1


def test_parent_is_dead():
    import gc
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import \
        save_widget_location, restore_widget_location
    parent = Widget()
    parent.add_widget(Widget())
    parent.add_widget(Widget())
    w = Widget()
    parent.add_widget(w)
    parent.add_widget(Widget())
    location = save_widget_location(w)
    assert location['index'] == 1
    assert location['weak_parent']() is parent
    parent.remove_widget(w)
    del parent
    gc.collect()
    assert location['index'] == 1
    assert location['weak_parent']() is None
    restore_widget_location(w, location)
    assert w.parent is None


def test__save_when_widget_has_no_parent__restore_when_widget_has_parent():
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import \
        save_widget_location, restore_widget_location
    w = Widget()
    location = save_widget_location(w)
    assert 'index' not in location
    assert 'weak_parent' not in location
    parent = Widget()
    parent.add_widget(Widget())
    parent.add_widget(Widget())
    parent.add_widget(w)
    parent.add_widget(Widget())
    assert parent.children.index(w) == 1
    restore_widget_location(w, location)
    assert w.parent is parent
    assert parent.children.index(w) == 1


def test_pos_hint_is_isolated():
    from kivy.uix.widget import Widget
    from kivy_garden.draggable import \
        save_widget_location, restore_widget_location
    w = Widget()
    location = save_widget_location(w)
    assert w.pos_hint == {}
    assert location['pos_hint'] == {}
    w.pos_hint['x'] = 0
    assert location['pos_hint'] == {}
    location['pos_hint']['y'] = 0
    restore_widget_location(w, location)
    assert w.pos_hint == {'y': 0, }
    location['pos_hint']['center_x'] = 0
    assert w.pos_hint == {'y': 0, }
