"""Lokalne wspolrzedne GeoNames oraz odleglosc w linii prostej."""

import json
import math
import unicodedata
from functools import lru_cache
from pathlib import Path


def normalizuj(tekst) -> str:
    tekst = str(tekst or "").casefold().replace("ł", "l")
    return "".join(x for x in unicodedata.normalize("NFKD", tekst) if not unicodedata.combining(x)).strip()


@lru_cache(maxsize=1)
def miejscowosci() -> list[dict]:
    return json.loads((Path(__file__).with_name("dane") / "miejscowosci.json").read_text(encoding="utf-8"))["miejscowosci"]


@lru_cache(maxsize=1)
def indeks_miejscowosci():
    indeks = {}
    for miasto in miejscowosci():
        for nazwa in [miasto["nazwa"], miasto["nazwa_ascii"], *miasto["aliasy"]]:
            indeks.setdefault(normalizuj(nazwa), []).append(miasto)
    return indeks


@lru_cache(maxsize=5000)
def znajdz_miasto(nazwa: str, wojewodztwo: str = "") -> dict | None:
    wyniki = indeks_miejscowosci().get(normalizuj(nazwa), [])
    if wojewodztwo:
        zgodne = [x for x in wyniki if normalizuj(x["wojewodztwo"]) == normalizuj(wojewodztwo)]
        if zgodne:
            return zgodne[0]
    return wyniki[0] if wyniki else None


def dystans_km(szerokosc, dlugosc, szerokosc_uczelni, dlugosc_uczelni) -> float | None:
    if any(x is None for x in [szerokosc, dlugosc, szerokosc_uczelni, dlugosc_uczelni]):
        return None
    a, b, c, d = map(math.radians, [szerokosc, dlugosc, szerokosc_uczelni, dlugosc_uczelni])
    hav = math.sin((c-a)/2)**2 + math.cos(a)*math.cos(c)*math.sin((d-b)/2)**2
    return round(6371.0088 * 2 * math.asin(math.sqrt(min(1, hav))), 1)
