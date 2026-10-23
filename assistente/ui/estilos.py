"""Identidade visual: paletas clara/escura e CSS responsivo.

As cores foram escolhidas para ter contraste mínimo de 4,5:1 (WCAG AA) entre
texto e fundo; o teste `tests/test_acessibilidade.py` confere isso.
"""

from __future__ import annotations

PALETAS: dict[str, dict[str, str]] = {
    "claro": {
        "fundo": "#F7F6F2",
        "superficie": "#FFFFFF",
        "superficie2": "#EDEBE4",
        "texto": "#1F2933",
        "suave": "#52606D",
        "borda": "#DAD7CD",
        "primaria": "#0F766E",
        "texto_primaria": "#FFFFFF",
        "destaque": "#B45309",
        "perigo": "#B42318",
        "sucesso": "#15803D",
        "aviso": "#9A5B00",
        "info": "#1D4ED8",
        "trilho": "#E4E1D8",
    },
    "escuro": {
        "fundo": "#11161B",
        "superficie": "#1A2129",
        "superficie2": "#232C35",
        "texto": "#E8EBEE",
        "suave": "#A7B1BC",
        "borda": "#33404C",
        "primaria": "#2DD4BF",
        "texto_primaria": "#062E2A",
        "destaque": "#FBBF24",
        "perigo": "#F87171",
        "sucesso": "#4ADE80",
        "aviso": "#FBBF24",
        "info": "#93C5FD",
        "trilho": "#2B3640",
    },
}

_CSS_BASE = """
:root {
  --lume-fundo: %(fundo)s; --lume-sup: %(superficie)s; --lume-sup2: %(superficie2)s;
  --lume-texto: %(texto)s; --lume-suave: %(suave)s; --lume-borda: %(borda)s;
  --lume-pri: %(primaria)s; --lume-pri-texto: %(texto_primaria)s; --lume-dest: %(destaque)s;
  --lume-perigo: %(perigo)s; --lume-sucesso: %(sucesso)s; --lume-aviso: %(aviso)s; --lume-info: %(info)s;
  --lume-trilho: %(trilho)s;
}
.block-container { padding-top: 3.5rem; padding-bottom: 4rem; max-width: 1180px; }
h1, h2, h3 { letter-spacing: -0.01em; }

/* Cabeçalho das páginas */
.lume-hero { display: flex; gap: 1rem; align-items: center; margin: 0 0 1.2rem 0; }
.lume-hero .icone { width: 3rem; height: 3rem; border-radius: 0.9rem; display: grid; place-items: center;
  font-size: 1.5rem; background: var(--lume-pri); color: var(--lume-pri-texto); flex: 0 0 auto; }
.lume-hero h1 { font-size: 1.75rem; margin: 0; padding: 0; line-height: 1.2; color: var(--lume-texto); }
.lume-hero p { margin: 0.15rem 0 0 0; color: var(--lume-suave); font-size: 0.98rem; }

/* Cartões de indicadores */
.lume-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.8rem; margin-bottom: 1rem; }
.lume-metric { background: var(--lume-sup); border: 1px solid var(--lume-borda); border-radius: 0.9rem;
  padding: 0.9rem 1rem; position: relative; overflow: hidden; }
.lume-metric::before { content: ""; position: absolute; inset: 0 auto 0 0; width: 4px; background: var(--cor, var(--lume-pri)); }
.lume-metric .rotulo { color: var(--lume-suave); font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.lume-metric .valor { color: var(--lume-texto); font-size: 1.9rem; font-weight: 700; line-height: 1.15; margin-top: 0.2rem; }
.lume-metric .detalhe { color: var(--lume-suave); font-size: 0.85rem; margin-top: 0.15rem; }

/* Barras de progresso */
.lume-barra { margin: 0.35rem 0 0.9rem 0; }
.lume-barra .topo { display: flex; justify-content: space-between; font-size: 0.92rem; color: var(--lume-texto); margin-bottom: 0.3rem; }
.lume-barra .topo span:last-child { font-weight: 700; }
.lume-barra .trilho { height: 0.6rem; background: var(--lume-trilho); border-radius: 999px; overflow: hidden; }
.lume-barra .cheio { height: 100%%; background: var(--cor, var(--lume-pri)); border-radius: 999px; }

/* Etiquetas */
.lume-chip { display: inline-block; padding: 0.1rem 0.55rem; border-radius: 999px; font-size: 0.8rem; font-weight: 600;
  border: 1px solid currentColor; margin-right: 0.3rem; line-height: 1.5; }
.lume-chip.alta, .lume-chip.atrasada { color: var(--lume-perigo); }
.lume-chip.media { color: var(--lume-aviso); }
.lume-chip.baixa, .lume-chip.neutra { color: var(--lume-suave); }
.lume-chip.concluida { color: var(--lume-sucesso); }
.lume-chip.exemplo { color: var(--lume-info); }

/* Itens de lista */
.lume-item-titulo { font-weight: 650; font-size: 1.02rem; color: var(--lume-texto); margin: 0; }
.lume-item-titulo.feito { text-decoration: line-through; color: var(--lume-suave); }
.lume-item-meta { color: var(--lume-suave); font-size: 0.88rem; margin: 0.15rem 0 0 0; }

/* Sugestões inteligentes */
.lume-sug { background: var(--lume-sup); border: 1px solid var(--lume-borda); border-left: 4px solid var(--lume-dest);
  border-radius: 0.8rem; padding: 0.7rem 0.9rem; margin-bottom: 0.6rem; }
.lume-sug .t { color: var(--lume-texto); font-weight: 600; }
.lume-sug .m { color: var(--lume-suave); font-size: 0.86rem; margin-top: 0.2rem; }

/* Estado vazio */
.lume-vazio { border: 1px dashed var(--lume-borda); border-radius: 0.9rem; padding: 1rem 1.1rem; color: var(--lume-suave);
  background: var(--lume-sup); }
.lume-vazio strong { color: var(--lume-texto); }

/* Linha do tempo do planejador */
.lume-hora { font-variant-numeric: tabular-nums; font-weight: 700; color: var(--lume-pri); font-size: 0.95rem; }

/* Acessibilidade: foco visível no teclado */
button:focus-visible, a:focus-visible, input:focus-visible, textarea:focus-visible, [role="tab"]:focus-visible {
  outline: 3px solid var(--lume-dest) !important; outline-offset: 2px !important; }

/* Celular */
@media (max-width: 640px) {
  /* 4rem no topo: espaço para a barra do Streamlit (botão do menu), que fica por cima do conteúdo. */
  .block-container { padding: 4rem 0.9rem 4rem 0.9rem; }
  .lume-hero h1 { font-size: 1.4rem; }
  .lume-hero .icone { width: 2.5rem; height: 2.5rem; font-size: 1.25rem; }
  .lume-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.6rem; }
  .lume-metric .valor { font-size: 1.55rem; }
  .stButton button, .stDownloadButton button, .stFormSubmitButton button { min-height: 2.75rem; width: 100%%; }
  /* Só campos de digitação (não afeta caixas de seleção e interruptores, cujo input fica escondido). */
  input[type="text"], input[type="number"], input[type="password"], textarea, [data-baseweb="select"] > div {
    min-height: 2.75rem; font-size: 16px !important; }
}
"""

# Ajustes para o tema escuro. O tema base do Streamlit é claro (config.toml);
# aqui sobrescrevemos as superfícies principais quando o usuário escolhe "escuro".
_CSS_ESCURO = """
[data-testid="stApp"], [data-testid="stHeader"], [data-testid="stBottomBlockContainer"], [data-testid="stBottom"] > div {
  background: var(--lume-fundo) !important; color: var(--lume-texto) !important; }
[data-testid="stSidebar"], [data-testid="stSidebar"] > div { background: var(--lume-sup) !important; }
[data-testid="stApp"] p, [data-testid="stApp"] li, [data-testid="stApp"] label, [data-testid="stApp"] h1,
[data-testid="stApp"] h2, [data-testid="stApp"] h3, [data-testid="stApp"] h4, [data-testid="stApp"] span,
[data-testid="stApp"] summary, [data-testid="stWidgetLabel"], [data-testid="stCaptionContainer"],
[data-testid="stMarkdownContainer"] { color: var(--lume-texto); }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--lume-suave) !important; }
[data-baseweb="input"], [data-baseweb="input"] > div, [data-baseweb="base-input"], [data-baseweb="textarea"],
[data-baseweb="select"] > div, [data-baseweb="popover"] ul, [data-baseweb="menu"], [data-testid="stNumberInputContainer"],
input, textarea { background: var(--lume-sup2) !important; color: var(--lume-texto) !important;
  border-color: var(--lume-borda) !important; }
[data-testid="stSelectbox"] div[role="group"], [data-testid="stMultiSelect"] div[role="group"],
[data-testid="stTimeInput"] div[role="group"], [data-testid="stDateInputField"] {
  background: var(--lume-sup2) !important; color: var(--lume-texto) !important; border-color: var(--lume-borda) !important; }
[data-testid="stButtonGroup"] button { background: var(--lume-sup2) !important; color: var(--lume-texto) !important;
  border-color: var(--lume-borda) !important; }
[data-testid="stButtonGroup"] button p { color: var(--lume-texto) !important; }
[data-testid="stButtonGroup"] button[aria-checked="true"] { background: var(--lume-pri) !important; border-color: var(--lume-pri) !important; }
[data-testid="stButtonGroup"] button[aria-checked="true"] p { color: var(--lume-pri-texto) !important; }
input::placeholder, textarea::placeholder { color: var(--lume-suave) !important; opacity: 1; }
[data-baseweb="popover"] li { color: var(--lume-texto) !important; }
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] li[aria-selected="true"] { background: var(--lume-borda) !important; }
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stExpander"] details, [data-testid="stForm"],
[data-testid="stPopoverBody"], div[role="dialog"] { background: var(--lume-sup) !important; border-color: var(--lume-borda) !important; }
[data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryFormSubmit"], [data-testid="stPopoverButton"],
[data-testid="stBaseButton-pills"], [data-testid="stBaseButton-segmented_control"], [data-testid="stDownloadButton"] button {
  background: var(--lume-sup2) !important; color: var(--lume-texto) !important; border-color: var(--lume-borda) !important; }
[data-testid="stBaseButton-pillsActive"], [data-testid="stBaseButton-segmented_controlActive"] {
  background: var(--lume-pri) !important; color: var(--lume-pri-texto) !important; }
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  background: var(--lume-pri) !important; color: var(--lume-pri-texto) !important; border-color: var(--lume-pri) !important; }
[data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-primaryFormSubmit"] p,
[data-testid="stBaseButton-pillsActive"] p, [data-testid="stBaseButton-segmented_controlActive"] p { color: var(--lume-pri-texto) !important; }
[data-testid="stBaseButton-tertiary"] p { color: var(--lume-pri) !important; }
[data-testid="stTabs"] button p { color: var(--lume-suave); }
[data-testid="stTabs"] button[aria-selected="true"] p { color: var(--lume-texto); }
[data-testid="stSidebarNav"] a span, [data-testid="stNavSectionHeader"] { color: var(--lume-texto) !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: var(--lume-sup2) !important; }
[data-testid="stChatMessage"] { background: var(--lume-sup) !important; }
[data-testid="stChatInput"] textarea, [data-testid="stChatInput"] > div { background: var(--lume-sup2) !important; }
[data-testid="stTable"] td, [data-testid="stTable"] th { color: var(--lume-texto) !important; border-color: var(--lume-borda) !important; }
[data-testid="stSlider"] [data-testid="stSliderThumbValue"], [data-testid="stTickBarMin"], [data-testid="stTickBarMax"] { color: var(--lume-texto) !important; }
[data-testid="stAlertContainer"] p { color: inherit; }
hr { border-color: var(--lume-borda) !important; }
"""


def css(tema: str) -> str:
    paleta = PALETAS.get(tema, PALETAS["claro"])
    texto = _CSS_BASE % paleta
    if tema == "escuro":
        texto += _CSS_ESCURO
    return f"<style>{texto}</style>"


def cor(tema: str, nome: str) -> str:
    return PALETAS.get(tema, PALETAS["claro"])[nome]
