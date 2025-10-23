"""Página para listar e filtrar cartas cadastradas."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

import streamlit as st

from utils.api import CollectorAPIError, get_client

st.title("🃏 Cartas")
st.write("Consulte as cartas cadastradas via API e aplique filtros rápidos.")

client = get_client()


@st.cache_data(show_spinner=False)
def load_cards(base_url: str) -> List[Dict[str, Any]]:
    return client.list_cards()


cards: List[Dict[str, Any]] = []
error_message: str | None = None
try:
    cards = load_cards(client.base_url)
except CollectorAPIError as exc:
    error_message = str(exc)
except Exception as exc:  # pragma: no cover - feedback ao usuário
    error_message = f"Erro inesperado ao buscar cartas: {exc}"

if error_message:
    st.error(error_message)
    st.stop()

if not cards:
    st.info("Nenhuma carta cadastrada até o momento.")
    if st.button("Recarregar"):
        load_cards.clear()
        st.experimental_rerun()
    st.stop()

name_filter = st.text_input("Filtrar por nome", placeholder="Pikachu")
card_types = sorted({card.get("type") for card in cards if card.get("type")})
selected_type = st.selectbox("Tipo", options=["(todos)"] + card_types)
rarities = sorted({card.get("rarity") for card in cards if card.get("rarity")})
selected_rarity = st.selectbox("Raridade", options=["(todas)"] + rarities)

filtered_cards = cards
if name_filter:
    filtered_cards = [card for card in filtered_cards if name_filter.lower() in card.get("name", "").lower()]
if selected_type != "(todos)":
    filtered_cards = [card for card in filtered_cards if card.get("type") == selected_type]
if selected_rarity != "(todas)":
    filtered_cards = [card for card in filtered_cards if card.get("rarity") == selected_rarity]

st.caption(f"Mostrando {len(filtered_cards)} de {len(cards)} cartas.")

if st.button("Atualizar lista"):
    load_cards.clear()
    st.experimental_rerun()

if not filtered_cards:
    st.warning("Nenhuma carta corresponde aos filtros selecionados.")
else:
    st.dataframe(filtered_cards, use_container_width=True)

    with st.expander("Resumo por tipo"):
        by_type: Dict[str, int] = defaultdict(int)
        for card in filtered_cards:
            if card.get("type"):
                by_type[card["type"]] += 1
        if by_type:
            st.table({"Tipo": list(by_type.keys()), "Quantidade": list(by_type.values())})
        else:
            st.write("Sem dados de tipo disponíveis.")
