"""
Agente Optimizador de Rutas - Fase 2
Implementa optimización dinámica de rutas con algoritmos avanzados
"""

import asyncio
import heapq
import random
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from enum import Enum
import networkx as nx

from .base_agent import BaseAgent, AgentState, MessageType
from .communication import communication_manager

class OptimizationStrategy(Enum):
    """Estrategias de optimización"""
    MINIMIZE_TIME = "minimize_time"
    MINIMIZE_FUEL = "minimize_fuel"
    BALANCE_LOAD = "balance_load"
    EMERGENCY_PRIORITY = "emergency_priority"
    DYNAMIC_ADAPTATION = "dynamic_adaptation"

class RouteOptimizerAgent(BaseAgent):
    """
    Agente especializado en optimización dinámica de rutas
    """
    
    def __init__(self, agent_id: str, street_graph: nx.Graph, 
                 optimization_area: Tuple[float, float, float]):
        super().__init__(agent_id, "route_optimizer", optimization_area[:2])
        
        self.street_graph = street_graph
        self.optimization_area = optimization_area  # (lat, lon, radius)
        self.current_strategy = OptimizationStrategy.DYNAMIC_ADAPTATION
        
        # Estado del tráfico en tiempo real
        self.real_time_traffic = {}
        self.congestion_prediction = {}
        self.route_cache = {}
        
        # Métricas de optimización
        self.optimization_metrics = {
            "routes_optimized": 0,
            "average_improvement": 0.0,
            "cache_hits": 0,
            "computation_time": 0.0
        }
        
        # Algoritmos disponibles
        self.algorithms = {
            "dijkstra": self._dijkstra_optimization,
            "a_star": self._a_star_optimization,
            "genetic": self._genetic_algorithm_optimization,
            "ant_colony": self._ant_colony_optimization,
            "fuzzy_multi_objective": self._fuzzy_multi_objective_optimization
        }
        
        # Configuración de algoritmos genéticos
        self.genetic_config = {
            "population_size": 50,
            "generations": 100,
            "mutation_rate": 0.1,
            "crossover_rate": 0.8
        }
        
        # Configuración de colonia de hormigas
        self.ant_config = {
            "num_ants": 30,
            "iterations": 50,
            "alpha": 1.0,  # Importancia de feromonas
            "beta": 2.0,   # Importancia de heurística
            "evaporation": 0.5
        }
        
        # Matrices de feromonas para ACO
        self.pheromone_matrix = {}
        self.heuristic_matrix = {}
        
        # Variables aleatorias para optimización estocástica
        self.stochastic_factors = {
            "traffic_variability": 0.2,
            "route_exploration": 0.1,
            "prediction_uncertainty": 0.15
        }

    async def perceive(self, environment_state: Dict[str, Any]) -> Dict[str, Any]:
        """Percibe el estado del tráfico para optimización"""
        perception = {}
        
        try:
            # Actualizar estado de tráfico en tiempo real
            vehicles = environment_state.get("vehicles", {})
            self._update_real_time_traffic(vehicles)
            
            # Obtener datos de congestión
            congestion_data = environment_state.get("congestion", {})
            self._update_congestion_data(congestion_data)
            
            # Calcular métricas de red
            network_metrics = self._calculate_network_metrics()
            
            # Identificar cuellos de botella
            bottlenecks = self._identify_bottlenecks()
            
            # Predicción de tráfico futuro
            traffic_prediction = self._predict_future_traffic()
            
            perception = {
                "real_time_traffic": self.real_time_traffic.copy(),
                "network_metrics": network_metrics,
                "bottlenecks": bottlenecks,
                "traffic_prediction": traffic_prediction,
                "optimization_requests": environment_state.get("route_requests", []),
                "emergency_zones": environment_state.get("emergency_zones", [])
            }
            
        except Exception as e:
            self.logger.error(f"Error en percepción de optimizador: {e}")
            perception = {"real_time_traffic": {}}
        
        return perception

    async def decide(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """Decide optimizaciones de ruta usando algoritmos avanzados"""
        decisions = {}
        
        try:
            optimization_requests = perception.get("optimization_requests", [])
            bottlenecks = perception.get("bottlenecks", [])
            emergency_zones = perception.get("emergency_zones", [])
            
            # Seleccionar estrategia de optimización
            strategy = self._select_optimization_strategy(perception)
            
            # Procesar solicitudes de optimización
            optimized_routes = []
            for request in optimization_requests:
                route = await self._optimize_route(request, strategy, perception)
                if route:
                    optimized_routes.append(route)
            
            # Balanceamiento de carga de tráfico
            load_balancing = self._calculate_load_balancing(bottlenecks)
            
            # Recomendaciones de redistribución
            redistribution_suggestions = self._generate_redistribution_suggestions(
                perception, strategy
            )
            
            decisions = {
                "optimized_routes": optimized_routes,
                "load_balancing": load_balancing,
                "redistribution_suggestions": redistribution_suggestions,
                "strategy_used": strategy.value,
                "update_pheromones": True if strategy == OptimizationStrategy.DYNAMIC_ADAPTATION else False
            }
            
        except Exception as e:
            self.logger.error(f"Error en decisión de optimización: {e}")
            decisions = {"optimized_routes": []}
        
        return decisions

    async def act(self, decision: Dict[str, Any]) -> bool:
        """Ejecuta optimizaciones y envía recomendaciones"""
        try:
            # Enviar rutas optimizadas
            optimized_routes = decision.get("optimized_routes", [])
            for route in optimized_routes:
                await self._send_optimized_route(route)
            
            # Implementar balanceamiento de carga
            load_balancing = decision.get("load_balancing", {})
            if load_balancing:
                await self._implement_load_balancing(load_balancing)
            
            # Enviar sugerencias de redistribución
            redistribution = decision.get("redistribution_suggestions", {})
            if redistribution:
                await self._send_redistribution_suggestions(redistribution)
            
            # Actualizar feromonas si se usa ACO
            if decision.get("update_pheromones", False):
                self._update_pheromone_matrix()
            
            # Actualizar métricas
            self._update_optimization_metrics(decision)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error ejecutando optimización: {e}")
            return False

    def _select_optimization_strategy(self, perception: Dict[str, Any]) -> OptimizationStrategy:
        """Selecciona la estrategia de optimización usando lógica difusa"""
        
        # Factores de entrada
        traffic_density = len(perception.get("real_time_traffic", {}))
        bottleneck_count = len(perception.get("bottlenecks", []))
        emergency_count = len(perception.get("emergency_zones", []))
        
        # Normalizar factores
        density_factor = min(1.0, traffic_density / 50.0)
        bottleneck_factor = min(1.0, bottleneck_count / 10.0)
        emergency_factor = min(1.0, emergency_count / 5.0)
        
        # Lógica difusa para selección de estrategia
        if emergency_factor > 0.5:
            return OptimizationStrategy.EMERGENCY_PRIORITY
        elif bottleneck_factor > 0.7:
            return OptimizationStrategy.BALANCE_LOAD
        elif density_factor > 0.8:
            return OptimizationStrategy.MINIMIZE_TIME
        else:
            return OptimizationStrategy.DYNAMIC_ADAPTATION

    async def _optimize_route(self, request: Dict, strategy: OptimizationStrategy, 
                            perception: Dict) -> Optional[Dict]:
        """Optimiza una ruta específica"""
        start_node = request.get("start")
        end_node = request.get("end")
        vehicle_id = request.get("vehicle_id")
        constraints = request.get("constraints", {})
        
        if not start_node or not end_node:
            return None
        
        # Verificar cache
        cache_key = f"{start_node}_{end_node}_{strategy.value}"
        if cache_key in self.route_cache:
            cache_entry = self.route_cache[cache_key]
            if (datetime.now() - cache_entry["timestamp"]).seconds < 300:  # 5 minutos
                self.optimization_metrics["cache_hits"] += 1
                return cache_entry["route"]
        
        # Seleccionar algoritmo según estrategia
        algorithm = self._select_algorithm(strategy, constraints)
        
        # Ejecutar optimización
        start_time = datetime.now()
        optimized_route = await algorithm(start_node, end_node, constraints, perception)
        computation_time = (datetime.now() - start_time).total_seconds()
        
        if optimized_route:
            # Calcular mejora respecto a ruta básica
            basic_route = self._calculate_basic_route(start_node, end_node)
            improvement = self._calculate_improvement(basic_route, optimized_route)
            
            route_result = {
                "vehicle_id": vehicle_id,
                "start": start_node,
                "end": end_node,
                "route": optimized_route["path"],
                "estimated_time": optimized_route["time"],
                "estimated_distance": optimized_route["distance"],
                "improvement_percentage": improvement,
                "algorithm_used": algorithm.__name__,
                "computation_time": computation_time,
                "strategy": strategy.value
            }
            
            # Guardar en cache
            self.route_cache[cache_key] = {
                "route": route_result,
                "timestamp": datetime.now()
            }
            
            return route_result
        
        return None

    def _select_algorithm(self, strategy: OptimizationStrategy, constraints: Dict) -> callable:
        """Selecciona el algoritmo apropiado"""
        if strategy == OptimizationStrategy.MINIMIZE_TIME:
            return self.algorithms["dijkstra"]
        elif strategy == OptimizationStrategy.BALANCE_LOAD:
            return self.algorithms["genetic"]
        elif strategy == OptimizationStrategy.EMERGENCY_PRIORITY:
            return self.algorithms["a_star"]
        elif strategy == OptimizationStrategy.DYNAMIC_ADAPTATION:
            return self.algorithms["ant_colony"]
        else:
            return self.algorithms["fuzzy_multi_objective"]

    async def _dijkstra_optimization(self, start: Any, end: Any, constraints: Dict, 
                                   perception: Dict) -> Optional[Dict]:
        """Optimización usando algoritmo de Dijkstra modificado"""
        try:
            # Crear grafo con pesos dinámicos
            weighted_graph = self._create_weighted_graph(perception)
            
            # Aplicar Dijkstra
            path = nx.dijkstra_path(weighted_graph, start, end, weight='dynamic_weight')
            distance = nx.dijkstra_path_length(weighted_graph, start, end, weight='dynamic_weight')
            
            # Estimar tiempo considerando tráfico
            estimated_time = self._estimate_travel_time(path, perception)
            
            return {
                "path": path,
                "distance": distance,
                "time": estimated_time,
                "confidence": 0.9
            }
            
        except Exception as e:
            self.logger.error(f"Error en Dijkstra: {e}")
            return None

    async def _a_star_optimization(self, start: Any, end: Any, constraints: Dict, 
                                 perception: Dict) -> Optional[Dict]:
        """Optimización usando A* con heurística dinámica"""
        try:
            # Implementación simplificada de A*
            weighted_graph = self._create_weighted_graph(perception)
            
            def heuristic(node1, node2):
                # Heurística euclidiana con factor de tráfico
                if node1 in weighted_graph.nodes and node2 in weighted_graph.nodes:
                    pos1 = (weighted_graph.nodes[node1].get('lat', 0), 
                           weighted_graph.nodes[node1].get('lon', 0))
                    pos2 = (weighted_graph.nodes[node2].get('lat', 0), 
                           weighted_graph.nodes[node2].get('lon', 0))
                    
                    euclidean_dist = ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)**0.5
                    traffic_factor = self.real_time_traffic.get(f"{node1}_{node2}", 1.0)
                    return euclidean_dist * traffic_factor
                return 0
            
            path = nx.astar_path(weighted_graph, start, end, heuristic=heuristic, weight='dynamic_weight')
            distance = nx.astar_path_length(weighted_graph, start, end, heuristic=heuristic, weight='dynamic_weight')
            
            estimated_time = self._estimate_travel_time(path, perception)
            
            return {
                "path": path,
                "distance": distance,
                "time": estimated_time,
                "confidence": 0.85
            }
            
        except Exception as e:
            self.logger.error(f"Error en A*: {e}")
            return None

    async def _genetic_algorithm_optimization(self, start: Any, end: Any, constraints: Dict, 
                                            perception: Dict) -> Optional[Dict]:
        """Optimización usando algoritmo genético"""
        try:
            # Generar población inicial de rutas
            population = self._generate_initial_population(start, end, self.genetic_config["population_size"])
            
            best_route = None
            best_fitness = float('inf')
            
            for generation in range(self.genetic_config["generations"]):
                # Evaluar fitness de cada individuo
                fitness_scores = []
                for individual in population:
                    fitness = self._evaluate_route_fitness(individual, perception)
                    fitness_scores.append(fitness)
                    
                    if fitness < best_fitness:
                        best_fitness = fitness
                        best_route = individual.copy()
                
                # Selección, cruce y mutación
                new_population = []
                
                # Elitismo: mantener los mejores
                sorted_indices = sorted(range(len(fitness_scores)), key=lambda i: fitness_scores[i])
                elite_size = max(1, self.genetic_config["population_size"] // 10)
                
                for i in range(elite_size):
                    new_population.append(population[sorted_indices[i]].copy())
                
                # Generar nueva población
                while len(new_population) < self.genetic_config["population_size"]:
                    # Selección por torneo
                    parent1 = self._tournament_selection(population, fitness_scores)
                    parent2 = self._tournament_selection(population, fitness_scores)
                    
                    # Cruce
                    if random.random() < self.genetic_config["crossover_rate"]:
                        child = self._crossover_routes(parent1, parent2)
                    else:
                        child = parent1.copy()
                    
                    # Mutación
                    if random.random() < self.genetic_config["mutation_rate"]:
                        child = self._mutate_route(child)
                    
                    new_population.append(child)
                
                population = new_population
            
            if best_route:
                distance = self._calculate_route_distance(best_route)
                estimated_time = self._estimate_travel_time(best_route, perception)
                
                return {
                    "path": best_route,
                    "distance": distance,
                    "time": estimated_time,
                    "confidence": 0.8
                }
            
        except Exception as e:
            self.logger.error(f"Error en algoritmo genético: {e}")
        
        return None

    async def _ant_colony_optimization(self, start: Any, end: Any, constraints: Dict, 
                                     perception: Dict) -> Optional[Dict]:
        """Optimización usando colonia de hormigas"""
        try:
            # Inicializar matrices si no existen
            if not self.pheromone_matrix:
                self._initialize_pheromone_matrix()
            
            best_route = None
            best_distance = float('inf')
            
            for iteration in range(self.ant_config["iterations"]):
                iteration_routes = []
                
                # Cada hormiga construye una ruta
                for ant in range(self.ant_config["num_ants"]):
                    route = self._construct_ant_route(start, end, perception)
                    if route:
                        iteration_routes.append(route)
                        distance = self._calculate_route_distance(route)
                        
                        if distance < best_distance:
                            best_distance = distance
                            best_route = route.copy()
                
                # Actualizar feromonas
                self._update_pheromones_aco(iteration_routes)
                
                # Evaporación
                self._evaporate_pheromones()
            
            if best_route:
                estimated_time = self._estimate_travel_time(best_route, perception)
                
                return {
                    "path": best_route,
                    "distance": best_distance,
                    "time": estimated_time,
                    "confidence": 0.75
                }
            
        except Exception as e:
            self.logger.error(f"Error en colonia de hormigas: {e}")
        
        return None

    async def _fuzzy_multi_objective_optimization(self, start: Any, end: Any, constraints: Dict, 
                                                perception: Dict) -> Optional[Dict]:
        """Optimización multi-objetivo con lógica difusa"""
        try:
            # Generar varias rutas candidatas usando diferentes criterios
            candidate_routes = []
            
            # Ruta por tiempo mínimo
            time_route = await self._dijkstra_optimization(start, end, constraints, perception)
            if time_route:
                candidate_routes.append(("time", time_route))
            
            # Ruta por distancia mínima
            distance_graph = self._create_distance_weighted_graph()
            try:
                path = nx.dijkstra_path(distance_graph, start, end, weight='distance')
                distance_route = {
                    "path": path,
                    "distance": nx.dijkstra_path_length(distance_graph, start, end, weight='distance'),
                    "time": self._estimate_travel_time(path, perception),
                    "confidence": 0.8
                }
                candidate_routes.append(("distance", distance_route))
            except:
                pass
            
            # Ruta balanceada
            if len(candidate_routes) >= 2:
                balanced_route = self._create_balanced_route(candidate_routes, constraints)
                if balanced_route:
                    candidate_routes.append(("balanced", balanced_route))
            
            # Evaluación difusa de las rutas
            if candidate_routes:
                best_route = self._fuzzy_route_evaluation(candidate_routes, constraints, perception)
                return best_route
            
        except Exception as e:
            self.logger.error(f"Error en optimización multi-objetivo: {e}")
        
        return None

    def _fuzzy_route_evaluation(self, candidate_routes: List, constraints: Dict, 
                               perception: Dict) -> Optional[Dict]:
        """Evaluación difusa de rutas candidatas"""
        best_score = 0
        best_route = None
        
        for route_type, route in candidate_routes:
            # Normalizar métricas
            time_score = self._normalize_time_score(route["time"])
            distance_score = self._normalize_distance_score(route["distance"])
            traffic_score = self._evaluate_traffic_score(route["path"], perception)
            safety_score = self._evaluate_safety_score(route["path"], perception)
            
            # Pesos difusos según contexto
            emergency_factor = len(perception.get("emergency_zones", [])) / 5.0
            congestion_factor = len(perception.get("bottlenecks", [])) / 10.0
            
            # Ajustar pesos según contexto
            time_weight = 0.4 + emergency_factor * 0.2
            distance_weight = 0.2
            traffic_weight = 0.2 + congestion_factor * 0.2
            safety_weight = 0.2 + emergency_factor * 0.1
            
            # Normalizar pesos
            total_weight = time_weight + distance_weight + traffic_weight + safety_weight
            time_weight /= total_weight
            distance_weight /= total_weight
            traffic_weight /= total_weight
            safety_weight /= total_weight
            
            # Calcular puntuación total
            total_score = (
                time_score * time_weight +
                distance_score * distance_weight +
                traffic_score * traffic_weight +
                safety_score * safety_weight
            )
            
            if total_score > best_score:
                best_score = total_score
                best_route = route
        
        return best_route

    # Métodos auxiliares para optimización
    def _create_weighted_graph(self, perception: Dict) -> nx.Graph:
        """Crea grafo con pesos dinámicos"""
        weighted_graph = self.street_graph.copy()
        
        for edge in weighted_graph.edges():
            # Peso base (distancia)
            base_weight = weighted_graph[edge[0]][edge[1]].get('weight', 1.0)
            
            # Factor de tráfico
            traffic_key = f"{edge[0]}_{edge[1]}"
            traffic_factor = self.real_time_traffic.get(traffic_key, 1.0)
            
            # Agregar variabilidad estocástica
            stochastic_factor = 1 + np.random.normal(0, self.stochastic_factors["traffic_variability"])
            stochastic_factor = max(0.5, min(2.0, stochastic_factor))
            
            # Peso dinámico final
            dynamic_weight = base_weight * traffic_factor * stochastic_factor
            weighted_graph[edge[0]][edge[1]]['dynamic_weight'] = dynamic_weight
        
        return weighted_graph

    def _update_real_time_traffic(self, vehicles: Dict):
        """Actualiza estado de tráfico en tiempo real"""
        # Reset traffic data
        for edge in self.street_graph.edges():
            edge_key = f"{edge[0]}_{edge[1]}"
            self.real_time_traffic[edge_key] = 1.0
        
        # Contar vehículos por arista
        vehicle_counts = {}
        for vehicle_id, vehicle_data in vehicles.items():
            # Simplificación: asignar vehículo a arista más cercana
            vehicle_pos = (vehicle_data.get("lat", 0), vehicle_data.get("lon", 0))
            
            closest_edge = None
            min_distance = float('inf')
            
            for edge in self.street_graph.edges():
                node1_pos = (self.street_graph.nodes[edge[0]].get('lat', 0), 
                           self.street_graph.nodes[edge[0]].get('lon', 0))
                node2_pos = (self.street_graph.nodes[edge[1]].get('lat', 0), 
                           self.street_graph.nodes[edge[1]].get('lon', 0))
                
                # Distancia del vehículo al centro de la arista
                edge_center = ((node1_pos[0] + node2_pos[0]) / 2, 
                             (node1_pos[1] + node2_pos[1]) / 2)
                distance = ((vehicle_pos[0] - edge_center[0])**2 + 
                          (vehicle_pos[1] - edge_center[1])**2)**0.5
                
                if distance < min_distance:
                    min_distance = distance
                    closest_edge = edge
            
            if closest_edge and min_distance < 0.001:  # Dentro del rango
                edge_key = f"{closest_edge[0]}_{closest_edge[1]}"
                vehicle_counts[edge_key] = vehicle_counts.get(edge_key, 0) + 1
        
        # Calcular factores de congestión
        for edge_key, count in vehicle_counts.items():
            # Factor de congestión basado en capacidad de la arista
            capacity = 10  # Capacidad base por arista
            congestion_factor = 1 + (count / capacity) * 2  # Factor de ralentización
            self.real_time_traffic[edge_key] = min(5.0, congestion_factor)

    def _calculate_network_metrics(self) -> Dict[str, float]:
        """Calcula métricas de la red de tráfico"""
        metrics = {}
        
        # Densidad promedio de tráfico
        traffic_values = list(self.real_time_traffic.values())
        metrics["average_traffic_density"] = sum(traffic_values) / len(traffic_values) if traffic_values else 1.0
        
        # Conectividad de la red
        metrics["network_connectivity"] = nx.node_connectivity(self.street_graph)
        
        # Centralidad promedio
        betweenness = nx.betweenness_centrality(self.street_graph)
        metrics["average_centrality"] = sum(betweenness.values()) / len(betweenness) if betweenness else 0
        
        return metrics

    def _identify_bottlenecks(self) -> List[Dict]:
        """Identifica cuellos de botella en la red"""
        bottlenecks = []
        
        # Umbral para considerar una arista como cuello de botella
        bottleneck_threshold = 3.0
        
        for edge_key, traffic_factor in self.real_time_traffic.items():
            if traffic_factor > bottleneck_threshold:
                edge_parts = edge_key.split('_')
                if len(edge_parts) == 2:
                    node1, node2 = edge_parts[0], edge_parts[1]
                    
                    bottlenecks.append({
                        "edge": (node1, node2),
                        "congestion_level": traffic_factor,
                        "severity": "high" if traffic_factor > 4.0 else "medium"
                    })
        
        return bottlenecks

    def _predict_future_traffic(self) -> Dict[str, float]:
        """Predice el tráfico futuro usando modelos estocásticos"""
        prediction = {}
        
        for edge_key, current_traffic in self.real_time_traffic.items():
            # Modelo simple de predicción con componente estocástica
            trend = np.random.normal(0, 0.1)  # Tendencia aleatoria
            seasonal = np.sin(datetime.now().hour * np.pi / 12) * 0.2  # Patrón diario
            noise = np.random.normal(0, self.stochastic_factors["prediction_uncertainty"])
            
            predicted_traffic = current_traffic * (1 + trend + seasonal + noise)
            predicted_traffic = max(0.5, min(5.0, predicted_traffic))
            
            prediction[edge_key] = predicted_traffic
        
        return prediction

    # Métodos auxiliares para algoritmos específicos
    def _generate_initial_population(self, start: Any, end: Any, population_size: int) -> List[List]:
        """Genera población inicial para algoritmo genético"""
        population = []
        
        for _ in range(population_size):
            try:
                # Generar ruta aleatoria con exploración estocástica
                route = self._generate_random_route(start, end)
                if route:
                    population.append(route)
            except:
                # Si falla, usar ruta básica con mutación
                basic_route = self._calculate_basic_route(start, end)
                if basic_route:
                    mutated_route = self._mutate_route(basic_route)
                    population.append(mutated_route)
        
        # Asegurar que tenemos suficientes individuos
        while len(population) < population_size:
            basic_route = self._calculate_basic_route(start, end)
            if basic_route:
                population.append(basic_route)
        
        return population[:population_size]

    def _generate_random_route(self, start: Any, end: Any) -> Optional[List]:
        """Genera una ruta aleatoria con exploración estocástica"""
        try:
            current = start
            route = [start]
            visited = {start}
            max_steps = len(self.street_graph.nodes()) * 2
            
            for _ in range(max_steps):
                if current == end:
                    break
                
                # Obtener vecinos
                neighbors = list(self.street_graph.neighbors(current))
                unvisited_neighbors = [n for n in neighbors if n not in visited]
                
                if not unvisited_neighbors:
                    # Si no hay vecinos sin visitar, permitir retroceso ocasional
                    if random.random() < 0.3:
                        unvisited_neighbors = neighbors
                
                if not unvisited_neighbors:
                    break
                
                # Selección estocástica del siguiente nodo
                if end in unvisited_neighbors and random.random() < 0.7:
                    # Probabilidad alta de ir directamente al destino
                    next_node = end
                else:
                    # Selección con bias hacia el destino
                    weights = []
                    for neighbor in unvisited_neighbors:
                        if neighbor in self.street_graph.nodes and end in self.street_graph.nodes:
                            # Calcular distancia al destino
                            neighbor_pos = (self.street_graph.nodes[neighbor].get('lat', 0),
                                          self.street_graph.nodes[neighbor].get('lon', 0))
                            end_pos = (self.street_graph.nodes[end].get('lat', 0),
                                     self.street_graph.nodes[end].get('lon', 0))
                            
                            distance_to_end = ((neighbor_pos[0] - end_pos[0])**2 + 
                                             (neighbor_pos[1] - end_pos[1])**2)**0.5
                            
                            # Peso inversamente proporcional a la distancia
                            weight = 1.0 / (distance_to_end + 0.001)
                            weights.append(weight)
                        else:
                            weights.append(1.0)
                    
                    # Agregar factor de exploración estocástica
                    exploration_factor = self.stochastic_factors["route_exploration"]
                    weights = [w * (1 + np.random.normal(0, exploration_factor)) for w in weights]
                    
                    # Seleccionar según pesos
                    total_weight = sum(weights)
                    if total_weight > 0:
                        weights = [w / total_weight for w in weights]
                        next_node = np.random.choice(unvisited_neighbors, p=weights)
                    else:
                        next_node = random.choice(unvisited_neighbors)
                
                route.append(next_node)
                visited.add(next_node)
                current = next_node
            
            return route if current == end else None
            
        except Exception as e:
            self.logger.error(f"Error generando ruta aleatoria: {e}")
            return None

    def _calculate_basic_route(self, start: Any, end: Any) -> Optional[List]:
        """Calcula ruta básica usando camino más corto"""
        try:
            return nx.shortest_path(self.street_graph, start, end)
        except:
            return None

    def _evaluate_route_fitness(self, route: List, perception: Dict) -> float:
        """Evalúa el fitness de una ruta (menor es mejor)"""
        if len(route) < 2:
            return float('inf')
        
        total_cost = 0
        
        for i in range(len(route) - 1):
            edge_key = f"{route[i]}_{route[i+1]}"
            
            # Costo base (distancia)
            base_cost = 1.0
            if self.street_graph.has_edge(route[i], route[i+1]):
                base_cost = self.street_graph[route[i]][route[i+1]].get('weight', 1.0)
            
            # Factor de tráfico
            traffic_factor = self.real_time_traffic.get(edge_key, 1.0)
            
            # Penalización por congestión
            congestion_penalty = max(0, traffic_factor - 2.0) * 2
            
            total_cost += base_cost * traffic_factor + congestion_penalty
        
        # Penalización por longitud excesiva
        length_penalty = max(0, len(route) - 10) * 0.5
        
        return total_cost + length_penalty

    def _tournament_selection(self, population: List, fitness_scores: List) -> List:
        """Selección por torneo para algoritmo genético"""
        tournament_size = 3
        tournament_indices = random.sample(range(len(population)), 
                                         min(tournament_size, len(population)))
        
        best_index = min(tournament_indices, key=lambda i: fitness_scores[i])
        return population[best_index].copy()

    def _crossover_routes(self, parent1: List, parent2: List) -> List:
        """Cruce de rutas para algoritmo genético"""
        if len(parent1) < 3 or len(parent2) < 3:
            return parent1.copy()
        
        # Encontrar nodos comunes (excluyendo inicio y fin)
        common_nodes = set(parent1[1:-1]) & set(parent2[1:-1])
        
        if common_nodes:
            # Seleccionar punto de cruce aleatorio
            crossover_node = random.choice(list(common_nodes))
            
            # Encontrar posiciones del nodo en ambos padres
            pos1 = parent1.index(crossover_node)
            pos2 = parent2.index(crossover_node)
            
            # Crear hijo combinando segmentos
            child = parent1[:pos1] + parent2[pos2:]
            
            # Verificar validez del camino
            if self._is_valid_route(child):
                return child
        
        # Si no se puede hacer cruce válido, devolver padre 1
        return parent1.copy()

    def _mutate_route(self, route: List) -> List:
        """Mutación de ruta para algoritmo genético"""
        if len(route) < 3:
            return route
        
        mutated_route = route.copy()
        
        # Seleccionar nodo interno aleatorio para mutar
        internal_indices = list(range(1, len(route) - 1))
        if not internal_indices:
            return mutated_route
        
        mutation_index = random.choice(internal_indices)
        current_node = mutated_route[mutation_index]
        
        # Obtener vecinos del nodo anterior
        prev_node = mutated_route[mutation_index - 1]
        neighbors = list(self.street_graph.neighbors(prev_node))
        
        # Filtrar vecinos válidos (que puedan conectar con el siguiente nodo)
        next_node = mutated_route[mutation_index + 1]
        valid_neighbors = []
        
        for neighbor in neighbors:
            if (neighbor != current_node and 
                self.street_graph.has_edge(neighbor, next_node)):
                valid_neighbors.append(neighbor)
        
        if valid_neighbors:
            # Seleccionar nuevo nodo con sesgo estocástico
            if random.random() < 0.7:  # 70% probabilidad de selección inteligente
                # Seleccionar el vecino más cercano al destino
                end_node = route[-1]
                if end_node in self.street_graph.nodes:
                    end_pos = (self.street_graph.nodes[end_node].get('lat', 0),
                             self.street_graph.nodes[end_node].get('lon', 0))
                    
                    best_neighbor = min(valid_neighbors, key=lambda n: (
                        (self.street_graph.nodes[n].get('lat', 0) - end_pos[0])**2 +
                        (self.street_graph.nodes[n].get('lon', 0) - end_pos[1])**2
                    ) if n in self.street_graph.nodes else float('inf'))
                    
                    mutated_route[mutation_index] = best_neighbor
                else:
                    mutated_route[mutation_index] = random.choice(valid_neighbors)
            else:  # 30% probabilidad de selección completamente aleatoria
                mutated_route[mutation_index] = random.choice(valid_neighbors)
        
        return mutated_route

    def _is_valid_route(self, route: List) -> bool:
        """Verifica si una ruta es válida"""
        if len(route) < 2:
            return False
        
        for i in range(len(route) - 1):
            if not self.street_graph.has_edge(route[i], route[i+1]):
                return False
        
        return True

    def _initialize_pheromone_matrix(self):
        """Inicializa matriz de feromonas para ACO"""
        initial_pheromone = 1.0
        
        for edge in self.street_graph.edges():
            edge_key = f"{edge[0]}_{edge[1]}"
            self.pheromone_matrix[edge_key] = initial_pheromone
            
            # Heurística inicial (inverso de la distancia)
            distance = self.street_graph[edge[0]][edge[1]].get('weight', 1.0)
            self.heuristic_matrix[edge_key] = 1.0 / (distance + 0.001)

    def _construct_ant_route(self, start: Any, end: Any, perception: Dict) -> Optional[List]:
        """Construye ruta para una hormiga en ACO"""
        try:
            current = start
            route = [start]
            visited = {start}
            
            while current != end and len(route) < 50:  # Límite de pasos
                neighbors = [n for n in self.street_graph.neighbors(current) if n not in visited]
                
                if not neighbors:
                    break
                
                # Calcular probabilidades basadas en feromonas y heurística
                probabilities = []
                for neighbor in neighbors:
                    edge_key = f"{current}_{neighbor}"
                    
                    pheromone = self.pheromone_matrix.get(edge_key, 1.0)
                    heuristic = self.heuristic_matrix.get(edge_key, 1.0)
                    
                    # Aplicar factores de tráfico
                    traffic_factor = self.real_time_traffic.get(edge_key, 1.0)
                    adjusted_heuristic = heuristic / traffic_factor
                    
                    probability = (pheromone ** self.ant_config["alpha"]) * \
                                (adjusted_heuristic ** self.ant_config["beta"])
                    probabilities.append(probability)
                
                # Selección estocástica
                if sum(probabilities) > 0:
                    probabilities = [p / sum(probabilities) for p in probabilities]
                    next_node = np.random.choice(neighbors, p=probabilities)
                else:
                    next_node = random.choice(neighbors)
                
                route.append(next_node)
                visited.add(next_node)
                current = next_node
            
            return route if current == end else None
            
        except Exception as e:
            self.logger.error(f"Error construyendo ruta de hormiga: {e}")
            return None

    def _update_pheromones_aco(self, routes: List[List]):
        """Actualiza feromonas después de iteración ACO"""
        for route in routes:
            if len(route) < 2:
                continue
            
            # Calcular calidad de la ruta (inverso del costo)
            route_cost = self._calculate_route_distance(route)
            pheromone_deposit = 1.0 / (route_cost + 0.001)
            
            # Depositar feromonas en las aristas de la ruta
            for i in range(len(route) - 1):
                edge_key = f"{route[i]}_{route[i+1]}"
                if edge_key in self.pheromone_matrix:
                    self.pheromone_matrix[edge_key] += pheromone_deposit

    def _evaporate_pheromones(self):
        """Aplica evaporación de feromonas"""
        evaporation_rate = self.ant_config["evaporation"]
        
        for edge_key in self.pheromone_matrix:
            self.pheromone_matrix[edge_key] *= (1 - evaporation_rate)
            # Mantener un mínimo de feromona
            self.pheromone_matrix[edge_key] = max(0.01, self.pheromone_matrix[edge_key])

    def _update_pheromone_matrix(self):
        """Actualiza matriz de feromonas global"""
        # Aplicar decay global
        decay_factor = 0.95
        for edge_key in self.pheromone_matrix:
            self.pheromone_matrix[edge_key] *= decay_factor

    def _calculate_route_distance(self, route: List) -> float:
        """Calcula distancia total de una ruta"""
        if len(route) < 2:
            return float('inf')
        
        total_distance = 0
        for i in range(len(route) - 1):
            if self.street_graph.has_edge(route[i], route[i+1]):
                distance = self.street_graph[route[i]][route[i+1]].get('weight', 1.0)
                total_distance += distance
            else:
                return float('inf')  # Ruta inválida
        
        return total_distance

    def _estimate_travel_time(self, route: List, perception: Dict) -> float:
        """Estima tiempo de viaje considerando tráfico"""
        if len(route) < 2:
            return 0
        
        total_time = 0
        base_speed = 50  # km/h base
        
        for i in range(len(route) - 1):
            edge_key = f"{route[i]}_{route[i+1]}"
            
            # Distancia de la arista
            distance = 1.0  # km (simplificado)
            if self.street_graph.has_edge(route[i], route[i+1]):
                distance = self.street_graph[route[i]][route[i+1]].get('weight', 1.0)
            
            # Factor de tráfico
            traffic_factor = self.real_time_traffic.get(edge_key, 1.0)
            effective_speed = base_speed / traffic_factor
            
            # Tiempo en horas
            time = distance / effective_speed
            total_time += time
        
        return total_time * 60  # Convertir a minutos

    def _calculate_improvement(self, basic_route: Optional[List], optimized_route: Dict) -> float:
        """Calcula mejora porcentual respecto a ruta básica"""
        if not basic_route:
            return 0.0
        
        basic_time = self._estimate_travel_time(basic_route, {})
        optimized_time = optimized_route.get("time", basic_time)
        
        if basic_time > 0:
            improvement = ((basic_time - optimized_time) / basic_time) * 100
            return max(0, improvement)
        
        return 0.0

    def _create_distance_weighted_graph(self) -> nx.Graph:
        """Crea grafo con pesos de distancia únicamente"""
        distance_graph = self.street_graph.copy()
        
        for edge in distance_graph.edges():
            distance = distance_graph[edge[0]][edge[1]].get('weight', 1.0)
            distance_graph[edge[0]][edge[1]]['distance'] = distance
        
        return distance_graph

    def _create_balanced_route(self, candidate_routes: List, constraints: Dict) -> Optional[Dict]:
        """Crea ruta balanceada combinando criterios"""
        if len(candidate_routes) < 2:
            return None
        
        # Promediar métricas de las rutas candidatas
        total_time = sum(route[1]["time"] for route in candidate_routes)
        total_distance = sum(route[1]["distance"] for route in candidate_routes)
        
        avg_time = total_time / len(candidate_routes)
        avg_distance = total_distance / len(candidate_routes)
        
        # Seleccionar la ruta más cercana a los promedios
        best_route = None
        best_score = float('inf')
        
        for route_type, route in candidate_routes:
            time_diff = abs(route["time"] - avg_time)
            distance_diff = abs(route["distance"] - avg_distance)
            
            # Puntuación compuesta (menor es mejor)
            score = time_diff + distance_diff
            
            if score < best_score:
                best_score = score
                best_route = route
        
        return best_route

    def _normalize_time_score(self, time: float) -> float:
        """Normaliza puntuación de tiempo (0-1, mayor es mejor)"""
        max_time = 120  # minutos
        return max(0, 1 - (time / max_time))

    def _normalize_distance_score(self, distance: float) -> float:
        """Normaliza puntuación de distancia (0-1, mayor es mejor)"""
        max_distance = 50  # km
        return max(0, 1 - (distance / max_distance))

    def _evaluate_traffic_score(self, route: List, perception: Dict) -> float:
        """Evalúa puntuación de tráfico (0-1, mayor es mejor)"""
        if len(route) < 2:
            return 0
        
        total_traffic = 0
        for i in range(len(route) - 1):
            edge_key = f"{route[i]}_{route[i+1]}"
            traffic_factor = self.real_time_traffic.get(edge_key, 1.0)
            total_traffic += traffic_factor
        
        avg_traffic = total_traffic / (len(route) - 1)
        max_traffic = 5.0
        
        return max(0, 1 - (avg_traffic / max_traffic))

    def _evaluate_safety_score(self, route: List, perception: Dict) -> float:
        """Evalúa puntuación de seguridad (0-1, mayor es mejor)"""
        safety_score = 1.0
        emergency_zones = perception.get("emergency_zones", [])
        
        # Penalizar rutas que pasan cerca de zonas de emergencia
        for emergency in emergency_zones:
            emergency_pos = emergency.get("position", (0, 0))
            
            for node in route:
                if node in self.street_graph.nodes:
                    node_pos = (self.street_graph.nodes[node].get('lat', 0),
                               self.street_graph.nodes[node].get('lon', 0))
                    
                    distance = ((node_pos[0] - emergency_pos[0])**2 + 
                               (node_pos[1] - emergency_pos[1])**2)**0.5
                    
                    if distance < 0.005:  # Cerca de zona de emergencia
                        safety_score *= 0.8
        
        return max(0, safety_score)

    # Métodos para envío de resultados
    async def _send_optimized_route(self, route: Dict):
        """Envía ruta optimizada al vehículo solicitante"""
        message = {
            "optimized_route": route
        }
        
        vehicle_id = route.get("vehicle_id")
        if vehicle_id:
            await communication_manager.send_message(
                self.agent_id,
                vehicle_id,
                MessageType.RESPONSE,
                message
            )

    async def _implement_load_balancing(self, load_balancing: Dict):
        """Implementa estrategias de balanceamiento de carga"""
        message = {
            "load_balancing_update": load_balancing
        }
        
        await communication_manager.send_to_topic(
            "traffic",
            self.agent_id,
            MessageType.NOTIFICATION,
            message
        )

    async def _send_redistribution_suggestions(self, redistribution: Dict):
        """Envía sugerencias de redistribución de tráfico"""
        message = {
            "traffic_redistribution": redistribution
        }
        
        await communication_manager.send_to_topic(
            "route",
            self.agent_id,
            MessageType.NOTIFICATION,
            message
        )

    def _calculate_load_balancing(self, bottlenecks: List) -> Dict[str, Any]:
        """Calcula estrategias de balanceamiento de carga"""
        balancing = {}
        
        if bottlenecks:
            # Identificar rutas alternativas para cuellos de botella
            alternative_routes = {}
            
            for bottleneck in bottlenecks:
                edge = bottleneck["edge"]
                try:
                    # Crear grafo temporal sin la arista congestionada
                    temp_graph = self.street_graph.copy()
                    temp_graph.remove_edge(edge[0], edge[1])
                    
                    # Buscar ruta alternativa
                    if nx.has_path(temp_graph, edge[0], edge[1]):
                        alt_path = nx.shortest_path(temp_graph, edge[0], edge[1])
                        alternative_routes[f"{edge[0]}_{edge[1]}"] = alt_path
                except:
                    pass
            
            balancing = {
                "bottlenecks": bottlenecks,
                "alternative_routes": alternative_routes,
                "redistribution_factor": 0.3  # 30% del tráfico a rutas alternativas
            }
        
        return balancing

    def _generate_redistribution_suggestions(self, perception: Dict, 
                                           strategy: OptimizationStrategy) -> Dict[str, Any]:
        """Genera sugerencias de redistribución de tráfico"""
        suggestions = {}
        
        network_metrics = perception.get("network_metrics", {})
        avg_density = network_metrics.get("average_traffic_density", 1.0)
        
        if avg_density > 2.0:  # Alta densidad general
            suggestions = {
                "reduce_new_vehicle_spawning": True,
                "encourage_alternative_routes": True,
                "suggest_departure_time_shifts": True,
                "priority_emergency_vehicles": True
            }
            
            if strategy == OptimizationStrategy.EMERGENCY_PRIORITY:
                suggestions["clear_emergency_corridors"] = True
        
        return suggestions

    def _update_optimization_metrics(self, decision: Dict):
        """Actualiza métricas de optimización"""
        optimized_routes = decision.get("optimized_routes", [])
        
        self.optimization_metrics["routes_optimized"] += len(optimized_routes)
        
        if optimized_routes:
            improvements = [route.get("improvement_percentage", 0) for route in optimized_routes]
            comp_times = [route.get("computation_time", 0) for route in optimized_routes]
            
            # Actualizar promedios
            total_routes = self.optimization_metrics["routes_optimized"]
            if total_routes > 0:
                self.optimization_metrics["average_improvement"] = (
                    (self.optimization_metrics["average_improvement"] * (total_routes - len(optimized_routes)) +
                     sum(improvements)) / total_routes
                )
                
                self.optimization_metrics["computation_time"] = (
                    (self.optimization_metrics["computation_time"] * (total_routes - len(optimized_routes)) +
                     sum(comp_times)) / total_routes
                )

    def _update_congestion_data(self, congestion_data: Dict):
        """Actualiza datos de congestión"""
        for edge_key, congestion_level in congestion_data.items():
            self.real_time_traffic[edge_key] = max(1.0, congestion_level)

    def get_optimizer_metrics(self) -> Dict[str, Any]:
        """Retorna métricas del optimizador"""
        base_metrics = self.get_metrics()
        return {
            **base_metrics,
            "optimization_metrics": self.optimization_metrics,
            "current_strategy": self.current_strategy.value,
            "cache_size": len(self.route_cache),
            "active_bottlenecks": len(self._identify_bottlenecks()),
            "average_traffic_density": sum(self.real_time_traffic.values()) / len(self.real_time_traffic) if self.real_time_traffic else 1.0
        }

    async def optimize_route(self, request):
        """Optimiza una ruta según los parámetros especificados"""
        try:
            start_node = request.get("start_node")
            end_node = request.get("end_node")
            
            if not start_node or not end_node:
                return None
            
            if start_node not in self.street_graph.nodes or end_node not in self.street_graph.nodes:
                return None
            
            # Usar Dijkstra como algoritmo principal
            if nx.has_path(self.street_graph, start_node, end_node):
                route = nx.shortest_path(self.street_graph, start_node, end_node, weight="weight")
                cost = nx.shortest_path_length(self.street_graph, start_node, end_node, weight="weight")
                
                return {
                    "route": route,
                    "total_cost": cost,
                    "algorithm": "dijkstra",
                    "computation_time": 0.001,
                    "vehicle_type": request.get("vehicle_type", "normal")
                }
            return None
        except Exception as e:
            self.logger.error(f"Error optimizando ruta: {e}")
            return None
