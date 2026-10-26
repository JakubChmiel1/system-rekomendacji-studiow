import streamlit as st

from app.database import initialize_database

st.set_page_config(page_title="Rekomendacje kierunków studiów")
initialize_database()
st.title("Rekomendacje kierunków studiów")
st.write("Środowisko gotowe do pracy.")
st.write("Mój pierwszy tekst")