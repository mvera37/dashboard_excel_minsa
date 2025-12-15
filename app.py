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

# --- ESTILOS CSS (MEJORADOS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* 1. FONDO GENERAL (Azul-Grisáceo Profesional) */
    .stApp { 
        font-family: 'Inter', sans-serif; 
        background-color: #F1F5F9; /* Slate 100 */
    }
    
    /* 2. NAVBAR */
    .navbar { 
        display: flex; justify-content: space-between; align-items: center; 
        padding: 1rem 2rem; background: white; border-radius: 12px; 
        margin-bottom: 1.5rem; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); 
        border: 1px solid #E2E8F0;
    }
    .nav-logo { font-weight: 800; font-size: 1.4rem; color: #0F172A; display: flex; align-items: center; gap: 10px; }
    
    /* 3. TARJETAS "3D" (Cajas Blancas) */
    /* Esta clase envuelve gráficos y KPIs para separarlos del fondo */
    .content-card {
        background: white;
        padding: 20px;
        border-radius: 16px;
        border: 1px solid #E2E8F0; /* Borde sutil */
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); /* Sombra suave */
        margin-bottom: 20px;
        height: 100%;
    }
    
    /* Títulos dentro de las tarjetas */
    .card-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 15px;
        border-bottom: 1px solid #F1F5F9;
        padding-bottom: 10px;
    }

    /* KPIs Específicos */
    .kpi-val { font-size: 2rem; font-weight: 800; color: #0F172A; line-height: 1.2; }
    .kpi-lbl { font-size: 0.85rem; color: #64748B; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 5px; }
    .kpi-sub { font-size: 0.8rem; font-weight: 500; margin-top: 5px; }
    
    /* Tabs Clean */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: white; border-radius: 6px; padding: 8px 16px; font-weight: 600; border: 1px solid #E2E8F0; }
    .stTabs [aria-selected="true"] { background-color: #2563EB; color: white; border-color: #2563EB; }
    
    .hero-title { font-size: 3.5rem; font-weight: 800; color: #0F172A; line-height: 1.1; margin-bottom: 1rem; }
    .highlight { color: #2563EB; }
    
    /* Estilos para el sidebar del código 2 */
    .sidebar .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .sidebar .stTabs [data-baseweb="tab"] { 
        background-color: white; 
        border-radius: 6px; 
        padding: 6px 16px; 
        font-weight: 600; 
        border: 1px solid #E2E8F0; 
        font-size: 0.9rem;
    }
    .sidebar .stTabs [aria-selected="true"] { 
        background-color: #2563EB; 
        color: white; 
        border-color: #2563EB; 
    }
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
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
        
        if 'fecha_solicitud' in df.columns:
            df['fecha_solicitud'] = pd.to_datetime(df['fecha_solicitud'])
            dias = {0:'Domingo', 1:'Lunes', 2:'Martes', 3:'Miércoles', 4:'Jueves', 5:'Viernes', 6:'Sábado'}
            df['nombre_dia'] = df['fecha_solicitud'].dt.day_name().map({
                'Monday':'Lunes', 'Tuesday':'Martes', 'Wednesday':'Miércoles', 
                'Thursday':'Jueves', 'Friday':'Viernes', 'Saturday':'Sábado', 'Sunday':'Domingo'
            })
        return df
    except Exception as e:
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

# --- HELPER: ESTILO DE GRÁFICOS ---
def style_chart(fig):
    """Limpia los gráficos para que se vean bien dentro de las tarjetas blancas"""
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', # Fondo transparente para integrarse a la tarjeta
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter", color="#64748B"),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='#F1F5F9', zeroline=False),
        colorway=px.colors.qualitative.Prism 
    )
    return fig

# --- HELPER: KPI CARD (NUEVO DISEÑO 3D) ---
def kpi_card_html(title, value, subtext, color="neutral"):
    """Genera el HTML para una tarjeta KPI dentro de un contenedor blanco"""
    c_style = "color:#64748B"
    if color == "success": c_style = "color:#10B981"
    if color == "warning": c_style = "color:#F59E0B"
    
    return f"""
    <div class="content-card">
        <div class="kpi-val">{value}</div>
        <div class="kpi-lbl">{title}</div>
        <div class="kpi-sub" style="{c_style}">{subtext}</div>
    </div>
    """

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
        st.markdown('<span style="background:#DBEAFE; color:#1E40AF; padding:4px 12px; border-radius:20px; font-weight:700; font-size:0.8rem">Dirección de Telemedicina - DITEL</span>', unsafe_allow_html=True)
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
        # Imagen con estilo de tarjeta
        st.markdown("""
        <div style="border-radius:20px; overflow:hidden; box-shadow:0 10px 30px rgba(0,0,0,0.1); border:4px solid white;">
            <img src="https://images.unsplash.com/photo-1579684385127-1ef15d508118?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80" style="width:100%;">
        </div>
        """, unsafe_allow_html=True)

# --- VISTA 2: DASHBOARD NACIONAL MEJORADO ---
def render_dashboard():
    # --- SIDEBAR DEL CÓDIGO 2 (MEJORADO) ---
    with st.sidebar:
        st.title("📊 Dashboard")
        st.caption("Filtros Globales")
        
        # Lógica de Filtros (del código 2)
        if 'fecha_solicitud' in df_master.columns:
            # Crear columnas necesarias para los filtros (como en código 2)
            df_master['mes_num'] = df_master['fecha_solicitud'].dt.month
            mapa_meses = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio',
                          7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
            df_master['nombre_mes'] = df_master['mes_num'].map(mapa_meses)
            
            # A. Filtro Año
            years_avail = sorted(df_master['fecha_solicitud'].dt.year.unique(), reverse=True)
            sel_year = st.multiselect("📅 Año Fiscal", years_avail, default=years_avail[:1] if years_avail else None)
            
            # Filtrado preliminar por año
            if sel_year:
                df_year = df_master[df_master['fecha_solicitud'].dt.year.isin(sel_year)]
            else:
                df_year = df_master.copy()
            
            # B. Filtro Mes (Dependiente del año seleccionado)
            if 'nombre_mes' in df_year.columns:
                # Ordenar meses lógicamente no alfabéticamente
                meses_unicos = df_year[['mes_num', 'nombre_mes']].drop_duplicates().sort_values('mes_num')
                opciones_mes = meses_unicos['nombre_mes'].tolist()
                
                sel_month = st.multiselect("🗓️ Mes", opciones_mes)
                
                # Filtrado final
                if sel_month:
                    df_f = df_year[df_year['nombre_mes'].isin(sel_month)]
                else:
                    df_f = df_year
            else:
                df_f = df_year
        else:
            df_f = df_master.copy()
            
        st.markdown("---")
        st.caption("Navegación")
        if st.button("🏠 Volver al Inicio"):
            st.session_state["app_state"] = "HOME"
            st.rerun()
            
        st.write("")
        st.info(f"Registros: **{len(df_f):,.0f}**")
    
    st.markdown("## Panorama Ejecutivo Nacional")
    
    # --- CÁLCULO DE KPIs (con validaciones del código 2) ---
    total = len(df_f)
    if total > 0:
        pct_atend = (df_f['es_atendido'].sum() / total) * 100
        pct_anul = (df_f['es_anulado'].sum() / total) * 100
        tiempo_avg = df_f['tiempo_atencion_dias'].mean()
        tasa_anorm = (df_f['es_anormal'].sum() / total) * 100
        
        # Intensidad 40-69 (Indicador MINSA)
        target = df_f[(df_f['sexo']=='FEMENINO') & (df_f['edad'].between(40,69))]
        intensidad = (target['es_atendido'].sum() / len(target)) * 100 if len(target) > 0 else 0
        
        # Validación de columna departamento (del código 2)
        col_dep = 'departamento' if 'departamento' in df_f.columns else 'nombdep'
        deptos_activos = df_f[col_dep].nunique() if col_dep in df_f.columns else 0
        
        # Promedio atenciones por día (mejorado del código 2)
        min_date = df_f['fecha_solicitud'].min()
        max_date = df_f['fecha_solicitud'].max()
        if pd.notnull(min_date) and pd.notnull(max_date):
            dias_periodo = (max_date - min_date).days + 1
            prom_diario = total / dias_periodo if dias_periodo > 0 else total
        else:
            prom_diario = 0
            
    else:
        pct_atend=pct_anul=tiempo_avg=tasa_anorm=intensidad=deptos_activos=prom_diario=0

    # KPI ROW 1 (usando el efecto 3D del código 2 pero manteniendo estructura)
    k1, k2, k3, k4 = st.columns(4)
    
    # Helper para tarjetas KPI (combinando ambos)
    def card_kpi(col, titulo, valor, subtitulo="", tipo="normal"):
        if tipo == "success":
            color_class = "kpi-success"
        elif tipo == "warning":
            color_class = "kpi-warning"
        else:
            color_class = ""
        
        col.markdown(f"""
        <div class="content-card kpi-card {color_class}">
            <div class="kpi-val">{valor}</div>
            <div class="kpi-lbl">{titulo}</div>
            <div class="kpi-sub">{subtitulo}</div>
        </div>
        """, unsafe_allow_html=True)
    
    card_kpi(k1, "Total Procesado", f"{total:,.0f}", "Mamografías")
    card_kpi(k2, "Intensidad 40-69", f"{intensidad:.1f}%", "Indicador MINSA", "success")
    card_kpi(k3, "Tasa Anormalidad", f"{tasa_anorm:.1f}%", "BIRADS 3-5", "warning")
    card_kpi(k4, "Promedio Diario", f"{prom_diario:.0f}", "Atenciones/día")

    st.write("")
    
    # KPI ROW 2
    k5, k6, k7, k8 = st.columns(4)
    card_kpi(k5, "% Atendidas", f"{pct_atend:.1f}%", "Efectividad")
    card_kpi(k6, "% Anuladas", f"{pct_anul:.1f}%", "Calidad Operativa", "warning")
    card_kpi(k7, "Tiempo Promedio", f"{tiempo_avg:.1f} d", "Desde solicitud")
    card_kpi(k8, "Deptos Activos", f"{deptos_activos}", "Cobertura Nacional")
    
    st.write("")

    # --- CUERPO PRINCIPAL CON TARJETAS ESTILIZADAS ---
    c_main_L, c_main_R = st.columns([1.5, 1])
    
    with c_main_L:
        # TARJETA: MAPA NACIONAL (estilizada como código 2)
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">🗺️ Mapa Nacional</div>', unsafe_allow_html=True)
        st.info("👆 Clic en un departamento para drill-down.")
        
        if geojson_peru and col_dep in df_f.columns:
            # Preparar datos para mapa (del código 2)
            map_data = df_f.groupby(col_dep).size().reset_index(name='Total')
            
            fig_map = px.choropleth_mapbox(
                map_data, geojson=geojson_peru, locations=col_dep, 
                featureidkey="properties.NOMBDEP",
                color="Total", color_continuous_scale="Blues",
                mapbox_style="carto-positron", zoom=3.8, 
                center={"lat": -9.19, "lon": -75.01}, opacity=0.9,
                labels={col_dep: 'Departamento', 'Total': 'Nro. Atenciones'}  # Mejora del código 2
            )
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=450)
            
            evt = st.plotly_chart(fig_map, use_container_width=True, on_select="rerun")
            if evt and evt['selection']['points']:
                sel = evt['selection']['points'][0]['location']
                st.session_state["selected_dept"] = sel
                st.session_state["app_state"] = "REGIONAL"
                st.rerun()
        else:
            st.warning("GeoJSON no encontrado o columna de departamento no disponible")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # TARJETA: RANKING (mejorado con etiquetas del código 2)
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">📊 Ranking de Mamografías por Departamento</div>', unsafe_allow_html=True)
        
        if col_dep in df_f.columns:
            df_rank = df_f[col_dep].value_counts().reset_index()
            df_rank.columns = ['Departamento', 'Total']  # Nombres limpios
            
            fig_rank = px.bar(df_rank, x='Departamento', y='Total', 
                             color='Total', color_continuous_scale='Blues',
                             labels={'Departamento': 'Región', 'Total': 'Nro. Atenciones'})  # Mejora código 2
            st.plotly_chart(fig_rank, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c_main_R:
        # PESTAÑAS EN TARJETAS INDIVIDUALES
        tabs = st.tabs(["📈 Temporal", "👥 Demografía", "🩺 Clínico", "⚙️ Flujo"])
        
        # 1. ANÁLISIS TEMPORAL (CON TODO LO DEL CÓDIGO 1)
        with tabs[0]:
            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">Análisis Temporal</div>', unsafe_allow_html=True)
            
            # EVOLUCIÓN MENSUAL (completa del código 1)
            st.markdown("**Evolución Mensual**")
            if 'anio_mes' in df_f.columns:
                evo = df_f.groupby('anio_mes').agg(
                    Total=('es_atendido', 'count'),
                    Anormales=('es_anormal', 'sum')
                ).reset_index()
                
                fig_evo = go.Figure()
                fig_evo.add_trace(go.Scatter(x=evo['anio_mes'], y=evo['Total'], 
                                             name='Total', fill='tozeroy',
                                             line=dict(color='#1E88E5')))
                fig_evo.add_trace(go.Scatter(x=evo['anio_mes'], y=evo['Anormales'], 
                                             name='Anormales', 
                                             line=dict(color='#FF6B6B', dash='dot')))
                fig_evo.update_layout(
                    height=250, 
                    margin=dict(l=0,r=0,t=10,b=0), 
                    legend=dict(orientation="h", y=1.1),
                    xaxis_title='Mes',
                    yaxis_title='Cantidad'  # Mejora del código 2
                )
                st.plotly_chart(fig_evo, use_container_width=True)
                
                # TIEMPO PROMEDIO MENSUAL (con etiquetas mejoradas)
                st.markdown("**Tiempo Promedio Mensual (Días)**")
                evo_time = df_f.groupby('anio_mes')['tiempo_atencion_dias'].mean().reset_index()
                fig_tm = px.line(evo_time, x='anio_mes', y='tiempo_atencion_dias', 
                                markers=True,
                                labels={'anio_mes': 'Mes', 'tiempo_atencion_dias': 'Días Promedio'})  # Mejora
                fig_tm.update_traces(line_color='#F59E0B')  # Color del código 2
                fig_tm.update_layout(height=200, margin=dict(l=0,r=0,t=10,b=0))
                st.plotly_chart(fig_tm, use_container_width=True)

            # PATRÓN SEMANAL (MANTENIDO DEL CÓDIGO 1)
            st.markdown("**Patrón Semanal (Día Pico)**")
            if 'nombre_dia' in df_f.columns:
                dias_order = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
                sem = df_f['nombre_dia'].value_counts().reindex(dias_order).reset_index()
                sem.columns = ['Día', 'Cantidad']  # Nombres limpios
                
                fig_sem = px.bar(sem, x='Día', y='Cantidad', color='Cantidad', 
                                color_continuous_scale='Viridis',
                                labels={'Día': 'Día de la semana', 'Cantidad': 'Atenciones'})  # Mejora
                fig_sem.update_layout(height=200, xaxis_title=None)
                st.plotly_chart(fig_sem, use_container_width=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

        # 2. DEMOGRAFÍA (CON TODO DEL CÓDIGO 1 + MEJORAS DEL 2)
        with tabs[1]:
            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">Perfil Demográfico</div>', unsafe_allow_html=True)
            
            # MIGRANTES (mejor presentación del código 2)
            st.caption("**Migrantes (No Peruanos)**")
            df_mig = df_f[df_f['nacionalidad'] != 'PERU']
            if not df_mig.empty:
                top_mig = df_mig['nacionalidad'].value_counts().head(5).reset_index()
                top_mig.columns = ['País', 'Casos']  # Nombres limpios
                st.dataframe(top_mig, use_container_width=True, hide_index=True)
            else:
                st.info("Sin registros de extranjeros.")
                
            # ETNIA / RAZA (MANTENIDO DEL CÓDIGO 1)
            st.caption("**Etnia / Raza**")
            if 'etnia' in df_f.columns:
                etnia_dist = df_f['etnia'].value_counts().reset_index()
                etnia_dist.columns = ['Etnia', 'Cantidad']  # Nombres limpios
                
                fig_et = px.pie(etnia_dist, names='Etnia', values='Cantidad', hole=0.4,
                               labels={'Etnia': 'Grupo étnico', 'Cantidad': 'Pacientes'})  # Mejora
                fig_et.update_layout(height=200, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_et, use_container_width=True)
            
            # EDAD (con etiquetas mejoradas)
            st.caption("**Distribución por Edad**")
            age_dist = df_f['grupo_etario'].value_counts().sort_index()
            age_dist_df = age_dist.reset_index()
            age_dist_df.columns = ['Grupo Etario', 'Pacientes']  # Nombres limpios
            
            fig_age = px.bar(age_dist_df, x='Grupo Etario', y='Pacientes',
                            labels={'Grupo Etario': 'Rango de Edad', 'Pacientes': 'Cantidad'})  # Mejora
            fig_age.update_layout(height=200, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_age, use_container_width=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

        # 3. CLÍNICO (con etiquetas mejoradas)
        with tabs[2]:
            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">Indicadores Clínicos</div>', unsafe_allow_html=True)
            
            st.markdown("**Distribución BIRADS**")
            bi_counts = df_f['birads_categoria'].value_counts().sort_index()
            bi_counts_df = bi_counts.reset_index()
            bi_counts_df.columns = ['Categoría BIRADS', 'Casos']  # Nombres limpios
            
            fig_bi = px.bar(bi_counts_df, x='Categoría BIRADS', y='Casos', 
                           color='Categoría BIRADS', text_auto=True,
                           labels={'Categoría BIRADS': 'Clasificación', 'Casos': 'Pacientes'})  # Mejora
            fig_bi.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig_bi, use_container_width=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

        # 4. FLUJO (con etiquetas mejoradas)
        with tabs[3]:
            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">Flujo Operativo</div>', unsafe_allow_html=True)
            
            st.markdown("**Distribución por Estado**")
            flujo_counts = df_f['estado'].value_counts().reset_index()
            flujo_counts.columns = ['Estado', 'Cantidad']  # Nombres limpios
            
            fig_flujo = px.bar(flujo_counts, x='Cantidad', y='Estado', 
                              orientation='h', text_auto=True, color='Estado',
                              labels={'Cantidad': 'Nro. Casos', 'Estado': 'Estado Actual'})  # Mejora
            st.plotly_chart(fig_flujo, use_container_width=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

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
        st.markdown(f"## Análisis Regional: **{dep}**")
        
    total = len(df_r)
    if total > 0:
        tasa = (df_r['es_anormal'].sum()/total)*100
        tiempo = df_r['tiempo_atencion_dias'].mean()
        target_r = df_r[(df_r['sexo']=='FEMENINO') & (df_r['edad'].between(40,69))]
        intensidad_r = (target_r['es_atendido'].sum() / len(target_r)) * 100 if len(target_r) > 0 else 0
    else: tasa=tiempo=intensidad_r=0
    
    # KPIs Regionales en Tarjetas
    r1, r2, r3, r4 = st.columns(4)
    r1.markdown(kpi_card_html("Total Regional", f"{total:,}", "Casos"), unsafe_allow_html=True)
    r2.markdown(kpi_card_html("Intensidad (40-69)", f"{intensidad_r:.1f}%", "Local", "success"), unsafe_allow_html=True)
    r3.markdown(kpi_card_html("Tasa Anormalidad", f"{tasa:.1f}%", "Local", "warning"), unsafe_allow_html=True)
    r4.markdown(kpi_card_html("Tiempo Promedio", f"{tiempo:.1f} d", "Local"), unsafe_allow_html=True)
    
    st.write("")
    
    # Regional Dashboard Body
    c_left, c_right = st.columns([2, 1])
    
    with c_left:
        # PESTAÑAS DENTRO DE TARJETAS
        t1, t2, t3 = st.tabs(["📊 Evolución", "🩺 Mapa de Calor", "📄 Data"])
        
        with t1:
            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">Tendencias Locales</div>', unsafe_allow_html=True)
            if 'anio_mes' in df_r.columns:
                evo_dep = df_r.groupby('anio_mes').size().reset_index(name='Total')
                fig_ln = px.area(evo_dep, x='anio_mes', y='Total', markers=True,
                                 labels={'anio_mes': 'Mes', 'Total': 'Atenciones'})
                st.plotly_chart(style_chart(fig_ln), use_container_width=True)
            
            st.markdown("#### Estado de Atención")
            est_dep = df_r['estado'].value_counts().reset_index()
            est_dep.columns = ['Estado', 'Total']
            fig_bar = px.bar(est_dep, x='Estado', y='Total', color='Estado', text_auto=True,
                             labels={'Estado': 'Situación', 'Total': 'Cantidad'})
            st.plotly_chart(style_chart(fig_bar), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with t2:
            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">Correlación Edad vs Riesgo</div>', unsafe_allow_html=True)
            if not df_r.empty:
                ct = pd.crosstab(df_r['grupo_etario'], df_r['birads_categoria'])
                fig_hm = px.imshow(ct, text_auto=True, aspect="auto", color_continuous_scale="Reds",
                                   labels=dict(x="Categoría BIRADS", y="Grupo Etario", color="Casos"))
                st.plotly_chart(style_chart(fig_hm), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with t3:
            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">Registros Detallados</div>', unsafe_allow_html=True)
            st.dataframe(df_r[['fecha_solicitud','provincia','distrito','edad','birads_categoria','estado']], use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with c_right:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Top Distritos</div>', unsafe_allow_html=True)
        top_dist = df_r['distrito'].value_counts().head(10).reset_index()
        top_dist.columns = ['Distrito', 'Total']
        fig_d = px.bar(top_dist, x='Total', y='Distrito', orientation='h', text_auto=True,
                       labels={'Total': 'Atenciones', 'Distrito': 'Jurisdicción'})
        st.plotly_chart(style_chart(fig_d), use_container_width=True)
        
        st.markdown('<div class="card-title" style="margin-top:20px">Etnia Local</div>', unsafe_allow_html=True)
        fig_et = px.pie(df_r, names='etnia', hole=0.5)
        fig_et.update_layout(showlegend=False, height=200)
        st.plotly_chart(style_chart(fig_et), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# --- CONTROLADOR ---
if st.session_state["app_state"] == "HOME":
    render_home()
elif st.session_state["app_state"] == "DASHBOARD":
    render_dashboard()
elif st.session_state["app_state"] == "REGIONAL":
    render_regional()