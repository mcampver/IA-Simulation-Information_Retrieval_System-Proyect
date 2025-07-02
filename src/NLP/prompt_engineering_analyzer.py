"""
Analizador de Prompt Engineering para CVRP Assistant
==================================================

Este script evalúa diferentes estrategias de prompt engineering para la extracción
de parámetros CVRP (Capacitated Vehicle Routing Problem) usando múltiples métricas
y casos de prueba variados.

Autor: Sistema de Análisis de Prompt Engineering
Fecha: 2025-07-02
"""

import json
import os
import sys
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import re
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Añadir el directorio raíz al path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

# Importar el módulo Gemini
from src.NLP.Gemini import Gemini

class PromptStrategy(Enum):
    """Estrategias de prompt engineering disponibles"""
    ZERO_SHOT = "zero_shot"
    FEW_SHOT = "few_shot"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    ROLE_PLAYING = "role_playing"
    STRUCTURED_OUTPUT = "structured_output"
    CONTEXT_AWARE = "context_aware"
    STEP_BY_STEP = "step_by_step"

@dataclass
class TestCase:
    """Caso de prueba para evaluación de prompts"""
    id: str
    name: str
    description: str
    user_input: str
    expected_trucks: int
    expected_capacities: List[int]
    expected_demands: List[int]
    complexity_level: str  # "simple", "medium", "complex"
    scenario_type: str     # "explicit", "implicit", "ambiguous"
    depot_info: Dict
    targets_info: List[Dict]

@dataclass
class EvaluationMetrics:
    """Métricas de evaluación para un caso de prueba"""
    truck_count_accuracy: float
    capacity_accuracy: float
    demand_accuracy: float
    response_completeness: float
    json_validity: float
    reasoning_quality: float
    execution_time: float
    token_efficiency: float
    overall_score: float

class PromptEngineering:
    """Generador de prompts basado en diferentes estrategias"""
    
    def __init__(self):
        self.strategies = {
            PromptStrategy.ZERO_SHOT: self._generate_zero_shot,
            PromptStrategy.FEW_SHOT: self._generate_few_shot,
            PromptStrategy.CHAIN_OF_THOUGHT: self._generate_chain_of_thought,
            PromptStrategy.ROLE_PLAYING: self._generate_role_playing,
            PromptStrategy.STRUCTURED_OUTPUT: self._generate_structured_output,
            PromptStrategy.CONTEXT_AWARE: self._generate_context_aware,
            PromptStrategy.STEP_BY_STEP: self._generate_step_by_step
        }
    
    def generate_prompt(self, strategy: PromptStrategy, depot_info: dict, targets_info: list, 
                       user_description: str, solver: str, explicit_trucks: Optional[int] = None) -> str:
        """Genera un prompt basado en la estrategia especificada"""
        return self.strategies[strategy](depot_info, targets_info, user_description, solver, explicit_trucks)
    
    def _generate_zero_shot(self, depot_info: dict, targets_info: list, 
                           user_description: str, solver: str, explicit_trucks: Optional[int] = None) -> str:
        """Estrategia Zero-Shot: prompt directo sin ejemplos"""
        return f"""
        Analyze the following Vehicle Routing Problem and extract the required parameters.

        DEPOT: Node {depot_info['id']} at {depot_info['position']}
        TARGETS: {len(targets_info)} locations
        ALGORITHM: {solver}
        USER REQUEST: "{user_description}"

        Extract: number of trucks, truck capacities, and target demands.

        Respond with JSON format:
        {{
            "num_trucks": <integer>,
            "truck_capacities": [<list>],
            "target_demands": [<list>],
            "reasoning": {{...}}
        }}
        """
    
    def _generate_few_shot(self, depot_info: dict, targets_info: list, 
                          user_description: str, solver: str, explicit_trucks: Optional[int] = None) -> str:
        """Estrategia Few-Shot: prompt con ejemplos"""
        examples = '''
        EXAMPLE 1:
        Input: "Necesito entregar a 2 tiendas con 1 camión de 100 cajas"
        Output: {"num_trucks": 1, "truck_capacities": [100], "target_demands": [40, 50]}
        
        EXAMPLE 2:
        Input: "Reparto a 3 restaurantes, tengo 2 vehículos grandes"
        Output: {"num_trucks": 2, "truck_capacities": [150, 150], "target_demands": [50, 60, 70]}
        '''
        
        return f"""
        {examples}
        
        Now analyze this case:
        DEPOT: Node {depot_info['id']} at {depot_info['position']}
        TARGETS: {len(targets_info)} locations
        USER REQUEST: "{user_description}"
        
        Following the pattern above, provide your analysis in JSON format.
        """
    
    def _generate_chain_of_thought(self, depot_info: dict, targets_info: list, 
                                  user_description: str, solver: str, explicit_trucks: Optional[int] = None) -> str:
        """Estrategia Chain of Thought: razonamiento paso a paso"""
        return f"""
        Let's think step by step about this Vehicle Routing Problem:

        GIVEN INFORMATION:
        - Depot: Node {depot_info['id']} at {depot_info['position']}
        - Destinations: {len(targets_info)} locations
        - User description: "{user_description}"
        - Algorithm: {solver}

        STEP 1: Analyze the user's explicit requirements
        - Look for specific numbers of vehicles mentioned
        - Identify capacity constraints
        - Find demand patterns

        STEP 2: Infer missing information
        - If trucks not specified, calculate based on destinations and typical capacity
        - If capacities not mentioned, estimate based on context
        - If demands not given, distribute reasonably

        STEP 3: Validate the solution
        - Ensure total capacity ≥ total demand
        - Check if number of trucks is reasonable
        - Verify demands are positive integers

        STEP 4: Provide reasoning for each decision

        Now provide your complete analysis in JSON format with detailed reasoning.
        """
    
    def _generate_role_playing(self, depot_info: dict, targets_info: list, 
                              user_description: str, solver: str, explicit_trucks: Optional[int] = None) -> str:
        """Estrategia Role Playing: asumir rol de experto"""
        return f"""
        You are an expert logistics coordinator with 15 years of experience in vehicle routing optimization.
        
        A client comes to you with this delivery scenario:
        "{user_description}"
        
        SCENARIO DETAILS:
        - Starting point: Depot {depot_info['id']} at {depot_info['position']}
        - Delivery points: {len(targets_info)} locations
        - Optimization method: {solver}
        
        As an expert, you need to:
        1. Assess the fleet requirements (number of vehicles)
        2. Determine appropriate vehicle capacities
        3. Estimate demand at each location
        4. Provide professional reasoning for your decisions
        
        Based on your expertise, what would be your professional recommendation?
        
        Provide your expert analysis in this JSON structure:
        {{
            "num_trucks": <your_expert_recommendation>,
            "truck_capacities": [<capacities_based_on_experience>],
            "target_demands": [<realistic_demand_estimates>],
            "expert_reasoning": {{
                "fleet_rationale": "why this number of vehicles",
                "capacity_rationale": "basis for capacity decisions",
                "demand_rationale": "how demands were estimated"
            }}
        }}
        """
    
    def _generate_structured_output(self, depot_info: dict, targets_info: list, 
                                   user_description: str, solver: str, explicit_trucks: Optional[int] = None) -> str:
        """Estrategia Structured Output: formato muy estructurado"""
        return f"""
        VEHICLE ROUTING PROBLEM ANALYSIS
        ================================
        
        INPUT PARAMETERS:
        ├── Depot Location: {depot_info['id']} at {depot_info['position']}
        ├── Target Count: {len(targets_info)}
        ├── User Requirements: "{user_description}"
        └── Solver Algorithm: {solver}
        
        REQUIRED OUTPUT STRUCTURE:
        {{
            "analysis_metadata": {{
                "input_complexity": "<simple|medium|complex>",
                "explicit_constraints": "<list_of_explicit_constraints>",
                "implicit_assumptions": "<list_of_assumptions>"
            }},
            "extracted_parameters": {{
                "num_trucks": <integer_value>,
                "truck_capacities": [<capacity_1>, <capacity_2>, ...],
                "target_demands": [<demand_1>, <demand_2>, ...]
            }},
            "decision_rationale": {{
                "truck_count_logic": "<reasoning>",
                "capacity_assignment_logic": "<reasoning>",
                "demand_estimation_logic": "<reasoning>"
            }},
            "validation_checks": {{
                "capacity_demand_balance": "<feasible|infeasible>",
                "solution_optimality": "<assessment>"
            }}
        }}
        
        Please fill in this exact structure with your analysis.
        """
    
    def _generate_context_aware(self, depot_info: dict, targets_info: list, 
                               user_description: str, solver: str, explicit_trucks: Optional[int] = None) -> str:
        """Estrategia Context Aware: considera contexto geográfico y cultural"""
        return f"""
        CONTEXTUAL ANALYSIS FOR HAVANA, CUBA LOGISTICS
        =============================================
        
        GEOGRAPHIC CONTEXT:
        - Location: Havana, Cuba (tropical climate, urban density)
        - Infrastructure: Mixed road conditions, traffic patterns
        - Depot: {depot_info['id']} at coordinates {depot_info['position']}
        - Destinations: {len(targets_info)} locations in urban area
        
        CULTURAL & ECONOMIC CONTEXT:
        - Local business practices and delivery expectations
        - Typical vehicle sizes and availability in Cuba
        - Common cargo types and volumes
        - Traffic patterns and delivery windows
        
        USER SCENARIO:
        "{user_description}"
        
        ALGORITHM CONSIDERATIONS:
        - Using {solver} which is suitable for this problem size
        - Consider local constraints and preferences
        
        Given this rich context, analyze the requirements considering:
        1. Local vehicle availability and typical capacities
        2. Urban delivery patterns in Havana
        3. Realistic demand distributions for the area
        4. Cultural factors affecting logistics decisions
        
        Provide culturally and geographically informed analysis:
        {{
            "num_trucks": <context_aware_recommendation>,
            "truck_capacities": [<locally_appropriate_capacities>],
            "target_demands": [<realistic_local_demands>],
            "contextual_reasoning": {{
                "geographic_factors": "how location influenced decisions",
                "cultural_considerations": "local practices considered",
                "infrastructure_impact": "road/traffic influence"
            }}
        }}
        """
    
    def _generate_step_by_step(self, depot_info: dict, targets_info: list, 
                              user_description: str, solver: str, explicit_trucks: Optional[int] = None) -> str:
        """Estrategia Step by Step: proceso muy detallado"""
        return f"""
        STEP-BY-STEP CVRP PARAMETER EXTRACTION
        ====================================
        
        STEP 1: INPUT ANALYSIS
        ----------------------
        Depot: {depot_info['id']} at {depot_info['position']}
        Targets: {len(targets_info)} destinations
        User Request: "{user_description}"
        Algorithm: {solver}
        
        STEP 2: EXPLICIT PARAMETER EXTRACTION
        ------------------------------------
        □ Scan for explicit truck count mentions
        □ Look for capacity specifications  
        □ Identify demand requirements
        □ Note any constraints mentioned
        
        STEP 3: IMPLICIT PARAMETER INFERENCE
        -----------------------------------
        □ If truck count missing: estimate based on destinations/capacity ratio
        □ If capacities missing: infer from context and typical values
        □ If demands missing: distribute based on scenario type
        
        STEP 4: FEASIBILITY VALIDATION
        -----------------------------
        □ Check: total_capacity >= total_demand
        □ Check: truck_count is reasonable for destination count
        □ Check: individual demands are positive integers
        
        STEP 5: ALGORITHM-SPECIFIC OPTIMIZATION
        -------------------------------------
        □ Consider {solver} characteristics
        □ Adjust parameters for algorithm efficiency
        □ Note any solver-specific recommendations
        
        STEP 6: FINAL PARAMETER COMPILATION
        ---------------------------------
        Provide your final analysis following this exact format:
        {{
            "step_by_step_analysis": {{
                "step2_explicit_findings": "what was explicitly stated",
                "step3_inferences_made": "what was inferred and why",
                "step4_validation_results": "feasibility check results",
                "step5_solver_adjustments": "algorithm-specific considerations"
            }},
            "final_parameters": {{
                "num_trucks": <final_truck_count>,
                "truck_capacities": [<final_capacities>],
                "target_demands": [<final_demands>]
            }}
        }}
        """

class CVRPPromptAnalyzer:
    """Analizador principal para evaluación de prompts de CVRP"""
    
    def __init__(self):
        self.gemini = Gemini()
        self.prompt_generator = PromptEngineering()
        self.test_cases = self._create_test_cases()
        self.results = []
    
    def _create_test_cases(self) -> List[TestCase]:
        """Crea casos de prueba variados de diferentes niveles de complejidad"""
        
        # Información común de depot y targets para pruebas
        depot = {"id": 12345, "position": [-82.3666, 23.1136]}
        
        test_cases = [
            # CASOS SIMPLES
            TestCase(
                id="simple_01",
                name="Caso Explícito Simple",
                description="Usuario especifica claramente todos los parámetros",
                user_input="Tengo 2 camiones de 50 cajas cada uno para repartir a 3 tiendas que necesitan 20, 15 y 10 cajas respectivamente",
                expected_trucks=2,
                expected_capacities=[50, 50],
                expected_demands=[20, 15, 10],
                complexity_level="simple",
                scenario_type="explicit",
                depot_info=depot,
                targets_info=[
                    {"id": 101, "position": [-82.3656, 23.1146]},
                    {"id": 102, "position": [-82.3676, 23.1126]},
                    {"id": 103, "position": [-82.3686, 23.1156]}
                ]
            ),
            
            TestCase(
                id="simple_02",
                name="Caso Básico con Inferencia",
                description="Usuario da contexto básico, necesita inferir algunos parámetros",
                user_input="Necesito entregar productos a 2 supermercados con 1 camión grande",
                expected_trucks=1,
                expected_capacities=[120],
                expected_demands=[50, 60],
                complexity_level="simple",
                scenario_type="implicit",
                depot_info=depot,
                targets_info=[
                    {"id": 201, "position": [-82.3650, 23.1140]},
                    {"id": 202, "position": [-82.3670, 23.1130]}
                ]
            ),
            
            # CASOS MEDIANOS
            TestCase(
                id="medium_01",
                name="Caso con Múltiples Restricciones",
                description="Usuario especifica algunas restricciones pero no todas",
                user_input="Tengo 3 camiones para repartir medicinas a 5 farmacias en La Habana. Cada farmacia necesita diferente cantidad según su tamaño: 2 son grandes y 3 pequeñas",
                expected_trucks=3,
                expected_capacities=[80, 80, 60],
                expected_demands=[40, 45, 25, 20, 30],
                complexity_level="medium",
                scenario_type="implicit",
                depot_info=depot,
                targets_info=[
                    {"id": 301, "position": [-82.3660, 23.1150]},
                    {"id": 302, "position": [-82.3680, 23.1120]},
                    {"id": 303, "position": [-82.3690, 23.1160]},
                    {"id": 304, "position": [-82.3640, 23.1140]},
                    {"id": 305, "position": [-82.3670, 23.1135]}
                ]
            ),
            
            TestCase(
                id="medium_02",
                name="Caso con Restricciones de Capacidad",
                description="Usuario menciona restricciones pero de forma indirecta",
                user_input="Necesito optimizar la entrega de alimentos a 4 restaurantes. Mis camiones pueden cargar máximo 100 kg cada uno. Los restaurantes del centro necesitan más que los de la periferia",
                expected_trucks=2,
                expected_capacities=[100, 100],
                expected_demands=[60, 55, 35, 40],
                complexity_level="medium",
                scenario_type="implicit",
                depot_info=depot,
                targets_info=[
                    {"id": 401, "position": [-82.3665, 23.1145]},
                    {"id": 402, "position": [-82.3675, 23.1125]},
                    {"id": 403, "position": [-82.3695, 23.1165]},
                    {"id": 404, "position": [-82.3635, 23.1135]}
                ]
            ),
            
            # CASOS COMPLEJOS
            TestCase(
                id="complex_01",
                name="Caso Ambiguo con Múltiples Interpretaciones",
                description="Descripción ambigua que puede interpretarse de varias formas",
                user_input="Mañana necesito hacer la ruta de distribución. Tengo varios vehículos disponibles y muchos clientes esperando. Algunos pedidos son urgentes",
                expected_trucks=3,
                expected_capacities=[80, 70, 60],
                expected_demands=[35, 25, 40, 30, 20, 25],
                complexity_level="complex",
                scenario_type="ambiguous",
                depot_info=depot,
                targets_info=[
                    {"id": 501, "position": [-82.3655, 23.1155]},
                    {"id": 502, "position": [-82.3685, 23.1115]},
                    {"id": 503, "position": [-82.3705, 23.1175]},
                    {"id": 504, "position": [-82.3625, 23.1125]},
                    {"id": 505, "position": [-82.3645, 23.1165]},
                    {"id": 506, "position": [-82.3695, 23.1145]}
                ]
            ),
            
            TestCase(
                id="complex_02",
                name="Caso con Restricciones Conflictivas",
                description="Usuario da información que podría ser contradictoria",
                user_input="Tengo 1 camión pequeño pero necesito entregar a 8 puntos de venta grandes volúmenes de mercancía para el fin de semana",
                expected_trucks=3,
                expected_capacities=[60, 60, 50],
                expected_demands=[30, 35, 25, 40, 20, 30, 25, 35],
                complexity_level="complex",
                scenario_type="ambiguous",
                depot_info=depot,
                targets_info=[
                    {"id": 601, "position": [-82.3650, 23.1150]},
                    {"id": 602, "position": [-82.3670, 23.1130]},
                    {"id": 603, "position": [-82.3690, 23.1170]},
                    {"id": 604, "position": [-82.3630, 23.1140]},
                    {"id": 605, "position": [-82.3660, 23.1160]},
                    {"id": 606, "position": [-82.3680, 23.1120]},
                    {"id": 607, "position": [-82.3700, 23.1180]},
                    {"id": 608, "position": [-82.3620, 23.1130]}
                ]
            ),
            
            TestCase(
                id="complex_03",
                name="Caso de Optimización Multiobjetivo",
                description="Usuario menciona múltiples objetivos y restricciones",
                user_input="Necesito minimizar costos y tiempo de entrega. Tengo restricciones de horarios en algunos lugares, limitaciones de peso en mis vehículos y algunos clientes prioritarios que deben ser atendidos primero",
                expected_trucks=4,
                expected_capacities=[90, 85, 75, 70],
                expected_demands=[45, 35, 30, 25, 40, 20],
                complexity_level="complex",
                scenario_type="ambiguous",
                depot_info=depot,
                targets_info=[
                    {"id": 701, "position": [-82.3645, 23.1155]},
                    {"id": 702, "position": [-82.3675, 23.1125]},
                    {"id": 703, "position": [-82.3685, 23.1165]},
                    {"id": 704, "position": [-82.3635, 23.1145]},
                    {"id": 705, "position": [-82.3665, 23.1135]},
                    {"id": 706, "position": [-82.3695, 23.1175]}
                ]
            )
        ]
        
        return test_cases
    
    def evaluate_prompt_response(self, response: str, test_case: TestCase, 
                               execution_time: float) -> EvaluationMetrics:
        """Evalúa la respuesta de un prompt según múltiples métricas"""
        
        # Inicializar métricas
        metrics = EvaluationMetrics(
            truck_count_accuracy=0.0,
            capacity_accuracy=0.0,
            demand_accuracy=0.0,
            response_completeness=0.0,
            json_validity=0.0,
            reasoning_quality=0.0,
            execution_time=execution_time,
            token_efficiency=0.0,
            overall_score=0.0
        )
        
        try:
            # Extraer JSON de la respuesta
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed_response = json.loads(json_str)
                metrics.json_validity = 1.0
                
                # Evaluar precisión del número de camiones
                if "num_trucks" in parsed_response:
                    actual_trucks = parsed_response["num_trucks"]
                    # Verificar que actual_trucks sea un número válido
                    if isinstance(actual_trucks, (int, float)) and actual_trucks > 0:
                        if actual_trucks == test_case.expected_trucks:
                            metrics.truck_count_accuracy = 1.0
                        else:
                            # Penalización proporcional a la diferencia
                            diff = abs(float(actual_trucks) - float(test_case.expected_trucks))
                            metrics.truck_count_accuracy = max(0, 1 - (diff / float(test_case.expected_trucks)))
                    else:
                        metrics.truck_count_accuracy = 0.0
                
                # Evaluar precisión de capacidades
                if "truck_capacities" in parsed_response:
                    actual_capacities = parsed_response["truck_capacities"]
                    # Verificar que sea una lista válida de números
                    if isinstance(actual_capacities, list) and all(isinstance(x, (int, float)) and x > 0 for x in actual_capacities):
                        if len(actual_capacities) == len(test_case.expected_capacities):
                            capacity_errors = [abs(float(a) - float(e)) for a, e in zip(actual_capacities, test_case.expected_capacities)]
                            avg_error = sum(capacity_errors) / len(capacity_errors)
                            avg_expected = sum(test_case.expected_capacities) / len(test_case.expected_capacities)
                            metrics.capacity_accuracy = max(0, 1 - (avg_error / avg_expected))
                        else:
                            metrics.capacity_accuracy = 0.5  # Penalización por longitud incorrecta
                    else:
                        metrics.capacity_accuracy = 0.0
                
                # Evaluar precisión de demandas
                if "target_demands" in parsed_response:
                    actual_demands = parsed_response["target_demands"]
                    # Verificar que sea una lista válida de números
                    if isinstance(actual_demands, list) and all(isinstance(x, (int, float)) and x > 0 for x in actual_demands):
                        if len(actual_demands) == len(test_case.expected_demands):
                            demand_errors = [abs(float(a) - float(e)) for a, e in zip(actual_demands, test_case.expected_demands)]
                            avg_error = sum(demand_errors) / len(demand_errors)
                            avg_expected = sum(test_case.expected_demands) / len(test_case.expected_demands)
                            metrics.demand_accuracy = max(0, 1 - (avg_error / avg_expected))
                        else:
                            metrics.demand_accuracy = 0.5
                    else:
                        metrics.demand_accuracy = 0.0
                
                # Evaluar completitud de la respuesta
                required_fields = ["num_trucks", "truck_capacities", "target_demands"]
                present_fields = sum(1 for field in required_fields if field in parsed_response)
                metrics.response_completeness = present_fields / len(required_fields)
                
                # Evaluar calidad del razonamiento
                reasoning_indicators = ["reasoning", "rationale", "explanation", "logic", "because"]
                reasoning_score = 0
                response_lower = response.lower()
                for indicator in reasoning_indicators:
                    if indicator in response_lower:
                        reasoning_score += 0.2
                metrics.reasoning_quality = min(1.0, reasoning_score)
                
            else:
                metrics.json_validity = 0.0
                
        except json.JSONDecodeError:
            metrics.json_validity = 0.0
        except Exception as e:
            logger.error(f"Error evaluating response: {e}")
        
        # Calcular eficiencia de tokens (aproximada)
        token_count = len(response.split())
        metrics.token_efficiency = min(1.0, 100 / token_count) if token_count > 0 else 0
        
        # Calcular puntuación general
        weights = {
            'truck_count_accuracy': 0.25,
            'capacity_accuracy': 0.20,
            'demand_accuracy': 0.20,
            'response_completeness': 0.15,
            'json_validity': 0.10,
            'reasoning_quality': 0.10
        }
        
        metrics.overall_score = sum(
            getattr(metrics, metric) * weight 
            for metric, weight in weights.items()
        )
        
        return metrics
    
    def run_comprehensive_analysis(self, strategies: List[PromptStrategy] = None) -> Dict[str, Any]:
        """Ejecuta análisis completo de todas las estrategias y casos de prueba"""
        
        if strategies is None:
            strategies = list(PromptStrategy)
        
        logger.info(f"Iniciando análisis completo con {len(strategies)} estrategias y {len(self.test_cases)} casos de prueba")
        
        results = []
        
        for strategy in strategies:
            logger.info(f"Evaluando estrategia: {strategy.value}")
            
            for test_case in self.test_cases:
                logger.info(f"  Caso de prueba: {test_case.id}")
                
                try:
                    # Generar prompt
                    prompt = self.prompt_generator.generate_prompt(
                        strategy, test_case.depot_info, test_case.targets_info,
                        test_case.user_input, "vns_solver", None
                    )
                    
                    # Medir tiempo de ejecución
                    start_time = time.time()
                    response = self.gemini.ask(prompt)
                    execution_time = time.time() - start_time
                    
                    # Evaluar respuesta
                    metrics = self.evaluate_prompt_response(response, test_case, execution_time)
                    
                    # Guardar resultado
                    result = {
                        'strategy': strategy.value,
                        'test_case_id': test_case.id,
                        'test_case_name': test_case.name,
                        'complexity_level': test_case.complexity_level,
                        'scenario_type': test_case.scenario_type,
                        'metrics': metrics,
                        'prompt': prompt,
                        'response': response,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Error en {strategy.value} - {test_case.id}: {e}")
                    
                # Pausa entre llamadas para evitar rate limiting
                time.sleep(1)
        
        self.results = results
        return self._compile_analysis_report()
    
    def _compile_analysis_report(self) -> Dict[str, Any]:
        """Compila un reporte completo del análisis"""
        
        if not self.results:
            return {"error": "No hay resultados para analizar"}
        
        # Convertir resultados a DataFrame para análisis
        df_data = []
        for result in self.results:
            row = {
                'strategy': result['strategy'],
                'test_case_id': result['test_case_id'],
                'complexity_level': result['complexity_level'],
                'scenario_type': result['scenario_type'],
                'truck_count_accuracy': result['metrics'].truck_count_accuracy,
                'capacity_accuracy': result['metrics'].capacity_accuracy,
                'demand_accuracy': result['metrics'].demand_accuracy,
                'response_completeness': result['metrics'].response_completeness,
                'json_validity': result['metrics'].json_validity,
                'reasoning_quality': result['metrics'].reasoning_quality,
                'execution_time': result['metrics'].execution_time,
                'token_efficiency': result['metrics'].token_efficiency,
                'overall_score': result['metrics'].overall_score
            }
            df_data.append(row)
        
        df = pd.DataFrame(df_data)
        
        # Análisis por estrategia
        strategy_analysis = df.groupby('strategy').agg({
            'truck_count_accuracy': ['mean', 'std'],
            'overall_score': ['mean', 'std'],
            'execution_time': ['mean', 'std']
        }).round(4)
        
        # Aplanar columnas MultiIndex para evitar problemas con JSON
        strategy_analysis.columns = ['_'.join(col).strip() for col in strategy_analysis.columns.values]
        strategy_analysis = strategy_analysis.to_dict('index')
        
        # Análisis por complejidad
        complexity_analysis = df.groupby('complexity_level').agg({
            'overall_score': ['mean', 'std'],
            'truck_count_accuracy': ['mean', 'std']
        }).round(4)
        
        # Aplanar columnas MultiIndex para evitar problemas con JSON
        complexity_analysis.columns = ['_'.join(col).strip() for col in complexity_analysis.columns.values]
        complexity_analysis = complexity_analysis.to_dict('index')
        
        # Mejores estrategias por métrica
        best_strategies = {
            'truck_count_accuracy': df.loc[df['truck_count_accuracy'].idxmax()]['strategy'],
            'overall_score': df.loc[df['overall_score'].idxmax()]['strategy'],
            'execution_time': df.loc[df['execution_time'].idxmin()]['strategy']
        }
        
        # Recomendaciones
        recommendations = self._generate_recommendations(df)
        
        report = {
            'executive_summary': {
                'total_tests': len(self.results),
                'strategies_evaluated': df['strategy'].nunique(),
                'average_overall_score': df['overall_score'].mean(),
                'best_strategy_overall': best_strategies['overall_score'],
                'best_strategy_truck_accuracy': best_strategies['truck_count_accuracy']
            },
            'strategy_performance': strategy_analysis,
            'complexity_analysis': complexity_analysis,
            'best_strategies': best_strategies,
            'recommendations': recommendations,
            'detailed_results': self.results,
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        return report
    
    def _generate_recommendations(self, df: pd.DataFrame) -> List[str]:
        """Genera recomendaciones basadas en el análisis"""
        
        recommendations = []
        
        # Recomendación por mejor estrategia general
        best_overall = df.groupby('strategy')['overall_score'].mean().idxmax()
        recommendations.append(
            f"🏆 La estrategia '{best_overall}' mostró el mejor rendimiento general con una puntuación promedio de {df[df['strategy'] == best_overall]['overall_score'].mean():.3f}"
        )
        
        # Recomendación por precisión en número de camiones
        best_trucks = df.groupby('strategy')['truck_count_accuracy'].mean().idxmax()
        if best_trucks != best_overall:
            recommendations.append(
                f"🚛 Para máxima precisión en conteo de camiones, considere '{best_trucks}' con {df[df['strategy'] == best_trucks]['truck_count_accuracy'].mean():.3f} de precisión"
            )
        
        # Recomendación por velocidad
        fastest = df.groupby('strategy')['execution_time'].mean().idxmin()
        recommendations.append(
            f"⚡ La estrategia más rápida es '{fastest}' con {df[df['strategy'] == fastest]['execution_time'].mean():.3f} segundos promedio"
        )
        
        # Recomendación por complejidad
        complex_cases = df[df['complexity_level'] == 'complex']
        if not complex_cases.empty:
            best_for_complex = complex_cases.groupby('strategy')['overall_score'].mean().idxmax()
            recommendations.append(
                f"🧩 Para casos complejos, '{best_for_complex}' es la mejor opción con {complex_cases[complex_cases['strategy'] == best_for_complex]['overall_score'].mean():.3f} de puntuación"
            )
        
        return recommendations
    
    def save_analysis_report(self, filename: str = None) -> str:
        """Guarda el reporte de análisis en un archivo"""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"prompt_engineering_analysis_{timestamp}.json"
        
        report = self._compile_analysis_report()
        
        # Crear directorio de resultados si no existe
        results_dir = Path(__file__).parent / "analysis_results"
        results_dir.mkdir(exist_ok=True)
        
        filepath = results_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Reporte guardado en: {filepath}")
        return str(filepath)
    
    def create_visualization(self, save_path: str = None) -> str:
        """Crea visualizaciones del análisis"""
        
        if not self.results:
            return "No hay resultados para visualizar"
        
        # Convertir a DataFrame
        df_data = []
        for result in self.results:
            row = {
                'strategy': result['strategy'],
                'test_case_id': result['test_case_id'],
                'complexity_level': result['complexity_level'],
                'truck_count_accuracy': result['metrics'].truck_count_accuracy,
                'overall_score': result['metrics'].overall_score,
                'execution_time': result['metrics'].execution_time
            }
            df_data.append(row)
        
        df = pd.DataFrame(df_data)
        
        # Crear figura con subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Análisis de Estrategias de Prompt Engineering para CVRP', fontsize=16, fontweight='bold')
        
        # 1. Rendimiento por estrategia
        strategy_scores = df.groupby('strategy')['overall_score'].mean().sort_values(ascending=True)
        axes[0, 0].barh(range(len(strategy_scores)), strategy_scores.values)
        axes[0, 0].set_yticks(range(len(strategy_scores)))
        axes[0, 0].set_yticklabels(strategy_scores.index, rotation=0)
        axes[0, 0].set_xlabel('Puntuación General Promedio')
        axes[0, 0].set_title('Rendimiento por Estrategia')
        axes[0, 0].grid(axis='x', alpha=0.3)
        
        # 2. Precisión de conteo de camiones
        truck_accuracy = df.groupby('strategy')['truck_count_accuracy'].mean().sort_values(ascending=True)
        axes[0, 1].barh(range(len(truck_accuracy)), truck_accuracy.values, color='orange')
        axes[0, 1].set_yticks(range(len(truck_accuracy)))
        axes[0, 1].set_yticklabels(truck_accuracy.index, rotation=0)
        axes[0, 1].set_xlabel('Precisión de Conteo de Camiones')
        axes[0, 1].set_title('Precisión en Número de Camiones')
        axes[0, 1].grid(axis='x', alpha=0.3)
        
        # 3. Tiempo de ejecución
        execution_times = df.groupby('strategy')['execution_time'].mean().sort_values(ascending=True)
        axes[1, 0].barh(range(len(execution_times)), execution_times.values, color='green')
        axes[1, 0].set_yticks(range(len(execution_times)))
        axes[1, 0].set_yticklabels(execution_times.index, rotation=0)
        axes[1, 0].set_xlabel('Tiempo de Ejecución (segundos)')
        axes[1, 0].set_title('Velocidad de Respuesta')
        axes[1, 0].grid(axis='x', alpha=0.3)
        
        # 4. Heatmap de rendimiento por complejidad
        pivot_data = df.pivot_table(values='overall_score', index='strategy', columns='complexity_level', aggfunc='mean')
        sns.heatmap(pivot_data, annot=True, cmap='YlOrRd', ax=axes[1, 1], cbar_kws={'label': 'Puntuación'})
        axes[1, 1].set_title('Rendimiento por Complejidad')
        axes[1, 1].set_xlabel('Nivel de Complejidad')
        axes[1, 1].set_ylabel('Estrategia')
        
        plt.tight_layout()
        
        # Guardar visualización
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = Path(__file__).parent / "analysis_results" / f"prompt_analysis_visualization_{timestamp}.png"
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Visualización guardada en: {save_path}")
        return str(save_path)

def main():
    """Función principal para ejecutar el análisis completo"""
    
    print("🚀 Iniciando Análisis Completo de Prompt Engineering para CVRP")
    print("=" * 60)
    
    # Crear analizador
    analyzer = CVRPPromptAnalyzer()
    
    # Ejecutar análisis con todas las estrategias
    print("\n📊 Ejecutando análisis con todas las estrategias...")
    report = analyzer.run_comprehensive_analysis()
    
    # Mostrar resumen ejecutivo
    print("\n📈 RESUMEN EJECUTIVO")
    print("-" * 30)
    summary = report['executive_summary']
    print(f"Total de pruebas: {summary['total_tests']}")
    print(f"Estrategias evaluadas: {summary['strategies_evaluated']}")
    print(f"Puntuación promedio general: {summary['average_overall_score']:.3f}")
    print(f"Mejor estrategia (general): {summary['best_strategy_overall']}")
    print(f"Mejor estrategia (precisión camiones): {summary['best_strategy_truck_accuracy']}")
    
    # Mostrar recomendaciones
    print("\n💡 RECOMENDACIONES")
    print("-" * 30)
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"{i}. {rec}")
    
    # Guardar reporte
    print("\n💾 Guardando resultados...")
    report_path = analyzer.save_analysis_report()
    viz_path = analyzer.create_visualization()
    
    print(f"✅ Reporte guardado: {report_path}")
    print(f"✅ Visualización guardada: {viz_path}")
    
    print("\n🎉 Análisis completo finalizado!")
    
    return report

if __name__ == "__main__":
    # Ejecutar análisis completo
    analysis_report = main()
