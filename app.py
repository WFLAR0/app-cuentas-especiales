# -*- coding: utf-8 -*-
import pandas as pd
import streamlit as st
from datetime import datetime, date

st.set_page_config(
    page_title="Herramientas de Negociación - Cuentas Especiales",
    layout="wide",
    page_icon="🧰",
)

# ======================== CONFIG DE DATOS =========================
# True  -> usa datos ficticios locales
# False -> usa SQL Server (consulta por idcuenta)
USE_FAKE_DATA = False

SQL = {
    "DRIVER": "{ODBC Driver 17 for SQL Server}",
    "SERVER": "ADMIN",           # <-- tu servidor
    "DATABASE": "bd_prueba",     # <-- tu base
    "USERNAME": "",              # si usas SQL Auth
    "PASSWORD": "",              # si usas SQL Auth
    "TRUSTED_CONNECTION": "yes", # "no" si usarás usuario/contraseña
    "TABLE": "dbo.base_segmentacion"  # <-- tu tabla/vista con alias de columnas
}

# =========================== ESTILOS ==============================
CSS = """
<style>
:root{
  --azul:#003366;
  --azul-claro:#006699;
  --gris-claro:#f2f4f8;
  --gris:#d9e1ec;
  --gris-oscuro:#6e7c91;
  --blanco:#ffffff;
}

html, body {
  background-color: var(--gris-claro);
  font-family: 'Segoe UI', sans-serif;
  color: #1a1a1a;
}

div.block-container {
  padding-top: 1.2rem;
  padding-bottom: 1.5rem;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(90deg, var(--azul) 0%, var(--azul-claro) 100%);
  color: white;
  padding: 16px 20px;
  border-radius: 12px;
  margin-bottom: 24px;
  font-weight: 600;
  box-shadow: 0 4px 10px rgba(0,0,0,0.15);
}

.badge {
  display: inline-block;
  padding: 6px 16px;
  border-radius: 30px;
  font-weight: 600;
  background-color: white;
  color: var(--azul);
  border: 2px solid var(--azul-claro);
}

.card {
  background: white;
  border-left: 5px solid var(--azul-claro);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 18px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.05);
  transition: box-shadow 0.2s ease;
}
.card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }

.card h3 {
  font-size: 1rem;
  font-weight: 700;
  color: var(--azul);
  margin: 0 0 14px 0;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--gris);
}

.row {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 8px;
  margin-bottom: 10px;
}

.lbl {
  font-weight: 600;
  background-color: var(--gris);
  color: var(--azul);
  padding: 6px 12px;
  border-radius: 8px;
  text-transform: uppercase;
  font-size: 0.85rem;
}

.val {
  background-color: var(--gris-claro);
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid var(--gris);
  font-size: 0.9rem;
}

/* Línea divisoria simple (sin rectángulos) */
.rule{
  width:100%;
  height:2px;
  background:linear-gradient(90deg, var(--azul) 0%, var(--azul-claro) 100%);
  border:none;
  border-radius:0;
  margin:14px 0 16px 0;
}

.note {
  font-size: 0.85rem;
  color: var(--gris-oscuro);
  opacity: 0.75;
  margin-top: 20px;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ======================== UTILIDADES UI ==========================
def is_date_like(v):
    if v is None:
        return False
    if isinstance(v, (pd.Timestamp, datetime, date)):
        return True
    if isinstance(v, str) and any(ch.isdigit() for ch in v):
        try:
            pd.to_datetime(v, errors="raise")
            return True
        except Exception:
            return False
    return False

def fmt(v):
    """Formato robusto: maneja NaT/NaN/None, fechas y números."""
    if v is None:
        return "—"
    try:
        if pd.isna(v):  # NaN / NaT
            return "—"
    except Exception:
        pass
    if is_date_like(v):
        ts = pd.to_datetime(v, errors="coerce")
        return "—" if (ts is pd.NaT or pd.isna(ts)) else ts.strftime("%d/%m/%Y")
    if isinstance(v, (int, float)):
        try:
            return f"{v:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        except Exception:
            pass
    return str(v)

def card(title, items, row_dict):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<h3>{title}</h3>', unsafe_allow_html=True)
    for label, key in items:
        st.markdown(
            f'<div class="row"><div class="lbl">{label}</div>'
            f'<div class="val">{fmt(row_dict.get(key))}</div></div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

def divider_line():
    st.markdown("<div class='rule'></div>", unsafe_allow_html=True)

# ========================= OBTENER DATOS =========================
def load_fake_data():
    data = [
        {
            "idcuenta":"1275583","idcli":"816207","canal_registro":"CoreBank","promotor_adn":"PEÑA CHOQUE ANGELA",
            "nombre_cliente":"CARRILLO CIERTO CLELIA EUTROPIA","asesor":"PEÑA CHOQUE ANGELA","region":"CENTRO ORIENTE",
            "establecimiento":"OFICINA - AUCAYACU","tramo":"2. TRAMO CONTENCION",

            "monto_desembolsado":26132.0,"estado_contable":"REFINANCIADO","tasa_original_desembolso":15.00,
            "tasa_actual":15.00,"fecha_desembolso":"2024-04-25","total_cuotas":36,
            "clasificacion_externa":"4 Perdida","nro_cuotas_pagado":13,"top_contencion":"NO TOP (Asesor)",
            "cuotas_no_pagadas":23,"frecuencia":"05:Mensual",

            "saldo_capital_actual":18166.2,"dias_atraso":48,"monto_cuota_actual":1839.4,
            "fecha_ultimo_pago":"2025-07-26","fecha_vence_cuota":"2025-07-01","otros":26.34,
            "intereses":424.50,"int_comp_mor":19.98,

            "fecha_ultima_reprogramacion":"1900-01-01","tipo_de_repro":"NINGUNO","nro_de_reprogramaciones":0,

            "producto":"PYME - CAMPAÑA REFINANCIAMIENTO","tipo_cliente":"Compartido",
            "cliente_con_descuento":"SIN DESCUENTO DE INTERESES","cuota_con_condenacion":"NO",
            "fecha_cuota_con_condenacion":"1900-01-01","fecha_ultima_condonacion":"1900-01-01",
            "campania_refinanciamiento":"—","impacto":"—","fecha_de_impacto":"2025-08-01","campania":"—",

            "total_vencido":1839.43,"clasificacion_interna":"3 Dudoso","clasificacion_externa_det":"4 Perdida",
            "clasificacion_final":"3 Dudoso","dni":"23011773",

            "detalle_cuotas_ej1":"26.3 | 1,368.6 | 444.48","detalle_cuotas_ej2":"683.2 | 231.2 | 940.8",
            "otros_ej1":"NO PAGO | PAGO CON | Dscto. MAX","otros_ej2":"COBs | Fecha Depósito 0"
        },
        {
            "idcuenta":"2000001","idcli":"900111","canal_registro":"Canal Web","promotor_adn":"PEREZ RUIZ",
            "nombre_cliente":"GARCÍA TORRES","asesor":"LUIS QUISPE","region":"NORTE",
            "establecimiento":"OFICINA - PIURA","tramo":"1. REGULAR",

            "monto_desembolsado":18000,"estado_contable":"VIGENTE","tasa_original_desembolso":17.5,
            "tasa_actual":16.2,"fecha_desembolso":"2023-11-04","total_cuotas":24,
            "clasificacion_externa":"2 CPP","nro_cuotas_pagado":8,"top_contencion":"—",
            "cuotas_no_pagadas":2,"frecuencia":"Mensual",

            "saldo_capital_actual":9200,"dias_atraso":5,"monto_cuota_actual":950,
            "fecha_ultimo_pago":"2025-07-10","fecha_vence_cuota":"2025-08-10","otros":0,
            "intereses":150,"int_comp_mor":2.5,

            "fecha_ultima_reprogramacion":"2024-06-01","tipo_de_repro":"AMPLIACIÓN PLAZO","nro_de_reprogramaciones":1,

            "producto":"PYME","tipo_cliente":"Individual",
            "cliente_con_descuento":"—","cuota_con_condenacion":"NO",
            "fecha_cuota_con_condenacion":"—","fecha_ultima_condonacion":"—",
            "campania_refinanciamiento":"—","impacto":"—","fecha_de_impacto":"—","campania":"Campaña Julio",

            "total_vencido":980,"clasificacion_interna":"1 Normal","clasificacion_externa_det":"2 CPP",
            "clasificacion_final":"1 Normal","dni":"44556677",

            "detalle_cuotas_ej1":"23.4 | 900 | 80","detalle_cuotas_ej2":"—",
            "otros_ej1":"—","otros_ej2":"—"
        }
    ]
    return pd.DataFrame(data)

def load_sql_data_by_id(idcuenta):
    import pyodbc
    auth = "Trusted_Connection=yes;" if SQL["TRUSTED_CONNECTION"].lower() == "yes" \
           else f"UID={SQL['USERNAME']};PWD={SQL['PASSWORD']};"
    conn_str = f"DRIVER={SQL['DRIVER']};SERVER={SQL['SERVER']};DATABASE={SQL['DATABASE']};{auth}"
    query = f"SELECT * FROM {SQL['TABLE']} WHERE idcuenta = ?"
    with pyodbc.connect(conn_str) as cn:
        df = pd.read_sql_query(query, cn, params=[idcuenta])
    # convertir columnas tipo fecha si las hay
    for c in df.columns:
        if "fecha" in c.lower():
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df

# ========================= BUSCADOR (sidebar) ====================
st.sidebar.header("Consulta por idcuenta")

if USE_FAKE_DATA:
    # modo demo con lista desplegable
    df_all = load_fake_data()
    for c in df_all.columns:
        if "fecha" in c.lower():
            df_all[c] = pd.to_datetime(df_all[c], errors="coerce")

    ids = sorted(df_all["idcuenta"].astype(str).unique().tolist())
    sel_id = st.sidebar.selectbox("idcuenta", ids)
    buscar = st.sidebar.button("📌 Buscar", use_container_width=True)

    if "selected_id" not in st.session_state:
        st.session_state["selected_id"] = None
    if buscar:
        st.session_state["selected_id"] = sel_id

    if not st.session_state["selected_id"]:
        st.info("Selecciona un **idcuenta** y pulsa **📌 Buscar**.")
        st.stop()

    row_df = df_all[df_all["idcuenta"].astype(str) == str(st.session_state["selected_id"])]
    if row_df.empty:
        st.warning("No se encontró registro con ese idcuenta.")
        st.stop()
    row = row_df.iloc[0].to_dict()

else:
    # modo SQL: caja de texto + botón (no cargamos todo el universo)
    id_input = st.sidebar.text_input("idcuenta", value="", placeholder="Escribe el ID exacto")
    buscar = st.sidebar.button("📌 Buscar", use_container_width=True)

    if "selected_id" not in st.session_state:
        st.session_state["selected_id"] = None
    if "selected_df" not in st.session_state:
        st.session_state["selected_df"] = None

    if buscar:
        st.session_state["selected_id"] = id_input.strip() if id_input else None
        st.session_state["selected_df"] = None
        if st.session_state["selected_id"]:
            df_sel = load_sql_data_by_id(st.session_state["selected_id"])
            st.session_state["selected_df"] = df_sel

    if st.session_state["selected_df"] is None or st.session_state["selected_id"] is None:
        st.info("Ingresa un **idcuenta** y pulsa **📌 Buscar**.")
        st.stop()

    if st.session_state["selected_df"].empty:
        st.warning("No se encontró registro con ese idcuenta.")
        st.stop()

    row = st.session_state["selected_df"].iloc[0].to_dict()

# ============================ TOP BAR ===========================
st.markdown(
    f"""
    <div class="topbar">
      <div style="font-size:1.05rem; font-weight:800;">HERRAMIENTAS DE NEGOCIACIÓN - CUENTAS ESPECIALES</div>
      <div><span class="badge">IDCUENTA: {row.get("idcuenta")}</span></div>
    </div>
    """,
    unsafe_allow_html=True
)

# ============================ 2 COLUMNAS =========================
LEFT, RIGHT = st.columns([1.05, 1])

with LEFT:
    card(
        "DATOS DEL CLIENTE",
        [
            ("IDCLI", "idcli"),
            ("CANAL REGISTRO", "canal_registro"),
            ("PROMOTOR ADN", "promotor_adn"),
            ("NOMBRE DE CLIENTE", "nombre_cliente"),
            ("ASESOR", "asesor"),
            ("REGION", "region"),
            ("ESTABLECIMIENTO", "establecimiento"),
            ("TRAMO", "tramo"),
        ],
        row,
    )
    card(
        "DATOS DE CREDITO",
        [
            ("MONTO DESEMBOLSADO", "monto_desembolsado"),
            ("ESTADO CONTABLE", "estado_contable"),
            ("TASA ORIGINAL (DESEMBOLSO)", "tasa_original_desembolso"),
            ("TASA ACTUAL", "tasa_actual"),
            ("FECHA DE DESEMBOLSO", "fecha_desembolso"),
            ("TOTAL DE CUOTAS", "total_cuotas"),
            ("CLASIFICACION EXTERNA", "clasificacion_externa"),
            ("NRO CUOTAS PAGADO", "nro_cuotas_pagado"),
            ("TOP CONTENCION", "top_contencion"),
            ("CUOTAS NO PAGADAS", "cuotas_no_pagadas"),
            ("FRECUENCIA", "frecuencia"),
        ],
        row,
    )

with RIGHT:
    card(
        "ESTADO DE CREDITO",
        [
            ("SALDO CAPITAL ACTUAL", "saldo_capital_actual"),
            ("DIAS DE ATRASO", "dias_atraso"),
            ("MONTO DE CUOTA ACTUAL", "monto_cuota_actual"),
            ("FECHA DE ULTIMO DE PAGO", "fecha_ultimo_pago"),
            ("FECHA DE VENCE DE CUOTA", "fecha_vence_cuota"),
            ("OTROS", "otros"),
            ("INTERESES", "intereses"),
            ("INT.COMP/MOR", "int_comp_mor"),
        ],
        row,
    )
    card(
        "REPROGRAMACIONES",
        [
            ("FECHA ULTIMA REPROGRAMACION", "fecha_ultima_reprogramacion"),
            ("TIPO DE REPRO", "tipo_de_repro"),
            ("NRO DE REPROGRAMACIONES", "nro_de_reprogramaciones"),
        ],
        row,
    )
    card(
        "HERRAMIENTAS DE NEGOCIACION",
        [
            ("PRODUCTO", "producto"),
            ("TIPO CLIENTE", "tipo_cliente"),
            ("CLIENTE CON DESCUENTO", "cliente_con_descuento"),
            ("CUOTA CON CONDACION", "cuota_con_condenacion"),
            ("FECHA CUOTA CON CONDACION", "fecha_cuota_con_condenacion"),
            ("FECHA ULTIMA CONDONACION", "fecha_ultima_condonacion"),
            ("CAMPAÑA REFINANCIAMIENTO", "campania_refinanciamiento"),
            ("IMPACTO", "impacto"),
            ("FECHA DE IMPACTO", "fecha_de_impacto"),
            ("CAMPAÑA", "campania"),
            ("CAMPAÑA EXTRAORDINARIO", "campania_extraoridniario"),
            ("CAMPAÑA DOBLE SALTO", "campania_doble_salto"),
        ],
        row,
    )

# ===== Línea separadora para secciones finales =====
divider_line()

# Sub-sección final en 2 columnas
L2, R2 = st.columns([1.05, 1])
with L2:
    card(
        "CAMPAÑA DE CANCELACION CON 50% DSCT. INT.",
        [
            ("TOTAL VENCIDO", "total_vencido"),
            ("CLASIFICACION INTERNA", "clasificacion_interna"),
            ("CLASIFICACION EXTERNA", "clasificacion_externa_det"),
            ("CLASIFICACION FINAL", "clasificacion_final"),
            ("DNI", "dni"),
        ],
        row,
    )
with R2:
    card(
        "DETALLE DE CUOTAS",
        [
            ("EJEMPLO1", "detalle_cuotas_ej1"),
            ("EJEMPLO2", "detalle_cuotas_ej2"),
        ],
        row,
    )
    card(
        "OTROS",
        [
            ("EJ 1", "otros_ej1"),
            ("EJ 2", "otros_ej2"),
        ],
        row,
    )

#st.markdown('<div class="note">Fuente: '
#            f'{"Datos ficticios" if USE_FAKE_DATA else "SQL Server"} · '
#            'Búsqueda exclusivamente por <b>idcuenta</b> (pulsa <b>📌 Buscar</b> para aplicar).</div>',
#            unsafe_allow_html=False)
