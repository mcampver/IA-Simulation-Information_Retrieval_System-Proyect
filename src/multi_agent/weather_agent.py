"""
Agente Climático Especializado - Fase 2
"""

import asyncio
import random
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

from .base_agent import BaseAgent, AgentState, MessageType
from .communication import communication_manager

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

class WeatherAgent(BaseAgent):
    """
    Agente especializado en monitoreo y predicción climática
    """
    
    def __init__(self, agent_id: str, coverage_area: Tuple[float, float, float]):
        super().__init__(agent_id, "weather", coverage_area[:2])
        
        self.coverage_area = coverage_area
        self.current_conditions = {
            "temperature": 25.0,
            "humidity": 60.0,
            "precipitation": 0.0,
            "wind_speed": 5.0,
            "visibility": 10.0,
            "condition": WeatherCondition.CLEAR
        }
        
        self.weather_forecast = []
        self.weather_history = []
        
        # Variables estocásticas para simulación realista
        self.weather_variability = {
            "temperature_variance": 2.0,
            "humidity_variance": 10.0,
            "precipitation_probability": 0.15,
            "wind_variance": 3.0
        }

    async def perceive(self, environment_state: Dict[str, Any]) -> Dict[str, Any]:
        """Percibe y actualiza las condiciones climáticas"""
        perception = {}
        
        try:
            # Simular lectura de sensores con variables aleatorias
            new_conditions = self._simulate_weather_sensors()
            
            # Actualizar condiciones actuales
            self.current_conditions.update(new_conditions)
            
            # Evaluar impacto en el tráfico
            traffic_impact = self._assess_traffic_impact(self.current_conditions)
            
            perception = {
                "current_weather": self.current_conditions.copy(),
                "traffic_impact_factor": traffic_impact,
                "visibility_factor": self._calculate_visibility_factor(),
                "road_conditions": self._assess_road_conditions()
            }
            
            # Generar predicciones
            self._update_weather_forecast()
            perception["forecast"] = self.weather_forecast[:6]
            
        except Exception as e:
            self.logger.error(f"Error en percepción climática: {e}")
            perception = {"current_weather": self.current_conditions.copy()}
        
        return perception

    async def decide(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """Decide alertas y recomendaciones climáticas"""
        decisions = {}
        
        try:
            current_weather = perception.get("current_weather", {})
            traffic_impact = perception.get("traffic_impact_factor", 1.0)
            
            # Evaluar necesidad de alertas
            if traffic_impact > 1.5:
                decisions["issue_weather_advisory"] = True
                decisions["alert_level"] = "high" if traffic_impact > 2.0 else "medium"
            
            # Recomendaciones para vehículos
            vehicle_advisories = self._generate_vehicle_advisories(current_weather)
            decisions["vehicle_advisories"] = vehicle_advisories
            
        except Exception as e:
            self.logger.error(f"Error en decisión climática: {e}")
            decisions = {"maintain_monitoring": True}
        
        return decisions

    async def act(self, decision: Dict[str, Any]) -> bool:
        """Ejecuta alertas y notificaciones climáticas"""
        try:
            if decision.get("issue_weather_advisory", False):
                await self._send_weather_advisory(decision)
            
            if "vehicle_advisories" in decision:
                await self._broadcast_vehicle_advisories(decision["vehicle_advisories"])
            
            self._update_weather_history()
            return True
            
        except Exception as e:
            self.logger.error(f"Error ejecutando acciones climáticas: {e}")
            return False

    def _simulate_weather_sensors(self) -> Dict[str, Any]:
        """Simula lecturas de sensores con variables aleatorias"""
        current = self.current_conditions.copy()
        
        # Temperatura con variabilidad
        temp_change = np.random.normal(0, self.weather_variability["temperature_variance"])
        current["temperature"] += temp_change
        current["temperature"] = max(-10, min(45, current["temperature"]))
        
        # Humedad
        humidity_change = np.random.normal(0, self.weather_variability["humidity_variance"])
        current["humidity"] += humidity_change
        current["humidity"] = max(0, min(100, current["humidity"]))
        
        # Precipitación con modelo estocástico
        if np.random.random() < self.weather_variability["precipitation_probability"]:
            current["precipitation"] = np.random.exponential(2.0)
        else:
            current["precipitation"] *= 0.8
        
        current["precipitation"] = max(0, min(50, current["precipitation"]))
        
        # Viento
        wind_change = np.random.normal(0, self.weather_variability["wind_variance"])
        current["wind_speed"] += wind_change
        current["wind_speed"] = max(0, min(100, current["wind_speed"]))
        
        # Visibilidad
        visibility_factor = 1.0
        if current["precipitation"] > 5:
            visibility_factor *= (1 - current["precipitation"] / 50)
        
        current["visibility"] = max(0.1, min(10, 10 * visibility_factor))
        
        # Determinar condición
        current["condition"] = self._classify_weather_condition(current)
        
        return current

    def _classify_weather_condition(self, conditions: Dict) -> WeatherCondition:
        """Clasifica la condición climática"""
        precip = conditions["precipitation"]
        visibility = conditions["visibility"]
        
        if precip > 10:
            return WeatherCondition.HEAVY_RAIN
        elif precip > 2:
            return WeatherCondition.LIGHT_RAIN
        elif visibility < 3:
            return WeatherCondition.FOG
        else:
            return WeatherCondition.CLEAR

    def _assess_traffic_impact(self, conditions: Dict) -> float:
        """Evalúa el impacto del clima en el tráfico"""
        base_impact = 1.0
        
        precip = conditions.get("precipitation", 0)
        if precip > 0:
            base_impact += 0.1 + (precip / 20.0) * 0.8
        
        visibility = conditions.get("visibility", 10)
        if visibility < 5:
            base_impact += (5 - visibility) / 5 * 0.5
        
        return min(3.0, base_impact)

    def _generate_vehicle_advisories(self, weather: Dict) -> Dict[str, Any]:
        """Genera avisos para vehículos"""
        advisories = {}
        condition = weather.get("condition", WeatherCondition.CLEAR)
        
        if condition == WeatherCondition.HEAVY_RAIN:
            advisories["speed_reduction"] = 0.6
            advisories["increase_following_distance"] = 2.5
        elif condition == WeatherCondition.FOG:
            advisories["speed_reduction"] = 0.4
            advisories["increase_following_distance"] = 3.0
        elif condition == WeatherCondition.LIGHT_RAIN:
            advisories["speed_reduction"] = 0.8
            advisories["increase_following_distance"] = 1.5
        
        return advisories

    async def _send_weather_advisory(self, decision: Dict):
        """Envía aviso meteorológico"""
        advisory = {
            "weather_update": {
                "severity": decision.get("alert_level", "medium"),
                "conditions": self.current_conditions.copy(),
                "recommendations": decision.get("vehicle_advisories", {})
            }
        }
        
        await communication_manager.send_to_topic(
            "weather",
            self.agent_id,
            MessageType.NOTIFICATION,
            advisory
        )

    async def _broadcast_vehicle_advisories(self, advisories: Dict):
        """Transmite avisos a vehículos"""
        message = {
            "weather_advisory": {
                "source": self.agent_id,
                "conditions": self.current_conditions.copy(),
                "recommendations": advisories
            }
        }
        
        await communication_manager.send_to_topic(
            "weather",
            self.agent_id,
            MessageType.NOTIFICATION,
            message
        )

    def _update_weather_forecast(self):
        """Actualiza predicción meteorológica"""
        self.weather_forecast = []
        current = self.current_conditions.copy()
        
        for hour in range(1, 7):
            forecast_hour = current.copy()
            
            # Tendencia de temperatura
            temp_trend = np.sin((datetime.now().hour + hour) * np.pi / 12) * 2
            forecast_hour["temperature"] += temp_trend + np.random.normal(0, 1)
            
            # Persistencia de precipitación
            forecast_hour["precipitation"] *= (0.9 ** hour)
            
            self.weather_forecast.append({
                "hour": hour,
                "conditions": forecast_hour,
                "confidence": max(0.3, 1.0 - hour * 0.1)
            })

    def _calculate_visibility_factor(self) -> float:
        """Calcula factor de visibilidad"""
        visibility = self.current_conditions.get("visibility", 10)
        return min(1.0, visibility / 10.0)

    def _assess_road_conditions(self) -> str:
        """Evalúa condiciones de carretera"""
        precip = self.current_conditions.get("precipitation", 0)
        if precip > 5:
            return "wet"
        elif precip > 0:
            return "damp"
        else:
            return "dry"

    def _update_weather_history(self):
        """Actualiza historial climático"""
        self.weather_history.append({
            "timestamp": datetime.now(),
            "conditions": self.current_conditions.copy()
        })
        
        # Mantener últimas 24 horas
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.weather_history = [
            entry for entry in self.weather_history 
            if entry["timestamp"] > cutoff_time
        ]

    def get_weather_metrics(self) -> Dict[str, Any]:
        """Retorna métricas climáticas"""
        base_metrics = self.get_metrics()
        return {
            **base_metrics,
            "current_conditions": self.current_conditions,
            "traffic_impact_factor": self._assess_traffic_impact(self.current_conditions),
            "coverage_area": self.coverage_area
        }

    # Métodos de utilidad para interactuar con otros agentes
    
    async def get_current_weather(self) -> Dict[str, Any]:
        """Obtiene las condiciones meteorológicas actuales"""
        return {
            "temperature": self.current_conditions["temperature"],
            "humidity": self.current_conditions["humidity"],
            "precipitation": self.current_conditions["precipitation"],
            "wind_speed": self.current_conditions["wind_speed"],
            "visibility": self.current_conditions["visibility"],
            "condition": self.current_conditions["condition"].value,
            "traffic_impact": self._assess_traffic_impact(self.current_conditions),
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_forecast(self, hours_ahead: int = 24) -> Dict[str, Any]:
        """Obtiene pronóstico del tiempo para las próximas horas"""
        if not self.weather_forecast:
            # Generar pronóstico simple si no existe
            for i in range(1, min(hours_ahead + 1, 25)):
                event_type = random.choice(["clear", "cloudy", "light_rain"])
                self.weather_forecast.append({
                    "hour": i,
                    "type": event_type,
                    "probability": random.uniform(0.1, 0.9)
                })
        
        forecast_events = [
            event for event in self.weather_forecast
            if event["hour"] <= hours_ahead
        ]
        
        return {
            "hours_ahead": hours_ahead,
            "events": forecast_events,
            "base_conditions": self.current_conditions,
            "generated_at": datetime.now().isoformat()
        }
    
    async def trigger_event(self, event_type: str, intensity: float = 0.5, duration_minutes: int = 30):
        """Desencadena un evento meteorológico específico"""
        try:
            condition = WeatherCondition(event_type.lower().replace(" ", "_"))
        except ValueError:
            condition = WeatherCondition.CLOUDY  # Default fallback
        
        # Aplicar evento inmediatamente
        old_condition = self.current_conditions["condition"]
        self.current_conditions["condition"] = condition
        
        # Modificar parámetros según el tipo de evento
        if event_type.lower() in ["rain", "heavy_rain"]:
            self.current_conditions["precipitation"] = intensity * 10.0  # mm
            self.current_conditions["visibility"] = max(1.0, 10.0 - intensity * 8.0)
        elif event_type.lower() == "snow":
            self.current_conditions["precipitation"] = intensity * 5.0
            self.current_conditions["temperature"] = max(-5.0, self.current_conditions["temperature"] - intensity * 10.0)
            self.current_conditions["visibility"] = max(0.5, 10.0 - intensity * 9.0)
        elif event_type.lower() == "fog":
            self.current_conditions["visibility"] = max(0.1, 2.0 - intensity * 1.8)
            self.current_conditions["humidity"] = min(100.0, self.current_conditions["humidity"] + intensity * 30.0)
        
        # Notificar a otros agentes
        try:
            await communication_manager._broadcast_message({
                "type": MessageType.NOTIFICATION.value,
                "content": {
                    "weather_event": event_type,
                    "intensity": intensity,
                    "duration_minutes": duration_minutes,
                    "conditions": await self.get_current_weather()
                },
                "sender": self.agent_id
            }, topic="weather_update")
        except:
            # Si no hay método de broadcast, usar envío directo
            pass
        
        self.logger.info(f"Evento meteorológico activado: {event_type} (intensidad: {intensity})")
        
        # Programar restauración después de la duración
        async def restore_weather():
            await asyncio.sleep(duration_minutes * 60)  # Convertir a segundos
            self.current_conditions["condition"] = old_condition
            # Restaurar valores gradualmente
            await self._update_weather_conditions()
        
        asyncio.create_task(restore_weather())
