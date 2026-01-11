import streamlit as st
from modules.map_utils import gerar_mapa
from streamlit_folium import st_folium

def aba_mapa(df_lt):

    st.header("🗺️ Mapa de Torres")

    if df_lt is None or df_lt.empty:
        st.warning("Nenhum dado carregado.")
        return

    mapa = gerar_mapa(df_lt)
    st_folium(mapa, width=800, height=550)
