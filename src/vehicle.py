import random
import math  # Añadir importación de math para la función exponencial

# Parámetros de congestión
CONGESTION_ALPHA = 0.5  # Controla la pendiente de la curva logística
CONGESTION_THRESHOLD = 5  # Umbral a partir del cual la congestión se vuelve significativa

# Número de vehículos a simular (reducido para depuración)
NUM_VEHICLES = 5

# Pesos para priorizar tipos de vías
HIGHWAY_WEIGHTS = {
    "motorway": 10.0,  # Máxima prioridad para autopistas
    "trunk": 8.0,      # Alta prioridad para vías troncales
    "primary": 7.0,    # Prioridad media-alta para vías primarias
    "secondary": 3.0,  # Prioridad media
    "tertiary": 2.0,   # Prioridad media-baja
    "default": 1.0     # Prioridad baja para el resto
}

def get_edge_weight(street_graph, current, neighbor):
    """Determina el peso de prioridad para un enlace basado en su tipo de vía"""
    try:
        edge_data = street_graph.get_edge_data(current, neighbor, 0)
        highway_type = edge_data.get('highway_type', 'default')
        return HIGHWAY_WEIGHTS.get(highway_type, HIGHWAY_WEIGHTS["default"])
    except Exception:
        return HIGHWAY_WEIGHTS["default"]

def weighted_choice(choices, weights):
    """Selecciona un elemento de las opciones basado en los pesos proporcionados"""
    total = sum(weights)
    r = random.uniform(0, total)
    upto = 0
    for choice, weight in zip(choices, weights):
        upto += weight
        if upto >= r:
            return choice
    # Por si acaso, devuelve el último elemento
    return choices[-1] if choices else None

def initialize_vehicles(street_graph, all_nodes, vehicle_speeds, vehicles, street_congestion):
    """Inicializa la posición de los vehículos y les asigna rutas aleatorias"""
    
    if not all_nodes:
        print("No hay nodos en el grafo. Inicialización fallida.")
        return
    
    print(f"Inicializando {NUM_VEHICLES} vehículos...")
    
    # Categorías de vehículos con diferentes comportamientos
    vehicle_types = ["normal", "agresivo", "cauteloso", "lento", "rápido"]
    
    for i in range(NUM_VEHICLES):
        vid = f"veh_{i}"
        
        # Seleccionar un nodo aleatorio para comenzar
        start_node = random.choice(all_nodes)
        node_data = street_graph.nodes[start_node]
        
        # Tipo de vehículo para comportamiento
        vehicle_type = random.choice(vehicle_types)
        
        # Ubicar el vehículo en ese nodo
        vehicles[vid] = {
            "lat": float(node_data['lat']),
            "lon": float(node_data['lon']),
            "current_node": start_node,
            "next_node": None,
            "previous_node": None,  # Para mantener dirección
            "progress": 0.0,
            "type": vehicle_type,   # Tipo de comportamiento
        }
        
        # Asignar velocidad según tipo de vehículo
        # Estos valores ahora serán factores que se multiplicarán por la velocidad máxima de la calle
        if vehicle_type == "rápido":
            speed_factor = random.uniform(0.9, 1.0)  # Cerca del límite
        elif vehicle_type == "agresivo":
            speed_factor = random.uniform(0.85, 1.05)  # Puede exceder ligeramente
        elif vehicle_type == "lento":
            speed_factor = random.uniform(0.5, 0.7)  # Significativamente por debajo
        elif vehicle_type == "cauteloso":
            speed_factor = random.uniform(0.7, 0.85)  # Moderadamente por debajo
        else:  # normal
            speed_factor = random.uniform(0.75, 0.9)  # Ligeramente por debajo
        
        # Guardar el factor de velocidad base (se ajustará con límites reales en cada calle)
        vehicle_speeds[vid] = speed_factor * 0.005  # Base de velocidad
        
        # Asignar una ruta aleatoria
        assign_random_route(vid, street_graph, all_nodes, vehicles, street_congestion)
    
    print(f"Vehículos inicializados: {len(vehicles)}")

def assign_random_route(vehicle_id, street_graph, all_nodes, vehicles, street_congestion):
    """Asigna una ruta aleatoria a un vehículo, priorizando avenidas principales"""
    
    if not all_nodes or len(all_nodes) < 2:
        print("No hay suficientes nodos para asignar rutas")
        return
    
    try:
        current = vehicles[vehicle_id]["current_node"]
        
        # Encontrar nodos conectados
        neighbors = list(street_graph.neighbors(current))
        
        if neighbors:
            # Calcular pesos para cada vecino basado en el tipo de vía
            weights = [get_edge_weight(street_graph, current, neighbor) for neighbor in neighbors]
            
            # Elegir un vecino con selección ponderada
            destination = weighted_choice(neighbors, weights)
            
            # Asignar ese nodo como el siguiente en la ruta
            vehicles[vehicle_id]["next_node"] = destination
            vehicles[vehicle_id]["progress"] = 0.0
        else:
            # Si no hay vecinos, asignar un nodo aleatorio y teletransportarse
            new_node = random.choice(all_nodes)
            node_data = street_graph.nodes[new_node]
            vehicles[vehicle_id]["current_node"] = new_node
            vehicles[vehicle_id]["lat"] = float(node_data['lat'])
            vehicles[vehicle_id]["lon"] = float(node_data['lon'])
            assign_random_route(vehicle_id, street_graph, all_nodes, vehicles, street_congestion)
    
        # Incrementar congestión en la nueva calle
        if vehicles[vehicle_id]["next_node"] is not None:
            edge = (vehicles[vehicle_id]["current_node"], vehicles[vehicle_id]["next_node"])
            if edge in street_congestion:
                street_congestion[edge] += 1
    
    except Exception as e:
        print(f"Error asignando ruta para {vehicle_id}: {e}")

def plan_continuous_route(vehicle_id, street_graph, all_nodes, vehicles, street_congestion):
    """Asigna una ruta que mantiene la dirección de movimiento actual, priorizando avenidas principales"""
    try:
        current = vehicles[vehicle_id]["current_node"]
        previous = vehicles[vehicle_id].get("previous_node")
        
        # Encontrar nodos conectados
        neighbors = list(street_graph.neighbors(current))
        
        if not neighbors:
            # Si no hay vecinos, asignar un nodo aleatorio
            assign_random_route(vehicle_id, street_graph, all_nodes, vehicles, street_congestion)
            return
            
        if previous and len(neighbors) > 1:
            # Intentar mantener la dirección (no volver al nodo anterior)
            filtered_neighbors = [n for n in neighbors if n != previous]
            if filtered_neighbors:
                # Calcular pesos para cada vecino filtrado
                weights = [get_edge_weight(street_graph, current, neighbor) for neighbor in filtered_neighbors]
                destination = weighted_choice(filtered_neighbors, weights)
            else:
                # Si solo queda el nodo anterior, usarlo
                destination = previous
        else:
            # Sin nodo anterior, usar selección ponderada
            weights = [get_edge_weight(street_graph, current, neighbor) for neighbor in neighbors]
            destination = weighted_choice(neighbors, weights)
        
        # Guardar el nodo actual como previo para la próxima vez
        vehicles[vehicle_id]["previous_node"] = current
        
        # Asignar el próximo nodo y resetear progreso
        vehicles[vehicle_id]["next_node"] = destination
        vehicles[vehicle_id]["progress"] = 0.0
        
        # Incrementar congestión en la nueva calle
        if vehicles[vehicle_id]["next_node"] is not None:
            edge = (vehicles[vehicle_id]["current_node"], vehicles[vehicle_id]["next_node"])
            if edge in street_congestion:
                street_congestion[edge] += 1
        
    except Exception as e:
        print(f"Error planificando ruta continua para {vehicle_id}: {e}")
        # Fallback a ruta aleatoria
        assign_random_route(vehicle_id, street_graph, all_nodes, vehicles, street_congestion)
        


def update_vehicle_positions(street_graph, traffic_lights, vehicles, vehicle_speeds, all_nodes, street_congestion):
    """Actualiza las posiciones de los vehículos en sus rutas y gestiona la congestión del tráfico"""
    for vid, v in vehicles.items():
        current_node = v["current_node"]
        next_node = v["next_node"]
        
        # Guardar la calle actual para actualizar la congestión
        current_edge = (current_node, next_node) if next_node is not None else None

        # Si no tiene un nodo siguiente, asignar uno
        if next_node is None:
            assign_random_route(vid, street_graph, all_nodes, vehicles, street_congestion)
            continue
            
        # Obtener las coordenadas de los nodos
        try:
            # Obtener límites de velocidad de la calle actual
            edge_data = street_graph.get_edge_data(current_node, next_node, 0)
            max_speed = edge_data.get('max_speed', 50)  # km/h
            min_speed = edge_data.get('min_speed', 30)  # km/h
            
            # Convertir km/h a unidades de progreso por actualización
            max_speed_progress = max_speed * 0.0001  # Ajusta este factor según necesites
            min_speed_progress = min_speed * 0.0001  # Ajusta este factor según necesites
            
            # Ajustar la velocidad del vehículo para que esté dentro del rango de la calle
            base_vehicle_speed = vehicle_speeds[vid]
            
            # Aplicar el tipo de conductor (respetando límites)
            if v["type"] == "agresivo":
                # Los agresivos pueden exceder ligeramente el límite
                adjusted_speed = min(base_vehicle_speed, max_speed_progress * 1.1)
            elif v["type"] == "cauteloso":
                # Los cautelosos nunca exceden el límite y prefieren ir más lento
                adjusted_speed = min(base_vehicle_speed, max_speed_progress * 0.8)
            else:
                # Otros respetan el límite máximo
                adjusted_speed = min(base_vehicle_speed, max_speed_progress)
            
            # Nunca ir por debajo del mínimo (excepto en situaciones de tráfico)
            adjusted_speed = max(adjusted_speed, min_speed_progress)
            
            # Ajustar velocidad basada en la congestión de la calle actual
            current_congestion = street_congestion.get((current_node, next_node), 0)
            
            # Modelo de congestión con función logística
            # La función devuelve valores entre 0 y 1, donde:
            # - Valores cercanos a 1 significan poco impacto (pocos vehículos)
            # - Valores cercanos a 0 significan mucho impacto (muchos vehículos)
            congestion_factor = 1 / (1 + math.exp(CONGESTION_ALPHA * (current_congestion - CONGESTION_THRESHOLD)))
            
            # Limitar la reducción máxima al 20% de la velocidad original
            congestion_factor = max(0.2, congestion_factor)
            
            adjusted_speed = adjusted_speed * congestion_factor
            
            # Comportamiento ante semáforos
            if next_node in traffic_lights:
                light_state = traffic_lights[next_node]["state"]
                
                # Si el semáforo está en rojo y estamos cerca, desacelerar
                if light_state == "red" and v["progress"] > 0.7 and v["progress"] <= 0.97:
                    # Reducir velocidad drásticamente cuando está cerca
                    v["progress"] += adjusted_speed * 0.1
                    continue
                elif light_state == "red" and v["progress"] > 0.98:
                    
                    v["progress"] += 0
                    continue
            
            current_lat = float(street_graph.nodes[current_node]['lat'])
            current_lon = float(street_graph.nodes[current_node]['lon'])
            next_lat = float(street_graph.nodes[next_node]['lat'])
            next_lon = float(street_graph.nodes[next_node]['lon'])
            
            # Actualizar el progreso basado en la velocidad ajustada
            v["progress"] += adjusted_speed 
            
            if v["progress"] >= 1.0:
                # Decrementar la congestión en la calle que acaba de dejar
                if current_edge in street_congestion:
                    street_congestion[current_edge] = max(0, street_congestion[current_edge] - 1)
                
                # Llegó al nodo siguiente
                v["current_node"] = next_node
                v["next_node"] = None
                v["lat"] = next_lat
                v["lon"] = next_lon
                
                # Decidir si continuar en la misma dirección o cambiar
                if random.random() < 0.7:  # 70% de probabilidad de mantener dirección
                    plan_continuous_route(vid, street_graph, all_nodes, vehicles, street_congestion)
                else:
                    # Asignar una nueva ruta aleatoria
                    assign_random_route(vid, street_graph, all_nodes, vehicles, street_congestion)
                
                # Incrementar la congestión en la nueva calle
                new_edge = (v["current_node"], v["next_node"])
                if v["next_node"] is not None and new_edge in street_congestion:
                    street_congestion[new_edge] += 1
                
            else:
                # Interpolación lineal entre los nodos con pequeña variación
                variation = random.uniform(-0.000000005, 0.000000005)  # Pequeña variación para evitar solapamiento
                v["lat"] = current_lat + (next_lat - current_lat) * v["progress"] + variation
                v["lon"] = current_lon + (next_lon - current_lon) * v["progress"] + variation
                
        except Exception as e:
            # En caso de error, asignar una nueva ruta
            print(f"Error en actualización de {vid}: {e}")
            assign_random_route(vid, street_graph, all_nodes, vehicles, street_congestion)