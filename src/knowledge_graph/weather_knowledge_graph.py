"""
Grafo de Conocimiento del Clima para Logística Urbana
Basado en los principios del paper: Representación del conocimiento con grafos
"""

import networkx as nx
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class WeatherCondition(Enum):
    """Condiciones climáticas principales"""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAINY = "rainy"
    STORMY = "stormy"
    FOGGY = "foggy"
    WINDY = "windy"


class TransportImpact(Enum):
    """Niveles de impacto en el transporte"""
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"


@dataclass
class WeatherEntity:
    """Entidad del grafo de conocimiento"""
    id: str
    name: str
    type: str
    properties: Dict[str, Any]


@dataclass
class WeatherRelation:
    """Relación entre entidades del grafo"""
    source: str
    target: str
    relation_type: str
    weight: float
    properties: Dict[str, Any]


class WeatherKnowledgeGraph:
    """
    Grafo de conocimiento para modelar relaciones clima-transporte
    """
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.entities = {}
        self.relations = []
        self._initialize_knowledge_base()
    
    def _initialize_knowledge_base(self):
        """Inicializa la base de conocimiento con reglas predefinidas"""
        
        # Entidades climáticas
        weather_entities = [
            WeatherEntity("clear_sky", "Cielo Despejado", "weather_condition", 
                         {"visibility": "excellent", "precipitation": 0, "wind_factor": 0.1}),
            WeatherEntity("light_clouds", "Nubosidad Ligera", "weather_condition",
                         {"visibility": "good", "precipitation": 0, "wind_factor": 0.2}),
            WeatherEntity("heavy_clouds", "Nubosidad Densa", "weather_condition",
                         {"visibility": "moderate", "precipitation": 0, "wind_factor": 0.3}),
            WeatherEntity("light_rain", "Lluvia Ligera", "weather_condition",
                         {"visibility": "reduced", "precipitation": 2, "wind_factor": 0.4}),
            WeatherEntity("moderate_rain", "Lluvia Moderada", "weather_condition",
                         {"visibility": "poor", "precipitation": 5, "wind_factor": 0.6}),
            WeatherEntity("heavy_rain", "Lluvia Intensa", "weather_condition",
                         {"visibility": "very_poor", "precipitation": 10, "wind_factor": 0.8}),
            WeatherEntity("thunderstorm", "Tormenta", "weather_condition",
                         {"visibility": "very_poor", "precipitation": 15, "wind_factor": 1.0}),
            WeatherEntity("fog", "Niebla", "weather_condition",
                         {"visibility": "very_poor", "precipitation": 0, "wind_factor": 0.2}),
            WeatherEntity("strong_wind", "Viento Fuerte", "weather_condition",
                         {"visibility": "moderate", "precipitation": 0, "wind_factor": 0.9})
        ]
        
        # Entidades de impacto en transporte
        transport_entities = [
            WeatherEntity("normal_speed", "Velocidad Normal", "transport_impact",
                         {"speed_factor": 1.0, "risk_level": "low", "delay_probability": 0.05}),
            WeatherEntity("reduced_speed", "Velocidad Reducida", "transport_impact",
                         {"speed_factor": 0.8, "risk_level": "moderate", "delay_probability": 0.15}),
            WeatherEntity("slow_speed", "Velocidad Lenta", "transport_impact",
                         {"speed_factor": 0.6, "risk_level": "high", "delay_probability": 0.30}),
            WeatherEntity("very_slow_speed", "Velocidad Muy Lenta", "transport_impact",
                         {"speed_factor": 0.4, "risk_level": "very_high", "delay_probability": 0.50}),
            WeatherEntity("dangerous_conditions", "Condiciones Peligrosas", "transport_impact",
                         {"speed_factor": 0.2, "risk_level": "extreme", "delay_probability": 0.80})
        ]
        
        # Agregar entidades al grafo
        all_entities = weather_entities + transport_entities
        for entity in all_entities:
            self.add_entity(entity)
        
        # Definir relaciones clima-transporte
        relations = [
            # Condiciones favorables
            WeatherRelation("clear_sky", "normal_speed", "causes", 1.0, {"confidence": 0.95}),
            WeatherRelation("light_clouds", "normal_speed", "causes", 0.9, {"confidence": 0.90}),
            
            # Condiciones moderadas
            WeatherRelation("heavy_clouds", "reduced_speed", "causes", 0.8, {"confidence": 0.85}),
            WeatherRelation("light_rain", "reduced_speed", "causes", 0.9, {"confidence": 0.90}),
            
            # Condiciones adversas
            WeatherRelation("moderate_rain", "slow_speed", "causes", 0.9, {"confidence": 0.95}),
            WeatherRelation("heavy_rain", "very_slow_speed", "causes", 0.95, {"confidence": 0.98}),
            WeatherRelation("fog", "slow_speed", "causes", 0.85, {"confidence": 0.90}),
            WeatherRelation("strong_wind", "reduced_speed", "causes", 0.75, {"confidence": 0.80}),
            
            # Condiciones extremas
            WeatherRelation("thunderstorm", "dangerous_conditions", "causes", 1.0, {"confidence": 0.99})
        ]
        
        # Agregar relaciones al grafo
        for relation in relations:
            self.add_relation(relation)
    
    def add_entity(self, entity: WeatherEntity):
        """Agrega una entidad al grafo de conocimiento"""
        self.entities[entity.id] = entity
        self.graph.add_node(entity.id, **entity.properties, name=entity.name, type=entity.type)
    
    def add_relation(self, relation: WeatherRelation):
        """Agrega una relación al grafo de conocimiento"""
        self.relations.append(relation)
        self.graph.add_edge(
            relation.source, 
            relation.target, 
            relation_type=relation.relation_type,
            weight=relation.weight,
            **relation.properties
        )
    
    def query_weather_impact(self, weather_conditions: Dict[str, Any]) -> Dict[str, float]:
        """
        Consulta el impacto del clima en el transporte
        
        Args:
            weather_conditions: Diccionario con condiciones climáticas actuales
            
        Returns:
            Diccionario con factores de impacto
        """
        # Clasificar las condiciones climáticas
        weather_entity = self._classify_weather(weather_conditions)
        
        if not weather_entity:
            return {"speed_factor": 1.0, "delay_probability": 0.05, "risk_level": "low"}
        
        # Buscar impactos relacionados
        impacts = []
        for successor in self.graph.successors(weather_entity):
            edge_data = self.graph[weather_entity][successor]
            if edge_data.get('relation_type') == 'causes':
                node_data = self.graph.nodes[successor]
                impact = {
                    "speed_factor": node_data.get('speed_factor', 1.0),
                    "delay_probability": node_data.get('delay_probability', 0.05),
                    "risk_level": node_data.get('risk_level', 'low'),
                    "confidence": edge_data.get('confidence', 0.5),
                    "weight": edge_data.get('weight', 1.0)
                }
                impacts.append(impact)
        
        if not impacts:
            return {"speed_factor": 1.0, "delay_probability": 0.05, "risk_level": "low"}
        
        # Seleccionar el impacto con mayor confianza
        best_impact = max(impacts, key=lambda x: x['confidence'])
        return best_impact
    
    def _classify_weather(self, conditions: Dict[str, Any]) -> Optional[str]:
        """Clasifica las condiciones climáticas en una entidad del grafo"""
        precipitation = conditions.get('precipitation', 0)
        cloud_cover = conditions.get('cloud_cover', 0)
        wind_speed = conditions.get('wind_speed', 0)
        visibility = conditions.get('visibility', 10000)
        weather_code = conditions.get('weather_code', 0)
        
        # Condiciones extremas
        if weather_code in [95, 96, 99]:  # Tormentas eléctricas
            return "thunderstorm"
        
        if visibility < 1000:  # Niebla densa
            return "fog"
        
        if wind_speed > 50:  # Viento fuerte (km/h)
            return "strong_wind"
        
        # Condiciones de lluvia
        if precipitation > 10:
            return "heavy_rain"
        elif precipitation > 5:
            return "moderate_rain"
        elif precipitation > 0:
            return "light_rain"
        
        # Condiciones de nubosidad
        if cloud_cover > 75:
            return "heavy_clouds"
        elif cloud_cover > 25:
            return "light_clouds"
        else:
            return "clear_sky"
    
    def get_route_weight_multiplier(self, weather_conditions: Dict[str, Any]) -> float:
        """
        Calcula el multiplicador de peso para las aristas de rutas basado en el clima
        
        Returns:
            Factor multiplicativo para el peso de las aristas (1.0 = normal, >1.0 = más pesado)
        """
        impact = self.query_weather_impact(weather_conditions)
        speed_factor = impact.get('speed_factor', 1.0)
        delay_probability = impact.get('delay_probability', 0.05)
        
        # El peso aumenta inversamente al factor de velocidad
        # También considera la probabilidad de retrasos
        weight_multiplier = (1.0 / speed_factor) * (1.0 + delay_probability)
        
        return weight_multiplier
    
    def export_knowledge_graph(self, filepath: str):
        """Exporta el grafo de conocimiento a un archivo JSON"""
        data = {
            "entities": [
                {
                    "id": entity.id,
                    "name": entity.name,
                    "type": entity.type,
                    "properties": entity.properties
                }
                for entity in self.entities.values()
            ],
            "relations": [
                {
                    "source": rel.source,
                    "target": rel.target,
                    "relation_type": rel.relation_type,
                    "weight": rel.weight,
                    "properties": rel.properties
                }
                for rel in self.relations
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def visualize_graph(self, filepath: str = None):
        """Genera una visualización del grafo de conocimiento"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            
            plt.figure(figsize=(14, 10))
            
            # Posiciones para el layout
            pos = nx.spring_layout(self.graph, k=3, iterations=50)
            
            # Separar nodos por tipo
            weather_nodes = [n for n in self.graph.nodes() if self.graph.nodes[n]['type'] == 'weather_condition']
            impact_nodes = [n for n in self.graph.nodes() if self.graph.nodes[n]['type'] == 'transport_impact']
            
            # Dibujar nodos
            nx.draw_networkx_nodes(self.graph, pos, nodelist=weather_nodes, 
                                 node_color='lightblue', node_size=1500, alpha=0.8, label='Condiciones Climáticas')
            nx.draw_networkx_nodes(self.graph, pos, nodelist=impact_nodes, 
                                 node_color='lightcoral', node_size=1500, alpha=0.8, label='Impacto en Transporte')
            
            # Dibujar aristas con diferentes colores según el peso
            edges = self.graph.edges(data=True)
            edge_weights = [d['weight'] for _, _, d in edges]
            nx.draw_networkx_edges(self.graph, pos, edge_color=edge_weights, 
                                 edge_cmap=plt.cm.Reds, width=2, alpha=0.7)
            
            # Etiquetas
            labels = {n: self.graph.nodes[n]['name'][:15] + "..." if len(self.graph.nodes[n]['name']) > 15 
                     else self.graph.nodes[n]['name'] for n in self.graph.nodes()}
            nx.draw_networkx_labels(self.graph, pos, labels, font_size=8, font_weight='bold')
            
            plt.title("Grafo de Conocimiento: Clima y Transporte", fontsize=16, fontweight='bold')
            plt.legend()
            plt.axis('off')
            plt.tight_layout()
            
            if filepath:
                plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.show()
            
        except ImportError:
            print("Matplotlib no disponible para visualización")


if __name__ == "__main__":
    # Ejemplo de uso
    kg = WeatherKnowledgeGraph()
    
    # Probar consultas
    test_conditions = {
        'precipitation': 8,
        'cloud_cover': 90,
        'wind_speed': 25,
        'visibility': 5000,
        'weather_code': 61
    }
    
    impact = kg.query_weather_impact(test_conditions)
    print(f"Impacto del clima: {impact}")
    
    weight_multiplier = kg.get_route_weight_multiplier(test_conditions)
    print(f"Multiplicador de peso para rutas: {weight_multiplier:.2f}")
    
    # Exportar grafo
    kg.export_knowledge_graph("weather_knowledge_graph.json")
    
    # Visualizar (opcional)
    # kg.visualize_graph("weather_knowledge_graph.png")
