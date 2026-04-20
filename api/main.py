"""
main.py
API REST para Retail-PL-Analyzer
Expone endpoints de P&L consumibles desde Power BI o el agente LLM

Uso:
    uv add fastapi uvicorn
    uv run uvicorn api.main:app --reload
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import pandas as pd
import numpy as np
import math
import sys


def clean(obj):
    """Convierte NaN, numpy types a tipos JSON-serializables"""
    if isinstance(obj, list):
        return [clean(i) for i in obj]
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if math.isnan(float(obj)) else float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj

sys.path.append(str(Path(__file__).parent.parent))
from pl_model.pl_engine import (
    cargar_datos,
    pl_por_tienda_mes,
    pl_por_categoria,
    ranking_rentabilidad,
    variacion_vs_periodo_anterior,
    oportunidades_mejora,
    resumen_ejecutivo,
)

app = FastAPI(
    title="Retail P&L Analyzer API",
    description="API de rentabilidad por tienda y categoria — Supermercados ABC",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cargar datos al iniciar
ventas, opex, pl_base, tiendas, cats = cargar_datos()
pl_tienda   = pl_por_tienda_mes(pl_base)
pl_cat      = pl_por_categoria(ventas)
rank_anual  = ranking_rentabilidad(pl_base, "anual")
variacion   = variacion_vs_periodo_anterior(pl_base)
oport       = oportunidades_mejora(pl_base, ventas)
resumen     = resumen_ejecutivo(pl_base)


@app.get("/")
def root():
    return {"status": "ok", "proyecto": "Retail P&L Analyzer", "version": "1.0.0"}


@app.get("/resumen")
def get_resumen():
    """Resumen ejecutivo anual — para dashboard principal"""
    return clean(resumen.to_dict("records"))


@app.get("/tiendas")
def get_tiendas(
    anio: int = Query(None, description="Filtrar por año (2022-2024)"),
    formato: str = Query(None, description="Express | Supermarket"),
    nse: str = Query(None, description="AB | BC"),
):
    """P&L mensual por tienda con filtros opcionales"""
    df = pl_tienda.copy()
    df["fecha"] = df["fecha"].astype(str)
    if anio:
        df = df[df["anio"] == anio]
    if formato:
        df = df[df["formato"] == formato]
    if nse:
        df = df[df["nse"] == nse]
    if df.empty:
        raise HTTPException(404, "No se encontraron datos con esos filtros")
    return df.to_dict("records")


@app.get("/categorias")
def get_categorias(
    anio: int = Query(None),
    categoria: str = Query(None),
):
    """P&L por categoría de producto"""
    df = pl_cat.copy()
    if anio:
        df = df[df["anio"] == anio]
    if categoria:
        df = df[df["categoria"].str.contains(categoria, case=False)]
    if df.empty:
        raise HTTPException(404, "No se encontraron datos")
    return df.to_dict("records")


@app.get("/ranking")
def get_ranking(
    anio: int = Query(None),
    top: int = Query(5, description="Top N tiendas"),
):
    """Ranking de tiendas por EBITDA"""
    df = rank_anual.copy()
    if anio:
        df = df[df["anio"] == anio]
    else:
        df = df[df["anio"] == df["anio"].max()]
    return df.head(top).to_dict("records")


@app.get("/variacion")
def get_variacion(tienda_id: str = Query(None)):
    """Variación mensual vs período anterior"""
    df = variacion.copy()
    df["fecha"] = df["fecha"].astype(str)
    if tienda_id:
        df = df[df["tienda_id"] == tienda_id]
    return df.to_dict("records")


@app.get("/oportunidades")
def get_oportunidades():
    """Oportunidades de mejora identificadas"""
    return clean({
        "anio_analisis": oport["anio_analisis"],
        "impacto_potencial_soles": oport["impacto_potencial_soles"],
        "tiendas_bajo_margen": oport["tiendas_bajo_margen"],
        "categorias_alta_merma": oport["categorias_alta_merma"],
        "tiendas_opex_alto": oport["tiendas_opex_alto"],
    })


@app.get("/tiendas/{tienda_id}")
def get_tienda_detalle(tienda_id: str, anio: int = Query(None)):
    """Detalle completo de una tienda específica"""
    df = pl_tienda[pl_tienda["tienda_id"] == tienda_id.upper()].copy()
    df["fecha"] = df["fecha"].astype(str)
    if anio:
        df = df[df["anio"] == anio]
    if df.empty:
        raise HTTPException(404, f"Tienda {tienda_id} no encontrada")
    return {
        "tienda_id": tienda_id.upper(),
        "tienda_nombre": df["tienda_nombre"].iloc[0],
        "formato": df["formato"].iloc[0],
        "distrito": df["distrito"].iloc[0],
        "nse": df["nse"].iloc[0],
        "data": df.to_dict("records"),
    }
