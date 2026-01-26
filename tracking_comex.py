import streamlit as st
import pandas as pd
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Tracking COMEX", page_icon="🚢", layout="wide")

# Título
st.title("🚢 Sistema de Tracking COMEX")
st.markdown("**Gestión y seguimiento de embarques en tiempo real**")

# Mapeo de prefijos de contenedor a carriers
CONTAINER_PREFIXES = {
    'CMAU': 'CMA CGM',
    'ONEU': 'ONE',
    'KKFU': 'K-Line',
    'OOLU': 'OOCL',
    'MSCU': 'MSC',
    'MAEU': 'Maersk',
    'HLCU': 'Hapag-Lloyd',
    'NYKU': 'NYK Line',
    'YMLU': 'Yang Ming',
    'EISU': 'Evergreen'
}

def detect_carrier(container):
    """Detecta el carrier desde el prefijo del contenedor"""
    if pd.isna(container) or not container:
        return ''
    prefix = str(container)[:4].upper()
    return CONTAINER_PREFIXES.get(prefix, '')

# Sidebar para cargar archivo
with st.sidebar:
    st.header("📁 Cargar Datos")
    uploaded_file = st.file_uploader(
        "Subir archivo Excel o CSV", 
        type=['xlsx', 'xls', 'csv'],
        help="Podés cargar archivos .xlsx, .xls o .csv"
    )
    
    st.markdown("---")
    st.markdown("### 📋 Formato del archivo")
    st.markdown("""
    **Columnas requeridas:**
    - `Forwarder`
    - `Buque`
    - `BL`
    
    **Columnas opcionales:**
    - `Contenedor`
    - `Carrier`
    - `Estado` (Loaded, In Transit, Arrived, Delivered, Pendiente)
    - `ETD` (Fecha de salida)
    - `ETA` (Fecha estimada de llegada)
    - `Puerto Origen`
    - `Puerto Destino`
    - `Peso KG`
    - `Descripcion`
    - `Observaciones`
    """)
    
    st.markdown("---")
    st.info("💡 **Tip:** Trabajá directo en Excel y cargá el archivo aquí. ¡No hace falta exportar a CSV!")

# Procesar archivo
if uploaded_file is not None:
    try:
        # Detectar tipo de archivo y leer
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension == 'csv':
            df = pd.read_csv(uploaded_file)
            st.success(f"✅ Archivo CSV cargado: **{uploaded_file.name}**")
        else:  # xlsx o xls
            df = pd.read_excel(uploaded_file)
            st.success(f"✅ Archivo Excel cargado: **{uploaded_file.name}**")
        
        # Normalizar nombres de columnas
        df.columns = df.columns.str.strip()
        
        # Detectar carrier automáticamente si no existe
        if 'Carrier' not in df.columns or df['Carrier'].isna().all():
            if 'Contenedor' in df.columns:
                df['Carrier'] = df['Contenedor'].apply(detect_carrier)
            else:
                df['Carrier'] = ''
        
        # Asegurar que existen las columnas básicas
        required_cols = ['Forwarder', 'Buque', 'BL']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            st.error(f"❌ Faltan columnas requeridas: {', '.join(missing_cols)}")
            st.info("💡 Asegurate de que tu Excel tenga columnas con los nombres: Forwarder, Buque, BL")
        else:
            # Rellenar columnas opcionales si no existen
            optional_cols = {
                'Contenedor': '',
                'Estado': 'Pendiente',
                'ETD': '',
                'ETA': '',
                'Puerto Origen': '',
                'Puerto Destino': '',
                'Peso KG': '',
                'Descripcion': '',
                'Observaciones': ''
            }
            
            for col, default_val in optional_cols.items():
                if col not in df.columns:
                    df[col] = default_val
            
            # Filtros
            st.markdown("---")
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                search_term = st.text_input("🔍 Buscar", placeholder="Forwarder, BL, Contenedor...")
            
            with col2:
                estados_unicos = ['Todos'] + sorted(df['Estado'].dropna().unique().tolist())
                estado_filter = st.selectbox("📊 Filtrar por Estado", estados_unicos)
            
            with col3:
                carriers_unicos = ['Todos'] + sorted([c for c in df['Carrier'].dropna().unique().tolist() if c])
                carrier_filter = st.selectbox("🚢 Filtrar por Carrier", carriers_unicos)
            
            # Aplicar filtros
            df_filtered = df.copy()
            
            if search_term:
                mask = (
                    df_filtered['Forwarder'].astype(str).str.contains(search_term, case=False, na=False) |
                    df_filtered['BL'].astype(str).str.contains(search_term, case=False, na=False) |
                    df_filtered['Contenedor'].astype(str).str.contains(search_term, case=False, na=False) |
                    df_filtered['Buque'].astype(str).str.contains(search_term, case=False, na=False)
                )
                df_filtered = df_filtered[mask]
            
            if estado_filter != 'Todos':
                df_filtered = df_filtered[df_filtered['Estado'] == estado_filter]
            
            if carrier_filter != 'Todos':
                df_filtered = df_filtered[df_filtered['Carrier'] == carrier_filter]
            
            # Métricas
            st.markdown("---")
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("📦 Total Embarques", len(df))
            
            with col2:
                loaded = len(df[df['Estado'] == 'Loaded'])
                st.metric("📥 Cargados", loaded)
            
            with col3:
                transit = len(df[df['Estado'].isin(['In Transit', 'Departed'])])
                st.metric("🚢 En Tránsito", transit)
            
            with col4:
                arrived = len(df[df['Estado'] == 'Arrived'])
                st.metric("🎯 Arribados", arrived)
            
            with col5:
                delivered = len(df[df['Estado'] == 'Delivered'])
                st.metric("✅ Entregados", delivered)
            
            st.markdown("---")
            
            # Mostrar tabla
            st.subheader(f"📋 Embarques ({len(df_filtered)} resultados)")
            
            if len(df_filtered) > 0:
                # Configurar colores para estados
                def highlight_status(val):
                    colors = {
                        'Loaded': 'background-color: #667eea; color: white',
                        'Departed': 'background-color: #f093fb; color: white',
                        'In Transit': 'background-color: #ffa726; color: white',
                        'Arrived': 'background-color: #4facfe; color: white',
                        'Delivered': 'background-color: #43e97b; color: white',
                        'Pendiente': 'background-color: #999; color: white'
                    }
                    return colors.get(val, '')
                
                # Seleccionar columnas a mostrar
                display_cols = ['Forwarder', 'Buque', 'BL', 'Contenedor', 'Carrier', 
                               'Estado', 'ETD', 'ETA', 'Puerto Origen', 'Puerto Destino']
                
                df_display = df_filtered[display_cols].copy()
                
                # Aplicar estilo a la columna Estado
                styled_df = df_display.style.applymap(
                    highlight_status, 
                    subset=['Estado']
                )
                
                st.dataframe(styled_df, height=400)
                
                # Botones de descarga
                col1, col2 = st.columns(2)
                
                with col1:
                    # Descargar como Excel
                    output = pd.ExcelWriter('temp.xlsx', engine='openpyxl')
                    df_filtered.to_excel(output, index=False, sheet_name='Tracking')
                    output.close()
                    
                    with open('temp.xlsx', 'rb') as f:
                        st.download_button(
                            label="📥 Descargar Excel",
                            data=f.read(),
                            file_name=f'tracking_comex_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )
                
                with col2:
                    # Descargar como CSV
                    st.download_button(
                        label="📥 Descargar CSV",
                        data=df_filtered.to_csv(index=False).encode('utf-8'),
                        file_name=f'tracking_comex_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
                        mime='text/csv'
                    )
                
                # Detalle de embarque seleccionado
                st.markdown("---")
                st.subheader("🔍 Ver Detalle de Embarque")
                
                bl_options = df_filtered['BL'].tolist()
                selected_bl = st.selectbox("Seleccionar BL", bl_options)
                
                if selected_bl:
                    shipment = df_filtered[df_filtered['BL'] == selected_bl].iloc[0]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Forwarder:** {shipment['Forwarder']}")
                        st.markdown(f"**Buque:** {shipment['Buque']}")
                        st.markdown(f"**BL:** {shipment['BL']}")
                        st.markdown(f"**Contenedor:** {shipment['Contenedor'] or 'N/A'}")
                        st.markdown(f"**Carrier:** {shipment['Carrier'] or 'N/A'}")
                    
                    with col2:
                        st.markdown(f"**Estado:** {shipment['Estado']}")
                        st.markdown(f"**ETD:** {shipment['ETD'] or 'N/A'}")
                        st.markdown(f"**ETA:** {shipment['ETA'] or 'N/A'}")
                        st.markdown(f"**Puerto Origen:** {shipment['Puerto Origen'] or 'N/A'}")
                        st.markdown(f"**Puerto Destino:** {shipment['Puerto Destino'] or 'N/A'}")
                    
                    if shipment['Peso KG']:
                        st.markdown(f"**⚖️ Peso:** {shipment['Peso KG']} KG")
                    
                    if shipment['Descripcion']:
                        st.markdown(f"**📝 Descripción:** {shipment['Descripcion']}")
                    
                    if shipment['Observaciones']:
                        st.markdown("---")
                        st.markdown(f"**📌 Observaciones:** {shipment['Observaciones']}")
            else:
                st.info("ℹ️ No se encontraron embarques con los filtros aplicados")
                
    except Exception as e:
        st.error(f"❌ Error al procesar el archivo: {str(e)}")
        st.info("💡 Asegurate de que el archivo Excel esté correctamente formateado y no tenga celdas fusionadas en los encabezados")

else:
    # Mensaje cuando no hay archivo cargado
    st.info("👈 Subí un archivo Excel o CSV desde el panel lateral para comenzar")
    
    # Mostrar ejemplo
    st.markdown("---")
    st.subheader("📄 Ejemplo de datos")
    st.markdown("Tu Excel debería verse algo así:")
    
    example_data = {
        'Forwarder': ['Craft ARG', 'Craft ARG', 'Craft ARG'],
        'Buque': ['NYK DIANA', 'V2537 E', 'MSC ANNA'],
        'BL': ['GSUBEZEI2500016', 'GXLI25090032', 'HF15BU251506'],
        'Contenedor': ['ONEU5828437', 'CMAU1234567', 'MSCU9876543'],
        'Estado': ['In Transit', 'Arrived', 'Loaded'],
        'ETD': ['2025-01-15', '2025-01-10', '2025-01-28'],
        'ETA': ['2025-02-10', '2025-01-26', '2025-02-20'],
        'Puerto Origen': ['Shanghai', 'Hong Kong', 'Ningbo'],
        'Puerto Destino': ['Buenos Aires', 'Buenos Aires', 'Buenos Aires']
    }
    
    st.dataframe(pd.DataFrame(example_data))
    
    # Descargar ejemplo como CSV
    st.download_button(
        label="📥 Descargar CSV de ejemplo",
        data=pd.DataFrame(example_data).to_csv(index=False).encode('utf-8'),
        file_name='ejemplo_tracking.csv',
        mime='text/csv'
    )
