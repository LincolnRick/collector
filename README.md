# Collector

Interface web para visualizar e alimentar a API FastAPI do projeto Collector. O backend continua responsável por expor os endpoints de cartas Pokémon, enquanto o frontend em Streamlit oferece páginas para importação de CSV, listagem e análises rápidas da coleção.

## Requisitos

- Python 3.10+
- Pip ou outro gerenciador compatível

## Configuração do ambiente

1. Crie um arquivo `.env` na raiz do repositório com base em [`.env.example`](./.env.example).
2. Instale as dependências do projeto:

   ```bash
   pip install -r requirements.txt
   ```

## Executando o backend FastAPI

O backend pode ser iniciado com o Uvicorn apontando para o app FastAPI já existente:

```bash
uvicorn collector.api.routes:app --reload
```

Por padrão o servidor ficará disponível em `http://localhost:8000`.

## Executando o frontend Streamlit

1. Garanta que o backend esteja em execução e acessível pelo endereço configurado em `FASTAPI_BASE_URL`.
2. Inicie o Streamlit apontando para o arquivo principal do frontend:

   ```bash
   streamlit run frontend/app.py
   ```

As páginas ficarão acessíveis no navegador padrão exibindo:

- **Importar CSV:** upload de arquivos e envio em lote para a API.
- **Cartas:** listagem com filtros de nome, tipo e raridade, além de botões para marcar se cada carta já faz parte da sua coleção.
- **Coleção:** métricas e resumos da coleção cadastrada, com indicadores de progresso (cartas possuídas x faltantes).

### Imagens das cartas

Para que as imagens sejam exibidas no frontend, organize os arquivos correspondentes em uma pasta local e informe o caminho através da variável de ambiente `CARD_IMAGES_DIR` (por exemplo, `export CARD_IMAGES_DIR=./data/imagens`). O CSV deve conter o nome do arquivo na coluna `Imagem`. O Streamlit tentará localizar as imagens automaticamente nas seguintes pastas, em ordem:

1. Diretório configurado em `CARD_IMAGES_DIR`.
2. `./images`
3. `./data/images`

Caso a imagem não seja encontrada em nenhum desses caminhos, a carta será exibida sem miniatura.

## Estrutura relevante

```
collector/
├─ frontend/
│  ├─ app.py                 # Entrada do Streamlit
│  ├─ utils/api.py           # Cliente HTTP compartilhado
│  └─ pages/
│     ├─ 1_📥_Importar_CSV.py
│     ├─ 2_🃏_Cartas.py
│     └─ 3_📚_Coleção.py
└─ collector/                # Código do backend FastAPI
```

## Desenvolvimento

- Utilize `streamlit cache clear` caso precise limpar o cache das páginas entre execuções.
- Novas páginas podem ser adicionadas em `frontend/pages/` seguindo a convenção de prefixo numérico para ordenar o menu lateral.
