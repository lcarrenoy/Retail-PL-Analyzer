"""
dashboard.py
Dashboard interactivo Retail P&L Analyzer — Supermercados ABC
Consume la API FastAPI en localhost:8000

Uso:
    uv run streamlit run dashboard/dashboard.py
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import requests

API = "http://localhost:8000"

st.set_page_config(
    page_title="Retail P&L Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Estilos ──────────────────────────────────────────────────
st.markdown("""
<style>
.metric-card {
    background: #f8f9fa;
    border-radius: 10px;
    padding: 16px 20px;
    border-left: 4px solid #1D9E75;
}
.metric-label { font-size: 12px; color: #666; margin-bottom: 4px; }
.metric-value { font-size: 24px; font-weight: 600; color: #1a1a1a; }
.metric-delta { font-size: 12px; color: #1D9E75; }
.metric-delta.neg { color: #E24B4A; }
h1 { color: #1a1a1a; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=60)
def fetch(endpoint, params=None):
    try:
        r = requests.get(f"{API}{endpoint}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error conectando a la API: {e}")
        return []


# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.image("https://via.placeholder.com/200x60/1D9E75/white?text=ABC+Supermercados", width=200)
    st.markdown("### Filtros")

    anio = st.selectbox("Año", [2024, 2023, 2022], index=0)
    formato = st.selectbox("Formato", ["Todos", "Express", "Supermarket"])
    nse = st.selectbox("NSE", ["Todos", "AB", "BC"])

    st.markdown("---")
    st.markdown("**Retail P&L Analyzer**")
    st.markdown("v1.0.0 · [GitHub](https://github.com/lcarrenoy/Retail-PL-Analyzer)")

fmt_param = None if formato == "Todos" else formato
nse_param = None if nse == "Todos" else nse

# ── Header ───────────────────────────────────────────────────
st.title("📊 Retail P&L Analyzer")
st.caption(f"Supermercados ABC · Análisis de rentabilidad {anio}")

# ── KPIs principales ─────────────────────────────────────────
resumen_data = fetch("/resumen")
if resumen_data:
    df_res = pd.DataFrame(resumen_data)
    row = df_res[df_res["anio"] == anio].iloc[0] if anio in df_res["anio"].values else df_res.iloc[-1]
    row_ant = df_res[df_res["anio"] == anio - 1]

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        delta = f"vs {anio-1}" if not row_ant.empty else ""
        st.metric("Ventas totales", f"S/. {row['ventas']/1e6:.1f}M",
                  delta=f"{row['crecimiento_pct']:+.1f}%" if pd.notna(row.get('crecimiento_pct')) else None)
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

# ─ Tab 1: Por tienda ─────────────────────────────────────────
with tab1:
    params = {"anio": anio}
    if fmt_param: params["formato"] = fmt_param
    if nse_param: params["nse"] = nse_param

    data = fetch("/tiendas", params)
    if data:
        df = pd.DataFrame(data)
        df["fecha"] = pd.to_datetime(df["fecha"])

        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("Ventas mensuales por tienda")
            df_agg = df.groupby(["fecha", "tienda_nombre"])["ventas"].sum().reset_index()
            fig = px.line(df_agg, x="fecha", y="ventas", color="tienda_nombre",
                          labels={"ventas": "Ventas (S/.)", "fecha": "Mes", "tienda_nombre": "Tienda"},
                          color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(height=350, legend=dict(orientation="h", y=-0.3))
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.subheader("EBITDA % por tienda")
            df_ebitda = df.groupby("tienda_nombre").agg(
                ventas=("ventas", "sum"),
                ebitda=("ebitda", "sum")
            ).reset_index()
            df_ebitda["ebitda_pct"] = (df_ebitda["ebitda"] / df_ebitda["ventas"] * 100).round(2)
            df_ebitda = df_ebitda.sort_values("ebitda_pct")
            fig2 = px.bar(df_ebitda, x="ebitda_pct", y="tienda_nombre", orientation="h",
                          labels={"ebitda_pct": "EBITDA %", "tienda_nombre": ""},
                          color="ebitda_pct",
                          color_continuous_scale=["#E24B4A", "#EF9F27", "#1D9E75"])
            fig2.update_layout(height=350, coloraxis_showscale=False)
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Detalle por tienda")
        df_det = df.groupby(["tienda_nombre", "formato", "distrito", "nse"]).agg(
            ventas=("ventas", "sum"),
            margen_bruto=("margen_bruto", "sum"),
            merma=("merma", "sum"),
            total_opex=("total_opex", "sum"),
            ebitda=("ebitda", "sum"),
        ).reset_index()
        df_det["margen_pct"] = (df_det["margen_bruto"] / df_det["ventas"] * 100).round(1)
        df_det["ebitda_pct"] = (df_det["ebitda"] / df_det["ventas"] * 100).round(1)
        df_det["merma_pct"]  = (df_det["merma"]  / df_det["ventas"] * 100).round(1)
        df_det["ventas_fmt"] = df_det["ventas"].apply(lambda x: f"S/. {x/1e6:.2f}M")
        st.dataframe(
            df_det[["tienda_nombre","formato","distrito","nse","ventas_fmt","margen_pct","merma_pct","ebitda_pct"]].rename(columns={
                "tienda_nombre": "Tienda", "formato": "Formato", "distrito": "Distrito",
                "nse": "NSE", "ventas_fmt": "Ventas", "margen_pct": "Margen %",
                "merma_pct": "Merma %", "ebitda_pct": "EBITDA %"
            }),
            use_container_width=True, hide_index=True
        )

# ─ Tab 2: Por categoría ──────────────────────────────────────
with tab2:
    data_cat = fetch("/categorias", {"anio": anio})
    if data_cat:
        df_cat = pd.DataFrame(data_cat)
        df_cat_agg = df_cat.groupby("categoria").agg(
            ventas=("ventas", "sum"),
            margen_bruto=("margen_bruto", "sum"),
            merma=("merma", "sum"),
        ).reset_index()
        df_cat_agg["margen_pct"] = (df_cat_agg["margen_bruto"] / df_cat_agg["ventas"] * 100).round(1)
        df_cat_agg["merma_pct"]  = (df_cat_agg["merma"]  / df_cat_agg["ventas"] * 100).round(1)

        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("Margen bruto por categoría")
            fig3 = px.bar(df_cat_agg.sort_values("margen_pct"),
                          x="margen_pct", y="categoria", orientation="h",
                          labels={"margen_pct": "Margen bruto %", "categoria": ""},
                          color="margen_pct",
                          color_continuous_scale=["#EF9F27", "#1D9E75"])
            fig3.update_layout(height=380, coloraxis_showscale=False)
            st.plotly_chart(fig3, use_container_width=True)

        with col_b:
            st.subheader("Merma por categoría")
            fig4 = px.bar(df_cat_agg.sort_values("merma_pct", ascending=False),
                          x="categoria", y="merma_pct",
                          labels={"merma_pct": "Merma %", "categoria": ""},
                          color="merma_pct",
                          color_continuous_scale=["#1D9E75", "#E24B4A"])
            fig4.add_hline(y=8, line_dash="dash", line_color="#E24B4A",
                           annotation_text="Umbral 8%")
            fig4.update_layout(height=380, coloraxis_showscale=False)
            st.plotly_chart(fig4, use_container_width=True)

# ─ Tab 3: Ranking ────────────────────────────────────────────
with tab3:
    data_rank = fetch("/ranking", {"anio": anio, "top": 10})
    if data_rank:
        df_rank = pd.DataFrame(data_rank)
        st.subheader(f"🏆 Ranking de rentabilidad {anio}")

        fig5 = go.Figure()
        fig5.add_trace(go.Bar(
            x=df_rank["tienda_nombre"], y=df_rank["ebitda_pct"],
            marker_color=["#1D9E75" if i < 3 else "#378ADD" if i < 7 else "#E24B4A"
                          for i in range(len(df_rank))],
            text=[f"{v:.1f}%" for v in df_rank["ebitda_pct"]],
            textposition="outside",
        ))
        fig5.update_layout(
            height=380, yaxis_title="EBITDA %",
            xaxis_title="", showlegend=False,
        )
        st.plotly_chart(fig5, use_container_width=True)

        st.dataframe(
            df_rank[["rank","tienda_nombre","formato","distrito","ventas","ebitda_pct","margen_bruto_pct","merma_pct"]].rename(columns={
                "rank": "#", "tienda_nombre": "Tienda", "formato": "Formato",
                "distrito": "Distrito", "ventas": "Ventas",
                "ebitda_pct": "EBITDA %", "margen_bruto_pct": "Margen %", "merma_pct": "Merma %"
            }),
            use_container_width=True, hide_index=True
        )

# ─ Tab 4: Oportunidades ──────────────────────────────────────
with tab4:
    data_op = fetch("/oportunidades")
    if data_op:
        st.subheader("⚡ Oportunidades de mejora identificadas")

        impacto = data_op.get("impacto_potencial_soles", 0)
        st.metric("💰 Impacto potencial estimado",
                  f"S/. {impacto:,.0f}",
                  help="Estimado con mejora del 3% en EBITDA de tiendas bajo el percentil 25")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("#### 🏪 Tiendas con bajo margen")
            tiendas_bm = data_op.get("tiendas_bajo_margen", [])
            if tiendas_bm:
                df_bm = pd.DataFrame(tiendas_bm)
                for _, row in df_bm.iterrows():
                    color = "🔴" if row["ebitda_pct"] < 18 else "🟡"
                    st.markdown(f"{color} **{row['tienda_nombre']}** ({row['formato']}) — EBITDA {row['ebitda_pct']:.1f}%")

            st.markdown("#### 📦 Categorías con alta merma")
            cats_am = data_op.get("categorias_alta_merma", [])
            if cats_am:
                df_am = pd.DataFrame(cats_am)
                fig6 = px.bar(df_am, x="categoria", y="merma_pct",
                              color="merma_pct",
                              color_continuous_scale=["#EF9F27", "#E24B4A"],
                              labels={"merma_pct": "Merma %", "categoria": ""})
                fig6.add_hline(y=8, line_dash="dash", line_color="gray")
                fig6.update_layout(height=280, coloraxis_showscale=False)
                st.plotly_chart(fig6, use_container_width=True)

        with col_b:
            st.markdown("#### 💡 Acciones recomendadas")
            st.info("**Frutas y Verduras (14.9% merma)**\nRevisar planificación de compras y cadena de frío. Reducir al 10% genera ~S/. 180K en ahorro anual.")
            st.warning("**ABC Lince y San Miguel**\nAlto OPEX relativo. Revisar estructura de personal y renegociar alquileres en próximo ciclo.")
            st.success("**Panadería (45% margen bruto)**\nCategoría de mayor margen — oportunidad de ampliar surtido y aumentar participación en ventas totales.")
