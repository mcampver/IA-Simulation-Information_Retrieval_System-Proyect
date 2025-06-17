import json
import os
import sys
import networkx as nx
import random
import re
import difflib
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Set

# Añadir el directorio raíz al path para importar correctamente
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

# Importar el módulo Gemini
from src.NLP.Gemini import Gemini

class CVRPAssistant:
    """Asistente conversacional para extraer parámetros de CVRP usando direcciones en lenguaje natural"""
    
    def __init__(self):
        self.gemini = Gemini()
        self.street_graph, self.street_data = self._load_street_graph()
        self.all_nodes = list(self.street_graph.nodes())
        
        # Parámetros del CVRP
        self.params = {
            "start_point": None,
            "target_points": [],
            "num_trucks": 0,
            "truck_capacities": [],
            "target_demands": []
        }
        
        # Estado de la conversación
        self.conversation_state = "start"
        self.history = []
    
    def _load_street_graph(self) -> Tuple[nx.MultiDiGraph, Dict]:
        """Carga el grafo de calles desde el archivo JSON y extrae información de calles"""
        cache_file = os.path.join("cache", "479c34c9f9679cb8467293e0403a0250c7ef8556.json")
        
        try:
            import ijson
            
            street_graph = nx.MultiDiGraph()
            nodes = {}
            
            # Datos para búsqueda de calles
            street_data = {
                'streets': set(),           # Conjunto de nombres de calles
                'nodes_by_street': {},      # Mapeo de calles a nodos
                'streets_by_node': {},      # Mapeo de nodos a calles
                'intersections': {},        # Mapeo de intersecciones a nodos
                'neighborhoods': set(),     # Conjunto de barrios
                'nodes_by_neighborhood': {} # Mapeo de barrios a nodos
            }
            
            # Extraer nodos
            with open(cache_file, 'r', encoding='utf-8') as f:
                for element in ijson.items(f, 'elements.item'):
                    if element.get('type') == 'node':
                        node_id = element.get('id')
                        lat = element.get('lat')
                        lon = element.get('lon')
                        tags = element.get('tags', {})
                        
                        if node_id and lat and lon:
                            nodes[node_id] = (float(lat), float(lon))
                            street_graph.add_node(node_id, lat=float(lat), lon=float(lon), tags=tags)
                            
                            # Si el nodo tiene nombre, guardarlo
                            if 'name' in tags:
                                node_name = tags['name']
                                street_graph.nodes[node_id]['name'] = node_name
            
            # Extraer vías y construir el índice de calles
            with open(cache_file, 'r', encoding='utf-8') as f:
                for element in ijson.items(f, 'elements.item'):
                    if element.get('type') == 'way' and element.get('tags', {}).get('highway'):
                        way_id = element.get('id')
                        way_nodes = element.get('nodes', [])
                        tags = element.get('tags', {})
                        oneway = tags.get('oneway', 'no')
                        
                        # Extraer nombre de la calle y barrio si existen
                        street_name = tags.get('name')
                        neighborhood = tags.get('addr:suburb') or tags.get('addr:district') or tags.get('addr:neighbourhood')
                        
                        # Guardar información de la calle
                        if street_name:
                            street_data['streets'].add(street_name)
                            
                            if street_name not in street_data['nodes_by_street']:
                                street_data['nodes_by_street'][street_name] = set()
                            
                            # Relacionar los nodos con esta calle
                            for node_id in way_nodes:
                                if node_id in nodes:
                                    street_data['nodes_by_street'][street_name].add(node_id)
                                    
                                    if node_id not in street_data['streets_by_node']:
                                        street_data['streets_by_node'][node_id] = set()
                                    
                                    street_data['streets_by_node'][node_id].add(street_name)
                        
                        # Guardar información del barrio
                        if neighborhood:
                            street_data['neighborhoods'].add(neighborhood)
                            
                            if neighborhood not in street_data['nodes_by_neighborhood']:
                                street_data['nodes_by_neighborhood'][neighborhood] = set()
                            
                            # Relacionar los nodos con este barrio
                            for node_id in way_nodes:
                                if node_id in nodes:
                                    street_data['nodes_by_neighborhood'][neighborhood].add(node_id)
                        
                        # Añadir aristas
                        for i in range(len(way_nodes) - 1):
                            if way_nodes[i] in nodes and way_nodes[i+1] in nodes:
                                node1 = way_nodes[i]
                                node2 = way_nodes[i+1]
                                
                                # Añadir aristas según dirección
                                if oneway == 'yes':
                                    street_graph.add_edge(node1, node2, weight=1.0, street_name=street_name, way_id=way_id)
                                else:
                                    street_graph.add_edge(node1, node2, weight=1.0, street_name=street_name, way_id=way_id)
                                    street_graph.add_edge(node2, node1, weight=1.0, street_name=street_name, way_id=way_id)
            
            # Construir el índice de intersecciones
            self._build_intersection_index(street_data)
            
            print(f"Grafo cargado con {len(street_graph.nodes())} nodos y {len(street_graph.edges())} aristas")
            print(f"Se encontraron {len(street_data['streets'])} calles y {len(street_data['neighborhoods'])} barrios")
            
            return street_graph, street_data
            
        except Exception as e:
            print(f"Error cargando el grafo: {e}")
            # Crear un grafo mínimo para desarrollo
            street_graph = nx.MultiDiGraph()
            for i in range(100):
                street_graph.add_node(i, lat=23.1136 + random.uniform(-0.01, 0.01), 
                                     lon=-82.3666 + random.uniform(-0.01, 0.01))
            
            # Conectar nodos
            for i in range(99):
                street_graph.add_edge(i, i+1, weight=1.0)
                street_graph.add_edge(i+1, i, weight=1.0)
            
            print("Usando grafo de desarrollo con 100 nodos")
            return street_graph, {}
    
    def _build_intersection_index(self, street_data: Dict):
        """Construye un índice de intersecciones de calles"""
        for node_id, streets in street_data['streets_by_node'].items():
            if len(streets) >= 2:
                # Este nodo representa una intersección de al menos 2 calles
                streets_list = sorted(list(streets))
                for i in range(len(streets_list)):
                    for j in range(i+1, len(streets_list)):
                        street1 = streets_list[i]
                        street2 = streets_list[j]
                        intersection_key = f"{street1} y {street2}"
                        
                        if intersection_key not in street_data['intersections']:
                            street_data['intersections'][intersection_key] = set()
                        
                        street_data['intersections'][intersection_key].add(node_id)
    
    def find_street_by_name(self, street_name: str) -> List[str]:
        """Encuentra calles cuyo nombre coincide o se parece al proporcionado"""
        if not street_name or not self.street_data:
            return []
        
        # Buscar coincidencias exactas primero
        matches = [s for s in self.street_data['streets'] if street_name.lower() in s.lower()]
        
        # Si no hay coincidencias exactas, buscar similares
        if not matches:
            matches = difflib.get_close_matches(street_name, self.street_data['streets'], n=5, cutoff=0.6)
        
        return matches
    
    def find_intersection(self, street1: str, street2: str) -> List[int]:
        """Encuentra nodos que representan la intersección de dos calles"""
        if not street1 or not street2 or not self.street_data:
            return []
        
        # Buscar coincidencias exactas para ambas calles
        street1_matches = self.find_street_by_name(street1)
        street2_matches = self.find_street_by_name(street2)
        
        if not street1_matches or not street2_matches:
            return []
        
        # Buscar intersecciones para cada combinación de coincidencias
        intersection_nodes = []
        for s1 in street1_matches:
            for s2 in street2_matches:
                intersection_key = f"{s1} y {s2}"
                alt_intersection_key = f"{s2} y {s1}"
                
                if intersection_key in self.street_data['intersections']:
                    intersection_nodes.extend(self.street_data['intersections'][intersection_key])
                elif alt_intersection_key in self.street_data['intersections']:
                    intersection_nodes.extend(self.street_data['intersections'][alt_intersection_key])
        
        return list(set(intersection_nodes))
    
    def find_location_by_address(self, address: str) -> List[int]:
        """Busca nodos correspondientes a una dirección en lenguaje natural"""
        if not address or not self.street_data:
            return []
        
        # Consultar a Gemini para extraer información de la dirección
        prompt = f"""
        El usuario ha proporcionado esta dirección en La Habana, Cuba: "{address}"
        
        Por favor, extrae la siguiente información de la dirección:
        1. Nombres de calles mencionadas (puede ser una o dos calles si es una intersección)
        2. Número de la calle (si se proporciona)
        3. Barrio o zona (como Vedado, Centro Habana, Miramar, etc.)
        
        Responde con un formato JSON estructurado así:
        {{
            "calle1": "nombre de la primera calle",
            "calle2": "nombre de la segunda calle o vacío si no hay",
            "numero": "número de la calle o vacío",
            "barrio": "nombre del barrio o vacío"
        }}
        
        Solo proporciona el JSON sin texto adicional.
        """
        
        try:
            response = self.gemini.ask(prompt)
            address_info = json.loads(response)
            
            # Extraer información
            street1 = address_info.get('calle1', '')
            street2 = address_info.get('calle2', '')
            street_number = address_info.get('numero', '')
            neighborhood = address_info.get('barrio', '')
            
            # Buscar nodos
            if street1 and street2:
                # Caso de intersección
                return self.find_intersection(street1, street2)
            elif street1:
                # Caso de una sola calle
                street_matches = self.find_street_by_name(street1)
                nodes = []
                
                for street in street_matches:
                    if street in self.street_data['nodes_by_street']:
                        nodes.extend(self.street_data['nodes_by_street'][street])
                
                # Filtrar por barrio si está disponible
                if neighborhood and nodes:
                    neighborhood_matches = difflib.get_close_matches(neighborhood, self.street_data['neighborhoods'], n=3, cutoff=0.6)
                    if neighborhood_matches:
                        neighborhood_nodes = set()
                        for n in neighborhood_matches:
                            if n in self.street_data['nodes_by_neighborhood']:
                                neighborhood_nodes.update(self.street_data['nodes_by_neighborhood'][n])
                        
                        # Intersección de nodos de calle y barrio
                        nodes = list(set(nodes).intersection(neighborhood_nodes))
                
                return nodes
            elif neighborhood:
                # Solo tenemos barrio
                neighborhood_matches = difflib.get_close_matches(neighborhood, self.street_data['neighborhoods'], n=1, cutoff=0.6)
                if neighborhood_matches and neighborhood_matches[0] in self.street_data['nodes_by_neighborhood']:
                    return list(self.street_data['nodes_by_neighborhood'][neighborhood_matches[0]])
        
        except Exception as e:
            print(f"Error procesando dirección: {e}")
        
        # Si no se encontró nada o hubo un error
        return []
    
    def get_node_address(self, node_id: int) -> str:
        """Devuelve la dirección legible para un nodo del grafo"""
        if not node_id in self.street_graph:
            return f"Nodo {node_id}"
        
        # Obtener calles asociadas al nodo
        streets = self.street_data['streets_by_node'].get(node_id, set())
        neighborhood = None
        
        # Buscar barrio
        for n, nodes in self.street_data['nodes_by_neighborhood'].items():
            if node_id in nodes:
                neighborhood = n
                break
        
        # Formar dirección
        if len(streets) >= 2:
            streets_list = list(streets)
            address = f"{streets_list[0]} y {streets_list[1]}"
        elif len(streets) == 1:
            address = next(iter(streets))
        else:
            # Si no hay información de calles, usar coordenadas
            lat = self.street_graph.nodes[node_id].get('lat')
            lon = self.street_graph.nodes[node_id].get('lon')
            address = f"Coordenadas ({lat:.6f}, {lon:.6f})"
        
        # Añadir barrio si está disponible
        if neighborhood:
            address += f", {neighborhood}"
        
        return address
    
    def get_random_addresses(self, n: int) -> List[str]:
        """Devuelve n direcciones aleatorias para sugerencias"""
        if not self.street_data or not self.street_data['intersections']:
            # Si no hay datos de calles, devolver nodos aleatorios
            random_nodes = self.get_random_nodes(n)
            return [f"Nodo {node}" for node in random_nodes]
        
        # Seleccionar intersecciones aleatorias
        intersections = list(self.street_data['intersections'].keys())
        if len(intersections) < n:
            sample = intersections
        else:
            sample = random.sample(intersections, n)
        
        return sample
    
    def get_random_nodes(self, n: int) -> List[int]:
        """Obtiene n nodos aleatorios del grafo para sugerencias"""
        if n >= len(self.all_nodes):
            return random.sample(self.all_nodes, len(self.all_nodes))
        return random.sample(self.all_nodes, n)
    
    def validate_node(self, node_id) -> bool:
        """Valida si un nodo existe en el grafo"""
        try:
            node_id = int(node_id)
            return node_id in self.all_nodes
        except (ValueError, TypeError):
            return False
    
    def process_start_point(self, text: str) -> Tuple[bool, str]:
        """Procesa la respuesta del usuario para el punto de inicio como dirección"""
        if not text.strip():
            return False, "Por favor, proporciona una dirección para el punto de inicio."
        
        nodes = self.find_location_by_address(text)
        
        if not nodes:
            return False, f"No pude encontrar una ubicación para '{text}'. Por favor, intenta con otra dirección."
        
        # Tomar el primer nodo encontrado (podría mejorarse para elegir el más relevante)
        node_id = nodes[0]
        self.params["start_point"] = node_id
        
        # Obtener dirección legible
        address = self.get_node_address(node_id)
        
        return True, f"He localizado el depósito en {address} (nodo {node_id})."
    
    def process_target_points(self, text: str) -> Tuple[bool, str]:
        """Procesa la respuesta del usuario para los puntos objetivo como direcciones"""
        if not text.strip():
            return False, "Por favor, proporciona al menos una dirección para los puntos objetivo."
        
        # Consultar a Gemini para extraer las direcciones individuales
        prompt = f"""
        El usuario ha proporcionado la siguiente lista de direcciones en La Habana, Cuba:
        "{text}"
        
        Por favor, extrae cada dirección individual de la lista. Las direcciones pueden estar separadas por comas, puntos y comas, o nuevas líneas.
        
        Responde con un formato JSON estructurado así:
        {{
            "direcciones": [
                "primera dirección",
                "segunda dirección",
                "etc..."
            ]
        }}
        
        Solo proporciona el JSON sin texto adicional.
        """
        
        try:
            response = self.gemini.ask(prompt)
            addresses_info = json.loads(response)
            addresses = addresses_info.get('direcciones', [])
            
            if not addresses:
                return False, "No pude identificar ninguna dirección en tu respuesta."
            
            valid_nodes = []
            invalid_addresses = []
            
            for address in addresses:
                nodes = self.find_location_by_address(address)
                if nodes:
                    # Tomar el primer nodo encontrado
                    valid_nodes.append(nodes[0])
                else:
                    invalid_addresses.append(address)
            
            if valid_nodes:
                self.params["target_points"] = valid_nodes
                
                # Preparar mensaje con direcciones legibles
                locations = [self.get_node_address(node) for node in valid_nodes]
                
                msg = f"He registrado {len(valid_nodes)} puntos objetivo:"
                for i, loc in enumerate(locations):
                    msg += f"\n{i+1}. {loc} (nodo {valid_nodes[i]})"
                
                if invalid_addresses:
                    msg += f"\n\nNo pude encontrar las siguientes direcciones: {', '.join(invalid_addresses)}"
                
                return True, msg
            else:
                return False, f"No pude encontrar ninguna ubicación válida. Las direcciones no fueron reconocidas: {', '.join(invalid_addresses)}"
                
        except Exception as e:
            print(f"Error procesando direcciones objetivo: {e}")
            return False, "Hubo un error al procesar las direcciones. Por favor, intenta con un formato más simple."
    
    def process_num_trucks(self, text: str) -> Tuple[bool, str]:
        """Procesa la respuesta del usuario para el número de camiones"""
        prompt = f"""
        El usuario está proporcionando información sobre el número de camiones para un problema CVRP.
        Su respuesta es: "{text}"
        
        Necesito extraer un número entero positivo de esta respuesta.
        
        Responde solo con el número, sin texto adicional.
        Si no puedes identificar un número claro, responde con "no_number".
        """
        
        response = self.gemini.ask(prompt)
        
        if response.strip().lower() == "no_number":
            return False, "No pude identificar un número válido en tu respuesta."
        
        try:
            num_trucks = int(response.strip())
            if num_trucks > 0:
                self.params["num_trucks"] = num_trucks
                return True, f"He registrado {num_trucks} camiones."
            else:
                return False, "El número de camiones debe ser mayor que cero."
        except ValueError:
            return False, "No pude identificar un número válido en tu respuesta."
    
    def process_truck_capacities(self, text: str) -> Tuple[bool, str]:
        """Procesa la respuesta del usuario para las capacidades de los camiones"""
        prompt = f"""
        El usuario está proporcionando información sobre las capacidades de los camiones para un problema CVRP.
        Su respuesta es: "{text}"
        Necesitamos {self.params["num_trucks"]} valores de capacidad.
        
        Necesito extraer una lista de números positivos de esta respuesta.
        
        Responde con una lista de números separados por comas, sin texto adicional.
        Si no puedes identificar ningún número, responde con "no_numbers".
        """
        
        response = self.gemini.ask(prompt)
        
        if response.strip().lower() == "no_numbers":
            return False, "No pude identificar valores válidos en tu respuesta."
        
        try:
            capacities = [int(cap.strip()) for cap in response.split(',')]
            
            # Validar que sean positivos
            if all(cap > 0 for cap in capacities):
                # Si hay menos capacidades que camiones, repetir la última
                while len(capacities) < self.params["num_trucks"]:
                    capacities.append(capacities[-1])
                
                # Si hay más capacidades que camiones, recortar
                if len(capacities) > self.params["num_trucks"]:
                    capacities = capacities[:self.params["num_trucks"]]
                
                self.params["truck_capacities"] = capacities
                return True, f"He registrado las capacidades: {capacities}."
            else:
                return False, "Todas las capacidades deben ser mayores que cero."
        except ValueError:
            return False, "No pude identificar valores válidos en tu respuesta."
    
    def process_target_demands(self, text: str) -> Tuple[bool, str]:
        """Procesa la respuesta del usuario para las demandas de los puntos objetivo"""
        prompt = f"""
        El usuario está proporcionando información sobre las demandas de los puntos objetivo para un problema CVRP.
        Su respuesta es: "{text}"
        Necesitamos {len(self.params["target_points"])} valores de demanda, uno para cada punto objetivo.
        
        Necesito extraer una lista de números positivos de esta respuesta.
        
        Responde con una lista de números separados por comas, sin texto adicional.
        Si no puedes identificar ningún número, responde con "no_numbers".
        """
        
        response = self.gemini.ask(prompt)
        
        if response.strip().lower() == "no_numbers":
            return False, "No pude identificar valores válidos en tu respuesta."
        
        try:
            demands = [int(dem.strip()) for dem in response.split(',')]
            
            # Validar que sean positivos
            if all(dem > 0 for dem in demands):
                # Si hay menos demandas que puntos objetivo, repetir la última
                while len(demands) < len(self.params["target_points"]):
                    demands.append(demands[-1])
                
                # Si hay más demandas que puntos objetivo, recortar
                if len(demands) > len(self.params["target_points"]):
                    demands = demands[:len(self.params["target_points"])]
                
                self.params["target_demands"] = demands
                return True, f"He registrado las demandas: {demands}."
            else:
                return False, "Todas las demandas deben ser mayores que cero."
        except ValueError:
            return False, "No pude identificar valores válidos en tu respuesta."
    
    def interact(self, user_input: str = None) -> str:
        """Interactúa con el usuario para obtener los parámetros"""
        # Primer mensaje sin entrada del usuario
        if self.conversation_state == "start" and not user_input:
            self.conversation_state = "ask_start_point"
            random_addresses = self.get_random_addresses(3)
            return (f"¡Hola! Te ayudaré a configurar tu problema CVRP para La Habana. "
                   f"Primero, necesito saber la dirección del punto de inicio (depósito). "
                   f"Puedes especificar una dirección como una intersección (ej: 'Calle 23 y L, Vedado') "
                   f"o cualquier ubicación en La Habana.\n\n"
                   f"Algunos ejemplos de direcciones válidas: {', '.join(random_addresses)}.")
        
        # Procesar la respuesta del usuario según el estado
        if self.conversation_state == "ask_start_point":
            success, message = self.process_start_point(user_input)
            if success:
                self.conversation_state = "ask_target_points"
                random_addresses = self.get_random_addresses(2)
                return (f"{message}\n\n"
                       f"Ahora, necesito las direcciones de los puntos objetivo (destinos). "
                       f"Puedes proporcionarme una lista de direcciones separadas por comas o en líneas separadas. "
                       f"Por ejemplo: '{random_addresses[0]}; {random_addresses[1]}'")
            else:
                random_addresses = self.get_random_addresses(3)
                return (f"{message}\n\n"
                       f"Ejemplos de direcciones válidas: {', '.join(random_addresses)}. "
                       f"Por favor, intenta de nuevo.")
        
        elif self.conversation_state == "ask_target_points":
            success, message = self.process_target_points(user_input)
            if success:
                self.conversation_state = "ask_num_trucks"
                return f"{message}\n\n¿Cuántos camiones deseas utilizar?"
            else:
                random_addresses = self.get_random_addresses(3)
                return (f"{message}\n\n"
                       f"Ejemplos de direcciones válidas: {', '.join(random_addresses)}. "
                       f"Por favor, intenta de nuevo.")
        
        elif self.conversation_state == "ask_num_trucks":
            success, message = self.process_num_trucks(user_input)
            if success:
                self.conversation_state = "ask_truck_capacities"
                return f"{message}\n\nAhora, ¿cuáles son las capacidades de los camiones? Dame {self.params['num_trucks']} valores separados por comas."
            else:
                return f"{message}\n\nPor favor, proporciona un número entero positivo."
        
        elif self.conversation_state == "ask_truck_capacities":
            success, message = self.process_truck_capacities(user_input)
            if success:
                self.conversation_state = "ask_target_demands"
                return f"{message}\n\nPor último, ¿cuáles son las demandas de los puntos objetivo? Dame {len(self.params['target_points'])} valores separados por comas."
            else:
                return f"{message}\n\nPor favor, proporciona {self.params['num_trucks']} valores positivos separados por comas."
        
        elif self.conversation_state == "ask_target_demands":
            success, message = self.process_target_demands(user_input)
            if success:
                self.conversation_state = "completed"
                self.save_params()
                return f"{message}\n\n¡Perfecto! He guardado todos los parámetros necesarios para resolver tu problema CVRP. El archivo de configuración está listo para ser utilizado con optimized_route.py."
            else:
                return f"{message}\n\nPor favor, proporciona {len(self.params['target_points'])} valores positivos separados por comas."
        
        elif self.conversation_state == "completed":
            return "Ya he recopilado toda la información necesaria. El archivo de configuración está listo para ser utilizado con optimized_route.py."
        
        return "Lo siento, ha ocurrido un error en la conversación."
    
    def save_params(self) -> None:
        """Guarda los parámetros en un archivo JSON"""
        output_file = os.path.join("cache", "cvrp_params.json")
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Formatear los parámetros como espera optimized_route.py
        formatted_params = {
            "start_point": self.params["start_point"],
            "target_points": self.params["target_points"],
            "num_trucks": self.params["num_trucks"],
            "truck_capacities": self.params["truck_capacities"],
            "target_demands": self.params["target_demands"]
        }
        
        with open(output_file, 'w') as f:
            json.dump(formatted_params, f, indent=2)
        
        print(f"Parámetros guardados en {output_file}")

# Script principal para usar el asistente
def main():
    assistant = CVRPAssistant()
    
    print(assistant.interact())  # Mensaje inicial
    
    while assistant.conversation_state != "completed":
        user_input = input("> ")
        response = assistant.interact(user_input)
        print(response)
    
    print("\nTodos los parámetros han sido recopilados y guardados. ¡Gracias!")

if __name__ == "__main__":
    main()