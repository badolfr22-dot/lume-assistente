"""Verificações de acessibilidade que dá para automatizar."""

import pytest
from streamlit.testing.v1 import AppTest

from assistente import demo
from assistente.ui.estilos import PALETAS

from tests.test_interface import PAGINAS, _script_pagina


def _luminancia(hex_cor: str) -> float:
    canais = [int(hex_cor[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canais]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contraste(a: str, b: str) -> float:
    l1, l2 = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


# Pares (texto, fundo) realmente usados na interface.
PARES = [
    ("texto", "fundo"), ("texto", "superficie"), ("texto", "superficie2"),
    ("suave", "fundo"), ("suave", "superficie"), ("suave", "superficie2"),
    ("texto_primaria", "primaria"), ("primaria", "superficie"),
    ("perigo", "superficie"), ("sucesso", "superficie"), ("aviso", "superficie"),
    ("info", "superficie"), ("destaque", "superficie"),
]


@pytest.mark.parametrize("tema", list(PALETAS))
@pytest.mark.parametrize("texto, fundo", PARES)
def test_contraste_minimo_wcag_aa(tema, texto, fundo):
    paleta = PALETAS[tema]
    razao = contraste(paleta[texto], paleta[fundo])
    assert razao >= 4.5, f"{tema}: {texto} sobre {fundo} = {razao:.2f}:1"


@pytest.mark.parametrize("pagina", PAGINAS)
def test_campos_e_botoes_tem_rotulo(pagina):
    demo.carregar()
    at = AppTest.from_function(_script_pagina, args=(pagina,), default_timeout=60)
    at.run()
    assert not at.exception
    for tipo in ("text_input", "text_area", "selectbox", "multiselect", "number_input", "date_input",
                 "time_input", "slider", "checkbox", "toggle", "radio"):
        for widget in at.get(tipo):
            assert widget.label and widget.label.strip(), f"{pagina}: {tipo} sem rótulo"
    for botao in list(at.button) + list(at.get("form_submit_button")):
        assert botao.label.strip(), f"{pagina}: botão sem texto"
