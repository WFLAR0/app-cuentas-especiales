# -*- coding: utf-8 -*-
import time
import pandas as pd
import streamlit as st
from datetime import datetime, date
from contextlib import contextmanager
import psycopg2

st.set_page_config(
    page_title="Herramientas de Negociación - Cuentas Especiales",
    layout="wide",
    page_icon="🧰",
)

# ======================================================================
# ESTILOS (CSS)
# ======================================================================
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
div.block-container { padding-top: 1.2rem; padding-bottom: 1.5rem; }

.topbar {
  display:flex; justify-content:space-between; align-items:center;
  background:linear-gradient(90deg, var(--azul) 0%, var(--azul-claro) 100%);
  color:white; padding:16px 20px; border-radius:12px; margin-bottom:24px; font-weight:600;
  box-shadow:0 4px 10px rgba(0,0,0,0.15);
}
.badge { display:inline-block; padding:6px 16px; border-radius:30px; font-weight:600;
  background-color:white; color:var(--azul); border:2px solid var(--azul-claro); }

.card {
  background:white; border-left:5px solid var(--azul-claro); border-radius:12px;
  padding:16px 20px; margin-bottom:18px; box-shadow:0 2px 6px rgba(0,0,0,0.05);
  transition: box-shadow .2s ease;
}
.card:hover { box-shadow:0 4px 12px rgba(0,0,0,0.1); }
.card h3 { font-size:1rem; font-weight:700; color:var(--azul); margin:0 0 14px 0;
  padding-bottom:4px; border-bottom:1px solid var(--gris); }

.row { display:grid; grid-template-columns:200px 1fr; gap:8px; margin-bottom:10px; }
.lbl { font-weight:600; background-color:var(--gris); color:var(--azul);
  padding:6px 12px; border-radius:8px; text-transform:uppercase; font-size:.85rem; }
.val { background-color:var(--gris-claro); padding:6px 12px; border-radius:8px;
  border:1px solid var(--gris); font-size:.9rem; }

/* Línea divisoria simple */
.rule{ width:100%; height:2px; background:linear-gradient(90deg, var(--azul) 0%, var(--azul-claro) 100%);
  border:none; border-radius:0; margin:14px 0 16px 0; }

.note { font-size:.85rem; color:var(--gris-oscuro); opacity:.75; margin-top:20px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ======================================================================
# UTILIDADES UI
# ======================================================================
def is_date_like(v):
    if v is None: return False
    if isinstance(v, (pd.Timestamp, datetime, date)): return True
    if isinstance(v, str) and any(ch.isdigit() for ch in v):
        try: pd.to_datetime(v, errors="raise"); return True
        except Exception: return False
    return False

def fmt(v):
    if v is None: return "—"
    try:
        if pd.isna(v): return "—"
    except Exception:
        pass
    if is_date_like(v):
        ts = pd.to_datetime(v, errors="coerce")
        return "—" if (ts is pd.NaT or pd.isna(ts)) else ts.strftime("%d/%m/%Y")
    if isinstance(v, (int, float)):
        try: return f"{v:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        except Exception: pass
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

# ======================================================================
# CONEXIÓN POSTGRES (SUPABASE via psycopg2)
# ======================================================================
def _pg_cfg():
    pg = st.secrets.get("pg", {})
    required = ["host", "port", "dbname", "user", "password"]
    missing = [k for k in required if not pg.get(k)]
    return pg, missing

@contextmanager
def pg_conn():
    pg, missing = _pg_cfg()
    if missing:
        st.error(f"Faltan claves en secrets.toml: {', '.join(missing)} (sección [pg]).")
        raise RuntimeError("Secrets incompletos.")
    conn = psycopg2.connect(
        host=pg['host'],
        port=pg.get('port', 5432),
        dbname=pg['dbname'],
        user=pg['user'],
        password=pg['password'],
        sslmode=pg.get('sslmode','require')
    )
    try:
        yield conn
    finally:
        conn.close()

def init_login_tables():
    with pg_conn() as cn:
        with cn.cursor() as cur:
            schema = st.secrets.get("pg", {}).get("schema", "public")
            cur.execute(f"""
                create table if not exists {schema}.allowed_users(
                    email text primary key,
                    is_active boolean not null default true
                );
            """)
            cur.execute(f"""
                create table if not exists {schema}.login_audit(
                    id bigserial primary key,
                    email text not null,
                    login_at timestamptz not null default now(),
                    user_agent text,
                    ip text
                );
            """)
            cur.execute(f"""
                create table if not exists {schema}.user_login_stats(
                    email text primary key,
                    login_count integer not null default 0
                );
            """)
        cn.commit()

def is_allowed_email(email:str)->bool:
    schema = st.secrets.get("pg", {}).get("schema", "public")
    with pg_conn() as cn, cn.cursor() as cur:
        cur.execute(
            f"select 1 from {schema}.allowed_users where lower(email)=lower(%s) and is_active = true limit 1;",
            (email,)
        )
        return cur.fetchone() is not None

def record_login(email:str, user_agent:str=None, ip:str=None)->int:
    schema = st.secrets.get("pg", {}).get("schema", "public")
    with pg_conn() as cn, cn.cursor() as cur:
        cur.execute(f"insert into {schema}.login_audit(email,user_agent,ip) values (%s,%s,%s);",
                    (email, user_agent, ip))
        cur.execute(f"""
            insert into {schema}.user_login_stats(email, login_count)
            values (%s, 1)
            on conflict (email) do update
            set login_count = {schema}.user_login_stats.login_count + 1
            returning login_count;
        """, (email,))
        count = cur.fetchone()[0]
        cn.commit()
        return count

def load_pg_record_by_id(idcuenta:str)->pd.DataFrame:
    schema = st.secrets.get("pg", {}).get("schema", "public")
    with pg_conn() as cn:
        df = pd.read_sql_query(
            f"select * from {schema}.base_segmentacion where idcuenta = %s;",
            cn, params=(idcuenta,)
        )
    for c in df.columns:
        if "fecha" in c.lower():
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df

# ======================================================================
# AUTH: correo permitido + contraseña compartida (PLAIN desde secrets)
# ======================================================================
def verify_shared_password(plain_password: str) -> bool:
    auth = st.secrets.get("auth", {})
    stored_plain = auth.get("shared_password_plain", "")
    if not stored_plain:
        st.error("Falta 'shared_password_plain' en .streamlit/secrets.toml (sección [auth]).")
        return False
    return plain_password == stored_plain

def login_view():
    st.title("Ingreso")
    st.caption("Acceso restringido: **correo autorizado** + **contraseña compartida**.")
    if "fail_count" not in st.session_state: st.session_state["fail_count"] = 0
    if "lock_until" not in st.session_state: st.session_state["lock_until"] = 0.0

    now = time.time()
    if now < st.session_state["lock_until"]:
        wait = int(st.session_state["lock_until"] - now)
        st.error(f"Demasiados intentos fallidos. Intenta de nuevo en {wait} s.")
        return

    with st.form("login-form", clear_on_submit=False):
        email = st.text_input("Correo institucional", "", placeholder="usuario@empresa.com")
        password = st.text_input("Contraseña", "", type="password")
        submitted = st.form_submit_button("Iniciar sesión")

    if submitted:
        if not email or "@" not in email:
            st.error("Ingresa un correo válido."); return
        if not password:
            st.error("Ingresa la contraseña."); return
        try:
            init_login_tables()
            # Si quieres permitir a cualquiera, comenta la siguiente validación:
            if not is_allowed_email(email):
                st.session_state["fail_count"] += 1
                st.error("Correo no autorizado."); return

            if not verify_shared_password(password):
                st.session_state["fail_count"] += 1
                if st.session_state["fail_count"] >= 5:
                    st.session_state["lock_until"] = time.time() + 30
                st.error("Contraseña incorrecta."); return

            # éxito
            st.session_state["fail_count"] = 0
            st.session_state["lock_until"] = 0.0
            count = record_login(email=email, user_agent="streamlit", ip=None)
            st.session_state["auth_email"] = email
            st.session_state["login_count"] = count
            st.success(f"Bienvenido, {email}. Inicios acumulados: {count}")
            st.rerun()
        except Exception as e:
            st.error(f"Error de autenticación: {e}")

# Gate de autenticación
if "auth_email" not in st.session_state or not st.session_state["auth_email"]:
    login_view()
    st.stop()

# Botón de cierre de sesión
with st.sidebar:
    st.markdown(f"**Usuario:** {st.session_state['auth_email']}")
    st.markdown(f"**Ingresos:** {st.session_state.get('login_count','—')}")
    if st.button("Cerrar sesión"):
        for k in ["auth_email", "login_count", "selected_id", "selected_df"]:
            if k in st.session_state: del st.session_state[k]
        st.rerun()

# ======================================================================
# BÚSQUEDA por idcuenta (SIEMPRE Supabase/Postgres)
# ======================================================================
st.sidebar.header("Consulta por idcuenta")

id_input = st.sidebar.text_input("idcuenta", value="", placeholder="Escribe el ID exacto")
buscar = st.sidebar.button("📌 Buscar", use_container_width=True)

if "selected_id" not in st.session_state: st.session_state["selected_id"] = None
if "selected_df" not in st.session_state: st.session_state["selected_df"] = None

if buscar:
    st.session_state["selected_id"] = id_input.strip() if id_input else None
    st.session_state["selected_df"] = None
    if st.session_state["selected_id"]:
        try:
            st.session_state["selected_df"] = load_pg_record_by_id(st.session_state["selected_id"])
        except Exception as e:
            st.error(f"Error consultando base_segmentacion: {e}")

if st.session_state["selected_df"] is None or st.session_state["selected_id"] is None:
    st.info("Ingresa un **idcuenta** y pulsa **📌 Buscar**.")
    st.stop()

row_df = st.session_state["selected_df"]
if row_df.empty:
    st.warning("No se encontró registro con ese idcuenta.")
    st.stop()

row = row_df.iloc[0].to_dict()

# ======================================================================
# TOP BAR
# ======================================================================
st.markdown(
    f"""
    <div class="topbar">
      <div style="font-size:1.05rem; font-weight:800;">HERRAMIENTAS DE NEGOCIACIÓN - CUENTAS ESPECIALES</div>
      <div><span class="badge">IDCUENTA: {row.get("idcuenta")}</span></div>
    </div>
    """,
    unsafe_allow_html=True
)

# ======================================================================
# LAYOUT (2 columnas) — SOLO LOS CAMPOS PEDIDOS
# ======================================================================
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
        ],
        row,
    )

divider_line()

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

st.markdown('<div class="note">Fuente: Supabase · Postgres · Búsqueda exclusivamente por <b>idcuenta</b>.</div>',
            unsafe_allow_html=True)
