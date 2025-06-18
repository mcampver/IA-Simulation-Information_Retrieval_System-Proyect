"""
Grafo de Conocimiento Extendido para Optimización de Rutas
Incluye tipos de calles, superficies, y factores de afectación del sistema de rutas
"""

import json
import networkx as nx
from typing import Dict, List
import os

class ExtendedKnowledgeGraph:
    def __init__(self):
        """Inicializa el grafo de conocimiento extendido"""
        self.entities = []
        self.relations = []
        self.graph = nx.DiGraph()
        
    def create_extended_knowledge_graph(self):
        """Crea un grafo de conocimiento que incluye todos los factores de optimized_route.py"""
        
        # ============ CONDICIONES CLIMÁTICAS ============
        weather_conditions = [
            {
                "id": "clear_sky",
                "name": "Cielo Despejado",
                "type": "weather_condition",
                "properties": {
                    "visibility": "excellent",
                    "precipitation": 0,
                    "wind_factor": 0.1,
                    "impact_multiplier": 1.0
                }
            },
            {
                "id": "light_clouds",
                "name": "Nubosidad Ligera",
                "type": "weather_condition",
                "properties": {
                    "visibility": "good",
                    "precipitation": 0,
                    "wind_factor": 0.2,
                    "impact_multiplier": 1.05
                }
            },
            {
                "id": "heavy_clouds",
                "name": "Nubosidad Densa",
                "type": "weather_condition",
                "properties": {
                    "visibility": "moderate",
                    "precipitation": 0,
                    "wind_factor": 0.3,
                    "impact_multiplier": 1.1
                }
            },
            {
                "id": "light_rain",
                "name": "Lluvia Ligera",
                "type": "weather_condition",
                "properties": {
                    "visibility": "reduced",
                    "precipitation": 2,
                    "wind_factor": 0.4,
                    "impact_multiplier": 1.2
                }
            },
            {
                "id": "moderate_rain",
                "name": "Lluvia Moderada",
                "type": "weather_condition",
                "properties": {
                    "visibility": "poor",
                    "precipitation": 5,
                    "wind_factor": 0.6,
                    "impact_multiplier": 1.4
                }
            },
            {
                "id": "heavy_rain",
                "name": "Lluvia Intensa",
                "type": "weather_condition",
                "properties": {
                    "visibility": "very_poor",
                    "precipitation": 10,
                    "wind_factor": 0.8,
                    "impact_multiplier": 1.7
                }
            },
            {
                "id": "storm",
                "name": "Tormenta",
                "type": "weather_condition",
                "properties": {
                    "visibility": "extremely_poor",
                    "precipitation": 15,
                    "wind_factor": 1.0,
                    "impact_multiplier": 2.0
                }
            }
        ]
        
        # ============ TIPOS DE CARRETERA ============
        road_types = [
            {
                "id": "motorway",
                "name": "Autopista",
                "type": "road_type",
                "properties": {
                    "weather_resistance": 0.8,
                    "capacity": "very_high",
                    "speed_limit": 120,
                    "lanes": "4+",
                    "surface_quality": "excellent",
                    "maintenance_level": "high"
                }
            },
            {
                "id": "trunk",
                "name": "Vía Principal",
                "type": "road_type",
                "properties": {
                    "weather_resistance": 0.85,
                    "capacity": "high",
                    "speed_limit": 90,
                    "lanes": "2-4",
                    "surface_quality": "very_good",
                    "maintenance_level": "high"
                }
            },
            {
                "id": "primary",
                "name": "Carretera Primaria",
                "type": "road_type",
                "properties": {
                    "weather_resistance": 0.9,
                    "capacity": "medium_high",
                    "speed_limit": 70,
                    "lanes": "2-4",
                    "surface_quality": "good",
                    "maintenance_level": "medium_high"
                }
            },
            {
                "id": "secondary",
                "name": "Carretera Secundaria",
                "type": "road_type",
                "properties": {
                    "weather_resistance": 1.0,
                    "capacity": "medium",
                    "speed_limit": 50,
                    "lanes": "2",
                    "surface_quality": "good",
                    "maintenance_level": "medium"
                }
            },
            {
                "id": "tertiary",
                "name": "Carretera Terciaria",
                "type": "road_type",
                "properties": {
                    "weather_resistance": 1.1,
                    "capacity": "medium_low",
                    "speed_limit": 40,
                    "lanes": "1-2",
                    "surface_quality": "fair",
                    "maintenance_level": "medium"
                }
            },
            {
                "id": "residential",
                "name": "Calle Residencial",
                "type": "road_type",
                "properties": {
                    "weather_resistance": 1.2,
                    "capacity": "low",
                    "speed_limit": 30,
                    "lanes": "1-2",
                    "surface_quality": "fair",
                    "maintenance_level": "low"
                }
            },
            {
                "id": "service",
                "name": "Calle de Servicio",
                "type": "road_type",
                "properties": {
                    "weather_resistance": 1.3,
                    "capacity": "very_low",
                    "speed_limit": 20,
                    "lanes": "1",
                    "surface_quality": "poor",
                    "maintenance_level": "low"
                }
            },
            {
                "id": "track",
                "name": "Camino Sin Pavimentar",
                "type": "road_type",
                "properties": {
                    "weather_resistance": 1.5,
                    "capacity": "very_low",
                    "speed_limit": 15,
                    "lanes": "1",
                    "surface_quality": "poor",
                    "maintenance_level": "very_low"
                }
            },
            {
                "id": "path",
                "name": "Sendero",
                "type": "road_type",
                "properties": {
                    "weather_resistance": 1.8,
                    "capacity": "minimal",
                    "speed_limit": 10,
                    "lanes": "0-1",
                    "surface_quality": "very_poor",
                    "maintenance_level": "none"
                }
            }
        ]
        
        # ============ TIPOS DE SUPERFICIE ============
        surface_types = [
            {
                "id": "asphalt",
                "name": "Asfalto",
                "type": "surface_type",
                "properties": {
                    "weather_factor": 1.0,
                    "durability": "high",
                    "grip": "good",
                    "drainage": "moderate",
                    "maintenance_cost": "medium"
                }
            },
            {
                "id": "concrete",
                "name": "Concreto",
                "type": "surface_type",
                "properties": {
                    "weather_factor": 0.9,
                    "durability": "very_high",
                    "grip": "excellent",
                    "drainage": "good",
                    "maintenance_cost": "low"
                }
            },
            {
                "id": "paved",
                "name": "Pavimentado",
                "type": "surface_type",
                "properties": {
                    "weather_factor": 1.0,
                    "durability": "high",
                    "grip": "good",
                    "drainage": "moderate",
                    "maintenance_cost": "medium"
                }
            },
            {
                "id": "unpaved",
                "name": "Sin Pavimentar",
                "type": "surface_type",
                "properties": {
                    "weather_factor": 1.4,
                    "durability": "low",
                    "grip": "poor",
                    "drainage": "poor",
                    "maintenance_cost": "high"
                }
            },
            {
                "id": "gravel",
                "name": "Grava",
                "type": "surface_type",
                "properties": {
                    "weather_factor": 1.3,
                    "durability": "medium",
                    "grip": "fair",
                    "drainage": "good",
                    "maintenance_cost": "medium"
                }
            },
            {
                "id": "dirt",
                "name": "Tierra",
                "type": "surface_type",
                "properties": {
                    "weather_factor": 1.6,
                    "durability": "very_low",
                    "grip": "very_poor",
                    "drainage": "very_poor",
                    "maintenance_cost": "very_high"
                }
            },
            {
                "id": "grass",
                "name": "Césped",
                "type": "surface_type",
                "properties": {
                    "weather_factor": 1.8,
                    "durability": "very_low",
                    "grip": "very_poor",
                    "drainage": "poor",
                    "maintenance_cost": "very_high"
                }
            }
        ]
        
        # ============ FACTORES DE TRANSPORTE ============
        transport_factors = [
            {
                "id": "lane_count",
                "name": "Número de Carriles",
                "type": "transport_factor",
                "properties": {
                    "description": "Afecta la disponibilidad de rutas alternativas",
                    "base_factor": 1.0,
                    "reduction_per_lane": 0.1,
                    "min_factor": 0.8
                }
            },
            {
                "id": "traffic_density",
                "name": "Densidad de Tráfico",
                "type": "transport_factor",
                "properties": {
                    "description": "Afecta la velocidad y tiempo de viaje",
                    "low": 1.0,
                    "medium": 1.3,
                    "high": 1.7,
                    "very_high": 2.2
                }
            },
            {
                "id": "vehicle_capacity",
                "name": "Capacidad del Vehículo",
                "type": "transport_factor",
                "properties": {
                    "description": "Determina la cantidad de entregas por ruta",
                    "default_capacity": 100,
                    "weight_limit": "kg",
                    "volume_limit": "m3"
                }
            },
            {
                "id": "delivery_demand",
                "name": "Demanda de Entrega",
                "type": "transport_factor",
                "properties": {
                    "description": "Cantidad requerida en cada punto de entrega",
                    "default_demand": 1,
                    "unit": "packages",
                    "affects_route_planning": True
                }
            }
        ]
        
        # ============ IMPACTOS ESPECÍFICOS ============
        transport_impacts = [
            {
                "id": "reduced_visibility",
                "name": "Visibilidad Reducida",
                "type": "transport_impact",
                "properties": {
                    "severity": "medium",
                    "affects_speed": True,
                    "safety_concern": True,
                    "time_penalty": 1.2
                }
            },
            {
                "id": "wet_surface",
                "name": "Superficie Mojada",
                "type": "transport_impact",
                "properties": {
                    "severity": "medium",
                    "affects_speed": True,
                    "safety_concern": True,
                    "time_penalty": 1.3
                }
            },
            {
                "id": "flooding_risk",
                "name": "Riesgo de Inundación",
                "type": "transport_impact",
                "properties": {
                    "severity": "high",
                    "affects_route": True,
                    "safety_concern": True,
                    "time_penalty": 2.0
                }
            },
            {
                "id": "road_damage",
                "name": "Daño en Carretera",
                "type": "transport_impact",
                "properties": {
                    "severity": "high",
                    "affects_route": True,
                    "maintenance_required": True,
                    "time_penalty": 1.8
                }
            }
        ]
        
        # Combinar todas las entidades
        self.entities = (weather_conditions + road_types + surface_types + 
                        transport_factors + transport_impacts)
        
        # ============ CREAR RELACIONES ============
        self._create_weather_road_relations()
        self._create_surface_road_relations()
        self._create_factor_impact_relations()
        self._create_optimization_relations()
        
        return {
            "entities": self.entities,
            "relations": self.relations
        }
    
    def _create_weather_road_relations(self):
        """Crea relaciones entre condiciones climáticas y tipos de carretera"""
        
        # Mapeo de intensidad de afectación climática por tipo de carretera
        weather_road_impacts = {
            "clear_sky": [
                ("motorway", 1.0, 0.95), ("trunk", 1.0, 0.95), ("primary", 1.0, 0.95),
                ("secondary", 1.0, 0.95), ("tertiary", 1.0, 0.95), ("residential", 1.0, 0.95),
                ("service", 1.0, 0.9), ("track", 1.0, 0.9), ("path", 1.0, 0.85)
            ],
            "light_rain": [
                ("motorway", 1.1, 0.9), ("trunk", 1.15, 0.85), ("primary", 1.2, 0.8),
                ("secondary", 1.3, 0.75), ("tertiary", 1.4, 0.7), ("residential", 1.5, 0.65),
                ("service", 1.7, 0.6), ("track", 2.0, 0.5), ("path", 2.5, 0.4)
            ],
            "moderate_rain": [
                ("motorway", 1.2, 0.85), ("trunk", 1.3, 0.8), ("primary", 1.4, 0.75),
                ("secondary", 1.6, 0.7), ("tertiary", 1.8, 0.65), ("residential", 2.0, 0.6),
                ("service", 2.3, 0.55), ("track", 2.8, 0.45), ("path", 3.5, 0.35)
            ],
            "heavy_rain": [
                ("motorway", 1.4, 0.8), ("trunk", 1.6, 0.75), ("primary", 1.8, 0.7),
                ("secondary", 2.2, 0.65), ("tertiary", 2.6, 0.6), ("residential", 3.0, 0.55),
                ("service", 3.5, 0.5), ("track", 4.2, 0.4), ("path", 5.0, 0.3)
            ],
            "storm": [
                ("motorway", 1.8, 0.7), ("trunk", 2.2, 0.65), ("primary", 2.6, 0.6),
                ("secondary", 3.2, 0.55), ("tertiary", 3.8, 0.5), ("residential", 4.5, 0.45),
                ("service", 5.2, 0.4), ("track", 6.0, 0.3), ("path", 7.0, 0.2)
            ]
        }
        
        for weather_id, road_impacts in weather_road_impacts.items():
            for road_id, impact_factor, confidence in road_impacts:
                self.relations.append({
                    "source": weather_id,
                    "target": road_id,
                    "relation_type": "affects_road_performance",
                    "weight": impact_factor,
                    "properties": {
                        "confidence": confidence,
                        "impact_type": "travel_time_multiplier",
                        "severity": self._get_severity_level(impact_factor)
                    }
                })
    
    def _create_surface_road_relations(self):
        """Crea relaciones entre tipos de superficie y tipos de carretera"""
        
        # Mapeo típico de superficies por tipo de carretera
        surface_road_mapping = [
            ("concrete", "motorway", 0.9, 0.95),
            ("asphalt", "motorway", 1.0, 0.9),
            ("asphalt", "trunk", 1.0, 0.95),
            ("asphalt", "primary", 1.0, 0.9),
            ("asphalt", "secondary", 1.0, 0.85),
            ("paved", "tertiary", 1.0, 0.8),
            ("asphalt", "residential", 1.0, 0.7),
            ("paved", "residential", 1.0, 0.6),
            ("asphalt", "service", 1.0, 0.5),
            ("unpaved", "service", 1.4, 0.4),
            ("gravel", "track", 1.3, 0.8),
            ("dirt", "track", 1.6, 0.7),
            ("unpaved", "track", 1.4, 0.9),
            ("dirt", "path", 1.6, 0.8),
            ("grass", "path", 1.8, 0.6)
        ]
        
        for surface_id, road_id, weight, confidence in surface_road_mapping:
            self.relations.append({
                "source": surface_id,
                "target": road_id,
                "relation_type": "typical_surface_for",
                "weight": weight,
                "properties": {
                    "confidence": confidence,
                    "relationship_type": "composition"
                }
            })
    
    def _create_factor_impact_relations(self):
        """Crea relaciones entre factores de transporte e impactos"""
        
        factor_impact_relations = [
            ("lane_count", "reduced_visibility", 0.8, 0.9),
            ("traffic_density", "reduced_visibility", 1.5, 0.85),
            ("vehicle_capacity", "wet_surface", 1.2, 0.8),
            ("delivery_demand", "flooding_risk", 1.0, 0.7),
            ("lane_count", "road_damage", 0.7, 0.9),
            ("traffic_density", "road_damage", 1.8, 0.95)
        ]
        
        for factor_id, impact_id, weight, confidence in factor_impact_relations:
            self.relations.append({
                "source": factor_id,
                "target": impact_id,
                "relation_type": "influences_impact",
                "weight": weight,
                "properties": {
                    "confidence": confidence,
                    "relationship_type": "causation"
                }
            })
    
    def _create_optimization_relations(self):
        """Crea relaciones que afectan la optimización de rutas"""
        
        # Relaciones de optimización basadas en el análisis de optimized_route.py
        optimization_relations = [
            # Clima afecta diferentes superficies
            ("light_rain", "unpaved", 2.0, 0.95),
            ("moderate_rain", "dirt", 2.5, 0.9),
            ("heavy_rain", "grass", 3.0, 0.85),
            ("storm", "unpaved", 3.5, 0.9),
            
            # Factores que mejoran la optimización
            ("lane_count", "motorway", 0.8, 0.9),
            ("traffic_density", "residential", 1.5, 0.8),
            
            # Impactos en la planificación de rutas
            ("flooding_risk", "track", 2.0, 0.95),
            ("road_damage", "unpaved", 1.8, 0.9)
        ]
        
        for source_id, target_id, weight, confidence in optimization_relations:
            self.relations.append({
                "source": source_id,
                "target": target_id,
                "relation_type": "optimization_factor",
                "weight": weight,
                "properties": {
                    "confidence": confidence,
                    "affects_route_planning": True,
                    "optimization_impact": self._get_optimization_impact(weight)
                }
            })
    
    def _get_severity_level(self, impact_factor):
        """Determina el nivel de severidad basado en el factor de impacto"""
        if impact_factor <= 1.2:
            return "low"
        elif impact_factor <= 1.8:
            return "medium"
        elif impact_factor <= 2.5:
            return "high"
        else:
            return "very_high"
    
    def _get_optimization_impact(self, weight):
        """Determina el impacto en la optimización"""
        if weight < 1.0:
            return "positive"
        elif weight <= 1.5:
            return "neutral"
        else:
            return "negative"
    
    def save_to_json(self, filename):
        """Guarda el grafo de conocimiento extendido en un archivo JSON"""
        knowledge_graph = self.create_extended_knowledge_graph()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(knowledge_graph, f, indent=2, ensure_ascii=False)
        
        print(f"Grafo de conocimiento extendido guardado en: {filename}")
        print(f"Entidades: {len(knowledge_graph['entities'])}")
        print(f"Relaciones: {len(knowledge_graph['relations'])}")
        
        return knowledge_graph

if __name__ == "__main__":
    # Crear y guardar el grafo de conocimiento extendido
    kg = ExtendedKnowledgeGraph()
    knowledge_graph = kg.save_to_json("extended_knowledge_graph.json")
    
    # Mostrar estadísticas
    print("\n=== ESTADÍSTICAS DEL GRAFO ===")
    entity_types = {}
    for entity in knowledge_graph['entities']:
        entity_type = entity['type']
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
    
    for entity_type, count in entity_types.items():
        print(f"{entity_type}: {count}")
