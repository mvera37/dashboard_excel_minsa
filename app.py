import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go
import os
import json
import warnings
import datetime

# --- CONFIGURACIÓN ---
warnings.filterwarnings("ignore")
st.set_page_config(page_title="TeleMammo BI", page_icon="💙", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp { font-family: 'Inter', sans-serif; background-color: #F8FAFC; }
    
    .navbar { display: flex; justify-content: space-between; align-items: center; padding: 1rem 2rem; background: white; border-radius: 12px; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    .nav-logo { font-weight: 800; font-size: 1.4rem; color: #0F172A; display: flex; align-items: center; gap: 10px; }
    
    .kpi-container { background: white; padding: 15px; border-radius: 10px; border-left: 5px solid #2563EB; box-shadow: 0 4px 6px rgba(0,0,0,0.03); transition: transform 0.2s; height: 100%; }
    .kpi-container:hover { transform: translateY(-2px); }
    .kpi-val { font-size: 1.8rem; font-weight: 800; color: #1E293B; }
    .kpi-lbl { font-size: 0.85rem; color: #64748B; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-sub { font-size: 0.75rem; color: #10B981; font-weight: 600; margin-top: 5px; }

    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #ffffff; border-radius: 6px; padding: 8px 16px; font-weight: 600; border: 1px solid #E2E8F0; }
    .stTabs [aria-selected="true"] { background-color: #EFF6FF; color: #2563EB; border-color: #2563EB; }
    
    .hero-title { font-size: 3.5rem; font-weight: 800; color: #0F172A; line-height: 1.1; margin-bottom: 1rem; }
    .highlight { color: #2563EB; }
    </style>
""", unsafe_allow_html=True)

# --- CONEXIÓN ---
load_dotenv()
if not os.getenv("DATABASE_URL"):
    st.error("❌ Falta DATABASE_URL en .env")
    st.stop()

engine = create_engine(os.getenv("DATABASE_URL"))

# --- ESTADO ---
if "app_state" not in st.session_state: st.session_state["app_state"] = "HOME"
if "selected_dept" not in st.session_state: st.session_state["selected_dept"] = None

# --- CARGA DE DATOS ---
@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_sql("SELECT * FROM vista_master_dashboard", engine)
        
        # Normalización de columnas
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
        
        # Validar y convertir fechas
        if 'fecha_solicitud' in df.columns:
            df['fecha_solicitud'] = pd.to_datetime(df['fecha_solicitud'])
            
            # Asegurar día de semana nombre
            dias = {0:'Domingo', 1:'Lunes', 2:'Martes', 3:'Miércoles', 4:'Jueves', 5:'Viernes', 6:'Sábado'}
            # Postgres DOW: 0=Domingo. Pandas dt.dayofweek: 0=Lunes.
            # Ajustamos según lo que venga de SQL o calculamos aquí en Pandas
            df['nombre_dia'] = df['fecha_solicitud'].dt.day_name().map({
                'Monday':'Lunes', 'Tuesday':'Martes', 'Wednesday':'Miércoles', 
                'Thursday':'Jueves', 'Friday':'Viernes', 'Saturday':'Sábado', 'Sunday':'Domingo'
            })
        
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

@st.cache_data
def load_geo():
    path = "geojson/peru_departamental_simple.geojson"
    if not os.path.exists(path): path = "peru_departamental_simple.geojson"
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f: return json.load(f)
    return None

df_master = load_data()
geojson_peru = load_geo()

# --- FUNCIONES DE GRÁFICOS ---
def plot_mapa_nacional(df):
    col_dep = 'departamento' if 'departamento' in df.columns else 'nombdep'
    map_data = df.groupby(col_dep).agg(
        total=('es_atendido', 'count'),
        anormales=('es_anormal', 'sum'),
        tiempo=('tiempo_atencion_dias', 'mean')
    ).reset_index()
    map_data['tasa_anormalidad'] = (map_data['anormales'] / map_data['total']) * 100
    
    fig = px.choropleth_mapbox(
        map_data, geojson=geojson_peru, locations=col_dep, featureidkey="properties.NOMBDEP",
        color="total", color_continuous_scale="Blues",
        mapbox_style="carto-positron", zoom=3.8, center={"lat": -9.19, "lon": -75.01}, opacity=0.8,
        hover_data={"total":True, "tasa_anormalidad":':.1f', "tiempo":':.1f'},
        labels={'total':'Total Casos'}
    )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=450, clickmode='event+select')
    return fig

# --- VISTA 1: HOME ---
def render_home():
    st.markdown("""
    <div class="navbar">
        <div class="nav-logo"><span>💙</span> TeleMammo <small style="color:#64748B; margin-left:8px">MINSA BI</small></div>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns([1.1, 1], gap="large")
    with c1:
        st.write("")
        st.markdown('<span style="background:#DBEAFE; color:#1E40AF; padding:4px 12px; border-radius:20px; font-weight:700; font-size:0.8rem">SISTEMA OFICIAL 2025</span>', unsafe_allow_html=True)
        st.markdown('<div class="hero-title">Transformando el Diagnóstico: <span class="highlight">Telemamografía</span></div>', unsafe_allow_html=True)
        st.markdown("""
        <p style="font-size:1.1rem; color:#475569; line-height:1.6;">
        Modernizando la detección temprana del cáncer de mama en Perú con tecnología digital avanzada.
        Monitoreo en tiempo real de cobertura, tiempos de atención y hallazgos clínicos (BIRADS).
        </p>
        """, unsafe_allow_html=True)
        
        st.write("")
        if st.button("👉 Acceder al Dashboard Ejecutivo", type="primary"):
            st.session_state["app_state"] = "DASHBOARD"
            st.rerun()
            
        if not df_master.empty:
            total = len(df_master)
            col_tiempo = 'tiempo_atencion_dias' if 'tiempo_atencion_dias' in df_master.columns else df_master.columns[0]
            tiempo = df_master[col_tiempo].mean() if col_tiempo in df_master.columns else 0
            st.markdown(f"""
            <div style="margin-top:30px; display:flex; gap:20px; font-weight:600; color:#64748B;">
                <div>🏥 {total:,.0f} Atenciones</div>
                <div>⚡ {tiempo:.1f} Días promedio</div>
                <div>🛡️ Datos Seguros</div>
            </div>
            """, unsafe_allow_html=True)

    with c2:
        st.markdown('<img src="https://images.unsplash.com/photo-1579684385127-1ef15d508118?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80" style="width:100%; border-radius:20px; box-shadow:0 10px 30px rgba(0,0,0,0.1);">', unsafe_allow_html=True)

# --- VISTA 2: DASHBOARD NACIONAL ---
def render_dashboard():
    with st.sidebar:
        st.header("🎛️ Filtros Globales")
        if st.button("🏠 Inicio"):
            st.session_state["app_state"] = "HOME"
            st.rerun()
        st.markdown("---")
        
        # Filtros Dinámicos
        if 'fecha_solicitud' in df_master.columns:
            y_opts = sorted(df_master['fecha_solicitud'].dt.year.unique())
            sel_year = st.multiselect("Año", y_opts, default=y_opts)
            
            df_f = df_master.copy()
            if sel_year: df_f = df_f[df_f['fecha_solicitud'].dt.year.isin(sel_year)]
        else:
            df_f = df_master.copy()
    
    st.markdown("## 🟦 Visión Estratégica Nacional")
    
    # --- CÁLCULO DE KPIs ---
    total = len(df_f)
    if total > 0:
        pct_atend = (df_f['es_atendido'].sum() / total) * 100
        pct_anul = (df_f['es_anulado'].sum() / total) * 100
        tiempo_avg = df_f['tiempo_atencion_dias'].mean()
        tasa_anorm = (df_f['es_anormal'].sum() / total) * 100
        
        # Intensidad 40-69 (Indicador MINSA)
        # Filtro: Mujeres 40-69
        target = df_f[(df_f['sexo']=='FEMENINO') & (df_f['edad'].between(40,69))]
        # Intensidad = (Atendidas en target / Total en target) * 100
        intensidad = (target['es_atendido'].sum() / len(target)) * 100 if len(target) > 0 else 0
        
        deptos_activos = df_f['departamento'].nunique()
        
        # Promedio atenciones por día
        # Calculamos el rango de días en el filtro actual
        min_date = df_f['fecha_solicitud'].min()
        max_date = df_f['fecha_solicitud'].max()
        if pd.notnull(min_date) and pd.notnull(max_date):
            dias_periodo = (max_date - min_date).days + 1
            prom_diario = total / dias_periodo if dias_periodo > 0 else total
        else:
            prom_diario = 0
            
    else:
        pct_atend=pct_anul=tiempo_avg=tasa_anorm=intensidad=deptos_activos=prom_diario=0

    # KPI ROW 1
    k1, k2, k3, k4 = st.columns(4)
    def card(col, lbl, val, sub=""):
        col.markdown(f"""<div class="kpi-container"><div class="kpi-val">{val}</div><div class="kpi-lbl">{lbl}</div><div class="kpi-sub">{sub}</div></div>""", unsafe_allow_html=True)
    
    card(k1, "Total Procesado", f"{total:,.0f}")
    card(k2, "Intensidad 40-69", f"{intensidad:.1f}%", "Indicador MINSA")
    card(k3, "Tasa Anormalidad", f"{tasa_anorm:.1f}%", "BIRADS 3-5")
    card(k4, "Promedio Diario", f"{prom_diario:.0f}", "Atenciones/día")

    st.write("")
    
    # KPI ROW 2
    k5, k6, k7, k8 = st.columns(4)
    card(k5, "% Atendidas", f"{pct_atend:.1f}%")
    card(k6, "% Anuladas", f"{pct_anul:.1f}%", "Calidad Operativa")
    card(k7, "Tiempo Promedio", f"{tiempo_avg:.1f} d")
    card(k8, "Deptos Activos", f"{deptos_activos}")
    
    st.write("")

    # --- CUERPO PRINCIPAL ---
    c_main_L, c_main_R = st.columns([1.5, 1])
    
    with c_main_L:
        st.subheader("🗺️ Mapa Nacional")
        st.info("👆 Clic en un departamento para drill-down.")
        if geojson_peru:
            fig_map = plot_mapa_nacional(df_f)
            evt = st.plotly_chart(fig_map, use_container_width=True, on_select="rerun")
            if evt and evt['selection']['points']:
                sel = evt['selection']['points'][0]['location']
                st.session_state["selected_dept"] = sel
                st.session_state["app_state"] = "REGIONAL"
                st.rerun()
        else:
            st.warning("GeoJSON no encontrado")
        
        # --- NUEVO: GRÁFICO DE BARRAS DEBAJO DEL MAPA ---
        st.markdown("##### 📊 Ranking de Mamografías por Departamento")
        df_rank = df_f['departamento'].value_counts().reset_index()
        df_rank.columns = ['Departamento', 'Total']
        fig_rank = px.bar(df_rank, x='Departamento', y='Total', color='Total', color_continuous_scale='Blues')
        st.plotly_chart(fig_rank, use_container_width=True)

    with c_main_R:
        # PESTAÑAS
        tabs = st.tabs(["📈 Temporal", "👥 Demografía", "🩺 Clínico", "⚙️ Flujo"])
        
        # 1. ANÁLISIS TEMPORAL
        with tabs[0]:
            st.markdown("**Evolución Mensual**")
            if 'anio_mes' in df_f.columns:
                evo = df_f.groupby('anio_mes').agg(
                    Total=('es_atendido', 'count'),
                    Anormales=('es_anormal', 'sum')
                ).reset_index()
                
                fig_evo = go.Figure()
                fig_evo.add_trace(go.Scatter(x=evo['anio_mes'], y=evo['Total'], name='Total', fill='tozeroy'))
                fig_evo.add_trace(go.Scatter(x=evo['anio_mes'], y=evo['Anormales'], name='Anormales', line=dict(color='red', dash='dot')))
                fig_evo.update_layout(height=250, margin=dict(l=0,r=0,t=10,b=0), legend=dict(orientation="h", y=1.1))
                st.plotly_chart(fig_evo, use_container_width=True)
                
                st.markdown("**Tiempo Promedio Mensual (Días)**")
                evo_time = df_f.groupby('anio_mes')['tiempo_atencion_dias'].mean().reset_index()
                fig_tm = px.line(evo_time, x='anio_mes', y='tiempo_atencion_dias', markers=True)
                fig_tm.update_layout(height=200, margin=dict(l=0,r=0,t=10,b=0))
                st.plotly_chart(fig_tm, use_container_width=True)

            st.markdown("**Patrón Semanal (Día Pico)**")
            if 'nombre_dia' in df_f.columns:
                dias_order = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
                sem = df_f['nombre_dia'].value_counts().reindex(dias_order).reset_index()
                fig_sem = px.bar(sem, x='nombre_dia', y='count', color='count', color_continuous_scale='Viridis')
                fig_sem.update_layout(height=200, xaxis_title=None)
                st.plotly_chart(fig_sem, use_container_width=True)

        # 2. DEMOGRAFÍA (NUEVO: MIGRANTES Y ETNIAS)
        with tabs[1]:
            st.markdown("**Migrantes (No Peruanos)**")
            df_mig = df_f[df_f['nacionalidad'] != 'PERU']
            if not df_mig.empty:
                top_mig = df_mig['nacionalidad'].value_counts().head(5).reset_index()
                st.dataframe(top_mig, use_container_width=True, hide_index=True)
            else:
                st.info("Sin registros de extranjeros.")
                
            st.markdown("**Etnia / Raza**")
            if 'etnia' in df_f.columns:
                etnia_dist = df_f['etnia'].value_counts().reset_index()
                fig_et = px.pie(etnia_dist, names='etnia', values='count', hole=0.4)
                fig_et.update_layout(height=200, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_et, use_container_width=True)
            
            st.markdown("**Edad**")
            age_dist = df_f['grupo_etario'].value_counts().sort_index()
            fig_age = px.bar(age_dist, x=age_dist.index, y=age_dist.values)
            fig_age.update_layout(height=200, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_age, use_container_width=True)

        # 3. CLÍNICO
        with tabs[2]:
            st.markdown("**Distribución BIRADS**")
            bi_counts = df_f['birads_categoria'].value_counts().sort_index()
            fig_bi = px.bar(bi_counts, x=bi_counts.index, y=bi_counts.values, color=bi_counts.index, text_auto=True)
            fig_bi.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig_bi, use_container_width=True)

        # 4. FLUJO
        with tabs[3]:
            st.markdown("**Distribución por Estado**")
            fig_flujo = px.bar(df_f['estado'].value_counts().reset_index(), x='count', y='estado', orientation='h', text_auto=True, color='estado')
            st.plotly_chart(fig_flujo, use_container_width=True)

# --- VISTA 3: REGIONAL ---
def render_regional():
    dep = st.session_state["selected_dept"]
    col_dep = 'departamento' if 'departamento' in df_master.columns else 'nombdep'
    
    df_r = df_master[df_master[col_dep] == dep]
    
    col_back, col_tit = st.columns([1, 5])
    with col_back:
        if st.button("⬅️ Volver"):
            st.session_state["app_state"] = "DASHBOARD"
            st.session_state["selected_dept"] = None
            st.rerun()
    with col_tit:
        st.markdown(f"## 🟩 Análisis Regional: **{dep}**")
        
    total = len(df_r)
    if total > 0:
        tasa = (df_r['es_anormal'].sum()/total)*100
        tiempo = df_r['tiempo_atencion_dias'].mean()
        
        # Intensidad Local
        target_r = df_r[(df_r['sexo']=='FEMENINO') & (df_r['edad'].between(40,69))]
        intensidad_r = (target_r['es_atendido'].sum() / len(target_r)) * 100 if len(target_r) > 0 else 0
        
        pendientes = len(df_r[df_r['estado'].astype(str).str.lower() == 'pendiente'])
    else:
        tasa=tiempo=intensidad_r=pendientes=0
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Regional", f"{total:,}")
    k2.metric("Intensidad (40-69)", f"{intensidad_r:.1f}%")
    k3.metric("Tasa Anormalidad", f"{tasa:.1f}%")
    k4.metric("Tiempo Promedio", f"{tiempo:.1f} d")
    
    st.markdown("---")
    
    # Análisis Regional Profundo
    c_left, c_right = st.columns([2, 1])
    
    with c_left:
        t1, t2, t3 = st.tabs(["📊 Evolución & Operativo", "🩺 Clínico", "📄 Data"])
        
        with t1:
            st.markdown("##### 📈 Evolución Mensual del Departamento")
            if 'anio_mes' in df_r.columns:
                evo_dep = df_r.groupby('anio_mes').size().reset_index(name='Total')
                fig_ln = px.line(evo_dep, x='anio_mes', y='Total', markers=True, title=f"Tendencia en {dep}")
                st.plotly_chart(fig_ln, use_container_width=True)
            
            st.markdown("##### ⚙️ Estado de Atención")
            est_dep = df_r['estado'].value_counts().reset_index()
            c_e1, c_e2 = st.columns(2)
            # Barras
            fig_bar = px.bar(est_dep, x='estado', y='count', color='estado', text_auto=True)
            c_e1.plotly_chart(fig_bar, use_container_width=True)
            # Pie
            fig_pie = px.pie(est_dep, names='estado', values='count', hole=0.4)
            c_e2.plotly_chart(fig_pie, use_container_width=True)

        with t2:
            st.markdown("**Heatmap: Edad vs BIRADS**")
            if not df_r.empty:
                ct = pd.crosstab(df_r['grupo_etario'], df_r['birads_categoria'])
                fig_hm = px.imshow(ct, text_auto=True, aspect="auto", color_continuous_scale="Reds")
                st.plotly_chart(fig_hm, use_container_width=True)

        with t3:
            st.dataframe(df_r[['fecha_solicitud','provincia','distrito','establecimiento','edad','birads_categoria','estado','tiempo_atencion_dias']], use_container_width=True)

    with c_right:
        st.markdown("**Top Distritos**")
        top_dist = df_r['distrito'].value_counts().head(10).reset_index()
        fig_d = px.bar(top_dist, x='count', y='distrito', orientation='h', text_auto=True)
        st.plotly_chart(fig_d, use_container_width=True)
        
        st.markdown("**Etnia Local**")
        fig_et = px.pie(df_r, names='etnia', hole=0.5)
        st.plotly_chart(fig_et, use_container_width=True)

# --- CONTROLADOR ---
if st.session_state["app_state"] == "HOME":
    render_home()
elif st.session_state["app_state"] == "DASHBOARD":
    render_dashboard()
elif st.session_state["app_state"] == "REGIONAL":
    render_regional()