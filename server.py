import asyncio
import websockets
import json
import random
import os
import networkx as nx
from datetime import datetime
import math
from src.vehicle import initialize_vehicles, update_vehicle_positions
from src.traffic_lights import initialize_traffic_lights, update_traffic_lights
from src.optimized_route import optimize_delivery_routes

# Importar análisis climático
import sys
sys.path.append("src/weather")
try:
    from weather_impact_analyzer import WeatherImpactAnalyzer
    WEATHER_ANALYZER = WeatherImpactAnalyzer()
    print("Sistema de análisis climático inicializado")
except ImportError as e:
    print(f"Advertencia: Sistema climático no disponible: {e}")
    WEATHER_ANALYZER = None


traffic_lights = {}  # node_id: {"state": "red"/"green", "timer": X}

# Centro de La Habana
lat_base, lon_base = 23.1136, -82.3666

# Grafo de calles y rutas
street_graph = nx.MultiDiGraph()
all_nodes = []
vehicle_speeds = {}  # Velocidades diferentes para cada vehículo
vehicles = {}
street_congestion = {}  # (node1, node2): cantidad_vehiculos


def haversine(lat1, lon1, lat2, lon2):
    """Calcula la distancia entre dos puntos geográficos en km"""
    R = 6371.0  # Radio de la Tierra en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def load_streets():
    """Carga los datos del mapa desde los archivos de caché y construye el grafo de calles"""
    global street_graph, all_nodes, street_congestion
    
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
    
    try:
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
        
    except Exception as e:
        print(f"Error cargando datos de calles: {e}")
        print("Creando grafo de desarrollo...")
        # Crear un grafo mínimo para desarrollo
        for i in range(20):
            lat = lat_base + random.uniform(-0.01, 0.01)
            lon = lon_base + random.uniform(-0.01, 0.01)
            street_graph.add_node(i, lat=lat, lon=lon)
            if i > 0:
                # Agregar también velocidades en el grafo de desarrollo
                max_speed = random.choice([30, 50, 70, 90])
                min_speed = max_speed * 0.7
                street_graph.add_edge(i-1, i, weight=0.01, max_speed=max_speed, min_speed=min_speed, 
                                     highway_type="residential")
        all_nodes = list(street_graph.nodes())
        print("Usando grafo de desarrollo con 20 nodos")



async def send_positions(websocket):
    """Envía las posiciones actualizadas de los vehículos al cliente"""
    while True:
        try:
            # Actualizar las posiciones
            #update_vehicle_positions(street_graph, traffic_lights, vehicles, vehicle_speeds, all_nodes, street_congestion)
            #update_traffic_lights(traffic_lights)
            
            # Empaquetar y enviar los datos
            payload = {
                "timestamp": datetime.now().isoformat(),
                "vehicles": [
                    {"id": vid, "lat": v["lat"], "lon": v["lon"]}
                    for vid, v in vehicles.items()
                ],
                "traffic_lights": [
                    {
                        "node_id": nid,
                        "lat": data["lat"],
                        "lon": data["lon"],
                        "state": data["state"],
                        "zone": data.get("zone", 0),
                        "direction": data.get("direction", "east")
                    } for nid, data in traffic_lights.items()
                ]
            }
            
            await websocket.send(json.dumps(payload))
            await asyncio.sleep(0.2)  # Actualización más frecuente
        except websockets.exceptions.ConnectionClosed:
            print("Cliente desconectado")
            break
        except Exception as e:
            print(f"Error enviando datos: {e}")
            await asyncio.sleep(1)

async def handler(websocket):
    """Manejador principal de conexiones WebSocket"""
    print("Cliente conectado")
    try:
        # Iniciar una tarea para enviar actualizaciones de posición
        position_task = asyncio.create_task(send_positions(websocket))
        
        # Recibir y procesar mensajes del cliente
        async for message in websocket:
            try:
                data = json.loads(message)
                message_type = data.get('type', '')
                
                if message_type == 'optimization_request':
                    # Manejar solicitud de optimización
                    await handle_optimization_request(websocket, data)
                # Aquí puedes manejar otros tipos de mensajes si es necesario
                
            except json.JSONDecodeError:
                print("Error: Mensaje recibido no es JSON válido")
            except Exception as e:
                print(f"Error procesando mensaje: {e}")
        
        # Cancelar la tarea de envío de posiciones cuando el cliente se desconecta
        position_task.cancel()
        
    except websockets.exceptions.ConnectionClosed:
        print("Cliente desconectado")
    except Exception as e:
        print(f"Error en el handler: {e}")

# Maneja solicitudes de optimización de rutas
async def handle_optimization_request(websocket, data):
    """Maneja solicitudes de optimización de rutas"""
    try:
        start_point = data.get('start_point')
        target_points = data.get('target_points', [])
        num_trucks = data.get('num_trucks', 1)
        truck_capacities = data.get('truck_capacities')
        target_demands = data.get('target_demands')
        
        # Validar datos de entrada
        if not start_point or not target_points:
            await websocket.send(json.dumps({
                "type": "optimization_error",
                "message": "Se requiere un punto de inicio y al menos un objetivo"
            }))
            return
              # Convertir IDs de nodos a enteros si es necesario
        try:
            start_point = int(start_point)
            target_points = [int(p) for p in target_points]
        except ValueError:
            # Si los IDs no son numéricos, mantenerlos como están
            pass
        
        # Obtener información climática si está disponible
        weather_info = None
        if WEATHER_ANALYZER:
            try:
                weather_factor, weather_details = WEATHER_ANALYZER.calculate_weather_impact_factor()
                weather_info = {
                    "impact_factor": weather_factor,
                    "interpretation": weather_details.get('interpretation', ''),
                    "weather_summary": weather_details.get('weather_data', {})
                }
                print(f"Optimización con factor climático: {weather_factor:.2f}")
            except Exception as e:
                print(f"Error obteniendo datos climáticos: {e}")
                weather_info = {"error": str(e)}
            
        # Realizar la optimización (con análisis climático integrado)
        routes, total_cost = optimize_delivery_routes(
            street_graph=street_graph,
            start_point=start_point,
            target_points=target_points,
            num_trucks=num_trucks,
            truck_capacities=truck_capacities,
            target_demands=target_demands,
            use_weather_impact=True  # Habilitar análisis climático
        )
        
        # Preparar resultados para enviar al cliente
        if routes:
            try:
                # Verificar que routes sea iterable
                if not hasattr(routes, '__iter__'):
                    raise TypeError(f"Las rutas deben ser iterables, se recibió: {type(routes)}")
                    
                # Convertir las rutas a formato amigable para el cliente
                formatted_routes = []
                for route in routes:
                    # Verificar que cada ruta sea iterable
                    if not hasattr(route, '__iter__'):
                        print(f"Advertencia: Se encontró una ruta que no es iterable: {type(route)}. Saltando.")
                        continue
                        
                    route_points = []
                    for node_id in route:
                        try:
                            node_data = street_graph.nodes[node_id]
                            route_points.append({
                                "node_id": node_id,
                                "lat": node_data.get('lat'),
                                "lon": node_data.get('lon')
                            })
                        except (KeyError, TypeError) as e:
                            print(f"Error al procesar el nodo {node_id}: {e}")
                            continue
                            
                    formatted_routes.append(route_points)
                      # Enviar resultados (incluir información climática si está disponible)
                response_data = {
                    "type": "optimization_result",
                    "routes": formatted_routes,
                    "total_cost": total_cost
                }
                
                if weather_info:
                    response_data["weather_info"] = weather_info
                
                await websocket.send(json.dumps(response_data))
            except Exception as e:
                print(f"Error al formatear rutas: {e}")
                await websocket.send(json.dumps({
                    "type": "optimization_error",
                    "message": f"Error al procesar las rutas optimizadas: {str(e)}"
                }))
        else:
            await websocket.send(json.dumps({
                "type": "optimization_error",
                "message": "No se pudo encontrar una solución"
            }))
            
    except Exception as e:
        print(f"Error en optimización: {e}")
        await websocket.send(json.dumps({
            "type": "optimization_error",
            "message": f"Error en el proceso de optimización: {str(e)}"
        }))


async def main():
    # Cargar calles, inicializar vehículos y semaforos
    load_streets()
    #initialize_vehicles(street_graph, all_nodes, vehicle_speeds, vehicles, street_congestion)
    #initialize_traffic_lights(street_graph, traffic_lights)


    print("Servidor WebSocket iniciando en puerto 8765...")
    async with websockets.serve(
        handler, 
        "localhost", 
        8765,
        ping_interval=30,
        ping_timeout=10
    ):
        # Mantener el servidor ejecutándose indefinidamente
        await asyncio.Future()


    
# Ejecuta el punto de entrada principal
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Servidor detenido por el usuario")

