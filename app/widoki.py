"""Widoki aplikacji Streamlit."""

from datetime import datetime
from html import escape
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

from app import dane
from app.database import polaczenie
from app.konta import utworz_konto, zaloguj
from app.rekomendacje import filtruj, top_kierunki
from app.ustawienia import OBSZARY, POZIOMY, PRZEDMIOTY, PYTANIA, TRYBY


def brand():
    st.markdown('<div class="brand"><span class="brand-mark">↗</span> kierunek<span style="color:#0d9383">.</span></div>',unsafe_allow_html=True)


def ekran_logowania():
    lewa,prawa = st.columns([1.1,1],gap="large",vertical_alignment="center")
    with lewa:
        st.markdown('''<div class="login-hero"><div class="brand"><span class="brand-mark">↗</span> kierunek.</div>
        <div class="eyebrow" style="color:#83d9bd">Twój następny krok</div><h1>Studia, które<br>pasują do Ciebie.</h1>
        <p>Połącz swoje zainteresowania, wyniki i plany. Odkryj kierunki, w których możesz rozwinąć skrzydła.</p>
        <div class="feature-row"><span class="feature-icon">01</span> Osobisty ranking kierunków</div>
        <div class="feature-row"><span class="feature-icon">02</span> Uczelnie na mapie Twoich możliwości</div>
        <div class="feature-row"><span class="feature-icon">03</span> Rozmowa z Twoim doradcą</div><div class="orb"></div></div>''',unsafe_allow_html=True)
    with prawa:
        with st.container(key="login-card"):
            st.markdown('<div class="eyebrow">Dobrze Cię widzieć</div>',unsafe_allow_html=True)
            st.subheader("Zaplanuj swój kierunek")
            st.caption("Zaloguj się, aby wrócić do swoich wyników i rekomendacji.")
            logowanie,rejestracja = st.tabs(["Zaloguj się","Utwórz konto"])
            with logowanie:
                with st.form("logowanie"):
                    email = st.text_input("E-mail lub login",placeholder="twoj@email.pl",key="email_logowania")
                    haslo = st.text_input("Hasło",type="password",placeholder="Wpisz hasło",key="haslo_logowania")
                    wyslane = st.form_submit_button("Zaloguj się  →",type="primary",width="stretch")
                if wyslane:
                    try:
                        if not email.strip() or not haslo:
                            raise ValueError("Uzupełnij e-mail i hasło.")
                        identyfikator = zaloguj(email,haslo)
                        if not identyfikator:
                            raise ValueError("Nieprawidłowy e-mail lub hasło.")
                        st.session_state.clear()
                        st.session_state["id_uzytkownika"] = identyfikator
                        st.rerun()
                    except ValueError as blad:
                        st.error(str(blad))
            with rejestracja:
                with st.form("rejestracja"):
                    email = st.text_input("Adres e-mail",placeholder="twoj@email.pl",key="email_rejestracji")
                    haslo = st.text_input("Nowe hasło",type="password",help="Od 12 do 256 znaków.",key="nowe_haslo")
                    powtorzenie = st.text_input("Powtórz hasło",type="password")
                    wyslane = st.form_submit_button("Utwórz moje konto",type="primary",width="stretch")
                if wyslane:
                    try:
                        if haslo != powtorzenie:
                            raise ValueError("Hasła muszą być takie same.")
                        identyfikator = utworz_konto(email,haslo)
                        st.session_state.clear()
                        st.session_state["id_uzytkownika"] = identyfikator
                        st.rerun()
                    except ValueError as blad:
                        st.error(str(blad))
            st.markdown('<div class="small-note">Twój profil, ankieta i rozmowy są zapisywane na Twoim koncie w tej instalacji.</div>',unsafe_allow_html=True)


def metryka(etykieta,wartosc,opis=""):
    st.markdown(f'<div class="metric-card"><small>{escape(str(etykieta))}</small><strong>{escape(str(wartosc))}</strong><span>{escape(str(opis))}</span></div>',unsafe_allow_html=True)


def bezpieczny_url(adres):
    adres = str(adres or "").strip()
    if adres.startswith("www."):
        adres = "https://"+adres
    return adres if urlparse(adres).scheme in ["http","https"] and urlparse(adres).netloc else None


def karta_kierunku(oferta,konto,ulubione,numer=None,prefix="oferta"):
    with st.container(border=True):
        a,b = st.columns([4,1],vertical_alignment="top")
        with a:
            if numer:
                st.markdown(f'<div class="rank-label">#{numer:02d} w Twoim rankingu</div>',unsafe_allow_html=True)
            st.markdown(f'<div class="course-title">{escape(oferta["nazwa"])}</div><div class="course-school">{escape(oferta["uczelnia"])}</div>',unsafe_allow_html=True)
            znaczniki = [oferta.get("miasto") or "Brak miejscowości",oferta.get("tryb_studiow") or "",oferta.get("jezyk") or "",OBSZARY[oferta["obszar"]]]
            if oferta.get("dystans_km") is not None:
                znaczniki.append(f"~{round(oferta['dystans_km'])} km")
            st.markdown("".join(f'<span class="pill">{escape(x)}</span>' for x in znaczniki if x),unsafe_allow_html=True)
        with b:
            st.markdown(f'<div class="score">{oferta["dopasowanie"]:.0f}%</div><div class="score-label">dopasowania</div>',unsafe_allow_html=True)
        if oferta["powody"]:
            st.caption(oferta["powody"][0])
        with st.expander("Dlaczego ten kierunek? Sprawdź szczegóły"):
            for powod in oferta["powody"]:
                st.write("• "+powod)
            for uwaga in oferta["ostrzezenia"]:
                st.warning(uwaga)
            st.caption(oferta["opis_wymagan"])
            st.caption(f"{oferta['poziom']} · Profil {oferta.get('profil') or 'niepodany'} · {oferta.get('liczba_semestrow') or '?'} semestrów")
            if oferta.get("opis"):
                st.write(oferta["opis"])
            rozbicie = pd.DataFrame([{"Kryterium":{"zainteresowania":"Zainteresowania","wyniki":"Przygotowanie przedmiotowe","predyspozycje":"Mocne strony","preferencje":"Preferencje"}[k],"Ocena":v,"Waga":f"{oferta['wagi'][k]*100:.0f}%"} for k,v in oferta["rozbicie"].items()])
            st.dataframe(rozbicie,hide_index=True,width="stretch")
            url = bezpieczny_url(oferta.get("adres_rekrutacji") or oferta.get("adres_strony") or oferta.get("adres_zrodla"))
            if url:
                st.link_button("Sprawdź u źródła ↗",url)
            st.caption("Dopasowanie jest oceną zgodności z profilem. Nie jest prawdopodobieństwem przyjęcia ani potwierdzeniem trwającej rekrutacji.")
        if st.button("♥ Zapisano — usuń" if oferta["id"] in ulubione else "♡ Zapisz kierunek",key=f"{prefix}_ulubione_{oferta['id']}"):
            dane.przelacz_ulubione(konto["id"],oferta["id"])
            st.rerun()


def przeglad(konto,profil,ankieta,wyniki,oferty,ranking,ulubione):
    imie = profil.get("imie") or "odkrywco"
    st.markdown(f'<div class="hero"><div class="eyebrow">Twój osobisty plan na przyszłość</div><h2>Cześć, {escape(imie)} 👋</h2><p>Dobry kierunek zaczyna się od Ciebie. Poznaj propozycje dopasowane do Twoich zainteresowań, wyników i planów.</p></div>',unsafe_allow_html=True)
    gotowe = sum([bool(profil.get("imie")),bool(wyniki),bool(ankieta),profil.get("szerokosc") is not None])
    a,b,c = st.columns(3)
    with a: metryka("Kierunki do odkrycia",len({x['id_kierunku'] for x in oferty}),"Oficjalny katalog RAD-on")
    with b: metryka("Twój profil",f"{gotowe*25}%","Wyniki, ankieta i lokalizacja")
    with c: metryka("Twoje ulubione",len(ulubione),"Wróć do zapisanych propozycji")
    if not ankieta or not wyniki:
        st.info("To wstępny ranking. Dodaj wyniki matury i wypełnij ankietę, aby uzyskać osobiste dopasowanie.")
        a,b = st.columns(2)
        with a:
            if st.button("＋ Uzupełnij profil",width="stretch"):
                st.session_state["przejdz_do"]="Mój profil"; st.rerun()
        with b:
            if st.button("✦ Wypełnij ankietę",width="stretch"):
                st.session_state["przejdz_do"]="Ankieta"; st.rerun()
    st.subheader("Twoje top 10 kierunków")
    st.caption("Procent opisuje dopasowanie do profilu, a nie szansę przyjęcia. Różne warianty tego samego kierunku nie zajmują osobnych miejsc.")
    if st.session_state.get("filtry_katalogu"):
        st.caption("Ranking uwzględnia wybrane filtry katalogu.")
        if st.button("Wyczyść filtry katalogu"):
            st.session_state["filtry_katalogu"]={}
            for klucz in list(st.session_state):
                if klucz.startswith("f_"): del st.session_state[klucz]
            st.rerun()
    if not ranking:
        st.info("Brak propozycji dla aktualnych filtrów. Poszerz zakres wyszukiwania.")
    for i,oferta in enumerate(ranking,1):
        karta_kierunku(oferta,konto,ulubione,i,"ranking")


def filtry_katalogu(oferty,profil):
    zapisane = st.session_state.get("filtry_katalogu",{})
    def lista(etykieta,klucz,opcje,format_func=str):
        opcje = sorted(set(x for x in opcje if x))
        if f"f_{klucz}" in st.session_state:
            st.session_state[f"f_{klucz}"] = [x for x in st.session_state[f"f_{klucz}"] if x in opcje]
        return st.multiselect(etykieta,opcje,default=[x for x in zapisane.get(klucz,[]) if x in opcje],format_func=format_func,key=f"f_{klucz}")
    with st.container(border=True):
        st.markdown('<div class="eyebrow">Znajdź swój kierunek</div>',unsafe_allow_html=True)
        tekst = st.text_input("Nazwa kierunku",value=zapisane.get("szukaj",""),placeholder="np. informatyka, psychologia, prawo…",key="f_szukaj")
        a,b = st.columns(2)
        with a: regiony = lista("Województwo","wojewodztwa",[x.get("wojewodztwo") for x in oferty])
        with b: uczelnie = lista("Uczelnia","uczelnie",[x["uczelnia"] for x in oferty if not regiony or x.get("wojewodztwo") in regiony])
        with st.expander("Więcej filtrów: tryb, język, miasto i odległość"):
            a,b = st.columns(2)
            with a:
                miasta = lista("Miasto uczelni","miasta",[x.get("miasto") for x in oferty])
                tryby = lista("Tryb studiów","tryby",[x.get("tryb_studiow") for x in oferty])
                obszary = lista("Obszar zainteresowań","obszary",list(OBSZARY),lambda x:OBSZARY[x])
            with b:
                jezyki = lista("Język studiów","jezyki",[x.get("jezyk") for x in oferty])
                poziomy = lista("Poziom studiów","poziomy",[x.get("poziom") for x in oferty])
                opcje = ["Dowolna","publiczna","niepubliczna"]
                rodzaj = st.selectbox("Rodzaj uczelni",opcje,index=opcje.index(zapisane.get("rodzaj") or "Dowolna"),key="f_rodzaj")
            ogranicz = st.toggle("Ogranicz odległość od domu",value=zapisane.get("dystans") is not None,disabled=profil.get("szerokosc") is None,key="f_ogranicz")
            if profil.get("szerokosc") is None:
                st.caption("Najpierw zapisz miejsce zamieszkania w zakładce Mapa uczelni.")
            limit = st.slider("Maksymalna odległość w linii prostej (km)",0,1500,int(zapisane.get("dystans") if zapisane.get("dystans") is not None else profil.get("maksymalny_dystans",300)),step=10,disabled=not ogranicz,key="f_dystans")
            ukryj = st.checkbox("Ukryj kierunki z niespełnionymi, zweryfikowanymi wymaganiami",value=zapisane.get("ukryj_niespelnione",True),key="f_ukryj")
        sortowanie = st.selectbox("Sortuj według",["Dopasowanie","Odległość","Nazwa kierunku"],key="f_sortowanie")
    wynik = {"szukaj":tekst,"wojewodztwa":regiony,"uczelnie":uczelnie,"miasta":miasta,"tryby":tryby,"obszary":obszary,"jezyki":jezyki,"poziomy":poziomy,"rodzaj":None if rodzaj=="Dowolna" else rodzaj,"dystans":limit if ogranicz else None,"ukryj_niespelnione":ukryj,"sortowanie":sortowanie}
    st.session_state["filtry_katalogu"] = wynik
    return wynik


def katalog(konto,profil,oferty,ulubione):
    st.subheader("Odkryj swoje możliwości")
    filtry = filtry_katalogu(oferty,profil)
    wynik = filtruj(oferty,filtry)
    st.caption(f"{len(wynik)} wariantów studiów spełnia wybrane filtry.")
    if not wynik:
        st.info("Brak wyników. Zmień nazwę kierunku lub poszerz filtry."); return
    strony = max(1,(len(wynik)+9)//10)
    if st.session_state.get("strona_katalogu",1)>strony:
        st.session_state["strona_katalogu"] = 1
    numer = st.number_input("Strona wyników",min_value=1,max_value=strony,value=1,key="strona_katalogu")
    for oferta in wynik[(int(numer)-1)*10:int(numer)*10]:
        karta_kierunku(oferta,konto,ulubione,prefix="katalog")


def profil(konto,profil,wyniki,kwalifikacje):
    st.subheader("Zacznij od siebie")
    st.caption("Zapisane wyniki i kwalifikacje wykorzystamy w Twoim rankingu. Możesz je później zmienić.")
    with st.form("profil_kandydata"):
        a,b = st.columns(2)
        with a:
            imie = st.text_input("Jak masz na imię?",value=profil.get("imie") or "",max_chars=80)
            szkoly = ["Liceum ogólnokształcące","Technikum","Szkoła branżowa","Inna"]
            typ = st.selectbox("Twoja szkoła",szkoly,index=szkoly.index(profil["typ_szkoly"]) if profil.get("typ_szkoly") in szkoly else 0)
        with b:
            opcje = ["Bez preferencji",*TRYBY]
            tryb = st.selectbox("Preferowany tryb studiów",opcje,index=opcje.index(profil.get("tryb_studiow")) if profil.get("tryb_studiow") in opcje else 0)
            st.caption("Miejsce zamieszkania: "+(profil.get("miejsce_zamieszkania") or "jeszcze nie wskazano — wybierz je na mapie"))
        st.markdown("**Wyniki matury**")
        st.caption("Dodaj wiersz dla każdego przedmiotu i poziomu. Dla przedmiotów zdawanych ponownie możesz podać różne lata.")
        tabela = pd.DataFrame(wyniki,columns=["przedmiot","poziom","wynik_procentowy","rok_matury"])
        tabela = st.data_editor(tabela,num_rows="dynamic",hide_index=True,width="stretch",key="edytor_matury",column_config={
            "przedmiot":st.column_config.SelectboxColumn("Przedmiot",options=PRZEDMIOTY,required=True),
            "poziom":st.column_config.SelectboxColumn("Poziom",options=POZIOMY,required=True,default="podstawowy"),
            "wynik_procentowy":st.column_config.NumberColumn("Wynik (%)",min_value=0,max_value=100,required=True,format="%.1f"),
            "rok_matury":st.column_config.NumberColumn("Rok",min_value=2000,max_value=2100,step=1,required=True,default=datetime.now().year,format="%d"),
        })
        kompletne = st.checkbox("Wpisałem wszystkie zdawane przedmioty maturalne",value=bool(profil.get("matura_uzupelniona")))
        st.caption("Dopiero komplet wyników pozwala traktować brak przedmiotu jako informację do sprawdzania wymagań uczelni.")
        st.markdown("**Kwalifikacje zawodowe**")
        kwal = st.data_editor(pd.DataFrame(kwalifikacje,columns=["kod_kwalifikacji","nazwa_kwalifikacji"]),num_rows="dynamic",hide_index=True,width="stretch",key="edytor_kwalifikacji",column_config={"kod_kwalifikacji":st.column_config.TextColumn("Kod, np. INF.04",max_chars=30),"nazwa_kwalifikacji":st.column_config.TextColumn("Nazwa kwalifikacji",max_chars=250)})
        wyslane = st.form_submit_button("Zapisz profil i przelicz ranking",type="primary",width="stretch")
    if wyslane:
        try:
            dane.zapisz_profil(konto["id"],imie,typ,tryb,kompletne,tabela.where(pd.notnull(tabela),None).to_dict("records"),kwal.where(pd.notnull(kwal),None).to_dict("records"))
            st.session_state["komunikat"]="Profil został zapisany. Ranking uwzględnia aktualne wyniki."
            st.rerun()
        except ValueError as blad: st.error(str(blad))


def ankieta(konto,odpowiedzi):
    st.subheader("Poznajmy Twoją stronę")
    st.caption("Nie ma dobrych ani złych odpowiedzi. Możesz wrócić do ankiety i wypełnić ją ponownie — ranking uwzględni najnowszą wersję.")
    with polaczenie() as baza:
        wersje = baza.execute("SELECT COUNT(*),MAX(data_utworzenia) FROM wersje_ankiety WHERE id_uzytkownika=?",(konto["id"],)).fetchone()
    if wersje[0]: st.caption(f"Zapisanych wersji: {wersje[0]} · Ostatni zapis: {wersje[1][:16].replace('T',' ')} UTC")
    nowe = {}
    with st.form("ankieta"):
        st.markdown("**01 / Zainteresowania i predyspozycje**")
        for kod in ["zainteresowania","mocne_strony","slabe_strony"]:
            pytanie,opcje = PYTANIA[kod]
            opcje = list(OBSZARY) if kod=="zainteresowania" else opcje
            domyslne = [x for x in odpowiedzi.get(kod,[]) if x in opcje]
            nowe[kod] = st.multiselect(pytanie,opcje,default=domyslne,max_selections=6,format_func=(lambda x:OBSZARY[x]) if kod=="zainteresowania" else str,key=f"a_{kod}")
        st.markdown("**02 / Jak chcesz się uczyć i pracować?**")
        for kod in ["srodowisko_pracy","styl_nauki","motywacja","praca_zespolowa"]:
            pytanie,opcje = PYTANIA[kod]
            nowe[kod] = st.selectbox(pytanie,opcje,index=opcje.index(odpowiedzi[kod]) if odpowiedzi.get(kod) in opcje else len(opcje)-1,key=f"a_{kod}")
        st.markdown("**03 / Twoje plany na studia**")
        a,b = st.columns(2)
        for index,kod in enumerate(["preferowany_tryb","preferowany_jezyk","rodzaj_uczelni","przeprowadzka"]):
            with a if index%2==0 else b:
                pytanie,opcje = PYTANIA[kod]
                nowe[kod] = st.selectbox(pytanie,opcje,index=opcje.index(odpowiedzi[kod]) if odpowiedzi.get(kod) in opcje else 0,key=f"a_{kod}")
        nowe["dodatkowe_informacje"] = st.text_area(PYTANIA["dodatkowe_informacje"][0],value=odpowiedzi.get("dodatkowe_informacje", ""),max_chars=1500,placeholder="Np. zależy mi na pracy z ludźmi i możliwości łączenia studiów z pracą…")
        wyslane = st.form_submit_button("Zapisz ankietę i odśwież rekomendacje",type="primary",width="stretch")
    if wyslane:
        try:
            dane.zapisz_ankiete(konto["id"],nowe)
            st.session_state["komunikat"]="Ankieta zapisana. Twój ranking został przeliczony."
            st.rerun()
        except ValueError as blad: st.error(str(blad))
