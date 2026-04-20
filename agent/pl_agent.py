"""
pl_agent.py
Agente conversacional para consultas en lenguaje natural sobre el P&L
Usa LangGraph + Claude API como LLM

Uso:
    uv run python agent/pl_agent.py
"""

import os
import json
import requests
from dotenv import load_dotenv

from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

API = "http://localhost:8000"


# ── Tools que el agente puede usar ──────────────────────────

@tool
def obtener_resumen_ejecutivo() -> str:
    """
    Obtiene el resumen ejecutivo anual de Supermercados ABC.
    Incluye ventas totales, margen bruto, EBITDA, merma y crecimiento por año.
    Usar cuando pregunten por resultados generales, totales o tendencias anuales.
    """
    r = requests.get(f"{API}/resumen")
    return json.dumps(r.json(), ensure_ascii=False, indent=2)


@tool
def obtener_ranking_tiendas(anio: int = 2024) -> str:
    """
    Obtiene el ranking de tiendas por EBITDA para un año dado.
    Usar cuando pregunten por las mejores o peores tiendas, o por rentabilidad por tienda.
    anio: año de analisis (2022, 2023 o 2024)
    """
    r = requests.get(f"{API}/ranking", params={"anio": anio, "top": 10})
    return json.dumps(r.json(), ensure_ascii=False, indent=2)


@tool
def obtener_categorias(anio: int = 2024) -> str:
    """
    Obtiene rentabilidad por categoria de producto.
    Usar cuando pregunten por categorias, margen por producto, merma por tipo de producto.
    anio: 2022, 2023 o 2024
    """
    r = requests.get(f"{API}/categorias", params={"anio": anio})
    data = r.json()
    cats = {}
    for row in data:
        cat = row["categoria"]
        if cat not in cats:
            cats[cat] = {"ventas": 0, "margen_bruto": 0, "merma": 0}
        cats[cat]["ventas"]       += row.get("ventas", 0)
        cats[cat]["margen_bruto"] += row.get("margen_bruto", 0)
        cats[cat]["merma"]        += row.get("merma", 0)
    resultado = []
    for cat, vals in cats.items():
        ventas = vals["ventas"]
        resultado.append({
            "categoria": cat,
            "ventas": round(ventas, 0),
            "margen_bruto_pct": round(vals["margen_bruto"] / ventas * 100, 1) if ventas else 0,
            "merma_pct": round(vals["merma"] / ventas * 100, 1) if ventas else 0,
        })
    resultado.sort(key=lambda x: x["margen_bruto_pct"], reverse=True)
    return json.dumps(resultado, ensure_ascii=False, indent=2)


@tool
def obtener_oportunidades() -> str:
    """
    Obtiene las oportunidades de mejora identificadas automaticamente.
    Incluye tiendas con bajo margen, categorias con alta merma e impacto potencial en soles.
    Usar cuando pregunten por oportunidades, problemas, tiendas que mejorar o impacto financiero.
    """
    r = requests.get(f"{API}/oportunidades")
    return json.dumps(r.json(), ensure_ascii=False, indent=2)


@tool
def obtener_detalle_tienda(tienda: str, anio: int = 2024) -> str:
    """
    Obtiene el detalle completo de una tienda especifica por nombre o ID.
    Tiendas disponibles: Miraflores (T01), San Isidro (T02), Surco (T03),
    La Molina (T04), San Borja (T05), Barranco (T06), Pueblo Libre (T07),
    Jesus Maria (T08), Lince (T09), San Miguel (T10).
    """
    nombre_a_id = {
        "miraflores": "T01", "san isidro": "T02", "surco": "T03",
        "la molina": "T04", "san borja": "T05", "barranco": "T06",
        "pueblo libre": "T07", "jesus maria": "T08", "lince": "T09",
        "san miguel": "T10",
    }
    tid = nombre_a_id.get(tienda.lower().strip(), tienda.upper())
    r = requests.get(f"{API}/tiendas/{tid}", params={"anio": anio})
    if r.status_code == 404:
        return f"Tienda '{tienda}' no encontrada."
    data = r.json()
    data["data"] = data.get("data", [])[:6]
    return json.dumps(data, ensure_ascii=False, indent=2)


# ── Configuracion del agente ─────────────────────────────────

tools = [
    obtener_resumen_ejecutivo,
    obtener_ranking_tiendas,
    obtener_categorias,
    obtener_oportunidades,
    obtener_detalle_tienda,
]

llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0,
    max_tokens=2048,
)

SYSTEM_PROMPT = """Eres un analista financiero senior especializado en retail.
Tienes acceso a los datos de P&L de Supermercados ABC: 10 tiendas en Lima,
10 categorias de productos, 3 anos de historia (2022-2024).

Cuando respondas:
- Se directo y usa los datos reales de las herramientas
- Expresa ventas en millones de soles (S/. XM)
- Redondea porcentajes a 1 decimal
- Identifica siempre las implicancias para el negocio
- Responde en espanol"""

agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)


def chat(pregunta: str, historial: list = None) -> str:
    """Ejecuta una pregunta y retorna la respuesta"""
    if historial is None:
        historial = []
    messages = historial + [HumanMessage(content=pregunta)]
    result = agent.invoke({"messages": messages})
    return result["messages"][-1].content


# ── CLI interactivo ──────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*55)
    print("Retail P&L Analyzer — Agente Conversacional")
    print("Supermercados ABC | LangGraph + Claude API")
    print("="*55)
    print("Escribe tu pregunta o 'salir' para terminar\n")
    print("Ejemplos:")
    print("  - Cuales son las tiendas con menor EBITDA?")
    print("  - Que categoria tiene mayor merma?")
    print("  - Cuanto crecieron las ventas en 2024?")
    print("  - Cual es el impacto potencial de mejora?\n")

    historial = []

    while True:
        try:
            pregunta = input("Tu: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nHasta luego.")
            break

        if not pregunta:
            continue
        if pregunta.lower() in ["salir", "exit", "quit"]:
            print("Hasta luego.")
            break

        print("\nAgente: ", end="", flush=True)
        try:
            respuesta = chat(pregunta, historial)
            print(respuesta)
            historial.append(HumanMessage(content=pregunta))
            historial.append(AIMessage(content=respuesta))
        except Exception as e:
            print(f"Error: {e}")
        print()
