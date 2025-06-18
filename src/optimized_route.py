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
    from weather_impact_analyzer import get_weather_impact_for_routes, get_differentiated_weather_factors
    WEATHER_ANALYSIS_AVAILABLE = True
    print("Análisis climático diferenciado disponible para optimización de rutas")
except ImportError as e:
    print(f"Advertencia: Análisis climático no disponible: {e}")
    WEATHER_ANALYSIS_AVAILABLE = False
    
    def get_weather_impact_for_routes():
        """Función dummy si el análisis climático no está disponible"""
        return 1.0
    
    def get_differentiated_weather_factors():
        """Función dummy para factores diferenciados"""
        return {'motorway': 1.0, 'primary': 1.0, 'secondary': 1.0, 'residential': 1.0, 'unpaved': 1.0}


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
        # Obtener factores de impacto climático diferenciados
        weather_factors = {'base': 1.0}
        if use_weather_impact and WEATHER_ANALYSIS_AVAILABLE:
            try:
                weather_factors = get_differentiated_weather_factors()
                base_factor = get_weather_impact_for_routes()
                weather_factors['base'] = base_factor
                print(f"Factores climáticos diferenciados aplicados:")
                for road_type, factor in weather_factors.items():
                    print(f"  {road_type}: {factor:.2f}")
            except Exception as e:
                print(f"Error obteniendo factores climáticos: {e}")
                weather_factors = {'base': 1.0}
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
        
        # Calcular distancias directamente sin cache
        print(f"Calculando matriz de distancias para {n} puntos...")
        import time
        start_time = time.time()
        
        # Elegir método según número de puntos para optimizar velocidad
        if n <= 150:
            # Pocos puntos: usar método preciso
            dist_matrix = _calculate_distance_matrix_ultra_fast(
                street_graph, all_points, weather_factors, n, start_time
            )
        elif n <= 300:
            # Puntos medios: usar Dijkstra optimizado con progreso cada 20%
            dist_matrix = _calculate_distance_matrix_fast_medium(
                street_graph, all_points, weather_factors, n, start_time
            )
        else: 
            # Muchos puntos: usar aproximación euclidiana (instantáneo)
            print("⚡ Demasiados puntos, usando aproximación rápida...")
            dist_matrix = _calculate_euclidean_matrix_with_climate(
                all_points, weather_factors, street_graph
            )
        
        total_time = time.time() - start_time
        print(f"Matriz de distancias calculada en {total_time:.2f} segundos")
        
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
        
        # ////////// TABU SEARCH SOLVER (OPTIMIZADO PARA VELOCIDAD) //////////
        
        print("Iniciando optimización con Tabu Search...")
        optimization_start = time.time()
        
        routes = ts_solver.solve_vrp(
            dist_matrix,
            objectives,
            demands,
            truck_capacities,
            num_trucks,
            max_iter=300,        # Reducido de 1000
            base_tabu_tenure=50,  # Reducido de 100
            no_improve_limit=100, # Reducido de 200
            diversification_interval=150  # Reducido de 500
        )
        
        optimization_time = time.time() - optimization_start
        print(f"Optimización completada en {optimization_time:.2f} segundos")
        
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
              # Expandir la ruta para incluir nodos intermedios (OPTIMIZADO)
            paths_and_costs = []
            route_cost = 0
            
            # Usar matriz precalculada cuando sea posible
            for i in range(len(complete_route) - 1):
                src = complete_route[i]
                dst = complete_route[i + 1]
                
                # Usar costo de la matriz precalculada
                cost = None
                path = None
                
                if src in node_index_map and dst in node_index_map:
                    src_idx = node_index_map[src]
                    dst_idx = node_index_map[dst]
                    if dist_matrix[src_idx][dst_idx] != float('inf'):
                        cost = dist_matrix[src_idx][dst_idx]
                        # Solo calcular el path si realmente lo necesitamos
                        try:
                            path = nx.shortest_path(street_graph, src, dst, weight='weight')
                        except:
                            path = [src, dst]  # Fallback simple
                
                if cost is None or path is None:
                    try:
                        path = nx.shortest_path(street_graph, src, dst, weight='weight')
                        # Calcular costo usando factores climáticos
                        cost = _apply_weather_factor_to_path(street_graph, path, weather_factors)
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        print(f"Advertencia: No hay camino entre {src} y {dst}")
                        path = [src, dst]
                        cost = 0
                
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

def _get_road_type_factor(street_graph, node1, node2):
    """
    Determina el factor de impacto climático basado en el tipo de carretera
    """
    try:
        edge_data = street_graph[node1][node2]
        
        # Obtener tipo de carretera si existe
        road_type = edge_data.get('highway', 'residential')
        lane_count = edge_data.get('lanes', 1)
        surface = edge_data.get('surface', 'asphalt')
        
        # Factores base por tipo de carretera (multiplicador adicional del clima)
        road_type_factors = {
            'motorway': 0.8,      # Autopistas son más resistentes al clima
            'trunk': 0.85,        # Vías principales
            'primary': 0.9,       # Carreteras primarias
            'secondary': 1.0,     # Carreteras secundarias (factor base)
            'tertiary': 1.1,      # Carreteras terciarias
            'residential': 1.2,   # Calles residenciales más afectadas
            'service': 1.3,       # Calles de servicio
            'track': 1.5,         # Caminos sin pavimentar muy afectados
            'path': 1.8           # Senderos muy vulnerables
        }
        
        # Factores por superficie
        surface_factors = {
            'asphalt': 1.0,       # Asfalto - factor base
            'concrete': 0.9,      # Concreto más resistente
            'paved': 1.0,         # Pavimentado
            'unpaved': 1.4,       # Sin pavimentar
            'gravel': 1.3,        # Grava
            'dirt': 1.6,          # Tierra
            'grass': 1.8          # Césped
        }
        
        # Factores por número de carriles (más carriles = alternativas)
        lane_factor = max(0.8, 1.0 - (lane_count - 1) * 0.1)
        
        # Combinar factores
        road_factor = road_type_factors.get(road_type, 1.0)
        surf_factor = surface_factors.get(surface, 1.0)
        
        return road_factor * surf_factor * lane_factor
        
    except (KeyError, TypeError):
        # Si no hay información, asumir carretera secundaria
        return 1.0

def _calculate_weather_adjusted_distance(street_graph, source, target, weather_factors):
    """
    Calcula la distancia ajustada por clima de manera optimizada
    """
    try:
        # Usar solo la ruta más corta pero con factores diferenciados por segmento
        path = nx.shortest_path(street_graph, source, target, weight='weight')
        
        total_cost = 0
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            
            # Costo base de la arista
            base_cost = street_graph[u][v].get('weight', 1.0)
            
            # Obtener factor climático específico para este tipo de carretera
            edge_data = street_graph[u][v]
            road_type = edge_data.get('highway', 'residential')
            
            # Mapear tipos de carretera a factores climáticos (optimizado)
            if road_type in ['motorway', 'trunk']:
                weather_factor = weather_factors.get('motorway', weather_factors.get('base', 1.0))
            elif road_type == 'primary':
                weather_factor = weather_factors.get('primary', weather_factors.get('base', 1.0))
            elif road_type in ['secondary', 'tertiary']:
                weather_factor = weather_factors.get('secondary', weather_factors.get('base', 1.0))
            elif road_type in ['residential', 'service']:
                weather_factor = weather_factors.get('residential', weather_factors.get('base', 1.0))
            elif road_type in ['track', 'path']:
                weather_factor = weather_factors.get('unpaved', weather_factors.get('base', 1.0))
            else:
                weather_factor = weather_factors.get('base', 1.0)
            
            # Factor específico para este tipo de carretera (simplificado)
            road_factor = _get_road_type_factor_optimized(edge_data)
            
            # Costo ajustado de esta arista
            adjusted_cost = base_cost * weather_factor * road_factor
            total_cost += adjusted_cost
        
        return total_cost
        
    except Exception as e:
        print(f"Error calculando distancia ajustada entre {source} y {target}: {e}")
        # Fallback: usar distancia normal con factor climático base
        try:
            base_distance = nx.shortest_path_length(street_graph, source, target, weight='weight')
            return base_distance * weather_factors.get('base', 1.0)
        except:
            return float('inf')

def _get_road_type_factor_optimized(edge_data):
    """
    Versión optimizada del factor de tipo de carretera
    """
    road_type = edge_data.get('highway', 'residential')
    surface = edge_data.get('surface', 'asphalt')
    
    # Factores simplificados por tipo de carretera
    type_factors = {
        'motorway': 0.8, 'trunk': 0.85, 'primary': 0.9,
        'secondary': 1.0, 'tertiary': 1.1, 'residential': 1.2,
        'service': 1.3, 'track': 1.5, 'path': 1.8
    }
    
    # Factores por superficie (simplificado)
    surface_factors = {
        'asphalt': 1.0, 'concrete': 0.9, 'unpaved': 1.4,
        'gravel': 1.3, 'dirt': 1.6
    }
    
    road_factor = type_factors.get(road_type, 1.0)
    surf_factor = surface_factors.get(surface, 1.0)
    
    return road_factor * surf_factor

def _apply_weather_factor_to_path(street_graph, path, weather_factors):
    """
    Aplica factores climáticos a un camino de manera optimizada
    """
    total_cost = 0
    
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        
        # Costo base de la arista
        base_cost = street_graph[u][v].get('weight', 1.0)
        
        # Obtener tipo de carretera
        edge_data = street_graph[u][v]
        road_type = edge_data.get('highway', 'residential')
        
        # Factor climático específico (optimizado con mapeo directo)
        if road_type in ['motorway', 'trunk']:
            weather_factor = weather_factors.get('motorway', weather_factors.get('base', 1.0))
        elif road_type == 'primary':
            weather_factor = weather_factors.get('primary', weather_factors.get('base', 1.0))
        elif road_type in ['secondary', 'tertiary']:
            weather_factor = weather_factors.get('secondary', weather_factors.get('base', 1.0))
        elif road_type in ['residential', 'service']:
            weather_factor = weather_factors.get('residential', weather_factors.get('base', 1.0))
        elif road_type in ['track', 'path']:
            weather_factor = weather_factors.get('unpaved', weather_factors.get('base', 1.0))
        else:
            weather_factor = weather_factors.get('base', 1.0)
        
        # Factor de superficie simplificado
        surface = edge_data.get('surface', 'asphalt')
        surface_factor = 1.4 if surface in ['unpaved', 'dirt', 'gravel'] else 1.0
        
        # Costo ajustado
        adjusted_cost = base_cost * weather_factor * surface_factor
        total_cost += adjusted_cost
    
    return total_cost

def _calculate_distance_matrix_ultra_fast(street_graph, all_points, weather_factors, n, start_time):
    """
    Calcula matriz de distancias de forma ultra optimizada
    """
    import time
    
    dist_matrix = [[float('inf') for _ in range(n)] for _ in range(n)]
    avg_weather_factor = sum(weather_factors.values()) / len(weather_factors)
    
    print("🚀 Usando algoritmo ultra-rápido...")
    
    for i in range(n):
        dist_matrix[i][i] = 0  # Distancia a sí mismo
        source = all_points[i]
        
        try:
            # Usar solo distancias base de Dijkstra + factor promedio (súper rápido)
            shortest_paths = nx.single_source_dijkstra_path_length(
                street_graph, source, weight='weight')
            
            for j in range(n):
                if i != j:
                    target = all_points[j]
                    base_distance = shortest_paths.get(target, float('inf'))
                    
                    # Aplicar factor climático promedio (sin calcular rutas individuales)
                    if base_distance != float('inf'):
                        dist_matrix[i][j] = base_distance * avg_weather_factor
                    else:
                        dist_matrix[i][j] = float('inf')
            
            # Progreso más frecuente
            if (i + 1) % max(1, n // 10) == 0:  # Cada 10%
                elapsed = time.time() - start_time
                progress = (i + 1) / n * 100
                print(f"⚡ Progreso: {progress:.0f}% ({elapsed:.1f}s)")
                
        except Exception as e:
            print(f"❌ Error en nodo {source}: {e}")
    
    total_time = time.time() - start_time
    print(f"✅ Matriz calculada en {total_time:.2f}s (modo ultra-rápido)")
    return dist_matrix

def _calculate_distance_matrix_fast_medium(street_graph, all_points, weather_factors, n, start_time):
    """
    Método medio: optimizado para 7-15 puntos
    """
    import time
    
    dist_matrix = [[float('inf') for _ in range(n)] for _ in range(n)]
    avg_weather_factor = sum(weather_factors.values()) / len(weather_factors)
    
    print("⚡ Usando método medio-rápido...")
    
    for i in range(n):
        dist_matrix[i][i] = 0
        source = all_points[i]
        
        try:
            shortest_paths = nx.single_source_dijkstra_path_length(
                street_graph, source, weight='weight')
            
            for j in range(n):
                if i != j:
                    target = all_points[j]
                    base_distance = shortest_paths.get(target, float('inf'))
                    
                    if base_distance != float('inf'):
                        dist_matrix[i][j] = base_distance * avg_weather_factor
                    else:
                        dist_matrix[i][j] = float('inf')
            
            # Progreso cada 20%
            if (i + 1) % max(1, n // 5) == 0:
                elapsed = time.time() - start_time
                progress = (i + 1) / n * 100
                print(f"⚡ Progreso: {progress:.0f}% ({elapsed:.1f}s)")
                
        except Exception as e:
            print(f"❌ Error en nodo {source}: {e}")
    
    total_time = time.time() - start_time
    print(f"✅ Matriz medio-rápida en {total_time:.2f}s")
    return dist_matrix

def _calculate_euclidean_matrix_with_climate(all_points, weather_factors, street_graph):
    """
    Calcula matriz usando distancias euclidianas + factores climáticos (SÚPER RÁPIDO)
    """
    import math
    n = len(all_points)
    dist_matrix = [[0.0 for _ in range(n)] for _ in range(n)]
    avg_weather_factor = sum(weather_factors.values()) / len(weather_factors)
    
    print("🏃‍♂️ Usando aproximación euclidiana (ultra-rápido)...")
    
    # Obtener coordenadas
    coords = {}
    for point in all_points:
        try:
            node_data = street_graph.nodes[point]
            coords[point] = (node_data.get('lat', 0), node_data.get('lon', 0))
        except:
            coords[point] = (0, 0)
    
    # Calcular distancias euclidianas
    for i in range(n):
        for j in range(n):
            if i == j:
                dist_matrix[i][j] = 0
            else:
                lat1, lon1 = coords[all_points[i]]
                lat2, lon2 = coords[all_points[j]]
                
                # Distancia euclidiana simple
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                distance = math.sqrt(dlat*dlat + dlon*dlon) * 111  # ~111km por grado
                
                # Factor de corrección para calles + clima
                dist_matrix[i][j] = distance * 1.4 * avg_weather_factor
    
    print("✅ Matriz euclidiana lista")
    return dist_matrix