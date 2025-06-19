import json
import os
import sys
import networkx as nx
import random
import re
import difflib
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Set

# Añadir el directorio raíz al path para importar correctamente
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

# Importar el módulo Gemini
from src.NLP.Gemini import Gemini

class CVRPAssistant:
    """Asistente conversacional para extraer parámetros de CVRP (demandas, camiones y capacidades)"""
    
    def __init__(self):
        self.gemini = Gemini()
        
        # Parámetros del CVRP (depot y targets se obtienen del mapa)
        self.params = {
            "num_trucks": 0,
            "truck_capacities": [],
            "target_demands": []
        }
        
        # Estado de la conversación
        self.conversation_state = "ready"
        self.history = []
    
    def analyze_requirements(self, depot_info: dict, targets_info: list, user_description: str, solver: str = 'vns_solver') -> dict:
        """
        Analiza los requerimientos del usuario y extrae parámetros para CVRP
        
        Args:
            depot_info: Información del depósito seleccionado {id: int, position: [lon, lat]}
            targets_info: Lista de objetivos seleccionados [{id: int, position: [lon, lat]}, ...]
            user_description: Descripción en lenguaje natural del usuario
            solver: Algoritmo de optimización seleccionado ('vns_solver', 'ts_solver', 'sa_solver', 'ag_solver')
        
        Returns:
            dict con los parámetros extraídos y mensajes de respuesta
        """
        
        # Construir contexto para el análisis
        context = self._build_context(depot_info, targets_info, solver)
        
        # Prompt para analizar los requerimientos
        prompt = f"""
        El usuario tiene un problema de ruteo de vehículos (CVRP) con la siguiente configuración:

        DEPÓSITO:
        - Nodo ID: {depot_info['id']}
        - Coordenadas: {depot_info['position']}

        PUNTOS OBJETIVO ({len(targets_info)} destinos):
        {self._format_targets_for_prompt(targets_info)}

        ALGORITMO SELECCIONADO: {self._get_solver_description(solver)}

        DESCRIPCIÓN DEL USUARIO:
        "{user_description}"

        Por favor, analiza la descripción del usuario y extrae la siguiente información considerando que se usará {solver.replace('_', ' ').title()}:

        1. NÚMERO DE CAMIONES: ¿Cuántos vehículos necesita? Si no se especifica, sugiere un número razonable basado en los {len(targets_info)} destinos y el algoritmo {solver}.

        2. CAPACIDADES DE LOS CAMIONES: ¿Qué capacidad tiene cada camión? Si no se especifica, sugiere capacidades razonables.

        3. DEMANDAS DE LOS DESTINOS: ¿Cuál es la demanda de cada punto objetivo? Si no se especifica, sugiere demandas razonables basadas en el contexto.

        4. OBSERVACIONES: Cualquier información adicional relevante que hayas inferido, incluyendo consideraciones específicas para el algoritmo {solver}.

        Responde ÚNICAMENTE con un JSON en este formato exacto:
        {{
            "num_trucks": <número_entero>,
            "truck_capacities": [<lista_de_capacidades_enteras>],
            "target_demands": [<lista_de_demandas_enteras>],
            "reasoning": {{
                "num_trucks_reason": "explicación de por qué elegiste este número de camiones",
                "capacities_reason": "explicación de las capacidades elegidas",
                "demands_reason": "explicación de las demandas asignadas",
                "solver_considerations": "consideraciones específicas para {solver}"
            }},
            "observations": "observaciones adicionales o sugerencias"
        }}

        IMPORTANTE: 
        - La lista truck_capacities debe tener exactamente num_trucks elementos
        - La lista target_demands debe tener exactamente {len(targets_info)} elementos
        - Todos los números deben ser enteros positivos
        - No incluyas texto fuera del JSON
        """
        
        try:
            response = self.gemini.ask(prompt)
            
            # Limpiar la respuesta para extraer solo el JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                analysis_result = json.loads(json_str)
                
                # Validar y procesar los resultados
                validation_result = self._validate_analysis(analysis_result, len(targets_info))
                
                if validation_result["valid"]:
                    self.params["num_trucks"] = analysis_result["num_trucks"]
                    self.params["truck_capacities"] = analysis_result["truck_capacities"]
                    self.params["target_demands"] = analysis_result["target_demands"]
                    
                    return {
                        "success": True,
                        "params": self.params.copy(),
                        "analysis": analysis_result,
                        "message": self._format_success_message(analysis_result, targets_info, solver)
                    }
                else:
                    return {
                        "success": False,
                        "error": validation_result["error"],
                        "message": f"Error en el análisis: {validation_result['error']}"
                    }
            else:
                return {
                    "success": False,
                    "error": "No se pudo extraer JSON de la respuesta",
                    "message": "La IA no pudo procesar correctamente tu descripción. Intenta ser más específico."
                }
                
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Error parsing JSON: {e}",
                "message": "Hubo un error al procesar la respuesta de la IA. Intenta reformular tu descripción."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error general: {e}",
                "message": f"Error inesperado: {str(e)}"
            }
    
    def _build_context(self, depot_info: dict, targets_info: list, solver: str = 'vns_solver') -> str:
        """Construye contexto geográfico y logístico"""
        return f"Ruteo en La Habana, Cuba con {len(targets_info)} destinos desde el depósito {depot_info['id']} usando {solver}"
    
    def _get_solver_description(self, solver: str) -> str:
        """Obtiene la descripción del solver seleccionado"""
        descriptions = {
            'vns_solver': 'Variable Neighborhood Search - Búsqueda en vecindario variable, bueno para problemas medianos',
            'ts_solver': 'Tabu Search - Búsqueda tabú, excelente para escape de óptimos locales',
            'sa_solver': 'Simulated Annealing - Recocido simulado, robusto para problemas complejos',
            'ag_solver': 'Algoritmo Genético - Evolución de poblaciones, buena exploración global'
        }
        return descriptions.get(solver, 'Algoritmo de optimización')
    
    def _format_targets_for_prompt(self, targets_info: list) -> str:
        """Formatea la información de los objetivos para el prompt"""
        formatted = ""
        for i, target in enumerate(targets_info, 1):
            formatted += f"  {i}. Nodo ID: {target['id']} - Coordenadas: {target['position']}\n"
        return formatted.strip()
    
    def _validate_analysis(self, analysis: dict, num_targets: int) -> dict:
        """Valida que el análisis de la IA sea correcto"""
        try:
            # Verificar campos requeridos
            required_fields = ["num_trucks", "truck_capacities", "target_demands"]
            for field in required_fields:
                if field not in analysis:
                    return {"valid": False, "error": f"Campo faltante: {field}"}
            
            # Validar num_trucks
            num_trucks = analysis["num_trucks"]
            if not isinstance(num_trucks, int) or num_trucks <= 0:
                return {"valid": False, "error": "num_trucks debe ser un entero positivo"}
            
            # Validar truck_capacities
            capacities = analysis["truck_capacities"]
            if not isinstance(capacities, list) or len(capacities) != num_trucks:
                return {"valid": False, "error": f"truck_capacities debe ser una lista de {num_trucks} elementos"}
            
            if not all(isinstance(cap, int) and cap > 0 for cap in capacities):
                return {"valid": False, "error": "Todas las capacidades deben ser enteros positivos"}
            
            # Validar target_demands
            demands = analysis["target_demands"]
            if not isinstance(demands, list) or len(demands) != num_targets:
                return {"valid": False, "error": f"target_demands debe ser una lista de {num_targets} elementos"}
            
            if not all(isinstance(dem, int) and dem > 0 for dem in demands):
                return {"valid": False, "error": "Todas las demandas deben ser enteros positivos"}
            
            return {"valid": True}
            
        except Exception as e:
            return {"valid": False, "error": f"Error en validación: {str(e)}"}
    
    def _format_success_message(self, analysis: dict, targets_info: list, solver: str = 'vns_solver') -> str:
        """Formatea el mensaje de éxito con la información analizada"""
        message = "✅ **Análisis completado exitosamente**\n\n"
        
        # Información del algoritmo seleccionado
        message += f"⚙️ **Algoritmo:** {solver.replace('_', ' ').title()}\n\n"
        
        # Información de camiones
        message += f"🚛 **Camiones:** {analysis['num_trucks']}\n"
        message += f"📦 **Capacidades:** {analysis['truck_capacities']}\n\n"
        
        # Información de demandas
        message += "📍 **Demandas por destino:**\n"
        for i, (target, demand) in enumerate(zip(targets_info, analysis['target_demands'])):
            message += f"  • Nodo {target['id']}: {demand} unidades\n"
        
        # Razonamiento si está disponible
        if "reasoning" in analysis:
            reasoning = analysis["reasoning"]
            message += "\n🤔 **Razonamiento:**\n"
            if "num_trucks_reason" in reasoning:
                message += f"  • Camiones: {reasoning['num_trucks_reason']}\n"
            if "capacities_reason" in reasoning:
                message += f"  • Capacidades: {reasoning['capacities_reason']}\n"
            if "demands_reason" in reasoning:
                message += f"  • Demandas: {reasoning['demands_reason']}\n"
            if "solver_considerations" in reasoning:
                message += f"  • Algoritmo: {reasoning['solver_considerations']}\n"
        
        # Observaciones adicionales
        if "observations" in analysis and analysis["observations"]:
            message += f"\n💡 **Observaciones:** {analysis['observations']}\n"
        
        message += "\n✨ Los parámetros están listos para la optimización."
        
        return message
    
    def get_params(self) -> dict:
        """Devuelve los parámetros actuales"""
        return self.params.copy()
    
    def reset(self):
        """Reinicia el asistente"""
        self.params = {
            "num_trucks": 0,
            "truck_capacities": [],
            "target_demands": []
        }
        self.conversation_state = "ready"
        self.history = []

# Función para usar desde el servidor
def analyze_cvrp_requirements(depot_info: dict, targets_info: list, user_description: str, solver: str = 'vns_solver') -> dict:
    """
    Función helper para analizar requerimientos de CVRP
    
    Args:
        depot_info: Información del depósito {id, position}
        targets_info: Lista de objetivos [{id, position}, ...]
        user_description: Descripción del usuario
        solver: Algoritmo de optimización seleccionado
    
    Returns:
        dict con resultado del análisis
    """
    assistant = CVRPAssistant()
    return assistant.analyze_requirements(depot_info, targets_info, user_description, solver)

if __name__ == "__main__":
    # Ejemplo de uso
    depot = {"id": 12345, "position": [-82.3666, 23.1136]}
    targets = [
        {"id": 12346, "position": [-82.3656, 23.1146]},
        {"id": 12347, "position": [-82.3676, 23.1126]},
        {"id": 12348, "position": [-82.3686, 23.1156]}
    ]
    
    description = "Necesito repartir productos alimenticios a 3 tiendas pequeñas en La Habana. Cada tienda necesita entre 10-20 cajas. Tengo 2 camiones disponibles con capacidad de 50 cajas cada uno."
    
    result = analyze_cvrp_requirements(depot, targets, description)
    print(json.dumps(result, indent=2))