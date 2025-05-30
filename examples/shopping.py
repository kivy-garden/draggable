'''
https://www.youtube.com/watch?v=PNj8uEdd5c0

To animate widgets like in the video: pip install kivy-garden-posani
'''

from collections.abc import Iterable
import itertools
from contextlib import closing
from os import PathLike
import sqlite3
from dataclasses import dataclass

from kivy.app import App
from kivy.properties import ObjectProperty
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.factory import Factory as F
import asynckivy as ak
from kivy_garden.draggable import KXDraggableBehavior

try:
    from kivy_garden import posani
    posani.install(target="SHFood")
except ImportError:
    import types

    def do_nothing(*args, **kwargs):
        pass
    posani = types.SimpleNamespace(
        activate=do_nothing,
        deactivate=do_nothing,
    )


def detect_image_format(image_data: bytes) -> str:
    if image_data.startswith(b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A"):
        return "png"
    elif image_data.startswith(b"\xFF\xD8"):
        return "jpg"
    raise ValueError("Unknown image format")


KV_CODE = r'''
#:import ak asynckivy
#:import posani __main__.posani

<SHLabel@Label,SHButton@Button>:
    size_hint_min: [v + dp(8) for v in self.texture_size]
    halign: 'center'

<SHFood>:
    orientation: 'vertical'
    spacing: '4dp'
    drag_timeout: 0
    drag_cls: 'food'
    size: '200dp', '200dp'
    size_hint: None, None
    opacity: .5 if self.is_being_dragged else 1.
    on_drag_start: posani.deactivate(self)
    on_drag_end: posani.activate(self)
    canvas.before:
        Color:
            rgba: .4, .4, .4, 1
        Line:
            rectangle: (*self.pos, *self.size, )
    Image:
        fit_mode: "contain"
        texture: root.datum.texture
        size_hint_y: 3.
    SHLabel:
        text: '{} ({} yen)'.format(root.datum.name, root.datum.price)

<SHShelf@KXReorderableBehavior+SemiRecycleBehavior+StackLayout>:
    padding: '10dp'
    spacing: '10dp'
    size_hint_min_y: self.minimum_height
    drag_classes: ['food', ]
    viewclass: 'SHFood'

<SHMain>:
    orientation: 'vertical'
    padding: '10dp'
    spacing: '10dp'
    EquitableBoxLayout:
        BoxLayout:
            orientation: 'vertical'
            SHLabel:
                text: 'Shelf'
                font_size: max(20, sp(16))
                bold: True
                color: rgba("#44AA44")
            ScrollView:
                size_hint_y: 1000.
                always_overscroll: False
                do_scroll_x: False
                SHShelf:
                    id: shelf
        Splitter:
            sizable_from: 'left'
            min_size: 100
            max_size: root.width
            BoxLayout:
                orientation: 'vertical'
                SHLabel:
                    text: 'Your Shopping Cart'
                    font_size: max(20, sp(16))
                    bold: True
                    color: rgba("#4466FF")
                ScrollView:
                    size_hint_y: 1000.
                    always_overscroll: False
                    do_scroll_x: False
                    SHShelf:
                        id: cart
    BoxLayout:
        size_hint_y: None
        height: self.minimum_height
        SHButton:
            text: 'sort by price\n(ascend)'
            on_press: shelf.data = sorted(shelf.data, key=lambda d: d.price)
        SHButton:
            text: 'sort by price\n(descend)'
            on_press: shelf.data = sorted(shelf.data, key=lambda d: d.price, reverse=True)
        SHButton:
            text: 'sort by name\n(ascend)'
            on_press: shelf.data = sorted(shelf.data, key=lambda d: d.name)
        SHButton:
            text: 'sort by name\n(descend)'
            on_press: shelf.data = sorted(shelf.data, key=lambda d: d.name, reverse=True)
        Widget:
        SHButton:
            text: 'total price'
            on_press: ak.managed_start(root.show_total_price())
        SHButton:
            text: 'sort by price\n(ascend)'
            on_press: cart.data = sorted(cart.data, key=lambda d: d.price)
        SHButton:
            text: 'sort by price\n(descend)'
            on_press: cart.data = sorted(cart.data, key=lambda d: d.price, reverse=True)
'''


@dataclass
class Food:
    name: str = ''
    price: int = 0
    texture: F.Texture = None


class ShoppingApp(App):
    def build(self):
        Builder.load_string(KV_CODE)
        return SHMain()

    def on_start(self):
        self.root.main(db_path=__file__ + r".sqlite3")


class SHMain(F.BoxLayout):
    async def show_total_price(self, *, _cache=[]):
        popup = _cache.pop() if _cache else F.Popup(
            size_hint=(.5, .2, ),
            title="Total",
            title_size="20sp",
            content=F.Label(font_size="20sp"),
        )
        total_price = sum(d.price for d in self.ids.cart.data)
        popup.content.text = f"{total_price} yen"
        popup.open()
        try:
            await ak.event(popup, "on_dismiss")
        finally:
            await ak.sleep(popup._anim_duration + 0.1)
            _cache.append(popup)

    def main(self, db_path: PathLike):
        import os.path
        from random import randint

        if not os.path.exists(db_path):
            try:
                self._init_database(db_path)
            except Exception:
                os.remove(db_path)
                raise
        self.ids.shelf.data = [
            food
            for food in self._load_database(db_path)
            for __ in range(randint(2, 4))
        ]

    @staticmethod
    def _load_database(db_path: PathLike) -> list[Food]:
        from io import BytesIO
        from kivy.core.image import Image as CoreImage

        with sqlite3.connect(str(db_path)) as conn:
            # FIXME: It's probably better to ``Texture.add_reload_observer()``.
            return [
                Food(name=name, price=price, texture=CoreImage(BytesIO(image_data), ext=image_type).texture)
                for name, price, image_data, image_type in conn.execute("SELECT name, price, image, image_type FROM Foods")
            ]

    @staticmethod
    def _init_database(db_path: PathLike):
        import requests

        FOOD_DATA = (
            # (name, price, image_url)
            ("blueberry", 500, r"https://3.bp.blogspot.com/-RVk4JCU_K2M/UvTd-IhzTvI/AAAAAAAAdhY/VMzFjXNoRi8/s180-c/fruit_blueberry.png"),
            ("cacao", 800, r"https://3.bp.blogspot.com/-WT_RsvpvAhc/VPQT6ngLlmI/AAAAAAAAsEA/aDIU_F9TYc8/s180-c/fruit_cacao_kakao.png"),
            ("dragon fruit", 1200, r"https://1.bp.blogspot.com/-hATAhM4UmCY/VGLLK4mVWYI/AAAAAAAAou4/-sW2fvsEnN0/s180-c/fruit_dragonfruit.png"),
            ("kiwi", 130, r"https://2.bp.blogspot.com/-Y8xgv2nvwEs/WCdtGij7aTI/AAAAAAAA_fo/PBXfb8zCiQAZ8rRMx-DNclQvOHBbQkQEwCLcB/s180-c/fruit_kiwi_green.png"),
            ("lemon", 200, r"https://2.bp.blogspot.com/-UqVL2dBOyMc/WxvKDt8MQbI/AAAAAAABMmk/qHrz-vwCKo8okZsZpZVDsHLsKFXdI1BjgCLcBGAs/s180-c/fruit_lemon_tategiri.png"),
            ("mangosteen", 300, r"https://4.bp.blogspot.com/-tc72dGzUpww/WGYjEAwIauI/AAAAAAABAv8/xKvtWmqeKFcro6otVdLi5FFF7EoVxXiEwCLcB/s180-c/fruit_mangosteen.png"),
            ("apple", 150, r"https://4.bp.blogspot.com/-uY6ko43-ABE/VD3RiIglszI/AAAAAAAAoEA/kI39usefO44/s180-c/fruit_ringo.png"),
            ("orange", 100, r"https://1.bp.blogspot.com/-fCrHtwXvM6w/Vq89A_TvuzI/AAAAAAAA3kE/fLOFjPDSRn8/s180-c/fruit_slice10_orange.png"),
            ("soldum", 400, r"https://2.bp.blogspot.com/-FtWOiJkueNA/WK7e09oIUyI/AAAAAAABB_A/ry22yAU3W9sbofMUmA5-nn3D45ix_Y5RwCLcB/s180-c/fruit_soldum.png"),
            ("corn", 50, r"https://1.bp.blogspot.com/-RAJBy7nx2Ro/XkZdTINEtOI/AAAAAAABXWE/x8Sbcghba9UzR8Ppafozi4_cdmD1pawowCNcBGAsYHQ/s180-c/vegetable_toumorokoshi_corn_wagiri.png"),
            ("aloe", 400, r"https://4.bp.blogspot.com/-v7OAB-ULlrs/VVGVQ1FCjxI/AAAAAAAAtjg/H09xS1Nf9_A/s180-c/plant_aloe_kaniku.png"),
        )
        with requests.Session() as session:
            FOOD_DATA = tuple(
                (name, price, c := session.get(image_url).content, detect_image_format(c))
                for name, price, image_url in FOOD_DATA
            )
        with sqlite3.connect(str(db_path)) as conn, closing(conn.cursor()) as cur:
            cur.execute("""
                CREATE TABLE Foods (
                    name TEXT NOT NULL UNIQUE,
                    price INT NOT NULL,
                    image BLOB NOT NULL,
                    image_type TEXT NOT NULL,
                    PRIMARY KEY (name)
                );
            """)
            cur.executemany("INSERT INTO Foods(name, price, image, image_type) VALUES (?, ?, ?, ?)", FOOD_DATA)


class SHFood(KXDraggableBehavior, F.BoxLayout):
    datum: Food = ObjectProperty(Food(), rebind=True)


class EquitableBoxLayout(F.BoxLayout):
    '''Always dispatches touch events to all its children'''
    def on_touch_down(self, touch):
        return any([c.dispatch('on_touch_down', touch) for c in self.children])
    def on_touch_move(self, touch):
        return any([c.dispatch('on_touch_move', touch) for c in self.children])
    def on_touch_up(self, touch):
        return any([c.dispatch('on_touch_up', touch) for c in self.children])


class SemiRecycleBehavior:
    '''
    Mix-in class that adds RecyclewView-like interface to layouts.
    But unlike RecycleView, this one creates view widgets as much as the number of the data.
    '''

    viewclass = ObjectProperty()
    '''widget-class or its name'''

    def __init__(self, **kwargs):
        self._rv_refresh_params = {}
        self._rv_trigger_refresh = Clock.create_trigger(self._rv_refresh, -1)
        super().__init__(**kwargs)

    def on_viewclass(self, *args):
        self._rv_refresh_params['viewclass'] = None
        self._rv_trigger_refresh()

    def _get_data(self) -> Iterable:
        data = self._rv_refresh_params.get('data')
        return [c.datum for c in reversed(self.children)] if data is None else data

    def _set_data(self, new_data: Iterable):
        self._rv_refresh_params['data'] = new_data
        self._rv_trigger_refresh()

    data = property(_get_data, _set_data)

    def _rv_refresh(self, *args):
        viewclass = self.viewclass
        if not viewclass:
            self.clear_widgets()
            return
        data = self.data
        params = self._rv_refresh_params
        reusable_widgets = '' if 'viewclass' in params else self.children[::-1]
        self.clear_widgets()
        if isinstance(viewclass, str):
            viewclass = F.get(viewclass)
        for datum, w in zip(data, itertools.chain(reusable_widgets, iter(viewclass, None))):
            w.datum = datum
            self.add_widget(w)
        params.clear()
F.register("SemiRecycleBehavior", cls=SemiRecycleBehavior)


if __name__ == '__main__':
    ShoppingApp().run()
