import networkx as nx
import sys
import os
sys.path.append("src/metaheuristic/ag_solver")
import ag_solver as ag_solver
sys.path.append("src/metaheuristic/vns_solver") 
import vns_solver 
sys.path.append("src/metaheuristic/sa_solver") 
import sa_solver 
sys.path.append("src/metaheuristic/ts_solver") 
import ts_solver

# Importar el analizador de impacto climático
sys.path.append("src/weather")
try:
    from weather_impact_analyzer import get_weather_impact_for_routes
    WEATHER_ANALYSIS_AVAILABLE = True
    print("Análisis climático disponible para optimización de rutas")
except ImportError as e:
    print(f"Advertencia: Análisis climático no disponible: {e}")
    WEATHER_ANALYSIS_AVAILABLE = False
    
    def get_weather_impact_for_routes():
        """Función dummy si el análisis climático no está disponible"""
        return 1.0


# def expand_route_with_path_nodes(street_graph, route):
#     """
#     Expande una ruta para incluir todos los nodos intermedios del camino
#     """
#     expanded_route = []
#     for i in range(len(route) - 1):
#         src = route[i]
#         dst = route[i + 1]
#         try:
#             # Obtener el camino completo entre los dos puntos
#             path = nx.shortest_path(street_graph, src, dst, weight='weight')
#             # Añadir todos los nodos excepto el último (para evitar duplicados)
#             expanded_route.extend(path[:-1])
#         except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
#             print(f"Error al expandir ruta entre {src} y {dst}: {e}")
#             # Si no hay camino, al menos incluir el origen
#             expanded_route.append(src)
    
#     # Añadir el último nodo de la ruta original
#     if route:
#         expanded_route.append(route[-1])
    
#     return expanded_route

def optimize_delivery_routes(street_graph, start_point, target_points, num_trucks=1, 
                            truck_capacities=None, target_demands=None, use_weather_impact=True):
    """
    Optimiza rutas de entrega utilizando el solver VRP avanzado con análisis climático
    
    Args:
        street_graph: Grafo de NetworkX con la red de calles
        start_point: Nodo de inicio (depósito)
        target_points: Lista de nodos objetivo
        num_trucks: Número de vehículos disponibles
        truck_capacities: Lista de capacidades de los vehículos
        target_demands: Lista de demandas para cada punto objetivo
        use_weather_impact: Si usar el análisis de impacto climático
    
    Returns:
        (rutas_optimizadas, costo_total)
    """
    try:
        # Obtener factor de impacto climático
        weather_factor = 1.0
        if use_weather_impact and WEATHER_ANALYSIS_AVAILABLE:
            try:
                weather_factor = get_weather_impact_for_routes()
                print(f"Factor de impacto climático aplicado: {weather_factor:.2f}")
            except Exception as e:
                print(f"Error obteniendo factor climático: {e}")
                weather_factor = 1.0
        else:
            print("Análisis climático deshabilitado o no disponible")
        
        # Validar y preparar capacidades
        if not truck_capacities:
            truck_capacities = [100] * num_trucks  # Capacidad por defecto
        elif len(truck_capacities) < num_trucks:
            # Extender con la última capacidad si faltan valores
            truck_capacities.extend([truck_capacities[-1]] * (num_trucks - len(truck_capacities)))
        
        # Validar y preparar demandas
        if not target_demands:
            target_demands = [1] * len(target_points)  # Demanda por defecto
        elif len(target_demands) < len(target_points):
            # Extender con la última demanda si faltan valores
            target_demands.extend([target_demands[-1]] * (len(target_points) - len(target_demands)))
        
        # Crear matriz de distancias
        all_points = [start_point] + target_points
        n = len(all_points)
        dist_matrix = [[float('inf') for _ in range(n)] for _ in range(n)]
        
        # Calcular distancias reales usando el algoritmo de camino más corto
        for i in range(n):
            # La distancia de un nodo a sí mismo es 0
            dist_matrix[i][i] = 0
            source = all_points[i]
            
            try:
                # Calcular todas las distancias desde source en una sola llamada
                shortest_paths = nx.single_source_dijkstra_path_length(
                    street_graph, source, weight='weight')
                  # Llenar toda la fila i (distancias desde source a todos los demás)
                for j in range(n):
                    if i == j:
                        continue  # Ya asignado como 0
                    
                    target = all_points[j]
                    base_distance = shortest_paths.get(target, float('inf'))
                    
                    # Aplicar factor climático a la distancia
                    adjusted_distance = base_distance * weather_factor
                    
                    # Guardar en la matriz
                    dist_matrix[i][j] = adjusted_distance
                    
            except nx.NetworkXError as e:
                print(f"Error al calcular distancias desde {source}: {e}")
        
        # Preparar vector de demandas (incluyendo el depósito como 0)
        demands = [0] + target_demands
        
        # ////////// GENETIC ALGORITHM SOLVER //////////
        # routes = ag_solver.solve_vrp(
        #     dist_matrix, 
        #     demands, 
        #     truck_capacities, 
        #     pop_size=400,
        #     sel_size=40,
        #     max_gen=1000,
        #     no_improve_limit=20,
        #     mut_rate=0.3)
        
        # ////////// SIMULATED ANNEALING SOLVER //////////

        # routes = sa_solver.solve(
        #     N=n,  # Número total de nodos (incluyendo el depósito)
        #     T=num_trucks,  # Número de vehículos
        #     capacity=truck_capacities,  # Capacidades de cada vehículo
        #     demand=demands,  # Demandas de cada nodo
        #     distMat=dist_matrix,  # Matriz de distancias
        #     T0=100.0,  # Temperatura inicial
        #     Tf=0.1,  # Temperatura final
        #     alpha=0.98,  # Factor de enfriamiento
        #     iterPerTemp=100,  # Iteraciones por nivel de temperatura
        #     lambdaPen=1000.0,  # Penalización por usar más vehículos
        #     maxSeconds=30.0,  # Tiempo máximo de ejecución en segundos
        #     seed=42  # Semilla aleatoria para reproducibilidad
        # )
        
        # Preparar los objetivos (índices de 1 a n-1, excluyendo el depósito)
        objectives = list(range(1, n))
        
        # ////////// TABU SEARCH SOLVER //////////
        
        routes = ts_solver.solve_vrp(
            dist_matrix,
            objectives,
            demands,
            truck_capacities,
            num_trucks,
            max_iter=1000,
            base_tabu_tenure=100,
            no_improve_limit=200,
            diversification_interval=500
        )
        
        # Calcular el costo total de las rutas
        total_cost = 0
        final_routes = []
        
        # Crear un mapa de índices para búsqueda rápida
        node_index_map = {node: idx for idx, node in enumerate(all_points)}
        
        for route in routes:
            # Convertir índices de ruta a IDs de nodos reales
            real_route = [all_points[i] for i in route]
            # Añadir el depósito al principio y final de cada ruta
            complete_route = [start_point] + real_route + [start_point]
            
            # Expandir la ruta para incluir nodos intermedios
            paths_and_costs = []
            route_cost = 0
            
            # Primero, calculamos los caminos más cortos entre cada par de nodos consecutivos
            for i in range(len(complete_route) - 1):
                src = complete_route[i]
                dst = complete_route[i + 1]
                
                # Intentamos obtener el camino y costo de la matriz precalculada
                cost = None
                if src in node_index_map and dst in node_index_map:
                    src_idx = node_index_map[src]
                    dst_idx = node_index_map[dst]
                    if dist_matrix[src_idx][dst_idx] != float('inf'):
                        cost = dist_matrix[src_idx][dst_idx]
                
                try:
                    # Obtener el camino completo entre src y dst
                    path = nx.shortest_path(street_graph, src, dst, weight='weight')
                    
                    # Si el costo no se obtuvo de la matriz, calcularlo
                    if cost is None:
                        segment_cost = 0
                        for k in range(len(path) - 1):
                            u = path[k]
                            v = path[k + 1]
                            segment_cost += street_graph[u][v]['weight']
                        cost = segment_cost
                    
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    print(f"Advertencia: No hay camino entre {src} y {dst}")
                    path = [src, dst]  # Fallback
                    cost = 0  # No sumamos costo para este segmento
                
                paths_and_costs.append((path, cost))
                route_cost += cost
            
            # Construir la ruta expandida y eliminar duplicados
            expanded_route = []
            for i, (path, _) in enumerate(paths_and_costs):
                if i == len(paths_and_costs) - 1:
                    # Incluir todo el último camino
                    expanded_route.extend(path)
                else:
                    # Excluir el último nodo para evitar duplicados
                    expanded_route.extend(path[:-1])
            
            final_routes.append(expanded_route)
            total_cost += route_cost
        
        return final_routes, total_cost
        
    except Exception as e:
        print(f"Error en la optimización de rutas: {e}")
        import traceback
        traceback.print_exc()
        return [], 0
    

# def optimize_delivery_routes(street_graph, start_point, target_points, num_trucks=1, 
#                             truck_capacities=None, target_demands=None,
#                             max_iterations=2000, time_limit=10.0):
#     """
#     Optimiza rutas de entrega utilizando el solver VNS avanzado
    
#     Args:
#         street_graph: Grafo de NetworkX con la red de calles
#         start_point: Nodo de inicio (depósito)
#         target_points: Lista de nodos objetivo
#         num_trucks: Número de vehículos disponibles
#         truck_capacities: Lista de capacidades de los vehículos
#         target_demands: Lista de demandas para cada punto objetivo
#         max_iterations: Número máximo de iteraciones para VNS
#         time_limit: Límite de tiempo en segundos
    
#     Returns:
#         (rutas_optimizadas, costo_total)
#     """
#     try:
#         # Validar y preparar capacidades
#         if not truck_capacities:
#             truck_capacities = [100] * num_trucks  # Capacidad por defecto
#         elif len(truck_capacities) < num_trucks:
#             # Extender con la última capacidad si faltan valores
#             truck_capacities.extend([truck_capacities[-1]] * (num_trucks - len(truck_capacities)))
        
#         # Validar y preparar demandas
#         if not target_demands:
#             target_demands = [1] * len(target_points)  # Demanda por defecto
#         elif len(target_demands) < len(target_points):
#             # Extender con la última demanda si faltan valores
#             target_demands.extend([target_demands[-1]] * (len(target_points) - len(target_demands)))
        
#         # Crear matriz de distancias
#         all_points = [start_point] + target_points
#         n = len(all_points)
#         dist_matrix = []
        
#         # Inicializar matriz con distancias infinitas
#         for i in range(n):
#             row = []
#             for j in range(n):
#                 row.append(float('inf'))
#             dist_matrix.append(row)
        
#         # Calcular distancias reales usando el algoritmo de camino más corto
#         for i in range(n):
#             # La distancia de un nodo a sí mismo es 0
#             dist_matrix[i][i] = 0
#             source = all_points[i]
            
#             # Calcular las distancias desde este nodo a todos los demás
#             try:
#                 # Usar Dijkstra para calcular las distancias más cortas
#                 shortest_paths = nx.single_source_dijkstra_path_length(
#                     street_graph, source, weight='weight')
                
#                 for j in range(n):
#                     target = all_points[j]
#                     if target in shortest_paths:
#                         dist_matrix[i][j] = shortest_paths[target]
#             except nx.NetworkXNoPath:
#                 print(f"Advertencia: No hay camino desde {source} a algunos destinos")
#                 continue
        
#         # Preparar vector de demandas (incluyendo el depósito como 0)
#         demands = [0] + target_demands
        
#         # Ejecutar el solver VNS
#         solution = vns_solver.vns_hetero_improved(
#             dist_matrix, 
#             demands, 
#             truck_capacities, 
#             max_iterations, 
#             time_limit
#         )
        
#         # Calcular el costo total de las rutas
#         total_cost = solution.total_cost
#         final_routes = []
        
#         for route in solution.routes:
#             # Solo procesamos rutas que no estén vacías
#             if not route.nodes:
#                 continue
                
#             # Convertir índices de ruta a IDs de nodos reales
#             real_route = [all_points[i] for i in route.nodes]
#             # Añadir el depósito al principio y final de cada ruta
#             complete_route = [start_point] + real_route + [start_point]
#             expanded_route = expand_route_with_path_nodes(street_graph, complete_route)
#             final_routes.append(expanded_route)
        
#         return final_routes, total_cost
        
#     except Exception as e:
#         print(f"Error en la optimización de rutas: {e}")
#         import traceback
#         traceback.print_exc()
#         return [], 0