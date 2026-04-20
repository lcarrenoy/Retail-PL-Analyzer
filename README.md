# Retail P&L Analyzer — Category & Store Profitability

> Modelo de P&L desagregado por tienda y categoría para retail. Pipeline Python/SQL de datos de ventas, merma y gastos operativos con dashboard interactivo y agente LLM conversacional sobre rentabilidad.

[![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.56-red?logo=streamlit)](https://streamlit.io)
[![LangChain](https://img.shields.io/badge/LangChain-1.2-purple)](https://langchain.com)
[![Claude API](https://img.shields.io/badge/Claude-Sonnet_4-orange)](https://anthropic.com)

---

## Demo

🚀 **[Dashboard en Streamlit Cloud](https://retail-pl-analyzer.streamlit.app)**
---

## Arquitectura

```
data/sample/          →   pl_model/pl_engine.py   →   api/main.py (FastAPI)
  ventas_por_cat.csv                                      ↓              ↓
  gastos_opex.csv       6 tablas de análisis       dashboard/        agent/
  pl_consolidado.csv    exportadas a data/output/  dashboard.py      pl_agent.py
  dim_tiendas.csv                                  (Streamlit)       (LangChain +
  dim_categorias.csv                                                   Claude API)
```

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Datos | Python · pandas · numpy |
| P&L Engine | pandas · numpy |
| API | FastAPI · uvicorn |
| Dashboard | Streamlit · Plotly |
| Agente LLM | LangChain · LangGraph · Claude API |
| Entorno | uv · pyproject.toml |

---

## Estructura del repositorio

```
Retail-PL-Analyzer/
├── data/
│   ├── sample/          ← CSVs sintéticos generados
│   └── output/          ← tablas procesadas por pl_engine
├── pl_model/
│   └── pl_engine.py     ← motor de P&L: márgenes, merma, EBITDA, oportunidades
├── api/
│   └── main.py          ← FastAPI con 7 endpoints REST
├── dashboard/
│   └── dashboard.py     ← dashboard Streamlit con 4 tabs
├── agent/
│   └── pl_agent.py      ← agente LLM conversacional
├── generate_synthetic_data.py
├── pyproject.toml
├── uv.lock
├── .env.example
└── README.md
```

---

## Cómo ejecutar

### 1. Clonar y configurar entorno

```bash
git clone https://github.com/lcarrenoy/Retail-PL-Analyzer
cd Retail-PL-Analyzer
uv sync
cp .env.example .env
# Agrega tu ANTHROPIC_API_KEY en .env
```

### 2. Generar datos sintéticos

```bash
uv run python generate_synthetic_data.py
```

Genera 5 CSVs con datos de **Supermercados ABC** (ficticio):
- 10 tiendas en Lima (Express y Supermarket, NSE AB y BC)
- 10 categorías de productos
- 36 meses de historia (2022–2024)
- S/. 482M en ventas totales simuladas

### 3. Ejecutar el P&L engine

```bash
uv run python pl_model/pl_engine.py
```

### 4. Levantar la API

```bash
uv run uvicorn api.main:app --reload
# Docs en: http://localhost:8000/docs
```

### 5. Levantar el dashboard

```bash
uv run streamlit run dashboard/dashboard.py
# Abre: http://localhost:8501
```

### 6. Ejecutar el agente LLM

```bash
uv run python agent/pl_agent.py
```

---

## Endpoints de la API

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/resumen` | Resumen ejecutivo anual |
| GET | `/tiendas` | P&L mensual por tienda (filtros: año, formato, NSE) |
| GET | `/tiendas/{id}` | Detalle de una tienda específica |
| GET | `/categorias` | P&L por categoría de producto |
| GET | `/ranking` | Ranking de tiendas por EBITDA |
| GET | `/variacion` | Variación mensual vs período anterior |
| GET | `/oportunidades` | Oportunidades de mejora identificadas |

---

## Hallazgos clave (2024)

- **S/. 173.8M** en ventas totales · **+8.8%** crecimiento vs 2023
- **EBITDA promedio: 18.8%** · Margen bruto: 29.2%
- **Tiendas con bajo margen:** ABC Pueblo Libre (18.0%), ABC San Miguel (18.1%), ABC Lince (18.5%)
- **Categorías con alta merma:** Frutas y Verduras (14.9%), Panadería (12.1%), Carnes y Pescados (10.2%)
- **Impacto potencial identificado: S/. 1,614,756**

---

## Ejemplo del agente conversacional

```
Tu: ¿Qué categoría tiene mayor merma y cuánto impacto tiene en el P&L?

Agente: Frutas y Verduras es la categoría con mayor merma, alcanzando un 14.9%
en 2024. Con ventas de S/. 17.4M esto representa S/. 2.6M perdidos por
deterioro. La reducción al 10% generaría ~S/. 180K en ahorro anual directo
en EBITDA. Prioridad estratégica: optimizar rotación de inventario y
mejorar pronósticos de demanda para perecibles.
```

---

## Roadmap

- [ ] Deploy en Streamlit Cloud
- [ ] Integración con Power BI vía endpoints REST
- [ ] Reporte ejecutivo en Quarto (GitHub Pages)
- [ ] Modelos dbt para transformación de datos
- [ ] Dockerización del stack completo

---

*Proyecto de [Luis Carreño](https://github.com/lcarrenoy) · Ingeniero Industrial · MSc Financial Engineering*
