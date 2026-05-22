import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from io import BytesIO

st.set_page_config(
    page_title="COMEX Tracker",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0f172a; }
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    
    /* KPI cards */
    .kpi-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        text-align: center;
    }
    .kpi-label { color: #94a3b8; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 4px; }
    .kpi-value { color: #f1f5f9; font-size: 2rem; font-weight: 800; line-height: 1; }
    .kpi-sub   { color: #64748b; font-size: 0.72rem; margin-top: 3px; }

    /* Alert banner */
    .alert-banner {
        background: linear-gradient(90deg, #7f1d1d 0%, #991b1b 100%);
        border: 1px solid #ef4444;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        color: #fca5a5;
        font-size: 0.85rem;
        margin-bottom: 0.75rem;
    }
    .alert-banner b { color: #fef2f2; }

    /* Section headers */
    .section-header {
        color: #94a3b8;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        border-bottom: 1px solid #1e293b;
        padding-bottom: 6px;
        margin-bottom: 12px;
        margin-top: 20px;
    }

    /* Status badges */
    .badge { display:inline-block; padding:2px 10px; border-radius:999px; font-size:0.75rem; font-weight:600; }
    .badge-transit  { background:#92400e; color:#fcd34d; }
    .badge-arrived  { background:#1e3a5f; color:#7dd3fc; }
    .badge-loaded   { background:#312e81; color:#a5b4fc; }
    .badge-delivered{ background:#14532d; color:#86efac; }
    .badge-pending  { background:#1e293b; color:#94a3b8; }
    .badge-alert    { background:#7f1d1d; color:#fca5a5; }

    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    div[data-testid="stMetric"] { background: #1e293b; border-radius: 10px; padding: 12px; border: 1px solid #334155; }
</style>
""", unsafe_allow_html=True)

# ── CONTAINER PREFIXES ───────────────────────────────────────────────────────
CONTAINER_PREFIXES = {
    'CMAU': 'CMA CGM', 'ONEU': 'ONE', 'KKFU': 'K-Line',
    'OOLU': 'OOCL', 'MSCU': 'MSC', 'MAEU': 'Maersk',
    'HLCU': 'Hapag-Lloyd', 'NYKU': 'NYK Line',
    'YMLU': 'Yang Ming', 'EISU': 'Evergreen'
}

STATUS_ORDER = ['Loaded', 'Departed', 'In Transit', 'Arrived', 'Delivered', 'Pendiente']
STATUS_COLORS = {
    'Loaded':    '#818cf8',
    'Departed':  '#c084fc',
    'In Transit':'#fb923c',
    'Arrived':   '#38bdf8',
    'Delivered': '#4ade80',
    'Pendiente': '#64748b',
    'ETA Vencida': '#ef4444',
}

# ── DEMO DATA ────────────────────────────────────────────────────────────────
TODAY = datetime.today()

def demo_data():
    rows = [
        # BL, Forwarder, Buque, Contenedor, Estado, ETD, ETA, Origen, Destino, Producto, KG, Obs
        ("MAEU250100123", "Craft ARG",    "MAERSK EDINBURGH", "MAEU4512398", "Delivered",  TODAY-timedelta(55), TODAY-timedelta(20), "Shanghai",    "Buenos Aires", "Reactivos de laboratorio",  2400, ""),
        ("MSCU250200456", "Craft ARG",    "MSC ANNA",         "MSCU7831045", "Delivered",  TODAY-timedelta(48), TODAY-timedelta(15), "Hong Kong",   "Buenos Aires", "Equipos de diagnóstico",    1800, ""),
        ("HLCU250300789", "Ultramar",     "EVER GIVEN II",    "HLCU3321098", "Arrived",    TODAY-timedelta(40), TODAY-timedelta(3),  "Ningbo",      "Buenos Aires", "Insumos biotecnológicos",   3100, "Liberación pendiente DUA"),
        ("ONEU250400012", "Ultramar",     "NYK DIANA",        "ONEU5828437", "Arrived",    TODAY-timedelta(38), TODAY-timedelta(5),  "Busan",       "Buenos Aires", "Cultivos celulares",        900,  "Inspección SENASA en curso"),
        ("CMAU250500345", "Craft ARG",    "CMA CGM MARCO POLO","CMAU1234567","In Transit", TODAY-timedelta(22), TODAY+timedelta(8),  "Rotterdam",   "Buenos Aires", "Anticuerpos monoclonales",  650,  ""),
        ("YMLU250600678", "Panalpina",    "YANG MING UNITY",  "YMLU9087654", "In Transit", TODAY-timedelta(18), TODAY+timedelta(12), "Hamburg",     "Buenos Aires", "Medios de cultivo",         2200, ""),
        ("OOLU250700901", "Panalpina",    "OOCL BERLIN",      "OOLU4456789", "In Transit", TODAY-timedelta(15), TODAY+timedelta(4),  "Felixstowe",  "Buenos Aires", "Kits ELISA",                750,  "ETA ajustada por clima"),
        ("EISU250800234", "Ultramar",     "EVER GLORY",       "EISU2234567", "In Transit", TODAY-timedelta(30), TODAY-timedelta(2),  "Qingdao",     "Buenos Aires", "Enzimas de restricción",    400,  "⚠️ ETA vencida - confirmar arribo"),
        ("MSCU250900567", "Craft ARG",    "MSC OSCAR",        "MSCU5543210", "In Transit", TODAY-timedelta(35), TODAY-timedelta(8),  "Shanghai",    "Buenos Aires", "Tubos de centrífuga",       1200, "⚠️ Sin novedad del forwarder"),
        ("MAEU251000890", "DB Schenker",  "MAERSK STOCKHOLM", "MAEU8876543", "Departed",   TODAY-timedelta(8),  TODAY+timedelta(22), "Los Angeles", "Buenos Aires", "Reactivos PCR",             550,  ""),
        ("HLCU251100123", "DB Schenker",  "HAPAG INNOVATION", "HLCU6654321", "Departed",   TODAY-timedelta(5),  TODAY+timedelta(25), "New York",    "Buenos Aires", "Plásticos de laboratorio",  3400, ""),
        ("CMAU251200456", "Panalpina",    "CMA CGM JULES VERNE","CMAU9987654","Loaded",    TODAY-timedelta(2),  TODAY+timedelta(30), "Shanghai",    "Buenos Aires", "Filtros HEPA",              800,  ""),
        ("ONEU251300789", "Craft ARG",    "ONE COSMOS",       "ONEU1123456", "Loaded",     TODAY-timedelta(1),  TODAY+timedelta(32), "Hong Kong",   "Buenos Aires", "Pipetas y consumibles",     1600, ""),
        ("YMLU251400012", "Ultramar",     "YANG MING WITNESS","YMLU3345678", "Pendiente",  None,                TODAY+timedelta(45), "Ningbo",      "Buenos Aires", "Columnas de cromatografía", 320,  "Booking confirmado"),
        ("OOLU251500345", "DB Schenker",  "OOCL HONG KONG",   "OOLU7789012", "Pendiente",  None,                TODAY+timedelta(50), "Busan",       "Buenos Aires", "Viales estériles",          2800, "En proceso de OC"),
    ]
    cols = ["BL","Forwarder","Buque","Contenedor","Estado","ETD","ETA",
            "Puerto Origen","Puerto Destino","Descripcion","Peso KG","Observaciones"]
    df = pd.DataFrame(rows, columns=cols)
    df["Carrier"] = df["Contenedor"].apply(lambda x: CONTAINER_PREFIXES.get(str(x)[:4].upper(), ""))
    return df

# ── HELPERS ──────────────────────────────────────────────────────────────────
def detect_carrier(container):
    if pd.isna(container) or not container:
        return ''
    return CONTAINER_PREFIXES.get(str(container)[:4].upper(), '')

def dias_en_transito(etd):
    try:
        etd_dt = pd.to_datetime(etd)
        if pd.isna(etd_dt):
            return None
        return (TODAY - etd_dt).days
    except:
        return None

def is_eta_vencida(row):
    if row["Estado"] in ["Delivered", "Pendiente"]:
        return False
    try:
        eta = pd.to_datetime(row["ETA"])
        if pd.isna(eta):
            return False
        return eta.date() < TODAY.date()
    except:
        return False

def kpi_card(label, value, sub=""):
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>"""

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚢 COMEX Tracker")
    st.markdown("<div class='section-header'>Cargar datos</div>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Excel o CSV", type=['xlsx', 'xls', 'csv'],
        help="Columnas requeridas: Forwarder, Buque, BL"
    )
    use_demo = st.toggle("Usar datos demo", value=uploaded_file is None)

    st.markdown("<div class='section-header'>Filtros</div>", unsafe_allow_html=True)

    # Placeholder — se llenará después de cargar datos
    filter_estado   = st.empty()
    filter_forwarder = st.empty()
    filter_carrier  = st.empty()
    filter_search   = st.empty()

    st.markdown("<div class='section-header'>Columnas requeridas</div>", unsafe_allow_html=True)
    st.caption("Forwarder · Buque · BL\nOpcionales: Contenedor, Carrier, Estado, ETD, ETA, Puerto Origen, Puerto Destino, Peso KG, Descripcion, Observaciones")

# ── LOAD DATA ────────────────────────────────────────────────────────────────
df_raw = None

if uploaded_file and not use_demo:
    try:
        ext = uploaded_file.name.split('.')[-1].lower()
        df_raw = pd.read_csv(uploaded_file) if ext == 'csv' else pd.read_excel(uploaded_file)
        df_raw.columns = df_raw.columns.str.strip()
        if 'Carrier' not in df_raw.columns:
            df_raw['Carrier'] = df_raw.get('Contenedor', pd.Series()).apply(detect_carrier)
        for col, default in [('Estado','Pendiente'),('ETD',''),('ETA',''),
                              ('Puerto Origen',''),('Puerto Destino',''),
                              ('Peso KG',''),('Descripcion',''),('Observaciones',''),
                              ('Contenedor',''),('Carrier','')]:
            if col not in df_raw.columns:
                df_raw[col] = default
        st.sidebar.success(f"✅ {uploaded_file.name}")
    except Exception as e:
        st.sidebar.error(f"Error: {e}")
        df_raw = demo_data()
else:
    df_raw = demo_data()
    if use_demo:
        st.sidebar.info("📊 Mostrando datos demo")

# ── ENRICH ───────────────────────────────────────────────────────────────────
df = df_raw.copy()
df["Días en Tránsito"] = df["ETD"].apply(dias_en_transito)
df["ETA Vencida"] = df.apply(is_eta_vencida, axis=1)
df["Estado Visual"] = df.apply(
    lambda r: "ETA Vencida" if r["ETA Vencida"] else r["Estado"], axis=1
)

# ── SIDEBAR FILTERS (now data is loaded) ────────────────────────────────────
with st.sidebar:
    estados_opts = ['Todos'] + STATUS_ORDER
    sel_estado = filter_estado.selectbox("Estado", estados_opts)

    fwd_opts = ['Todos'] + sorted(df['Forwarder'].dropna().unique().tolist())
    sel_fwd = filter_forwarder.selectbox("Forwarder", fwd_opts)

    car_opts = ['Todos'] + sorted([c for c in df['Carrier'].dropna().unique() if c])
    sel_carrier = filter_carrier.selectbox("Carrier", car_opts)

    search = filter_search.text_input("🔍 Buscar BL / Buque / Contenedor", "")

# ── APPLY FILTERS ────────────────────────────────────────────────────────────
dff = df.copy()
if sel_estado != 'Todos':
    dff = dff[dff['Estado'] == sel_estado]
if sel_fwd != 'Todos':
    dff = dff[dff['Forwarder'] == sel_fwd]
if sel_carrier != 'Todos':
    dff = dff[dff['Carrier'] == sel_carrier]
if search:
    mask = (
        dff['BL'].astype(str).str.contains(search, case=False, na=False) |
        dff['Buque'].astype(str).str.contains(search, case=False, na=False) |
        dff['Contenedor'].astype(str).str.contains(search, case=False, na=False)
    )
    dff = dff[mask]

# ── HEADER ───────────────────────────────────────────────────────────────────
col_title, col_date = st.columns([4, 1])
with col_title:
    st.markdown("## 🚢 COMEX · Shipment Tracker")
with col_date:
    st.markdown(f"<div style='text-align:right; color:#64748b; padding-top:12px; font-size:0.8rem'>{TODAY.strftime('%d/%m/%Y')}</div>", unsafe_allow_html=True)

# ── ALERTS ───────────────────────────────────────────────────────────────────
alertas = df[df["ETA Vencida"] == True]
if len(alertas) > 0:
    for _, row in alertas.iterrows():
        eta_str = pd.to_datetime(row['ETA']).strftime('%d/%m') if pd.notna(row['ETA']) and row['ETA'] != '' else "?"
        dias_over = (TODAY - pd.to_datetime(row['ETA'])).days if pd.notna(row['ETA']) and row['ETA'] != '' else "?"
        st.markdown(f"""
        <div class="alert-banner">
            🚨 <b>ETA VENCIDA</b> · {row['BL']} · {row['Descripcion'] or row['Buque']} 
            · ETA original: {eta_str} · <b>{dias_over} días de demora</b>
            {f" · {row['Observaciones']}" if row['Observaciones'] else ""}
        </div>""", unsafe_allow_html=True)

# ── KPIs ─────────────────────────────────────────────────────────────────────
total      = len(df)
en_transito = len(df[df['Estado'].isin(['In Transit', 'Departed'])])
arribados  = len(df[df['Estado'] == 'Arrived'])
entregados = len(df[df['Estado'] == 'Delivered'])
alertas_n  = len(alertas)
avg_dias   = df[df['Días en Tránsito'].notna() & df['Estado'].isin(['In Transit','Departed'])]['Días en Tránsito'].mean()

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.markdown(kpi_card("Total Embarques", total, "en seguimiento"), unsafe_allow_html=True)
k2.markdown(kpi_card("En Tránsito", en_transito, "Departed + In Transit"), unsafe_allow_html=True)
k3.markdown(kpi_card("Arribados", arribados, "pendientes de liberación"), unsafe_allow_html=True)
k4.markdown(kpi_card("Entregados", entregados, "ciclo completo"), unsafe_allow_html=True)
k5.markdown(kpi_card("⚠️ Alertas ETA", alertas_n, "ETA vencida activa"), unsafe_allow_html=True)
k6.markdown(kpi_card("Días Prom. Tránsito", f"{avg_dias:.0f}" if pd.notna(avg_dias) else "—", "embarques activos"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── CHARTS ───────────────────────────────────────────────────────────────────
ch1, ch2 = st.columns([1, 1])

with ch1:
    st.markdown("<div class='section-header'>Estado de embarques</div>", unsafe_allow_html=True)
    counts = df.groupby('Estado Visual').size().reset_index(name='n')
    counts['color'] = counts['Estado Visual'].map(STATUS_COLORS)
    # Ordenar
    order_map = {s: i for i, s in enumerate(STATUS_ORDER + ['ETA Vencida'])}
    counts['order'] = counts['Estado Visual'].map(lambda x: order_map.get(x, 99))
    counts = counts.sort_values('order')

    fig_bar = px.bar(
        counts, x='Estado Visual', y='n',
        color='Estado Visual',
        color_discrete_map=STATUS_COLORS,
        text='n',
        height=280,
    )
    fig_bar.update_traces(textposition='outside', textfont_size=13)
    fig_bar.update_layout(
        plot_bgcolor='#0f172a', paper_bgcolor='#0f172a',
        font_color='#94a3b8', showlegend=False,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(showgrid=False, color='#475569'),
        yaxis=dict(showgrid=True, gridcolor='#1e293b', color='#475569'),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with ch2:
    st.markdown("<div class='section-header'>Embarques por forwarder</div>", unsafe_allow_html=True)
    fwd_counts = df.groupby('Forwarder').size().reset_index(name='n').sort_values('n', ascending=True)
    fig_fwd = px.bar(
        fwd_counts, x='n', y='Forwarder', orientation='h',
        color='n', color_continuous_scale=['#1e3a5f', '#38bdf8'],
        text='n', height=280,
    )
    fig_fwd.update_traces(textposition='outside', textfont_size=13)
    fig_fwd.update_layout(
        plot_bgcolor='#0f172a', paper_bgcolor='#0f172a',
        font_color='#94a3b8', showlegend=False, coloraxis_showscale=False,
        margin=dict(l=0, r=20, t=10, b=0),
        xaxis=dict(showgrid=True, gridcolor='#1e293b', color='#475569'),
        yaxis=dict(showgrid=False, color='#475569'),
    )
    st.plotly_chart(fig_fwd, use_container_width=True)

# ── TABLE ────────────────────────────────────────────────────────────────────
st.markdown(f"<div class='section-header'>Embarques · {len(dff)} resultado{'s' if len(dff)!=1 else ''}</div>", unsafe_allow_html=True)

display_cols = ['BL', 'Forwarder', 'Buque', 'Contenedor', 'Carrier',
                'Estado', 'ETD', 'ETA', 'Días en Tránsito',
                'Puerto Origen', 'Puerto Destino', 'Descripcion', 'Peso KG']
df_show = dff[[c for c in display_cols if c in dff.columns]].copy()

# Format dates
for dcol in ['ETD', 'ETA']:
    if dcol in df_show.columns:
        df_show[dcol] = pd.to_datetime(df_show[dcol], errors='coerce').dt.strftime('%d/%m/%Y').fillna('—')

def color_estado(val):
    colors = {
        'Loaded':    'background-color:#312e81; color:#a5b4fc',
        'Departed':  'background-color:#4c1d95; color:#c4b5fd',
        'In Transit':'background-color:#78350f; color:#fcd34d',
        'Arrived':   'background-color:#0c4a6e; color:#7dd3fc',
        'Delivered': 'background-color:#14532d; color:#86efac',
        'Pendiente': 'background-color:#1e293b; color:#64748b',
    }
    return colors.get(val, '')

def color_dias(val):
    try:
        v = int(val)
        if v > 40: return 'color:#ef4444; font-weight:bold'
        if v > 25: return 'color:#fb923c'
        return 'color:#4ade80'
    except:
        return ''

styled = df_show.style\
    .map(color_estado, subset=['Estado'])\
    .map(color_dias, subset=['Días en Tránsito'] if 'Días en Tránsito' in df_show.columns else [])\
    .set_properties(**{'font-size': '13px'})

st.dataframe(styled, height=380, use_container_width=True)

# ── DETALLE ──────────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Detalle de embarque</div>", unsafe_allow_html=True)

if len(dff) > 0:
    bl_list = dff['BL'].tolist()
    sel_bl = st.selectbox("Seleccionar BL", bl_list, label_visibility="collapsed")
    ship = dff[dff['BL'] == sel_bl].iloc[0]

    d1, d2, d3 = st.columns(3)
    with d1:
        st.markdown(f"**BL:** `{ship['BL']}`")
        st.markdown(f"**Buque:** {ship['Buque']}")
        st.markdown(f"**Carrier:** {ship.get('Carrier','—') or '—'}")
        st.markdown(f"**Contenedor:** {ship.get('Contenedor','—') or '—'}")
    with d2:
        eta_raw = pd.to_datetime(ship['ETA'], errors='coerce')
        etd_raw = pd.to_datetime(ship['ETD'], errors='coerce')
        eta_str = eta_raw.strftime('%d/%m/%Y') if pd.notna(eta_raw) else '—'
        etd_str = etd_raw.strftime('%d/%m/%Y') if pd.notna(etd_raw) else '—'
        estado_badge = ship['Estado']
        alerta = " ⚠️ ETA VENCIDA" if ship['ETA Vencida'] else ""
        st.markdown(f"**Estado:** {estado_badge}{alerta}")
        st.markdown(f"**ETD:** {etd_str}")
        st.markdown(f"**ETA:** {eta_str}")
        dias = ship.get('Días en Tránsito')
        st.markdown(f"**Días en tránsito:** {int(dias) if pd.notna(dias) else '—'}")
    with d3:
        st.markdown(f"**Forwarder:** {ship['Forwarder']}")
        st.markdown(f"**Origen → Destino:** {ship.get('Puerto Origen','—')} → {ship.get('Puerto Destino','—')}")
        st.markdown(f"**Producto:** {ship.get('Descripcion','—') or '—'}")
        peso = ship.get('Peso KG')
        st.markdown(f"**Peso:** {f'{int(peso):,} KG' if pd.notna(peso) and peso != '' else '—'}")

    obs = ship.get('Observaciones','')
    if obs:
        st.warning(f"📌 {obs}")
else:
    st.info("Sin resultados con los filtros aplicados.")

# ── EXPORTS ──────────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Exportar</div>", unsafe_allow_html=True)
ex1, ex2 = st.columns(2)

with ex1:
    st.download_button(
        "📥 Descargar CSV",
        data=dff.drop(columns=['ETA Vencida','Estado Visual'], errors='ignore').to_csv(index=False).encode('utf-8'),
        file_name=f'comex_tracker_{TODAY.strftime("%Y%m%d")}.csv',
        mime='text/csv'
    )

with ex2:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        dff.drop(columns=['ETA Vencida','Estado Visual'], errors='ignore').to_excel(writer, index=False, sheet_name='Shipments')
    st.download_button(
        "📥 Descargar Excel",
        data=buf.getvalue(),
        file_name=f'comex_tracker_{TODAY.strftime("%Y%m%d")}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
