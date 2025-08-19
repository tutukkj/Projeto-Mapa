# app.py
from flask import Flask, render_template
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import json

# ==============================
# 1. SERVIDOR FLASK
# ==============================
server = Flask(__name__)

@server.route('/')
def index():
    return render_template('index.html')

# ==============================
# 2. DASH
# ==============================
app = Dash(__name__, server=server, url_base_pathname='/dashboard/')

# ==============================
# 2.1 CARREGAMENTO E PREPARAÇÃO DOS DADOS
# ==============================
try:
    with open("eventos.json", "r", encoding="utf-8") as f:
        eventos = json.load(f)
    with open("locais.json", "r", encoding="utf-8") as f:
        locais = json.load(f)
except FileNotFoundError as e:
    print(f"Erro: O arquivo {e.filename} não foi encontrado.")
    raise SystemExit(1)

df_eventos = pd.DataFrame(eventos)
df_locais = pd.DataFrame(locais)

df = pd.merge(
    df_eventos, df_locais,
    how="inner",
    on="local_id",
    suffixes=("_evento", "_local")
)

df.rename(columns={
    "numero_local": "numero",
    "nome": "nome_local",
    "endereco": "endereco_local"
}, inplace=True)

# Coordenadas válidas
df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
df = df.dropna(subset=["latitude", "longitude"])

# Datas e ano
"""
df['data_criacao'] = pd.to_datetime(df['data_criacao'], errors='coerce')
df = df.dropna(subset=['data_criacao'])
df['ano'] = df['data_criacao'].dt.year.astype('Int64')
"""
df['data_evento'] = pd.to_datetime(df['data_evento'])
df['ano'] = df['data_evento'].dt.year.astype('Int64')

# Escala de cores
escala_personalizada = [
    [0.0, "rgba(0, 255, 255, 0)"],
    [0.01, "rgb(255, 255, 153)"],
    [0.1, "rgb(255, 204, 102)"],
    [0.4, "rgb(255, 102, 0)"],
    [0.7, "rgb(204, 51, 0)"],
    [1.0, "rgb(178, 24, 43)"]
]

anos = sorted([int(a) for a in df['ano'].dropna().unique()])

# ==============================
# ZONAS (envelopes aproximados + centros)
# Limite municipal (aprox.): W=-46.84, E=-46.36, N=-23.36, S=-24.00 (DataGeo/IGC)
# ==============================
zonas_coordenadas = {
    # Leste do município (lon >= -46.52), faixa central a norte. Ponto de referência: Brás.
    'Zona Leste':  {'lat_min': -23.66, 'lat_max': -23.45, 'lon_min': -46.62, 'lon_max': -46.36},
    # Oeste do município (lon <= -46.67), faixa central
    'Zona Oeste':  {'lat_min': -23.62, 'lat_max': -23.50, 'lon_min': -46.84, 'lon_max': -46.67},
    # Norte do Tietê (lat >= ~-23.52)
    'Zona Norte':  {'lat_min': -23.52, 'lat_max': -23.36, 'lon_min': -46.84, 'lon_max': -46.45},
    # Sul (inclui extremo sul rural)
    'Zona Sul':  {'lat_min': -24.00, 'lat_max': -23.62, 'lon_min': -46.84, 'lon_max': -46.50},
    # Centro histórico/ampliado
    'Zona Central': {'lat_min': -23.566, 'lat_max': -23.525, 'lon_min': -46.67, 'lon_max': -46.62},
}

centros_regioes = {
    'Zona Central': {'lat': -23.5505, 'lon': -46.6333},  # Sé
    'Zona Norte': {'lat': -23.4950, 'lon': -46.6230},  # Santana/Carandiru
    'Zona Leste':  {'lat': -23.5600, 'lon': -46.4900},  # Tatuapé/Itaquera (meio termo)
    'Zona Oeste':{'lat': -23.5700, 'lon': -46.7000}, # Butantã/Vila Sônia
    'Zona Sul':  {'lat': -23.6800, 'lon': -46.6400},  # Sto Amaro/Brooklin (meio termo)
}

zonas = list(zonas_coordenadas.keys())

# demais filtros
def limpar_e_obter_unicos(coluna):
    if coluna in df.columns:
        valores = df[coluna].dropna().astype(str).str.strip().unique()
        return sorted([v for v in valores if v])
    return []

bairros = limpar_e_obter_unicos('bairro')
# NOVO: obtem a lista de cidades únicas da coluna 'cidade'
cidades = limpar_e_obter_unicos('cidade')

# ==============================
# 2.2 LAYOUT DASH
# ==============================
app.layout = html.Div(
    style={'fontFamily': 'Arial, sans-serif', 'padding': '20px', 'backgroundColor': '#f0f2f5'},
    children=[
        html.H1("Mapa de Calor de Eventos", style={'textAlign': 'center', 'color': '#333'}),

        html.Div([
            html.Label("Ano:", style={'marginRight': '5px'}),
            dcc.Dropdown(
                id='filtro-ano',
                options=[{'label': str(ano), 'value': ano} for ano in anos],
                value=None,# sem filtro inicial
                clearable=True,
                placeholder="Todos",
                style={'width': '150px', 'marginRight': '20px'}
            ),

            # NOVO: Dropdown para o filtro de cidade
            html.Label("Cidade:", style={'marginRight': '5px'}),
            dcc.Dropdown(
                id='filtro-cidade',
                options=[{'label': c, 'value': c} for c in cidades],
                value=None,
                clearable=True,
                placeholder="Todas",
                style={'width': '220px', 'marginRight': '20px'}
            ),

            html.Label("Bairro:", style={'marginRight': '5px'}),
            dcc.Dropdown(
                id='filtro-bairro',
                options=[{'label': b, 'value': b} for b in bairros],
                value=None,
                clearable=True,
                placeholder="Todos",
                style={'width': '220px', 'marginRight': '20px'}
            ),

            html.Label("Zona:", style={'marginRight': '5px'}),
            dcc.Dropdown(
                id='filtro-zona',
                options=[{'label': z, 'value': z} for z in zonas],
                value=None,
                clearable=True,
                placeholder="Todas",
                style={'width': '180px'}
            ),
        ], style={
            'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
            'marginBottom': '20px', 'flexWrap': 'wrap'
        }),

        dcc.Graph(
            id='mapa-eventos',
            style={'height': '80vh', 'boxShadow': '0 4px 8px rgba(0,0,0,.1)', 'borderRadius': '8px'},
            config={'scrollZoom': True}
        )
    ]
)

# ==============================
# 2.3 CALLBACK
# ==============================
# Zooms ajustáveis
ZOOM_PADRAO = 10.5 # zoom quando NÃO há zona selecionada (centro da cidade)
ZOOM_POR_ZONA = 11 # zoom quando há zona selecionada (ajuste a gosto)
ZOOM_POR_CIDADE = 12  # NOVO: zoom para quando há cidade selecionada
ZOOM_POR_BAIRRO = 14 # NOVO: zoom para quando há bairro selecionado

# Centro padrão (igual ao “Centro”, porém com MENOS zoom)
CENTRO_SP = {'lat': centros_regioes['Zona Central']['lat'],
             'lon': centros_regioes['Zona Central']['lon']}

@app.callback(
    Output('mapa-eventos', 'figure'),
    [Input('filtro-ano', 'value'),
     # NOVO: Adiciona o input do filtro de cidade
     Input('filtro-cidade', 'value'),
     Input('filtro-bairro', 'value'),
     Input('filtro-zona', 'value')]
)
def atualizar_mapa(ano_selecionado, cidade_selecionada, bairro_selecionado, zona_selecionada):
    # 1) Sempre começa com uma cópia do dataframe completo
    df_filtrado = df.copy()
    center_lat = CENTRO_SP['lat']
    center_lon = CENTRO_SP['lon']
    zoom = ZOOM_PADRAO
    
    # Aplica os filtros, um por um
    if ano_selecionado:
        df_filtrado = df_filtrado[df_filtrado['ano'] == ano_selecionado]
    # Lógica de zoom por bairro
    if bairro_selecionado:
        df_filtrado = df_filtrado[df_filtrado['bairro'] == bairro_selecionado]
        if not df_filtrado.empty:
            center_lat = df_filtrado['latitude'].mean()
            center_lon = df_filtrado['longitude'].mean()
            zoom = ZOOM_POR_BAIRRO
    # Lógica de zoom por cidade
    elif cidade_selecionada:
        df_filtrado = df_filtrado[df_filtrado['cidade'] == cidade_selecionada]
        
        if not df_filtrado.empty:
            center_lat = df_filtrado['latitude'].mean()
            center_lon = df_filtrado['longitude'].mean()
            zoom = ZOOM_POR_CIDADE
    
    # Lógica de zoom para a zona (só é executada se a cidade e o bairro não forem selecionados)
    elif zona_selecionada:
        coords = zonas_coordenadas[zona_selecionada]
        df_filtrado = df_filtrado[
            (df_filtrado['latitude'] >= coords['lat_min']) &
            (df_filtrado['latitude'] <= coords['lat_max']) &
            (df_filtrado['longitude'] >= coords['lon_min']) &
            (df_filtrado['longitude'] <= coords['lon_max'])
        ]
        center_lat = centros_regioes[zona_selecionada]['lat']
        center_lon = centros_regioes[zona_selecionada]['lon']
        zoom = ZOOM_POR_ZONA
    

    # Agrupa por ponto/local para densidade
    contagem = df_filtrado.groupby(
        ["latitude", "longitude", "nome_local", "endereco_local", "numero"],
        dropna=True
    ).size().reset_index(name="casos")

    # Figura
    if not contagem.empty:
        fig = px.density_mapbox(
            contagem,
            lat="latitude",
            lon="longitude",
            z="casos",
            radius=18,
            center=dict(lat=center_lat, lon=center_lon),
            zoom=zoom,
            mapbox_style="open-street-map",
            color_continuous_scale=escala_personalizada,
            opacity=0.65
        )
    else:
        # Caso não haja dados, mostra um mapa estático com mensagem
        fig = px.scatter_mapbox(
            lat=[center_lat],
            lon=[center_lon],
            zoom=zoom,
            mapbox_style="open-street-map"
        )
        fig.add_annotation(
            text="Nenhum evento encontrado para os filtros selecionados.",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="#555")
        )

    fig.update_layout(margin={"r":0, "t":0, "l":0, "b":0})
    return fig

# ==============================
# 3. EXECUÇÃO
# ==============================
if __name__ == "__main__":
    server.run(debug=True)