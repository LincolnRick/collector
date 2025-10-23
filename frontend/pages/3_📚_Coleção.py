"""Dashboard com indicadores gerais da coleção."""

from __future__ import annotations

from collections import Counter
from typing import Dict, List

import streamlit as st

from utils.api import CollectorAPIError, get_client

st.title("📚 Coleção")
st.write("Acompanhe métricas da coleção de cartas cadastrada no backend.")

client = get_client()


@st.cache_data(show_spinner=False)
def load_cards(base_url: str) -> List[Dict[str, object]]:
    return client.list_cards()


cards: List[Dict[str, object]] = []
error_message: str | None = None
try:
    cards = load_cards(client.base_url)
except CollectorAPIError as exc:
    error_message = str(exc)
except Exception as exc:  # pragma: no cover - feedback ao usuário
    error_message = f"Erro inesperado ao carregar dados: {exc}"

if error_message:
    st.error(error_message)
    st.stop()

if not cards:
    st.info("Ainda não há cartas cadastradas. Importe dados ou crie cartas manualmente.")
    st.stop()

for_trade = sum(1 for card in cards if card.get("for_trade"))
unique_sets = {card.get("set_name") for card in cards if card.get("set_name")}
unique_types = [card.get("type") for card in cards if card.get("type")]

col1, col2, col3 = st.columns(3)
col1.metric("Total de cartas", len(cards))
col2.metric("Disponíveis para troca", for_trade)
col3.metric("Conjuntos únicos", len(unique_sets))

st.subheader("Distribuição por raridade")
rarity_counter = Counter(card.get("rarity", "Desconhecida") or "Desconhecida" for card in cards)
chart_data = {
    "Raridade": list(rarity_counter.keys()),
    "Quantidade": list(rarity_counter.values()),
}
st.bar_chart(chart_data, x="Raridade", y="Quantidade", use_container_width=True)

st.subheader("Tipos encontrados")
if unique_types:
    type_counter = Counter(unique_types)
    st.write(
        "\n".join(
            f"- {type_name} ({count} cartas)"
            for type_name, count in type_counter.most_common()
        )
    )
else:
    st.write("Sem informação de tipo disponível.")

st.subheader("Principais conjuntos")
set_counter = Counter(card.get("set_name", "Desconhecido") or "Desconhecido" for card in cards)
most_common_sets = set_counter.most_common(10)
if most_common_sets:
    st.table(
        {
            "Conjunto": [name for name, _ in most_common_sets],
            "Cartas": [count for _, count in most_common_sets],
        }
    )
else:
    st.write("Sem dados de conjunto para exibir.")

if st.button("Atualizar indicadores"):
    load_cards.clear()
    st.experimental_rerun()
