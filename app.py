import streamlit as st
import pandas as pd

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Gestor Nómina Pro 2026", layout="wide", page_icon="🇨🇴")

# Estilos CSS
st.markdown("""
<style>
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #2e7d32; }
    div[data-testid="stMetricValue"] { font-size: 20px; color: #1565C0; }
    .total-highlight { font-size: 24px; font-weight: bold; color: #b71c1c; }
</style>
""", unsafe_allow_html=True)

# --- CONSTANTES LEGALES 2026 (Proyectadas) ---
SMMLV = 1750905 
AUX_TRANS = 249095
UVT = 49799 
TOPE_AUXILIO = SMMLV * 2
TOPE_LEY_1607 = SMMLV * 10

# --- FUNCIONES DE CÁLCULO MASIVO ---

def calcular_linea_empleado(row, config):
    # 1. Extracción de datos (Aseguramos que sean números)
    salario = float(row["Salario Base"])
    dias = float(row["Días Trab."])
    riesgo = int(row["Riesgo ARL (1-5)"]) if row["Riesgo ARL (1-5)"] > 0 else 1
    
    tasas_arl = {1: 0.00522, 2: 0.01044, 3: 0.02436, 4: 0.04350, 5: 0.06960}
    tasa_arl = tasas_arl.get(riesgo, 0.00522)
    
    # 2. Cálculos Devengado
    valor_dia = salario / 30
    valor_hora = valor_dia / 8 
    
    total_extras = (
        (row["H.E. Diurna"] * valor_hora * 1.25) +
        (row["H.E. Nocturna"] * valor_hora * 1.75) +
        (row["H.E. Dom/Fest"] * valor_hora * 1.80) + 
        (row["Recargo Noc"] * valor_hora * 0.35)
    )
    
    # Auxilio Transporte
    if salario <= TOPE_AUXILIO and config["aplica_aux"]:
        aux_transporte = (AUX_TRANS / 30) * dias
        aux_dotacion = True
    else:
        aux_transporte = 0
        aux_dotacion = False
        
    total_devengado = (salario / 30 * dias) + total_extras + aux_transporte
    base_ss = total_devengado - aux_transporte 
    
    # 3. Seguridad Social (EMPLEADOR)
    exonerado = config["exoneracion"] and (base_ss < TOPE_LEY_1607)
    
    aportes_empresa = {
        "Salud (8.5%)": 0 if exonerado else base_ss * 0.085,
        "Pensión (12%)": base_ss * 0.12,
        "ARL": base_ss * tasa_arl,
        "Caja (4%)": base_ss * 0.04,
        "ICBF (3%)": 0 if exonerado else base_ss * 0.03,
        "SENA (2%)": 0 if exonerado else base_ss * 0.02
    }
    
    # 4. Prestaciones Sociales + Dotación
    prov_dotacion = (config["valor_dotacion"] * 3 / 12) if aux_dotacion else 0
    
    prestaciones = {
        "Cesantías (8.33%)": total_devengado * 0.0833,
        "Int. Cesantías (1%)": total_devengado * 0.0833 * 0.12, 
        "Prima (8.33%)": total_devengado * 0.0833,
        "Vacaciones (4.17%)": (base_ss) * 0.0417, 
        "Prov. Dotación": prov_dotacion
    }
    
    # 5. Deducciones al EMPLEADO
    deducciones_empleado = {
        "Salud Emp (4%)": base_ss * 0.04,
        "Pensión Emp (4%)": base_ss * 0.04
    }
    
    # 6. Totales
    total_aportes_empresa = sum(aportes_empresa.values())
    total_prestaciones = sum(prestaciones.values())
    total_deducciones_emp = sum(deducciones_empleado.values())
    
    neto_empleado = total_devengado - total_deducciones_emp
    costo_total_empresa = total_devengado + total_aportes_empresa + total_prestaciones
    
    return {
        "Nombre": str(row["Nombre"]),
        "Salario Base": salario,
        "Total Devengado": total_devengado,
        "Aux. Trans": aux_transporte,
        "Total Extras": total_extras,
        "SS (Empresa)": total_aportes_empresa,
        "Prestaciones": total_prestaciones,
        "Deducciones Empleado": total_deducciones_emp,
        "NETO A PAGAR (Empleado)": neto_empleado,
        "COSTO TOTAL (Empresa)": costo_total_empresa
    }

# --- INTERFAZ BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Configuración Global")
    st.info(f"**SMMLV 2026:** ${SMMLV:,.0f}")
    
    with st.expander("Parámetros Dotación y Auxilio"):
        valor_dotacion = st.number_input("Costo Estimado 1 Kit Dotación", value=180000, step=10000)
        aplicar_aux = st.checkbox("Calcular Aux. Transporte", value=True)
        aplicar_ley1607 = st.checkbox("Aplicar Exoneración Ley 1607", value=True)

    st.markdown("---")
    st.write("Selecciona qué deseas ver en el reporte final:")
    ver_ss = st.checkbox("Incluir Seguridad Social", value=True)
    ver_prest = st.checkbox("Incluir Prestaciones y Dotación", value=True)

# --- INTERFAZ PRINCIPAL ---
st.title("👥 Gestor de Nómina Multi-Empleado 2026")
st.markdown("Agrega, edita o elimina empleados en la tabla. El cálculo se actualiza automáticamente.")

# 1. TABLA DE ENTRADA
if 'df_empleados' not in st.session_state:
    data_inicial = {
        "Nombre": ["Empleado 1", "Empleado 2"],
        "Salario Base": [SMMLV, 2500000],
        "Días Trab.": [30, 30],
        "H.E. Diurna": [0.0, 2.0],
        "H.E. Nocturna": [0.0, 0.0],
        "H.E. Dom/Fest": [0.0, 5.0],
        "Recargo Noc": [0.0, 0.0],
        "Riesgo ARL (1-5)": [1, 3]
    }
    st.session_state.df_empleados = pd.DataFrame(data_inicial)

st.caption("📝 **Edita esta tabla directamente:** (Doble clic en las celdas)")
# Configuramos las columnas para forzar tipos de datos y evitar errores
column_config = {
    "Salario Base": st.column_config.NumberColumn(min_value=0, required=True, default=0),
    "Días Trab.": st.column_config.NumberColumn(min_value=0, max_value=30, default=30),
    "H.E. Diurna": st.column_config.NumberColumn(default=0),
    "H.E. Nocturna": st.column_config.NumberColumn(default=0),
    "H.E. Dom/Fest": st.column_config.NumberColumn(default=0),
    "Recargo Noc": st.column_config.NumberColumn(default=0),
    "Riesgo ARL (1-5)": st.column_config.NumberColumn(min_value=1, max_value=5, default=1)
}

df_input = st.data_editor(
    st.session_state.df_empleados, 
    num_rows="dynamic", 
    column_config=column_config,
    use_container_width=True
)

# 2. PROCESAMIENTO CON LIMPIEZA DE DATOS (AQUÍ ESTÁ LA SOLUCIÓN)
config_calc = {
    "valor_dotacion": valor_dotacion,
    "aplica_aux": aplicar_aux,
    "exoneracion": aplicar_ley1607
}

resultados = []

if not df_input.empty:
    # --- ESCUDO ANTI-ERRORES ---
    # Rellenamos los vacíos (None) con 0 en las columnas numéricas
    cols_numericas_input = ["Salario Base", "Días Trab.", "H.E. Diurna", "H.E. Nocturna", 
                           "H.E. Dom/Fest", "Recargo Noc", "Riesgo ARL (1-5)"]
    
    # Creamos una copia limpia para calcular
    df_clean = df_input.copy()
    df_clean[cols_numericas_input] = df_clean[cols_numericas_input].fillna(0)
    
    for index, row in df_clean.iterrows():
        # Ahora sí preguntamos, sabiendo que row["Salario Base"] nunca será None
        if row["Salario Base"] > 0:
            res = calcular_linea_empleado(row, config_calc)
            resultados.append(res)

if resultados:
    df_res = pd.DataFrame(resultados)
    
    # 3. LÓGICA DE FILTROS Y VISUALIZACIÓN
    col_visual = ["Nombre", "Salario Base", "Total Extras", "Aux. Trans"]
    total_custom = df_res["Salario Base"] + df_res["Total Extras"] + df_res["Aux. Trans"]
    
    if ver_ss:
        col_visual.append("SS (Empresa)")
        total_custom += df_res["SS (Empresa)"]
        
    if ver_prest:
        col_visual.append("Prestaciones")
        total_custom += df_res["Prestaciones"]
        
    df_res["COSTO FILTRADO"] = total_custom
    
    # --- RESULTADOS RESUMEN ---
    st.markdown("### 📊 Resumen Financiero")
    
    total_empleados = len(df_res)
    suma_total_empresa = df_res["COSTO TOTAL (Empresa)"].sum()
    suma_neto_empleados = df_res["NETO A PAGAR (Empleado)"].sum()
    suma_filtrada = df_res["COSTO FILTRADO"].sum()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Empleados", total_empleados)
    c2.metric("Nómina Neta (A pagar)", f"${suma_neto_empleados:,.0f}")
    c3.metric("Carga Prestacional/SS", f"${(suma_total_empresa - suma_neto_empleados):,.0f}")
    c4.metric("COSTO REAL TOTAL", f"${suma_total_empresa:,.0f}", delta="Gasto Total", delta_color="inverse")
    
    st.divider()
    
    tab_reporte, tab_detalle = st.tabs(["📋 Reporte Gerencial", "🔎 Comparativa Gasto vs Pago"])
    
    with tab_reporte:
        st.subheader("Subtotal Personalizado")
        st.markdown(f"**Viendo:** Salario + Extras + Aux {'+ SS' if ver_ss else ''} {'+ Prestaciones' if ver_prest else ''}")
        
        col_finales = col_visual + ["COSTO FILTRADO"]
        cols_numericas = [c for c in col_finales if c != "Nombre"]
        
        st.dataframe(
            df_res[col_finales].style.format("${:,.0f}", subset=cols_numericas), 
            use_container_width=True
        )
        st.markdown(f"### Total de esta vista: <span style='color:green'>${suma_filtrada:,.0f}</span>", unsafe_allow_html=True)

    with tab_detalle:
        st.subheader("¿Quién paga qué?")
        df_comparativo = df_res[["Nombre", "COSTO TOTAL (Empresa)", "NETO A PAGAR (Empleado)"]].copy()
        df_comparativo["Diferencia (Carga)"] = df_comparativo["COSTO TOTAL (Empresa)"] - df_comparativo["NETO A PAGAR (Empleado)"]
        
        cols_num_comp = ["COSTO TOTAL (Empresa)", "NETO A PAGAR (Empleado)", "Diferencia (Carga)"]
        
        st.dataframe(
            df_comparativo.style.format("${:,.0f}", subset=cols_num_comp).background_gradient(subset=["Diferencia (Carga)"], cmap="Reds"),
            use_container_width=True
        )

else:
    # Mensaje amigable cuando no hay datos
    st.info("👋 **Bienvenido.** Agrega empleados en la tabla de arriba para ver los cálculos.")

if resultados:
    csv = df_res.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descargar Reporte (CSV)", data=csv, file_name="nomina_2026.csv", mime="text/csv")