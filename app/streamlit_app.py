import streamlit as st

from app.database import initialize_database, polaczenie
from app.radon import importuj_wszystko, pobierz_katalog

st.set_page_config(page_title="Rekomendacje kierunków studiów")
initialize_database()
st.title("Rekomendacje kierunków studiów")
st.write("Środowisko gotowe do pracy.")
st.write("Mój pierwszy tekst")


st.subheader("Katalog studiów")
st.caption("Źródło: RAD-on/POL-on. Rejestr prowadzonych studiów nie potwierdza otwartej rekrutacji ani progów przyjęcia.")
st.caption("Wyświetlamy studia pierwszego stopnia i jednolite magisterskie. Miasto oznacza siedzibę uczelni prowadzącej.")
szukaj = st.text_input("Szukaj kierunku, uczelni lub miasta")
katalog = pobierz_katalog(szukaj)
st.write(f"Liczba pasujących wariantów studiów: {len(katalog)}")
st.dataframe(katalog, hide_index=True)
st.markdown("[Dokumentacja źródła danych RAD-on](https://radon.nauka.gov.pl/pomoc/knowledge-base/kierunki-studiow-uruchomienia-pol-on-scenariusze-uzycia-uslugi/)")

st.subheader("Aktualizacja danych")
st.write("Pobierz pełne katalogi instytucji i kierunków z RAD-on, wraz ze wszystkimi poziomami i wariantami studiów. Pobieranie wymaga internetu i może potrwać kilka minut.")
if st.button("Pobierz wszystkie dane z API", type="primary"):
    pasek = st.progress(0.0, text="Przygotowywanie pobierania…")

    def pokaz_postep(etap, pobrano, razem):
        udzial = min(pobrano / razem, 1.0) if razem else 0.0
        if etap == "instytucje":
            pasek.progress(0.2 * udzial, text=f"Instytucje: {pobrano} / {razem or '?'}")
        elif etap == "kierunki":
            pasek.progress(0.2 + 0.7 * udzial, text=f"Kierunki: {pobrano} / {razem or '?'}")
        else:
            pasek.progress(0.9 + 0.1 * udzial, text="Zapisywanie danych w bazie…")

    try:
        wynik = importuj_wszystko(postep=pokaz_postep)
        st.session_state["wynik_importu"] = (
            f"Pobrano wszystkie dane: {wynik['instytucje']} instytucji, "
            f"{wynik['kierunki']} kierunków i {wynik['warianty']} wariantów studiów."
        )
        st.rerun()
    except (ValueError, PermissionError) as blad:
        st.error(str(blad))
    finally:
        pasek.empty()
if "wynik_importu" in st.session_state:
    st.success(st.session_state.pop("wynik_importu"))
with polaczenie() as baza:
    historia = [dict(wiersz) for wiersz in baza.execute(
        "SELECT rodzaj, zakres, adres_zrodla, liczba_instytucji, liczba_kierunkow, liczba_wariantow, data_pobrania, data_importu "
        "FROM historia_importow ORDER BY id DESC LIMIT 10"
    )]
st.write("Ostatnie importy")
st.dataframe(historia, hide_index=True)
