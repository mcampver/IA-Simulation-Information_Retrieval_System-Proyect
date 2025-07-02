"""
Comparador de Prompts CVRP - Análisis Específico del Prompt Actual vs Optimizados
================================================================================

Este script se enfoca específicamente en comparar el prompt actual utilizado en 
cvrp_assistant.py con versiones optimizadas usando técnicas de prompt engineering.

Autor: Sistema de Optimización de Prompts
Fecha: 2025-07-02
"""

import json
import os
import sys
import time
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import re
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Añadir el directorio raíz al path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

# Importar módulos necesarios
from src.NLP.Gemini import Gemini
from src.NLP.cvrp_assistant import CVRPAssistant

class CurrentPromptExtractor:
    """Extrae y analiza el prompt actual usado en cvrp_assistant.py"""
    
    def __init__(self):
        self.current_prompt_template = self._extract_current_prompt()
    
    def _extract_current_prompt(self) -> str:
        """Extrae el template del prompt actual del archivo cvrp_assistant.py"""
        
        # Este es el prompt actual extraído del código
        return '''
        {header_trucks}
        The user has a Capacitated Vehicle Routing Problem (CVRP) with the following configuration:

        DEPOT:
        - Node ID: {depot_id}
        - Coordinates: {depot_position}

        TARGET LOCATIONS ({num_targets} destinations):
        {targets_formatted}

        SELECTED ALGORITHM: {solver_description}

        USER DESCRIPTION:
        "{user_description}"

        Please analyze the user's description and extract the following information, considering that {solver_title} will be used:

        1. NUMBER OF TRUCKS: {trucks_instruction}

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
        - The target_demands list must contain exactly {num_targets} elements
        - All numbers must be positive integers
        - Do not include any text outside of the JSON
        '''
    
    def format_current_prompt(self, depot_info: dict, targets_info: list, 
                             user_description: str, solver: str, explicit_trucks: Optional[int] = None) -> str:
        """Formatea el prompt actual con los datos proporcionados"""
        
        # Preparar header de camiones
        header_trucks = ""
        if explicit_trucks is not None:
            header_trucks = (
                f"El usuario ha indicado que tiene EXACTAMENTE "
                f"{explicit_trucks} camiones disponibles.\n\n"
            )
        
        # Instrucción para camiones
        trucks_instruction = (
            f"Use EXACTLY the {explicit_trucks} trucks the user specified."
            if explicit_trucks is not None
            else f"How many vehicles are needed? If not specified, suggest a reasonable number based on the {len(targets_info)} destinations and the {solver} algorithm."
        )
        
        # Formatear targets
        targets_formatted = ""
        for i, target in enumerate(targets_info, 1):
            targets_formatted += f"  {i}. Nodo ID: {target['id']} - Coordenadas: {target['position']}\n"
        targets_formatted = targets_formatted.strip()
        
        # Descripción del solver
        solver_descriptions = {
            'vns_solver': 'Variable Neighborhood Search - Búsqueda en vecindario variable, bueno para problemas medianos',
            'ts_solver': 'Tabu Search - Búsqueda tabú, excelente para escape de óptimos locales',
            'sa_solver': 'Simulated Annealing - Recocido simulado, robusto para problemas complejos',
            'ag_solver': 'Algoritmo Genético - Evolución de poblaciones, buena exploración global'
        }
        solver_description = solver_descriptions.get(solver, 'Algoritmo de optimización')
        
        return self.current_prompt_template.format(
            header_trucks=header_trucks,
            depot_id=depot_info['id'],
            depot_position=depot_info['position'],
            num_targets=len(targets_info),
            targets_formatted=targets_formatted,
            solver_description=solver_description,
            solver_title=solver.replace('_', ' ').title(),
            user_description=user_description,
            trucks_instruction=trucks_instruction,
            solver=solver
        )

class OptimizedPromptGenerator:
    """Genera versiones optimizadas del prompt actual"""
    
    def __init__(self):
        self.optimization_strategies = {
            'clarity_enhanced': self._generate_clarity_enhanced,
            'constraint_focused': self._generate_constraint_focused,
            'example_driven': self._generate_example_driven,
            'step_by_step_enhanced': self._generate_step_by_step_enhanced,
            'validation_focused': self._generate_validation_focused,
            'context_rich': self._generate_context_rich
        }
    
    def generate_optimized_prompt(self, strategy: str, depot_info: dict, targets_info: list, 
                                 user_description: str, solver: str, explicit_trucks: Optional[int] = None) -> str:
        """Genera un prompt optimizado según la estrategia especificada"""
        return self.optimization_strategies[strategy](depot_info, targets_info, user_description, solver, explicit_trucks)
    
    def _generate_clarity_enhanced(self, depot_info: dict, targets_info: list, 
                                  user_description: str, solver: str, explicit_trucks: Optional[int] = None) -> str:
        """Versión con claridad mejorada del prompt actual"""
        
        header_trucks = ""
        if explicit_trucks is not None:
            header_trucks = f"🚛 CONSTRAINT: The user has specified EXACTLY {explicit_trucks} trucks available.\n\n"
        
        return f'''
        🎯 MISSION: Extract precise CVRP parameters from user description
        
        {header_trucks}📍 PROBLEM SETUP:
        ├── Depot (Starting Point): Node {depot_info['id']} at {depot_info['position']}
        ├── Destinations: {len(targets_info)} delivery locations
        ├── Algorithm: {solver.replace('_', ' ').title()}
        └── User Request: "{user_description}"
        
        🔍 DESTINATIONS DETAILS:
        {self._format_targets_numbered(targets_info)}
        
        📋 EXTRACTION TASKS:
        
        1️⃣ VEHICLE COUNT:
           {f"→ Use EXACTLY {explicit_trucks} trucks (user specified)" if explicit_trucks else f"→ Determine optimal number of vehicles for {len(targets_info)} destinations"}
        
        2️⃣ VEHICLE CAPACITIES:
           → Analyze context clues for capacity requirements
           → If not specified, suggest realistic capacities based on delivery type
        
        3️⃣ LOCATION DEMANDS:
           → Extract or infer demand for each of the {len(targets_info)} destinations
           → Ensure demands are realistic and balanced
        
        📤 OUTPUT FORMAT (JSON ONLY):
        {{
            "num_trucks": <integer>,
            "truck_capacities": [<{explicit_trucks or 'N'} capacities>],
            "target_demands": [<{len(targets_info)} demands>],
            "extraction_confidence": {{
                "trucks_confidence": "<high|medium|low>",
                "capacities_confidence": "<high|medium|low>",
                "demands_confidence": "<high|medium|low>"
            }},
            "reasoning": {{
                "trucks_rationale": "clear explanation",
                "capacities_rationale": "clear explanation", 
                "demands_rationale": "clear explanation"
            }}
        }}
        
        ⚠️ VALIDATION REQUIREMENTS:
        ✓ truck_capacities.length == num_trucks
        ✓ target_demands.length == {len(targets_info)}
        ✓ All values are positive integers
        ✓ Total capacity ≥ Total demand
        '''
    
    def _generate_constraint_focused(self, depot_info: dict, targets_info: list, 
                                    user_description: str, solver: str, explicit_trucks: Optional[int] = None) -> str:
        """Versión enfocada en restricciones y validación"""
        
        return f'''
        CONSTRAINT-AWARE CVRP PARAMETER EXTRACTION
        ==========================================
        
        PRIMARY CONSTRAINTS:
        {'• FIXED TRUCKS: ' + str(explicit_trucks) + ' vehicles available' if explicit_trucks else '• FLEXIBLE TRUCKS: Optimize vehicle count'}
        • DESTINATIONS: Exactly {len(targets_info)} delivery points required
        • ALGORITHM: {solver} optimization method
        • FEASIBILITY: Total capacity must exceed total demand
        
        INPUT DATA:
        • Depot: {depot_info['id']} at {depot_info['position']}
        • User Description: "{user_description}"
        
        CONSTRAINT ANALYSIS PROCESS:
        
        STEP 1: EXPLICIT CONSTRAINT IDENTIFICATION
        □ Check for explicit truck count → {explicit_trucks if explicit_trucks else 'Not specified'}
        □ Check for explicit capacities → Scan user description
        □ Check for explicit demands → Scan user description
        
        STEP 2: IMPLICIT CONSTRAINT INFERENCE  
        □ Infer missing truck count based on destinations/capacity ratio
        □ Infer capacities from delivery context (food, medicine, etc.)
        □ Infer demands from location types (stores, restaurants, etc.)
        
        STEP 3: FEASIBILITY VALIDATION
        □ Verify: sum(truck_capacities) ≥ sum(target_demands)
        □ Verify: num_trucks is reasonable for {len(targets_info)} destinations
        □ Verify: all values are positive integers
        
        STEP 4: OPTIMIZATION CONSIDERATION
        □ Consider {solver} algorithm characteristics
        □ Balance between solution quality and computational efficiency
        
        REQUIRED OUTPUT (JSON):
        {{
            "constraint_analysis": {{
                "explicit_trucks": {explicit_trucks if explicit_trucks else 'null'},
                "explicit_capacities": "<found|not_found>",
                "explicit_demands": "<found|not_found>"
            }},
            "num_trucks": <integer>,
            "truck_capacities": [<list_of_{explicit_trucks or 'N'}_integers>],
            "target_demands": [<list_of_{len(targets_info)}_integers>],
            "feasibility_check": {{
                "total_capacity": <sum_of_capacities>,
                "total_demand": <sum_of_demands>,
                "is_feasible": <true|false>
            }}
        }}
        '''
    
    def _generate_example_driven(self, depot_info: dict, targets_info: list, 
                                user_description: str, solver: str, explicit_trucks: Optional[int] = None) -> str:
        """Versión con ejemplos para mejorar comprensión"""
        
        return f'''
        CVRP PARAMETER EXTRACTION WITH EXAMPLES
        ======================================
        
        📚 LEARNING FROM EXAMPLES:
        
        EXAMPLE 1 - Explicit Case:
        Input: "Tengo 2 camiones de 50 cajas para 3 tiendas que necesitan 20, 15 y 10 cajas"
        Analysis: ✓ Trucks: 2 (explicit), ✓ Capacities: [50,50] (explicit), ✓ Demands: [20,15,10] (explicit)
        Output: {{"num_trucks": 2, "truck_capacities": [50,50], "target_demands": [20,15,10]}}
        
        EXAMPLE 2 - Partial Information:
        Input: "Necesito repartir medicinas a 4 farmacias con 1 camión grande"
        Analysis: ✓ Trucks: 1 (explicit), ✓ Capacities: [120] (inferred-large), ✓ Demands: [30,25,35,30] (inferred-balanced)
        Output: {{"num_trucks": 1, "truck_capacities": [120], "target_demands": [30,25,35,30]}}
        
        EXAMPLE 3 - Ambiguous Case:
        Input: "Entrega urgente a varios restaurantes"
        Analysis: ✓ Trucks: 2 (inferred), ✓ Capacities: [80,70] (inferred-medium), ✓ Demands: [40,35,25] (inferred-varied)
        Output: {{"num_trucks": 2, "truck_capacities": [80,70], "target_demands": [40,35,25]}}
        
        🎯 YOUR TASK:
        Current Case: "{user_description}"
        Depot: {depot_info['id']} at {depot_info['position']}
        Destinations: {len(targets_info)} locations
        {f"Constraint: EXACTLY {explicit_trucks} trucks" if explicit_trucks else "Constraint: Optimize truck count"}
        
        Following the pattern above, analyze this case:
        
        🔍 ANALYSIS PROCESS:
        1. Identify explicit parameters (what user clearly stated)
        2. Infer missing parameters (using context and examples)
        3. Validate feasibility (capacity ≥ demand)
        4. Apply algorithm considerations for {solver}
        
        📋 OUTPUT (JSON format like examples):
        {{
            "example_pattern_used": "<which_example_pattern_is_most_similar>",
            "num_trucks": <integer>,
            "truck_capacities": [<list_of_{explicit_trucks or 'N'}_integers>],
            "target_demands": [<list_of_{len(targets_info)}_integers>],
            "parameter_sources": {{
                "trucks_source": "<explicit|inferred_from_examples>",
                "capacities_source": "<explicit|inferred_from_context|inferred_from_examples>",
                "demands_source": "<explicit|inferred_balanced|inferred_varied>"
            }}
        }}
        '''
    
    def _generate_step_by_step_enhanced(self, depot_info: dict, targets_info: list, 
                                       user_description: str, solver: str, explicit_trucks: Optional[int] = None) -> str:
        """Versión con proceso paso a paso mejorado"""
        
        return f'''
        ENHANCED STEP-BY-STEP CVRP ANALYSIS
        ==================================
        
        📋 INPUTS:
        • Depot: {depot_info['id']} at {depot_info['position']}
        • Destinations: {len(targets_info)} locations  
        • User Request: "{user_description}"
        • Algorithm: {solver}
        {f'• Truck Constraint: EXACTLY {explicit_trucks} vehicles' if explicit_trucks else '• Truck Constraint: None (optimize)'}
        
        🔄 ANALYSIS WORKFLOW:
        
        ┌─ STEP 1: TEXT PARSING ─┐
        │ □ Scan for numbers      │
        │ □ Identify vehicle words│  
        │ □ Find capacity keywords│
        │ □ Locate demand hints   │
        └─────────────────────────┘
                    ↓
        ┌─ STEP 2: PARAMETER EXTRACTION ─┐
        │ Trucks: {f'{explicit_trucks} (fixed)' if explicit_trucks else '? (to determine)'}        │
        │ Capacities: ? (extract/infer)   │
        │ Demands: ? (extract/infer)      │
        └─────────────────────────────────┘
                    ↓
        ┌─ STEP 3: INTELLIGENT INFERENCE ─┐
        │ • Use context clues              │
        │ • Apply domain knowledge         │
        │ • Consider {len(targets_info)} destinations ratio   │
        │ • Factor in {solver} efficiency  │
        └──────────────────────────────────┘
                    ↓
        ┌─ STEP 4: VALIDATION & BALANCING ─┐
        │ • Check: total_capacity ≥ total_demand │
        │ • Ensure: realistic truck count        │
        │ • Verify: positive integer values      │
        │ • Balance: workload distribution       │
        └─────────────────────────────────────────┘
                    ↓
        ┌─ STEP 5: OPTIMIZATION TUNING ─┐
        │ • Adjust for {solver} algorithm │
        │ • Consider computational cost   │
        │ • Optimize for solution quality │
        └─────────────────────────────────┘
        
        📤 DELIVER RESULTS:
        
        Execute each step above and provide results in this JSON format:
        {{
            "step_1_parsing": {{
                "numbers_found": [<list_of_numbers_in_text>],
                "vehicle_keywords": [<vehicle_related_words>],
                "capacity_keywords": [<capacity_related_words>],
                "demand_keywords": [<demand_related_words>]
            }},
            "step_2_extraction": {{
                "explicit_trucks": {explicit_trucks if explicit_trucks else 'null'},
                "explicit_capacities": "<found_values_or_null>",
                "explicit_demands": "<found_values_or_null>"
            }},
            "step_3_inference": {{
                "inferred_trucks": <integer_if_needed>,
                "inferred_capacities": [<list_if_needed>],
                "inferred_demands": [<list_if_needed>],
                "inference_logic": "explanation of reasoning"
            }},
            "step_4_validation": {{
                "total_capacity": <sum>,
                "total_demand": <sum>,
                "is_feasible": <true|false>,
                "adjustments_made": "any corrections applied"
            }},
            "step_5_optimization": {{
                "algorithm_considerations": "{solver} specific adjustments",
                "final_tuning": "any final optimizations"
            }},
            "final_solution": {{
                "num_trucks": <integer>,
                "truck_capacities": [<list>],
                "target_demands": [<list>]
            }}
        }}
        '''
    
    def _generate_validation_focused(self, depot_info: dict, targets_info: list, 
                                    user_description: str, solver: str, explicit_trucks: Optional[int] = None) -> str:
        """Versión con enfoque en validación y consistencia"""
        
        return f'''
        VALIDATION-FOCUSED CVRP PARAMETER EXTRACTION
        ===========================================
        
        🎯 OBJECTIVE: Extract and validate CVRP parameters with high confidence
        
        📊 INPUT VALIDATION:
        ✓ Depot: {depot_info['id']} at {depot_info['position']} (valid coordinates)
        ✓ Targets: {len(targets_info)} destinations (valid count)
        ✓ Algorithm: {solver} (supported method)
        {f'✓ Truck constraint: {explicit_trucks} vehicles (user specified)' if explicit_trucks else '⚠ Truck count: To be determined'}
        ✓ User description: "{user_description}" (non-empty)
        
        🔍 EXTRACTION WITH VALIDATION:
        
        TRUCKS VALIDATION:
        {f'• Fixed at {explicit_trucks} (user constraint)' if explicit_trucks else '• Must determine optimal count'}
        • Validation rules:
          - Must be positive integer
          - Reasonable for {len(targets_info)} destinations (typically 1 to {max(1, len(targets_info)//2)})
          - Compatible with {solver} algorithm efficiency
        
        CAPACITIES VALIDATION:
        • Must extract/infer {explicit_trucks or 'N'} capacity values
        • Validation rules:
          - All values must be positive integers  
          - Realistic range: 10-500 units typical
          - Sum must be sufficient for total demand
          - Individual capacities should be balanced
        
        DEMANDS VALIDATION:
        • Must extract/infer exactly {len(targets_info)} demand values
        • Validation rules:
          - All values must be positive integers
          - Realistic range: 5-200 units per location typical
          - Total demand should not exceed 80% of total capacity
          - Distribution should reflect location types
        
        🔧 SELF-CORRECTION PROTOCOL:
        If initial extraction fails validation:
        1. Adjust values to meet constraints
        2. Ensure mathematical feasibility
        3. Apply domain knowledge corrections
        4. Verify final solution consistency
        
        📋 VALIDATED OUTPUT:
        {{
            "extraction_confidence": {{
                "overall_confidence": "<high|medium|low>",
                "trucks_confidence": "<high|medium|low>",
                "capacities_confidence": "<high|medium|low>", 
                "demands_confidence": "<high|medium|low>"
            }},
            "validation_results": {{
                "trucks_valid": <true|false>,
                "capacities_valid": <true|false>,
                "demands_valid": <true|false>,
                "mathematical_feasible": <true|false>,
                "total_capacity": <integer>,
                "total_demand": <integer>,
                "capacity_utilization": <percentage>
            }},
            "final_parameters": {{
                "num_trucks": <validated_integer>,
                "truck_capacities": [<validated_list_of_{explicit_trucks or 'N'}>],
                "target_demands": [<validated_list_of_{len(targets_info)}>]
            }},
            "corrections_applied": [<list_of_any_corrections_made>],
            "validation_warnings": [<list_of_any_concerns>]
        }}
        '''
    
    def _generate_context_rich(self, depot_info: dict, targets_info: list, 
                              user_description: str, solver: str, explicit_trucks: Optional[int] = None) -> str:
        """Versión enriquecida con contexto geográfico y cultural"""
        
        return f'''
        CONTEXT-RICH CVRP ANALYSIS FOR HAVANA, CUBA
        ==========================================
        
        🌍 GEOGRAPHIC & CULTURAL CONTEXT:
        
        📍 LOCATION INTELLIGENCE:
        • Region: Havana, Cuba (Caribbean, tropical climate)
        • Urban density: High (affects traffic patterns)
        • Infrastructure: Mixed modern/colonial road network
        • Depot location: {depot_info['id']} at {depot_info['position']}
        • Service area: {len(targets_info)} urban delivery points
        
        🚛 LOCAL LOGISTICS CONTEXT:
        • Typical vehicles: Medium trucks (30-150 unit capacity)
        • Common delivery types: Food, medicine, consumer goods
        • Traffic patterns: Heavy during 7-9am, 5-7pm
        • Fuel considerations: Efficiency important due to availability
        • Cultural factors: Relationship-based business, flexible timing
        
        ⚙️ ALGORITHM CONTEXT ({solver}):
        • Best for: {self._get_algorithm_context(solver)}
        • Typical performance: {self._get_algorithm_performance(solver)}
        • Recommended for: {len(targets_info)} destinations scenario
        
        🎯 USER SCENARIO ANALYSIS:
        Input: "{user_description}"
        {f'Constraint: EXACTLY {explicit_trucks} trucks available' if explicit_trucks else 'Constraint: Flexible fleet size'}
        
        🧠 CONTEXTUAL PARAMETER EXTRACTION:
        
        TRUCKS (considering local fleet availability):
        {f'• Fixed: {explicit_trucks} vehicles (user specified)' if explicit_trucks else f'• Optimal for Havana: 1-{max(1, len(targets_info)//3)} trucks for {len(targets_info)} destinations'}
        • Local consideration: Cuban truck availability and fuel efficiency
        
        CAPACITIES (based on Havana logistics):
        • Context clues from user description
        • Local standards: Small (30-50), Medium (60-100), Large (120-200)
        • Fuel efficiency: Prefer balanced loads over oversized vehicles
        
        DEMANDS (reflecting Cuban business patterns):
        • Urban delivery patterns in Havana
        • Business size distribution: Mix of small shops and larger stores
        • Seasonal/cultural demand variations
        
        📊 CULTURALLY-INFORMED OUTPUT:
        {{
            "contextual_analysis": {{
                "location_type": "Havana urban area",
                "business_context": "<food_delivery|medical_supply|retail|other>",
                "cultural_factors": [<list_of_cultural_considerations>],
                "infrastructure_impact": "road conditions and traffic assessment"
            }},
            "local_optimization": {{
                "fuel_efficiency_priority": "<high|medium|low>",
                "traffic_pattern_consideration": "<peak_hours|off_peak|flexible>",
                "vehicle_size_preference": "<small|medium|large|mixed>"
            }},
            "extracted_parameters": {{
                "num_trucks": <culturally_optimized_integer>,
                "truck_capacities": [<locally_appropriate_capacities>],
                "target_demands": [<havana_business_realistic_demands>]
            }},
            "cultural_reasoning": {{
                "trucks_rationale": "why this number works in Havana context",
                "capacities_rationale": "how capacities reflect local logistics",
                "demands_rationale": "how demands reflect Cuban business patterns"
            }}
        }}
        '''
    
    def _format_targets_numbered(self, targets_info: list) -> str:
        """Formatea los targets con numeración"""
        formatted = ""
        for i, target in enumerate(targets_info, 1):
            formatted += f"        {i}. Node {target['id']} at {target['position']}\n"
        return formatted.strip()
    
    def _get_algorithm_context(self, solver: str) -> str:
        """Obtiene contexto del algoritmo"""
        contexts = {
            'vns_solver': 'Medium-scale problems with balanced exploration',
            'ts_solver': 'Escaping local optima, good solution quality',
            'sa_solver': 'Complex optimization landscapes, robust solutions',
            'ag_solver': 'Large solution spaces, population-based search'
        }
        return contexts.get(solver, 'General optimization problems')
    
    def _get_algorithm_performance(self, solver: str) -> str:
        """Obtiene información de rendimiento del algoritmo"""
        performances = {
            'vns_solver': 'Fast convergence, good for 3-15 destinations',
            'ts_solver': 'Medium speed, excellent solution quality',
            'sa_solver': 'Slower but very robust, handles complexity well',
            'ag_solver': 'Variable speed, excellent for diverse solution exploration'
        }
        return performances.get(solver, 'Performance depends on problem complexity')

class PromptComparator:
    """Compara el prompt actual con las versiones optimizadas"""
    
    def __init__(self):
        self.gemini = Gemini()
        self.current_extractor = CurrentPromptExtractor()
        self.optimizer = OptimizedPromptGenerator()
        self.test_cases = self._create_comparison_test_cases()
    
    def _create_comparison_test_cases(self) -> List[Dict]:
        """Crea casos de prueba específicos para comparación de prompts"""
        
        depot = {"id": 12345, "position": [-82.3666, 23.1136]}
        
        return [
            {
                "id": "compare_01",
                "name": "Caso Explícito con Números Claros",
                "user_input": "Tengo 2 camiones de 80 cajas cada uno para repartir a 4 tiendas que necesitan 30, 25, 20 y 35 cajas",
                "depot_info": depot,
                "targets_info": [
                    {"id": 101, "position": [-82.3656, 23.1146]},
                    {"id": 102, "position": [-82.3676, 23.1126]},
                    {"id": 103, "position": [-82.3686, 23.1156]},
                    {"id": 104, "position": [-82.3696, 23.1166]}
                ],
                "expected": {
                    "num_trucks": 2,
                    "truck_capacities": [80, 80],
                    "target_demands": [30, 25, 20, 35]
                },
                "complexity": "simple",
                "explicit_trucks": 2
            },
            {
                "id": "compare_02", 
                "name": "Caso Ambiguo con Contexto",
                "user_input": "Necesito entregar medicinas urgentes a varios hospitales con los vehículos que tengo disponibles",
                "depot_info": depot,
                "targets_info": [
                    {"id": 201, "position": [-82.3650, 23.1140]},
                    {"id": 202, "position": [-82.3670, 23.1130]},
                    {"id": 203, "position": [-82.3690, 23.1170]}
                ],
                "expected": {
                    "num_trucks": 2,
                    "truck_capacities": [100, 80],
                    "target_demands": [60, 50, 40]
                },
                "complexity": "medium",
                "explicit_trucks": None
            },
            {
                "id": "compare_03",
                "name": "Caso Conflictivo",
                "user_input": "Tengo 1 camión pequeño pero necesito entregar grandes volúmenes a 6 restaurantes",
                "depot_info": depot,
                "targets_info": [
                    {"id": 301, "position": [-82.3655, 23.1145]},
                    {"id": 302, "position": [-82.3665, 23.1135]},
                    {"id": 303, "position": [-82.3675, 23.1155]},
                    {"id": 304, "position": [-82.3685, 23.1125]},
                    {"id": 305, "position": [-82.3695, 23.1165]},
                    {"id": 306, "position": [-82.3705, 23.1175]}
                ],
                "expected": {
                    "num_trucks": 3,
                    "truck_capacities": [60, 60, 50],
                    "target_demands": [35, 30, 25, 40, 30, 35]
                },
                "complexity": "complex",
                "explicit_trucks": 1  # Conflicto: dice 1 pero necesita más
            }
        ]
    
    def run_comparison_analysis(self) -> Dict[str, Any]:
        """Ejecuta análisis comparativo completo"""
        
        logger.info("Iniciando análisis comparativo de prompts")
        
        # Estrategias a comparar
        optimization_strategies = [
            'clarity_enhanced',
            'constraint_focused', 
            'example_driven',
            'step_by_step_enhanced',
            'validation_focused',
            'context_rich'
        ]
        
        results = []
        
        for test_case in self.test_cases:
            logger.info(f"Evaluando caso: {test_case['name']}")
            
            case_results = {
                'test_case': test_case,
                'prompt_results': {}
            }
            
            # Evaluar prompt actual
            try:
                current_prompt = self.current_extractor.format_current_prompt(
                    test_case['depot_info'],
                    test_case['targets_info'],
                    test_case['user_input'],
                    'vns_solver',
                    test_case['explicit_trucks']
                )
                
                start_time = time.time()
                current_response = self.gemini.ask(current_prompt)
                current_time = time.time() - start_time
                
                case_results['prompt_results']['current'] = {
                    'prompt': current_prompt,
                    'response': current_response,
                    'execution_time': current_time,
                    'metrics': self._evaluate_response(current_response, test_case['expected'])
                }
                
                time.sleep(1)  # Evitar rate limiting
                
            except Exception as e:
                logger.error(f"Error evaluando prompt actual: {e}")
                case_results['prompt_results']['current'] = {'error': str(e)}
            
            # Evaluar prompts optimizados
            for strategy in optimization_strategies:
                try:
                    optimized_prompt = self.optimizer.generate_optimized_prompt(
                        strategy,
                        test_case['depot_info'],
                        test_case['targets_info'],
                        test_case['user_input'],
                        'vns_solver',
                        test_case['explicit_trucks']
                    )
                    
                    start_time = time.time()
                    optimized_response = self.gemini.ask(optimized_prompt)
                    optimized_time = time.time() - start_time
                    
                    case_results['prompt_results'][strategy] = {
                        'prompt': optimized_prompt,
                        'response': optimized_response,
                        'execution_time': optimized_time,
                        'metrics': self._evaluate_response(optimized_response, test_case['expected'])
                    }
                    
                    time.sleep(1)  # Evitar rate limiting
                    
                except Exception as e:
                    logger.error(f"Error evaluando estrategia {strategy}: {e}")
                    case_results['prompt_results'][strategy] = {'error': str(e)}
            
            results.append(case_results)
        
        # Compilar reporte comparativo
        comparison_report = self._compile_comparison_report(results)
        
        return comparison_report
    
    def _evaluate_response(self, response: str, expected: Dict) -> Dict[str, float]:
        """Evalúa una respuesta individual"""
        
        metrics = {
            'truck_accuracy': 0.0,
            'capacity_accuracy': 0.0,
            'demand_accuracy': 0.0,
            'json_validity': 0.0,
            'completeness': 0.0,
            'overall_score': 0.0
        }
        
        try:
            # Extraer JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)
                metrics['json_validity'] = 1.0
                
                # Evaluar número de camiones
                if 'num_trucks' in parsed:
                    actual_trucks = parsed['num_trucks']
                    expected_trucks = expected['num_trucks']
                    # Verificar que sean números válidos
                    if isinstance(actual_trucks, (int, float)) and isinstance(expected_trucks, (int, float)):
                        if actual_trucks == expected_trucks:
                            metrics['truck_accuracy'] = 1.0
                        else:
                            diff = abs(float(actual_trucks) - float(expected_trucks))
                            metrics['truck_accuracy'] = max(0, 1 - (diff / float(expected_trucks)))
                    else:
                        metrics['truck_accuracy'] = 0.0
                
                # Evaluar capacidades
                if 'truck_capacities' in parsed:
                    actual_caps = parsed['truck_capacities']
                    expected_caps = expected['truck_capacities']
                    # Verificar que sean listas válidas de números
                    if (isinstance(actual_caps, list) and isinstance(expected_caps, list) and
                        all(isinstance(x, (int, float)) for x in actual_caps) and
                        all(isinstance(x, (int, float)) for x in expected_caps)):
                        if len(actual_caps) == len(expected_caps):
                            errors = [abs(float(a) - float(e)) for a, e in zip(actual_caps, expected_caps)]
                            avg_error = sum(errors) / len(errors)
                            avg_expected = sum(expected_caps) / len(expected_caps)
                            metrics['capacity_accuracy'] = max(0, 1 - (avg_error / avg_expected))
                        else:
                            metrics['capacity_accuracy'] = 0.3  # Penalización por longitud
                    else:
                        metrics['capacity_accuracy'] = 0.0
                
                # Evaluar demandas
                if 'target_demands' in parsed:
                    actual_demands = parsed['target_demands']
                    expected_demands = expected['target_demands']
                    # Verificar que sean listas válidas de números
                    if (isinstance(actual_demands, list) and isinstance(expected_demands, list) and
                        all(isinstance(x, (int, float)) for x in actual_demands) and
                        all(isinstance(x, (int, float)) for x in expected_demands)):
                        if len(actual_demands) == len(expected_demands):
                            errors = [abs(float(a) - float(e)) for a, e in zip(actual_demands, expected_demands)]
                            avg_error = sum(errors) / len(errors)
                            avg_expected = sum(expected_demands) / len(expected_demands)
                            metrics['demand_accuracy'] = max(0, 1 - (avg_error / avg_expected))
                        else:
                            metrics['demand_accuracy'] = 0.3
                    else:
                        metrics['demand_accuracy'] = 0.0
                
                # Completitud
                required_fields = ['num_trucks', 'truck_capacities', 'target_demands']
                present = sum(1 for field in required_fields if field in parsed)
                metrics['completeness'] = present / len(required_fields)
                
        except json.JSONDecodeError:
            metrics['json_validity'] = 0.0
        
        # Puntuación general
        weights = [0.3, 0.25, 0.25, 0.1, 0.1]
        values = [metrics['truck_accuracy'], metrics['capacity_accuracy'], 
                 metrics['demand_accuracy'], metrics['json_validity'], metrics['completeness']]
        metrics['overall_score'] = sum(w * v for w, v in zip(weights, values))
        
        return metrics
    
    def _compile_comparison_report(self, results: List[Dict]) -> Dict[str, Any]:
        """Compila reporte comparativo final"""
        
        # Estrategias evaluadas
        strategies = ['current', 'clarity_enhanced', 'constraint_focused', 
                     'example_driven', 'step_by_step_enhanced', 'validation_focused', 'context_rich']
        
        # Compilar métricas por estrategia
        strategy_performance = {}
        
        for strategy in strategies:
            scores = []
            truck_accuracies = []
            execution_times = []
            
            for result in results:
                if strategy in result['prompt_results'] and 'metrics' in result['prompt_results'][strategy]:
                    metrics = result['prompt_results'][strategy]['metrics']
                    scores.append(metrics['overall_score'])
                    truck_accuracies.append(metrics['truck_accuracy'])
                    execution_times.append(result['prompt_results'][strategy]['execution_time'])
            
            if scores:
                strategy_performance[strategy] = {
                    'avg_overall_score': sum(scores) / len(scores),
                    'avg_truck_accuracy': sum(truck_accuracies) / len(truck_accuracies),
                    'avg_execution_time': sum(execution_times) / len(execution_times),
                    'test_count': len(scores)
                }
        
        # Encontrar mejores estrategias
        best_overall = max(strategy_performance.keys(), 
                          key=lambda s: strategy_performance[s]['avg_overall_score'])
        best_truck_accuracy = max(strategy_performance.keys(),
                                 key=lambda s: strategy_performance[s]['avg_truck_accuracy'])
        fastest = min(strategy_performance.keys(),
                     key=lambda s: strategy_performance[s]['avg_execution_time'])
        
        # Mejoras sobre prompt actual
        if 'current' in strategy_performance:
            current_score = strategy_performance['current']['avg_overall_score']
            improvements = {}
            
            for strategy, perf in strategy_performance.items():
                if strategy != 'current':
                    improvement = ((perf['avg_overall_score'] - current_score) / current_score) * 100
                    improvements[strategy] = improvement
        else:
            improvements = {}
        
        # Recomendaciones
        recommendations = self._generate_comparison_recommendations(
            strategy_performance, improvements, best_overall, best_truck_accuracy, fastest
        )
        
        return {
            'executive_summary': {
                'strategies_compared': len(strategies),
                'test_cases_evaluated': len(results),
                'best_overall_strategy': best_overall,
                'best_truck_accuracy_strategy': best_truck_accuracy,
                'fastest_strategy': fastest,
                'max_improvement_percent': max(improvements.values()) if improvements else 0
            },
            'strategy_performance': strategy_performance,
            'improvements_over_current': improvements,
            'detailed_results': results,
            'recommendations': recommendations,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def _generate_comparison_recommendations(self, performance: Dict, improvements: Dict,
                                           best_overall: str, best_truck_accuracy: str, fastest: str) -> List[str]:
        """Genera recomendaciones específicas para la comparación"""
        
        recommendations = []
        
        if improvements:
            max_improvement = max(improvements.values())
            best_improvement_strategy = max(improvements.keys(), key=lambda s: improvements[s])
            
            recommendations.append(
                f"🚀 MAYOR MEJORA: '{best_improvement_strategy}' supera al prompt actual en {max_improvement:.1f}%"
            )
        
        recommendations.append(
            f"🏆 MEJOR RENDIMIENTO GENERAL: '{best_overall}' con {performance[best_overall]['avg_overall_score']:.3f} puntos"
        )
        
        if best_truck_accuracy != best_overall:
            recommendations.append(
                f"🎯 MAYOR PRECISIÓN EN CAMIONES: '{best_truck_accuracy}' con {performance[best_truck_accuracy]['avg_truck_accuracy']:.3f} de precisión"
            )
        
        recommendations.append(
            f"⚡ MÁS RÁPIDO: '{fastest}' con {performance[fastest]['avg_execution_time']:.2f} segundos promedio"
        )
        
        # Recomendación específica para implementación
        if 'current' in performance and improvements:
            top_improvements = sorted(improvements.items(), key=lambda x: x[1], reverse=True)[:2]
            recommendations.append(
                f"💡 RECOMENDACIÓN: Considere implementar '{top_improvements[0][0]}' como reemplazo del prompt actual"
            )
        
        return recommendations
    
    def save_comparison_report(self, filename: str = None) -> str:
        """Guarda el reporte de comparación"""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"prompt_comparison_report_{timestamp}.json"
        
        # Crear directorio si no existe
        results_dir = Path(__file__).parent / "comparison_results"
        results_dir.mkdir(exist_ok=True)
        
        # Ejecutar análisis si no se ha hecho
        if not hasattr(self, '_comparison_report'):
            self._comparison_report = self.run_comparison_analysis()
        
        filepath = results_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self._comparison_report, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Reporte de comparación guardado en: {filepath}")
        return str(filepath)
    
    def create_comparison_visualization(self, save_path: str = None) -> str:
        """Crea visualización comparativa"""
        
        if not hasattr(self, '_comparison_report'):
            self._comparison_report = self.run_comparison_analysis()
        
        performance = self._comparison_report['strategy_performance']
        
        if not performance:
            return "No hay datos para visualizar"
        
        # Preparar datos para visualización
        strategies = list(performance.keys())
        overall_scores = [performance[s]['avg_overall_score'] for s in strategies]
        truck_accuracies = [performance[s]['avg_truck_accuracy'] for s in strategies]
        execution_times = [performance[s]['avg_execution_time'] for s in strategies]
        
        # Crear figura
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Comparación de Prompts: Actual vs Optimizados', fontsize=16, fontweight='bold')
        
        # 1. Puntuación general
        bars1 = axes[0, 0].bar(strategies, overall_scores, 
                              color=['red' if s == 'current' else 'skyblue' for s in strategies])
        axes[0, 0].set_title('Puntuación General')
        axes[0, 0].set_ylabel('Puntuación')
        axes[0, 0].tick_params(axis='x', rotation=45)
        axes[0, 0].grid(axis='y', alpha=0.3)
        
        # Destacar el mejor
        max_idx = overall_scores.index(max(overall_scores))
        bars1[max_idx].set_color('gold')
        
        # 2. Precisión de camiones
        bars2 = axes[0, 1].bar(strategies, truck_accuracies,
                              color=['red' if s == 'current' else 'lightgreen' for s in strategies])
        axes[0, 1].set_title('Precisión en Conteo de Camiones')
        axes[0, 1].set_ylabel('Precisión')
        axes[0, 1].tick_params(axis='x', rotation=45)
        axes[0, 1].grid(axis='y', alpha=0.3)
        
        max_idx = truck_accuracies.index(max(truck_accuracies))
        bars2[max_idx].set_color('darkgreen')
        
        # 3. Tiempo de ejecución
        bars3 = axes[1, 0].bar(strategies, execution_times,
                              color=['red' if s == 'current' else 'orange' for s in strategies])
        axes[1, 0].set_title('Tiempo de Ejecución')
        axes[1, 0].set_ylabel('Segundos')
        axes[1, 0].tick_params(axis='x', rotation=45)
        axes[1, 0].grid(axis='y', alpha=0.3)
        
        min_idx = execution_times.index(min(execution_times))
        bars3[min_idx].set_color('purple')
        
        # 4. Mejoras sobre prompt actual
        if 'current' in performance:
            improvements = self._comparison_report['improvements_over_current']
            if improvements:
                imp_strategies = list(improvements.keys())
                imp_values = list(improvements.values())
                
                colors = ['green' if v > 0 else 'red' for v in imp_values]
                axes[1, 1].bar(imp_strategies, imp_values, color=colors)
                axes[1, 1].set_title('Mejora sobre Prompt Actual (%)')
                axes[1, 1].set_ylabel('Mejora (%)')
                axes[1, 1].tick_params(axis='x', rotation=45)
                axes[1, 1].grid(axis='y', alpha=0.3)
                axes[1, 1].axhline(y=0, color='black', linestyle='-', alpha=0.5)
        
        plt.tight_layout()
        
        # Guardar
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = Path(__file__).parent / "comparison_results" / f"prompt_comparison_viz_{timestamp}.png"
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Visualización guardada en: {save_path}")
        return str(save_path)

def main():
    """Función principal para ejecutar comparación de prompts"""
    
    print("🔍 Análisis Comparativo: Prompt Actual vs Optimizados")
    print("=" * 55)
    
    # Crear comparador
    comparator = PromptComparator()
    
    # Ejecutar análisis comparativo
    print("\n⚙️ Ejecutando comparación completa...")
    report = comparator.run_comparison_analysis()
    
    # Mostrar resumen ejecutivo
    print("\n📊 RESUMEN EJECUTIVO")
    print("-" * 25)
    summary = report['executive_summary']
    print(f"Estrategias comparadas: {summary['strategies_compared']}")
    print(f"Casos de prueba: {summary['test_cases_evaluated']}")
    print(f"Mejor estrategia general: {summary['best_overall_strategy']}")
    print(f"Mejor para precisión de camiones: {summary['best_truck_accuracy_strategy']}")
    print(f"Estrategia más rápida: {summary['fastest_strategy']}")
    print(f"Máxima mejora sobre actual: {summary['max_improvement_percent']:.1f}%")
    
    # Mostrar recomendaciones
    print("\n💡 RECOMENDACIONES CLAVE")
    print("-" * 25)
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"{i}. {rec}")
    
    # Guardar resultados
    print("\n💾 Guardando resultados...")
    report_path = comparator.save_comparison_report()
    viz_path = comparator.create_comparison_visualization()
    
    print(f"✅ Reporte: {report_path}")
    print(f"✅ Visualización: {viz_path}")
    
    print("\n🎉 Análisis comparativo completado!")
    
    return report

if __name__ == "__main__":
    comparison_report = main()
