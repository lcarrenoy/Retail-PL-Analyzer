"""
dashboard_cloud.py
Dashboard Retail P&L Analyzer — version para Streamlit Cloud
Lee CSVs directamente sin necesitar la API local

Deploy:
    1. Sube este archivo como dashboard/dashboard.py
    2. Ve a share.streamlit.io
    3. Conecta el repo y selecciona dashboard/dashboard.py
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path

DATA = Path("data/sample")
OUTPUT = Path("data/output")

st.set_page_config(
    page_title="Retail P&L Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.metric-card { background:#f8f9fa; border-radius:10px; padding:16px 20px; border-left:4px solid #1D9E75; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def cargar_datos():
    ventas  = pd.read_csv(DATA / "ventas_por_categoria.csv", parse_dates=["fecha"])
    opex    = pd.read_csv(DATA / "gastos_operativos.csv",    parse_dates=["fecha"])
    pl      = pd.read_csv(DATA / "pl_consolidado.csv",       parse_dates=["fecha"])
    tiendas = pd.read_csv(DATA / "dim_tiendas.csv")
    cats    = pd.read_csv(DATA / "dim_categorias.csv")
    return ventas, opex, pl, tiendas, cats


@st.cache_data
def calcular_resumen(pl):
    df = pl.groupby("anio").agg(
        ventas=("ventas","sum"), margen_bruto=("margen_bruto","sum"),
        merma=("merma","sum"), total_opex=("total_opex","sum"),
        ebitda=("ebitda","sum"), unidades=("unidades","sum"),
    ).reset_index()
    df["margen_bruto_pct"] = (df["margen_bruto"] / df["ventas"] * 100).round(2)
    df["merma_pct"]        = (df["merma"]         / df["ventas"] * 100).round(2)
    df["opex_pct"]         = (df["total_opex"]    / df["ventas"] * 100).round(2)
    df["ebitda_pct"]       = (df["ebitda"]         / df["ventas"] * 100).round(2)
    df["crecimiento_pct"]  = (df["ventas"].pct_change() * 100).round(2)
    return df


@st.cache_data
def calcular_ranking(pl, anio):
    df = pl[pl["anio"] == anio].groupby(
        ["tienda_id","tienda_nombre","formato","distrito","nse"]
    ).agg(ventas=("ventas","sum"), margen_bruto=("margen_bruto","sum"),
          merma=("merma","sum"), total_opex=("total_opex","sum"), ebitda=("ebitda","sum")
    ).reset_index()
    df["margen_bruto_pct"] = (df["margen_bruto"] / df["ventas"] * 100).round(2)
    df["ebitda_pct"]       = (df["ebitda"]       / df["ventas"] * 100).round(2)
    df["merma_pct"]        = (df["merma"]         / df["ventas"] * 100).round(2)
    df["rank"] = df["ebitda_pct"].rank(ascending=False).astype(int)
    return df.sort_values("rank")


@st.cache_data
def calcular_categorias(ventas, anio):
    df = ventas[ventas["anio"] == anio].groupby("categoria").agg(
        ventas=("ventas","sum"), margen_bruto=("margen_bruto","sum"), merma=("merma","sum")
    ).reset_index()
    df["margen_bruto_pct"] = (df["margen_bruto"] / df["ventas"] * 100).round(1)
    df["merma_pct"]        = (df["merma"]         / df["ventas"] * 100).round(1)
    return df


@st.cache_data
def calcular_oportunidades(pl, anio):
    rank = calcular_ranking(pl, anio)
    p25 = rank["ebitda_pct"].quantile(0.25)
    bajo_margen = rank[rank["ebitda_pct"] < p25][["tienda_nombre","formato","ebitda_pct","ventas"]]
    impacto = bajo_margen["ventas"].sum() * 0.03
    return bajo_margen, round(impacto, 0)


# ── Cargar datos ─────────────────────────────────────────────
ventas, opex, pl, tiendas, cats = cargar_datos()
resumen = calcular_resumen(pl)

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏪 Supermercados ABC")
    st.markdown("Análisis de rentabilidad por tienda y categoría")
    st.markdown("---")
    anio = st.selectbox("Año", [2024, 2023, 2022], index=0)
    formato = st.selectbox("Formato", ["Todos", "Express", "Supermarket"])
    nse = st.selectbox("NSE", ["Todos", "AB", "BC"])
    st.markdown("---")
    st.markdown("**Retail P&L Analyzer v1.0**")
    st.markdown("[GitHub](https://github.com/lcarrenoy/Retail-PL-Analyzer)")

# ── Header + KPIs ────────────────────────────────────────────
st.title("📊 Retail P&L Analyzer")
st.caption(f"Supermercados ABC · Análisis de rentabilidad {anio}")

row = resumen[resumen["anio"] == anio].iloc[0]
row_ant = resumen[resumen["anio"] == anio - 1]

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    delta = f"{row['crecimiento_pct']:+.1f}%" if pd.notna(row.get("crecimiento_pct")) else None
    st.metric("Ventas totales", f"S/. {row['ventas']/1e6:.1f}M", delta=delta)
with col2:
    st.metric("Margen bruto", f"{row['margen_bruto_pct']:.1f}%")
with col3:
    st.metric("EBITDA", f"{row['ebitda_pct']:.1f}%")
with col4:
    st.metric("Merma", f"{row['merma_pct']:.1f}%")
with col5:
    st.metric("OPEX / Ventas", f"{row['opex_pct']:.1f}%")

st.markdown("---")

# ── Tabs ─────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["🏪 Por tienda", "🛒 Por categoría", "🏆 Ranking", "⚡ Oportunidades"])

# ─ Tab 1 ─────────────────────────────────────────────────────
with tab1:
    df = pl[pl["anio"] == anio].copy()
    if formato != "Todos": df = df[df["formato"] == formato]
    if nse != "Todos":     df = df[df["nse"] == nse]

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Ventas mensuales por tienda")
        agg = df.groupby(["fecha","tienda_nombre"])["ventas"].sum().reset_index()
        fig = px.line(agg, x="fecha", y="ventas", color="tienda_nombre",
                      labels={"ventas":"Ventas (S/.)","fecha":"Mes","tienda_nombre":"Tienda"},
                      color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(height=350, legend=dict(orientation="h", y=-0.3))
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("EBITDA % por tienda")
        eb = df.groupby("tienda_nombre").agg(ventas=("ventas","sum"), ebitda=("ebitda","sum")).reset_index()
        eb["ebitda_pct"] = (eb["ebitda"] / eb["ventas"] * 100).round(2)
        eb = eb.sort_values("ebitda_pct")
        fig2 = px.bar(eb, x="ebitda_pct", y="tienda_nombre", orientation="h",
                      color="ebitda_pct", color_continuous_scale=["#E24B4A","#EF9F27","#1D9E75"])
        fig2.update_layout(height=350, coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Detalle por tienda")
    det = df.groupby(["tienda_nombre","formato","distrito","nse"]).agg(
        ventas=("ventas","sum"), margen_bruto=("margen_bruto","sum"),
        merma=("merma","sum"), ebitda=("ebitda","sum"),
    ).reset_index()
    det["Margen %"] = (det["margen_bruto"] / det["ventas"] * 100).round(1)
    det["Merma %"]  = (det["merma"]         / det["ventas"] * 100).round(1)
    det["EBITDA %"] = (det["ebitda"]         / det["ventas"] * 100).round(1)
    det["Ventas"]   = det["ventas"].apply(lambda x: f"S/. {x/1e6:.2f}M")
    st.dataframe(det[["tienda_nombre","formato","distrito","nse","Ventas","Margen %","Merma %","EBITDA %"]].rename(
        columns={"tienda_nombre":"Tienda","formato":"Formato","distrito":"Distrito","nse":"NSE"}),
        use_container_width=True, hide_index=True)

# ─ Tab 2 ─────────────────────────────────────────────────────
with tab2:
    df_cat = calcular_categorias(ventas, anio)
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Margen bruto por categoría")
        fig3 = px.bar(df_cat.sort_values("margen_bruto_pct"), x="margen_bruto_pct", y="categoria",
                      orientation="h", color="margen_bruto_pct",
                      color_continuous_scale=["#EF9F27","#1D9E75"])
        fig3.update_layout(height=380, coloraxis_showscale=False)
        st.plotly_chart(fig3, use_container_width=True)
    with col_b:
        st.subheader("Merma por categoría")
        fig4 = px.bar(df_cat.sort_values("merma_pct", ascending=False),
                      x="categoria", y="merma_pct", color="merma_pct",
                      color_continuous_scale=["#1D9E75","#E24B4A"])
        fig4.add_hline(y=8, line_dash="dash", line_color="#E24B4A", annotation_text="Umbral 8%")
        fig4.update_layout(height=380, coloraxis_showscale=False)
        st.plotly_chart(fig4, use_container_width=True)

# ─ Tab 3 ─────────────────────────────────────────────────────
with tab3:
    rank = calcular_ranking(pl, anio)
    st.subheader(f"🏆 Ranking de rentabilidad {anio}")
    fig5 = go.Figure()
    fig5.add_trace(go.Bar(
        x=rank["tienda_nombre"], y=rank["ebitda_pct"],
        marker_color=["#1D9E75" if i < 3 else "#378ADD" if i < 7 else "#E24B4A" for i in range(len(rank))],
        text=[f"{v:.1f}%" for v in rank["ebitda_pct"]], textposition="outside",
    ))
    fig5.update_layout(height=380, yaxis_title="EBITDA %", showlegend=False)
    st.plotly_chart(fig5, use_container_width=True)
    rank["Ventas"] = rank["ventas"].apply(lambda x: f"S/. {x/1e6:.2f}M")
    st.dataframe(rank[["rank","tienda_nombre","formato","distrito","Ventas","ebitda_pct","margen_bruto_pct","merma_pct"]].rename(
        columns={"rank":"#","tienda_nombre":"Tienda","formato":"Formato","distrito":"Distrito",
                 "ebitda_pct":"EBITDA %","margen_bruto_pct":"Margen %","merma_pct":"Merma %"}),
        use_container_width=True, hide_index=True)

# ─ Tab 4 ─────────────────────────────────────────────────────
with tab4:
    bajo_margen, impacto = calcular_oportunidades(pl, anio)
    cats_merma = calcular_categorias(ventas, anio)
    alta_merma = cats_merma[cats_merma["merma_pct"] > 8].sort_values("merma_pct", ascending=False)

    st.subheader("⚡ Oportunidades de mejora identificadas")
    st.metric("💰 Impacto potencial estimado", f"S/. {impacto:,.0f}",
              help="Estimado con mejora del 3% en EBITDA de tiendas bajo el percentil 25")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 🏪 Tiendas con bajo margen")
        for _, row in bajo_margen.iterrows():
            color = "🔴" if row["ebitda_pct"] < 18 else "🟡"
            st.markdown(f"{color} **{row['tienda_nombre']}** ({row['formato']}) — EBITDA {row['ebitda_pct']:.1f}%")

        st.markdown("#### 📦 Categorías con alta merma")
        fig6 = px.bar(alta_merma, x="categoria", y="merma_pct",
                      color="merma_pct", color_continuous_scale=["#EF9F27","#E24B4A"])
        fig6.add_hline(y=8, line_dash="dash", line_color="gray")
        fig6.update_layout(height=280, coloraxis_showscale=False)
        st.plotly_chart(fig6, use_container_width=True)

    with col_b:
        st.markdown("#### 💡 Acciones recomendadas")
        st.info("**Frutas y Verduras (14.9% merma)**\nRevisar planificación de compras y cadena de frío. Reducir al 10% genera ~S/. 180K en ahorro anual.")
        st.warning("**Tiendas con bajo EBITDA**\nAlto OPEX relativo. Revisar estructura de personal y renegociar alquileres en próximo ciclo.")
        st.success("**Panadería (45% margen bruto)**\nCategoría de mayor margen — oportunidad de ampliar surtido y aumentar participación en ventas totales.")
