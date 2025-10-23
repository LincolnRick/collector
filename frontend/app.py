"""Aplicação principal Streamlit para o Collector."""

from __future__ import annotations

import streamlit as st

from utils.api import get_client

st.set_page_config(page_title="Collector", page_icon="🃏", layout="wide")

client = get_client()

if "api_status" not in st.session_state:
    st.session_state.api_status = client.healthcheck()

st.sidebar.title("Collector")
st.sidebar.markdown(
    """
    Integração visual para o backend FastAPI existente. Utilize o menu lateral
    para navegar entre as páginas disponíveis e manipular a sua coleção de
    cartas Pokémon.
    """
)

api_base_url = client.base_url
st.sidebar.markdown("**API FastAPI**: %s" % api_base_url)
status_icon = "🟢" if st.session_state.api_status else "🔴"
st.sidebar.markdown(f"**Status da API**: {status_icon}")

st.sidebar.caption(
    "Configure o arquivo `.env` com a URL correta do backend antes de executar `streamlit run frontend/app.py`."
)

st.title("Collector 🧾")
st.write(
    "Bem-vindo ao painel da sua coleção de cartas Pokémon! Selecione uma das páginas no menu lateral para começar."
)

st.info(
    "Caso esteja executando o backend localmente, certifique-se de iniciar o servidor FastAPI antes do Streamlit."
)
