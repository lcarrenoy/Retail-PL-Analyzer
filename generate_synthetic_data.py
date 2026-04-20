"""
generate_synthetic_data.py
Genera datos sintéticos de Supermercados ABC para Retail-PL-Analyzer
Simula 3 años de data (2022-2024) con lógica de negocio realista

Uso:
    pip install faker pandas numpy
    python generate_synthetic_data.py
"""

import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import datetime, timedelta
import os

fake = Faker("es_ES")
np.random.seed(42)
random.seed(42)

# ── Configuración del negocio ────────────────────────────────
TIENDAS = [
    {"id": "T01", "nombre": "ABC Miraflores",    "formato": "Express",    "distrito": "Miraflores",    "nse": "AB"},
    {"id": "T02", "nombre": "ABC San Isidro",    "formato": "Express",    "distrito": "San Isidro",    "nse": "AB"},
    {"id": "T03", "nombre": "ABC Surco",          "formato": "Supermarket","distrito": "Surco",         "nse": "AB"},
    {"id": "T04", "nombre": "ABC La Molina",      "formato": "Supermarket","distrito": "La Molina",     "nse": "AB"},
    {"id": "T05", "nombre": "ABC San Borja",      "formato": "Express",    "distrito": "San Borja",     "nse": "AB"},
    {"id": "T06", "nombre": "ABC Barranco",       "formato": "Express",    "distrito": "Barranco",      "nse": "BC"},
    {"id": "T07", "nombre": "ABC Pueblo Libre",   "formato": "Supermarket","distrito": "Pueblo Libre",  "nse": "BC"},
    {"id": "T08", "nombre": "ABC Jesus Maria",    "formato": "Supermarket","distrito": "Jesus Maria",   "nse": "BC"},
    {"id": "T09", "nombre": "ABC Lince",          "formato": "Express",    "distrito": "Lince",         "nse": "BC"},
    {"id": "T10", "nombre": "ABC San Miguel",     "formato": "Supermarket","distrito": "San Miguel",    "nse": "BC"},
]

CATEGORIAS = [
    {"id": "C01", "nombre": "Abarrotes",         "margen_base": 0.18, "merma_base": 0.02},
    {"id": "C02", "nombre": "Perecibles",         "margen_base": 0.28, "merma_base": 0.08},
    {"id": "C03", "nombre": "Bebidas",            "margen_base": 0.22, "merma_base": 0.01},
    {"id": "C04", "nombre": "Lacteos",            "margen_base": 0.20, "merma_base": 0.05},
    {"id": "C05", "nombre": "Carnes y Pescados",  "margen_base": 0.32, "merma_base": 0.10},
    {"id": "C06", "nombre": "Panaderia",          "margen_base": 0.45, "merma_base": 0.12},
    {"id": "C07", "nombre": "Limpieza",           "margen_base": 0.25, "merma_base": 0.01},
    {"id": "C08", "nombre": "Cuidado Personal",   "margen_base": 0.35, "merma_base": 0.01},
    {"id": "C09", "nombre": "Congelados",         "margen_base": 0.30, "merma_base": 0.03},
    {"id": "C10", "nombre": "Frutas y Verduras",  "margen_base": 0.38, "merma_base": 0.15},
]

# Factores por formato
FACTORES_FORMATO = {
    "Express":     {"ventas": 0.65, "personal": 0.55, "alquiler": 0.70},
    "Supermarket": {"ventas": 1.35, "personal": 1.45, "alquiler": 1.30},
}

# Factores por NSE
FACTORES_NSE = {
    "AB": {"precio": 1.15, "ticket": 1.20},
    "BC": {"precio": 1.00, "ticket": 1.00},
}

# Estacionalidad mensual (índice)
ESTACIONALIDAD = {
    1: 0.85, 2: 0.80, 3: 0.90, 4: 0.88,
    5: 0.92, 6: 0.95, 7: 0.98, 8: 0.97,
    9: 0.95, 10: 1.00, 11: 1.10, 12: 1.35
}


def generar_ventas_mensuales():
    """Genera tabla de ventas mensuales por tienda y categoría"""
    registros = []
    fechas = pd.date_range("2022-01-01", "2024-12-31", freq="MS")

    for fecha in fechas:
        for tienda in TIENDAS:
            for cat in CATEGORIAS:
                fmt = tienda["formato"]
                nse = tienda["nse"]

                # Ventas base
                venta_base = random.uniform(80_000, 150_000)
                venta_base *= FACTORES_FORMATO[fmt]["ventas"]
                venta_base *= FACTORES_NSE[nse]["precio"]
                venta_base *= ESTACIONALIDAD[fecha.month]

                # Tendencia crecimiento anual ~8%
                anos_desde_inicio = (fecha.year - 2022) + (fecha.month - 1) / 12
                venta_base *= (1 + 0.08) ** anos_desde_inicio

                # Ruido aleatorio ±10%
                venta_base *= random.uniform(0.90, 1.10)

                # Costo de ventas
                margen = cat["margen_base"] * random.uniform(0.85, 1.15)
                costo_ventas = venta_base * (1 - margen)

                # Merma
                merma_pct = cat["merma_base"] * random.uniform(0.80, 1.20)
                merma = venta_base * merma_pct

                # Unidades vendidas
                precio_unitario = random.uniform(8, 45) * FACTORES_NSE[nse]["precio"]
                unidades = int(venta_base / precio_unitario)

                registros.append({
                    "fecha":         fecha.strftime("%Y-%m-%d"),
                    "anio":          fecha.year,
                    "mes":           fecha.month,
                    "tienda_id":     tienda["id"],
                    "tienda_nombre": tienda["nombre"],
                    "formato":       tienda["formato"],
                    "distrito":      tienda["distrito"],
                    "nse":           tienda["nse"],
                    "categoria_id":  cat["id"],
                    "categoria":     cat["nombre"],
                    "ventas":        round(venta_base, 2),
                    "costo_ventas":  round(costo_ventas, 2),
                    "margen_bruto":  round(venta_base - costo_ventas, 2),
                    "merma":         round(merma, 2),
                    "unidades":      unidades,
                    "precio_promedio": round(precio_unitario, 2),
                })

    return pd.DataFrame(registros)


def generar_gastos_operativos():
    """Genera gastos operativos mensuales por tienda"""
    registros = []
    fechas = pd.date_range("2022-01-01", "2024-12-31", freq="MS")

    for fecha in fechas:
        for tienda in TIENDAS:
            fmt = tienda["formato"]

            # Personal
            personal_base = random.uniform(25_000, 35_000)
            personal = personal_base * FACTORES_FORMATO[fmt]["personal"]
            personal *= (1 + 0.05) ** ((fecha.year - 2022) + (fecha.month - 1) / 12)

            # Alquiler (fijo con ajuste anual)
            alquiler_base = random.uniform(15_000, 22_000)
            alquiler = alquiler_base * FACTORES_FORMATO[fmt]["alquiler"]
            alquiler *= (1 + 0.03) ** (fecha.year - 2022)

            # Servicios (luz, agua, etc.)
            servicios = random.uniform(4_000, 8_000) * FACTORES_FORMATO[fmt]["ventas"]

            # Logística
            logistica = random.uniform(3_000, 6_000) * FACTORES_FORMATO[fmt]["ventas"]

            # Mantenimiento
            mantenimiento = random.uniform(1_500, 3_500)

            # Otros gastos
            otros = random.uniform(1_000, 2_500)

            registros.append({
                "fecha":          fecha.strftime("%Y-%m-%d"),
                "anio":           fecha.year,
                "mes":            fecha.month,
                "tienda_id":      tienda["id"],
                "tienda_nombre":  tienda["nombre"],
                "formato":        tienda["formato"],
                "distrito":       tienda["distrito"],
                "personal":       round(personal, 2),
                "alquiler":       round(alquiler, 2),
                "servicios":      round(servicios, 2),
                "logistica":      round(logistica, 2),
                "mantenimiento":  round(mantenimiento, 2),
                "otros":          round(otros, 2),
                "total_opex":     round(personal + alquiler + servicios + logistica + mantenimiento + otros, 2),
            })

    return pd.DataFrame(registros)


def generar_pl_consolidado(df_ventas, df_opex):
    """Consolida ventas y opex en un P&L por tienda y mes"""
    ventas_agg = df_ventas.groupby(
        ["fecha", "anio", "mes", "tienda_id", "tienda_nombre", "formato", "distrito", "nse"]
    ).agg(
        ventas=("ventas", "sum"),
        costo_ventas=("costo_ventas", "sum"),
        margen_bruto=("margen_bruto", "sum"),
        merma=("merma", "sum"),
        unidades=("unidades", "sum"),
    ).reset_index()

    pl = ventas_agg.merge(
        df_opex[["fecha", "tienda_id", "personal", "alquiler", "servicios",
                 "logistica", "mantenimiento", "otros", "total_opex"]],
        on=["fecha", "tienda_id"], how="left"
    )

    pl["ebitda"] = pl["margen_bruto"] - pl["merma"] - pl["total_opex"]
    pl["margen_bruto_pct"] = (pl["margen_bruto"] / pl["ventas"] * 100).round(2)
    pl["merma_pct"] = (pl["merma"] / pl["ventas"] * 100).round(2)
    pl["ebitda_pct"] = (pl["ebitda"] / pl["ventas"] * 100).round(2)

    return pl


def main():
    print("Generando datos sinteticos de Supermercados ABC...")

    os.makedirs("data/sample", exist_ok=True)

    print("  [1/4] Generando ventas por tienda y categoria...")
    df_ventas = generar_ventas_mensuales()
    df_ventas.to_csv("data/sample/ventas_por_categoria.csv", index=False)
    print(f"        {len(df_ventas):,} registros → ventas_por_categoria.csv")

    print("  [2/4] Generando gastos operativos...")
    df_opex = generar_gastos_operativos()
    df_opex.to_csv("data/sample/gastos_operativos.csv", index=False)
    print(f"        {len(df_opex):,} registros → gastos_operativos.csv")

    print("  [3/4] Consolidando P&L...")
    df_pl = generar_pl_consolidado(df_ventas, df_opex)
    df_pl.to_csv("data/sample/pl_consolidado.csv", index=False)
    print(f"        {len(df_pl):,} registros → pl_consolidado.csv")

    print("  [4/4] Guardando dimensiones...")
    pd.DataFrame(TIENDAS).to_csv("data/sample/dim_tiendas.csv", index=False)
    pd.DataFrame(CATEGORIAS).to_csv("data/sample/dim_categorias.csv", index=False)

    print("\n  RESUMEN:")
    print(f"  Tiendas:     {len(TIENDAS)}")
    print(f"  Categorias:  {len(CATEGORIAS)}")
    print(f"  Meses:       36 (2022-2024)")
    print(f"  Registros ventas: {len(df_ventas):,}")
    print(f"  Ventas totales:  S/. {df_ventas['ventas'].sum():,.0f}")
    print(f"\n  Archivos en data/sample/")
    print("  Listo para el pipeline dbt y Power BI")


if __name__ == "__main__":
    main()
