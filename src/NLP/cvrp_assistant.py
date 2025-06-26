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
    """Conversational assistant for extracting CVRP parameters (demands, trucks, and capacities)"""
    
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
            Analyzes the user's requirements and extracts parameters for CVRP

        Args:
            depot_info: Information of the selected depot {id: int, position: [lon, lat]}
            targets_info: List of selected targets [{id: int, position: [lon, lat]}, ...]
            user_description: User's natural language description
            solver: Selected optimization algorithm ('vns_solver', 'ts_solver', 'sa_solver', 'ag_solver')

        Returns:
            dict with the extracted parameters and response messages
        """
        
        # Construir contexto para el análisis
        context = self._build_context(depot_info, targets_info, solver)
        
        match = re.search(r'tengo\s+(\d+)\s+camiones', user_description, re.IGNORECASE)
        explicit_trucks = int(match.group(1)) if match else None
        
                # 2) Preparamos un bloque que inyectaremos en el prompt
        header_trucks = ""
        if explicit_trucks is not None:
            header_trucks = (
                f"El usuario ha indicado que tiene EXACTAMENTE "
                f"{explicit_trucks} camiones disponibles.\n\n"
            )
        
        # Prompt para analizar los requerimientos
        prompt = f"""
        {header_trucks}
        The user has a Capacitated Vehicle Routing Problem (CVRP) with the following configuration:

        DEPOT:
        - Node ID: {depot_info['id']}
        - Coordinates: {depot_info['position']}

        TARGET LOCATIONS ({len(targets_info)} destinations):
        {self._format_targets_for_prompt(targets_info)}

        SELECTED ALGORITHM: {self._get_solver_description(solver)}

        USER DESCRIPTION:
        "{user_description}"

        Please analyze the user's description and extract the following information, considering that {solver.replace('_', ' ').title()} will be used:

        1. NUMBER OF TRUCKS: {
            f"Use EXACTLY the {explicit_trucks} trucks the user specified."
            if explicit_trucks is not None
            else f"How many vehicles are needed? If not specified, suggest a reasonable number based on the {len(targets_info)} destinations and the {solver} algorithm."
        }

        2. TRUCK CAPACITIES: What is the capacity of each truck? If not specified, suggest reasonable capacities.

        3. DEMANDS OF TARGET LOCATIONS: What is the demand for each target location? If not specified, suggest reasonable demands based on the context.

        4. OBSERVATIONS: Any additional relevant information you have inferred, including solver-specific considerations for {solver}.

        Respond ONLY with a JSON in this exact format:
        {{
            "num_trucks": <integer_number>,
            "truck_capacities": [<list_of_integer_capacities>],
            "target_demands": [<list_of_integer_demands>],
            "reasoning": {{
                "num_trucks_reason": "explanation of why this number of trucks was chosen",
                "capacities_reason": "explanation of the chosen capacities",
                "demands_reason": "explanation of the assigned demands",
                "solver_considerations": "specific considerations for {solver}"
            }},
            "observations": "additional observations or suggestions"
        }}

        IMPORTANT:
        - The truck_capacities list must contain exactly num_trucks elements
        - The target_demands list must contain exactly {len(targets_info)} elements
        - All numbers must be positive integers
        - Do not include any text outside of the JSON
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