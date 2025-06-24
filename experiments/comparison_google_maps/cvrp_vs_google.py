import sys
import os
import time
import logging
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import multiprocessing as mp
from functools import partial
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from scipy.stats import wilcoxon, ttest_rel
from tqdm import tqdm
import requests
import googlemaps  # Necesitarás instalar esta biblioteca

# Configurar correctamente las rutas de importación
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.append(str(PROJECT_ROOT))  # Ruta raíz del proyecto
sys.path.append(str(PROJECT_ROOT / "src"))  # Carpeta src

# Agregar todas las rutas necesarias para los módulos usados por optimized_route.py
sys.path.append(str(PROJECT_ROOT / "src/traffic_events"))
sys.path.append(str(PROJECT_ROOT / "src/crawler"))
sys.path.append(str(PROJECT_ROOT / "src/weather"))
sys.path.append(str(PROJECT_ROOT / "src/metaheuristic/ag_solver"))
sys.path.append(str(PROJECT_ROOT / "src/metaheuristic/vns_solver"))
sys.path.append(str(PROJECT_ROOT / "src/metaheuristic/sa_solver"))
sys.path.append(str(PROJECT_ROOT / "src/metaheuristic/ts_solver"))

# Ahora importa optimized_route
from src.optimized_route import optimize_delivery_routes, validate_node_connectivity

# Configuración básica
BASE_DIR = PROJECT_ROOT  # Base para rutas absolutas en el resto del script

# Configuración del experimento
CONFIG = {
    'client_counts': [5, 10, 15, 20],  # Diferentes tamaños de instancias
    'truck_capacity': 100,
    'truck_capacities': [50, 100, 150],  # Diferentes capacidades
    'n_runs': 10,  # Número de ejecuciones por instancia
    'seed_base': 42,
    'results_dir': PROJECT_ROOT / "experiments" / "comparison_google_maps" / "results",
    'graph_file': "479c34c9f9679cb8467293e0403a0250c7ef8556.json",  # Tu grafo de La Habana
    'google_api_key': "TU_API_KEY_AQUI",  
    'scenarios': [
        {'name': 'urbano_denso', 'area': 'centro', 'traffic': 'heavy'},
        {'name': 'urbano_normal', 'area': 'centro', 'traffic': 'normal'},
        {'name': 'suburbano', 'area': 'periferia', 'traffic': 'light'},
        {'name': 'mixto', 'area': 'mixto', 'traffic': 'mixed'}
    ]
}

# Asegurarse de que existe el directorio de resultados
os.makedirs(CONFIG['results_dir'], exist_ok=True)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(CONFIG['results_dir'] / "experiment.log"),
        logging.StreamHandler()
    ]
)

def initialize_google_maps_client(api_key):
    """Inicializa el cliente de Google Maps"""
    return googlemaps.Client(key=api_key)

def get_google_maps_route(gmaps_client, origin, destination, waypoints=None, mode='driving'):
    """
    Obtiene una ruta de Google Maps API
    
    Args:
        gmaps_client: Cliente de Google Maps
        origin: Coordenadas (lat, lng) de origen
        destination: Coordenadas (lat, lng) de destino
        waypoints: Lista de puntos intermedios (opcional)
        mode: Modo de transporte ('driving', 'walking', etc.)
        
    Returns:
        (ruta, distancia, tiempo)
    """
    try:
        # Convertir coordenadas a formato adecuado
        origin_str = f"{origin[0]},{origin[1]}"
        destination_str = f"{destination[0]},{destination[1]}"
        
        # Preparar waypoints si existen
        waypoints_str = None
        if waypoints:
            waypoints_str = [f"{wp[0]},{wp[1]}" for wp in waypoints]
        
        # Hacer la solicitud a Google Maps
        directions_result = gmaps_client.directions(
            origin=origin_str,
            destination=destination_str,
            waypoints=waypoints_str,
            mode=mode,
            optimize_waypoints=True  # Esto es importante para VRP
        )
        
        if not directions_result:
            return None, 0, 0
        
        # Extraer información
        route = directions_result[0]
        distance = route['legs'][0]['distance']['value']  # en metros
        duration = route['legs'][0]['duration']['value']  # en segundos
        
        # Extraer coordenadas de la ruta
        path = []
        for step in route['legs'][0]['steps']:
            path.append((step['start_location']['lat'], step['start_location']['lng']))
        path.append((route['legs'][0]['steps'][-1]['end_location']['lat'], 
                    route['legs'][0]['steps'][-1]['end_location']['lng']))
        
        return path, distance, duration
    
    except Exception as e:
        logging.error(f"Error en solicitud a Google Maps: {e}")
        return None, 0, 0

def optimize_route_with_google_maps(gmaps_client, depot, targets):
    """
    Optimiza una ruta usando Google Maps Directions API
    
    Args:
        gmaps_client: Cliente de Google Maps
        depot: Punto de depósito (lat, lng)
        targets: Lista de puntos objetivo [(lat, lng), ...]
        
    Returns:
        (ruta_optimizada, distancia_total, tiempo_total)
    """
    if not targets:
        return [], 0, 0
    
    try:
        # Para un solo objetivo, es una ruta simple
        if len(targets) == 1:
            path, distance, duration = get_google_maps_route(gmaps_client, depot, targets[0])
            return_path, return_distance, return_duration = get_google_maps_route(
                gmaps_client, targets[0], depot)
            
            if path and return_path:
                # Combinar ida y vuelta
                full_path = path + return_path[1:]  # Evitar duplicar el punto de conexión
                total_distance = distance + return_distance
                total_duration = duration + return_duration
                return full_path, total_distance, total_duration
            else:
                return [], 0, 0
        
        # Para múltiples objetivos, usar waypoints
        # Google Maps tiene límite de 23 waypoints en API básica (25 puntos total)
        if len(targets) > 23:
            logging.warning(f"Demasiados waypoints ({len(targets)}), limitando a 23")
            targets = targets[:23]
        
        # Solicitar ruta con optimización de waypoints
        directions_result = gmaps_client.directions(
            origin=f"{depot[0]},{depot[1]}",
            destination=f"{depot[0]},{depot[1]}",
            waypoints=[f"{t[0]},{t[1]}" for t in targets],
            mode="driving",
            optimize_waypoints=True
        )
        
        if not directions_result:
            return [], 0, 0
        
        # Extraer información
        route = directions_result[0]
        total_distance = sum(leg['distance']['value'] for leg in route['legs'])
        total_duration = sum(leg['duration']['value'] for leg in route['legs'])
        
        # Extraer el camino completo
        path = []
        for leg in route['legs']:
            if not path:
                # Agregar punto inicial del primer tramo
                start = leg['start_location']
                path.append((start['lat'], start['lng']))
            
            # Agregar pasos intermedios
            for step in leg['steps']:
                path.append((step['end_location']['lat'], step['end_location']['lng']))
        
        return path, total_distance, total_duration
    
    except Exception as e:
        logging.error(f"Error optimizando con Google Maps: {e}")
        return [], 0, 0

def load_havana_graph(filename=None):
    """Carga el grafo de La Habana desde un archivo JSON"""
    if filename is None:
        filename = CONFIG['graph_file']
    
    filepath = PROJECT_ROOT / "cache" / filename
    
    if not filepath.exists():
        logging.error(f"Archivo de grafo no encontrado: {filepath}")
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
        
        G = nx.Graph()
        
        # Procesar nodos
        for node in graph_data['nodes']:
            node_id = node['id']
            G.add_node(node_id, lat=node.get('lat'), lon=node.get('lon'))
        
        # Procesar aristas
        for edge in graph_data['edges']:
            source = edge['source']
            target = edge['target']
            weight = edge.get('weight', 1.0)
            G.add_edge(source, target, weight=weight)
            
            # Agregar atributos adicionales si están disponibles
            if 'highway' in edge:
                G[source][target]['highway'] = edge['highway']
            if 'lanes' in edge:
                G[source][target]['lanes'] = edge['lanes']
            if 'surface' in edge:
                G[source][target]['surface'] = edge['surface']
        
        return G
    
    except Exception as e:
        logging.error(f"Error cargando grafo: {e}")
        return None

def generate_test_instance(G, num_clients, scenario, seed=42):
    """
    Genera una instancia de prueba basada en el escenario
    
    Args:
        G: Grafo de NetworkX
        num_clients: Número de clientes a generar
        scenario: Diccionario con parámetros del escenario
        seed: Semilla aleatoria
        
    Returns:
        Diccionario con la instancia
    """
    random.seed(seed)
    np.random.seed(seed)
    
    # Obtener todos los nodos del grafo
    all_nodes = list(G.nodes())
    
    # Filtrar según el área del escenario
    area = scenario['area']
    if area == 'centro':
        # Seleccionar nodos más céntricos (por ejemplo, usando cercanía)
        centrality = nx.closeness_centrality(G)
        nodes_by_centrality = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        candidate_nodes = [node for node, _ in nodes_by_centrality[:int(len(all_nodes) * 0.3)]]
    elif area == 'periferia':
        # Seleccionar nodos periféricos
        centrality = nx.closeness_centrality(G)
        nodes_by_centrality = sorted(centrality.items(), key=lambda x: x[1])
        candidate_nodes = [node for node, _ in nodes_by_centrality[:int(len(all_nodes) * 0.3)]]
    else:  # mixto
        candidate_nodes = all_nodes
    
    # Seleccionar depósito (preferiblemente céntrico)
    centrality = nx.closeness_centrality(G)
    depot_candidates = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:10]
    depot = random.choice([node for node, _ in depot_candidates])
    
    # Seleccionar clientes
    clients = []
    while len(clients) < num_clients:
        candidate = random.choice(candidate_nodes)
        # Verificar que el cliente sea alcanzable desde el depósito
        if nx.has_path(G, depot, candidate) and candidate != depot and candidate not in clients:
            clients.append(candidate)
    
    # Generar demandas según el tipo de tráfico
    traffic = scenario['traffic']
    if traffic == 'heavy':
        # Demandas altas y variables
        demands = [random.randint(20, 80) for _ in range(num_clients)]
    elif traffic == 'light':
        # Demandas más bajas
        demands = [random.randint(5, 30) for _ in range(num_clients)]
    else:  # normal o mixed
        demands = [random.randint(10, 50) for _ in range(num_clients)]
    
    # Calcular capacidades necesarias
    total_demand = sum(demands)
    truck_capacity = CONFIG['truck_capacity']
    num_trucks = max(1, int(np.ceil(total_demand / truck_capacity)))
    
    # Generar coordenadas para la API de Google Maps
    depot_coords = (G.nodes[depot].get('lat', 0), G.nodes[depot].get('lon', 0))
    client_coords = [(G.nodes[c].get('lat', 0), G.nodes[c].get('lon', 0)) for c in clients]
    
    return {
        'depot': depot,
        'clients': clients,
        'demands': demands,
        'num_trucks': num_trucks,
        'truck_capacity': truck_capacity,
        'depot_coords': depot_coords,
        'client_coords': client_coords,
        'scenario': scenario['name']
    }

def run_single_comparison(instance, gmaps_client, n_runs=3):
    """
    Compara optimizadores CVRP con Google Maps para una instancia
    
    Args:
        instance: Diccionario con la instancia de prueba
        gmaps_client: Cliente de Google Maps
        n_runs: Número de ejecuciones
        
    Returns:
        Diccionario con resultados
    """
    depot = instance['depot']
    clients = instance['clients']
    demands = instance['demands']
    num_trucks = instance['num_trucks']
    truck_capacity = instance['truck_capacity']
    truck_capacities = [truck_capacity] * num_trucks
    
    depot_coords = instance['depot_coords']
    client_coords = instance['client_coords']
    
    # Cargar el grafo
    G = load_havana_graph()
    if not G:
        logging.error("No se pudo cargar el grafo")
        return None
    
    results = {
        'instance_size': len(clients),
        'scenario': instance['scenario'],
        'num_trucks': num_trucks,
        'total_demand': sum(demands),
        'truck_capacity': truck_capacity
    }
    
    # 1. Google Maps (una sola vez, ya que no es estocástico)
    t0 = time.time()
    google_path, google_distance, google_duration = optimize_route_with_google_maps(
        gmaps_client, depot_coords, client_coords)
    google_time = time.time() - t0
    
    # Convertir metros a km
    google_distance_km = google_distance / 1000
    
    results['google_distance'] = google_distance_km
    results['google_time'] = google_time
    results['google_duration'] = google_duration
    
    # 2. Optimizadores propios
    optimizers = [
        ('vns_solver', 'vns_solver'),
        ('ts_solver', 'ts_solver'),
        ('sa_solver', 'sa_solver'),
        ('ag_solver', 'ag_solver')
    ]
    
    for name, solver_id in optimizers:
        distances = []
        times = []
        
        for run in range(n_runs):
            t0 = time.time()
            routes, total_cost = optimize_delivery_routes(
                street_graph=G,
                start_point=depot,
                target_points=clients,
                num_trucks=num_trucks,
                truck_capacities=truck_capacities,
                target_demands=demands,
                use_weather_impact=False,  # Para comparación justa con Google
                use_traffic_impact=False,
                solver=solver_id
            )
            elapsed = time.time() - t0
            
            distances.append(total_cost)
            times.append(elapsed)
        
        results[f'{name}_mean_distance'] = np.mean(distances)
        results[f'{name}_std_distance'] = np.std(distances)
        results[f'{name}_mean_time'] = np.mean(times)
        results[f'{name}_std_time'] = np.std(times)
        results[f'{name}_raw_distances'] = distances
        results[f'{name}_raw_times'] = times
        
        # Calcular proporción respecto a Google Maps
        results[f'{name}_vs_google_ratio'] = np.mean(distances) / google_distance_km
    
    return results

def bootstrap_ci(data, n_boot=1000, ci=0.95):
    """Calcula intervalos de confianza por bootstrapping"""
    if len(data) == 0 or all(np.isnan(x) for x in data):
        return (np.nan, np.nan)
    
    # Filtrar NaNs
    data = [x for x in data if not np.isnan(x)]
    
    if len(data) == 0:
        return (np.nan, np.nan)
    
    # Bootstrap
    means = []
    for _ in range(n_boot):
        sample = np.random.choice(data, size=len(data), replace=True)
        means.append(np.mean(sample))
    
    # Intervalo de confianza
    lower = np.percentile(means, 100 * (1 - ci) / 2)
    upper = np.percentile(means, 100 * (1 + ci) / 2)
    
    return (lower, upper)

def run_statistical_tests(results_df, optimizers):
    """
    Realiza pruebas estadísticas para comparar optimizadores con Google Maps
    
    Args:
        results_df: DataFrame con resultados
        optimizers: Lista de nombres de optimizadores
        
    Returns:
        DataFrame con resultados de pruebas
    """
    test_results = []
    
    # Para cada escenario
    for scenario in results_df['scenario'].unique():
        scenario_data = results_df[results_df['scenario'] == scenario]
        
        # Para cada tamaño de instancia
        for size in scenario_data['instance_size'].unique():
            size_data = scenario_data[scenario_data['instance_size'] == size]
            
            for optimizer in optimizers:
                # Extraer datos para la prueba
                optimizer_distances = []
                google_distances = []
                
                for _, row in size_data.iterrows():
                    google_dist = row['google_distance']
                    for dist in row[f'{optimizer}_raw_distances']:
                        optimizer_distances.append(dist)
                        google_distances.append(google_dist)
                
                if len(optimizer_distances) < 5:
                    # Muy pocos datos para prueba estadística
                    p_value = np.nan
                    result = "Insuficientes datos"
                else:
                    # Prueba de Wilcoxon para muestras pareadas
                    try:
                        _, p_value = wilcoxon(optimizer_distances, google_distances)
                        if p_value < 0.05:
                            # Determinar quién es mejor
                            if np.mean(optimizer_distances) < np.mean(google_distances):
                                result = f"{optimizer} es significativamente mejor"
                            else:
                                result = "Google Maps es significativamente mejor"
                        else:
                            result = "No hay diferencia significativa"
                    except Exception as e:
                        logging.error(f"Error en prueba estadística: {e}")
                        p_value = np.nan
                        result = f"Error: {str(e)}"
                
                # Calcular proporción media
                ratio = np.mean(optimizer_distances) / np.mean(google_distances)
                
                test_results.append({
                    'scenario': scenario,
                    'instance_size': size,
                    'optimizer': optimizer,
                    'p_value': p_value,
                    'result': result,
                    'mean_ratio': ratio,
                    'optimizer_mean': np.mean(optimizer_distances),
                    'google_mean': np.mean(google_distances)
                })
    
    return pd.DataFrame(test_results)

def generate_visualizations(results_df, test_results_df, output_dir):
    """Genera visualizaciones para los resultados"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Gráfico de barras: Ratio de distancia respecto a Google Maps por escenario
    plt.figure(figsize=(12, 8))
    scenarios = results_df['scenario'].unique()
    optimizers = ['vns_solver', 'ts_solver', 'sa_solver', 'ag_solver']
    optimizer_names = ['VNS', 'Tabu Search', 'Simulated Annealing', 'Genetic Algorithm']
    
    bar_width = 0.2
    index = np.arange(len(scenarios))
    
    for i, optimizer in enumerate(optimizers):
        ratios = []
        for scenario in scenarios:
            scenario_data = results_df[results_df['scenario'] == scenario]
            ratio = scenario_data[f'{optimizer}_vs_google_ratio'].mean()
            ratios.append(ratio)
        
        plt.bar(index + i * bar_width, ratios, bar_width, 
                label=optimizer_names[i], alpha=0.7)
    
    plt.axhline(y=1.0, color='r', linestyle='--', alpha=0.5, label='Google Maps (referencia)')
    plt.xlabel('Escenario')
    plt.ylabel('Ratio de Distancia (Optimizador / Google Maps)')
    plt.title('Comparación de Optimizadores vs Google Maps por Escenario')
    plt.xticks(index + bar_width * 1.5, scenarios)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{output_dir}/ratio_by_scenario.png", dpi=300)
    plt.close()
    
    # 2. Gráfico de líneas: Tiempo de ejecución vs tamaño de instancia
    plt.figure(figsize=(12, 8))
    sizes = sorted(results_df['instance_size'].unique())
    
    for i, optimizer in enumerate(optimizers):
        times = []
        for size in sizes:
            size_data = results_df[results_df['instance_size'] == size]
            time_mean = size_data[f'{optimizer}_mean_time'].mean()
            times.append(time_mean)
        
        plt.plot(sizes, times, marker='o', linewidth=2, label=optimizer_names[i])
    
    # Google Maps como referencia
    google_times = []
    for size in sizes:
        size_data = results_df[results_df['instance_size'] == size]
        google_time = size_data['google_time'].mean()
        google_times.append(google_time)
    
    plt.plot(sizes, google_times, marker='s', linewidth=2, 
             color='red', label='Google Maps API')
    
    plt.xlabel('Número de Clientes')
    plt.ylabel('Tiempo de Ejecución (segundos)')
    plt.title('Tiempo de Ejecución vs Tamaño de Instancia')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{output_dir}/execution_time.png", dpi=300)
    plt.close()
    
    # 3. Mapa de calor: Significancia estadística por escenario y tamaño
    significance_data = {}
    for _, row in test_results_df.iterrows():
        scenario = row['scenario']
        size = row['instance_size']
        optimizer = row['optimizer']
        
        if scenario not in significance_data:
            significance_data[scenario] = {}
        
        if size not in significance_data[scenario]:
            significance_data[scenario][size] = {}
        
        # Codificar resultado en valor numérico
        if "significativamente mejor" in row['result'] and optimizer in row['result']:
            value = 1  # Optimizador mejor
        elif "significativamente mejor" in row['result'] and "Google" in row['result']:
            value = -1  # Google mejor
        else:
            value = 0  # Sin diferencia significativa
    
    # Convertir a matriz para el mapa de calor
    for optimizer in optimizers:
        data = []
        for scenario in scenarios:
            row = []
            for size in sizes:
                try:
                    row.append(significance_data[scenario][size][optimizer])
                except KeyError:
                    row.append(np.nan)
            data.append(row)
        
        plt.figure(figsize=(10, 6))
        plt.imshow(data, cmap='RdYlGn', vmin=-1, vmax=1)
        
        # Configurar etiquetas
        plt.colorbar(ticks=[-1, 0, 1], 
                    label='Significancia Estadística vs Google Maps')
        plt.xticks(np.arange(len(sizes)), sizes)
        plt.yticks(np.arange(len(scenarios)), scenarios)
        plt.xlabel('Número de Clientes')
        plt.ylabel('Escenario')
        plt.title(f'Significancia Estadística: {optimizer_names[optimizers.index(optimizer)]}')
        
        # Anotar valores
        for i in range(len(scenarios)):
            for j in range(len(sizes)):
                try:
                    value = data[i][j]
                    if value == 1:
                        text = "Mejor"
                    elif value == -1:
                        text = "Peor"
                    else:
                        text = "Similar"
                    plt.text(j, i, text, ha="center", va="center", color="black")
                except:
                    pass
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/significance_{optimizer}.png", dpi=300)
        plt.close()

def main():
    """Función principal del experimento"""
    logging.info("Iniciando experimento de comparación CVRP vs Google Maps")
    
    # Inicializar cliente de Google Maps
    gmaps_client = initialize_google_maps_client(CONFIG['google_api_key'])
    if not gmaps_client:
        logging.error("No se pudo inicializar el cliente de Google Maps")
        return
    
    # Cargar grafo
    G = load_havana_graph()
    if not G:
        logging.error("No se pudo cargar el grafo de La Habana")
        return
    
    # Lista para almacenar resultados
    all_results = []
    
    # Para cada escenario
    for scenario in CONFIG['scenarios']:
        logging.info(f"Procesando escenario: {scenario['name']}")
        
        # Para cada tamaño de instancia
        for num_clients in CONFIG['client_counts']:
            logging.info(f"  Tamaño de instancia: {num_clients} clientes")
            
            # Generar varias instancias con diferentes semillas
            for run in range(CONFIG['n_runs']):
                seed = CONFIG['seed_base'] + run
                instance = generate_test_instance(G, num_clients, scenario, seed)
                
                logging.info(f"    Ejecución {run+1}/{CONFIG['n_runs']}")
                result = run_single_comparison(instance, gmaps_client)
                
                if result:
                    all_results.append(result)
    
    # Convertir a DataFrame
    results_df = pd.DataFrame(all_results)
    
    # Guardar resultados
    results_path = CONFIG['results_dir'] / "cvrp_vs_google_results.csv"
    results_df.to_csv(results_path, index=False)
    logging.info(f"Resultados guardados en {results_path}")
    
    # Realizar pruebas estadísticas
    optimizers = ['vns_solver', 'ts_solver', 'sa_solver', 'ag_solver']
    test_results_df = run_statistical_tests(results_df, optimizers)
    
    # Guardar resultados de pruebas estadísticas
    test_results_path = CONFIG['results_dir'] / "statistical_test_results.csv"
    test_results_df.to_csv(test_results_path, index=False)
    logging.info(f"Resultados de pruebas estadísticas guardados en {test_results_path}")
    
    # Generar visualizaciones
    viz_dir = CONFIG['results_dir'] / "visualizations"
    generate_visualizations(results_df, test_results_df, viz_dir)
    logging.info(f"Visualizaciones generadas en {viz_dir}")
    
    logging.info("Experimento completado")

if __name__ == "__main__":
    main()