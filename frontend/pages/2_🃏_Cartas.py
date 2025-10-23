"""Página para listar e filtrar cartas cadastradas."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

import streamlit as st

from utils.api import CollectorAPIError, get_client
from utils.media import resolve_card_image

st.title("🃏 Cartas")
st.write("Consulte as cartas cadastradas via API, visualize as imagens e marque quais já fazem parte da sua coleção.")

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
        st.rerun()
    st.stop()

name_filter = st.text_input("Filtrar por nome", placeholder="Bulbasaur")
card_types = sorted({card.get("tipo") for card in cards if card.get("tipo")})
selected_type = st.selectbox("Tipo", options=["(todos)"] + card_types)
rarities = sorted({card.get("raridade") for card in cards if card.get("raridade")})
selected_rarity = st.selectbox("Raridade", options=["(todas)"] + rarities)

filtered_cards = cards
if name_filter:
    filtered_cards = [card for card in filtered_cards if name_filter.lower() in card.get("nome", "").lower()]
if selected_type != "(todos)":
    filtered_cards = [card for card in filtered_cards if card.get("tipo") == selected_type]
if selected_rarity != "(todas)":
    filtered_cards = [card for card in filtered_cards if card.get("raridade") == selected_rarity]

st.caption(f"Mostrando {len(filtered_cards)} de {len(cards)} cartas.")

if st.button("Atualizar lista"):
    load_cards.clear()
    st.rerun()

if not filtered_cards:
    st.warning("Nenhuma carta corresponde aos filtros selecionados.")
else:
    owned = sum(1 for card in filtered_cards if card.get("possui"))
    st.caption(f"Você possui {owned} de {len(filtered_cards)} cartas nesta visão.")

    cards_per_row = 3
    for start in range(0, len(filtered_cards), cards_per_row):
        row_cards = filtered_cards[start : start + cards_per_row]
        cols = st.columns(len(row_cards))
        for col, card in zip(cols, row_cards):
            with col:
                image_path = resolve_card_image(card.get("imagem"))
                if image_path:
                    st.image(image_path, caption=card.get("nome"), use_column_width=True)
                else:
                    st.markdown(f"**{card.get('nome', 'Carta sem nome')}**")

                st.markdown(
                    "\n".join(
                        filter(
                            None,
                            [
                                f"**HP:** {card.get('hp') or '-'}",
                                f"**Tipo:** {card.get('tipo') or '-'}",
                                f"**Raridade:** {card.get('raridade') or '-'}",
                                f"**Set:** {card.get('set') or '-'}",
                                f"**Número:** {card.get('numero') or '-'}",
                            ],
                        )
                    )
                )

                habilidade_nome = card.get("habilidade_nome")
                habilidade_desc = card.get("habilidade_desc")
                if habilidade_nome or habilidade_desc:
                    st.write(f"**Habilidade:** {habilidade_nome or '—'}")
                    if habilidade_desc:
                        st.caption(habilidade_desc)

                ataques = card.get("ataques")
                if ataques:
                    st.write(f"**Ataques:** {ataques}")

                if card.get("possui"):
                    st.success("Você possui esta carta.")
                    if st.button("Marcar como não tenho", key=f"unset_{card['id']}"):
                        with st.spinner("Atualizando carta..."):
                            client.update_card(card["id"], {"possui": False})
                        load_cards.clear()
                        st.rerun()
                else:
                    st.info("Você ainda não possui esta carta.")
                    if st.button("Marcar como tenho", key=f"set_{card['id']}"):
                        with st.spinner("Atualizando carta..."):
                            client.update_card(card["id"], {"possui": True})
                        load_cards.clear()
                        st.rerun()

    with st.expander("Resumo por tipo"):
        by_type: Dict[str, int] = defaultdict(int)
        for card in filtered_cards:
            if card.get("tipo"):
                by_type[card["tipo"]] += 1
        if by_type:
            st.table({"Tipo": list(by_type.keys()), "Quantidade": list(by_type.values())})
        else:
            st.write("Sem dados de tipo disponíveis.")
