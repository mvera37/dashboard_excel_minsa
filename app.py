import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go
import os
import json
import warnings
import re
from datetime import date

# --- CONFIGURACIÓN ---
warnings.filterwarnings("ignore")
st.set_page_config(page_title="DITEL - Portal BI", page_icon="🇵🇪", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    .stApp { background-color: #F8FAFC; font-family: 'Inter', sans-serif; }
    
    /* === ESTILOS LANDING PAGE === */
    .landing-header { text-align: center; margin-top: 40px; margin-bottom: 20px; }
    .landing-tag {
        background-color: #DBEAFE; color: #1E40AF; padding: 6px 16px; 
        border-radius: 20px; font-weight: 700; font-size: 0.8rem; 
        text-transform: uppercase; display: inline-block; letter-spacing: 0.05em;
    }
    .landing-title { font-size: 4rem; font-weight: 800; color: #0F172A; line-height: 1.1; margin-top: 20px; }
    .landing-subtitle { font-size: 1.2rem; color: #475569; margin-top: 20px; margin-bottom: 40px; line-height: 1.6; }
    .landing-footer {
        background-color: #0F172A; color: #94A3B8; padding: 60px 40px; margin-top: 80px;
        border-radius: 20px 20px 0 0; font-size: 0.9rem;
    }
    .footer-title { color: white; font-weight: 700; margin-bottom: 15px; font-size: 1rem; }
    
    /* === ESTILOS DASHBOARD === */
    .kpi-card {
        background-color: white; border-radius: 12px; padding: 20px 24px;
        border: 1px solid #E2E8F0; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        margin-bottom: 16px; height: 100%; display: flex; flex-direction: column; justify-content: center;
    }
    .kpi-val { font-size: 2rem; font-weight: 800; color: #0F172A; line-height: 1.1; margin-bottom: 8px; }
    .kpi-lbl { font-size: 0.7rem; color: #64748B; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
    .kpi-sub { font-size: 0.8rem; font-weight: 500; color: #94A3B8; }
    
    /* Contenedores de Gráficos */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: white; border-radius: 16px !important;
        border: 1px solid #E2E8F0 !important; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        padding: 20px !important; margin-bottom: 20px;
    }
    .chart-title {
        font-size: 0.95rem; font-weight: 700; color: #334155; margin-bottom: 15px;
        display: flex; align-items: center; gap: 8px; text-transform: uppercase; letter-spacing: 0.02em;
    }
    
    /* Botones Landing */
    div.stButton > button:first-child {
        width: 100%; border-radius: 8px; font-weight: 600; padding: 0.5rem 1rem;
    }
    
    /* Títulos Sidebar */
    .sidebar-section-title {
        font-size: 0.85rem; font-weight: 700; color: #1E40AF; text-transform: uppercase; 
        letter-spacing: 0.05em; margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid #DBEAFE; padding-bottom: 5px;
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

        if 'departamento' in df.columns:
            df['departamento'] = df['departamento'].astype(str).str.strip().str.upper()
            df['departamento'] = df['departamento'].replace({
                'LIMA METROPOLITANA': 'LIMA', 'LIMA REGION': 'LIMA',
                'LIMA PROVINCIAS': 'LIMA', 'GOBIERNO REGIONAL DE LIMA': 'LIMA'
            })

        if 'estado' in df.columns:
            df['estado'] = df['estado'].astype(str).str.strip().str.upper()
            macro_map = {
                'PENDIENTE': 'En Proceso', 'VALIDADO': 'En Proceso', 
                'APROBADO': 'En Proceso', 'OBSERVADO': 'En Proceso',
                'ATENDIDO': 'Atendidos', 'DERIVADO': 'Atendidos',
                'ANULADO': 'Anulados', 'REVOCADO': 'Anulados'
            }
            df['macro_estado'] = df['estado'].map(macro_map).fillna('Otros')

        if 'fecha_solicitud' in df.columns:
            df['fecha_solicitud'] = pd.to_datetime(df['fecha_solicitud'])
            df = df[df['fecha_solicitud'].dt.year.isin([2025, 2026])]
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
    except: 
        return pd.DataFrame()

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

def kpi_gerencial(title, value, subtext, color="#0F172A", icon=""):
    bg_alert = "white"
    if color == "#EF4444": bg_alert = "#FEF2F2" 
    elif color == "#F59E0B": bg_alert = "#FFFBEB" 
    elif color == "#10B981": bg_alert = "#F0FDF4" 
    elif color == "#3B82F6": bg_alert = "#EFF6FF" 
    
    return f"""
    <div style="background-color: {bg_alert}; border-radius: 12px; padding: 20px 24px;
                border: 1px solid #E2E8F0; box-shadow: 0 2px 4px rgba(0,0,0,0.02); height: 100%;">
        <div style="font-size: 0.75rem; color: #64748B; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">{title}</div>
        <div style="font-size: 2.2rem; font-weight: 800; color: {color}; line-height: 1.1; margin-bottom: 6px;">{icon} {value}</div>
        <div style="font-size: 0.8rem; font-weight: 600; color: #94A3B8;">{subtext}</div>
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
    else: 
        intensidad=tasa=prom=atend=anul=tiempo=dep=0

    r1 = st.columns(4)
    datos_r1 = [
        (f"{total:,.0f}", "Solicitudes", "Total"),
        (f"{intensidad:.1f}%", "Intensidad", "40-69 años"),
        (f"{tasa:.1f}%", "Anormalidad", "BIRADS 3-5"),
        (f"{prom:.0f}", "Promedio Diario", "Atenciones")
    ]
    for col, (val, tit, sub) in zip(r1, datos_r1):
        with col: st.markdown(kpi_html(val, tit, sub), unsafe_allow_html=True)

    r2 = st.columns(4)
    datos_r2 = [
        (f"{atend:.1f}%", "% Atendidas", "Efectividad"),
        (f"{anul:.1f}%", "% Anuladas", "Calidad Operativa"),
        (f"{tiempo:.1f} d", "Tiempo Promedio", "Desde solicitud"),
        (f"{dep}", "Deptos Activos", "Cobertura Nacional")
    ]
    for col, (val, tit, sub) in zip(r2, datos_r2):
        with col: st.markdown(kpi_html(val, tit, sub), unsafe_allow_html=True)
    
    st.write("")

def mostrar_seccion_gerencial(df_target, titulo):
    st.divider()
    st.markdown(f"### {titulo}")
    
    safe_key = str(hash(titulo))
    
    total = len(df_target)
    if total > 0:
        atendidos = len(df_target[df_target['estado'] == 'ATENDIDO'])
        derivados = len(df_target[df_target['estado'] == 'DERIVADO'])
        observados = len(df_target[df_target['estado'] == 'OBSERVADO'])
        anulados_rev = len(df_target[df_target['estado'].isin(['ANULADO', 'REVOCADO'])])
        
        val_procesable = total - anulados_rev
        ieo = (atendidos / val_procesable) * 100 if val_procesable > 0 else 0
        tasa_resolucion = (atendidos / (atendidos + derivados)) * 100 if (atendidos + derivados) > 0 else 0
        pct_derivados = (derivados / total) * 100
        pct_observados = (observados / total) * 100

        r1_g, r2_g, r3_g, r4_g = st.columns(4)
        with r1_g: st.markdown(kpi_gerencial("Índice Eficiencia Operativa", f"{ieo:.1f}%", "Eficiencia s/ procesables", "#10B981", "⚡"), unsafe_allow_html=True)
        with r2_g: st.markdown(kpi_gerencial("% Observados (Calidad)", f"{pct_observados:.1f}%", "Exceso de rechazos" if pct_observados>10 else "Normal", "#EF4444" if pct_observados>10 else "#0F172A", "⚠️"), unsafe_allow_html=True)
        with r3_g: st.markdown(kpi_gerencial("% Derivados", f"{pct_derivados:.1f}%", "Saturación local" if pct_derivados>20 else "Normal", "#F59E0B" if pct_derivados>20 else "#0F172A", "🏥"), unsafe_allow_html=True)
        with r4_g: st.markdown(kpi_gerencial("Tasa Resolución Clínica", f"{tasa_resolucion:.1f}%", "Atendidos vs Derivados", "#2563EB", "🩺"), unsafe_allow_html=True)
        
        st.write("")
        col_trend, col_nums = st.columns([3, 1])
        
        with col_trend:
            with st.container(border=True):
                st.markdown('<div class="chart-title">📈 Tendencia Operativa Mensual</div>', unsafe_allow_html=True)
                if 'anio_mes' in df_target.columns and 'macro_estado' in df_target.columns:
                    trend = df_target.groupby(['anio_mes', 'macro_estado']).size().reset_index(name='Total')
                    fig_trend_ger = px.area(trend, x='anio_mes', y='Total', color='macro_estado',
                                       color_discrete_map={'En Proceso': '#3B82F6', 'Atendidos': '#10B981', 'Anulados': '#EF4444'})
                    st.plotly_chart(style_chart(fig_trend_ger), use_container_width=True, key=f"trend_ger_{safe_key}")
                    
        with col_nums:
            tot_atendidos = len(df_target[df_target['macro_estado'] == 'Atendidos'])
            tot_anulados = len(df_target[df_target['macro_estado'] == 'Anulados'])
            tot_proceso = len(df_target[df_target['macro_estado'] == 'En Proceso'])
            
            st.markdown(kpi_gerencial("✅ Total Atendidos", f"{tot_atendidos:,.0f}", "Atendidos y Derivados", "#10B981"), unsafe_allow_html=True)
            st.write("")
            st.markdown(kpi_gerencial("⏳ Total En Proceso", f"{tot_proceso:,.0f}", "Pendientes y Observados", "#3B82F6"), unsafe_allow_html=True)
            st.write("")
            st.markdown(kpi_gerencial("❌ Total Anulados", f"{tot_anulados:,.0f}", "Anulados y Revocados", "#EF4444"), unsafe_allow_html=True)

        if 'nombre_eess_origen' in df_target.columns:
            st.write("")
            with st.container(border=True):
                tab_ip1, tab_ip2 = st.tabs(["⚠️ Calidad (% Observados)", "🐢 Cuellos de Botella (Tiempo Prom.)"])
                
                with tab_ip1:
                    st.markdown('<div class="chart-title">⚠️ Top 10 IPRESS: Problemas de Calidad (% Observados)</div>', unsafe_allow_html=True)
                    ipress_cal = df_target.groupby('nombre_eess_origen').agg(
                        Total=('estado', 'count'),
                        Obs=('estado', lambda x: (x == 'OBSERVADO').sum())
                    ).reset_index()
                    ipress_cal = ipress_cal[ipress_cal['Total'] > 5]
                    ipress_cal['% Observado'] = (ipress_cal['Obs'] / ipress_cal['Total']) * 100
                    top_obs = ipress_cal.sort_values('% Observado', ascending=False).head(10)

                    if not top_obs.empty:
                        fig_obs_ger = px.bar(
                            top_obs,
                            x='% Observado',
                            y='nombre_eess_origen',
                            orientation='h',
                            color='% Observado',
                            color_continuous_scale='Reds',
                            text_auto='.1f'
                        )
                        fig_obs_ger.update_traces(textposition='outside')
                        st.plotly_chart(style_chart(fig_obs_ger), use_container_width=True, key=f"obs_ger_{safe_key}")
                    else:
                        st.info("No hay suficientes datos.")

                with tab_ip2:
                    st.markdown('<div class="chart-title">🐢 Top 10 IPRESS: Cuellos de Botella (Tiempo Promedio)</div>', unsafe_allow_html=True)
                    if 'tiempo_atencion_dias' in df_target.columns:
                        ipress_tpo = df_target.groupby('nombre_eess_origen').agg(
                            Total=('estado', 'count'),
                            T_Prom=('tiempo_atencion_dias', 'mean')
                        ).reset_index().dropna()
                        ipress_tpo = ipress_tpo[ipress_tpo['Total'] > 5]
                        top_tpo = ipress_tpo.sort_values('T_Prom', ascending=False).head(10)

                        if not top_tpo.empty:
                            fig_tpo_ger = px.bar(
                                top_tpo,
                                x='T_Prom',
                                y='nombre_eess_origen',
                                orientation='h',
                                color='T_Prom',
                                color_continuous_scale='Oranges',
                                text_auto='.1f',
                                labels={'T_Prom': 'Días Promedio', 'nombre_eess_origen': 'EESS Origen'}
                            )
                            fig_tpo_ger.update_traces(textposition='outside')
                            st.plotly_chart(style_chart(fig_tpo_ger), use_container_width=True, key=f"tpo_ger_{safe_key}")
                        else:
                            st.info("No hay suficientes datos.")
                    else:
                        st.warning("No se encontró 'tiempo_atencion_dias'.")

            with st.container(border=True):
                st.markdown('<div class="chart-title">🔍 Diagnóstico Detallado por IPRESS (Origen)</div>', unsafe_allow_html=True)
                diag = df_target.groupby('nombre_eess_origen').agg(
                    Total=('estado', 'count'), Atendidos=('estado', lambda x: (x == 'ATENDIDO').sum()),
                    Observados=('estado', lambda x: (x == 'OBSERVADO').sum()), Derivados=('estado', lambda x: (x == 'DERIVADO').sum()),
                    T_Prom_Dias=('tiempo_atencion_dias', 'mean')
                ).reset_index()
                
                diag['% Atendidos'] = (diag['Atendidos'] / diag['Total']) * 100
                diag['% Observados'] = (diag['Observados'] / diag['Total']) * 100
                diag['% Derivados'] = (diag['Derivados'] / diag['Total']) * 100
                diag = diag.sort_values('Total', ascending=False)
                
                st.dataframe(
                    diag,
                    column_config={
                        "nombre_eess_origen": st.column_config.TextColumn("IPRESS Origen", width="large"),
                        "Total": st.column_config.NumberColumn("Total", format="%d"),
                        "% Atendidos": st.column_config.ProgressColumn("% Efectividad", min_value=0, max_value=100, format="%.1f%%"),
                        "% Observados": st.column_config.NumberColumn("% Observados", format="%.1f%%"),
                        "% Derivados": st.column_config.NumberColumn("% Derivados", format="%.1f%%"),
                        "T_Prom_Dias": st.column_config.NumberColumn("Tiempo Prom. (Días)", format="%.1f")
                    }, use_container_width=True, hide_index=True
                )

# --- CONTROLADOR GLOBAL DE FILTROS ---
def render_sidebar_filters(df_data):
    with st.sidebar:
        if st.session_state["app_state"] == "CONVENIO":
            st.header("Gestión 2025")
            if st.button("⬅️ Volver al Portal"):
                st.session_state["app_state"] = "HOME"
                st.rerun()
            st.info("Visualización exclusiva del Convenio de Gestión.")
            return df_data, "CONVENIO"
        
        else:
            fecha_txt = "N/A"
            if 'fecha_solicitud' in df_data.columns and not df_data.empty:
                f_max = df_data['fecha_solicitud'].max()
                if pd.notnull(f_max): fecha_txt = f_max.strftime("%d/%m/%Y")
            
            st.markdown(f"""
                <div style="background-color:#EFF6FF; border:1px solid #BFDBFE; color:#1E40AF; 
                            padding:10px; border-radius:8px; text-align:center; margin-bottom:20px;">
                    <small style="display:block; font-weight:600; margin-bottom:4px;">Última Actualización BD</small>
                    <span style="font-size:1.1rem; font-weight:800;">{fecha_txt}</span>
                </div>
            """, unsafe_allow_html=True)
            
            st.header("Navegación")
            if st.button("🏠 Inicio"): st.session_state["app_state"] = "HOME"; st.rerun()
            if st.button("📊 Dashboard General"): st.session_state["app_state"] = "DASHBOARD"; st.rerun()
            if st.button("📋 Datos Plan 2025-2026"): st.session_state["app_state"] = "PLAN_2025"; st.rerun()
            
            st.markdown("---")
            
            if st.session_state["app_state"] in ["DASHBOARD", "REGIONAL", "PLAN_2025"]:
                df_f = df_data.copy()

                st.markdown('<div class="sidebar-section-title">🩺 Especialidad</div>', unsafe_allow_html=True)
                opts_srv = ["TODOS"] + sorted(df_f['tipo_servicio'].unique()) if 'tipo_servicio' in df_f.columns else ["TODOS"]
                sel_srv = st.selectbox("Seleccione Especialidad", opts_srv, index=opts_srv.index("MAMOGRAFIA") if "MAMOGRAFIA" in opts_srv else 0, label_visibility="collapsed")
                if sel_srv != "TODOS": df_f = df_f[df_f['tipo_servicio'] == sel_srv]

                st.markdown('<div class="sidebar-section-title">📅 Filtrado Temporal</div>', unsafe_allow_html=True)
                
                modo_fecha = st.radio("Método de búsqueda:", ["Por Año / Mes", "Por Calendario (Específico / Rango)"])
                
                if modo_fecha == "Por Año / Mes":
                    c_year, c_month = st.columns(2)
                    with c_year:
                        years_disp = [2025, 2026]
                        sel_year = st.selectbox("Año", years_disp)
                        df_f = df_f[df_f['fecha_solicitud'].dt.year == sel_year]
                        
                    with c_month:
                        meses_orden = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
                        opts_mes = ["Todos"] + [m for m in meses_orden if m in df_f['nombre_mes'].unique()]
                        sel_mes = st.selectbox("Mes", opts_mes)
                        if sel_mes != "Todos": 
                            df_f = df_f[df_f['nombre_mes'] == sel_mes]
                            
                elif modo_fecha == "Por Calendario (Específico / Rango)":
                    if not df_data.empty and 'fecha_solicitud' in df_data.columns:
                        min_dt = df_data['fecha_solicitud'].min().date()
                        max_dt_data = df_data['fecha_solicitud'].max().date()
                    else:
                        min_dt = date(2025, 1, 1)
                        max_dt_data = date(2026, 12, 31)

                    max_dt = max(max_dt_data, date(2026, 12, 31))

                    modo_cal = st.radio("Tipo de selección:", ["Rango", "Fecha específica"], horizontal=True)

                    if modo_cal == "Rango":
                        val_rango = st.date_input(
                            "Seleccione Rango de Fechas",
                            value=(min_dt, max_dt_data),
                            min_value=min_dt,
                            max_value=max_dt,
                            format="DD/MM/YYYY"
                        )
                        if isinstance(val_rango, tuple) and len(val_rango) == 2:
                            fecha_ini, fecha_fin = val_rango
                            df_f = df_f[
                                (df_f['fecha_solicitud'].dt.date >= fecha_ini) &
                                (df_f['fecha_solicitud'].dt.date <= fecha_fin)
                            ]
                    else:
                        val_fecha = st.date_input(
                            "Seleccione Fecha",
                            value=max_dt_data,
                            min_value=min_dt,
                            max_value=max_dt,
                            format="DD/MM/YYYY"
                        )
                        df_f = df_f[df_f['fecha_solicitud'].dt.date == val_fecha]

                st.markdown('<div class="sidebar-section-title">🏥 Institución</div>', unsafe_allow_html=True)
                if 'nombre_eess_origen' in df_f.columns:
                    opts_eess = ["Todas las IPRESS"] + sorted(list(df_f['nombre_eess_origen'].dropna().astype(str).unique()))
                    sel_eess = st.selectbox("Filtrar por Origen", opts_eess, label_visibility="collapsed")
                    if sel_eess != "Todas las IPRESS": df_f = df_f[df_f['nombre_eess_origen'] == sel_eess]

                return df_f, sel_srv
            
            return df_data, "MAMOGRAFIA"
        # --- VISTA 1: HOME ---
def render_home():
    st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; padding: 10px 0;">
            <div style="font-weight:800; font-size:1.2rem; color:#0F172A;">
                <span style="color:#2563EB;">🛡️</span> DITEL-MINSA <br>
                <span style="font-size:0.7rem; color:#64748B; font-weight:500;">DIRECCIÓN DE TELEMEDICINA</span>
            </div>
            <div style="display:flex; gap:20px; font-size:0.9rem; font-weight:500; color:#475569;">
                <span>Inicio</span>
                <span>Recursos</span>
                <span>Soporte</span>
                <span style="color:#2563EB; font-weight:700;">Portal Médico</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 6, 1])
    with c2:
        st.markdown("""
            <div class="landing-header">
                <div class="landing-tag">📡 DITEL - MINSA | SALUD DIGITAL</div>
                <div class="landing-title">
                    Gestión de Información<br>en <span style="color:#2563EB">Telemedicina</span>
                </div>
                <div class="landing-subtitle">
                    Consolidación, trazabilidad y monitoreo para una atención oportuna y
                    eficiente en el Sistema Nacional de Salud.
                </div>
            </div>
        """, unsafe_allow_html=True)

        c_spacer_izq, col_btn_1, col_btn_2, col_btn_3, c_spacer_der = st.columns([0.5, 3, 3, 3, 0.5], gap="small")
        with col_btn_1:
            st.link_button("Tableros de gestión - DITEL 🔗", url="https://lookerstudio.google.com/u/1/reporting/e4705887-6f1e-450a-9c15-425fcb4d5e59/page/p_zgln1rvisd", type="primary", use_container_width=True)
        with col_btn_2:
            if st.button("Teleapoyo al Diagnóstico 📊", use_container_width=True): st.session_state["app_state"] = "DASHBOARD"; st.rerun()
        with col_btn_3:
            if st.button("Convenio Gestión 2025 🤝", use_container_width=True): st.session_state["app_state"] = "CONVENIO"; st.rerun()

    st.markdown("""
        <div class="landing-footer">
            <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:40px;">
                <div style="flex:1; min-width:250px;">
                    <div class="footer-title">🛡️ DITEL-MINSA</div>
                    <p>Dirección de Telemedicina.<br>Trabajando para digitalizar la salud del Perú.</p>
                </div>
                <div style="flex:1; min-width:200px;">
                    <div class="footer-title">Recursos</div>
                    <p>Normatividad<br>Guías Técnicas<br>Formatos DIC<br>Directorio Nacional</p>
                </div>
                <div style="flex:1; min-width:250px;">
                    <div class="footer-title">Contacto</div>
                    <p>📍 Av. Salaverry 801, Jesús María, Lima, Perú</p>
                    <p>📞 (01) 315-6600</p>
                    <p>✉️ soporte@minsa.gob.pe</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- VISTA 2: DASHBOARD GENERAL ---
def render_dashboard(df_filtered, srv_name):
    st.markdown(f"### 📊 Panorama Ejecutivo: {srv_name}")
    mostrar_kpis_completos(df_filtered)

    col_L, col_R = st.columns([1.5, 1])
    with col_L:
        with st.container(border=True):
            tab_map1, tab_map2 = st.tabs(["🗺️ Volumen General", "🚨 Alerta Riesgo Técnico (% BI-RADS 0)"])
            
            with tab_map1:
                st.markdown('<div class="chart-title">Mapa de Solicitudes Atendidas</div>', unsafe_allow_html=True)
                if geojson_peru and 'departamento' in df_filtered.columns and not df_filtered.empty:
                    map_data = df_filtered.groupby('departamento').size().reset_index(name='Total')
                    fig_map_nac = px.choropleth_mapbox(map_data, geojson=geojson_peru, locations='departamento', featureidkey="properties.NOMBDEP",
                                               color="Total", color_continuous_scale="Blues", mapbox_style="carto-positron",
                                               zoom=3.8, center={"lat": -9.19, "lon": -75.01}, opacity=0.9)
                    fig_map_nac.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=400)
                    evt = st.plotly_chart(fig_map_nac, use_container_width=True, on_select="rerun", key="mapa_nacional_vol")
                    if evt and evt['selection']['points']:
                        st.session_state["selected_dept"] = evt['selection']['points'][0]['location']
                        st.session_state["app_state"] = "REGIONAL"; st.rerun()
                else: 
                    st.warning("Sin datos geográficos.")
            
            with tab_map2:
                st.markdown('<div class="chart-title">Concentración de Casos Incompletos (Riesgo)</div>', unsafe_allow_html=True)
                if geojson_peru and 'departamento' in df_filtered.columns and 'birads_categoria' in df_filtered.columns and not df_filtered.empty:
                    map_b0 = df_filtered.groupby('departamento').apply(
                        lambda x: pd.Series({
                            'Total': len(x),
                            'B0': len(x[x['birads_categoria'].astype(str).str.contains('0 -', na=False)])
                        })
                    ).reset_index()
                    map_b0 = map_b0[map_b0['Total'] > 0]
                    map_b0['% BI-RADS 0'] = (map_b0['B0'] / map_b0['Total']) * 100
                    map_b0['% BI-RADS 0'] = map_b0['% BI-RADS 0'].round(1)
                    
                    fig_map_b0 = px.choropleth_mapbox(map_b0, geojson=geojson_peru, locations='departamento', featureidkey="properties.NOMBDEP",
                                               color="% BI-RADS 0", color_continuous_scale="Reds", mapbox_style="carto-positron",
                                               zoom=3.8, center={"lat": -9.19, "lon": -75.01}, opacity=0.9,
                                               hover_data={"Total": True, "B0": True})
                    fig_map_b0.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=400)
                    evt_b0 = st.plotly_chart(fig_map_b0, use_container_width=True, on_select="rerun", key="mapa_nacional_b0")
                    if evt_b0 and evt_b0['selection']['points']:
                        st.session_state["selected_dept"] = evt_b0['selection']['points'][0]['location']
                        st.session_state["app_state"] = "REGIONAL"; st.rerun()
                else: 
                    st.warning("Sin datos de BI-RADS para mapear.")

        with st.container(border=True):
            tab_rank1, tab_rank2 = st.tabs(["📊 Ranking Departamental (Volumen)", "🚨 Errores Técnicos (% BI-RADS 0)"])
    
            with tab_rank1:
                if 'departamento' in df_filtered.columns:
                    rank = df_filtered['departamento'].value_counts().reset_index()
                    rank.columns = ['Departamento', 'Atenciones']
                    rank = rank.sort_values('Atenciones', ascending=False).head(10)
                    fig_rank_nac = px.bar(rank.head(10), x='Departamento', y='Atenciones', color='Atenciones', color_continuous_scale='Blues')
                    st.plotly_chart(style_chart(fig_rank_nac), use_container_width=True, key="rank_nacional_v2")

            with tab_rank2:
                if 'departamento' in df_filtered.columns and 'birads_categoria' in df_filtered.columns:
                    dep_b0 = df_filtered.groupby('departamento').apply(
                    lambda x: (x['birads_categoria'].astype(str).str.contains('0 -').sum() / len(x)) * 100
                    ).reset_index(name='% B0')
                    dep_b0 = dep_b0.sort_values('% B0', ascending=False).head(10)
                    fig_dep_b0 = px.bar(dep_b0, x='% B0', y='departamento', orientation='h', color='% B0', color_continuous_scale='Reds')
                    st.plotly_chart(style_chart(fig_dep_b0), use_container_width=True, key="rank_dep_b0")

    with col_R:
        tabs = st.tabs(["📈 Temporal", "👥 Demografía", "🩺 Clínico", "⚙️ Flujo", "🚨 Análisis BI-RADS 0"])
        
        with tabs[0]: 
            with st.container(border=True):
                st.markdown('<div class="chart-title">📅 Evolución Mensual</div>', unsafe_allow_html=True)
                if 'anio_mes' in df_filtered.columns:
                    evo = df_filtered.groupby('anio_mes').size().reset_index(name='Total')
                    st.plotly_chart(style_chart(px.area(evo, x='anio_mes', y='Total', labels={'anio_mes': 'Mes', 'Total': 'Atenciones'})), use_container_width=True, key="nac_evo")
            with st.container(border=True):
                st.markdown('<div class="chart-title">⏱️ Tiempo Promedio</div>', unsafe_allow_html=True)
                if 'anio_mes' in df_filtered.columns:
                    evo_tm = df_filtered.groupby('anio_mes')['tiempo_atencion_dias'].mean().reset_index()
                    fig_tm = px.line(evo_tm, x='anio_mes', y='tiempo_atencion_dias', markers=True, labels={'anio_mes': 'Mes', 'tiempo_atencion_dias': 'Días Promedio'})
                    fig_tm.update_traces(line_color='#F59E0B')
                    st.plotly_chart(style_chart(fig_tm), use_container_width=True, key="nac_time")

        with tabs[1]: 
            with st.container(border=True):
                st.markdown('<div class="chart-title">🎂 Rango de Edades</div>', unsafe_allow_html=True)
                if 'grupo_etario' in df_filtered.columns:
                    age = df_filtered['grupo_etario'].value_counts().reset_index()
                    st.plotly_chart(style_chart(px.bar(age, x='grupo_etario', y='count', color='count', color_continuous_scale='Teal', labels={'grupo_etario': 'Grupo Etario', 'count': 'Pacientes'})), use_container_width=True, key="nac_age")
            with st.container(border=True):
                st.markdown('<div class="chart-title">🌎 Origen (Extranjeros)</div>', unsafe_allow_html=True)
                if 'nacionalidad' in df_filtered.columns:
                    nac = df_filtered['nacionalidad'].value_counts().reset_index()
                    nac.columns = ['Pais', 'Cantidad']
                    nac_fil = nac[~nac['Pais'].str.contains('PERU', case=False)] if len(nac)>1 else nac
                    if not nac_fil.empty:
                        st.plotly_chart(style_chart(px.treemap(nac_fil, path=['Pais'], values='Cantidad', color='Cantidad', color_continuous_scale='Mint', labels={'labels': 'País', 'value': 'Total'})), use_container_width=True, key="nac_nat")
                    else: 
                        st.info("Solo Perú.")

        with tabs[2]: 
            with st.container(border=True):
                st.markdown('<div class="chart-title">🩺 Distribución BI-RADS General</div>', unsafe_allow_html=True)
                if 'birads_categoria' in df_filtered.columns:
                    bi = df_filtered['birads_categoria'].value_counts().reset_index()
                    st.plotly_chart(style_chart(px.bar(bi, x='birads_categoria', y='count', color='birads_categoria', labels={'birads_categoria': 'Categoría', 'count': 'Casos'})), use_container_width=True, key="nac_birads")

        with tabs[3]: 
            with st.container(border=True):
                st.markdown('<div class="chart-title">⚙️ Estado Actual</div>', unsafe_allow_html=True)
                fl = df_filtered['estado'].value_counts().reset_index()
                st.plotly_chart(style_chart(px.bar(fl, x='count', y='estado', orientation='h', color='estado')), use_container_width=True, key="nac_state")

        with tabs[4]:
            st.markdown("### 🚨 Calidad Técnica Operativa")
            
            with st.expander("📖 Sobre BI-RADS 0 (Interpretación)", expanded=False):
                st.markdown("""
                El **BI-RADS 0** indica un estudio *incompleto*. Requiere evaluación adicional (ecografía o placas previas).
                **Problema Operativo:** Una tasa inusualmente alta (>10%) suele deberse a deficiencias técnicas locales: mala compresión, mal posicionamiento, o error al enviar la imagen DICOM al servidor PACS.
                """)

            birads_col = 'birads_categoria'
            total_casos = len(df_filtered)
            
            if birads_col in df_filtered.columns and total_casos > 0:
                df_b0 = df_filtered[df_filtered[birads_col].astype(str).str.contains('0 -', na=False)]
                total_b0 = len(df_b0)
                tasa_b0 = (total_b0 / total_casos) * 100
                t_prom_0 = df_b0['tiempo_atencion_dias'].mean() if 'tiempo_atencion_dias' in df_b0.columns else 0
                
                if tasa_b0 > 10: st.error(f"🚨 **Riesgo Técnico Detectado:** La tasa nacional de exámenes incompletos es **{tasa_b0:.1f}%**. Revisar el top de establecimientos críticos.")
                elif tasa_b0 > 5: st.warning(f"⚠️ **Atención:** Tasa BI-RADS 0 en **{tasa_b0:.1f}%**. Nivel moderado de rechazos técnicos.")
                else: st.success(f"✅ **Óptimo:** Tasa BI-RADS 0 controlada (**{tasa_b0:.1f}%**).")

                c1_b, c2_b, c3_b = st.columns(3)
                with c1_b: st.metric("Volumen Total", f"{total_b0} casos")
                with c2_b: st.metric("Tasa Nacional", f"{tasa_b0:.1f}%")
                with c3_b: st.metric("Tiempo Promedio", f"{t_prom_0:.1f} d" if pd.notna(t_prom_0) else "0 d")

                st.write("")
                with st.container(border=True):
                    st.markdown('<div class="chart-title">🚨 Top 10 IPRESS: Concentración de Errores Técnicos (% BI-RADS 0)</div>', unsafe_allow_html=True)
                    if 'nombre_eess_origen' in df_filtered.columns:
                        ipr_b = df_filtered.groupby('nombre_eess_origen').agg(
                            Total=('estado', 'count'), B0=(birads_col, lambda x: x.astype(str).str.contains('0 -').sum())
                        ).reset_index()
                        ipr_b = ipr_b[ipr_b['Total'] > 10] 
                        ipr_b['% B0'] = (ipr_b['B0'] / ipr_b['Total']) * 100
                        top_b0 = ipr_b.sort_values('% B0', ascending=False).head(10)
                        
                        if not top_b0.empty:
                            st.plotly_chart(style_chart(px.bar(top_b0, x='% B0', y='nombre_eess_origen', orientation='h', color='% B0', color_continuous_scale='Reds', text_auto='.1f')), use_container_width=True, key="nac_birads_rank_b0_v2")
                        else:
                            st.info("No hay suficientes datos procesados para el ranking.")

    mostrar_seccion_gerencial(df_filtered, "🌟 Análisis Detallado Nacional")

# --- VISTA 3: REGIONAL ---
def render_regional(df_filtered_global):
    dep = st.session_state["selected_dept"]
    col_dep = 'departamento' if 'departamento' in df_master.columns else 'nombdep'
    
    df_r = df_filtered_global[df_filtered_global[col_dep] == dep].copy()
    
    c1, c2 = st.columns([1, 4])
    with c1: st.button("⬅️ Volver al Nacional", on_click=lambda: st.session_state.update(app_state="DASHBOARD", selected_dept=None))
    with c2: st.markdown(f"### Análisis Regional: {dep}")
    
    mostrar_kpis_completos(df_r)
    
    t1, t2, t3, t4 = st.tabs(["📊 Gestión Operativa", "🩺 Clínico & Demo", "🚨 Alerta BI-RADS 0", "📄 Data Nominal"])

    with t1:
        c_left, c_right = st.columns(2)
        with c_left:
            with st.container(border=True):
                st.markdown('<div class="chart-title">📈 Tendencias Locales</div>', unsafe_allow_html=True)
                if 'anio_mes' in df_r.columns:
                    evo_reg = df_r.groupby('anio_mes').size().reset_index(name='Total')
                    st.plotly_chart(style_chart(px.area(evo_reg, x='anio_mes', y='Total')), use_container_width=True, key="reg_evo_loc")
            with st.container(border=True):
                st.markdown('<div class="chart-title">⚙️ Estado Atención Local</div>', unsafe_allow_html=True)
                fl_reg = df_r['estado'].value_counts().reset_index()
                st.plotly_chart(style_chart(px.bar(fl_reg, x='count', y='estado', orientation='h', color='estado')), use_container_width=True, key="reg_fl_loc")
        with c_right:
            with st.container(border=True):
                st.markdown('<div class="chart-title">🏆 Top Distritos</div>', unsafe_allow_html=True)
                if 'distrito' in df_r.columns:
                    top_dis = df_r['distrito'].value_counts().head(10).reset_index()
                    st.plotly_chart(style_chart(px.bar(top_dis, x='count', y='distrito', orientation='h')), use_container_width=True, key="reg_dis_loc")

    with t2:
        c_left, c_right = st.columns(2)
        with c_left:
             with st.container(border=True):
                st.markdown('<div class="chart-title">🔥 Riesgo Clínico Local</div>', unsafe_allow_html=True)
                if 'grupo_etario' in df_r.columns and 'birads_categoria' in df_r.columns:
                    ct_reg = pd.crosstab(df_r['grupo_etario'], df_r['birads_categoria'])
                    st.plotly_chart(style_chart(px.imshow(ct_reg, aspect="auto", color_continuous_scale="Reds")), use_container_width=True, key="reg_bir_heat")
        with c_right:
            with st.container(border=True):
                st.markdown('<div class="chart-title">🧑‍🤝‍🧑 Etnia Local</div>', unsafe_allow_html=True)
                if 'etnia' in df_r.columns:
                    etn_reg = df_r['etnia'].value_counts().head(8).reset_index()
                    etn_reg.columns = ['Etnia', 'Cantidad']
                    st.plotly_chart(style_chart(px.pie(etn_reg, names='Etnia', values='Cantidad', hole=0.6)), use_container_width=True, key="reg_eth_pie")

    with t3:
        st.markdown(f"### 🚨 Riesgo Operativo: BI-RADS 0 en {dep}")
        birads_col = 'birads_categoria'
        total_casos_r = len(df_r)
        
        if birads_col in df_r.columns and total_casos_r > 0:
            df_b0_r = df_r[df_r[birads_col].astype(str).str.contains('0 -', na=False)]
            total_b0_r = len(df_b0_r)
            tasa_b0_r = (total_b0_r / total_casos_r) * 100
            
            c1_r, c2_r = st.columns(2)
            with c1_r: st.metric("Casos BI-RADS 0 Regionales", f"{total_b0_r} casos")
            with c2_r: st.metric("Tasa BI-RADS 0 Regional", f"{tasa_b0_r:.1f}%")
            
            if tasa_b0_r > 10: st.error("🚨 Brecha de capacitación técnica crítica detectada en los técnicos de esta región.")
            
            with st.container(border=True):
                st.markdown('<div class="chart-title">🏥 IPRESS Locales: Alerta BI-RADS 0</div>', unsafe_allow_html=True)
                if 'nombre_eess_origen' in df_r.columns:
                    ipr_b_r = df_r.groupby('nombre_eess_origen').agg(
                        Total=('estado', 'count'), B0=(birads_col, lambda x: x.astype(str).str.contains('0 -').sum())
                    ).reset_index()
                    ipr_b_r = ipr_b_r[ipr_b_r['Total'] > 0]
                    ipr_b_r['% B0'] = (ipr_b_r['B0'] / ipr_b_r['Total']) * 100
                    top_b0_r = ipr_b_r.sort_values('% B0', ascending=False).head(10)
                    if not top_b0_r.empty:
                        st.plotly_chart(style_chart(px.bar(top_b0_r, x='% B0', y='nombre_eess_origen', orientation='h', color='% B0', color_continuous_scale='Reds', text_auto='.1f')), use_container_width=True, key="reg_birads0_rank_v2")

    with t4:
        with st.container(border=True):
            st.markdown('<div class="chart-title">📄 Registro Nominal Regional</div>', unsafe_allow_html=True)
            cols_show = ['fecha_solicitud', 'provincia', 'distrito', 'nombre_eess_origen', 'edad', 'birads_categoria', 'estado']
            cols_final = [c for c in cols_show if c in df_r.columns]
            st.dataframe(df_r[cols_final], use_container_width=True)

    mostrar_seccion_gerencial(df_r, f"🌟 Análisis detallado - Región {dep}")

# --- VISTA 4: PLAN 2025-2026 ---
def render_plan_2025(df_data):
    st.markdown("### 📋 PLAN PARA LA IMPLEMENTACIÓN DE LA TELEMAMOGRAFÍA EN ESTABLECIMIENTOS PRIORIZADOS, PERIODO 2025-2026")
    st.markdown("Monitorización específica de atenciones (Estado: Atendido | Servicio: Mamografía).")
    st.markdown("---")

    mask_base = (
        (df_data['tipo_servicio'] == 'MAMOGRAFIA') &
        (df_data['estado'].astype(str).str.upper().str.contains("ATENDIDO"))
    )

    mapeo_consultante = {
        "CENTRO MATERNO INFANTIL RÍMAC": "CENTRO MATERNO INFANTIL RÍMAC",
        "HOSPITAL GENERAL DE HUACHO": "HOSPITAL GENERAL DE HUACHO",
        "CENTRO MATERNO INFANTIL JOSE CARLOS MARIATEGUI": "CENTRO MATERNO INFANTIL JOSE CARLOS MARIATEGUI",
        "C.S. MATERNO INFANTIL PACHACUTEC  PERU-COREA": "C.S. MATERNO INFANTIL PACHACUTEC  PERU-COREA",
        "HOSPITAL AMAZONICO - YARINACOCHA": "HOSPITAL AMAZONICO - YARINACOCHA",
        "CENTRO MATERNO INFANTIL EL PROGRESO": "CENTRO MATERNO INFANTIL EL PROGRESO",
        "SANTA ANITA": "SANTA ANITA",
        "CENTRO DE SALUD MATERNO INFANTIL MAGDALENA": "CENTRO DE SALUD MATERNO INFANTIL MAGDALENA",
        "HOSPITAL REGIONAL DOCENTE CAJAMARCA": "HOSPITAL REGIONAL DOCENTE CAJAMARCA",
        "QUILLABAMBA": "QUILLABAMBA",
        "HOSPITAL HIPOLITO UNANUE DE TACNA": "HOSPITAL HIPOLITO UNANUE DE TACNA",
        "DE APOYO MANUEL HIGA ARAKAKI": "DE APOYO MANUEL HIGA ARAKAKI",
        "HOSPITAL VICTOR RAMOS GUARDIA - HUARAZ": "HOSPITAL VICTOR RAMOS GUARDIA - HUARAZ",
        "TUPAC AMARU": "TUPAC AMARU",
        "HOSPITAL DE APOYO DE POMABAMBA ANTONIO CALDAS DOMINGUEZ": "HOSPITAL DE APOYO DE POMABAMBA ANTONIO CALDAS DOMINGUEZ",
        "HOSPITAL DE VENTANILLA": "HOSPITAL DE VENTANILLA",
        "JOSE LEONARDO ORTIZ": "JOSE LEONARDO ORTIZ",
        "HOSPITAL DE EMERGENCIAS CHALHUANCA": "HOSPITAL DE EMERGENCIAS CHALHUANCA",
        "HOSPITAL SANTA GEMA DE  YURIMAGUAS": "HOSPITAL SANTA GEMA DE  YURIMAGUAS",
        "HOSPITAL REGIONAL DOCENTE LAS MERCEDES": "HOSPITAL REGIONAL DOCENTE LAS MERCEDES",
        "HOSPITAL REGIONAL JOSE ALFREDO MENDOZA OLAVARRIA JAMO II-2": "HOSPITAL REGIONAL JOSE ALFREDO MENDOZA OLAVARRIA JAMO II-2",
        "HOSPITAL SAN JUAN DE MATUCANA": "HOSPITAL SAN JUAN DE MATUCANA",
        "BANDA SHILCAYO": "BANDA SHILCAYO",
        "HOSP. ROMAN EGOAVIL PANDO VILLA RICA": "HOSP. ROMAN EGOAVIL PANDO VILLA RICA",
        "HOSPITAL DE APOYO SAN FRANCISCO": "HOSPITAL DE APOYO SAN FRANCISCO",
        "HOSPITAL DEPARTAMENTAL DE HUANCAVELICA": "HOSPITAL DEPARTAMENTAL DE HUANCAVELICA",
        "HOSPITAL REGIONAL DE LORETO FELIPE SANTIAGO ARRIOLA IGLESIAS": "HOSPITAL REGIONAL DE LORETO FELIPE SANTIAGO ARRIOLA IGLESIAS",
        "HOSPITAL SANTA ROSA": "HOSPITAL SANTA ROSA",
        "NAC. DANIEL A. CARRION": "NAC. DANIEL A. CARRION"
    }
    
    diris_map = {
        "CENTRO MATERNO INFANTIL RÍMAC": "LIMA NORTE",
        "HOSPITAL GENERAL DE HUACHO": "LIMA REGIÓN",
        "CENTRO MATERNO INFANTIL JOSE CARLOS MARIATEGUI": "LIMA SUR",
        "C.S. MATERNO INFANTIL PACHACUTEC  PERU-COREA": "CALLAO",
        "HOSPITAL AMAZONICO - YARINACOCHA": "UCAYALI",
        "CENTRO MATERNO INFANTIL EL PROGRESO": "LIMA NORTE",
        "SANTA ANITA": "LIMA ESTE",
        "CENTRO DE SALUD MATERNO INFANTIL MAGDALENA": "LIMA CENTRO",
        "QUILLABAMBA": "CUSCO",
        "HOSPITAL REGIONAL DOCENTE CAJAMARCA": "CAJAMARCA",
        "HOSPITAL HIPOLITO UNANUE DE TACNA": "TACNA",
        "DE APOYO MANUEL HIGA ARAKAKI": "JUNIN",
        "TUPAC AMARU": "CUSCO",
        "HOSPITAL VICTOR RAMOS GUARDIA - HUARAZ": "LAMBAYEQUE",
        "JOSE LEONARDO ORTIZ": "ANCASH",
        "HOSPITAL DE VENTANILLA": "CALLAO",
        "HOSPITAL DE APOYO DE POMABAMBA ANTONIO CALDAS DOMINGUEZ": "ANCASH",
        "HOSPITAL DE EMERGENCIAS CHALHUANCA": "APURIMAC",
        "HOSPITAL SANTA GEMA DE  YURIMAGUAS": "LORETO",
        "HOSPITAL REGIONAL DOCENTE LAS MERCEDES": "TUMBES",
        "HOSPITAL REGIONAL JOSE ALFREDO MENDOZA OLAVARRIA JAMO II-2": "LAMBAYEQUE",
        "BANDA SHILCAYO": "SAN MARTIN",
        "HOSP. ROMAN EGOAVIL PANDO VILLA RICA": "PASCO",
        "HOSPITAL SAN JUAN DE MATUCANA": "LIMA REGIÓN",
        "HOSPITAL DE APOYO SAN FRANCISCO": "AYACUCHO",
        "HOSPITAL DEPARTAMENTAL DE HUANCAVELICA": "HUANCAVELICA",
        "HOSPITAL REGIONAL DE LORETO FELIPE SANTIAGO ARRIOLA IGLESIAS": "LORETO",
        "HOSPITAL SANTA ROSA": "MADRE DE DIOS",
        "NAC. DANIEL A. CARRION": "CALLAO"
    }

    nombres_bd_origen = list(mapeo_consultante.values())
    df_t1 = df_data[mask_base & df_data['nombre_eess_origen'].isin(nombres_bd_origen)].copy()

    st.subheader("Tabla 1: E.S. CONSULTANTE (ORIGEN)")
    if not df_t1.empty:
        t1_agrup = df_t1.groupby(['nombre_eess_origen', 'departamento']).size().reset_index(name='ATENCIONES')
        t1_agrup['DIRIS_CUSTOM'] = t1_agrup['nombre_eess_origen'].map(diris_map).fillna("-")
        
        t1_agrup = t1_agrup.sort_values('ATENCIONES', ascending=False)
        t1_agrup.reset_index(drop=True, inplace=True)
        t1_agrup.index = t1_agrup.index + 1
        t1_agrup.reset_index(inplace=True)
        t1_agrup.rename(columns={'index': 'N°', 'departamento': 'REGIÓN'}, inplace=True)
        
        t1_final_display = t1_agrup[['N°', 'nombre_eess_origen', 'DIRIS_CUSTOM', 'REGIÓN', 'ATENCIONES']]
        t1_final_display.columns = ['N°', 'E.S. CONSULTANTE', 'DIRIS / DIRESA/GERESA', 'REGIÓN', 'ATENCIONES']
        
        fila_total_1 = pd.DataFrame([['', 'TOTAL GENERAL', '', '', t1_final_display['ATENCIONES'].sum()]], columns=t1_final_display.columns)
        t1_final = pd.concat([t1_final_display, fila_total_1], ignore_index=True)

        st.dataframe(
            t1_final, 
            column_config={
                "N°": st.column_config.TextColumn(width="small"),
                "E.S. CONSULTANTE": st.column_config.TextColumn(width="large"),
                "DIRIS / DIRESA/GERESA": st.column_config.TextColumn(width="medium"),
                "REGIÓN": st.column_config.TextColumn(width="medium"),
                "ATENCIONES": st.column_config.ProgressColumn(
                    "ATENCIONES", format="%d", min_value=0, max_value=int(t1_agrup['ATENCIONES'].max())
                )
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Sin datos para Tabla 1.")

    st.divider()

    mapeo_consultor = {
        "INSTITUTO NACIONAL DE ENFERMEDADES NEOPLASICAS": "INSTITUTO NACIONAL DE ENFERMEDADES NEOPLASICAS",
        "MINSA MOVIL": "MINSA MOVIL",
        "HOSPITAL DE EMERGENCIAS VILLA EL SALVADOR": "HOSPITAL DE EMERGENCIAS VILLA EL SALVADOR",
        "INSTITUTO REGIONAL DE ENFERMEDADES NEOPLÁSICAS DEL CENTRO - IREN CENTRO": "INSTITUTO REGIONAL DE ENFERMEDADES NEOPLÁSICAS DEL CENTRO - IREN CENTRO",
        "HOSPITAL DE LIMA ESTE -VITARTE": "HOSPITAL DE LIMA ESTE -VITARTE",
        "REGIONAL DE ENFERMEDADES NEOPLASICAS - NORTE - DR. LUIS PINILLOS GANOZA": "REGIONAL DE ENFERMEDADES NEOPLASICAS - NORTE - DR. LUIS PINILLOS GANOZA",
        "HOSPITAL REGIONAL DE LORETO FELIPE SANTIAGO ARRIOLA IGLESIAS": "HOSPITAL REGIONAL DE LORETO FELIPE SANTIAGO ARRIOLA IGLESIAS",
        "INSTITUTO REGIONAL DE ENFERMEDADES NEOPLASICAS": "INSTITUTO REGIONAL DE ENFERMEDADES NEOPLASICAS",
        "HOSPITAL DE APOYO SANTA ROSA": "HOSPITAL DE APOYO SANTA ROSA",
        "HOSPITAL REGIONAL DE AYACUCHO MIGUEL ÁNGEL MARISCAL LLERENA": "HOSPITAL REGIONAL DE AYACUCHO MIGUEL ÁNGEL MARISCAL LLERENA"
    }
    nombres_bd_destino = list(mapeo_consultor.values())
    col_destino = 'nombre_eess_destino'
    
    st.subheader("Tabla 2: E.S. CONSULTOR (DESTINO)")
    if col_destino in df_data.columns:
        df_t2 = df_data[mask_base & df_data[col_destino].isin(nombres_bd_destino)].copy()
        if not df_t2.empty:
            t2_agrup = df_t2.groupby([col_destino]).size().reset_index(name='ATENCIONES')
            t2_agrup = t2_agrup.sort_values('ATENCIONES', ascending=False)
            t2_agrup.reset_index(drop=True, inplace=True)
            t2_agrup.index = t2_agrup.index + 1
            t2_agrup.reset_index(inplace=True)
            t2_agrup.rename(columns={'index': 'N°'}, inplace=True)
            t2_agrup.columns = ['N°', 'E.S. CONSULTOR', 'ATENCIONES']
            
            fila_total_2 = pd.DataFrame([['', 'TOTAL GENERAL', t2_agrup['ATENCIONES'].sum()]], columns=t2_agrup.columns)
            t2_final = pd.concat([t2_agrup, fila_total_2], ignore_index=True)
            
            st.dataframe(
                t2_final,
                column_config={
                    "N°": st.column_config.TextColumn(width="small"),
                    "E.S. CONSULTOR": st.column_config.TextColumn(width="large"),
                    "ATENCIONES": st.column_config.ProgressColumn(
                        "ATENCIONES", format="%d", min_value=0, max_value=int(t2_agrup['ATENCIONES'].max())
                    )
                },
                use_container_width=True, hide_index=True
            )
        else:
            st.warning("Sin datos para Tabla 2.")
    else:
        st.error(f"❌ Falta columna '{col_destino}'.")

    st.divider()

    st.subheader("Tabla 3: CLASIFICACIÓN BIRADS")
    df_t3 = df_data[mask_base].copy()

    if 'birads_raw' in df_t3.columns:
        def clean_birads_num(val):
            val_str = str(val).upper().strip()
            match = re.search(r'([0-6])', val_str)
            if match: return match.group(1)
            return "0"

        df_t3['birads_clean'] = df_t3['birads_raw'].apply(clean_birads_num)
        t3_agrup = df_t3.groupby('birads_clean').size().reset_index(name='ATENCIONES')

        ref_birads = pd.DataFrame({'birads_clean': ['0', '1', '2', '3', '4', '5', '6']})
        t3_final = pd.merge(ref_birads, t3_agrup, on='birads_clean', how='left').fillna(0)
        t3_final['ATENCIONES'] = t3_final['ATENCIONES'].astype(int)

        t3_final.columns = ['BIRADS', 'ATENCIONES']
        
        total_b = t3_final['ATENCIONES'].sum()
        fila_total_3 = pd.DataFrame([['TOTAL GENERAL', total_b]], columns=['BIRADS', 'ATENCIONES'])
        
        t3_display = pd.concat([t3_final, fila_total_3], ignore_index=True)

        st.dataframe(
            t3_display,
            column_config={
                "BIRADS": st.column_config.TextColumn(width="medium"),
                "ATENCIONES": st.column_config.NumberColumn(format="%d")
            },
            use_container_width=False, hide_index=True
        )
    else:
        st.error("No se encontró la columna de BIRADS para generar la Tabla 3.")

# --- VISTA 5: CONVENIO DE GESTIÓN ---
def render_convenio():
    st.markdown("### 🤝 Convenio de Gestión 2025")
    st.markdown("Selecciona una región resaltada en el mapa para acceder al reporte detallado.")
    
    links_region = {
        "JUNIN": "https://lookerstudio.google.com/reporting/2693ae3f-4b20-484a-9435-0a8fc527be6f",
        "PASCO": "https://lookerstudio.google.com/reporting/82c7f660-0815-48b2-85f1-be3fd7dd5684",
        "ICA": "https://lookerstudio.google.com/reporting/ce0133bb-4ace-4239-a678-462c9fd70bc6",
        "AYACUCHO": "https://lookerstudio.google.com/reporting/c884d81c-63a8-4c6c-bfe4-ab4bef5b3428",
        "APURIMAC": "https://lookerstudio.google.com/reporting/fd23f4a4-97e2-408f-b14f-c83a154ab808",
        "HUANCAVELICA": "https://lookerstudio.google.com/reporting/5c324461-8586-4644-98c3-f82860a3a40b"
    }

    if geojson_peru:
        regiones_activas = list(links_region.keys())
        map_rows = []
        for feature in geojson_peru['features']:
            dept_name = feature['properties']['NOMBDEP']
            dept_key = str(dept_name).upper().replace("Í", "I") 
            
            if dept_key in regiones_activas: 
                color_value = dept_name 
            else: 
                color_value = "OTROS" 
            map_rows.append({"departamento": dept_name, "color_group": color_value})
        
        df_map_color = pd.DataFrame(map_rows)

        fig_map = px.choropleth_mapbox(
            df_map_color, geojson=geojson_peru, locations='departamento', featureidkey="properties.NOMBDEP",
            color="color_group", color_discrete_map={ "OTROS": "#E2E8F0" },
            mapbox_style="carto-positron", zoom=4.5, center={"lat": -9.19, "lon": -75.01}, opacity=0.8
        )
        fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=600)
        fig_map.update_traces(showlegend=False) 
        
        evt = st.plotly_chart(fig_map, use_container_width=True, on_select="rerun", key="mapa_convenios")
        if evt and evt['selection']['points']:
            selected_dept = evt['selection']['points'][0]['location']
            dept_key = str(selected_dept).upper().replace("Í", "I")
            if dept_key in links_region:
                url_destino = links_region[dept_key]
                st.success(f"✅ Región seleccionada: **{selected_dept}**")
                st.markdown(f"""
                    <div style="text-align:center; margin: 20px 0;">
                        <a href="{url_destino}" target="_blank" style="background-color:#2563EB; color:white; padding:12px 24px; border-radius:8px; text-decoration:none; font-weight:bold; font-size:1.1rem;">
                            Abrir Reporte de {selected_dept} 🚀
                        </a>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.warning(f"⚠️ La región **{selected_dept}** no tiene un reporte de convenio asignado todavía.")

# --- MAIN ROUTER ---
if st.session_state["app_state"] == "HOME":
    render_home()
else:
    df_filtrado, servicio_nombre = render_sidebar_filters(df_master)
    
    if st.session_state["app_state"] == "DASHBOARD":
        render_dashboard(df_filtrado, servicio_nombre)
    elif st.session_state["app_state"] == "REGIONAL":
        render_regional(df_filtrado)
    elif st.session_state["app_state"] == "PLAN_2025":
        render_plan_2025(df_filtrado)
    elif st.session_state["app_state"] == "CONVENIO":
        render_convenio()