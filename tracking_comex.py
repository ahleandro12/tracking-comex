import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from io import BytesIO

st.set_page_config(
    page_title="COMEX · Shipment Tracker",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── THEME ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main, .block-container { background-color: #080e1a; padding-top: 1rem; padding-bottom: 1rem; }

/* KPI */
.kpi { background: #0d1627; border: 1px solid #1e2d45; border-radius: 14px; padding: 14px 16px; text-align: center; }
.kpi-label { color: #4a6080; font-size: 0.65rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; margin-bottom: 4px; }
.kpi-value { color: #e2e8f0; font-size: 2.1rem; font-weight: 800; line-height: 1.1; }
.kpi-sub   { color: #2d4260; font-size: 0.65rem; margin-top: 2px; }
.kpi-alert .kpi-value { color: #ef4444; }
.kpi-green .kpi-value { color: #22c55e; }
.kpi-blue  .kpi-value { color: #38bdf8; }

/* Alert card */
.alert-card {
    background: linear-gradient(135deg, #1a0808 0%, #2d0f0f 100%);
    border: 1px solid #7f1d1d;
    border-left: 4px solid #ef4444;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
    display: flex;
    align-items: flex-start;
    gap: 12px;
}
.alert-icon  { font-size: 1.4rem; flex-shrink: 0; }
.alert-body  { flex: 1; }
.alert-title { color: #fca5a5; font-size: 0.8rem; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; }
.alert-bl    { color: #f87171; font-size: 1rem; font-weight: 800; font-family: monospace; }
.alert-detail{ color: #fca5a5; font-size: 0.8rem; margin-top: 2px; }
.alert-days  { color: #fef2f2; font-weight: 800; }
.alert-obs   { color: #f87171; font-size: 0.75rem; margin-top: 4px; font-style: italic; }

/* Section */
.sec { color: #2d4260; font-size: 0.65rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase;
       border-bottom: 1px solid #0d1627; padding-bottom: 5px; margin: 18px 0 12px 0; }

/* Timeline */
.timeline { display: flex; align-items: center; gap: 0; margin: 8px 0; }
.tl-step  { flex: 1; text-align: center; position: relative; }
.tl-step::after { content:''; position:absolute; top:12px; left:50%; width:100%; height:2px; background:#1e2d45; z-index:0; }
.tl-step:last-child::after { display:none; }
.tl-dot   { width:24px; height:24px; border-radius:50%; margin:0 auto 4px; border:2px solid #1e2d45;
            background:#0d1627; position:relative; z-index:1; display:flex; align-items:center; justify-content:center; font-size:.65rem; }
.tl-dot.done   { background:#22c55e; border-color:#22c55e; }
.tl-dot.active { background:#f59e0b; border-color:#f59e0b; box-shadow: 0 0 10px #f59e0b66; }
.tl-dot.alert  { background:#ef4444; border-color:#ef4444; box-shadow: 0 0 10px #ef444466; }
.tl-label { color:#4a6080; font-size:.6rem; font-weight:600; }
.tl-label.active { color:#f59e0b; }
.tl-label.done   { color:#22c55e; }
.tl-label.alert  { color:#ef4444; }

/* Detail panel */
.detail-card { background:#0d1627; border:1px solid #1e2d45; border-radius:12px; padding:16px; margin-top:8px; }
.detail-row  { display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px solid #0d1627; }
.detail-key  { color:#4a6080; font-size:.78rem; font-weight:600; }
.detail-val  { color:#cbd5e1; font-size:.78rem; font-weight:500; text-align:right; }

/* Forwarder badge */
.fwd-badge { display:inline-block; padding:2px 8px; border-radius:6px; font-size:.7rem; font-weight:600;
             background:#0d1f35; color:#38bdf8; border:1px solid #1e3a5f; }

#MainMenu, footer, header { visibility: hidden; }
div[data-testid="stMetric"] { background:#0d1627; border-radius:10px; padding:10px; border:1px solid #1e2d45; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ────────────────────────────────────────────────────────────────
TODAY = datetime.today()

CONTAINER_PREFIXES = {
    'CMAU':'CMA CGM','ONEU':'ONE','KKFU':'K-Line','OOLU':'OOCL',
    'MSCU':'MSC','MAEU':'Maersk','HLCU':'Hapag-Lloyd',
    'NYKU':'NYK Line','YMLU':'Yang Ming','EISU':'Evergreen'
}

STAGES = ['Booking','Loaded','Departed','In Transit','Arrived','Liberado','Delivered']

STATUS_COLORS = {
    'Loaded':'#818cf8','Departed':'#c084fc','In Transit':'#fb923c',
    'Arrived':'#38bdf8','Liberado':'#06b6d4','Delivered':'#4ade80',
    'Pendiente':'#475569','ETA Vencida':'#ef4444'
}

FORWARDER_COLORS = ['#38bdf8','#818cf8','#4ade80','#fb923c','#c084fc']

# ── SESSION STATE ────────────────────────────────────────────────────────────
if 'resolved' not in st.session_state:
    st.session_state.resolved = set()
if 'contacted' not in st.session_state:
    st.session_state.contacted = set()
if 'estado_overrides' not in st.session_state:
    st.session_state.estado_overrides = {}
if 'notas' not in st.session_state:
    st.session_state.notas = {}

# ── DEMO DATA ────────────────────────────────────────────────────────────────
def demo_data():
    rows = [
        ("MAEU250100123","Craft ARG",   "MAERSK EDINBURGH","MAEU4512398","Delivered", TODAY-timedelta(55),TODAY-timedelta(20),"Shanghai",   "Buenos Aires","Reactivos de laboratorio",   2400,""),
        ("MSCU250200456","Craft ARG",   "MSC ANNA",        "MSCU7831045","Delivered", TODAY-timedelta(48),TODAY-timedelta(15),"Hong Kong",  "Buenos Aires","Equipos de diagnóstico",     1800,""),
        ("HLCU250300789","Ultramar",    "EVER GIVEN II",   "HLCU3321098","Arrived",   TODAY-timedelta(40),TODAY-timedelta(3), "Ningbo",     "Buenos Aires","Insumos biotecnológicos",    3100,"Liberación pendiente DUA"),
        ("ONEU250400012","Ultramar",    "NYK DIANA",       "ONEU5828437","Arrived",   TODAY-timedelta(38),TODAY-timedelta(5), "Busan",      "Buenos Aires","Cultivos celulares",         900, "Inspección SENASA en curso"),
        ("CMAU250500345","Craft ARG",   "CMA CGM MARCO POLO","CMAU1234567","In Transit",TODAY-timedelta(22),TODAY+timedelta(8),"Rotterdam", "Buenos Aires","Anticuerpos monoclonales",   650, ""),
        ("YMLU250600678","Panalpina",   "YANG MING UNITY", "YMLU9087654","In Transit",TODAY-timedelta(18),TODAY+timedelta(12),"Hamburg",   "Buenos Aires","Medios de cultivo",          2200,""),
        ("OOLU250700901","Panalpina",   "OOCL BERLIN",     "OOLU4456789","In Transit",TODAY-timedelta(15),TODAY+timedelta(4), "Felixstowe","Buenos Aires","Kits ELISA",                 750, "ETA ajustada por clima"),
        ("EISU250800234","Ultramar",    "EVER GLORY",      "EISU2234567","In Transit",TODAY-timedelta(30),TODAY-timedelta(2), "Qingdao",   "Buenos Aires","Enzimas de restricción",     400, "ETA vencida - confirmar arribo"),
        ("MSCU250900567","Craft ARG",   "MSC OSCAR",       "MSCU5543210","In Transit",TODAY-timedelta(35),TODAY-timedelta(8), "Shanghai",  "Buenos Aires","Tubos de centrífuga",        1200,"Sin novedad del forwarder"),
        ("MAEU251000890","DB Schenker", "MAERSK STOCKHOLM","MAEU8876543","Departed",  TODAY-timedelta(8), TODAY+timedelta(22),"Los Angeles","Buenos Aires","Reactivos PCR",             550, ""),
        ("HLCU251100123","DB Schenker", "HAPAG INNOVATION","HLCU6654321","Departed",  TODAY-timedelta(5), TODAY+timedelta(25),"New York",  "Buenos Aires","Plásticos de laboratorio",   3400,""),
        ("CMAU251200456","Panalpina",   "CMA CGM JULES VERNE","CMAU9987654","Loaded",  TODAY-timedelta(2), TODAY+timedelta(30),"Shanghai", "Buenos Aires","Filtros HEPA",               800, ""),
        ("ONEU251300789","Craft ARG",   "ONE COSMOS",      "ONEU1123456","Loaded",    TODAY-timedelta(1), TODAY+timedelta(32),"Hong Kong", "Buenos Aires","Pipetas y consumibles",      1600,""),
        ("YMLU251400012","Ultramar",    "YANG MING WITNESS","YMLU3345678","Pendiente", None,               TODAY+timedelta(45),"Ningbo",   "Buenos Aires","Columnas de cromatografía",  320, "Booking confirmado"),
        ("OOLU251500345","DB Schenker", "OOCL HONG KONG",  "OOLU7789012","Pendiente", None,               TODAY+timedelta(50),"Busan",    "Buenos Aires","Viales estériles",            2800,"En proceso de OC"),
    ]
    cols = ["BL","Forwarder","Buque","Contenedor","Estado","ETD","ETA",
            "Puerto Origen","Puerto Destino","Descripcion","Peso KG","Observaciones"]
    df = pd.DataFrame(rows, columns=cols)
    df["Carrier"] = df["Contenedor"].apply(lambda x: CONTAINER_PREFIXES.get(str(x)[:4].upper(),""))
    return df

# ── HELPERS ──────────────────────────────────────────────────────────────────
def dias_transito(etd):
    try:
        d = pd.to_datetime(etd)
        return (TODAY - d).days if pd.notna(d) else None
    except: return None

def is_eta_vencida(row):
    if row["Estado"] in ["Delivered","Pendiente","Liberado"]: return False
    try:
        eta = pd.to_datetime(row["ETA"])
        return pd.notna(eta) and eta.date() < TODAY.date()
    except: return False

def stage_status(estado, eta_vencida):
    """Returns list of (stage, status) where status in done/active/alert/pending"""
    idx = STAGES.index(estado) if estado in STAGES else -1
    result = []
    for i, s in enumerate(STAGES):
        if i < idx: result.append('done')
        elif i == idx:
            result.append('alert' if eta_vencida else 'active')
        else: result.append('pending')
    return result

def fmt_date(d):
    try:
        dt = pd.to_datetime(d)
        return dt.strftime('%d/%m/%Y') if pd.notna(dt) else '—'
    except: return '—'

# ── LOAD DATA ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚢 COMEX Tracker")
    st.markdown("<div class='sec'>Datos</div>", unsafe_allow_html=True)
    uploaded = st.file_uploader("Excel o CSV", type=['xlsx','xls','csv'])
    use_demo = st.toggle("Usar datos demo", value=uploaded is None)

if uploaded and not use_demo:
    try:
        ext = uploaded.name.split('.')[-1].lower()
        df_raw = pd.read_csv(uploaded) if ext=='csv' else pd.read_excel(uploaded)
        df_raw.columns = df_raw.columns.str.strip()
        if 'Carrier' not in df_raw.columns:
            df_raw['Carrier'] = df_raw.get('Contenedor', pd.Series()).apply(
                lambda x: CONTAINER_PREFIXES.get(str(x)[:4].upper(),''))
        for c,v in [('Estado','Pendiente'),('ETD',None),('ETA',None),
                    ('Puerto Origen',''),('Puerto Destino',''),
                    ('Peso KG',None),('Descripcion',''),('Observaciones',''),
                    ('Contenedor',''),('Carrier','')]:
            if c not in df_raw.columns: df_raw[c] = v
        st.sidebar.success(f"✅ {uploaded.name}")
    except Exception as e:
        st.sidebar.error(f"Error: {e}")
        df_raw = demo_data()
else:
    df_raw = demo_data()
    if use_demo: st.sidebar.info("📊 Datos demo activos")

# Apply state overrides
df = df_raw.copy()
for bl, estado in st.session_state.estado_overrides.items():
    df.loc[df['BL']==bl, 'Estado'] = estado

df["Días en Tránsito"] = df["ETD"].apply(dias_transito)
df["ETA Vencida"] = df.apply(is_eta_vencida, axis=1)
df["Estado Visual"] = df.apply(lambda r: "ETA Vencida" if r["ETA Vencida"] else r["Estado"], axis=1)

# ── SIDEBAR FILTERS ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div class='sec'>Filtros</div>", unsafe_allow_html=True)
    sel_estado = st.selectbox("Estado", ['Todos'] + STAGES + ['ETA Vencida'])
    sel_fwd = st.selectbox("Forwarder", ['Todos'] + sorted(df['Forwarder'].dropna().unique().tolist()))
    sel_carrier = st.selectbox("Carrier", ['Todos'] + sorted([c for c in df['Carrier'].dropna().unique() if c]))
    search = st.text_input("🔍 BL / Buque / Contenedor")

    st.markdown("<div class='sec'>Exportar</div>", unsafe_allow_html=True)
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as w:
        df.drop(columns=['ETA Vencida','Estado Visual'], errors='ignore').to_excel(w, index=False)
    st.download_button("📥 Excel completo", buf.getvalue(),
        f"comex_{TODAY.strftime('%Y%m%d')}.xlsx",
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# Apply filters
dff = df.copy()
if sel_estado != 'Todos':
    if sel_estado == 'ETA Vencida': dff = dff[dff['ETA Vencida']==True]
    else: dff = dff[dff['Estado']==sel_estado]
if sel_fwd != 'Todos': dff = dff[dff['Forwarder']==sel_fwd]
if sel_carrier != 'Todos': dff = dff[dff['Carrier']==sel_carrier]
if search:
    m = (dff['BL'].astype(str).str.contains(search,case=False,na=False) |
         dff['Buque'].astype(str).str.contains(search,case=False,na=False) |
         dff['Contenedor'].astype(str).str.contains(search,case=False,na=False))
    dff = dff[m]

# ── HEADER ───────────────────────────────────────────────────────────────────
c1, c2 = st.columns([5,1])
with c1: st.markdown("## 🚢 COMEX · Shipment Tracker")
with c2: st.markdown(f"<div style='text-align:right;color:#2d4260;padding-top:14px;font-size:.8rem'>{TODAY.strftime('%d/%m/%Y')}</div>", unsafe_allow_html=True)

# ── ALERTS PANEL ─────────────────────────────────────────────────────────────
alertas = df[(df["ETA Vencida"]==True) & (~df["BL"].isin(st.session_state.resolved))]

if len(alertas) > 0:
    st.markdown(f"<div class='sec'>⚠️ Alertas activas — {len(alertas)} embarque{'s' if len(alertas)!=1 else ''} con ETA vencida</div>", unsafe_allow_html=True)

    for _, row in alertas.iterrows():
        bl = row['BL']
        eta_dt = pd.to_datetime(row['ETA'], errors='coerce')
        eta_str = eta_dt.strftime('%d/%m') if pd.notna(eta_dt) else '?'
        dias_over = (TODAY - eta_dt).days if pd.notna(eta_dt) else '?'
        contacted = bl in st.session_state.contacted

        with st.container():
            st.markdown(f"""
            <div class="alert-card">
                <div class="alert-icon">🚨</div>
                <div class="alert-body">
                    <div class="alert-title">ETA Vencida · {row['Forwarder']} · {row.get('Carrier','')}</div>
                    <div class="alert-bl">{bl}</div>
                    <div class="alert-detail">
                        {row.get('Descripcion','') or row['Buque']} · 
                        {row.get('Puerto Origen','?')} → {row.get('Puerto Destino','?')} · 
                        ETA: {eta_str} · <span class="alert-days">{dias_over} días de demora</span>
                        {"· ✅ Forwarder contactado" if contacted else ""}
                    </div>
                    {f'<div class="alert-obs">⚠ {row["Observaciones"]}</div>' if row.get("Observaciones") else ""}
                </div>
            </div>""", unsafe_allow_html=True)

            ac1, ac2, ac3, ac4 = st.columns([2,2,2,1])

            with ac1:
                if st.button(f"✅ Confirmar arribo", key=f"arr_{bl}"):
                    st.session_state.estado_overrides[bl] = 'Arrived'
                    st.session_state.resolved.add(bl)
                    st.rerun()

            with ac2:
                label_contact = "📞 Forwarder contactado" if contacted else "📞 Marcar contactado"
                if st.button(label_contact, key=f"cnt_{bl}"):
                    st.session_state.contacted.add(bl)
                    st.rerun()

            with ac3:
                if st.button(f"🔕 Desestimar alerta", key=f"dis_{bl}"):
                    st.session_state.resolved.add(bl)
                    st.rerun()

            with ac4:
                nota_key = f"nota_{bl}"
                nota = st.text_input("Nota rápida", key=nota_key,
                    value=st.session_state.notas.get(bl,''),
                    placeholder="Agregar nota...", label_visibility="collapsed")
                if nota: st.session_state.notas[bl] = nota

        st.markdown("<hr style='border:none;border-top:1px solid #0d1627;margin:4px 0'>", unsafe_allow_html=True)

# ── KPIs ─────────────────────────────────────────────────────────────────────
total = len(df)
en_transito = len(df[df['Estado'].isin(['In Transit','Departed'])])
arribados = len(df[df['Estado']=='Arrived'])
entregados = len(df[df['Estado']=='Delivered'])
alertas_n = len(alertas)
avg_dias = df[df['Días en Tránsito'].notna() & df['Estado'].isin(['In Transit','Departed'])]['Días en Tránsito'].mean()

def kpi(label, val, sub="", cls=""):
    return f'<div class="kpi {cls}"><div class="kpi-label">{label}</div><div class="kpi-value">{val}</div><div class="kpi-sub">{sub}</div></div>'

k = st.columns(6)
k[0].markdown(kpi("Total Embarques", total, "en seguimiento"), unsafe_allow_html=True)
k[1].markdown(kpi("En Tránsito", en_transito, "Departed + In Transit", "kpi-blue"), unsafe_allow_html=True)
k[2].markdown(kpi("Arribados", arribados, "pendientes de liberación"), unsafe_allow_html=True)
k[3].markdown(kpi("Entregados", entregados, "ciclo completo", "kpi-green"), unsafe_allow_html=True)
k[4].markdown(kpi("⚠️ Alertas ETA", alertas_n, "ETA vencida activa", "kpi-alert" if alertas_n>0 else ""), unsafe_allow_html=True)
k[5].markdown(kpi("Días Prom. Tránsito", f"{avg_dias:.0f}" if pd.notna(avg_dias) else "—", "embarques activos"), unsafe_allow_html=True)

# ── CHARTS ───────────────────────────────────────────────────────────────────
st.markdown("<div class='sec'>Visión general</div>", unsafe_allow_html=True)
ch1, ch2, ch3 = st.columns([2,2,1])

with ch1:
    st.markdown("**Estado de embarques**")
    counts = df.groupby('Estado Visual').size().reset_index(name='n')
    order = {s:i for i,s in enumerate(STAGES+['ETA Vencida','Pendiente'])}
    counts['ord'] = counts['Estado Visual'].map(lambda x: order.get(x,99))
    counts = counts.sort_values('ord')
    fig = px.bar(counts, x='Estado Visual', y='n',
        color='Estado Visual', color_discrete_map=STATUS_COLORS,
        text='n', height=240)
    fig.update_traces(textposition='outside', textfont_size=12, marker_line_width=0)
    fig.update_layout(plot_bgcolor='#080e1a', paper_bgcolor='#080e1a',
        font_color='#4a6080', showlegend=False,
        margin=dict(l=0,r=0,t=10,b=0),
        xaxis=dict(showgrid=False, color='#2d4260', tickfont_size=11),
        yaxis=dict(showgrid=True, gridcolor='#0d1627', color='#2d4260'))
    st.plotly_chart(fig, use_container_width=True)

with ch2:
    st.markdown("**Distribución por forwarder**")
    fwd_df = df.groupby(['Forwarder','Estado Visual']).size().reset_index(name='n')
    fig2 = px.bar(fwd_df, x='n', y='Forwarder', color='Estado Visual',
        color_discrete_map=STATUS_COLORS, orientation='h',
        text='n', height=240)
    fig2.update_traces(textposition='inside', textfont_size=10, marker_line_width=0)
    fig2.update_layout(plot_bgcolor='#080e1a', paper_bgcolor='#080e1a',
        font_color='#4a6080', showlegend=False,
        margin=dict(l=0,r=20,t=10,b=0),
        xaxis=dict(showgrid=True, gridcolor='#0d1627', color='#2d4260'),
        yaxis=dict(showgrid=False, color='#2d4260'))
    st.plotly_chart(fig2, use_container_width=True)

with ch3:
    st.markdown("**Peso total (KG)**")
    peso_df = df[df['Peso KG'].notna()].groupby('Estado')['Peso KG'].sum().reset_index()
    peso_df = peso_df[peso_df['Estado'].isin(['In Transit','Arrived','Delivered'])]
    fig3 = px.pie(peso_df, values='Peso KG', names='Estado',
        color='Estado', color_discrete_map=STATUS_COLORS,
        hole=0.6, height=240)
    fig3.update_traces(textinfo='none')
    total_kg = int(df['Peso KG'].sum()) if df['Peso KG'].notna().any() else 0
    fig3.add_annotation(text=f"{total_kg:,}<br>KG", x=0.5, y=0.5,
        font=dict(size=14, color='#e2e8f0', family='Inter'), showarrow=False)
    fig3.update_layout(plot_bgcolor='#080e1a', paper_bgcolor='#080e1a',
        font_color='#4a6080', showlegend=True,
        legend=dict(font=dict(size=10, color='#4a6080'), bgcolor='#080e1a'),
        margin=dict(l=0,r=0,t=10,b=0))
    st.plotly_chart(fig3, use_container_width=True)

# ── TABLE ────────────────────────────────────────────────────────────────────
st.markdown(f"<div class='sec'>Embarques · {len(dff)} resultado{'s' if len(dff)!=1 else ''}</div>", unsafe_allow_html=True)

show_cols = ['BL','Forwarder','Carrier','Buque','Estado','ETD','ETA',
             'Días en Tránsito','Puerto Origen','Puerto Destino','Descripcion','Peso KG']
df_show = dff[[c for c in show_cols if c in dff.columns]].copy()
for dc in ['ETD','ETA']:
    if dc in df_show.columns:
        df_show[dc] = pd.to_datetime(df_show[dc], errors='coerce').dt.strftime('%d/%m/%Y').fillna('—')

def color_estado(val):
    m = {'Loaded':'background-color:#1e1b4b;color:#a5b4fc',
         'Departed':'background-color:#2e1065;color:#c4b5fd',
         'In Transit':'background-color:#431407;color:#fed7aa',
         'Arrived':'background-color:#0c2340;color:#7dd3fc',
         'Liberado':'background-color:#082f49;color:#67e8f9',
         'Delivered':'background-color:#052e16;color:#86efac',
         'Pendiente':'background-color:#0f172a;color:#475569'}
    return m.get(val,'')

def color_dias(val):
    try:
        v = int(val)
        if v > 40: return 'color:#ef4444;font-weight:700'
        if v > 25: return 'color:#fb923c'
        return 'color:#4ade80'
    except: return ''

styled = df_show.style\
    .map(color_estado, subset=['Estado'])\
    .map(color_dias, subset=['Días en Tránsito'] if 'Días en Tránsito' in df_show.columns else [])
st.dataframe(styled, height=360, use_container_width=True)

# ── DETAIL PANEL ─────────────────────────────────────────────────────────────
st.markdown("<div class='sec'>Detalle y gestión de embarque</div>", unsafe_allow_html=True)

if len(dff) > 0:
    sel_bl = st.selectbox("Seleccionar BL", dff['BL'].tolist(), label_visibility="collapsed")
    ship = df[df['BL']==sel_bl].iloc[0].copy()

    # Timeline
    eta_vencida = bool(ship['ETA Vencida'])
    current_estado = ship['Estado']
    stage_stats = stage_status(current_estado, eta_vencida)

    tl_html = '<div class="timeline">'
    icons = {'done':'✓','active':'●','alert':'!','pending':'○'}
    for stage, stat in zip(STAGES, stage_stats):
        tl_html += f'''
        <div class="tl-step">
            <div class="tl-dot {stat}">{icons[stat]}</div>
            <div class="tl-label {stat}">{stage}</div>
        </div>'''
    tl_html += '</div>'
    st.markdown(tl_html, unsafe_allow_html=True)

    # Info + edición
    p1, p2, p3 = st.columns([3,3,2])

    with p1:
        st.markdown(f"""
        <div class="detail-card">
            <div class="detail-row"><span class="detail-key">BL</span><span class="detail-val" style="font-family:monospace">{ship['BL']}</span></div>
            <div class="detail-row"><span class="detail-key">Buque</span><span class="detail-val">{ship['Buque']}</span></div>
            <div class="detail-row"><span class="detail-key">Contenedor</span><span class="detail-val" style="font-family:monospace">{ship.get('Contenedor','—') or '—'}</span></div>
            <div class="detail-row"><span class="detail-key">Carrier</span><span class="detail-val">{ship.get('Carrier','—') or '—'}</span></div>
            <div class="detail-row"><span class="detail-key">Forwarder</span><span class="detail-val">{ship['Forwarder']}</span></div>
        </div>""", unsafe_allow_html=True)

    with p2:
        etd_s = fmt_date(ship['ETD'])
        eta_s = fmt_date(ship['ETA'])
        dias = ship.get('Días en Tránsito')
        dias_str = f"{int(dias)} días" if pd.notna(dias) else '—'
        peso = ship.get('Peso KG')
        peso_str = f"{int(peso):,} KG" if pd.notna(peso) and peso!='' else '—'
        alerta_str = ' · <span style="color:#ef4444;font-weight:700">⚠ ETA VENCIDA</span>' if eta_vencida else ''
        st.markdown(f"""
        <div class="detail-card">
            <div class="detail-row"><span class="detail-key">ETD</span><span class="detail-val">{etd_s}</span></div>
            <div class="detail-row"><span class="detail-key">ETA</span><span class="detail-val">{eta_s}{alerta_str}</span></div>
            <div class="detail-row"><span class="detail-key">Días en tránsito</span><span class="detail-val">{dias_str}</span></div>
            <div class="detail-row"><span class="detail-key">Origen → Destino</span><span class="detail-val">{ship.get('Puerto Origen','?')} → {ship.get('Puerto Destino','?')}</span></div>
            <div class="detail-row"><span class="detail-key">Peso</span><span class="detail-val">{peso_str}</span></div>
        </div>""", unsafe_allow_html=True)

    with p3:
        st.markdown("**Actualizar estado**")
        nuevo_estado = st.selectbox("Estado", STAGES,
            index=STAGES.index(current_estado) if current_estado in STAGES else 0,
            key=f"edit_estado_{sel_bl}", label_visibility="collapsed")
        if st.button("💾 Guardar estado", key=f"save_{sel_bl}", use_container_width=True):
            st.session_state.estado_overrides[sel_bl] = nuevo_estado
            if sel_bl in st.session_state.resolved and nuevo_estado not in ['In Transit','Departed']:
                st.session_state.resolved.discard(sel_bl)
            st.rerun()

        nota_actual = st.session_state.notas.get(sel_bl, ship.get('Observaciones','') or '')
        nueva_nota = st.text_area("Observaciones", value=nota_actual, height=80,
            key=f"obs_{sel_bl}", label_visibility="collapsed",
            placeholder="Observaciones del embarque...")
        if nueva_nota != nota_actual:
            st.session_state.notas[sel_bl] = nueva_nota

    obs_final = st.session_state.notas.get(sel_bl, ship.get('Observaciones',''))
    if obs_final:
        st.warning(f"📌 {obs_final}")
else:
    st.info("Sin resultados con los filtros aplicados.")
