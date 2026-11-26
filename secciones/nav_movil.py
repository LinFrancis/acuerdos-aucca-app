"""Selector pensado para el celular.

En pantallas angostas las filas de pestañas o botones horizontales quedan apretadas o se cortan.
Este selector muestra un solo botón grande con la opción actual; al tocarlo se abre una cuadrícula de
botones grandes para elegir y se cierra sola al elegir.

Se dibuja siempre, pero el CSS de `acuerdos.py` lo oculta en escritorio y oculta el selector
original (pills / radio) en celular, así que cada pantalla muestra solo el que le corresponde.
"""
from __future__ import annotations

from typing import Callable, Optional, Sequence

import streamlit as st


def selector_movil(opciones: Sequence, estado_key: str, clave: str, prefijo: str = "",
                   columnas: int = 2, al_elegir: Optional[Callable] = None,
                   iconos: Optional[dict] = None) -> None:
    """opciones: lista de textos, o de pares (valor, texto) si el valor guardado no es el texto.
    estado_key: clave de session_state donde se guarda la opción elegida (la del radio/pills original).
    clave: nombre único de este selector (también da el nombre a las clases CSS `st-key-mm_<clave>…`)."""
    pares = [(o, o) if isinstance(o, str) else (o[0], o[1]) for o in opciones]
    valores = [v for v, _ in pares]
    iconos = iconos or {}
    abierto = f"mm_{clave}_abierto"

    def _alternar() -> None:
        st.session_state[abierto] = not st.session_state.get(abierto, False)

    def _elegir(valor) -> None:
        if al_elegir:
            al_elegir(valor)
        else:
            st.session_state[estado_key] = valor
        st.session_state[abierto] = False

    actual = st.session_state.get(estado_key)
    if actual not in valores:
        actual = valores[0]
    texto_actual = dict(pares)[actual]
    abierta = bool(st.session_state.get(abierto, False))

    with st.container(key=f"mm_{clave}"):
        cabecera = f"{prefijo} {iconos.get(actual, '')} {texto_actual}".replace("  ", " ").strip()
        st.button(f"{cabecera}   {'▴' if abierta else '▾'}", key=f"mm_{clave}_btn", on_click=_alternar,
                  use_container_width=True, type="secondary")
        if abierta:
            cols = st.columns(columnas)
            for i, (valor, texto) in enumerate(pares):
                marca = "✓ " if valor == actual else ""
                cols[i % columnas].button(f"{marca}{iconos.get(valor, '')} {texto}".replace("  ", " ").strip(),
                                          key=f"mm_{clave}_t{i}", on_click=_elegir, args=(valor,),
                                          type="primary" if valor == actual else "secondary",
                                          use_container_width=True)
