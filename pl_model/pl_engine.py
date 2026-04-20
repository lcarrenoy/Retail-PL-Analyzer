"""
pl_engine.py
Motor de P&L para Retail-PL-Analyzer
Calcula rentabilidad por tienda, categoria, formato y periodo

Uso:
    uv run python pl_model/pl_engine.py
"""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_PATH = Path("data/sample")


def cargar_datos():
    """Carga los CSVs generados"""
    ventas   = pd.read_csv(DATA_PATH / "ventas_por_categoria.csv", parse_dates=["fecha"])
    opex     = pd.read_csv(DATA_PATH / "gastos_operativos.csv",    parse_dates=["fecha"])
    pl_base  = pd.read_csv(DATA_PATH / "pl_consolidado.csv",       parse_dates=["fecha"])
    tiendas  = pd.read_csv(DATA_PATH / "dim_tiendas.csv")
    cats     = pd.read_csv(DATA_PATH / "dim_categorias.csv")
    return ventas, opex, pl_base, tiendas, cats


def pl_por_tienda_mes(pl: pd.DataFrame) -> pd.DataFrame:
    """P&L mensual por tienda con todos los indicadores clave"""
    df = pl.copy()
    df["margen_neto"]     = df["ebitda"]
    df["margen_neto_pct"] = df["ebitda_pct"]
    df["opex_pct"]        = (df["total_opex"] / df["ventas"] * 100).round(2)
    df["ticket_promedio"] = (df["ventas"] / df["unidades"]).round(2)
    return df.sort_values(["fecha", "tienda_id"])


def pl_por_categoria(ventas: pd.DataFrame) -> pd.DataFrame:
    """Rentabilidad por categoria — sin opex (solo margen bruto y merma)"""
    df = ventas.groupby(["anio", "mes", "categoria_id", "categoria"]).agg(
        ventas=("ventas", "sum"),
        costo_ventas=("costo_ventas", "sum"),
        margen_bruto=("margen_bruto", "sum"),
        merma=("merma", "sum"),
        unidades=("unidades", "sum"),
    ).reset_index()
    df["margen_bruto_pct"] = (df["margen_bruto"] / df["ventas"] * 100).round(2)
    df["merma_pct"]        = (df["merma"]        / df["ventas"] * 100).round(2)
    df["margen_neto_cat"]  = (df["margen_bruto"] - df["merma"])
    df["margen_neto_pct"]  = (df["margen_neto_cat"] / df["ventas"] * 100).round(2)
    return df.sort_values(["anio", "mes", "categoria"])


def ranking_rentabilidad(pl: pd.DataFrame, periodo: str = "anual") -> pd.DataFrame:
    """
    Ranking de tiendas por rentabilidad
    periodo: 'anual' | 'mensual'
    """
    if periodo == "anual":
        grp = ["anio", "tienda_id", "tienda_nombre", "formato", "distrito", "nse"]
    else:
        grp = ["anio", "mes", "tienda_id", "tienda_nombre", "formato", "distrito", "nse"]

    df = pl.groupby(grp).agg(
        ventas=("ventas", "sum"),
        margen_bruto=("margen_bruto", "sum"),
        merma=("merma", "sum"),
        total_opex=("total_opex", "sum"),
        ebitda=("ebitda", "sum"),
        unidades=("unidades", "sum"),
    ).reset_index()

    df["margen_bruto_pct"] = (df["margen_bruto"] / df["ventas"] * 100).round(2)
    df["ebitda_pct"]       = (df["ebitda"]       / df["ventas"] * 100).round(2)
    df["merma_pct"]        = (df["merma"]         / df["ventas"] * 100).round(2)

    if periodo == "anual":
        df["rank"] = df.groupby("anio")["ebitda_pct"].rank(ascending=False).astype(int)
    else:
        df["rank"] = df.groupby(["anio", "mes"])["ebitda_pct"].rank(ascending=False).astype(int)

    return df.sort_values(["anio", "rank"] if periodo == "anual" else ["anio", "mes", "rank"])


def variacion_vs_periodo_anterior(pl: pd.DataFrame) -> pd.DataFrame:
    """Calcula variación % de ventas y EBITDA vs mes anterior"""
    df = pl.groupby(["fecha", "tienda_id", "tienda_nombre"]).agg(
        ventas=("ventas", "sum"),
        ebitda=("ebitda", "sum"),
    ).reset_index().sort_values(["tienda_id", "fecha"])

    df["ventas_ant"]     = df.groupby("tienda_id")["ventas"].shift(1)
    df["ebitda_ant"]     = df.groupby("tienda_id")["ebitda"].shift(1)
    df["var_ventas_pct"] = ((df["ventas"] - df["ventas_ant"]) / df["ventas_ant"] * 100).round(2)
    df["var_ebitda_pct"] = ((df["ebitda"] - df["ebitda_ant"]) / df["ebitda_ant"] * 100).round(2)

    return df.dropna(subset=["ventas_ant"])


def oportunidades_mejora(pl: pd.DataFrame, ventas: pd.DataFrame) -> dict:
    """
    Identifica oportunidades de mejora — inspirado en analisis de $500K+
    realizado en Manpower (91 cuentas corporativas)

    Retorna dict con:
    - tiendas_bajo_margen: tiendas con EBITDA < percentil 25
    - categorias_alta_merma: categorias con merma > 8% de ventas
    - tiendas_opex_alto: tiendas con opex > 35% de ventas
    """
    # Ranking anual último año
    rank = ranking_rentabilidad(pl, "anual")
    ultimo_anio = rank["anio"].max()
    rank_ultimo = rank[rank["anio"] == ultimo_anio]

    p25_ebitda = rank_ultimo["ebitda_pct"].quantile(0.25)
    tiendas_bajo = rank_ultimo[rank_ultimo["ebitda_pct"] < p25_ebitda][
        ["tienda_nombre", "formato", "ebitda_pct", "ventas"]
    ].to_dict("records")

    # Categorias con alta merma
    cats_merma = pl_por_categoria(ventas)
    cats_ultimo = cats_merma[cats_merma["anio"] == ultimo_anio]
    cats_agg = cats_ultimo.groupby("categoria").agg(
        ventas=("ventas", "sum"),
        merma=("merma", "sum"),
    ).reset_index()
    cats_agg["merma_pct"] = (cats_agg["merma"] / cats_agg["ventas"] * 100).round(2)
    alta_merma = cats_agg[cats_agg["merma_pct"] > 8][
        ["categoria", "merma_pct", "ventas"]
    ].sort_values("merma_pct", ascending=False).to_dict("records")

    # Tiendas con OPEX alto
    opex_alto = rank_ultimo[rank_ultimo["total_opex"] / rank_ultimo["ventas"] > 0.35][
        ["tienda_nombre", "formato", "ebitda_pct"]
    ].to_dict("records")

    impacto_potencial = rank_ultimo[rank_ultimo["ebitda_pct"] < p25_ebitda]["ventas"].sum() * 0.03

    return {
        "anio_analisis":        ultimo_anio,
        "tiendas_bajo_margen":  tiendas_bajo,
        "categorias_alta_merma": alta_merma,
        "tiendas_opex_alto":    opex_alto,
        "impacto_potencial_soles": round(impacto_potencial, 0),
    }


def resumen_ejecutivo(pl: pd.DataFrame) -> pd.DataFrame:
    """Resumen anual para dashboard ejecutivo"""
    df = pl.groupby("anio").agg(
        ventas=("ventas", "sum"),
        margen_bruto=("margen_bruto", "sum"),
        merma=("merma", "sum"),
        total_opex=("total_opex", "sum"),
        ebitda=("ebitda", "sum"),
        unidades=("unidades", "sum"),
    ).reset_index()

    df["margen_bruto_pct"] = (df["margen_bruto"] / df["ventas"] * 100).round(2)
    df["merma_pct"]        = (df["merma"]         / df["ventas"] * 100).round(2)
    df["opex_pct"]         = (df["total_opex"]    / df["ventas"] * 100).round(2)
    df["ebitda_pct"]       = (df["ebitda"]         / df["ventas"] * 100).round(2)
    df["crecimiento_pct"]  = (df["ventas"].pct_change() * 100).round(2)

    return df


def exportar_resultados(output_path: Path = Path("data/output")):
    """Corre todo el pipeline y exporta resultados listos para Power BI"""
    output_path.mkdir(parents=True, exist_ok=True)

    print("Cargando datos...")
    ventas, opex, pl_base, tiendas, cats = cargar_datos()

    print("Calculando P&L por tienda y mes...")
    pl_tienda = pl_por_tienda_mes(pl_base)
    pl_tienda.to_csv(output_path / "pl_tienda_mes.csv", index=False)

    print("Calculando P&L por categoria...")
    pl_cat = pl_por_categoria(ventas)
    pl_cat.to_csv(output_path / "pl_categoria.csv", index=False)

    print("Calculando ranking de rentabilidad...")
    rank = ranking_rentabilidad(pl_base, "anual")
    rank.to_csv(output_path / "ranking_rentabilidad.csv", index=False)

    print("Calculando variaciones vs periodo anterior...")
    variacion = variacion_vs_periodo_anterior(pl_base)
    variacion.to_csv(output_path / "variacion_vs_anterior.csv", index=False)

    print("Identificando oportunidades de mejora...")
    oportunidades = oportunidades_mejora(pl_base, ventas)

    print("Generando resumen ejecutivo...")
    resumen = resumen_ejecutivo(pl_base)
    resumen.to_csv(output_path / "resumen_ejecutivo.csv", index=False)

    # Imprimir hallazgos clave
    print("\n" + "="*55)
    print("HALLAZGOS CLAVE — Supermercados ABC")
    print("="*55)
    print(f"\nAnio de analisis: {oportunidades['anio_analisis']}")
    print(f"Impacto potencial identificado: S/. {oportunidades['impacto_potencial_soles']:,.0f}")

    print("\nTiendas con bajo margen:")
    for t in oportunidades["tiendas_bajo_margen"]:
        print(f"  - {t['tienda_nombre']} ({t['formato']}): EBITDA {t['ebitda_pct']:.1f}%")

    print("\nCategorias con alta merma (>8%):")
    for c in oportunidades["categorias_alta_merma"]:
        print(f"  - {c['categoria']}: {c['merma_pct']:.1f}% de merma")

    print(f"\nArchivos exportados en {output_path}/")
    print("  pl_tienda_mes.csv")
    print("  pl_categoria.csv")
    print("  ranking_rentabilidad.csv")
    print("  variacion_vs_anterior.csv")
    print("  resumen_ejecutivo.csv")

    return {
        "pl_tienda":    pl_tienda,
        "pl_categoria": pl_cat,
        "ranking":      rank,
        "variacion":    variacion,
        "oportunidades": oportunidades,
        "resumen":      resumen,
    }


if __name__ == "__main__":
    exportar_resultados()
