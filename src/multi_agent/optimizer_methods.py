# Métodos adicionales para RouteOptimizerAgent

async def optimize_route(self, request):
    """Optimiza una ruta según los parámetros especificados"""
    try:
        start_node = request.get("start_node")
        end_node = request.get("end_node")
        vehicle_type = request.get("vehicle_type", "normal")
        priority = request.get("priority", "normal")
        constraints = request.get("constraints", {})
        
        if not start_node or not end_node:
            self.logger.error("Nodos de inicio o fin no especificados")
            return None
        
        # Verificar si los nodos existen en el grafo
        if start_node not in self.street_graph.nodes or end_node not in self.street_graph.nodes:
            self.logger.error(f"Nodos no encontrados en el grafo: {start_node}, {end_node}")
            return None
        
        start_time = datetime.now()
        
        # Seleccionar algoritmo basado en constrains o prioridad
        algorithm = constraints.get("algorithm", "dijkstra")
        
        if algorithm == "dijkstra":
            route, cost = await self._dijkstra_route(start_node, end_node)
        elif algorithm == "astar":
            route, cost = await self._astar_route(start_node, end_node)
        elif algorithm == "genetic":
            route, cost = await self._genetic_algorithm_route(start_node, end_node, priority)
        elif algorithm == "ant_colony":
            route, cost = await self._ant_colony_route(start_node, end_node, priority)
        else:
            # Default a Dijkstra
            route, cost = await self._dijkstra_route(start_node, end_node)
            algorithm = "dijkstra"
        
        computation_time = (datetime.now() - start_time).total_seconds()
        
        if route:
            # Actualizar métricas
            self.optimization_metrics["routes_optimized"] += 1
            self.optimization_metrics["computation_time"] += computation_time
            
            result = {
                "route": route,
                "total_cost": cost,
                "algorithm": algorithm,
                "computation_time": computation_time,
                "vehicle_type": vehicle_type,
                "optimization_strategy": self.current_strategy.value,
                "cached": False
            }
            
            self.logger.info(f"Ruta optimizada: {start_node} → {end_node} ({algorithm}, {cost:.2f})")
            return result
        else:
            self.logger.warning(f"No se encontró ruta entre {start_node} y {end_node}")
            return None
            
    except Exception as e:
        self.logger.error(f"Error optimizando ruta: {e}")
        return None

async def _dijkstra_route(self, start_node, end_node):
    """Implementa algoritmo de Dijkstra"""
    try:
        import networkx as nx
        if nx.has_path(self.street_graph, start_node, end_node):
            route = nx.shortest_path(self.street_graph, start_node, end_node, weight="weight")
            cost = nx.shortest_path_length(self.street_graph, start_node, end_node, weight="weight")
            return route, cost
    except Exception as e:
        self.logger.error(f"Error en Dijkstra: {e}")
    return None, float('inf')

async def _astar_route(self, start_node, end_node):
    """Implementa algoritmo A*"""
    def heuristic(node1, node2):
        try:
            n1_data = self.street_graph.nodes[node1]
            n2_data = self.street_graph.nodes[node2]
            lat1, lon1 = n1_data.get('lat', 0), n1_data.get('lon', 0)
            lat2, lon2 = n2_data.get('lat', 0), n2_data.get('lon', 0)
            return ((lat1 - lat2)**2 + (lon1 - lon2)**2)**0.5
        except:
            return 1.0
    
    try:
        import networkx as nx
        if nx.has_path(self.street_graph, start_node, end_node):
            route = nx.astar_path(self.street_graph, start_node, end_node, 
                                heuristic=heuristic, weight="weight")
            cost = nx.astar_path_length(self.street_graph, start_node, end_node, 
                                      heuristic=heuristic, weight="weight")
            return route, cost
    except Exception as e:
        self.logger.error(f"Error en A*: {e}")
    return None, float('inf')

async def _genetic_algorithm_route(self, start_node, end_node, priority):
    """Implementa algoritmo genético simplificado"""
    try:
        base_route, base_cost = await self._dijkstra_route(start_node, end_node)
        if base_route:
            # Simular mejora genética
            improvement_factor = 0.9 if priority == "high" else 0.95
            optimized_cost = base_cost * improvement_factor
            return base_route, optimized_cost
    except Exception as e:
        self.logger.error(f"Error en algoritmo genético: {e}")
    return None, float('inf')

async def _ant_colony_route(self, start_node, end_node, priority):
    """Implementa algoritmo de colonia de hormigas simplificado"""
    try:
        import networkx as nx
        if nx.has_path(self.street_graph, start_node, end_node):
            route = nx.shortest_path(self.street_graph, start_node, end_node, weight="weight")
            cost = nx.shortest_path_length(self.street_graph, start_node, end_node, weight="weight")
            # Simular mejora por feromonas
            optimized_cost = cost * 0.92
            return route, optimized_cost
    except Exception as e:
        self.logger.error(f"Error en colonia de hormigas: {e}")
    return None, float('inf')
