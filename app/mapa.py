"""Interaktywna mapa z wyborem miejsca zamieszkania."""

from html import escape

import folium
from folium.plugins import MarkerCluster
import streamlit as st
from streamlit_folium import st_folium

from app import dane
from app.geo import miejscowosci, znajdz_miasto


def pokaz_mape(konto, profil, oferty):
    st.subheader("Twoje miejsce. Twoje możliwości.")
    st.caption("Wskaż dom na mapie lub wybierz miejscowość. Zapisana lokalizacja posłuży do obliczania przybliżonej odległości.")
    miasta = miejscowosci()
    etykiety = [f"{x['nazwa']} · {x['wojewodztwo']}" for x in miasta]
    a,b = st.columns([3,1],vertical_alignment="bottom")
    with a:
        wybrane = st.selectbox("Miejscowość zamieszkania",range(len(miasta)),format_func=lambda i:etykiety[i],index=None,placeholder="Wyszukaj swoją miejscowość…",key="miasto_domu")
    with b:
        if st.button("Zapisz miejscowość",disabled=wybrane is None,width="stretch"):
            miasto = miasta[wybrane]
            dane.zapisz_lokalizacje(konto["id"],miasto["nazwa"],miasto["szerokosc"],miasto["dlugosc"],profil.get("maksymalny_dystans",300))
            st.session_state["komunikat"] = "Zapisano miejsce zamieszkania. Odległości i ranking zostały przeliczone."
            st.rerun()
    wybor = st.toggle("Wybieram dokładny punkt zamieszkania na mapie",value=False,key="wybor_punktu")
    dom = (profil.get("szerokosc"),profil.get("dlugosc"))
    srodek = list(dom) if all(x is not None for x in dom) else [52.0,19.2]
    mapa = folium.Map(location=srodek,zoom_start=7 if dom[0] is not None else 6,tiles="OpenStreetMap",control_scale=True)
    klaster = MarkerCluster(name="Miejscowości uczelni").add_to(mapa)
    uczelnie = {}
    for oferta in oferty:
        if oferta.get("szerokosc") is not None:
            uczelnie.setdefault(oferta["id_uczelni"],oferta)
    for oferta in list(uczelnie.values())[:1000]:
        popup = f"<b>{escape(oferta['uczelnia'])}</b><br>{escape(oferta.get('miasto') or '')}<br>Przybliżona lokalizacja miejscowości"
        folium.Marker([oferta["szerokosc"],oferta["dlugosc"]],tooltip=escape(oferta["uczelnia"]),popup=folium.Popup(popup,max_width=280),icon=folium.Icon(color="cadetblue",icon="graduation-cap",prefix="fa")).add_to(klaster)
    if dom[0] is not None:
        folium.Marker(list(dom),tooltip="Twoje miejsce zamieszkania",icon=folium.Icon(color="green",icon="home",prefix="fa")).add_to(mapa)
    wynik = st_folium(mapa,height=490,use_container_width=True,returned_objects=["last_clicked"],key=f"mapa_{konto['id']}")
    if wybor and wynik and wynik.get("last_clicked"):
        punkt = wynik["last_clicked"]
        st.info(f"Wybrany punkt: {punkt['lat']:.5f}, {punkt['lng']:.5f}")
        if st.button("Zapisz ten punkt jako miejsce zamieszkania",type="primary"):
            dane.zapisz_lokalizacje(konto["id"],"Punkt wskazany na mapie",punkt["lat"],punkt["lng"],profil.get("maksymalny_dystans",300))
            st.session_state["komunikat"] = "Zapisano wskazany punkt. Ranking uwzględnia nową lokalizację."
            st.rerun()
    st.caption(f"Na mapie: {len(uczelnie)} uczelni z rozpoznaną miejscowością. Znaczniki pokazują miejscowości, nie dokładne budynki. Odległości są w linii prostej, nie czasem dojazdu.")
    st.markdown("<div class='small-note'>Współrzędne: <a href='https://www.geonames.org/'>GeoNames (CC BY 4.0)</a> · Mapa: © OpenStreetMap contributors. Podkład mapy wymaga internetu.</div>",unsafe_allow_html=True)
