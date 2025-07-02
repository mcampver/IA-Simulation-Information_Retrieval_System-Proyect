"""
Agente Vehículo con Lógica Difusa
Implementa comportamiento inteligente para vehículos en la simulación de tránsito
"""

import asyncio
import random
import math
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum

from .base_agent import BaseAgent, MessageType, AgentState
from .communication import communication_manager

class VehicleBehavior(Enum):
    """Tipos de comportamiento de vehículo"""
    NORMAL = "normal"
    AGGRESSIVE = "aggressive"
    CAUTIOUS = "cautious"
    SLOW = "slow"
    FAST = "fast"

class VehicleState(Enum):
    """Estados específicos del vehículo"""
    IDLE = "idle"
    MOVING = "moving"
    WAITING = "waiting"
    ROUTE_PLANNING = "route_planning"
    EMERGENCY_STOP = "emergency_stop"

class FuzzyLogicController:
    """
    Controlador de lógica difusa para toma de decisiones del vehículo
    """
    
    def __init__(self):
        self.rules = self._initialize_fuzzy_rules()
    
    def _initialize_fuzzy_rules(self) -> Dict[str, Any]:
        """Inicializa las reglas difusas para el comportamiento del vehículo"""
        return {
            "speed_control": {
                # Reglas para control de velocidad
                "very_low_traffic": {"speed_factor": 1.0, "confidence": 0.9},
                "low_traffic": {"speed_factor": 0.9, "confidence": 0.8},
                "medium_traffic": {"speed_factor": 0.7, "confidence": 0.7},
                "high_traffic": {"speed_factor": 0.5, "confidence": 0.8},
                "very_high_traffic": {"speed_factor": 0.3, "confidence": 0.9}
            },
            "route_selection": {
                # Reglas para selección de rutas
                "clear_path": {"preference": 0.9, "weight_factor": 1.0},
                "light_congestion": {"preference": 0.7, "weight_factor": 1.2},
                "moderate_congestion": {"preference": 0.5, "weight_factor": 1.5},
                "heavy_congestion": {"preference": 0.2, "weight_factor": 2.0}
            },
            "weather_adaptation": {
                # Reglas para adaptación al clima
                "clear": {"speed_factor": 1.0, "caution_level": 0.1},
                "light_rain": {"speed_factor": 0.8, "caution_level": 0.3},
                "heavy_rain": {"speed_factor": 0.6, "caution_level": 0.6},
                "fog": {"speed_factor": 0.5, "caution_level": 0.8}
            }
        }
    
    def evaluate_traffic_density(self, vehicles_in_area: int, area_capacity: int) -> str:
        """Evalúa la densidad de tráfico usando lógica difusa"""
        if area_capacity == 0:
            return "very_low_traffic"
        
        density_ratio = vehicles_in_area / area_capacity
        
        if density_ratio <= 0.2:
            return "very_low_traffic"
        elif density_ratio <= 0.4:
            return "low_traffic"
        elif density_ratio <= 0.6:
            return "medium_traffic"
        elif density_ratio <= 0.8:
            return "high_traffic"
        else:
            return "very_high_traffic"
    
    def calculate_speed_factor(self, traffic_density: str, weather_condition: str, 
                              behavior_type: VehicleBehavior) -> float:
        """Calcula el factor de velocidad usando reglas difusas mejoradas"""
        # Factor base por densidad de tráfico (más diferenciado)
        traffic_factors = {
            "very_low_traffic": 1.0,
            "low_traffic": 0.8,
            "medium_traffic": 0.6,
            "high_traffic": 0.3,
            "very_high_traffic": 0.1
        }
        traffic_factor = traffic_factors.get(traffic_density, 0.7)
        
        # Factor por condiciones climáticas (más reactivo)
        weather_factors = {
            "clear": 1.0,
            "light_rain": 0.7,
            "heavy_rain": 0.4,
            "rain": 0.5,
            "fog": 0.3,
            "storm": 0.2
        }
        weather_factor = weather_factors.get(weather_condition, 0.8)
        
        # Ajuste por comportamiento del vehículo (más diferenciado)
        behavior_multiplier = {
            VehicleBehavior.AGGRESSIVE: 1.5,
            VehicleBehavior.FAST: 1.3,
            VehicleBehavior.NORMAL: 1.0,
            VehicleBehavior.CAUTIOUS: 0.6,
            VehicleBehavior.SLOW: 0.4
        }.get(behavior_type, 1.0)
        
        # Combinar factores con lógica difusa
        final_factor = (traffic_factor * weather_factor * behavior_multiplier)
        return max(0.05, min(2.0, final_factor))  # Rango más amplio para ver diferencias

class VehicleAgent(BaseAgent):
    """
    Agente inteligente que representa un vehículo en la simulación
    """
    
    def __init__(self, vehicle_id: str, initial_position: Tuple[float, float],
                 behavior_type: VehicleBehavior = VehicleBehavior.NORMAL):
        super().__init__(vehicle_id, "vehicle", initial_position)
        
        # Características específicas del vehículo
        self.behavior_type = behavior_type
        self.vehicle_state = VehicleState.IDLE
        self.fuzzy_controller = FuzzyLogicController()
        
        # Parámetros de movimiento
        self.base_speed = random.uniform(0.003, 0.008)  # Velocidad base
        self.current_speed = 0.0
        self.max_speed = self._calculate_max_speed()
        self.acceleration = 0.001
        self.deceleration = 0.002
        
        # Estado de navegación
        self.current_node = None
        self.next_node = None
        self.target_node = None
        self.route = []
        self.route_progress = 0.0
        
        # Percepción del entorno
        self.perceived_traffic = 0
        self.perceived_weather = "clear"
        self.nearby_vehicles = []
        
        # Memoria del agente
        self.route_history = []
        self.traffic_memory = {}  # Memoria de congestión por arista
        
        # Contadores para métricas
        self.distance_traveled = 0.0
        self.route_changes = 0
        self.stops_count = 0

    def _calculate_max_speed(self) -> float:
        """Calcula la velocidad máxima según el tipo de comportamiento"""
        base_max = 0.01
        multipliers = {
            VehicleBehavior.SLOW: 0.5,
            VehicleBehavior.CAUTIOUS: 0.7,
            VehicleBehavior.NORMAL: 1.0,
            VehicleBehavior.FAST: 1.3,
            VehicleBehavior.AGGRESSIVE: 1.5
        }
        return base_max * multipliers.get(self.behavior_type, 1.0)

    async def perceive(self, environment_state: Dict[str, Any]) -> Dict[str, Any]:
        """Percibe el estado del entorno (tráfico, clima, otros vehículos)"""
        perception = {}
        
        try:
            # Percibir tráfico en el área
            street_graph = environment_state.get("street_graph")
            street_congestion = environment_state.get("street_congestion", {})
            
            if self.current_node and street_graph:
                # Analizar congestión en nodos adyacentes
                neighbors = list(street_graph.neighbors(self.current_node))
                total_congestion = 0
                checked_edges = 0
                
                for neighbor in neighbors:
                    edge_key = (self.current_node, neighbor)
                    congestion = street_congestion.get(edge_key, 0)
                    total_congestion += congestion
                    checked_edges += 1
                
                # Calcular densidad de tráfico percibida
                if checked_edges > 0:
                    avg_congestion = total_congestion / checked_edges
                    self.perceived_traffic = min(10, max(0, avg_congestion))
                
                perception["traffic_density"] = self.fuzzy_controller.evaluate_traffic_density(
                    int(self.perceived_traffic), 10
                )
            
            # Percibir condiciones climáticas
            weather_info = environment_state.get("weather_info", {})
            if weather_info:
                impact_factor = weather_info.get("impact_factor", 1.0)
                if impact_factor <= 1.1:
                    self.perceived_weather = "clear"
                elif impact_factor <= 1.3:
                    self.perceived_weather = "light_rain"
                elif impact_factor <= 1.6:
                    self.perceived_weather = "heavy_rain"
                else:
                    self.perceived_weather = "fog"
            
            perception["weather_condition"] = self.perceived_weather
            
            # Percibir otros vehículos cercanos
            all_vehicles = environment_state.get("vehicles", {})
            self.nearby_vehicles = []
            
            for other_id, other_vehicle in all_vehicles.items():
                if other_id != self.agent_id:
                    other_pos = (other_vehicle.get("lat", 0), other_vehicle.get("lon", 0))
                    distance = self.get_distance_to(other_pos)
                    
                    if distance < 0.01:  # Radio de percepción
                        self.nearby_vehicles.append({
                            "id": other_id,
                            "position": other_pos,
                            "distance": distance
                        })
            
            perception["nearby_vehicles_count"] = len(self.nearby_vehicles)
            perception["local_density"] = len(self.nearby_vehicles)
            
        except Exception as e:
            self.logger.error(f"Error en percepción: {e}")
            perception = {
                "traffic_density": "medium_traffic",
                "weather_condition": "clear",
                "nearby_vehicles_count": 0,
                "local_density": 0
            }
        
        return perception

    async def decide(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """Toma decisiones usando lógica difusa"""
        decisions = {}
        
        try:
            self.metrics["decisions_made"] += 1
            
            # Decisión de velocidad
            traffic_density = perception.get("traffic_density", "medium_traffic")
            weather_condition = perception.get("weather_condition", "clear")
            
            speed_factor = self.fuzzy_controller.calculate_speed_factor(
                traffic_density, weather_condition, self.behavior_type
            )
            
            target_speed = self.max_speed * speed_factor
            decisions["target_speed"] = target_speed
            
            # Decisión de cambio de carril/ruta
            local_density = perception.get("local_density", 0)
            should_change_route = False
            
            if local_density > 3 and traffic_density in ["high_traffic", "very_high_traffic"]:
                # Lógica difusa para cambio de ruta
                change_probability = min(0.8, local_density / 10.0)
                if random.random() < change_probability:
                    should_change_route = True
            
            decisions["change_route"] = should_change_route
            
            # Decisión de comportamiento adaptativo
            if weather_condition in ["heavy_rain", "fog"]:
                decisions["increase_caution"] = True
                decisions["following_distance_multiplier"] = 2.0
            else:
                decisions["increase_caution"] = False
                decisions["following_distance_multiplier"] = 1.0
            
            # Actualizar estado del vehículo
            if target_speed < 0.001:
                self.vehicle_state = VehicleState.WAITING
            elif should_change_route:
                self.vehicle_state = VehicleState.ROUTE_PLANNING
            else:
                self.vehicle_state = VehicleState.MOVING
            
        except Exception as e:
            self.logger.error(f"Error en decisión: {e}")
            decisions = {
                "target_speed": self.base_speed,
                "change_route": False,
                "increase_caution": False,
                "following_distance_multiplier": 1.0
            }
        
        return decisions

    async def act(self, decision: Dict[str, Any]) -> bool:
        """Ejecuta las acciones determinadas por las decisiones"""
        try:
            # Actualizar velocidad
            target_speed = decision.get("target_speed", self.base_speed)
            
            if target_speed > self.current_speed:
                self.current_speed = min(target_speed, 
                                       self.current_speed + self.acceleration)
            else:
                self.current_speed = max(target_speed, 
                                       self.current_speed - self.deceleration)
            
            # Procesar cambio de ruta si es necesario
            if decision.get("change_route", False) and self.route:
                await self._request_route_optimization()
                self.route_changes += 1
            
            # Mover el vehículo
            if self.current_speed > 0 and self.route:
                await self._move_along_route()
            
            # Comunicar estado a otros agentes si hay cambios significativos
            if decision.get("increase_caution", False):
                await self._broadcast_caution_message()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error ejecutando acción: {e}")
            return False

    async def _move_along_route(self):
        """Mueve el vehículo a lo largo de su ruta actual"""
        if not self.route or self.route_progress >= len(self.route) - 1:
            return
        
        # Calcular nueva posición
        current_idx = int(self.route_progress)
        next_idx = min(current_idx + 1, len(self.route) - 1)
        
        if current_idx < len(self.route) and next_idx < len(self.route):
            current_node = self.route[current_idx]
            next_node = self.route[next_idx]
            
            # Interpolación lineal entre nodos
            t = self.route_progress - current_idx
            
            # Actualizar posición (esto requeriría acceso al street_graph)
            # Por ahora, simulamos movimiento
            self.route_progress += self.current_speed * 10  # Factor de escala
            
            if self.route_progress >= len(self.route) - 1:
                # Llegó al destino
                await self._handle_destination_reached()

    async def _request_route_optimization(self):
        """Solicita una nueva ruta optimizada"""
        await communication_manager.send_to_topic(
            "optimization_requests",
            self.agent_id,
            MessageType.REQUEST,
            {
                "request_type": "route_optimization",
                "current_position": self.position,
                "current_node": self.current_node,
                "target_node": self.target_node,
                "vehicle_behavior": self.behavior_type.value,
                "urgency": "medium"
            }
        )

    async def _broadcast_caution_message(self):
        """Envía mensaje de precaución a vehículos cercanos"""
        await communication_manager.send_to_topic(
            "traffic",
            self.agent_id,
            MessageType.NOTIFICATION,
            {
                "message_type": "caution_advisory",
                "position": self.position,
                "reason": "adverse_conditions",
                "recommended_speed_reduction": 0.3
            }
        )

    async def _handle_destination_reached(self):
        """Maneja la llegada al destino"""
        self.vehicle_state = VehicleState.IDLE
        self.current_speed = 0.0
        self.route = []
        self.route_progress = 0.0
        
        # Notificar llegada
        await communication_manager.send_to_topic(
            "vehicle_updates",
            self.agent_id,
            MessageType.NOTIFICATION,
            {
                "event": "destination_reached",
                "position": self.position,
                "travel_time": (datetime.now() - self.metrics["uptime_start"]).total_seconds()
            }
        )

    def assign_route(self, route: List[Any], target_node: Any):
        """Asigna una nueva ruta al vehículo"""
        self.route = route
        self.target_node = target_node
        self.route_progress = 0.0
        self.vehicle_state = VehicleState.MOVING
        
        # Guardar en historial
        self.route_history.append({
            "timestamp": datetime.now(),
            "route": route.copy(),
            "target": target_node
        })

    def get_vehicle_metrics(self) -> Dict[str, Any]:
        """Retorna métricas específicas del vehículo"""
        base_metrics = self.get_metrics()
        return {
            **base_metrics,
            "behavior_type": self.behavior_type.value,
            "vehicle_state": self.vehicle_state.value,
            "current_speed": self.current_speed,
            "max_speed": self.max_speed,
            "distance_traveled": self.distance_traveled,
            "route_changes": self.route_changes,
            "stops_count": self.stops_count,
            "perceived_traffic": self.perceived_traffic,
            "perceived_weather": self.perceived_weather,
            "nearby_vehicles": len(self.nearby_vehicles)
        }

    async def handle_emergency(self, message):
        """Maneja mensajes de emergencia específicos para vehículos"""
        emergency_data = message.content
        emergency_type = emergency_data.get("emergency_type", "unknown")
        
        self.logger.warning(f"Emergencia recibida: {emergency_type}")
        
        if emergency_type == "traffic_jam":
            self.current_speed = min(self.current_speed, self.base_speed * 0.3)
        elif emergency_type == "accident":
            self.current_speed = 0.0
            self.vehicle_state = VehicleState.EMERGENCY_STOP
            
        self.metrics["emergency_responses"] = self.metrics.get("emergency_responses", 0) + 1
