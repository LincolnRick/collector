"""Página para importar cartas a partir de um arquivo CSV."""

from __future__ import annotations

import csv
import io
from typing import Any, Dict, List

import streamlit as st

from utils.api import get_client, parse_card_payload

st.title("📥 Importar CSV")
st.write(
    "Carregue um arquivo CSV contendo informações das cartas para enviá-las ao backend."
)


def _read_csv(uploaded_file: Any) -> List[Dict[str, Any]]:
    content = uploaded_file.read().decode("utf-8-sig")
    uploaded_file.seek(0)
    buffer = io.StringIO(content)
    reader = csv.DictReader(buffer)
    rows: List[Dict[str, Any]] = []
    for row in reader:
        rows.append({key.strip(): value for key, value in row.items()})
    return rows


def _ensure_session_state() -> None:
    if "csv_rows" not in st.session_state:
        st.session_state.csv_rows = []
    if "csv_import_result" not in st.session_state:
        st.session_state.csv_import_result = None


_ensure_session_state()

uploaded_file = st.file_uploader("Selecione um arquivo CSV", type="csv")
if uploaded_file is not None:
    try:
        rows = _read_csv(uploaded_file)
        if not rows:
            st.warning("O arquivo está vazio.")
        else:
            st.session_state.csv_rows = rows
            st.success(f"Foram identificadas {len(rows)} linhas prontas para importação.")
    except UnicodeDecodeError:
        st.error("Não foi possível decodificar o arquivo. Utilize codificação UTF-8.")
    except csv.Error as exc:
        st.error(f"Erro ao ler o CSV: {exc}")

if st.session_state.csv_rows:
    st.subheader("Pré-visualização")
    st.dataframe(st.session_state.csv_rows, width="stretch")

    client = get_client()

    if st.button("Enviar para a API", type="primary"):
        with st.spinner("Importando cartas..."):
            payloads = [parse_card_payload(row) for row in st.session_state.csv_rows]
            created, errors = client.bulk_create(payloads)
            st.session_state.csv_import_result = {"created": created, "errors": errors}

if st.session_state.get("csv_import_result"):
    result = st.session_state.csv_import_result
    created = result.get("created", [])
    errors = result.get("errors", [])

    if created:
        st.success(f"{len(created)} cartas importadas com sucesso!")

    if errors:
        st.error("Algumas linhas não puderam ser importadas:")
        st.table(errors)

    if st.button("Limpar resultados"):
        st.session_state.csv_rows = []
        st.session_state.csv_import_result = None
        st.experimental_rerun()

if not st.session_state.csv_rows and not st.session_state.get("csv_import_result"):
    st.info(
        "Após carregar um arquivo válido, utilize o botão de importação para enviar as cartas ao backend."
    )
