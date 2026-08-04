"""Cerebro de Edson AI: motor de intenciones extensible.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

AI_NAME = "Edson"
VERSION = "1.0.0"

# Memoria simplificada para evitar fallos por dependencias ausentes
class MemoryDummy:
    def __init__(self):
        self.datos = {}
        self._notas = []

    def recall(self, clave):
        return self.datos.get(clave)

    def remember(self, clave, valor):
        self.datos[clave] = valor

    def add_note(self, texto):
        self._notas.append({"texto": texto})

    def notes(self):
        return self._notas


Handler = Callable[["Contexto"], str]


@dataclass
class Contexto:
    texto: str
    limpio: str
    match: re.Match | None
    memory: MemoryDummy
    extra: dict = field(default_factory=dict)


@dataclass
class Skill:
    nombre: str
    patrones: list[re.Pattern]
    handler: Handler
    ayuda: str
    prioridad: int = 0


_SKILLS: list[Skill] = []


def skill(nombre: str, *patrones: str, ayuda: str = "", prioridad: int = 0):
    def deco(fn: Handler) -> Handler:
        _SKILLS.append(
            Skill(
                nombre=nombre,
                patrones=[re.compile(p, re.IGNORECASE) for p in patrones],
                handler=fn,
                ayuda=ayuda or nombre,
                prioridad=prioridad,
            )
        )
        return fn

    return deco


# --------------------------------------------------------------------------
# Habilidades (Skills)
# --------------------------------------------------------------------------
@skill("saludo", r"\b(hola|buenas|buenos dias|buenas tardes|buenas noches|que tal)\b",
       ayuda="Saludar", prioridad=1)
def _saludo(ctx: Contexto) -> str:
    nombre = ctx.memory.recall("nombre")
    hora = datetime.now().hour
    momento = "Buenos días" if hora < 12 else "Buenas tardes" if hora < 19 else "Buenas noches"
    return f"{momento}{', ' + nombre if nombre else ''}. ¿En qué te ayudo?"


@skill("identidad", r"\b(quien eres|como te llamas|tu nombre|que eres)\b",
       ayuda="Quién soy")
def _identidad(ctx: Contexto) -> str:
    return f"Soy {AI_NAME} AI, tu asistente personal (versión {VERSION})."


@skill("hora", r"\b(que hora|hora es|dime la hora)\b", ayuda="Hora actual")
def _hora(ctx: Contexto) -> str:
    return datetime.now().strftime("Son las %H:%M.")


@skill("fecha", r"\b(que fecha|fecha de hoy|que dia es|dia de hoy)\b",
       ayuda="Fecha de hoy")
def _fecha(ctx: Contexto) -> str:
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    hoy = datetime.now()
    return f"Hoy es {dias[hoy.weekday()]} {hoy:%d/%m/%Y}."


@skill("guardar_nombre", r"\b(me llamo|mi nombre es|soy)\s+(?P<valor>[a-zA-ZáéíóúñÁÉÍÓÚÑ ]{2,30})",
       ayuda="Recordar tu nombre", prioridad=2)
def _guardar_nombre(ctx: Contexto) -> str:
    valor = (ctx.match.group("valor") if ctx.match else "").strip().title()
    if not valor:
        return "¿Cómo te llamas?"
    ctx.memory.remember("nombre", valor)
    return f"Encantado, {valor}. Lo recordaré."


@skill("decir_nombre", r"\b(como me llamo|cual es mi nombre|sabes quien soy)\b",
       ayuda="Decir tu nombre", prioridad=3)
def _decir_nombre(ctx: Contexto) -> str:
    nombre = ctx.memory.recall("nombre")
    return f"Te llamas {nombre}." if nombre else "Aún no me has dicho tu nombre."


@skill("nota", r"^(anota|apunta|nota)\b[:\s]*(?P<valor>.+)$",
       ayuda="Guardar una nota", prioridad=2)
def _nota(ctx: Contexto) -> str:
    texto = ctx.match.group("valor").strip()
    ctx.memory.add_note(texto)
    return f"Nota guardada ({len(ctx.memory.notes())} en total)."


@skill("ver_notas", r"\b(mis notas|ver notas|lee mis notas|leer notas)\b",
       ayuda="Ver tus notas", prioridad=3)
def _ver_notas(ctx: Contexto) -> str:
    notas = ctx.memory.notes()[-10:]
    if not notas:
        return "No tienes notas guardadas."
    lineas = [f"{i}. {n['texto']}" for i, n in enumerate(notas, 1)]
    return "Tus últimas notas:\n" + "\n".join(lineas)


@skill("calculadora", r"^(?:calcula|cuanto es)?\s*(?P<expr>[-+*/ ()\d.,x]+)$",
       ayuda="Calcular: 'cuánto es 12*7'", prioridad=2)
def _calculadora(ctx: Contexto) -> str:
    expr = ctx.match.group("expr").replace("x", "*").replace(",", ".").strip()
    if not expr or not re.fullmatch(r"[-+*/ ()\d.]+", expr):
        return "No entendí la operación."
    try:
        resultado = eval(expr, {"__builtins__": {}}, {})
    except (SyntaxError, ZeroDivisionError, TypeError):
        return "Esa operación no es válida."
    if isinstance(resultado, float) and resultado.is_integer():
        resultado = int(resultado)
    return f"{expr} = {resultado}"


@skill("gracias", r"\b(gracias|te lo agradezco|muy amable)\b", ayuda="Agradecer")
def _gracias(ctx: Contexto) -> str:
    return random.choice(
        ["Con gusto.", "Siempre es un placer ayudarte.", "Para eso estoy."]
    )


@skill("despedida", r"\b(adios|hasta luego|nos vemos|chao|bye)\b", ayuda="Despedirse")
def _despedida(ctx: Contexto) -> str:
    return "Hasta luego. Aquí estaré cuando me necesites."


@skill("ayuda", r"\b(ayuda|que puedes hacer|comandos|opciones)\b",
       ayuda="Ver lo que puedo hacer", prioridad=3)
def _ayuda(ctx: Contexto) -> str:
    items = sorted({s.ayuda for s in _SKILLS if s.nombre != "ayuda"})
    return "Puedo ayudarte con:\n• " + "\n• ".join(items)


# --------------------------------------------------------------------------
class Brain:
    def __init__(self):
        self.memory = MemoryDummy()

    def answer(self, text: str) -> str:
        if not text or not text.strip():
            return "Dime algo y te ayudo."
        limpio = text.strip().lower()

        mejor: tuple[int, Skill, re.Match] | None = None
        for sk in _SKILLS:
            for patron in sk.patrones:
                m = patron.search(limpio)
                if m and (mejor is None or sk.prioridad > mejor[0]):
                    mejor = (sk.prioridad, sk, m)
                    break

        if mejor is None:
            return "Todavía estoy aprendiendo eso. Escribe «ayuda» para ver lo que puedo hacer."

        _, sk, m = mejor
        ctx = Contexto(texto=text, limpio=limpio, match=m, memory=self.memory)
        try:
            return sk.handler(ctx)
        except Exception as exc:
            return f"Ocurrió un inconveniente al procesar: {exc}"