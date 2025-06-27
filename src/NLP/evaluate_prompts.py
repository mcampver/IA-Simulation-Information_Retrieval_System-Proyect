# evaluate_prompts.py (Versión Final Corregida)

import os
import json
import re
import time
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Asumiendo que tu archivo Gemini.py está en una carpeta src/NLP/
# y que ejecutas esto desde la raíz del proyecto.
# Ajusta la importación si tu estructura de carpetas es diferente.
try:
    from src.NLP.Gemini import Gemini
except ImportError:
    # Fallback si el script se ejecuta desde la misma carpeta que Gemini.py
    from Gemini import Gemini


# --- 1. CONFIGURACIÓN ---
# Inicializar el cliente de Gemini
gemini_client = Gemini()

# --- 2. DEFINICIÓN DE PROMPTS ---

def get_optimized_prompt(depot_info, targets_info, user_description, solver='vns_solver'):
    """
    Genera el prompt optimizado (Versión 2).
    Esta versión delega la resolución de ambigüedades a la IA para mejorar la precisión.
    """
    # --- INICIO DE LA MODIFICACIÓN ---

    # 1. ELIMINAMOS el pre-procesamiento con expresiones regulares.
    #    Ya no intentaremos adivinar el número de camiones en Python.
    #
    # match = re.search(r'(\d+)\s+camiones', user_description, re.IGNORECASE)
    # explicit_trucks = int(match.group(1)) if match else None
    # header_trucks = ""
    # if explicit_trucks is not None: ...

    # 2. CREAMOS una instrucción más inteligente que enseña a la IA cómo actuar.
    num_trucks_instruction = (
        "Determina el número de camiones. Si el usuario menciona varios números o se corrige a sí mismo "
        "(ejemplo: 'necesito 2 camiones, no, perdón, 3'), **utiliza siempre la cifra final o la corrección más reciente**. "
        "Si no se especifica un número, sugiere uno que sea razonable para la tarea."
    )

    # --- FIN DE LA MODIFICACIÓN ---

    targets_str = "\n".join([f"  - Nodo ID: {t['id']} - Coordenadas: {t['position']}" for t in targets_info])

    # El prompt ahora no tiene el {header_trucks} y usa la nueva instrucción.
    return f"""
    Analiza la siguiente descripción de un problema CVRP y extrae los parámetros.

    CONTEXTO:
    - Depósito: Nodo {depot_info['id']} en {depot_info['position']}
    - Destinos ({len(targets_info)}):
{targets_str}
    - Algoritmo a usar: {solver}

    DESCRIPCIÓN DEL USUARIO:
    "{user_description}"

    TAREAS:
    1. NÚMERO DE CAMIONES: {num_trucks_instruction}
    2. CAPACIDADES DE LOS CAMIONES: ¿Cuál es la capacidad de cada camión? Si no se especifica, sugiere capacidades razonables.
    3. DEMANDAS DE LOS DESTINOS: ¿Cuál es la demanda de cada destino? Si no se especifica, sugiere demandas razonables.
    4. OBSERVACIONES: Cualquier información relevante inferida.

    Responde ÚNICAMENTE con un objeto JSON en este formato exacto, sin texto adicional:
    {{
        "num_trucks": <integer>,
        "truck_capacities": [<lista de integers>],
        "target_demands": [<lista de integers>],
        "reasoning": {{
            "num_trucks_reason": "explicación",
            "capacities_reason": "explicación",
            "demands_reason": "explicación"
        }},
        "observations": "observaciones"
    }}

    REGLAS IMPORTANTES:
    - La lista `truck_capacities` debe tener `num_trucks` elementos.
    - La lista `target_demands` debe tener {len(targets_info)} elementos.
    - Todos los números deben ser enteros positivos.
    """
    
# def get_optimized_prompt(depot_info, targets_info, user_description, solver='vns_solver'):
#     """
#     Genera el prompt optimizado, basado en tu cvrp_assistant.py.
#     Esta es la versión 'buena' y controlada.
#     """
#     match = re.search(r'(\d+)\s+camiones', user_description, re.IGNORECASE)
#     explicit_trucks = int(match.group(1)) if match else None

#     header_trucks = ""
#     if explicit_trucks is not None:
#         header_trucks = (
#             f"El usuario ha indicado que tiene EXACTAMENTE "
#             f"{explicit_trucks} camiones disponibles.\n\n"
#         )

#     num_trucks_instruction = (
#         f"Usa EXACTAMENTE los {explicit_trucks} camiones que el usuario especificó."
#         if explicit_trucks is not None
#         else f"Sugiere un número razonable de vehículos basado en los {len(targets_info)} destinos."
#     )

#     # Convertimos la lista de targets a un string más legible para el prompt
#     targets_str = "\n".join([f"  - Nodo ID: {t['id']} - Coordenadas: {t['position']}" for t in targets_info])

#     return f"""
#     {header_trucks}
#     Analiza la siguiente descripción de un problema CVRP y extrae los parámetros.

#     CONTEXTO:
#     - Depósito: Nodo {depot_info['id']} en {depot_info['position']}
#     - Destinos ({len(targets_info)}):
# {targets_str}
#     - Algoritmo a usar: {solver}

#     DESCRIPCIÓN DEL USUARIO:
#     "{user_description}"

#     TAREAS:
#     1. NÚMERO DE CAMIONES: {num_trucks_instruction}
#     2. CAPACIDADES DE LOS CAMIONES: ¿Cuál es la capacidad de cada camión? Si no se especifica, sugiere capacidades razonables.
#     3. DEMANDAS DE LOS DESTINOS: ¿Cuál es la demanda de cada destino? Si no se especifica, sugiere demandas razonables.
#     4. OBSERVACIONES: Cualquier información relevante inferida.

#     Responde ÚNICAMENTE con un objeto JSON en este formato exacto, sin texto adicional:
#     {{
#         "num_trucks": <integer>,
#         "truck_capacities": [<lista de integers>],
#         "target_demands": [<lista de integers>],
#         "reasoning": {{
#             "num_trucks_reason": "explicación",
#             "capacities_reason": "explicación",
#             "demands_reason": "explicación"
#         }},
#         "observations": "observaciones"
#     }}

#     REGLAS IMPORTANTES:
#     - La lista `truck_capacities` debe tener `num_trucks` elementos.
#     - La lista `target_demands` debe tener {len(targets_info)} elementos.
#     - Todos los números deben ser enteros positivos.
#     """

def get_weak_prompt(depot_info, targets_info, user_description, solver='vns_solver'):
    """
    Genera un prompt de calidad media.
    A veces puede funcionar, pero es propenso a errores sutiles.
    """
    targets_str = "\n".join([f"  - Nodo ID: {t['id']}" for t in targets_info])
    return f"""
    Análisis de Logística para CVRP.
    Datos de entrada:
    - Depósito: {depot_info['id']}
    - Destinos:
{targets_str}
    - Descripción del cliente: "{user_description}"
    Por favor, analiza la descripción y devuelve un objeto JSON con los siguientes campos:
    - num_trucks: el número de camiones que crees que se necesitan.
    - truck_capacities: las capacidades para esos camiones.
    - target_demands: las demandas para los destinos.
    Intenta ser preciso.
    """

# --- 3. CASOS DE PRUEBA ---

DEPOT_INFO = {"id": 1000, "position": [-82.36, 23.11]}
TARGETS_INFO = [
    {"id": 2001, "position": [-82.37, 23.12]},
    {"id": 2002, "position": [-82.35, 23.13]},
    {"id": 2003, "position": [-82.38, 23.10]},
]

test_cases = [
    {
        "name": "Explícito y Simple",
        "description": "Necesito 2 camiones para repartir a 3 tiendas. Cada camión tiene una capacidad de 100. Las demandas son 30, 40 y 50.",
        "targets": TARGETS_INFO,
        "expected": {"num_trucks": 2}
    },
    {
        "name": "Número de camiones implícito",
        "description": "Tengo que entregar 150 unidades en total a 3 tiendas. Mis camiones son pequeños, de capacidad 60.",
        "targets": TARGETS_INFO,
        "expected": {"num_trucks": 3}
    },
    {
        "name": "Número de camiones explícito (control)",
        "description": "Tengo exactamente 3 camiones con capacidad de 80 cada uno para repartir a estas 3 localizaciones.",
        "targets": TARGETS_INFO,
        "expected": {"num_trucks": 3}
    },
    {
        "name": "Información conflictiva",
        "description": "Tengo 2 camiones, no, mejor dicho, 1 camión grande con capacidad de 200. Las demandas para las 3 tiendas son muy altas.",
        "targets": TARGETS_INFO,
        "expected": {"num_trucks": 1}
    },
    {
        "name": "Información irrelevante (distractor)",
        "description": "Hoy es un día soleado en La Habana. Mi jefe, que es muy estricto, me pidió usar los 4 camiones de la empresa para repartir a 3 puntos. No importa si es ineficiente.",
        "targets": TARGETS_INFO,
        "expected": {"num_trucks": 4}
    }
]

# --- 4. MOTOR DE EVALUACIÓN ---

def run_evaluation():
    results = []
    prompts = {
        "Optimized": get_optimized_prompt,
        "Weak": get_weak_prompt
    }

    for case in test_cases:
        print(f"--- Ejecutando caso: {case['name']} ---")
        for prompt_name, prompt_func in prompts.items():
            print(f"  > Usando prompt: {prompt_name}")
            prompt_text = prompt_func(DEPOT_INFO, case['targets'], case['description'])
            time.sleep(2)
            response_text = gemini_client.ask(prompt_text)
            metrics = analyze_response(response_text, case['expected'], len(case['targets']))
            results.append({
                "case_name": case['name'],
                "prompt_type": prompt_name,
                **metrics
            })
    return pd.DataFrame(results)

# --- 5. ANÁLISIS DE MÉTRICAS ---

def analyze_response(response_text, expected_results, num_targets):
    metrics = {
        "valid_json": 0,
        "truck_count_correct": 0,
        "capacity_list_valid": 0,
        "demand_list_valid": 0,
        "hallucination_or_error": 1
    }
    try:
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            print(f"    [FAIL] No se encontró JSON en la respuesta.")
            return metrics

        json_str = json_match.group(0)
        data = json.loads(json_str)
        metrics["valid_json"] = 1

        num_trucks = data.get("num_trucks")
        if isinstance(num_trucks, int) and num_trucks == expected_results["num_trucks"]:
            metrics["truck_count_correct"] = 1

        capacities = data.get("truck_capacities")
        if isinstance(capacities, list) and len(capacities) == num_trucks:
            metrics["capacity_list_valid"] = 1

        demands = data.get("target_demands")
        if isinstance(demands, list) and len(demands) == num_targets:
            metrics["demand_list_valid"] = 1

        if all([metrics["truck_count_correct"], metrics["capacity_list_valid"], metrics["demand_list_valid"]]):
            metrics["hallucination_or_error"] = 0
            print(f"    [SUCCESS] Respuesta procesada correctamente.")
        else:
            print(f"    [FAIL] La respuesta contenía datos inválidos.")

    except (json.JSONDecodeError, AttributeError, TypeError):
        print(f"    [FAIL] Error al decodificar JSON o procesar la respuesta.")
    return metrics

# --- 6. VISUALIZACIÓN ---

def plot_results(df):
    """
    Genera una gráfica de barras comparando los dos prompts.
    """
    # **INICIO DE LA CORRECCIÓN**
    # 1. Definir el diccionario de métricas PRIMERO.
    metrics_to_plot = {
        "valid_json": "Formato JSON Válido",
        "truck_count_correct": "Nº de Camiones Correcto",
        "capacity_list_valid": "Lista de Capacidades Válida",
        "demand_list_valid": "Lista de Demandas Válida"
    }

    # 2. Usar las llaves del diccionario para seleccionar las columnas a promediar.
    metrics_cols = list(metrics_to_plot.keys())
    summary = df.groupby('prompt_type')[metrics_cols].mean().reset_index()
    # **FIN DE LA CORRECCIÓN**

    labels = list(metrics_to_plot.values())
    optimized_scores = summary[summary['prompt_type'] == 'Optimized'][metrics_cols].values.flatten() * 100
    weak_scores = summary[summary['prompt_type'] == 'Weak'][metrics_cols].values.flatten() * 100

    x = np.arange(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 8)) # Aumentado el tamaño para mejor legibilidad
    rects1 = ax.bar(x - width/2, optimized_scores, width, label='Prompt Optimizado', color='royalblue')
    rects2 = ax.bar(x + width/2, weak_scores, width, label='Prompt Débil', color='lightcoral')

    ax.set_ylabel('Tasa de Éxito (%)', fontsize=12)
    ax.set_title('Comparativa de Efectividad entre Prompts para Extracción de Parámetros CVRP', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=8, ha="right")
    ax.legend()
    ax.set_ylim(0, 110)

    ax.bar_label(rects1, padding=3, fmt='%.0f%%')
    ax.bar_label(rects2, padding=3, fmt='%.0f%%')

    fig.tight_layout()

    plt.savefig("prompt_comparison.png")
    print("\nGráfica comparativa guardada en 'prompt_comparison.png'")
    plt.show()


if __name__ == "__main__":
    results_df = run_evaluation()
    print("\n--- Resultados de la Evaluación ---")
    print(results_df.to_string()) # Usar to_string() para ver todas las filas
    plot_results(results_df)