"""Datas e horários usados no app (horário local do computador)."""

from __future__ import annotations

from datetime import date, datetime

FORMATOS_DATA = {
    "dd/mm/aaaa": "%d/%m/%Y",
    "aaaa-mm-dd": "%Y-%m-%d",
    "mm/dd/aaaa": "%m/%d/%Y",
}
FORMATOS_HORA = {"24h": "%H:%M", "12h": "%I:%M %p"}


def agora() -> datetime:
    return datetime.now().replace(microsecond=0)


def hoje() -> date:
    return date.today()


def agora_iso() -> str:
    return agora().isoformat(sep=" ")


def para_date(valor: str | date | None) -> date | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor)[:10])


def formatar_data(valor: str | date | None, formato: str = "dd/mm/aaaa") -> str:
    d = para_date(valor)
    if d is None:
        return "—"
    return d.strftime(FORMATOS_DATA.get(formato, "%d/%m/%Y"))


def formatar_hora(valor: str | None, formato: str = "24h") -> str:
    if not valor:
        return "—"
    t = datetime.strptime(valor[:5], "%H:%M")
    return t.strftime(FORMATOS_HORA.get(formato, "%H:%M"))


def minutos(hora: str) -> int:
    h, m = hora[:5].split(":")
    return int(h) * 60 + int(m)


def hora_de_minutos(total: int) -> str:
    total = max(0, min(total, 24 * 60 - 1))
    return f"{total // 60:02d}:{total % 60:02d}"


DIAS_SEMANA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def data_por_extenso(d: date) -> str:
    return f"{DIAS_SEMANA[d.weekday()]}, {d.day} de {MESES[d.month - 1]} de {d.year}"
