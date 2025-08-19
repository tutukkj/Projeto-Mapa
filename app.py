# app.py
from flask import Flask, render_template, redirect
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import json
import os

# ==============================
# 1. SERVIDOR FLASK E DASH
# ==============================

# Cria o servidor Flask
server = Flask(__name__)

# Configura o Dash para usar o servidor Flask. 
# Removendo url_base_pathname para que o Dash rode na raiz, junto com o Flask.
app = Dash(__name__, server=server, url_base_pathname="/")

# ==============================
# 2. CARREGAMENTO E PREPARAÇÃO DOS DADOS
# ==============================
# Usa a variável de ambiente para garantir que os caminhos de arquivos funcionem no Vercel
# O Vercel coloca os arquivos na raiz do /var/task
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EVENTOS_PATH = os.path.join(BASE_DIR, "eventos.json")
LOCAIS_PATH = os.path.join(BASE_DIR, "locais.json")

try:
    with open(EVENTOS_PATH, "r", encoding="utf-8") as f:
        eventos = json.load(f)
    with open(LOCAIS_PATH, "r", encoding="utf-8") as f:
        locais = json.load(f)
except FileNotFoundError as e:
    print(f"Erro: O arquivo {e.filename} não foi encontrado.")
    # No Vercel, este erro de arquivo pode acontecer se os arquivos não forem incluídos na implantação.
    # Certifique-se de que os arquivos eventos.json e locais.json estão na raiz do seu repositório.
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
# ==============================
zonas_coordenadas = {
    'Zona Leste':   {'lat_min': -23.66, 'lat_max': -23.45, 'lon_min': -46.62, 'lon_max': -46.36},
    'Zona Oeste':   {'lat_min': -23.62, 'lat_max': -23.50, 'lon_min': -46.84, 'lon_max': -46.67},
    'Zona Norte':   {'lat_min': -23.52, 'lat_max': -23.36, 'lon_min': -46.84, 'lon_max': -46.45},
    'Zona Sul':   {'lat_min': -24.00, 'lat_max': -23.62, 'lon_min': -46.84, 'lon_max': -46.50},
    'Zona Central': {'lat_min': -23.566, 'lat_max': -23.525, 'lon_min': -46.67, 'lon_max': -46.62},
}

centros_regioes = {
    'Zona Central': {'lat': -23.5505, 'lon': -46.6333},
    'Zona Norte': {'lat': -23.4950, 'lon': -46.6230},
    'Zona Leste':   {'lat': -23.5600, 'lon': -46.4900},
    'Zona Oeste': {'lat': -23.5700, 'lon': -46.7000},
    'Zona Sul':   {'lat': -23.6800, 'lon': -46.6400},
}

zonas = list(zonas_coordenadas.keys())

def limpar_e_obter_unicos(coluna):
    if coluna in df.columns:
        valores = df[coluna].dropna().astype(str).str.strip().unique()
        return sorted([v for v in valores if v])
    return []

bairros = limpar_e_obter_unicos('bairro')
cidades = limpar_e_obter_unicos('cidade')

# ==============================
# 3. LAYOUT DASH
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
                value=None,
                clearable=True,
                placeholder="Todos",
                style={'width': '150px', 'marginRight': '20px'}
            ),

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
# 4. CALLBACK
# ==============================

ZOOM_PADRAO = 10.5
ZOOM_POR_ZONA = 11
ZOOM_POR_CIDADE = 12
ZOOM_POR_BAIRRO = 14

CENTRO_SP = {'lat': centros_regioes['Zona Central']['lat'],
             'lon': centros_regioes['Zona Central']['lon']}

@app.callback(
    Output('mapa-eventos', 'figure'),
    [Input('filtro-ano', 'value'),
     Input('filtro-cidade', 'value'),
     Input('filtro-bairro', 'value'),
     Input('filtro-zona', 'value')]
)
def atualizar_mapa(ano_selecionado, cidade_selecionada, bairro_selecionado, zona_selecionada):
    df_filtrado = df.copy()
    center_lat = CENTRO_SP['lat']
    center_lon = CENTRO_SP['lon']
    zoom = ZOOM_PADRAO
    
    if ano_selecionado:
        df_filtrado = df_filtrado[df_filtrado['ano'] == ano_selecionado]
    
    if bairro_selecionado:
        df_filtrado = df_filtrado[df_filtrado['bairro'] == bairro_selecionado]
        if not df_filtrado.empty:
            center_lat = df_filtrado['latitude'].mean()
            center_lon = df_filtrado['longitude'].mean()
            zoom = ZOOM_POR_BAIRRO
    elif cidade_selecionada:
        df_filtrado = df_filtrado[df_filtrado['cidade'] == cidade_selecionada]
        if not df_filtrado.empty:
            center_lat = df_filtrado['latitude'].mean()
            center_lon = df_filtrado['longitude'].mean()
            zoom = ZOOM_POR_CIDADE
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
    
    contagem = df_filtrado.groupby(
        ["latitude", "longitude", "nome_local", "endereco_local", "numero"],
        dropna=True
    ).size().reset_index(name="casos")

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
# 5. EXECUÇÃO
# ==============================

if __name__ == "__main__":
    server = app.server
