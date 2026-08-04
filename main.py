"""Interfaz de chat en Kivy, pensada para pantalla táctil (Android).
- Burbujas de conversación con scroll automático.
- Respuestas en hilo aparte para no congelar la UI.
- Botón de voz on/off y revisión periódica de recordatorios.
"""

from __future__ import annotations
import threading

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.utils import get_color_from_hex as hexc

# Variables de configuración integradas por defecto
AI_NAME = "Edson"
VERSION = "1.0.0"
ANDROID = True  # Ajustado para compilación móvil

BG = hexc("#0F1620")
BAR = hexc("#152233")
USER_BUBBLE = hexc("#2F6FED")
AI_BUBBLE = hexc("#1E2B3C")
TEXT = hexc("#F2F5F9")
MUTED = hexc("#93A4BB")


class Burbuja(BoxLayout):
    def __init__(self, texto: str, propio: bool, **kw):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            padding=(dp(8), dp(4)),
            **kw,
        )
        color = USER_BUBBLE if propio else AI_BUBBLE
        label = Label(
            text=texto,
            color=TEXT,
            size_hint_x=0.82,
            halign="right" if propio else "left",
            valign="middle",
            padding=(dp(12), dp(10)),
            markup=True,
        )
        label.bind(width=lambda i, w: setattr(i, "text_size", (w - dp(24), None)))
        label.bind(texture_size=self._ajustar)
        self._label = label

        from kivy.graphics import Color, RoundedRectangle

        with label.canvas.before:
            Color(*color)
            self._rect = RoundedRectangle(radius=[dp(16)])
        label.bind(pos=self._redraw, size=self._redraw)

        if propio:
            self.add_widget(Label(size_hint_x=0.18))
            self.add_widget(label)
        else:
            self.add_widget(label)
            self.add_widget(Label(size_hint_x=0.18))

    def _redraw(self, *_):
        self._rect.pos = self._label.pos
        self._rect.size = self._label.size

    def _ajustar(self, instance, size):
        instance.height = size[1] + dp(20)
        self.height = instance.height + dp(8)


class ChatRoot(BoxLayout):
    def __init__(self, brain_instance, **kw):
        super().__init__(orientation="vertical", **kw)
        self.brain = brain_instance

        from kivy.graphics import Color, Rectangle

        with self.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_bg, size=self._sync_bg)

        self.add_widget(self._header())

        self.scroll = ScrollView(do_scroll_x=False)
        self.lista = BoxLayout(
            orientation="vertical", size_hint_y=None, padding=(0, dp(8))
        )
        self.lista.bind(minimum_height=self.lista.setter("height"))
        self.scroll.add_widget(self.lista)
        self.add_widget(self.scroll)

        self.add_widget(self._composer())

        # Mensaje de bienvenida inicial
        self.mensaje(f"¡Hola! Soy {AI_NAME} AI. ¿En qué te ayudo hoy?", propio=False)

    def _sync_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _panel(self, height):
        panel = BoxLayout(
            size_hint_y=None, height=height, padding=(dp(12), dp(8)), spacing=dp(8)
        )
        from kivy.graphics import Color, Rectangle

        with panel.canvas.before:
            Color(*BAR)
            rect = Rectangle(pos=panel.pos, size=panel.size)
        panel.bind(
            pos=lambda i, v: setattr(rect, "pos", v),
            size=lambda i, v: setattr(rect, "size", v),
        )
        return panel

    def _header(self):
        header = self._panel(dp(64))
        titulo = Label(
            text=f"[b]{AI_NAME} AI[/b]\n[size=12sp]v{VERSION} · asistente personal[/size]",
            markup=True,
            color=TEXT,
            halign="left",
            valign="middle",
        )
        titulo.bind(size=lambda i, s: setattr(i, "text_size", s))
        header.add_widget(titulo)
        return header

    def _composer(self):
        barra = self._panel(dp(72))
        self.entrada = TextInput(
            hint_text="Escribe tu mensaje…",
            multiline=False,
            background_color=hexc("#0F1620"),
            foreground_color=TEXT,
            cursor_color=USER_BUBBLE,
            padding=(dp(12), dp(14)),
            font_size="16sp",
        )
        self.entrada.bind(on_text_validate=lambda *_: self.enviar())
        enviar = Button(
            text="Enviar",
            size_hint_x=None,
            width=dp(88),
            background_normal="",
            background_color=USER_BUBBLE,
            color=TEXT,
            bold=True,
        )
        enviar.bind(on_release=lambda *_: self.enviar())
        barra.add_widget(self.entrada)
        barra.add_widget(enviar)
        return barra

    @mainthread
    def mensaje(self, texto: str, propio: bool) -> None:
        self.lista.add_widget(Burbuja(texto, propio))
        Clock.schedule_once(lambda *_: setattr(self.scroll, "scroll_y", 0), 0.05)

    def enviar(self) -> None:
        texto = self.entrada.text.strip()
        if not texto:
            return
        self.entrada.text = ""
        self.mensaje(texto, propio=True)
        threading.Thread(target=self._responder, args=(texto,), daemon=True).start()

    def _responder(self, texto: str) -> None:
        try:
            respuesta = self.brain.answer(texto)
        except Exception as exc:
            respuesta = f"Ocurrió un error: {exc}"
        self.mensaje(respuesta, propio=False)


class EdsonApp(App):
    title = f"{AI_NAME} AI"

    def build(self):
        from brain import Brain
        self.brain = Brain()
        return ChatRoot(self.brain)


if __name__ == "__main__":
    EdsonApp().run()