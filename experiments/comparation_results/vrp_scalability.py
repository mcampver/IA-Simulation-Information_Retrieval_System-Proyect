import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
import sys
import os
from tqdm import tqdm
import json
import math
sys.path.append("src/ag_solver")
sys.path.append("src/vns_solver")
import ag_solver
import vns_solver

# Configuración de visualizaciones
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("paper", font_scale=1.2)

def haversine(lat1, lon1, lat2, lon2):
    """Calcula la distancia entre dos puntos geográficos en km"""
    R = 6371.0  # Radio de la Tierra en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# 1. CARGA Y PREPARACIÓN DEL GRAFO DE LA HABANA
def load_havana_graph(filename='../cache/479c34c9f9679cb8467293e0403a0250c7ef8556.json'):
    """
    Carga el grafo de La Habana desde un archivo JSON o crea uno si no existe.
    En un escenario real, cargarías un grafo desde OSM.
    Versión optimizada para reducir el uso de memoria.
    """
    try:
        import ijson
    except ImportError:
        print("Instalando ijson para procesamiento de JSON por streaming...")
        import subprocess
        subprocess.check_call(["pip", "install", "ijson"])
        import ijson
    
    street_graph = nx.MultiDiGraph()  # Grafo dirigido para representar calles
    all_nodes = []
    street_congestion = {}  # Diccionario para almacenar congestión de calles
    
    # Velocidades estimadas basadas en tipo de calle (km/h)
    highway_speeds = {
        "motorway": 120,
        "trunk": 100,
        "primary": 90,
        "secondary": 70,
        "tertiary": 50,
        "residential": 30,
        "service": 20,
        "unclassified": 40,
        "living_street": 15,
        "pedestrian": 5,
        "track": 20,
        "path": 10,
        # Valores por defecto para otros tipos
        "default": 50
    }
    
    print(f"Intentando abrir archivo de caché: {filename}")
    
    # Procesamos primero los nodos
    nodes = {}
    with open(filename, 'r', encoding='utf-8') as f:
        # Procesamos elementos uno por uno para no cargar todo en memoria
        for element in ijson.items(f, 'elements.item'):
            if element.get('type') == 'node':
                node_id = element.get('id')
                lat = element.get('lat')
                lon = element.get('lon')
                if node_id and lat and lon:
                    nodes[node_id] = (float(lat), float(lon)) 
                    street_graph.add_node(node_id, lat=float(lat), lon=float(lon))
    
    print(f"Nodos extraídos: {len(nodes)}")
    
    # Procesamos las vías (ways) para crear aristas
    edge_count = 0
    with open(filename, 'r', encoding='utf-8') as f:
        for element in ijson.items(f, 'elements.item'):
            if element.get('type') == 'way' and element.get('tags', {}).get('highway'):
                way_nodes = element.get('nodes', [])
                
                # Verificar si es de un solo sentido
                oneway = element.get('tags', {}).get('oneway', 'no')
                
                # Obtener información de velocidad
                highway_type = element.get('tags', {}).get('highway', 'default')
                max_speed_raw = element.get('tags', {}).get('maxspeed')
                
                # Procesar maxspeed si existe
                max_speed = None
                if max_speed_raw:
                    try:
                        # Manejar formatos como "50" o "50 km/h"
                        max_speed = float(max_speed_raw.split()[0])
                    except (ValueError, IndexError):
                        max_speed = None
                
                # Usar velocidad estimada si no hay maxspeed
                if max_speed is None:
                    max_speed = highway_speeds.get(highway_type, highway_speeds["default"])
                
                # Calcular velocidad mínima (70% de la máxima como regla general)
                min_speed = max_speed * 0.7
                
                for i in range(len(way_nodes) - 1):
                    if way_nodes[i] in nodes and way_nodes[i+1] in nodes:
                        node1 = way_nodes[i]
                        node2 = way_nodes[i+1]
                        lat1, lon1 = nodes[node1]
                        lat2, lon2 = nodes[node2]
                        # Calcular distancia entre nodos
                        distance = haversine(lat1, lon1, lat2, lon2)
                        
                        # Añadir arista(s) según dirección con información de velocidad
                        if oneway == 'yes':
                            # Solo añadir en la dirección especificada
                            street_graph.add_edge(node1, node2, weight=distance, 
                                                 max_speed=max_speed, min_speed=min_speed,
                                                 highway_type=highway_type)
                            edge_count += 1
                        else:
                            # Añadir en ambas direcciones si es bidireccional
                            street_graph.add_edge(node1, node2, weight=distance, 
                                                 max_speed=max_speed, min_speed=min_speed,
                                                 highway_type=highway_type)
                            street_graph.add_edge(node2, node1, weight=distance, 
                                                 max_speed=max_speed, min_speed=min_speed,
                                                 highway_type=highway_type)
                            edge_count += 2
    
    # Lista de todos los nodos del grafo
    all_nodes = list(street_graph.nodes())
    
    # Inicializar congestión a 0 para todas las calles
    for edge in street_graph.edges():
        street_congestion[edge] = 0
    
    print(f"Grafo cargado con {len(all_nodes)} nodos y {edge_count} aristas")
    
    return street_graph

def generate_real_instance(G, num_clients, seed=42):
    """Genera una instancia de problema VRP basada en el grafo de La Habana."""
    np.random.seed(seed)
    
    # Obtener todos los nodos
    all_nodes = list(G.nodes())
    
    # Seleccionar un depósito (puerto de La Habana, simulado como el nodo 0)
    depot = np.random.choice(all_nodes)
    
    # Seleccionar clientes aleatorios
    client_candidates = [n for n in all_nodes if n != depot]
    clients = np.random.choice(client_candidates, size=min(num_clients, len(client_candidates)), replace=False)
    
    # Crear matriz de distancias para el depósito y los clientes
    nodes_to_include = [depot] + list(clients)
    n = len(nodes_to_include)
    dist_matrix = []
    
    # Inicializar matriz con infinitos
    for i in range(n):
        row = []
        for j in range(n):
            row.append(float('inf'))
        dist_matrix.append(row)
    
    # Calcular distancias usando Dijkstra
    for i, source_idx in enumerate(nodes_to_include):
        # Distancia a sí mismo es 0
        dist_matrix[i][i] = 0
        
        try:
            # Calcular distancias a todos los demás nodos
            length = nx.single_source_dijkstra_path_length(G, source_idx, weight='weight')
            
            for j, target_idx in enumerate(nodes_to_include):
                if target_idx in length:
                    dist_matrix[i][j] = length[target_idx]
        except nx.NetworkXNoPath:
            print(f"Advertencia: No hay camino desde {source_idx} a algunos destinos")
    
    # Generar demandas aleatorias (entre 1 y 3 unidades)
    demands = [0] + [np.random.randint(1, 4) for _ in range(len(clients))]
    
    # Mapeo de índices a nodos reales
    index_to_node = {i: node for i, node in enumerate(nodes_to_include)}
    
    return {
        'dist_matrix': dist_matrix,
        'demands': demands,
        'index_to_node': index_to_node,
        'depot': depot,
        'clients': clients,
        'graph': G
    }

def compute_greedy_solution(dist_matrix, demands, truck_capacity):
    """
    Implementa una heurística greedy básica (nearest neighbor) para comparación.
    """
    n = len(dist_matrix)
    remaining = list(range(1, n))  # Clientes (sin depósito)
    routes = []
    
    while remaining:
        route = []
        current = 0  # Comenzar en el depósito
        load = 0
        
        while remaining:
            # Encontrar el cliente más cercano
            best_dist = float('inf')
            best_next = -1
            
            for next_node in remaining:
                if load + demands[next_node] <= truck_capacity:
                    if dist_matrix[current][next_node] < best_dist:
                        best_dist = dist_matrix[current][next_node]
                        best_next = next_node
            
            if best_next == -1:
                # No hay cliente factible, terminar esta ruta
                break
            
            # Añadir el mejor cliente a la ruta
            route.append(best_next)
            load += demands[best_next]
            current = best_next
            remaining.remove(best_next)
        
        if route:
            routes.append(route)
    
    return routes

# 2. EXPERIMENTOS DE ESCALABILIDAD
def run_scalability_experiments(G, client_counts, truck_capacity=30, n_runs=5, n_boot=1000, ci_level=0.95):
    """Ejecuta experimentos de escalabilidad con diferentes cantidades de clientes."""
    results = []
    
    for num_clients in client_counts:
        print(f"\nEjecutando experimentos con {num_clients} clientes...")
        
        # Generar instancia
        instance = generate_real_instance(G, num_clients)
        dist_matrix = instance['dist_matrix']
        demands = instance['demands']
        
        # Configurar camiones (capacidad fija para todos)
        num_trucks = max(1, int(np.ceil(sum(demands) / truck_capacity)))
        truck_capacities = [truck_capacity] * num_trucks
        
        # 1. AG con parámetros estándar
        standard_times, standard_costs, standard_trucks, standard_cap_util = [], [], [], []
        for run in tqdm(range(n_runs), desc="AG Estándar"):
            t0 = time.time()
            routes = ag_solver.solve_vrp(
                dist_matrix, demands, truck_capacities,
                pop_size=100,
                sel_size=20,
                max_gen=200,
                no_improve_limit=20,
                mut_rate=0.3
            )
            standard_times.append(time.time() - t0)
            standard_costs.append(compute_total_distance(routes, dist_matrix))
            standard_trucks.append(len(routes))
            
            # Calcular utilización de capacidad
            total_used = 0
            for route in routes:
                route_demand = sum(demands[i] for i in route)
                total_used += route_demand
            cap_util = total_used / (len(routes) * truck_capacity) * 100
            standard_cap_util.append(cap_util)
        
        # 2. AG con parámetros intensivos
        intensive_times, intensive_costs, intensive_trucks, intensive_cap_util = [], [], [], []
        for run in tqdm(range(n_runs), desc="AG Intensivo"):
            t0 = time.time()
            routes = ag_solver.solve_vrp(
                dist_matrix, demands, truck_capacities,
                pop_size=500,
                sel_size=100,
                max_gen=500,
                no_improve_limit=30,
                mut_rate=0.3
            )
            intensive_times.append(time.time() - t0)
            intensive_costs.append(compute_total_distance(routes, dist_matrix))
            intensive_trucks.append(len(routes))
            
            # Calcular utilización de capacidad
            total_used = 0
            for route in routes:
                route_demand = sum(demands[i] for i in route)
                total_used += route_demand
            cap_util = total_used / (len(routes) * truck_capacity) * 100
            intensive_cap_util.append(cap_util)
        
        # 3. VNS solver
        vns_times, vns_costs, vns_trucks, vns_cap_util = [], [], [], []
        for run in tqdm(range(n_runs), desc="VNS Solver"):
            t0 = time.time()
            routes = vns_solver.vns_hetero_simplified(
                dist_matrix, 
                demands, 
                truck_capacities,
                max_iterations=2000,  
                time_limit=200.0
            )
            vns_times.append(time.time() - t0)
            vns_costs.append(compute_total_distance(routes, dist_matrix))
            vns_trucks.append(len(routes))
            
            # Calcular utilización de capacidad
            total_used = 0
            for route in routes:
                route_demand = sum(demands[i] for i in route)
                total_used += route_demand
            cap_util = total_used / (len(routes) * truck_capacity) * 100
            vns_cap_util.append(cap_util)
        
        # Bootstrapping para intervalos de confianza
        standard_cost_ci = bootstrap_ci(standard_costs, n_boot, ci_level)
        intensive_cost_ci = bootstrap_ci(intensive_costs, n_boot, ci_level)
        vns_cost_ci = bootstrap_ci(vns_costs, n_boot, ci_level)
        
        # Mejora porcentual respecto a AG estándar
        intensive_improvement = [(s - i) / s * 100 for s, i in zip(standard_costs, intensive_costs)]
        vns_improvement = [(s - v) / s * 100 for s, v in zip(standard_costs, vns_costs)]
        
        results.append({
            'num_clients': num_clients,
            'total_demand': sum(demands[1:]),
            'truck_capacity': truck_capacity,
            'num_trucks_required': num_trucks,
            
            # AG Estándar
            'standard_mean_cost': np.mean(standard_costs),
            'standard_cost_ci_lower': standard_cost_ci[0],
            'standard_cost_ci_upper': standard_cost_ci[1],
            'standard_mean_time': np.mean(standard_times),
            'standard_mean_trucks': np.mean(standard_trucks),
            'standard_mean_cap_util': np.mean(standard_cap_util),
            'standard_raw_costs': standard_costs,
            'standard_raw_times': standard_times,
            
            # AG Intensivo
            'intensive_mean_cost': np.mean(intensive_costs),
            'intensive_cost_ci_lower': intensive_cost_ci[0],
            'intensive_cost_ci_upper': intensive_cost_ci[1],
            'intensive_mean_time': np.mean(intensive_times),
            'intensive_mean_trucks': np.mean(intensive_trucks),
            'intensive_mean_cap_util': np.mean(intensive_cap_util),
            'intensive_mean_improvement': np.mean(intensive_improvement),
            'intensive_raw_costs': intensive_costs,
            'intensive_raw_times': intensive_times,
            'intensive_raw_improvements': intensive_improvement,
            
            # VNS
            'vns_mean_cost': np.mean(vns_costs),
            'vns_cost_ci_lower': vns_cost_ci[0],
            'vns_cost_ci_upper': vns_cost_ci[1],
            'vns_mean_time': np.mean(vns_times),
            'vns_mean_trucks': np.mean(vns_trucks),
            'vns_mean_cap_util': np.mean(vns_cap_util),
            'vns_mean_improvement': np.mean(vns_improvement),
            'vns_raw_costs': vns_costs,
            'vns_raw_times': vns_times,
            'vns_raw_improvements': vns_improvement
        })
    
    return pd.DataFrame(results)

# 3. FUNCIONES AUXILIARES
def compute_total_distance(routes, dist_matrix):
    """Calcula la distancia total para todas las rutas."""
    total = 0.0
    for r in routes:
        prev = 0  # Depósito
        for node in r:
            total += dist_matrix[prev][node]
            prev = node
        total += dist_matrix[prev][0]  # Regreso al depósito
    return total

def bootstrap_ci(data, n_boot=1000, ci=0.95):
    """Calcula intervalos de confianza mediante bootstrapping."""
    boot_means = []
    n = len(data)
    for _ in range(n_boot):
        sample = np.random.choice(data, size=n, replace=True)
        boot_means.append(np.mean(sample))
    lower = np.percentile(boot_means, (1-ci)/2*100)
    upper = np.percentile(boot_means, (1+ci)/2*100)
    return lower, upper

# 4. VISUALIZACIONES
def create_scalability_visualizations(results_df, output_dir="scalability_results"):
    """Crea visualizaciones para el experimento de escalabilidad."""
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Gráfico de líneas: costo vs. número de clientes
    plt.figure(figsize=(12, 8))
    plt.errorbar(
        results_df['num_clients'], 
        results_df['standard_mean_cost'],
        yerr=[results_df['standard_mean_cost'] - results_df['standard_cost_ci_lower'],
              results_df['standard_cost_ci_upper'] - results_df['standard_mean_cost']],
        fmt='-s', capsize=5, label='AG Estándar', linewidth=2
    )
    plt.errorbar(
        results_df['num_clients'], 
        results_df['intensive_mean_cost'],
        yerr=[results_df['intensive_mean_cost'] - results_df['intensive_cost_ci_lower'],
              results_df['intensive_cost_ci_upper'] - results_df['intensive_mean_cost']],
        fmt='-^', capsize=5, label='AG Intensivo', linewidth=2
    )
    plt.errorbar(
        results_df['num_clients'], 
        results_df['vns_mean_cost'],
        yerr=[results_df['vns_mean_cost'] - results_df['vns_cost_ci_lower'],
              results_df['vns_cost_ci_upper'] - results_df['vns_mean_cost']],
        fmt='-D', capsize=5, label='VNS Solver', linewidth=2, color='purple'
    )
    plt.title('Costo total vs. Número de clientes')
    plt.xlabel('Número de clientes')
    plt.ylabel('Costo total')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig(f"{output_dir}/cost_vs_clients.png", dpi=300, bbox_inches='tight')
    
    # 2. Gráfico de barras: mejora porcentual respecto a AG estándar
    plt.figure(figsize=(12, 7))
    x = range(len(results_df))
    width = 0.4
    plt.bar([i - width/2 for i in x], results_df['intensive_mean_improvement'], 
            width=width, label='AG Intensivo', alpha=0.7)
    plt.bar([i + width/2 for i in x], results_df['vns_mean_improvement'], 
            width=width, label='VNS Solver', alpha=0.7, color='purple')
    plt.axhline(y=10, color='r', linestyle='--', label='Umbral de éxito (10%)')
    plt.xticks(x, results_df['num_clients'])
    plt.title('Mejora porcentual respecto a AG Estándar')
    plt.xlabel('Número de clientes')
    plt.ylabel('Mejora (%)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(f"{output_dir}/improvement_percentage.png", dpi=300, bbox_inches='tight')
    
    # 3. Gráfico de tiempo de cómputo
    plt.figure(figsize=(12, 8))
    plt.plot(results_df['num_clients'], results_df['standard_mean_time'], 
             '-s', label='AG Estándar', linewidth=2)
    plt.plot(results_df['num_clients'], results_df['intensive_mean_time'], 
             '-^', label='AG Intensivo', linewidth=2)
    plt.plot(results_df['num_clients'], results_df['vns_mean_time'], 
             '-D', label='VNS Solver', linewidth=2, color='purple')
    plt.title('Tiempo de cómputo vs. Número de clientes')
    plt.xlabel('Número de clientes')
    plt.ylabel('Tiempo (segundos)')
    plt.yscale('log')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig(f"{output_dir}/computation_time.png", dpi=300, bbox_inches='tight')
    
    # 4. Utilización de capacidad
    plt.figure(figsize=(12, 7))
    plt.bar(results_df['num_clients'] - 3, results_df['standard_mean_cap_util'], 
            width=2, label='AG Estándar', alpha=0.7)
    plt.bar(results_df['num_clients'], results_df['intensive_mean_cap_util'], 
            width=2, label='AG Intensivo', alpha=0.7)
    plt.bar(results_df['num_clients'] + 3, results_df['vns_mean_cap_util'], 
            width=2, label='VNS Solver', alpha=0.7, color='purple')
    plt.title('Utilización promedio de capacidad por camión')
    plt.xlabel('Número de clientes')
    plt.ylabel('Utilización de capacidad (%)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(f"{output_dir}/capacity_utilization.png", dpi=300, bbox_inches='tight')
    
    # 5. Número de camiones utilizados
    plt.figure(figsize=(12, 7))
    plt.plot(results_df['num_clients'], results_df['standard_mean_trucks'], 
             '-s', label='AG Estándar', linewidth=2)
    plt.plot(results_df['num_clients'], results_df['intensive_mean_trucks'], 
             '-^', label='AG Intensivo', linewidth=2)
    plt.plot(results_df['num_clients'], results_df['vns_mean_trucks'], 
             '-D', label='VNS Solver', linewidth=2, color='purple')
    plt.plot(results_df['num_clients'], results_df['num_trucks_required'], 
             '--', label='Mínimo teórico', linewidth=1.5, color='red')
    plt.title('Número de camiones utilizados vs. Número de clientes')
    plt.xlabel('Número de clientes')
    plt.ylabel('Número de camiones')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig(f"{output_dir}/trucks_used.png", dpi=300, bbox_inches='tight')
    
    # 6. Análisis de eficiencia: mejora vs. tiempo
    plt.figure(figsize=(12, 8))
    
    # Mapeo entre nombres de métodos y prefijos en el DataFrame
    method_to_prefix = {
        'AG Estándar': 'standard',
        'AG Intensivo': 'intensive',
        'VNS Solver': 'vns'
    }
    
    # Crear un scatter plot multi-método
    methods = ['AG Estándar', 'AG Intensivo', 'VNS Solver']
    colors = ['blue', 'orange', 'purple']
    markers = ['s', '^', 'D']
    
    # Añadir un pequeño valor para evitar división por cero
    epsilon = 1e-10
    
    for i, (method, color, marker) in enumerate(zip(methods, colors, markers)):
        prefix = method_to_prefix[method]
        if i == 0:  # Para AG Estándar (comparación consigo mismo, siempre será 1.0)
            continue  # Saltamos este caso ya que no es informativo
        else:  # Para otros métodos, relativo al estándar
            relative_time = results_df[f'{prefix}_mean_time'] / (results_df['standard_mean_time'] + epsilon)
        
        plt.scatter(
            relative_time,
            results_df[f'{prefix}_mean_improvement'],
            c=color,
            s=100,
            alpha=0.7,
            marker=marker,
            label=method
        )
        
        # Añadir etiquetas para cada punto
        for j, row in results_df.iterrows():
            time_factor = row[f'{prefix}_mean_time'] / (row['standard_mean_time'] + epsilon)
            
            plt.annotate(
                f"{row['num_clients']} cl", 
                (time_factor, row[f'{prefix}_mean_improvement']),
                fontsize=8
            )
    
    plt.axhline(y=10, color='r', linestyle='--', label='Umbral mejora 10%')
    plt.title('Análisis de eficiencia: Mejora vs. Factor de tiempo')
    plt.xlabel('Factor de tiempo (relativo a AG Estándar)')
    plt.ylabel('Mejora respecto a AG Estándar (%)')
    plt.grid(True, alpha=0.3)
    plt.legend(loc='best')
    plt.savefig(f"{output_dir}/efficiency_analysis.png", dpi=300, bbox_inches='tight')
    
    # 7. Comparativa directa AG Intensivo vs VNS
    plt.figure(figsize=(10, 8))
    
    # Calcular diferencia porcentual VNS vs AG Intensivo
    vns_vs_ag = [(results_df['intensive_mean_cost'][i] - results_df['vns_mean_cost'][i]) / 
                 results_df['intensive_mean_cost'][i] * 100 
                 for i in range(len(results_df))]
    
    # Gráfico de barras para comparar VNS vs AG Intensivo
    plt.bar(results_df['num_clients'], vns_vs_ag, color='purple', alpha=0.7,
           label='Mejora de VNS sobre AG Intensivo')
    
    # Línea horizontal en 0%
    plt.axhline(y=0, color='k', linestyle='-', alpha=0.3)
    
    # Añadir etiquetas con valores exactos
    for i, value in enumerate(vns_vs_ag):
        plt.text(results_df['num_clients'][i], value + (0.5 if value > 0 else -1.5), 
                f"{value:.1f}%", ha='center')
    
    plt.title('Comparativa directa: VNS vs AG Intensivo')
    plt.xlabel('Número de clientes')
    plt.ylabel('Mejora relativa de VNS sobre AG Intensivo (%)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig(f"{output_dir}/vns_vs_ag_comparison.png", dpi=300, bbox_inches='tight')
    
def create_optimal_comparison_visualizations(results_df, output_dir="optimal_comparison_results"):
    """Crea visualizaciones para la comparación con la solución óptima."""
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Gráfico de barras: gap respecto al óptimo
    plt.figure(figsize=(12, 7))
    x = range(len(results_df))
    width = 0.25
    plt.bar([i - width for i in x], results_df['standard_mean_gap'], 
            width=width, label='AG Estándar', alpha=0.7)
    plt.bar([i for i in x], results_df['intensive_mean_gap'], 
            width=width, label='AG Intensivo', alpha=0.7)
    plt.bar([i + width for i in x], results_df['vns_mean_gap'], 
            width=width, label='VNS Solver', alpha=0.7, color='purple')
    plt.axhline(y=5, color='r', linestyle='--', label='Gap aceptable (5%)')
    plt.xticks(x, results_df['num_clients'])
    plt.title('Gap porcentual respecto a la solución óptima')
    plt.xlabel('Número de clientes')
    plt.ylabel('Gap (%)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(f"{output_dir}/gap_vs_optimal.png", dpi=300, bbox_inches='tight')
    
    # 2. Gráfico de líneas: costo vs. número de clientes (incluyendo óptimo)
    plt.figure(figsize=(12, 8))
    plt.plot(results_df['num_clients'], results_df['optimal_cost'], 
             '-*', label='Óptimo', linewidth=2, color='green')
    plt.plot(results_df['num_clients'], results_df['standard_mean_cost'], 
             '-s', label='AG Estándar', linewidth=2)
    plt.plot(results_df['num_clients'], results_df['intensive_mean_cost'], 
             '-^', label='AG Intensivo', linewidth=2)
    plt.plot(results_df['num_clients'], results_df['vns_mean_cost'], 
             '-D', label='VNS Solver', linewidth=2, color='purple')
    plt.title('Costo total vs. Número de clientes (incluyendo óptimo)')
    plt.xlabel('Número de clientes')
    plt.ylabel('Costo total')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig(f"{output_dir}/cost_vs_clients_with_optimal.png", dpi=300, bbox_inches='tight')
    
    # 3. Tiempo para encontrar la solución óptima vs. tiempo de heurísticas
    plt.figure(figsize=(12, 7))
    plt.semilogy(results_df['num_clients'], results_df['optimal_time'], 
                '-o', linewidth=2, color='green', label='Óptimo (fuerza bruta)')
    plt.semilogy(results_df['num_clients'], results_df['standard_mean_time'], 
                '-s', linewidth=2, label='AG Estándar')
    plt.semilogy(results_df['num_clients'], results_df['intensive_mean_time'], 
                '-^', linewidth=2, label='AG Intensivo')
    plt.semilogy(results_df['num_clients'], results_df['vns_mean_time'], 
                '-D', linewidth=2, color='purple', label='VNS Solver')
    plt.title('Tiempo de cómputo (escala logarítmica)')
    plt.xlabel('Número de clientes')
    plt.ylabel('Tiempo (segundos)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig(f"{output_dir}/computation_time_comparison.png", dpi=300, bbox_inches='tight')
    
    # 4. Gráfico de "proporción costo/óptimo"
    plt.figure(figsize=(12, 7))
    plt.plot(results_df['num_clients'], results_df['standard_mean_cost'] / results_df['optimal_cost'], 
             '-s', label='AG Estándar', linewidth=2)
    plt.plot(results_df['num_clients'], results_df['intensive_mean_cost'] / results_df['optimal_cost'], 
             '-^', label='AG Intensivo', linewidth=2)
    plt.plot(results_df['num_clients'], results_df['vns_mean_cost'] / results_df['optimal_cost'], 
             '-D', label='VNS Solver', linewidth=2, color='purple')
    plt.axhline(y=1, color='green', linestyle='-', label='Óptimo', linewidth=1.5)
    plt.axhline(y=1.05, color='r', linestyle='--', label='5% sobre óptimo', linewidth=1)
    plt.title('Relación entre costo de algoritmos y costo óptimo')
    plt.xlabel('Número de clientes')
    plt.ylabel('Costo / Costo óptimo')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig(f"{output_dir}/cost_ratio_to_optimal.png", dpi=300, bbox_inches='tight')
    
    # 5. Gráfico de frecuencia de alcanzar el óptimo
    optimal_frequency = {
        'AG Estándar': [],
        'AG Intensivo': [],
        'VNS Solver': []
    }
    
    # Calcular para cada instancia la frecuencia con que cada algoritmo alcanza el óptimo
    for i, row in results_df.iterrows():
        optimal_cost = row['optimal_cost']
        tolerance = 1e-6  # Tolerancia numérica pequeña
        
        # Contar cuántas veces cada algoritmo alcanza el óptimo
        standard_freq = sum(1 for cost in row['standard_raw_costs'] if abs(cost - optimal_cost) < tolerance) / len(row['standard_raw_costs'])
        intensive_freq = sum(1 for cost in row['intensive_raw_costs'] if abs(cost - optimal_cost) < tolerance) / len(row['intensive_raw_costs'])
        vns_freq = sum(1 for cost in row['vns_raw_costs'] if abs(cost - optimal_cost) < tolerance) / len(row['vns_raw_costs'])
        
        optimal_frequency['AG Estándar'].append(standard_freq * 100)
        optimal_frequency['AG Intensivo'].append(intensive_freq * 100)
        optimal_frequency['VNS Solver'].append(vns_freq * 100)
    
    # Gráfico de barras para la frecuencia de alcanzar el óptimo
    plt.figure(figsize=(12, 7))
    x = range(len(results_df))
    width = 0.25
    plt.bar([i - width for i in x], optimal_frequency['AG Estándar'], 
            width=width, label='AG Estándar', alpha=0.7)
    plt.bar([i for i in x], optimal_frequency['AG Intensivo'], 
            width=width, label='AG Intensivo', alpha=0.7)
    plt.bar([i + width for i in x], optimal_frequency['VNS Solver'], 
            width=width, label='VNS Solver', alpha=0.7, color='purple')
    plt.xticks(x, results_df['num_clients'])
    plt.title('Frecuencia de alcanzar la solución óptima')
    plt.xlabel('Número de clientes')
    plt.ylabel('Frecuencia (%)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(f"{output_dir}/optimal_solution_frequency.png", dpi=300, bbox_inches='tight')

def find_optimal_solution(dist_matrix, demands, truck_capacity):
    """
    Encuentra la solución óptima para el VRP mediante fuerza bruta.
    Solo viable para instancias pequeñas (≤ 7-8 clientes).
    """
    from itertools import permutations
    import time
    
    print(f"Buscando solución óptima para {len(dist_matrix)-1} clientes...")
    t_start = time.time()
    
    n = len(dist_matrix)
    clients = list(range(1, n))  # Excluye el depósito (0)
    
    best_cost = float('inf')
    best_routes = []
    
    # Generar todas las permutaciones posibles de clientes
    total_perms = math.factorial(len(clients))
    print(f"Evaluando {total_perms} permutaciones posibles...")
    
    for p in tqdm(permutations(clients), total=total_perms, desc="Búsqueda óptima"):
        # Intentar construir rutas factibles con esta permutación
        routes = []
        current_route = []
        load = 0
        
        for client in p:
            if load + demands[client] <= truck_capacity:
                current_route.append(client)
                load += demands[client]
            else:
                if current_route:  # Si la ruta tiene al menos un cliente
                    routes.append(current_route)
                current_route = [client]
                load = demands[client]
        
        if current_route:  # Añadir la última ruta si no está vacía
            routes.append(current_route)
        
        # Calcular costo
        cost = compute_total_distance(routes, dist_matrix)
        
        # Actualizar si encontramos una solución mejor
        if cost < best_cost:
            best_cost = cost
            best_routes = routes.copy()
    
    t_elapsed = time.time() - t_start
    print(f"Solución óptima encontrada en {t_elapsed:.2f} segundos.")
    print(f"Costo óptimo: {best_cost:.2f}, Rutas: {len(best_routes)}")
    
    return best_routes, best_cost

def run_comparison_with_optimal(G, small_client_counts, truck_capacity=30, n_runs=5, n_boot=1000, ci_level=0.95):
    """
    Ejecuta experimentos comparando con la solución óptima para instancias pequeñas.
    """
    results = []
    
    for num_clients in small_client_counts:
        print(f"\nEjecutando experimentos con {num_clients} clientes (comparación con óptimo)...")
        
        # Generar instancia
        instance = generate_real_instance(G, num_clients)
        dist_matrix = instance['dist_matrix']
        demands = instance['demands']
        
        # Configurar camiones
        num_trucks = max(1, int(np.ceil(sum(demands) / truck_capacity)))
        truck_capacities = [truck_capacity] * num_trucks
        
        # Encontrar solución óptima
        t0 = time.time()
        optimal_routes, optimal_cost = find_optimal_solution(dist_matrix, demands, truck_capacity)
        optimal_time = time.time() - t0
        
        # Calcular utilización de capacidad para la solución óptima
        optimal_trucks = len(optimal_routes)
        total_used = 0
        for route in optimal_routes:
            route_demand = sum(demands[i] for i in route)
            total_used += route_demand
        optimal_cap_util = total_used / (optimal_trucks * truck_capacity) * 100
        
        # 1. AG con parámetros estándar
        standard_times, standard_costs, standard_trucks, standard_cap_util = [], [], [], []
        for run in tqdm(range(n_runs), desc="AG Estándar"):
            t0 = time.time()
            routes = ag_solver.solve_vrp(
                dist_matrix, demands, truck_capacities,
                pop_size=100,
                sel_size=20,
                max_gen=200,
                no_improve_limit=20,
                mut_rate=0.3
            )
            standard_times.append(time.time() - t0)
            standard_costs.append(compute_total_distance(routes, dist_matrix))
            standard_trucks.append(len(routes))
            
            # Calcular utilización de capacidad
            total_used = 0
            for route in routes:
                route_demand = sum(demands[i] for i in route)
                total_used += route_demand
            cap_util = total_used / (len(routes) * truck_capacity) * 100
            standard_cap_util.append(cap_util)
        
        # 2. AG con parámetros intensivos
        intensive_times, intensive_costs, intensive_trucks, intensive_cap_util = [], [], [], []
        for run in tqdm(range(n_runs), desc="AG Intensivo"):
            t0 = time.time()
            routes = ag_solver.solve_vrp(
                dist_matrix, demands, truck_capacities,
                pop_size=500,
                sel_size=100,
                max_gen=500,
                no_improve_limit=30,
                mut_rate=0.3
            )
            intensive_times.append(time.time() - t0)
            intensive_costs.append(compute_total_distance(routes, dist_matrix))
            intensive_trucks.append(len(routes))
            
            # Calcular utilización de capacidad
            total_used = 0
            for route in routes:
                route_demand = sum(demands[i] for i in route)
                total_used += route_demand
            cap_util = total_used / (len(routes) * truck_capacity) * 100
            intensive_cap_util.append(cap_util)
        
        # 3. VNS solver
        vns_times, vns_costs, vns_trucks, vns_cap_util = [], [], [], []
        for run in tqdm(range(n_runs), desc="VNS Solver"):
            t0 = time.time()
            routes = vns_solver.vns_hetero_simplified(
                dist_matrix, 
                demands, 
                truck_capacities,
                max_iterations=2000,  
                time_limit=200.0
            )
            vns_times.append(time.time() - t0)
            vns_costs.append(compute_total_distance(routes, dist_matrix))
            vns_trucks.append(len(routes))
            
            # Calcular utilización de capacidad
            total_used = 0
            for route in routes:
                route_demand = sum(demands[i] for i in route)
                total_used += route_demand
            cap_util = total_used / (len(routes) * truck_capacity) * 100
            vns_cap_util.append(cap_util)
        
        # Bootstrapping para intervalos de confianza
        standard_cost_ci = bootstrap_ci(standard_costs, n_boot, ci_level)
        intensive_cost_ci = bootstrap_ci(intensive_costs, n_boot, ci_level)
        vns_cost_ci = bootstrap_ci(vns_costs, n_boot, ci_level)
        
        # Calcular gap respecto al óptimo
        standard_gap = [(s - optimal_cost) / optimal_cost * 100 for s in standard_costs]
        intensive_gap = [(i - optimal_cost) / optimal_cost * 100 for i in intensive_costs]
        vns_gap = [(v - optimal_cost) / optimal_cost * 100 for v in vns_costs]
        
        results.append({
            'num_clients': num_clients,
            'total_demand': sum(demands[1:]),
            'truck_capacity': truck_capacity,
            'num_trucks_required': num_trucks,
            
            # Óptimo
            'optimal_cost': optimal_cost,
            'optimal_time': optimal_time,
            'optimal_trucks': optimal_trucks,
            'optimal_cap_util': optimal_cap_util,
            
            # AG Estándar
            'standard_mean_cost': np.mean(standard_costs),
            'standard_cost_ci_lower': standard_cost_ci[0],
            'standard_cost_ci_upper': standard_cost_ci[1],
            'standard_mean_time': np.mean(standard_times),
            'standard_mean_trucks': np.mean(standard_trucks),
            'standard_mean_cap_util': np.mean(standard_cap_util),
            'standard_mean_gap': np.mean(standard_gap),
            'standard_raw_costs': standard_costs,
            'standard_raw_times': standard_times,
            'standard_raw_gaps': standard_gap,
            
            # AG Intensivo
            'intensive_mean_cost': np.mean(intensive_costs),
            'intensive_cost_ci_lower': intensive_cost_ci[0],
            'intensive_cost_ci_upper': intensive_cost_ci[1],
            'intensive_mean_time': np.mean(intensive_times),
            'intensive_mean_trucks': np.mean(intensive_trucks),
            'intensive_mean_cap_util': np.mean(intensive_cap_util),
            'intensive_mean_gap': np.mean(intensive_gap),
            'intensive_raw_costs': intensive_costs,
            'intensive_raw_times': intensive_times,
            'intensive_raw_gaps': intensive_gap,
            
            # VNS
            'vns_mean_cost': np.mean(vns_costs),
            'vns_cost_ci_lower': vns_cost_ci[0],
            'vns_cost_ci_upper': vns_cost_ci[1],
            'vns_mean_time': np.mean(vns_times),
            'vns_mean_trucks': np.mean(vns_trucks),
            'vns_mean_cap_util': np.mean(vns_cap_util),
            'vns_mean_gap': np.mean(vns_gap),
            'vns_raw_costs': vns_costs,
            'vns_raw_times': vns_times,
            'vns_raw_gaps': vns_gap
        })
    
    return pd.DataFrame(results)


# 5. FUNCIÓN PRINCIPAL
def main():
    # Cargar o crear grafo de La Habana
    G = load_havana_graph()
    
    # Definir número de clientes para cada prueba
    client_counts = [20, 50, 100, 150]  # Instancias grandes para AG vs VNS
    small_client_counts = [3, 4, 5, 6, 7]  # Instancias pequeñas para comparar con óptimo
    
    # PARTE 1: Experimentos de escalabilidad AG vs VNS
    print("\n=== EJECUTANDO EXPERIMENTOS DE ESCALABILIDAD AG VS VNS ===")
    results = run_scalability_experiments(
        G, client_counts, truck_capacity=30, n_runs=5, n_boot=1000, ci_level=0.95
    )
    
    # Guardar resultados
    os.makedirs('scalability_results', exist_ok=True)
    results.to_csv('scalability_results/havana_scalability_ag_vs_vns.csv', index=False)
    
    # Crear visualizaciones
    create_scalability_visualizations(results)
    
    # PARTE 2: Experimentos con comparación con el óptimo
    print("\n=== EJECUTANDO EXPERIMENTOS DE COMPARACIÓN CON EL ÓPTIMO ===")
    optimal_results = run_comparison_with_optimal(
        G, small_client_counts, truck_capacity=30, n_runs=5, n_boot=1000, ci_level=0.95
    )
    
    # Guardar resultados de comparación con óptimo
    optimal_results.to_csv('scalability_results/havana_comparison_with_optimal.csv', index=False)
    
    # Crear visualizaciones de comparación con óptimo
    create_optimal_comparison_visualizations(optimal_results, output_dir="scalability_results/optimal_comparison")
    
    print("\nExperimentos completados. Resultados guardados en 'scalability_results/'")

if __name__ == "__main__":
    main()

