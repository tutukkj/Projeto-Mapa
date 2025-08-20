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

# Usando 'left join' para manter todos os eventos do df_eventos
# e 'left_on'/'right_on' para mapear 'local_id' para 'id'.
df = pd.merge(
    df_eventos, df_locais,
    how="left",
    left_on="local_id",
    right_on="id",
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

# Datas, ano e hora
df['data_evento'] = pd.to_datetime(df['data_evento'], errors='coerce')
df = df.dropna(subset=['data_evento'])
df['ano'] = df['data_evento'].dt.year.astype('Int64')
df['hora'] = df['data_evento'].dt.hour

# ===== Normalizações importantes =====
# Usar dtype "string" do pandas para preservar NA (evita "Nan" string)
for col in ['bairro', 'cidade', 'evento_nome']:
    if col in df.columns:
        df[col] = df[col].astype('string')
        df[col] = df[col].str.strip()
        df[col] = df[col].replace({'': pd.NA})
        # padronização de capitalização (ignora NA)
        df[col] = df[col].str.title()

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

# Novo: Gera lista de horas para o filtro
horas = list(range(24))

# ==============================
# ZONAS (envelopes aproximados + centros)
# ==============================
zonas_coordenadas = {
    'Zona Leste':  {'lat_min': -23.66, 'lat_max': -23.45, 'lon_min': -46.62, 'lon_max': -46.36},
    'Zona Oeste':  {'lat_min': -23.62, 'lat_max': -23.50, 'lon_min': -46.84, 'lon_max': -46.67},
    'Zona Norte':  {'lat_min': -23.52, 'lat_max': -23.36, 'lon_min': -46.84, 'lon_max': -46.45},
    'Zona Sul':    {'lat_min': -24.00, 'lat_max': -23.62, 'lon_min': -46.84, 'lon_max': -46.50},
    'Zona Central':{'lat_min': -23.566, 'lat_max': -23.525,'lon_min': -46.67, 'lon_max': -46.62},
}

centros_regioes = {
    'Zona Central': {'lat': -23.5505, 'lon': -46.6333},
    'Zona Norte':   {'lat': -23.4950, 'lon': -46.6230},
    'Zona Leste':   {'lat': -23.5600, 'lon': -46.4900},
    'Zona Oeste':   {'lat': -23.5700, 'lon': -46.7000},
    'Zona Sul':     {'lat': -23.6800, 'lon': -46.6400},
}
zonas = list(zonas_coordenadas.keys())

def limpar_e_obter_unicos(coluna):
    if coluna in df.columns:
        # trabalha em cima do dtype string com NA preservado
        valores = df[coluna].dropna().unique().tolist()
        # ordena ignorando acentos/maiúsculas de forma simples
        return sorted(valores)
    return []

bairros  = limpar_e_obter_unicos('bairro')
cidades  = limpar_e_obter_unicos('cidade')
eventos  = limpar_e_obter_unicos('evento_nome')

# ==============================
# 2.2 LAYOUT DASH
# ==============================
app.layout = html.Div(
    style={'fontFamily': 'Arial, sans-serif', 'padding': '20px', 'backgroundColor': '#f0f2f5'},
    children=[
        # Painel de filtros agora fixo no topo
        html.Div([
            # Adiciona o título do dashboard aqui
            html.H1("DASHBOARD Ocorrências", style={'textAlign': 'center', 'color': '#333', 'paddingBottom': '20px'}),

            html.Div([
                html.Label("Ano:", className="filter-label"),
                dcc.Dropdown(
                    id='filtro-ano',
                    options=[{'label': str(ano), 'value': ano} for ano in anos],
                    value=None, clearable=True, placeholder="Todos",
                    style={'width': '200px', 'zIndex': 101}
                ),
            ], className="filter-group"),

            html.Div([
                html.Label("Cidade:", className="filter-label"),
                dcc.Dropdown(
                    id='filtro-cidade',
                    options=[{'label': c, 'value': c} for c in cidades],
                    value=None, clearable=True, placeholder="Todas",
                    style={'width': '200px', 'zIndex': 101}
                ),
            ], className="filter-group"),

            html.Div([
                html.Label("Bairro:", className="filter-label"),
                dcc.Dropdown(
                    id='filtro-bairro',
                    options=[{'label': b, 'value': b} for b in bairros],
                    value=None, clearable=True, placeholder="Todos",
                    style={'width': '200px', 'zIndex': 101}
                ),
            ], className="filter-group"),

            html.Div([
                html.Label("Zona:", className="filter-label"),
                dcc.Dropdown(
                    id='filtro-zona',
                    options=[{'label': z, 'value': z} for z in zonas],
                    value=None, clearable=True, placeholder="Todas",
                    style={'width': '200px', 'zIndex': 101}
                ),
            ], className="filter-group"),

            html.Div([
                html.Label("Evento:", className="filter-label"),
                dcc.Dropdown(
                    id='filtro-evento',
                    options=[{'label': e, 'value': e} for e in eventos],
                    value=None, clearable=True, placeholder="Todos",
                    style={'width': '200px', 'zIndex': 101}
                ),
            ], className="filter-group"),
            
            # Novo filtro de hora
            html.Div([
                html.Label("Hora:", className="filter-label"),
                dcc.Dropdown(
                    id='filtro-hora',
                    options=[{'label': f'{h:02d}:00', 'value': h} for h in horas],
                    value=None, clearable=True, placeholder="Todas",
                    style={'width': '200px', 'zIndex': 101}
                ),
            ], className="filter-group"),

        ], style={
            'position': 'sticky', 'top': '0', 'zIndex': '100',
            'display': 'flex', 'flexWrap': 'nowrap', 'gap': '40px', 'padding': '40px',
            'justifyContent': 'flex-start', 'backgroundColor': '#fff',
            'borderRadius': '12px', 'boxShadow': '0 4px 15px rgba(0,0,0,.1)',
            'marginBottom': '20px'
        }),

        # Contêiner para os gráficos
        html.Div([
            # NOVO: Contêiner para o mapa
            html.Div([
                html.Div(
                    id="evento-frequente",
                    style={
                        'textAlign': 'center', 'fontSize': '18px', 'marginBottom': '15px',
                        'color': '#333', 'fontWeight': 'bold'
                    }
                ),
                dcc.Graph(
                    id='mapa-eventos',
                    style={'height': '60vh', 'boxShadow': '0 4px 8px rgba(0,0,0,.1)', 'borderRadius': '8px'},
                    config={'scrollZoom': True, 'displayModeBar': False}
                ),
            ], style={
                'backgroundColor': '#fff', 'padding': '20px', 'borderRadius': '12px',
                'boxShadow': '0 4px 15px rgba(0,0,0,.1)', 'marginBottom': '20px'
            }),

            dcc.Graph(
                id='grafico-hora',
                config={'displayModeBar': False},
                style={'height': '40vh', 'boxShadow': '0 4px 8px rgba(0,0,0,.1)', 'borderRadius': '8px'}
            )
        ])
    ]
)

# ==============================
# 2.3 CALLBACKS
# ==============================
ZOOM_PADRAO = 10.5
ZOOM_POR_ZONA = 11
ZOOM_POR_CIDADE = 12
ZOOM_POR_BAIRRO = 14

CENTRO_SP = {
    'lat': centros_regioes['Zona Central']['lat'],
    'lon': centros_regioes['Zona Central']['lon']
}

# Callback para o mapa de calor e evento mais frequente
# NOVO: Adiciona filtro de hora como input
@app.callback(
    [Output('mapa-eventos', 'figure'),
     Output('evento-frequente', 'children')],
    [Input('filtro-ano', 'value'),
     Input('filtro-cidade', 'value'),
     Input('filtro-bairro', 'value'),
     Input('filtro-zona', 'value'),
     Input('filtro-evento', 'value'),
     Input('filtro-hora', 'value')] # Novo input
)
def atualizar_mapa(ano_selecionado, cidade_selecionada, bairro_selecionado, zona_selecionada, evento_selecionado, hora_selecionada):
    df_filtrado = df

    # --- Filtros combinados (AND) ---
    if ano_selecionado is not None:
        df_filtrado = df_filtrado[df_filtrado['ano'] == ano_selecionado]
    if cidade_selecionada:
        df_filtrado = df_filtrado[df_filtrado['cidade'] == cidade_selecionada]
    if bairro_selecionado:
        df_filtrado = df_filtrado[df_filtrado['bairro'] == bairro_selecionado]
    if zona_selecionada:
        coords = zonas_coordenadas[zona_selecionada]
        df_filtrado = df_filtrado[
            (df_filtrado['latitude'] >= coords['lat_min']) &
            (df_filtrado['latitude'] <= coords['lat_max']) &
            (df_filtrado['longitude'] >= coords['lon_min']) &
            (df_filtrado['longitude'] <= coords['lon_max'])
        ]
    if evento_selecionado:
        df_filtrado = df_filtrado[df_filtrado['evento_nome'] == evento_selecionado]
    # NOVO: Filtra o DataFrame pela hora selecionada
    if hora_selecionada is not None:
        df_filtrado = df_filtrado[df_filtrado['hora'] == hora_selecionada]

    # --- Centro/Zoom por prioridade: bairro > cidade > zona > default ---
    center_lat, center_lon, zoom = CENTRO_SP['lat'], CENTRO_SP['lon'], ZOOM_PADRAO
    if bairro_selecionado and not df_filtrado.empty:
        center_lat = df_filtrado['latitude'].mean()
        center_lon = df_filtrado['longitude'].mean()
        zoom = ZOOM_POR_BAIRRO
    elif cidade_selecionada and not df_filtrado.empty:
        center_lat = df_filtrado['latitude'].mean()
        center_lon = df_filtrado['longitude'].mean()
        zoom = ZOOM_POR_CIDADE
    elif zona_selecionada:
        center_lat = centros_regioes[zona_selecionada]['lat']
        center_lon = centros_regioes[zona_selecionada]['lon']
        zoom = ZOOM_POR_ZONA

    # --- Agrupamento para densidade ---
    contagem = df_filtrado.groupby(
        ["latitude", "longitude", "nome_local", "endereco_local", "numero"],
        dropna=True
    ).size().reset_index(name="casos")

    # --- Cartão: evento mais frequente (considerando filtros) ---
    if not df_filtrado.empty:
        vc = df_filtrado['evento_nome'].dropna().value_counts()
        if len(vc) > 0:
            top_evento = vc.index[0]
            top_cont = int(vc.iloc[0])
            evento_freq_text = f"🔝 Evento mais frequente: {top_evento} ({top_cont} ocorrências)"
        else:
            evento_freq_text = "Sem evento nomeado para os filtros atuais."
    else:
        evento_freq_text = "Nenhum evento encontrado."

    # --- Figura ---
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
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=16, color="#555")
        )

    fig.update_layout(margin={"r":0, "t":0, "l":0, "b":0})
    return fig, evento_freq_text


# Callback para o gráfico de eventos por hora
# NOTA: Este callback NÃO recebe o filtro de hora como input, conforme solicitado.
@app.callback(
    Output('grafico-hora', 'figure'),
    [Input('filtro-ano', 'value'),
     Input('filtro-cidade', 'value'),
     Input('filtro-bairro', 'value'),
     Input('filtro-zona', 'value'),
     Input('filtro-evento', 'value')]
)
def atualizar_grafico_hora(ano_selecionado, cidade_selecionada, bairro_selecionado, zona_selecionada, evento_selecionado):
    df_filtrado = df

    # --- Filtros combinados (AND) ---
    if ano_selecionado is not None:
        df_filtrado = df_filtrado[df_filtrado['ano'] == ano_selecionado]
    if cidade_selecionada:
        df_filtrado = df_filtrado[df_filtrado['cidade'] == cidade_selecionada]
    if bairro_selecionado:
        df_filtrado = df_filtrado[df_filtrado['bairro'] == bairro_selecionado]
    if zona_selecionada:
        coords = zonas_coordenadas[zona_selecionada]
        df_filtrado = df_filtrado[
            (df_filtrado['latitude'] >= coords['lat_min']) &
            (df_filtrado['latitude'] <= coords['lat_max']) &
            (df_filtrado['longitude'] >= coords['lon_min']) &
            (df_filtrado['longitude'] <= coords['lon_max'])
        ]
    if evento_selecionado:
        df_filtrado = df_filtrado[df_filtrado['evento_nome'] == evento_selecionado]

    # Contagem de eventos por hora
    contagem_hora = df_filtrado['hora'].value_counts().sort_index()

    # Criação do gráfico de barras
    fig = px.bar(
        x=contagem_hora.index,
        y=contagem_hora.values,
        labels={'x': 'Hora do Dia', 'y': 'Número de Eventos'},
        title="Distribuição de Eventos por Hora",
        template="plotly_white"
    )

    fig.update_layout(
        xaxis={'tickmode': 'linear'},
        yaxis={'tickformat': ',.0f'},
        title={'x': 0.5, 'xanchor': 'center'},
        margin={"r":20, "t":40, "l":20, "b":20}
    )

    return fig

# ==============================
# 3. EXECUÇÃO
# ==============================
if __name__ == "__main__":
    server.run(debug=True)
