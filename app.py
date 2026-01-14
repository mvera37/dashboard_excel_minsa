import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import plotly.express as px
import os
import json
import warnings
import datetime

# --- CONFIGURACIÓN ---
warnings.filterwarnings("ignore")
st.set_page_config(page_title="TeleMammo BI v11.1", page_icon="💙", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    .stApp { background-color: #F8FAFC; font-family: 'Inter', sans-serif; }
    
    /* 1. NAVBAR */
    .navbar { 
        display: flex; justify-content: space-between; align-items: center; 
        padding: 1rem 2rem; background: white; border-radius: 12px; 
        margin-bottom: 2rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); 
        border: 1px solid #E2E8F0; 
    }
    
    /* 2. HERO SECTION */
    .hero-badge {
        background-color: #DBEAFE; color: #1E40AF; padding: 6px 16px; 
        border-radius: 20px; font-weight: 700; font-size: 0.75rem; 
        text-transform: uppercase; display: inline-block; margin-bottom: 1rem;
        letter-spacing: 0.05em;
    }
    .hero-title {
        font-size: 3.5rem; font-weight: 800; color: #0F172A; line-height: 1.1; margin-bottom: 1.5rem;
    }
    .hero-desc {
        font-size: 1.1rem; color: #475569; line-height: 1.6; margin-bottom: 2rem; max-width: 95%;
    }
    .hero-stats-container {
        display: flex; flex-wrap: wrap; gap: 20px; align-items: center;
        margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid #E2E8F0;
    }
    .stat-item { display: flex; align-items: center; gap: 8px; color: #64748B; font-weight: 600; font-size: 0.95rem; }
    .update-badge {
        background-color: #EFF6FF; color: #2563EB; padding: 4px 12px; border-radius: 6px; 
        font-size: 0.85rem; font-weight: 700; border: 1px solid #BFDBFE;
    }

    /* 3. KPI CARDS */
    .kpi-card {
        background-color: white; border-radius: 12px; padding: 20px 24px;
        border: 1px solid #E2E8F0; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        margin-bottom: 16px; height: 100%; display: flex; flex-direction: column; justify-content: center;
    }
    .kpi-val { font-size: 2rem; font-weight: 800; color: #0F172A; line-height: 1.1; margin-bottom: 8px; }
    .kpi-lbl { font-size: 0.7rem; color: #64748B; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
    .kpi-sub { font-size: 0.8rem; font-weight: 500; color: #94A3B8; }

    /* 4. CHART CARDS */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: white; border-radius: 16px !important;
        border: 1px solid #E2E8F0 !important; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        padding: 20px !important; margin-bottom: 20px;
    }
    .chart-title {
        font-size: 0.95rem; font-weight: 700; color: #334155; margin-bottom: 15px;
        display: flex; align-items: center; gap: 8px; text-transform: uppercase; letter-spacing: 0.02em;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONEXIÓN ---
try: db_url = st.secrets["DATABASE_URL"]
except: load_dotenv(); db_url = os.getenv("DATABASE_URL")
if not db_url: st.error("❌ Falta DATABASE_URL"); st.stop()
engine = create_engine(db_url)

# --- ESTADO ---
if "app_state" not in st.session_state: st.session_state["app_state"] = "HOME"
if "selected_dept" not in st.session_state: st.session_state["selected_dept"] = None

# --- CARGA DE DATOS ---
@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_sql("SELECT * FROM vista_master_dashboard", engine)
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
        rename_map = {'es_anormalidad': 'es_anormal', 'pais_nombre': 'nacionalidad', 
                      'etnia_nombre': 'etnia', 'distrito_nombre': 'distrito'}
        df.rename(columns=rename_map, inplace=True)

        if 'fecha_solicitud' in df.columns:
            df['fecha_solicitud'] = pd.to_datetime(df['fecha_solicitud'])
            df['anio_mes'] = df['fecha_solicitud'].dt.strftime('%Y-%m')
            
            dias_map = {0:'Lunes', 1:'Martes', 2:'Miércoles', 3:'Jueves', 4:'Viernes', 5:'Sábado', 6:'Domingo'}
            df['dia_semana'] = df['fecha_solicitud'].dt.dayofweek.map(dias_map)
            
            mes_map = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 
                       7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
            df['mes_num'] = df['fecha_solicitud'].dt.month
            df['nombre_mes'] = df['mes_num'].map(mes_map)

        if 'sexo' in df.columns:
            df['sexo_norm'] = df['sexo'].astype(str).str.upper().apply(lambda x: 'FEMENINO' if x in ['2','FEMENINO','F'] else 'MASCULINO')
        
        if 'birads_raw' in df.columns:
            def map_birads(x):
                x = str(x).replace('.0','').strip()
                if x in ['1']: return '1 - Negativo'; 
                if x in ['2']: return '2 - Benigno'; 
                if x in ['3']: return '3 - Prob. Benigno'; 
                if x in ['4']: return '4 - Sospechoso'; 
                if x in ['5']: return '5 - Alta Sospecha'; 
                return '0 - Incompleto'
            df['birads_categoria'] = df['birads_raw'].apply(map_birads)
        return df
    except: return pd.DataFrame()

@st.cache_data
def load_geo():
    path = "geojson/peru_departamental_simple.geojson"
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f: return json.load(f)
    return None

df_master = load_data()
geojson_peru = load_geo()

# --- HELPERS ---
def style_chart(fig):
    fig.update_layout(
        paper_bgcolor='white', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter", color="#64748B"), 
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#F1F5F9', zeroline=False)
    )
    return fig

def kpi_html(value, title, subtext, color="#64748B"):
    return f"""
    <div class="kpi-card">
        <div class="kpi-val">{value}</div>
        <div class="kpi-lbl">{title}</div>
        <div class="kpi-sub" style="color:{color}">{subtext}</div>
    </div>
    """

def mostrar_kpis_completos(df_input):
    total = len(df_input)
    if total > 0:
        target = df_input[(df_input['sexo_norm']=='FEMENINO') & (df_input['edad'].between(40,69))]
        intensidad = (target['es_atendido'].sum()/len(target))*100 if len(target)>0 else 0
        tasa = (df_input['es_anormal'].sum()/total*100) if 'es_anormal' in df_input.columns else 0
        dias = (df_input['fecha_solicitud'].max()-df_input['fecha_solicitud'].min()).days + 1 if 'fecha_solicitud' in df_input.columns else 1
        prom = total/dias if dias>0 else 0
        atend = (df_input['es_atendido'].sum()/total)*100
        anul = (df_input['es_anulado'].sum()/total)*100
        tiempo = df_input['tiempo_atencion_dias'].mean() if 'tiempo_atencion_dias' in df_input.columns else 0
        dep = df_input['departamento'].nunique() if 'departamento' in df_input.columns else 0
    else: intensidad=tasa=prom=atend=anul=tiempo=dep=0

    # --- CORRECCIÓN DE SINTAXIS AQUÍ ---
    r1 = st.columns(4)
    datos_r1 = [(f"{total:,.0f}", "Solicitudes", "Total"), (f"{intensidad:.1f}%", "Intensidad", "40-69 años"), (f"{tasa:.1f}%", "Anormalidad", "BIRADS 3-5"), (f"{prom:.0f}", "Promedio Diario", "Atenciones")]
    for col, (val, tit, sub) in zip(r1, datos_r1):
        with col:
            st.markdown(kpi_html(val, tit, sub), unsafe_allow_html=True)

    r2 = st.columns(4)
    datos_r2 = [(f"{atend:.1f}%", "% Atendidas", "Efectividad"), (f"{anul:.1f}%", "% Anuladas", "Calidad Operativa"), (f"{tiempo:.1f} d", "Tiempo Promedio", "Desde solicitud"), (f"{dep}", "Deptos Activos", "Cobertura Nacional")]
    for col, (val, tit, sub) in zip(r2, datos_r2):
        with col:
            st.markdown(kpi_html(val, tit, sub), unsafe_allow_html=True)
    
    st.write("")
    # ----------------------------------

# --- CONTROLADOR GLOBAL DE FILTROS ---
def render_sidebar_filters(df_data):
    with st.sidebar:
        st.header("Filtros Globales")
        
        opts_srv = ["TODOS"] + sorted(df_data['tipo_servicio'].unique()) if 'tipo_servicio' in df_data.columns else ["TODOS"]
        sel_srv = st.selectbox("Especialidad", opts_srv, index=opts_srv.index("MAMOGRAFIA") if "MAMOGRAFIA" in opts_srv else 0)
        
        df_f = df_data.copy() if sel_srv == "TODOS" else df_data[df_data['tipo_servicio'] == sel_srv].copy()
        
        if 'anio' in df_f.columns:
            years = sorted(df_f['anio'].unique(), reverse=True)
            sel_year = st.selectbox("Año Fiscal", years)
            df_f = df_f[df_f['anio'] == sel_year]

        if 'nombre_mes' in df_f.columns:
            meses_orden = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
            df_f['nombre_mes'] = pd.Categorical(df_f['nombre_mes'], categories=meses_orden, ordered=True)
            opts_mes = ["Todos"] + list(df_f['nombre_mes'].sort_values().unique())
            sel_mes = st.selectbox("Mes", opts_mes)
            if sel_mes != "Todos": df_f = df_f[df_f['nombre_mes'] == sel_mes]

        st.markdown("---")
        if st.button("🏠 Volver al Inicio"): st.session_state["app_state"] = "HOME"; st.rerun()
        
        return df_f, sel_srv

# --- VISTA 1: HOME ---
def render_home():
    st.markdown("""<div class="navbar"><div style="font-weight:800; font-size:1.4rem; color:#0F172A; display:flex; align-items:center; gap:10px;"><span>💙</span> TeleMammo <small style="color:#64748B; margin-left:8px; font-weight:500;">MINSA BI</small></div></div>""", unsafe_allow_html=True)

    total_home = len(df_master)
    dias_home = df_master['tiempo_atencion_dias'].mean() if 'tiempo_atencion_dias' in df_master.columns else 0
    
    if 'fecha_solicitud' in df_master.columns:
        fecha_max = df_master['fecha_solicitud'].max()
        texto_fecha = fecha_max.strftime("%d/%m/%Y") if pd.notnull(fecha_max) else "Sin Data"
    else: texto_fecha = "N/A"

    c1, c2 = st.columns([1.2, 1], gap="large")
    with c1:
        st.write("") 
        st.markdown('<div class="hero-badge">Dirección de Telemedicina - DITEL</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-title">Transformando el Diagnóstico: <span style="color:#2563EB">Telemamografía</span></div>', unsafe_allow_html=True)
        st.markdown("""<div class="hero-desc">Modernizando la detección temprana del cáncer de mama en Perú con tecnología digital avanzada. Monitoreo en tiempo real de cobertura, tiempos de atención y hallazgos clínicos (BIRADS).</div>""", unsafe_allow_html=True)
        
        if st.button("🚀 Acceder al Dashboard Ejecutivo", type="primary"):
            st.session_state["app_state"] = "DASHBOARD"; st.rerun()

        st.markdown(f"""
        <div class="hero-stats-container">
            <div class="stat-item"><span style="font-size:1.2rem">📄</span> <span><strong>{total_home:,.0f}</strong> Atenciones</span></div>
            <div class="stat-item"><span style="font-size:1.2rem">⚡</span> <span><strong>{dias_home:.1f}</strong> Días prom</span></div>
            <div class="stat-item"><span style="font-size:1.2rem">🛡️</span> Datos Seguros</div>
            <div class="stat-item update-badge">📅 Actualizado al: {texto_fecha}</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown("""<div style="border-radius:20px; overflow:hidden; box-shadow:0 20px 40px -10px rgba(0,0,0,0.15); border:6px solid white;"><img src="https://images.unsplash.com/photo-1551076805-e1869033e561?q=80&w=1000&auto=format&fit=crop" style="width:100%; display:block;"></div>""", unsafe_allow_html=True)

# --- VISTA 2: DASHBOARD GENERAL ---
def render_dashboard(df_filtered, srv_name):
    st.markdown(f"### 📊 Panorama Ejecutivo: {srv_name}")
    mostrar_kpis_completos(df_filtered)

    col_L, col_R = st.columns([1.5, 1])
    with col_L:
        with st.container(border=True):
            st.markdown('<div class="chart-title">🗺️ Mapa Nacional</div>', unsafe_allow_html=True)
            if geojson_peru and 'departamento' in df_filtered.columns and not df_filtered.empty:
                map_data = df_filtered.groupby('departamento').size().reset_index(name='Total')
                fig_map = px.choropleth_mapbox(map_data, geojson=geojson_peru, locations='departamento', featureidkey="properties.NOMBDEP",
                                           color="Total", color_continuous_scale="Blues", mapbox_style="carto-positron",
                                           zoom=3.8, center={"lat": -9.19, "lon": -75.01}, opacity=0.9)
                fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=400)
                evt = st.plotly_chart(fig_map, use_container_width=True, on_select="rerun")
                if evt and evt['selection']['points']:
                    st.session_state["selected_dept"] = evt['selection']['points'][0]['location']
                    st.session_state["app_state"] = "REGIONAL"; st.rerun()
            else: st.warning("Sin datos geográficos.")

        with st.container(border=True):
            st.markdown('<div class="chart-title">📊 Ranking Departamental</div>', unsafe_allow_html=True)
            if 'departamento' in df_filtered.columns:
                rank = df_filtered['departamento'].value_counts().reset_index()
                rank.columns = ['Departamento', 'Atenciones']
                fig_rank = px.bar(rank.head(10), x='Departamento', y='Atenciones', color='Atenciones', color_continuous_scale='Blues', labels={'Departamento': 'Región', 'Atenciones': 'Nro. Solicitudes'})
                st.plotly_chart(style_chart(fig_rank), use_container_width=True)

    with col_R:
        tabs = st.tabs(["📈 Temporal", "👥 Demografía", "🩺 Clínico", "⚙️ Flujo"])
        
        with tabs[0]: 
            with st.container(border=True):
                st.markdown('<div class="chart-title">📅 Evolución Mensual</div>', unsafe_allow_html=True)
                if 'anio_mes' in df_filtered.columns:
                    evo = df_filtered.groupby('anio_mes').size().reset_index(name='Total')
                    st.plotly_chart(style_chart(px.area(evo, x='anio_mes', y='Total', labels={'anio_mes': 'Mes', 'Total': 'Atenciones'})), use_container_width=True)
            with st.container(border=True):
                st.markdown('<div class="chart-title">⏱️ Tiempo Promedio</div>', unsafe_allow_html=True)
                if 'anio_mes' in df_filtered.columns:
                    evo_tm = df_filtered.groupby('anio_mes')['tiempo_atencion_dias'].mean().reset_index()
                    fig_tm = px.line(evo_tm, x='anio_mes', y='tiempo_atencion_dias', markers=True, labels={'anio_mes': 'Mes', 'tiempo_atencion_dias': 'Días Promedio'})
                    fig_tm.update_traces(line_color='#F59E0B')
                    st.plotly_chart(style_chart(fig_tm), use_container_width=True)

        with tabs[1]: 
            with st.container(border=True):
                st.markdown('<div class="chart-title">🎂 Rango de Edades</div>', unsafe_allow_html=True)
                if 'grupo_etario' in df_filtered.columns:
                    age = df_filtered['grupo_etario'].value_counts().reset_index()
                    st.plotly_chart(style_chart(px.bar(age, x='grupo_etario', y='count', color='count', color_continuous_scale='Teal', labels={'grupo_etario': 'Grupo Etario', 'count': 'Pacientes'})), use_container_width=True)
            with st.container(border=True):
                st.markdown('<div class="chart-title">🌎 Origen (Extranjeros)</div>', unsafe_allow_html=True)
                if 'nacionalidad' in df_filtered.columns:
                    nac = df_filtered['nacionalidad'].value_counts().reset_index()
                    nac.columns = ['Pais', 'Cantidad']
                    nac_fil = nac[~nac['Pais'].str.contains('PERU', case=False)] if len(nac)>1 else nac
                    if not nac_fil.empty:
                        st.plotly_chart(style_chart(px.treemap(nac_fil, path=['Pais'], values='Cantidad', color='Cantidad', color_continuous_scale='Mint', labels={'labels': 'País', 'value': 'Total'})), use_container_width=True)
                    else: st.info("Solo Perú.")
            with st.container(border=True):
                st.markdown('<div class="chart-title">🧑‍🤝‍🧑 Etnia</div>', unsafe_allow_html=True)
                if 'etnia' in df_filtered.columns:
                    etn = df_filtered['etnia'].value_counts().head(8).reset_index()
                    etn.columns = ['Etnia', 'Cantidad']
                    st.plotly_chart(style_chart(px.pie(etn, names='Etnia', values='Cantidad', hole=0.6, color_discrete_sequence=px.colors.qualitative.Pastel)), use_container_width=True)

        with tabs[2]: 
            with st.container(border=True):
                st.markdown('<div class="chart-title">🩺 BIRADS</div>', unsafe_allow_html=True)
                if 'birads_categoria' in df_filtered.columns:
                    bi = df_filtered['birads_categoria'].value_counts().reset_index()
                    st.plotly_chart(style_chart(px.bar(bi, x='birads_categoria', y='count', color='birads_categoria', labels={'birads_categoria': 'Categoría', 'count': 'Casos'})), use_container_width=True)

        with tabs[3]: 
            with st.container(border=True):
                st.markdown('<div class="chart-title">⚙️ Estado</div>', unsafe_allow_html=True)
                fl = df_filtered['estado'].value_counts().reset_index()
                st.plotly_chart(style_chart(px.bar(fl, x='count', y='estado', orientation='h', color='estado', labels={'estado': 'Estado', 'count': 'Solicitudes'})), use_container_width=True)

# --- VISTA 3: REGIONAL ---
def render_regional(df_filtered_global):
    dep = st.session_state["selected_dept"]
    col_dep = 'departamento' if 'departamento' in df_master.columns else 'nombdep'
    
    df_r = df_filtered_global[df_filtered_global[col_dep] == dep].copy()
    
    st.button("⬅️ Volver al Nacional", on_click=lambda: st.session_state.update(app_state="DASHBOARD", selected_dept=None))
    st.markdown(f"### Análisis Regional: {dep}")
    
    mostrar_kpis_completos(df_r)
    
    t1, t2, t3 = st.tabs(["📊 Gestión", "🩺 Clínico & Demo", "📄 Data Detallada"])

    with t1:
        c_left, c_right = st.columns(2)
        with c_left:
            with st.container(border=True):
                st.markdown('<div class="chart-title">📈 Tendencias Locales</div>', unsafe_allow_html=True)
                if 'anio_mes' in df_r.columns:
                    evo = df_r.groupby('anio_mes').size().reset_index(name='Total')
                    st.plotly_chart(style_chart(px.area(evo, x='anio_mes', y='Total', labels={'anio_mes': 'Mes', 'Total': 'Atenciones'})), use_container_width=True)
            with st.container(border=True):
                st.markdown('<div class="chart-title">⚙️ Estado Atención Local</div>', unsafe_allow_html=True)
                fl = df_r['estado'].value_counts().reset_index()
                st.plotly_chart(style_chart(px.bar(fl, x='count', y='estado', orientation='h', color='estado', labels={'estado': 'Estado', 'count': 'Cantidad'})), use_container_width=True)
        with c_right:
            with st.container(border=True):
                st.markdown('<div class="chart-title">🏆 Top Distritos</div>', unsafe_allow_html=True)
                if 'distrito' in df_r.columns:
                    top = df_r['distrito'].value_counts().head(10).reset_index()
                    st.plotly_chart(style_chart(px.bar(top, x='count', y='distrito', orientation='h', labels={'distrito': 'Jurisdicción', 'count': 'Atenciones'})), use_container_width=True)

    with t2:
        c_left, c_right = st.columns(2)
        with c_left:
             with st.container(border=True):
                st.markdown('<div class="chart-title">🔥 Edad vs Riesgo (BIRADS)</div>', unsafe_allow_html=True)
                if 'grupo_etario' in df_r.columns and 'birads_categoria' in df_r.columns:
                    ct = pd.crosstab(df_r['grupo_etario'], df_r['birads_categoria'])
                    st.plotly_chart(style_chart(px.imshow(ct, aspect="auto", color_continuous_scale="Reds", labels={'x': 'BIRADS', 'y': 'Grupo Etario', 'color': 'Casos'})), use_container_width=True)
        with c_right:
            with st.container(border=True):
                st.markdown('<div class="chart-title">🧑‍🤝‍🧑 Etnia Local</div>', unsafe_allow_html=True)
                if 'etnia' in df_r.columns:
                    etn = df_r['etnia'].value_counts().head(8).reset_index()
                    etn.columns = ['Etnia', 'Cantidad']
                    st.plotly_chart(style_chart(px.pie(etn, names='Etnia', values='Cantidad', hole=0.6)), use_container_width=True)

    with t3:
        with st.container(border=True):
            st.markdown('<div class="chart-title">📄 Registro Detallado</div>', unsafe_allow_html=True)
            cols_show = ['fecha_solicitud', 'provincia', 'distrito', 'nombre_eess_origen', 'edad', 'birads_categoria', 'estado']
            cols_final = [c for c in cols_show if c in df_r.columns]
            st.dataframe(df_r[cols_final], use_container_width=True)

if st.session_state["app_state"] == "HOME":
    render_home()
else:
    df_filtrado, servicio_nombre = render_sidebar_filters(df_master)
    if st.session_state["app_state"] == "DASHBOARD":
        render_dashboard(df_filtrado, servicio_nombre)
    elif st.session_state["app_state"] == "REGIONAL":
        render_regional(df_filtrado)