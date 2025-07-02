"""
Agentes Especializados para el Sistema Multi-Agente - Fase 2
Implementa agentes específicos para control de tráfico, clima y optimización
"""

import asyncio
import random
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

from .base_agent import BaseAgent, AgentState, MessageType
from .communication import communication_manager

class TrafficLightState(Enum):
    """Estados de un semáforo"""
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    FLASHING = "flashing"

class WeatherCondition(Enum):
    """Condiciones climáticas avanzadas"""
    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    LIGHT_RAIN = "light_rain"
    HEAVY_RAIN = "heavy_rain"
    THUNDERSTORM = "thunderstorm"
    FOG = "fog"
    SNOW = "snow"
    HAIL = "hail"

class OptimizationStrategy(Enum):
    """Estrategias de optimización"""
    MINIMIZE_TIME = "minimize_time"
    MINIMIZE_FUEL = "minimize_fuel"
    BALANCE_LOAD = "balance_load"
    EMERGENCY_PRIORITY = "emergency_priority"

class TrafficControlAgent(BaseAgent):
    """
    Agente especializado en control de semáforos y regulación de tráfico
    """
    
    def __init__(self, agent_id: str, intersection_position: Tuple[float, float],
                 controlled_intersections: List[Any] = None):
        super().__init__(agent_id, "traffic_control", intersection_position)
        
        # Estado del semáforo
        self.traffic_light_state = TrafficLightState.RED
        self.controlled_intersections = controlled_intersections or []
        
        # Configuración de tiempos
        self.green_duration = 30.0  # segundos
        self.yellow_duration = 5.0
        self.red_duration = 25.0
        self.cycle_start_time = datetime.now()
        
        # Monitoreo de tráfico
        self.vehicle_count_by_direction = {"north": 0, "south": 0, "east": 0, "west": 0}
        self.queue_lengths = {"north": 0, "south": 0, "east": 0, "west": 0}
        self.average_wait_times = {"north": 0, "south": 0, "east": 0, "west": 0}
        
        # Control adaptativo
        self.adaptive_mode = True
        self.emergency_override = False
        self.congestion_threshold = 5  # vehículos por dirección
        
        # Historial de decisiones
        self.timing_history = []
        self.efficiency_metrics = {
            "total_vehicles_processed": 0,
            "average_wait_time": 0.0,
            "cycle_efficiency": 0.0
        }

    async def perceive(self, environment_state: Dict[str, Any]) -> Dict[str, Any]:
        """Percibe el estado del tráfico en la intersección"""
        perception = {}
        
        try:
            # Obtener información de vehículos cercanos
            vehicles = environment_state.get("vehicles", {})
            self._count_vehicles_by_direction(vehicles)
            
            # Calcular densidad de tráfico
            total_vehicles = sum(self.vehicle_count_by_direction.values())
            perception["traffic_density"] = total_vehicles
            perception["vehicle_distribution"] = self.vehicle_count_by_direction.copy()
            
            # Detectar congestión
            max_queue = max(self.queue_lengths.values())
            perception["congestion_level"] = min(10, max_queue / 2)
            
            # Estado actual del semáforo
            perception["current_light_state"] = self.traffic_light_state.value
            perception["time_in_current_state"] = (
                datetime.now() - self.cycle_start_time
            ).total_seconds()
            
            # Emergencias detectadas
            perception["emergency_vehicles_detected"] = self._detect_emergency_vehicles(vehicles)
            
        except Exception as e:
            self.logger.error(f"Error en percepción de tráfico: {e}")
            perception = {"traffic_density": 0, "congestion_level": 0}
        
        return perception

    async def decide(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """Decide los tiempos de semáforo usando lógica difusa avanzada"""
        decisions = {}
        
        try:
            current_time_in_state = perception.get("time_in_current_state", 0)
            traffic_density = perception.get("traffic_density", 0)
            congestion_level = perception.get("congestion_level", 0)
            emergency_detected = perception.get("emergency_vehicles_detected", False)
            
            # Prioridad 1: Emergencias
            if emergency_detected and not self.emergency_override:
                decisions["action"] = "emergency_green"
                decisions["duration"] = 60.0  # Verde extendido para emergencias
                self.emergency_override = True
                
            # Prioridad 2: Control adaptativo normal
            elif self.adaptive_mode:
                new_state, duration = self._fuzzy_traffic_control(
                    self.traffic_light_state,
                    current_time_in_state,
                    traffic_density,
                    congestion_level,
                    perception.get("vehicle_distribution", {})
                )
                
                decisions["action"] = "change_light"
                decisions["new_state"] = new_state
                decisions["duration"] = duration
                
            # Control por defecto
            else:
                decisions = self._default_timing_control(current_time_in_state)
            
            # Notificar cambios a vehículos
            if "action" in decisions:
                decisions["notify_vehicles"] = True
            
        except Exception as e:
            self.logger.error(f"Error en decisión de tráfico: {e}")
            decisions = {"action": "maintain", "duration": 5.0}
        
        return decisions

    async def act(self, decision: Dict[str, Any]) -> bool:
        """Ejecuta el control del semáforo"""
        try:
            action = decision.get("action", "maintain")
            
            if action == "change_light":
                new_state = TrafficLightState(decision.get("new_state", "red"))
                await self._change_traffic_light(new_state)
                
            elif action == "emergency_green":
                await self._change_traffic_light(TrafficLightState.GREEN)
                await self._notify_emergency_override()
                
            elif action == "maintain":
                # Mantener estado actual
                pass
            
            # Notificar a vehículos si es necesario
            if decision.get("notify_vehicles", False):
                await self._notify_vehicles_of_light_change()
            
            # Actualizar métricas
            self._update_efficiency_metrics()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error ejecutando control de tráfico: {e}")
            return False

    def _fuzzy_traffic_control(self, current_state: TrafficLightState, 
                              time_in_state: float, traffic_density: int, 
                              congestion_level: float, vehicle_distribution: Dict) -> Tuple[str, float]:
        """Lógica difusa avanzada para control de semáforos"""
        
        # Variables difusas de entrada
        # Tiempo en estado actual (normalizado)
        time_factor = min(1.0, time_in_state / 30.0)
        
        # Densidad de tráfico (normalizada)
        density_factor = min(1.0, traffic_density / 20.0)
        
        # Factor de congestión
        congestion_factor = min(1.0, congestion_level / 10.0)
        
        # Distribución de vehículos (asimetría)
        max_direction = max(vehicle_distribution.values()) if vehicle_distribution else 0
        min_direction = min(vehicle_distribution.values()) if vehicle_distribution else 0
        asymmetry_factor = (max_direction - min_direction) / max(1, max_direction + min_direction)
        
        # Reglas difusas
        if current_state == TrafficLightState.GREEN:
            # Decidir si cambiar a amarillo
            change_probability = (
                time_factor * 0.4 +
                (1 - density_factor) * 0.3 +
                congestion_factor * 0.2 +
                asymmetry_factor * 0.1
            )
            
            if change_probability > 0.6:
                return "yellow", self.yellow_duration
            else:
                # Extender verde si hay mucho tráfico
                extension = 10 * density_factor * (1 - time_factor)
                return "green", max(5, min(20, extension))
                
        elif current_state == TrafficLightState.YELLOW:
            if time_in_state >= self.yellow_duration:
                return "red", self.red_duration
                
        elif current_state == TrafficLightState.RED:
            # Decidir si cambiar a verde
            if time_in_state >= self.red_duration * 0.8:  # Mínimo 80% del tiempo rojo
                change_urgency = (
                    density_factor * 0.5 +
                    congestion_factor * 0.3 +
                    time_factor * 0.2
                )
                
                if change_urgency > 0.5:
                    # Duración de verde adaptativa
                    green_duration = self.green_duration * (1 + density_factor * 0.5)
                    return "green", min(60, green_duration)
        
        # Mantener estado actual
        return current_state.value, 5.0

    async def _change_traffic_light(self, new_state: TrafficLightState):
        """Cambia el estado del semáforo"""
        old_state = self.traffic_light_state
        self.traffic_light_state = new_state
        self.cycle_start_time = datetime.now()
        
        # Registrar cambio
        self.timing_history.append({
            "timestamp": datetime.now(),
            "from_state": old_state.value,
            "to_state": new_state.value,
            "traffic_density": sum(self.vehicle_count_by_direction.values())
        })
        
        self.logger.info(f"Semáforo cambiado: {old_state.value} -> {new_state.value}")

    async def _notify_vehicles_of_light_change(self):
        """Notifica a los vehículos sobre cambios en el semáforo"""
        message_content = {
            "traffic_light_update": {
                "intersection_id": self.agent_id,
                "current_state": self.traffic_light_state.value,
                "position": self.position,
                "estimated_change_time": 30.0  # Estimación
            }
        }
        
        await communication_manager.send_to_topic(
            "traffic",
            self.agent_id,
            MessageType.NOTIFICATION,
            message_content
        )

    def _count_vehicles_by_direction(self, vehicles: Dict):
        """Cuenta vehículos por dirección"""
        # Reset counters
        for direction in self.vehicle_count_by_direction:
            self.vehicle_count_by_direction[direction] = 0
        
        # Contar vehículos en un radio de 100 metros
        for vehicle_id, vehicle_data in vehicles.items():
            vehicle_pos = (vehicle_data.get("lat", 0), vehicle_data.get("lon", 0))
            distance = self.get_distance_to(vehicle_pos)
            
            if distance < 0.001:  # Aproximadamente 100 metros
                # Determinar dirección basada en posición relativa
                dx = vehicle_pos[0] - self.position[0]
                dy = vehicle_pos[1] - self.position[1]
                
                if abs(dx) > abs(dy):
                    direction = "east" if dx > 0 else "west"
                else:
                    direction = "north" if dy > 0 else "south"
                
                self.vehicle_count_by_direction[direction] += 1

    def _detect_emergency_vehicles(self, vehicles: Dict) -> bool:
        """Detecta vehículos de emergencia"""
        for vehicle_id, vehicle_data in vehicles.items():
            if vehicle_data.get("emergency", False):
                return True
        return False

    def _default_timing_control(self, time_in_state: float) -> Dict[str, Any]:
        """Control de tiempos por defecto"""
        if self.traffic_light_state == TrafficLightState.GREEN and time_in_state >= self.green_duration:
            return {"action": "change_light", "new_state": "yellow", "duration": self.yellow_duration}
        elif self.traffic_light_state == TrafficLightState.YELLOW and time_in_state >= self.yellow_duration:
            return {"action": "change_light", "new_state": "red", "duration": self.red_duration}
        elif self.traffic_light_state == TrafficLightState.RED and time_in_state >= self.red_duration:
            return {"action": "change_light", "new_state": "green", "duration": self.green_duration}
        
        return {"action": "maintain", "duration": 1.0}

    def _update_efficiency_metrics(self):
        """Actualiza métricas de eficiencia"""
        total_vehicles = sum(self.vehicle_count_by_direction.values())
        self.efficiency_metrics["total_vehicles_processed"] += total_vehicles
        
        # Calcular eficiencia del ciclo (simplificado)
        if total_vehicles > 0:
            self.efficiency_metrics["cycle_efficiency"] = min(1.0, total_vehicles / 20.0)

    async def _notify_emergency_override(self):
        """Notifica override de emergencia"""
        await communication_manager.emergency_broadcast(
            self.agent_id,
            "traffic_override",
            {
                "intersection_id": self.agent_id,
                "reason": "emergency_vehicle_detected",
                "duration": 60.0
            }
        )

    def get_traffic_metrics(self) -> Dict[str, Any]:
        """Retorna métricas específicas de tráfico"""
        base_metrics = self.get_metrics()
        return {
            **base_metrics,
            "current_light_state": self.traffic_light_state.value,
            "vehicle_count_by_direction": self.vehicle_count_by_direction,
            "efficiency_metrics": self.efficiency_metrics,
            "cycles_completed": len(self.timing_history),
            "adaptive_mode": self.adaptive_mode
        }

    async def modify_traffic_light(self, intersection_id: str, state: str = None, timing: int = None):
        """Modifica el estado de un semáforo específico"""
        try:
            if intersection_id not in self.traffic_lights:
                self.traffic_lights[intersection_id] = {
                    "state": TrafficLightState.GREEN,
                    "timer": 30
                }
            
            if state:
                try:
                    new_state = TrafficLightState(state.lower())
                    self.traffic_lights[intersection_id]["state"] = new_state
                except ValueError:
                    pass
            
            if timing:
                self.traffic_lights[intersection_id]["timer"] = max(5, min(120, timing))
            
            return True
        except:
            return False
    
    async def update_traffic_state(self, traffic_info: Dict[str, Any]):
        """Actualiza el estado de tráfico con información del entorno"""
        try:
            vehicle_count = traffic_info.get("vehicle_count", 0)
            self.logger.debug(f"Estado de tráfico actualizado: {vehicle_count} vehículos")
        except Exception as e:
            self.logger.error(f"Error actualizando estado: {e}")
