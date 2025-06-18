"""
Comparación de metaheurísticas para el VRP (Vehicle Routing Problem)
Este script ejecuta experimentos para comparar diferentes algoritmos.
"""
import sys
import os
import time
import logging
import logging.handlers 
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import multiprocessing as mp
from functools import partial
import io
from contextlib import redirect_stdout, redirect_stderr
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from scipy.stats import wilcoxon
import psutil
from tqdm import tqdm
import math

# Añadir rutas para los solvers
sys.path.append("src/metaheuristic/ag_solver")
sys.path.append("src/metaheuristic/vns_solver") 
sys.path.append("src/metaheuristic/sa_solver") 
sys.path.append("src/metaheuristic/ts_solver")

# ------ PARTE 1: CONFIGURACIÓN BÁSICA ------

# Directorio base
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_BASE = Path(os.environ.get('VRP_PROJECT_ROOT', str(BASE_DIR)))
if ENV_BASE.exists():
    BASE_DIR = ENV_BASE

# Configuración predeterminada ampliada
CONFIG = {
    'client_counts': [n for n in range(5,12)],  
    'truck_capacity': 100,
    'truck_capacities': [50],  # Diferentes capacidades para evaluar
    'n_runs': 10,                         
    'seed_base': 42,
    'results_dir': BASE_DIR / "experiments" / "comparation_results",
    'cache_dir': BASE_DIR / "experiments" / "cache",
    'graph_file': "479c34c9f9679cb8467293e0403a0250c7ef8556.json",
    'parallel': True,
    'n_processes': max(1, mp.cpu_count() - 1),
    'extended_experiments': {
        'run_hetero_fleet': True,       # Flota heterogénea
        'run_demand_patterns': True,    # Patrones de demanda
        'run_parameter_sensitivity': True,  # Análisis de sensibilidad
        'demand_patterns': ['uniform', 'clustered', 'heavy_tailed']
    },
    'viz': {
        'figsize': (10, 6),
        'dpi': 100,
        'style': 'seaborn-v0_8-darkgrid',
        'palette': 'tab10'
    }
}

# Configuración de logging
def setup_logging(log_file: Path):
    """Configura el sistema de logging con soporte para multiprocessing"""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    log_queue = mp.Queue(-1)
    handler = logging.handlers.QueueHandler(log_queue)
    
    root_logger = logging.getLogger()
    root_logger.handlers = []  # Eliminar handlers existentes
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    # Handlers para archivo y consola
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(processName)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    # Queue listener para manejar mensajes de forma segura en multiprocessing
    listener = logging.handlers.QueueListener(log_queue, file_handler, stream_handler)
    listener.start()
    return listener


def haversine(lat1, lon1, lat2, lon2):
    """Calcula la distancia entre dos puntos geográficos en km"""
    R = 6371.0  # Radio de la Tierra en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# ------ PARTE 2: CARGA DE DATOS Y GENERACIÓN DE INSTANCIAS ------
    
    
def load_havana_graph():
    """Carga los datos del mapa desde los archivos de caché y construye el grafo de calles"""
    street_graph = nx.MultiDiGraph()
    all_nodes = []
    street_congestion = {}
    
    # Cargar datos de OSM desde el archivo de caché
    cache_file = os.path.join("cache", "479c34c9f9679cb8467293e0403a0250c7ef8556.json")
    
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
    
    
    print(f"Intentando abrir archivo de caché: {cache_file}")
    with open(cache_file, 'r', encoding='utf-8') as f:
        osm_data = json.load(f)
        
    # Extraer nodos y crear grafo
    nodes = {}
    for element in osm_data.get('elements', []):
        if element.get('type') == 'node':
            node_id = element.get('id')
            lat = element.get('lat')
            lon = element.get('lon')
            if node_id and lat and lon:
                nodes[node_id] = (float(lat), float(lon)) 
                street_graph.add_node(node_id, lat=float(lat), lon=float(lon))
        
    print(f"Nodos extraídos: {len(nodes)}")
        
    # Extraer vías (ways) y crear aristas
    edge_count = 0
    for element in osm_data.get('elements', []):
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

def generate_real_instance(G: nx.MultiDiGraph, num_clients: int, seed: int) -> Dict[str, Any]:
    """Genera una instancia real del problema VRP"""
    random.seed(seed)
    np.random.seed(seed)
    
    # Seleccionar nodos
    all_nodes = list(G.nodes())
    if len(all_nodes) < num_clients + 1:
        raise ValueError(f"No hay suficientes nodos ({len(all_nodes)}) para {num_clients} clientes")
    
    depot = random.choice(all_nodes)
    candidates = [n for n in all_nodes if n != depot]
    clients = random.sample(candidates, k=num_clients)
    nodes_incl = [depot] + clients
    
    # Calcular matriz de distancias
    n = len(nodes_incl)
    dist_matrix = np.full((n, n), np.inf)
    for i, src in enumerate(nodes_incl):
        dist_matrix[i, i] = 0.0
        lengths = nx.single_source_dijkstra_path_length(G, src, weight='weight')
        for j, tgt in enumerate(nodes_incl):
            if tgt in lengths:
                dist_matrix[i, j] = lengths[tgt]
    
    # Generar demandas (el depósito tiene demanda 0)
    demands = [0] + [random.randint(1, 4) for _ in range(num_clients)]
    
    return {'dist_matrix': dist_matrix, 'demands': demands, 'depot': depot, 'clients': clients}

def generate_real_instance_with_demand_pattern(
    G: nx.MultiDiGraph, 
    num_clients: int, 
    seed: int,
    demand_pattern: str = 'uniform'  # 'uniform', 'clustered', 'heavy_tailed'
) -> Dict[str, Any]:
    """Genera instancia con diferentes patrones de demanda"""
    random.seed(seed)
    np.random.seed(seed)
    
    # Seleccionar nodos
    all_nodes = list(G.nodes())
    depot = random.choice(all_nodes)
    candidates = [n for n in all_nodes if n != depot]
    clients = random.sample(candidates, k=num_clients)
    nodes_incl = [depot] + clients
    
    # Calcular matriz de distancias (como está en el código original)
    n = len(nodes_incl)
    dist_matrix = np.full((n, n), np.inf)
    for i, src in enumerate(nodes_incl):
        dist_matrix[i, i] = 0.0
        lengths = nx.single_source_dijkstra_path_length(G, src, weight='weight')
        for j, tgt in enumerate(nodes_incl):
            if tgt in lengths:
                dist_matrix[i, j] = lengths[tgt]
    
    # Generar demandas según el patrón especificado
    demands = [0]  # Depósito tiene demanda 0
    
    if demand_pattern == 'uniform':
        # Demanda uniforme entre 1 y 4 (como estaba originalmente)
        demands.extend([random.randint(1, 4) for _ in range(num_clients)])
        
    elif demand_pattern == 'clustered':
        # Demandas agrupadas: algunos clientes con demandas altas, otros con bajas
        low_demand = random.sample(range(num_clients), num_clients // 2)
        for i in range(num_clients):
            if i in low_demand:
                demands.append(random.randint(1, 2))
            else:
                demands.append(random.randint(3, 5))
                
    elif demand_pattern == 'heavy_tailed':
        # Distribución con cola pesada: muchos con demanda baja, pocos con muy alta
        for _ in range(num_clients):
            if random.random() < 0.8:  # 80% de clientes
                demands.append(random.randint(1, 2))
            else:  # 20% de clientes
                demands.append(random.randint(5, 8))
    
    return {'dist_matrix': dist_matrix, 'demands': demands, 'depot': depot, 'clients': clients}

# ------ PARTE 3: ALGORITMOS DE RESOLUCIÓN ------

def compute_greedy_solution(dist_matrix: np.ndarray, demands: List[int], truck_capacity: int) -> List[List[int]]:
    """Implementación de un algoritmo greedy para VRP"""
    n = dist_matrix.shape[0]
    remaining = set(range(1, n))
    routes: List[List[int]] = []
    
    while remaining:
        route: List[int] = []
        current = 0  # Depósito
        load = 0
        
        while True:
            feasible = [i for i in remaining 
                        if load + demands[i] <= truck_capacity 
                        and np.isfinite(dist_matrix[current, i])]
            if not feasible:
                break
                
            # Elegir cliente más cercano
            next_node = min(feasible, key=lambda i: dist_matrix[current, i])
            route.append(next_node)
            load += demands[next_node]
            current = next_node
            remaining.remove(next_node)
            
        if not route:
            logging.warning("No se pueden asignar más clientes: posibles clientes no alcanzables o demanda excede capacidad")
            break
            
        routes.append(route)
        
    return routes

def compute_total_distance(routes: List[List[int]], dist_matrix: np.ndarray) -> float:
    """Calcula la distancia total de una solución"""
    total = 0.0
    for route in routes:
        prev = 0  # Depósito
        for node in route:
            total += dist_matrix[prev, node]
            prev = node
        # Volver al depósito
        total += dist_matrix[prev, 0]
    return total

# ------ PARTE 4: WRAPPERS PARA ALGORITMOS EXTERNOS ------

def create_algorithm_wrappers():
    """Crea los wrappers para todos los algoritmos"""
    
    # Importar algoritmos aquí para evitar problemas de pickle
    import ag_solver
    import vns_solver
    import sa_solver
    import ts_solver

    def ag_solver_wrapper(dm, d, tc, **kwargs):
        """Wrapper para algoritmo genético"""
        # Convertir tipos de datos
        dm_list = dm.tolist()
        d_list = [int(x) for x in d]
        tc_list = [int(x) for x in tc]
        
        # Parámetros
        pop_size = kwargs.get('pop_size', 50)
        sel_size = kwargs.get('sel_size', 20)
        max_gen = kwargs.get('max_gen', 100)
        no_improve_limit = kwargs.get('no_improve_limit', 20)
        mut_rate = kwargs.get('mut_rate', 0.3)
        
        # Llamar al solver
        return ag_solver.solve_vrp(
            dist_matrix=dm_list,
            demand=d_list,
            capacity=tc_list,
            pop_size=pop_size,
            sel_size=sel_size,
            max_gen=max_gen,
            no_improve_limit=no_improve_limit,
            mut_rate=mut_rate
        )

    def sa_wrapper(dm, d, tc, **kwargs):
        """Wrapper para SA con captura de salida"""
        N = len(dm)
        T = len(tc)
        max_iter = kwargs.get('max_iter', 1000)
        init_temp = kwargs.get('init_temp', 1000)
        alpha = kwargs.get('alpha', 0.995)
        
        # Parámetros adicionales
        Tf = 0.01
        iterPerTemp = 100
        lambdaPen = 100.0
        maxSeconds = 300.0
        seed = 0
        
        # Capturar stdout/stderr
        buffer_out = io.StringIO()
        buffer_err = io.StringIO()
        
        with redirect_stdout(buffer_out), redirect_stderr(buffer_err):
            result = sa_solver.solve(N, T, tc, d, dm.tolist(), init_temp, Tf, alpha, 
                               iterPerTemp, lambdaPen, maxSeconds, seed)
        
        # Enviar salida capturada al logger
        for line in buffer_out.getvalue().splitlines():
            if line.strip():
                logging.info(f"[SA stdout] {line}")
        
        for line in buffer_err.getvalue().splitlines():
            if line.strip():
                logging.error(f"[SA stderr] {line}")
        
        return result

    # Variante de SA con enfriamiento más rápido
    def sa_fast_wrapper(dm, d, tc, **kwargs):
        """SA con enfriamiento más rápido"""
        N = len(dm)
        T = len(tc)
        max_iter = kwargs.get('max_iter', 1000)
        init_temp = kwargs.get('init_temp', 1000)
        # Alpha más bajo = enfriamiento más rápido
        alpha = 0.95  
        
        Tf = 0.01
        iterPerTemp = 50  # Menos iteraciones por temperatura
        lambdaPen = 100.0
        maxSeconds = 300.0
        seed = 0
        
        buffer_out = io.StringIO()
        buffer_err = io.StringIO()
        
        with redirect_stdout(buffer_out), redirect_stderr(buffer_err):
            result = sa_solver.solve(N, T, tc, d, dm.tolist(), init_temp, Tf, alpha, 
                               iterPerTemp, lambdaPen, maxSeconds, seed)
        
        for line in buffer_out.getvalue().splitlines():
            if line.strip():
                logging.info(f"[SA-Fast stdout] {line}")
        
        for line in buffer_err.getvalue().splitlines():
            if line.strip():
                logging.error(f"[SA-Fast stderr] {line}")
        
        return result

    def ts_wrapper(dm, d, tc, **kwargs):
        """Wrapper para Tabu Search"""
        num_trucks = len(tc)
        max_iter = kwargs.get('max_iter', 1000)
        tabu_tenure = kwargs.get('tabu_tenure', 50)
        
        # Capturar stdout/stderr
        buffer_out = io.StringIO()
        buffer_err = io.StringIO()
        
        with redirect_stdout(buffer_out), redirect_stderr(buffer_err):
            # Convertir tipos
            objectives = np.ones(len(d), dtype=np.int32)
            demands_arr = np.array(d, dtype=np.int32)
            capacities_arr = np.array(tc, dtype=np.int32)
            
            result = ts_solver.solve_vrp(
                dist_matrix=dm.tolist(),
                objectives=objectives,
                demands=demands_arr,
                capacities=capacities_arr,
                num_trucks=num_trucks,
                max_iter=max_iter,
                base_tabu_tenure=tabu_tenure
            )
        
        # Enviar salida capturada al logger
        for line in buffer_out.getvalue().splitlines():
            if line.strip():
                logging.info(f"[TS stdout] {line}")
        
        for line in buffer_err.getvalue().splitlines():
            if line.strip():
                logging.error(f"[TS stderr] {line}")
        
        return result
    
    # Variante de TS con tenure más largo
    def ts_long_wrapper(dm, d, tc, **kwargs):
        """TS con memoria tabu más larga"""
        num_trucks = len(tc)
        max_iter = kwargs.get('max_iter', 1000)
        tabu_tenure = 100  # Tenure más largo
        
        buffer_out = io.StringIO()
        buffer_err = io.StringIO()
        
        with redirect_stdout(buffer_out), redirect_stderr(buffer_err):
            objectives = np.ones(len(d), dtype=np.int32)
            demands_arr = np.array(d, dtype=np.int32)
            capacities_arr = np.array(tc, dtype=np.int32)
            
            result = ts_solver.solve_vrp(
                dist_matrix=dm.tolist(),
                objectives=objectives,
                demands=demands_arr,
                capacities=capacities_arr,
                num_trucks=num_trucks,
                max_iter=max_iter,
                base_tabu_tenure=tabu_tenure
            )
        
        for line in buffer_out.getvalue().splitlines():
            if line.strip():
                logging.info(f"[TS-Long stdout] {line}")
        
        for line in buffer_err.getvalue().splitlines():
            if line.strip():
                logging.error(f"[TS-Long stderr] {line}")
        
        return result
    
    def vns_wrapper(dm, d, tc, **kwargs):
        """Wrapper para VNS básico"""
        # Capturar stdout/stderr
        buffer_out = io.StringIO()
        buffer_err = io.StringIO()
        
        with redirect_stdout(buffer_out), redirect_stderr(buffer_err):
            max_iter = kwargs.get('max_iter', 100)
            time_limit = kwargs.get('time_limit', 30.0)
            
            # Preparar argumentos con el tipo correcto
            dist_matrix_list = dm.tolist() if hasattr(dm, 'tolist') else [[float(cell) for cell in row] for row in dm]
            demands_list = [int(x) for x in d]
            capacities_list = [int(x) for x in tc]
            
            try:
                # Crear una instancia de VNSConfig si está disponible
                if hasattr(vns_solver, 'VNSConfig'):
                    config = vns_solver.VNSConfig()
                    result = vns_solver.vns_hetero_simplified(
                        distance_matrix=dist_matrix_list,
                        demands=demands_list,
                        capacities=capacities_list,
                        max_iterations=int(max_iter),
                        time_limit=float(time_limit),
                        config=config
                    )
                else:
                    result = vns_solver.vns_hetero_simplified(
                        distance_matrix=dist_matrix_list,
                        demands=demands_list,
                        capacities=capacities_list,
                        max_iterations=int(max_iter),
                        time_limit=float(time_limit)
                    )
            except Exception as e:
                logging.error(f"Error en VNS: {e}")
                # Devolver una solución vacía en caso de error
                result = []
        
        # Enviar salida capturada al logger
        for line in buffer_out.getvalue().splitlines():
            if line.strip():
                logging.info(f"[VNS stdout] {line}")
        
        for line in buffer_err.getvalue().splitlines():
            if line.strip():
                logging.error(f"[VNS stderr] {line}")
        
        return result

    def vns_intensive_wrapper(dm, d, tc, **kwargs):
        """VNS con búsqueda más intensiva"""
        buffer_out = io.StringIO()
        buffer_err = io.StringIO()
        
        with redirect_stdout(buffer_out), redirect_stderr(buffer_err):
            max_iter = kwargs.get('max_iter', 200)  # Más iteraciones
            time_limit = kwargs.get('time_limit', 30.0)  # Mayor tiempo límite
            
            # Preparar argumentos con el tipo correcto
            dist_matrix_list = dm.tolist() if hasattr(dm, 'tolist') else [[float(cell) for cell in row] for row in dm]
            demands_list = [int(x) for x in d]
            capacities_list = [int(x) for x in tc]
            
            try:
                # Crear una instancia de VNSConfig si está disponible
                if hasattr(vns_solver, 'VNSConfig'):
                    config = vns_solver.VNSConfig()
                    # Configurar para búsqueda más intensiva
                    if hasattr(config, 'intensification_factor'):
                        config.intensification_factor = 1.5  # Mayor intensificación
                        
                    result = vns_solver.vns_hetero_simplified(
                        distance_matrix=dist_matrix_list,
                        demands=demands_list,
                        capacities=capacities_list,
                        max_iterations=int(max_iter),
                        time_limit=float(time_limit),
                        config=config
                    )
                else:
                    result = vns_solver.vns_hetero_simplified(
                        distance_matrix=dist_matrix_list,
                        demands=demands_list,
                        capacities=capacities_list,
                        max_iterations=int(max_iter),
                        time_limit=float(time_limit)
                    )
            except Exception as e:
                logging.error(f"Error en VNS intensivo: {e}")
                # Devolver una solución vacía en caso de error
                result = []
                
            for line in buffer_out.getvalue().splitlines():
                if line.strip():
                    logging.info(f"[VNS-Intensive stdout] {line}")
            
            for line in buffer_err.getvalue().splitlines():
                if line.strip():
                    logging.error(f"[VNS-Intensive stderr] {line}")
            
            return result

    # Devolver lista de algoritmos con sus wrappers y parámetros
    return [
        ('vns_basic', vns_wrapper, {'max_iter': 100, 'max_no_improve': 20}),
        ('vns_intensive', vns_intensive_wrapper, {'max_iter': 200, 'max_no_improve': 30}),
        ('ag_small', ag_solver_wrapper, {'pop_size':50, 'max_gen':100, 'mut_rate':0.3}),
        ('ag_large', ag_solver_wrapper, {'pop_size':200, 'max_gen':200, 'mut_rate':0.3}),
        ('ag_mut_high', ag_solver_wrapper, {'pop_size':100, 'max_gen':150, 'mut_rate':0.5}),
        ('sa', sa_wrapper, {'max_iter':1000, 'init_temp':1000, 'alpha':0.995}),
        ('sa_fast', sa_fast_wrapper, {'max_iter':1000, 'init_temp':1000}),
        ('ts', ts_wrapper, {'max_iter':1000, 'tabu_tenure':50}),
        ('ts_long', ts_long_wrapper, {'max_iter':1000})
    ]

# ------ PARTE 5: FUNCIONES DE EXPERIMENTACIÓN ------

def bootstrap_ci(data: List[float], n_boot: int = 1000, ci: float = 0.95) -> Tuple[float, float]:
    """Calcula intervalos de confianza mediante bootstrap"""
    arr = np.array(data)
    n = len(arr)
    boot_means = np.empty(n_boot)
    
    for i in range(n_boot):
        sample = np.random.choice(arr, size=n, replace=True)
        boot_means[i] = sample.mean()
        
    alpha = (1 - ci) / 2
    lower = np.percentile(boot_means, 100 * alpha)
    upper = np.percentile(boot_means, 100 * (1 - alpha))
    
    return lower, upper

def run_single_experiment(
    num_clients: int,
    truck_capacity: int,
    seed: int,
    n_runs: int,
    graph_path: Path,
    heterogeneous_fleet: bool = False,
    demand_pattern: str = 'uniform'
) -> Dict[str, Any]:
    """Ejecuta el experimento para un tamaño de instancia y todos los algoritmos"""
    logging.info(f"Iniciando experimento con {num_clients} clientes (seed {seed}, "
                f"flota heterogénea: {heterogeneous_fleet}, patrón: {demand_pattern})")
    
    # Cargar grafo y generar instancia
    G = load_havana_graph()
    
    # Usar el generador apropiado según el patrón de demanda
    if demand_pattern != 'uniform':
        instance = generate_real_instance_with_demand_pattern(G, num_clients, seed, demand_pattern)
    else:
        instance = generate_real_instance(G, num_clients, seed)
    
    # Convertir distancias a kilómetros
    dist_matrix = instance['dist_matrix'] 
    demands = instance['demands']
    
    # Calcular número de camiones necesarios
    total_demand = sum(demands[1:])  # Excluir depósito
    num_trucks = max(1, int(np.ceil(total_demand / truck_capacity)))
    
    # Generar capacidades heterogéneas u homogéneas
    if heterogeneous_fleet:
        # Para flotas heterogéneas: un mix de capacidades
        base_cap = truck_capacity
        truck_caps = []
        # Crear una mezcla de capacidades (70%, 100%, 130% de la capacidad base)
        for i in range(num_trucks):
            if i % 3 == 0:
                truck_caps.append(int(base_cap * 0.7))
            elif i % 3 == 1:
                truck_caps.append(base_cap)
            else:
                truck_caps.append(int(base_cap * 1.3))
    else:
        # Flota homogénea tradicional
        truck_caps = [truck_capacity] * num_trucks
    
    logging.info(f"Instancia: {num_clients} clientes, demanda {total_demand}, "
                f"{num_trucks} camiones, capacidades: {truck_caps}")
    
    # Obtener lista de algoritmos
    algorithms = create_algorithm_wrappers()
    
    # Ejecutar cada algoritmo
    results = {
        'num_clients': num_clients, 
        'total_demand': total_demand, 
        'num_trucks': num_trucks,
        'heterogeneous_fleet': heterogeneous_fleet,
        'demand_pattern': demand_pattern
    }
    
    for alg_name, alg_func, params in algorithms:
        costs, times, num_routes, avg_load_pcts = [], [], [], []
        
        for run in range(n_runs):
            try:
                # Ejecutar algoritmo y medir tiempo
                t0 = time.time()
                routes = alg_func(dist_matrix, demands, truck_caps, **params)
                t1 = time.time()
                
                # Calcular costo (distancia total)
                cost = compute_total_distance(routes, dist_matrix)
                costs.append(cost)
                times.append(t1 - t0)
                
                # Calcular número de rutas
                num_routes.append(len(routes))
                
                # Calcular utilización de capacidad promedio
                route_loads = [sum(demands[node] for node in route) for route in routes]
                load_percentages = [load / truck_capacity * 100 for load in route_loads]
                avg_load_pcts.append(np.mean(load_percentages) if load_percentages else 0)
                
                logging.debug(f"Run {run+1}/{n_runs} de {alg_name}: costo={cost:.2f}km, tiempo={t1-t0:.2f}s")
            except Exception as e:
                logging.error(f"Error en {alg_name} (run {run+1}): {e}")
                costs.append(float('inf'))
                times.append(float('nan'))
                num_routes.append(0)
                avg_load_pcts.append(0)
        
        # Calcular estadísticas
        valid_costs = [c for c in costs if c != float('inf')]
        if valid_costs:
            ci_cost = bootstrap_ci(valid_costs)
            results[f'{alg_name}_mean_cost'] = np.mean(valid_costs)
            results[f'{alg_name}_ci_cost_lower'] = ci_cost[0]
            results[f'{alg_name}_ci_cost_upper'] = ci_cost[1]
            results[f'{alg_name}_mean_time'] = np.mean([t for i, t in enumerate(times) if costs[i] != float('inf')])
            
            # Calcular robustez (coeficiente de variación)
            results[f'{alg_name}_cost_std'] = np.std(valid_costs)
            results[f'{alg_name}_cost_cv'] = np.std(valid_costs) / np.mean(valid_costs) if np.mean(valid_costs) > 0 else float('inf')
            
            # Guardar promedio de rutas y utilización
            results[f'{alg_name}_mean_routes'] = np.mean([r for i, r in enumerate(num_routes) if costs[i] != float('inf')])
            results[f'{alg_name}_mean_load_pct'] = np.mean([p for i, p in enumerate(avg_load_pcts) if costs[i] != float('inf')])
        else:
            results[f'{alg_name}_mean_cost'] = float('inf')
            results[f'{alg_name}_ci_cost_lower'] = float('inf')
            results[f'{alg_name}_ci_cost_upper'] = float('inf')
            results[f'{alg_name}_mean_time'] = float('nan')
            results[f'{alg_name}_cost_std'] = float('inf')
            results[f'{alg_name}_cost_cv'] = float('inf')
            results[f'{alg_name}_mean_routes'] = 0
            results[f'{alg_name}_mean_load_pct'] = 0
        
        # Guardar datos crudos para análisis
        results[f'{alg_name}_raw_costs'] = costs
        results[f'{alg_name}_raw_times'] = times
        results[f'{alg_name}_raw_routes'] = num_routes
        results[f'{alg_name}_raw_load_pcts'] = avg_load_pcts
    
    return results

def run_experiments(config: Dict[str, Any]) -> pd.DataFrame:
    """Ejecuta todos los experimentos para diferentes tamaños de instancia"""
    client_counts = config['client_counts']
    truck_capacity = config['truck_capacity']
    n_runs = config['n_runs']
    seed_base = config['seed_base']
    parallel = config['parallel']
    n_processes = config['n_processes']
    
    # Preparar ruta del grafo
    graph_path = Path(config['cache_dir']) / config['graph_file']
    if not graph_path.exists():
        graph_path = BASE_DIR / "experiments" / config['graph_file']
    
    # Crear argumentos para cada experimento
    args_list = [
        (n_clients, truck_capacity, seed_base + idx, n_runs, graph_path)
        for idx, n_clients in enumerate(client_counts)
    ]
    
    # Ejecutar experimentos (en paralelo o secuencial)
    if parallel and n_processes > 1:
        logging.info(f"Ejecutando en paralelo con {n_processes} procesos")
        try:
            with mp.Pool(processes=n_processes) as pool:
                results_list = list(tqdm(
                    pool.starmap(run_single_experiment, args_list),
                    total=len(args_list),
                    desc="Experimentos"
                ))
        except Exception as e:
            logging.error(f"Error en paralelización: {e}, cambiando a secuencial")
            parallel = False
    
    # Modo secuencial (o fallback)
    if not parallel or n_processes <= 1:
        logging.info("Ejecutando secuencialmente")
        results_list = []
        for args in tqdm(args_list, desc="Experimentos"):
            try:
                results = run_single_experiment(*args)
                results_list.append(results)
            except Exception as e:
                logging.error(f"Error en experimento {args[0]} clientes: {e}")
                # Resultado vacío para mantener consistencia
                results_list.append({'num_clients': args[0], 'error': str(e)})
    
    # Convertir a DataFrame
    return pd.DataFrame(results_list)

def run_experiments_with_hetero_fleet(config: Dict[str, Any]) -> pd.DataFrame:
    """Ejecuta experimentos con flota heterogénea"""
    client_counts = config['client_counts']
    truck_capacity = config['truck_capacity']
    n_runs = config['n_runs']
    seed_base = config['seed_base']
    parallel = config['parallel']
    n_processes = config['n_processes']
    
    # Preparar ruta del grafo
    graph_path = Path(config['cache_dir']) / config['graph_file']
    if not graph_path.exists():
        graph_path = BASE_DIR / "experiments" / config['graph_file']
    
    # Crear argumentos para cada experimento
    args_list = [
        (n_clients, truck_capacity, seed_base + idx, n_runs, graph_path, True)  # True = heterogeneous fleet
        for idx, n_clients in enumerate(client_counts)
    ]
    
    # Ejecutar experimentos (en paralelo o secuencial)
    if parallel and n_processes > 1:
        logging.info(f"Ejecutando experimentos heterogéneos en paralelo con {n_processes} procesos")
        try:
            with mp.Pool(processes=n_processes) as pool:
                results_list = list(tqdm(
                    pool.starmap(run_single_experiment, args_list),
                    total=len(args_list),
                    desc="Experimentos heterogéneos"
                ))
        except Exception as e:
            logging.error(f"Error en paralelización: {e}, cambiando a secuencial")
            parallel = False
    
    # Modo secuencial (o fallback)
    if not parallel or n_processes <= 1:
        logging.info("Ejecutando experimentos heterogéneos secuencialmente")
        results_list = []
        for args in tqdm(args_list, desc="Experimentos heterogéneos"):
            try:
                results = run_single_experiment(*args)
                results_list.append(results)
            except Exception as e:
                logging.error(f"Error en experimento heterogéneo {args[0]} clientes: {e}")
                # Resultado vacío para mantener consistencia
                results_list.append({'num_clients': args[0], 'heterogeneous_fleet': True, 'error': str(e)})
    
    # Convertir a DataFrame
    return pd.DataFrame(results_list)

def run_experiments_with_demand_pattern(config: Dict[str, Any], pattern: str) -> pd.DataFrame:
    """Ejecuta experimentos con diferentes patrones de demanda"""
    client_counts = config['client_counts']
    truck_capacity = config['truck_capacity']
    n_runs = config['n_runs']
    seed_base = config['seed_base']
    parallel = config['parallel']
    n_processes = config['n_processes']
    
    # Preparar ruta del grafo
    graph_path = Path(config['cache_dir']) / config['graph_file']
    if not graph_path.exists():
        graph_path = BASE_DIR / "experiments" / config['graph_file']
    
    # Crear argumentos para cada experimento (con patrón de demanda específico)
    args_list = [
        (n_clients, truck_capacity, seed_base + idx, n_runs, graph_path, False, pattern)
        for idx, n_clients in enumerate(client_counts)
    ]
    
    # Ejecutar experimentos (en paralelo o secuencial)
    if parallel and n_processes > 1:
        logging.info(f"Ejecutando experimentos con patrón {pattern} en paralelo")
        try:
            with mp.Pool(processes=n_processes) as pool:
                results_list = list(tqdm(
                    pool.starmap(run_single_experiment, args_list),
                    total=len(args_list),
                    desc=f"Experimentos patrón {pattern}"
                ))
        except Exception as e:
            logging.error(f"Error en paralelización: {e}, cambiando a secuencial")
            parallel = False
    
    # Modo secuencial (o fallback)
    if not parallel or n_processes <= 1:
        logging.info(f"Ejecutando experimentos con patrón {pattern} secuencialmente")
        results_list = []
        for args in tqdm(args_list, desc=f"Experimentos patrón {pattern}"):
            try:
                results = run_single_experiment(*args)
                results_list.append(results)
            except Exception as e:
                logging.error(f"Error en experimento patrón {pattern} con {args[0]} clientes: {e}")
                results_list.append({
                    'num_clients': args[0], 
                    'heterogeneous_fleet': False, 
                    'demand_pattern': pattern,
                    'error': str(e)
                })
    
    # Convertir a DataFrame
    return pd.DataFrame(results_list)
# ------ PARTE 6: VISUALIZACIÓN ------

def plot_time_vs_clients(df: pd.DataFrame, algorithms: List[str], config: Dict[str, Any], output_path: Path) -> None:
    """Genera gráfico de tiempo vs número de clientes"""
    plt.figure(figsize=config['viz']['figsize'], dpi=config['viz']['dpi'])
    
    for alg in algorithms:
        y = df[f'{alg}_mean_time'].values
        x = df['num_clients'].values
        # Filtrar valores inválidos para escala log
        y = np.where(np.isnan(y) | (y <= 0), np.nan, y)
        plt.plot(x, y, marker='o', label=alg)
    
    plt.xlabel('Número de clientes')
    plt.ylabel('Tiempo medio (s)')
    plt.xscale('log')
    plt.yscale('log')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.title('Tiempo de ejecución vs Número de clientes')
    plt.tight_layout()
    plt.savefig(output_path, dpi=config['viz']['dpi'])
    plt.close()

def plot_cost_vs_clients(df: pd.DataFrame, algorithms: List[str], config: Dict[str, Any], output_path: Path) -> None:
    """Genera gráfico de costo vs número de clientes"""
    plt.figure(figsize=config['viz']['figsize'], dpi=config['viz']['dpi'])
    
    for alg in algorithms:
        y = df[f'{alg}_mean_cost'].values.astype(float)
        lower = df[f'{alg}_ci_cost_lower'].values.astype(float)
        upper = df[f'{alg}_ci_cost_upper'].values.astype(float)
        
        # Filtrar valores inválidos
        mask = np.isfinite(y) & (y > 0)
        if not any(mask):
            continue
            
        x = df['num_clients'].values[mask]
        y = y[mask]
        err_lower = y - lower[mask]
        err_upper = upper[mask] - y
        
        plt.errorbar(x, y, yerr=[err_lower, err_upper], marker='o', label=alg, capsize=3)
    
    plt.xlabel('Número de clientes')
    plt.ylabel('Costo medio (km)')  # Actualizado a km
    plt.xscale('log')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.title('Costo de solución vs Número de clientes')
    plt.tight_layout()
    plt.savefig(output_path, dpi=config['viz']['dpi'])
    plt.close()

def plot_routes_vs_clients(df: pd.DataFrame, algorithms: List[str], config: Dict[str, Any], output_path: Path) -> None:
    """Genera gráfico de número de rutas vs número de clientes"""
    plt.figure(figsize=config['viz']['figsize'], dpi=config['viz']['dpi'])
    
    for alg in algorithms:
        y = df[f'{alg}_mean_routes'].values
        x = df['num_clients'].values
        plt.plot(x, y, marker='o', label=alg)
    
    plt.xlabel('Número de clientes')
    plt.ylabel('Número medio de rutas')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.title('Número de rutas vs Número de clientes')
    plt.tight_layout()
    plt.savefig(output_path, dpi=config['viz']['dpi'])
    plt.close()

def plot_utilization_vs_clients(df: pd.DataFrame, algorithms: List[str], config: Dict[str, Any], output_path: Path) -> None:
    """Genera gráfico de utilización de capacidad vs número de clientes"""
    plt.figure(figsize=config['viz']['figsize'], dpi=config['viz']['dpi'])
    
    for alg in algorithms:
        y = df[f'{alg}_mean_load_pct'].values
        x = df['num_clients'].values
        plt.plot(x, y, marker='o', label=alg)
    
    plt.xlabel('Número de clientes')
    plt.ylabel('Utilización media de capacidad (%)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.title('Utilización de capacidad vs Número de clientes')
    plt.tight_layout()
    plt.savefig(output_path, dpi=config['viz']['dpi'])
    plt.close()

def plot_robustness_comparison(df: pd.DataFrame, algorithms: List[str], config: Dict[str, Any], output_path: Path) -> None:
    """Genera gráfico de barras con coeficiente de variación (menor es mejor)"""
    # Tomar solo la instancia más grande para simplificar
    largest_instance = df.loc[df['num_clients'].idxmax()]
    
    cv_values = [largest_instance.get(f'{alg}_cost_cv', float('inf')) for alg in algorithms]
    valid_indices = [i for i, cv in enumerate(cv_values) if np.isfinite(cv)]
    
    if not valid_indices:
        logging.warning("No hay datos válidos para el gráfico de robustez")
        return
    
    valid_algorithms = [algorithms[i] for i in valid_indices]
    valid_cv = [cv_values[i] for i in valid_indices]
    
    plt.figure(figsize=config['viz']['figsize'], dpi=config['viz']['dpi'])
    bars = plt.bar(valid_algorithms, valid_cv)
    
    # Añadir valores en las barras
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.3f}',
                ha='center', va='bottom', rotation=0)
    
    plt.ylabel('Coeficiente de variación (menor es mejor)')
    plt.title(f'Robustez de algoritmos (instancia con {largest_instance["num_clients"]} clientes)')
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=config['viz']['dpi'])
    plt.close()

def generate_visualizations(df: pd.DataFrame, algorithms: List[str], config: Dict[str, Any]) -> None:
    """Genera todas las visualizaciones"""
    viz_dir = Path(config['results_dir']) / "visualizations"
    viz_dir.mkdir(parents=True, exist_ok=True)
    
    # Configurar estilo
    plt.style.use(config['viz']['style'])
    
    # Gráficos principales
    logging.info("Generando gráficos")
    
    # Tiempo vs clientes
    time_path = viz_dir / "time_vs_clients.png"
    plot_time_vs_clients(df, algorithms, config, time_path)
    logging.info(f"Gráfico de tiempo guardado en {time_path}")
    
    # Costo vs clientes
    cost_path = viz_dir / "cost_vs_clients.png"
    plot_cost_vs_clients(df, algorithms, config, cost_path)
    logging.info(f"Gráfico de costo guardado en {cost_path}")
    
    # Nuevos gráficos
    routes_path = viz_dir / "routes_vs_clients.png"
    plot_routes_vs_clients(df, algorithms, config, routes_path)
    logging.info(f"Gráfico de rutas guardado en {routes_path}")
    
    util_path = viz_dir / "utilization_vs_clients.png"
    plot_utilization_vs_clients(df, algorithms, config, util_path)
    logging.info(f"Gráfico de utilización guardado en {util_path}")
    
    robustness_path = viz_dir / "robustness_comparison.png"
    plot_robustness_comparison(df, algorithms, config, robustness_path)
    logging.info(f"Gráfico de robustez guardado en {robustness_path}")

# ------ PARTE 7: FUNCIÓN PRINCIPAL ------

def run_comparison(config: Dict[str, Any] = None):
    """Función principal que ejecuta todo el experimento"""
    if config is None:
        config = CONFIG
    
    # Asegurar que existan directorios
    Path(config['results_dir']).mkdir(parents=True, exist_ok=True)
    Path(config['cache_dir']).mkdir(parents=True, exist_ok=True)
    
    # Configurar logging
    log_file = Path(config['results_dir']) / 'metaheuristic_comparison.log'
    listener = setup_logging(log_file)
    
    try:
        logging.info("Iniciando comparación de metaheurísticas")
        logging.info("Las distancias se miden en kilómetros (km)")
        logging.info(f"Configuración: {config}")
        
        # EXPERIMENTO 1: Comparación básica (existente)
        logging.info("=== Experimento 1: Escalabilidad básica ===")
        df_results = run_experiments(config)
        
        # Guardar resultados básicos
        results_path = Path(config['results_dir']) / "vrp_scalability_results.csv"
        df_results.to_csv(results_path, index=False)
        logging.info(f"Resultados básicos guardados en {results_path}")
        
        # Lista completa de algoritmos
        algorithms = ['vns_basic', 'vns_intensive', 'ag_small', 'ag_large', 
                     'ag_mut_high', 'sa', 'sa_fast', 'ts', 'ts_long']
        
        # Visualizaciones del experimento básico
        generate_visualizations(df_results, algorithms, config)
        
        # EXPERIMENTO 2: Flotas heterogéneas (si está habilitado)
        if config['extended_experiments']['run_hetero_fleet']:
            logging.info("=== Experimento 2: Flotas heterogéneas ===")
            df_hetero = run_experiments_with_hetero_fleet(config)
            hetero_results_path = Path(config['results_dir']) / "vrp_heterogeneous_results.csv"
            df_hetero.to_csv(hetero_results_path, index=False)
            logging.info(f"Resultados de flota heterogénea guardados en {hetero_results_path}")
            
            # Visualizaciones para flota heterogénea
            hetero_viz_dir = Path(config['results_dir']) / "visualizations" / "heterogeneous"
            hetero_viz_dir.mkdir(parents=True, exist_ok=True)
            generate_visualizations(df_hetero, algorithms, 
                                   {**config, 'results_dir': str(hetero_viz_dir)})
        
        # EXPERIMENTO 3: Diferentes patrones de demanda (si está habilitado)
        if config['extended_experiments']['run_demand_patterns']:
            logging.info("=== Experimento 3: Patrones de demanda ===")
            for pattern in config['extended_experiments']['demand_patterns']:
                logging.info(f"Ejecutando experimentos con patrón: {pattern}")
                df_demand = run_experiments_with_demand_pattern(config, pattern)
                demand_results_path = Path(config['results_dir']) / f"vrp_{pattern}_demand_results.csv"
                df_demand.to_csv(demand_results_path, index=False)
                logging.info(f"Resultados del patrón {pattern} guardados en {demand_results_path}")
                
                # Visualizaciones para este patrón
                pattern_viz_dir = Path(config['results_dir']) / "visualizations" / f"demand_{pattern}"
                pattern_viz_dir.mkdir(parents=True, exist_ok=True)
                generate_visualizations(df_demand, algorithms, 
                                      {**config, 'results_dir': str(pattern_viz_dir)})
        
        # EXPERIMENTO 4: Análisis de sensibilidad a parámetros (si está habilitado)
        if config['extended_experiments']['run_parameter_sensitivity']:
            logging.info("=== Experimento 4: Análisis de sensibilidad a parámetros ===")
            parameter_sensitivity_analysis(config)
            logging.info("Análisis de sensibilidad completado")
        
        # Realizar pruebas estadísticas más extensas
        logging.info("Realizando pruebas estadísticas")
        
        # Más pares para comparar todas las variantes
        pairs = [
            # Comparaciones entre grupos
            ('vns_basic', 'ag_large'), ('vns_basic', 'sa'), ('vns_basic', 'ts'),
            ('ag_large', 'sa'), ('ag_large', 'ts'), ('sa', 'ts'),
            
            # Comparaciones intragrupo
            ('vns_basic', 'vns_intensive'),
            ('ag_small', 'ag_large'), ('ag_small', 'ag_mut_high'), ('ag_large', 'ag_mut_high'),
            ('sa', 'sa_fast'),
            ('ts', 'ts_long')
        ]
         
        rows = []
        for _, row in df_results.iterrows():
            nc = row['num_clients']
            for a1, a2 in pairs:
                data1 = np.array(row[f'{a1}_raw_costs'])
                data2 = np.array(row[f'{a2}_raw_costs'])
                valid_idx = np.isfinite(data1) & np.isfinite(data2)
                
                if np.sum(valid_idx) < 5:
                    stat, p = float('nan'), float('nan')
                    result_type = "insuficientes_datos"
                else:
                    # Verificar si todos los elementos son iguales
                    diff = data1[valid_idx] - data2[valid_idx]
                    if np.all(diff == 0):
                        # Resultados idénticos - no es necesario el test
                        stat, p = 0.0, 1.0  # p=1 indica que no hay diferencia
                        result_type = "resultados_identicos"
                        logging.info(f"Algoritmos {a1} y {a2} producen resultados idénticos para {nc} clientes")
                    else:
                        try:
                            stat, p = wilcoxon(data1[valid_idx], data2[valid_idx])
                            result_type = "test_realizado"
                        except Exception as e:
                            if "zero_method" in str(e):
                                # Este caso no debería ocurrir con la verificación anterior,
                                # pero lo dejamos por seguridad
                                stat, p = 0.0, 1.0
                                result_type = "resultados_identicos"
                                logging.info(f"Algoritmos {a1} y {a2} producen resultados idénticos para {nc} clientes")
                            else:
                                logging.warning(f"Error Wilcoxon {a1} vs {a2} en {nc} clientes: {e}")
                                stat, p = float('nan'), float('nan')
                                result_type = "error"
                
                rows.append({
                    'num_clients': nc, 
                    'alg1': a1, 
                    'alg2': a2, 
                    'stat': stat, 
                    'p_value': p,
                    'result_type': result_type
                })
        
        df_stats = pd.DataFrame(rows)
        stats_path = Path(config['results_dir']) / "wilcoxon_results.csv"
        df_stats.to_csv(stats_path, index=False)
        logging.info(f"Estadísticas guardadas en {stats_path}")
        
        # Resumen de mejores algoritmos por tamaño de instancia
        create_performance_summary(df_results, algorithms, config)
        
        logging.info("Experimentos completados con éxito")
        
    except Exception as exc:
        logging.exception(f"Error durante la ejecución: {exc}")
    finally:
        listener.stop()

def create_performance_summary(df: pd.DataFrame, algorithms: List[str], config: Dict[str, Any]) -> None:
    """Crea un resumen del rendimiento de los algoritmos"""
    summary_rows = []
    
    for _, row in df.iterrows():
        n_clients = row['num_clients']
        
        # Encontrar mejor algoritmo por costo
        best_cost_alg = min(
            [alg for alg in algorithms if np.isfinite(row.get(f'{alg}_mean_cost', float('inf')))],
            key=lambda alg: row.get(f'{alg}_mean_cost', float('inf')),
            default=None
        )
        
        # Encontrar algoritmo más rápido
        fastest_alg = min(
            [alg for alg in algorithms if np.isfinite(row.get(f'{alg}_mean_time', float('inf')))],
            key=lambda alg: row.get(f'{alg}_mean_time', float('inf')),
            default=None
        )
        
        # Encontrar algoritmo más robusto (menor coeficiente de variación)
        most_robust_alg = min(
            [alg for alg in algorithms if np.isfinite(row.get(f'{alg}_cost_cv', float('inf')))],
            key=lambda alg: row.get(f'{alg}_cost_cv', float('inf')),
            default=None
        )
        
        # Encontrar algoritmo con mejor utilización de capacidad
        best_util_alg = max(
            [alg for alg in algorithms if np.isfinite(row.get(f'{alg}_mean_load_pct', 0))],
            key=lambda alg: row.get(f'{alg}_mean_load_pct', 0),
            default=None
        )
        
        summary_rows.append({
            'num_clients': n_clients,
            'best_cost_algorithm': best_cost_alg,
            'best_cost_value': row.get(f'{best_cost_alg}_mean_cost', float('inf')) if best_cost_alg else float('inf'),
            'fastest_algorithm': fastest_alg,
            'fastest_time': row.get(f'{fastest_alg}_mean_time', float('inf')) if fastest_alg else float('inf'),
            'most_robust_algorithm': most_robust_alg,
            'robustness_cv': row.get(f'{most_robust_alg}_cost_cv', float('inf')) if most_robust_alg else float('inf'),
            'best_utilization_algorithm': best_util_alg,
            'utilization_pct': row.get(f'{best_util_alg}_mean_load_pct', 0) if best_util_alg else 0
        })
    
    summary_df = pd.DataFrame(summary_rows)
    summary_path = Path(config['results_dir']) / "performance_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    logging.info(f"Resumen de rendimiento guardado en {summary_path}")
    
def analyze_convergence(config: Dict[str, Any]) -> None:
    """Analiza la velocidad de convergencia de cada algoritmo en una instancia fija"""
    # Usar una instancia de tamaño medio para el análisis
    num_clients = 10
    truck_capacity = config['truck_capacity']
    seed = config['seed_base']
    
    # Cargar grafo y generar instancia
    G = load_havana_graph()
    instance = generate_real_instance(G, num_clients, seed)
    
    dist_matrix = instance['dist_matrix']
    demands = instance['demands']
    
    # Calcular camiones necesarios
    total_demand = sum(demands[1:])
    num_trucks = max(1, int(np.ceil(total_demand / truck_capacity)))
    truck_caps = [truck_capacity] * num_trucks
    
    # Obtener algoritmos
    algorithms = create_algorithm_wrappers()
    
    # Para cada algoritmo, capturar su convergencia
    convergence_data = {}
    
    for alg_name, alg_func, params in algorithms:
        # Modificar los algoritmos para que devuelvan historial de convergencia
        # Esto requiere modificar cada wrapper para que capture el progreso
        
        # Ejemplo conceptual:
        if hasattr(alg_func, 'capture_convergence'):
            costs_history, solution = alg_func.capture_convergence(
                dist_matrix, demands, truck_caps, **params
            )
            convergence_data[alg_name] = costs_history
    
    # Visualizar convergencia
    plt.figure(figsize=config['viz']['figsize'], dpi=config['viz']['dpi'])
    for alg_name, history in convergence_data.items():
        plt.plot(history, label=alg_name)
    
    plt.xlabel('Iteraciones')
    plt.ylabel('Costo de la solución')
    plt.legend()
    plt.title(f'Análisis de convergencia ({num_clients} clientes)')
    plt.grid(True, alpha=0.3)
    
    # Guardar visualización
    viz_dir = Path(config['results_dir']) / "visualizations"
    viz_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(viz_dir / "convergence_analysis.png")
    plt.close()

def parameter_sensitivity_analysis(config: Dict[str, Any]) -> None:
    """Analiza la sensibilidad de los algoritmos a cambios en sus parámetros"""
    # Configurar cliente fijo y capacidad
    num_clients = 10
    truck_capacity = config['truck_capacity']
    seed = config['seed_base']
    n_runs = 5  # Reducir runs para este experimento específico
    
    # Cargar datos
    G = load_havana_graph()
    instance = generate_real_instance(G, num_clients, seed)
    dist_matrix = instance['dist_matrix']
    demands = instance['demands']
    
    # Calcular camiones
    total_demand = sum(demands[1:])
    num_trucks = max(1, int(np.ceil(total_demand / truck_capacity)))
    truck_caps = [truck_capacity] * num_trucks
    
    # Parámetros a variar para cada algoritmo
    parameter_ranges = {
        'ag_solver_wrapper': {
            'mut_rate': [0.1, 0.3, 0.5, 0.7, 0.9],
            'pop_size': [20, 50, 100, 200, 300]
        },
        'sa_wrapper': {
            'init_temp': [100, 500, 1000, 2000, 5000],
            'alpha': [0.8, 0.9, 0.95, 0.98, 0.995]
        },
        'ts_wrapper': {
            'tabu_tenure': [10, 25, 50, 100, 200]
        },
        'vns_wrapper': {
            'max_iter': [50, 100, 200, 500, 1000]
        }
    }
    
    # Obtener algoritmos con sus wrappers
    algorithms = create_algorithm_wrappers()
    
    # Crear un mapeo de nombres de algoritmos a funciones
    algorithm_funcs = {}
    for name, func, _ in algorithms:
        if name.startswith('ag_'):
            algorithm_funcs['ag_solver_wrapper'] = func
        elif name.startswith('sa'):
            algorithm_funcs['sa_wrapper'] = func
        elif name.startswith('ts'):
            algorithm_funcs['ts_wrapper'] = func
        elif name.startswith('vns'):
            algorithm_funcs['vns_wrapper'] = func
    
    # Resultados para cada algoritmo y parámetro
    sensitivity_results = {}
    
    # Para cada algoritmo
    for alg_name, param_dict in parameter_ranges.items():
        alg_func = algorithm_funcs.get(alg_name)
        if not alg_func:
            continue
            
        # Para cada parámetro
        for param_name, param_values in param_dict.items():
            results = []
            
            # Para cada valor del parámetro
            for param_value in param_values:
                params = {param_name: param_value}
                
                # Ejecutar n_runs veces
                costs = []
                for _ in range(n_runs):
                    try:
                        routes = alg_func(dist_matrix, demands, truck_caps, **params)
                        cost = compute_total_distance(routes, dist_matrix)
                        costs.append(cost)
                    except Exception as e:
                        logging.error(f"Error en {alg_name} con {param_name}={param_value}: {e}")
                
                # Calcular promedio
                avg_cost = np.mean(costs) if costs else float('inf')
                results.append((param_value, avg_cost))
            
            # Guardar resultados
            sensitivity_results[f"{alg_name}_{param_name}"] = results
    
    # Visualizar resultados
    for param_key, results in sensitivity_results.items():
        alg_name, param_name = param_key.split('_', 1)
        
        plt.figure(figsize=config['viz']['figsize'])
        x_values, y_values = zip(*results)
        plt.plot(x_values, y_values, marker='o')
        
        plt.xlabel(f'Valor de {param_name}')
        plt.ylabel('Costo promedio')
        plt.title(f'Sensibilidad de {alg_name} a {param_name}')
        plt.grid(True, alpha=0.3)
        
        # Guardar visualización
        viz_dir = Path(config['results_dir']) / "visualizations" / "sensitivity"
        viz_dir.mkdir(parents=True, exist_ok=True)
        plt.savefig(viz_dir / f"sensitivity_{alg_name}_{param_name}.png")
        plt.close()

# Ejecutar si se llama como script principal
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Comparación de metaheurísticas para VRP')
    parser.add_argument('--all', action='store_true', help='Ejecutar todos los experimentos')
    parser.add_argument('--basic', action='store_true', help='Ejecutar solo experimento básico')
    parser.add_argument('--hetero', action='store_true', help='Ejecutar experimento con flota heterogénea')
    parser.add_argument('--demand', action='store_true', help='Ejecutar experimento con patrones de demanda')
    parser.add_argument('--sensitivity', action='store_true', help='Ejecutar análisis de sensibilidad')
    
    args = parser.parse_args()
    
    # Configurar experimentos según argumentos
    if not any([args.all, args.basic, args.hetero, args.demand, args.sensitivity]):
        # Si no se especifica ningún argumento, ejecutar todo
        args.all = True
    
    # Configurar qué experimentos ejecutar
    config_copy = CONFIG.copy()
    config_copy['extended_experiments'] = {
        'run_hetero_fleet': args.all or args.hetero,
        'run_demand_patterns': args.all or args.demand,
        'run_parameter_sensitivity': args.all or args.sensitivity,
        'demand_patterns': ['uniform', 'clustered', 'heavy_tailed']
    }
    
    # Ejecutar comparación con la configuración actualizada
    run_comparison(config_copy)