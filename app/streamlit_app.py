from datetime import datetime
from html import escape
from pathlib import Path

import streamlit as st

from app import dane, widoki
from app.database import initialize_database, polaczenie, sciezka_bazy
from app.doradca import odpowiedz_doradcy
from app.konta import pobierz_konto
from app.mapa import pokaz_mape
from app.rekomendacje import filtruj, pobierz_oferty, policz_dopasowanie, top_kierunki
from app.ustawienia import OBSZARY, STRONY
from app.synchronizacja import stan_synchronizacji

st.set_page_config(page_title="Kierunek. — Znajdź swoje studia",page_icon="🎓",layout="wide",initial_sidebar_state="auto")
st.markdown("<style>"+Path(__file__).with_name("styl.css").read_text(encoding="utf-8")+"</style>",unsafe_allow_html=True)
initialize_database()


@st.cache_data(ttl=120,show_spinner=False)
def katalog_publiczny(sciezka,wersja):
    return pobierz_oferty()


def wyloguj():
    st.session_state.clear()


def okno_doradcy(konto,ranking,oferty,strona):
    with st.container(key="doradca"):
        st.markdown('<div class="advisor-head"><div class="advisor-icon">✦</div><div><strong>Twój doradca</strong><small>Pomoc w wyborze i nawigacji</small></div></div>',unsafe_allow_html=True)
        st.caption("Uwzględniam Twoje wyniki i ankietę. Możesz doprecyzować, czego szukasz.")
        historia = dane.pobierz_wiadomosci(konto["id"],20)
        with st.container(height=430,border=False):
            if not historia:
                with st.chat_message("assistant",avatar="🎓"):
                    st.write("Cześć! Pomogę Ci znaleźć kierunek i poruszać się po aplikacji. Opowiedz, co lubisz, lub zapytaj o swój ranking.")
                if st.button("Gdzie wpisać wyniki matury?",key="pytanie_matura",width="stretch"):
                    st.session_state["pytanie_doradcy"]="Gdzie mogę wpisać swoje wyniki matury?"
                if st.button("Wyjaśnij mój ranking",key="pytanie_ranking",width="stretch"):
                    st.session_state["pytanie_doradcy"]="Wyjaśnij mój ranking i podpowiedz, co uzupełnić, aby dopasowanie było lepsze."
            for wiadomosc in historia:
                with st.chat_message("user" if wiadomosc["rola"]=="uzytkownik" else "assistant",avatar="👤" if wiadomosc["rola"]=="uzytkownik" else "🎓"):
                    st.markdown(wiadomosc["tresc"])
        pytanie = st.chat_input("Zapytaj o kierunek lub swoje wyniki…",max_chars=2000,key="wiadomosc_doradcy")
        pytanie = pytanie or st.session_state.pop("pytanie_doradcy",None)
        if pytanie:
            with st.chat_message("user",avatar="👤"): st.write(pytanie)
            try:
                with st.spinner("Doradca przygotowuje odpowiedź…",show_time=True):
                    wynik = odpowiedz_doradcy(konto["id"],pytanie,ranking,oferty,strona)
                if wynik.get("strona") in STRONY:
                    st.session_state["przejdz_do"] = wynik["strona"]
                st.rerun()
            except ValueError as blad:
                st.warning(str(blad))
        preferencje = dane.pobierz_preferencje_czatu(konto["id"])
        if preferencje:
            obszary = [OBSZARY[x] for x in preferencje.get("preferowane_obszary",[]) if x in OBSZARY]
            st.caption("Preferencje z rozmowy: "+(", ".join(obszary) if obszary else "uwzględnione w rankingu"))
            if st.button("Cofnij preferencje z rozmowy",width="stretch"):
                dane.wyczysc_preferencje_czatu(konto["id"])
                st.rerun()
        if historia:
            with st.expander("Opcje rozmowy"):
                if st.button("Wyczyść historię tej rozmowy"):
                    dane.wyczysc_rozmowe(konto["id"])
                    st.rerun()
        st.markdown('<div class="small-note">Doradca może się mylić. Zasady rekrutacji sprawdzaj w oficjalnym źródle uczelni.</div>',unsafe_allow_html=True)


konto = pobierz_konto(st.session_state.get("id_uzytkownika"))
if not konto:
    widoki.ekran_logowania()
    st.stop()

if "przejdz_do" in st.session_state:
    docelowa = st.session_state.pop("przejdz_do")
    if docelowa in STRONY:
        st.session_state["nawigacja"] = docelowa

profil = dane.pobierz_profil(konto["id"])
wyniki = dane.pobierz_wyniki(konto["id"])
kwalifikacje = dane.pobierz_kwalifikacje(konto["id"])
ankieta = dane.pobierz_ankiete(konto["id"])
preferencje = dane.pobierz_preferencje_czatu(konto["id"])
ulubione = dane.pobierz_ulubione(konto["id"])
teraz = datetime.now()
with st.sidebar:
    widoki.brand()
    st.caption("TWOJA PRZESTRZEŃ")
    strony = list(STRONY)
    if st.session_state.get("nawigacja") not in strony:
        st.session_state["nawigacja"] = "Przegląd"
    ikony = {"Przegląd":"◈","Katalog kierunków":"▦","Mapa uczelni":"⌖","Mój profil":"◉","Ankieta":"☷","Ulubione":"♡"}
    strona = st.radio("Nawigacja",strony,format_func=lambda x:f"{ikony[x]}  {x}",key="nawigacja",label_visibility="collapsed")
    st.divider()
    rok = st.selectbox("Rok rekrutacji",[teraz.year,teraz.year+1],index=1 if teraz.month>=10 else 0,key="rok_rekrutacji")
    st.caption("Weryfikacja zapisanych wymagań dotyczy wybranego roku.")
    gotowe = sum([bool(profil.get("imie")),bool(wyniki),bool(ankieta),profil.get("szerokosc") is not None])
    st.progress(gotowe/4,text=f"Twój profil: {gotowe*25}%")
    st.markdown(f'<div class="account-box"><strong>{escape(profil.get("imie") or "Twoje konto")}</strong><br>{escape(konto["email"])}</div>',unsafe_allow_html=True)
    stan = stan_synchronizacji()
    ostatnia = stan.get("ostatni_import")
    st.caption("Dane aktualizują się automatycznie po 24 godzinach.")
    st.caption("Ostatni import: "+(ostatnia.strftime("%d.%m.%Y %H:%M UTC") if ostatnia else "trwa przygotowywanie pełnego katalogu"))
    if stan.get("stan")=="pobieranie":
        st.caption("Pobieranie nowych danych w tle…")
    elif stan.get("stan")=="blad":
        st.caption("Ponowimy aktualizację automatycznie. Dostępny jest poprzedni katalog.")
    st.button("Wyloguj się",on_click=wyloguj,width="stretch")

with polaczenie() as baza:
    wersja = baza.execute("SELECT COALESCE(MAX(id),0) FROM historia_importow").fetchone()[0]
oferty = katalog_publiczny(str(sciezka_bazy()),wersja)
ocenione = policz_dopasowanie(oferty,profil,wyniki,ankieta,kwalifikacje,preferencje,dane.pobierz_wymagania(rok))
przefiltrowane = filtruj(ocenione,st.session_state.get("filtry_katalogu",{}))
ranking = top_kierunki(przefiltrowane)

glowna,czat = st.columns([2.35,1],gap="large")
with glowna:
    if "komunikat" in st.session_state:
        st.success(st.session_state.pop("komunikat"))
    if strona=="Przegląd": widoki.przeglad(konto,profil,ankieta,wyniki,ocenione,ranking,ulubione)
    elif strona=="Katalog kierunków": widoki.katalog(konto,profil,ocenione,ulubione)
    elif strona=="Mapa uczelni":
        st.subheader("Uczelnie bliżej Ciebie")
        with st.expander("Filtruj uczelnie na mapie"):
            filtry = widoki.filtry_katalogu(ocenione,profil)
        pokaz_mape(konto,profil,filtruj(ocenione,filtry))
    elif strona=="Mój profil": widoki.profil(konto,profil,wyniki,kwalifikacje)
    elif strona=="Ankieta": widoki.ankieta(konto,ankieta)
    elif strona=="Ulubione":
        st.subheader("Zostaw sobie dobre opcje")
        st.caption("Wszystkie zapisane warianty, niezależnie od aktualnych filtrów katalogu.")
        zapisane = [x for x in ocenione if x["id"] in ulubione]
        if not zapisane: st.info("Tu pojawią się kierunki zapisane serduszkiem w katalogu lub rankingu.")
        for oferta in sorted(zapisane,key=lambda x:-x["dopasowanie"]): widoki.karta_kierunku(oferta,konto,ulubione,prefix="zapisane")
        niedostepne = len(ulubione)-len(zapisane)
        if niedostepne: st.caption(f"{niedostepne} zapisanych wariantów jest poza aktualnym katalogiem lub preferencjami rozmowy. Wpisy pozostają zapisane na koncie.")
with czat:
    ranking = top_kierunki(filtruj(ocenione,st.session_state.get("filtry_katalogu",{})))
    okno_doradcy(konto,ranking,ocenione,strona)
