"""
Entorno de Simulación Multi-Agente
Coordina todos los agentes y maneja el estado global de la simulación
"""

import asyncio
import logging
import random
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import networkx as nx

from .base_agent import BaseAgent, MessageType
from .communication import communication_manager
from .vehicle_agent import VehicleAgent, VehicleBehavior
from .specialized_agents import TrafficControlAgent, WeatherCondition
from .weather_agent import WeatherAgent
from .route_optimizer_agent import RouteOptimizerAgent

class SimulationEnvironment:
    """
    Entorno de simulación que coordina todos los agentes y mantiene el estado global
    """
    
    def __init__(self, street_graph: nx.MultiDiGraph):
        self.street_graph = street_graph
        self.logger = logging.getLogger("SimulationEnvironment")
        
        # Estado global del entorno
        self.global_state = {
            "current_time": datetime.now(),
            "simulation_speed": 1.0,
            "weather_conditions": {},
            "traffic_density": {},
            "emergency_events": [],
            "system_alerts": []
        }
        
        # Agentes registrados
        self.agents: Dict[str, BaseAgent] = {}
        self.vehicle_agents: Dict[str, VehicleAgent] = {}
        self.specialized_agents: Dict[str, BaseAgent] = {}
        
        # Agentes especializados
        self.traffic_control_agent: Optional[TrafficControlAgent] = None
        self.weather_agent: Optional[WeatherAgent] = None
        self.route_optimizer_agent: Optional[RouteOptimizerAgent] = None
        
        # Estado específico del entorno
        self.traffic_lights = {}
        self.street_congestion = {}
        
        # Configuración de simulación
        self.simulation_config = {
            "max_vehicles": 50,
            "vehicle_spawn_rate": 0.1,  # Probabilidad por segundo
            "weather_change_interval": 300,  # 5 minutos
            "traffic_update_interval": 10,   # 10 segundos
            "simulation_step": 0.1  # 100ms
        }
        
        # Control de simulación
        self._running = False
        self._simulation_task = None
        self._weather_task = None
        self._traffic_task = None
        
        # Estadísticas de simulación
        self.simulation_stats = {
            "total_vehicles_spawned": 0,
            "active_vehicles": 0,
            "completed_trips": 0,
            "average_trip_time": 0.0,
            "total_simulation_time": 0.0
        }

    async def initialize(self):
        """Inicializa el entorno de simulación"""
        self.logger.info("Inicializando entorno de simulación...")
        
        # Inicializar comunicación entre agentes
        await communication_manager.start()
        
        # Registrar el entorno como agente especial para comunicación
        await communication_manager.register_agent_id("environment", "environment")
        
        # Inicializar agentes especializados
        await self._initialize_specialized_agents()
        
        # Inicializar congestión en calles
        self._initialize_street_congestion()
        
        # Inicializar condiciones climáticas
        self._initialize_weather_conditions()
        
        # Crear algunos vehículos iniciales
        await self._spawn_initial_vehicles()
        
        self.logger.info("Entorno de simulación inicializado")

    def _initialize_street_congestion(self):
        """Inicializa la congestión en todas las calles"""
        for edge in self.street_graph.edges():
            self.street_congestion[edge] = 0

    def _initialize_weather_conditions(self):
        """Inicializa las condiciones climáticas"""
        self.global_state["weather_conditions"] = {
            "temperature": 25.0,
            "humidity": 60.0,
            "precipitation": 0.0,
            "wind_speed": 5.0,
            "visibility": 10.0,
            "condition": "clear"
        }

    async def _spawn_initial_vehicles(self):
        """Crea vehículos iniciales en la simulación"""
        all_nodes = list(self.street_graph.nodes())
        if not all_nodes:
            return
        
        initial_count = min(5, len(all_nodes) // 4)  # Máximo 5 vehículos iniciales
        
        for i in range(initial_count):
            await self._spawn_vehicle()

    async def _spawn_vehicle(self) -> Optional[VehicleAgent]:
        """Crea un nuevo vehículo en una posición aleatoria"""
        all_nodes = list(self.street_graph.nodes())
        if not all_nodes:
            return None
        
        # Seleccionar nodo inicial aleatorio
        start_node = random.choice(all_nodes)
        node_data = self.street_graph.nodes[start_node]
        initial_position = (
            node_data.get('lat', 0.0),
            node_data.get('lon', 0.0)
        )
        
        # Crear vehículo con comportamiento aleatorio
        behavior_types = list(VehicleBehavior)
        behavior = random.choice(behavior_types)
        
        vehicle_id = f"vehicle_{len(self.vehicle_agents) + 1}"
        vehicle = VehicleAgent(vehicle_id, initial_position, behavior)
        vehicle.current_node = start_node
        
        # Asignar destino aleatorio
        target_nodes = [n for n in all_nodes if n != start_node]
        if target_nodes:
            target_node = random.choice(target_nodes)
            
            try:
                # Usar optimizador de rutas si está disponible
                if self.route_optimizer_agent:
                    route_request = {
                        "start_node": start_node,
                        "end_node": target_node,
                        "vehicle_type": behavior.value,
                        "priority": "normal",
                        "constraints": {}
                    }
                    route_response = await self.route_optimizer_agent.optimize_route(route_request)
                    if route_response and route_response.get("route"):
                        vehicle.assign_route(route_response["route"], target_node)
                        self.logger.debug(f"Ruta optimizada asignada a {vehicle_id}: algoritmo {route_response.get('algorithm', 'unknown')}")
                    else:
                        # Fallback a ruta simple
                        if nx.has_path(self.street_graph, start_node, target_node):
                            route = nx.shortest_path(self.street_graph, start_node, target_node)
                            vehicle.assign_route(route, target_node)
                else:
                    # Calcular ruta simple cuando no hay optimizador
                    if nx.has_path(self.street_graph, start_node, target_node):
                        route = nx.shortest_path(self.street_graph, start_node, target_node)
                        vehicle.assign_route(route, target_node)
            except Exception as e:
                self.logger.error(f"Error asignando ruta a {vehicle_id}: {e}")
                # Si hay error, el vehículo permanece en idle
        
        # Registrar vehículo
        self.vehicle_agents[vehicle_id] = vehicle
        self.agents[vehicle_id] = vehicle
        await communication_manager.register_agent(vehicle)
        
        # Iniciar agente
        await vehicle.start()
        
        self.simulation_stats["total_vehicles_spawned"] += 1
        self.logger.info(f"Vehículo creado: {vehicle_id} ({behavior.value})")
        
        return vehicle

    async def start_simulation(self):
        """Inicia la simulación multi-agente"""
        if self._running:
            self.logger.warning("La simulación ya está en ejecución")
            return
        
        self._running = True
        self.logger.info("Iniciando simulación multi-agente...")
        
        # Inicializar si no se ha hecho
        if not communication_manager._running:
            await self.initialize()
        
        # Crear tareas de simulación
        self._simulation_task = asyncio.create_task(self._simulation_loop())
        self._weather_task = asyncio.create_task(self._weather_loop())
        self._traffic_task = asyncio.create_task(self._traffic_monitoring_loop())
        
        self.logger.info("Simulación multi-agente iniciada")

    async def stop_simulation(self):
        """Detiene la simulación de forma segura"""
        self._running = False
        self.logger.info("Deteniendo simulación...")
        
        # Cancelar tareas
        tasks = [self._simulation_task, self._weather_task, self._traffic_task]
        for task in tasks:
            if task and not task.done():
                task.cancel()
        
        # Esperar a que terminen las tareas
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Detener todos los agentes
        for agent in self.agents.values():
            await agent.stop()
        
        # Desregistrar el entorno del communication manager
        await communication_manager.unregister_agent("environment")
        
        # Detener comunicación
        await communication_manager.stop()
        
        self.logger.info("Simulación detenida")

    async def _simulation_loop(self):
        """Ciclo principal de simulación"""
        last_update = datetime.now()
        
        while self._running:
            try:
                current_time = datetime.now()
                delta_time = (current_time - last_update).total_seconds()
                
                # Actualizar tiempo de simulación
                self.global_state["current_time"] = current_time
                self.simulation_stats["total_simulation_time"] += delta_time
                
                # Actualizar estado del entorno
                await self._update_environment_state()
                
                # Procesar spawning de vehículos
                await self._process_vehicle_spawning()
                
                # Limpiar vehículos que completaron su viaje
                await self._cleanup_completed_vehicles()
                
                # Actualizar métricas
                self._update_simulation_metrics()
                
                last_update = current_time
                await asyncio.sleep(self.simulation_config["simulation_step"])
                
            except Exception as e:
                self.logger.error(f"Error en ciclo de simulación: {e}")
                await asyncio.sleep(1)

    async def _update_environment_state(self):
        """Actualiza el estado del entorno que perciben los agentes"""
        try:
            # Actualizar agentes especializados primero
            await self._update_specialized_agents()
            
            # Preparar estado del entorno para los agentes
            environment_state = {
                "street_graph": self.street_graph,
                "street_congestion": self.street_congestion,
                "weather_info": self.global_state.get("weather_conditions", {}),
                "traffic_lights": getattr(self.traffic_control_agent, 'traffic_lights', {}) if self.traffic_control_agent else {},
                "vehicles": {
                    agent_id: {
                        "lat": agent.position[0],
                        "lon": agent.position[1],
                        "state": agent.vehicle_state.value if hasattr(agent, 'vehicle_state') else "unknown"
                    }
                    for agent_id, agent in self.vehicle_agents.items()
                },
                "current_time": self.global_state["current_time"]
            }
            
            # Enviar estado a todos los agentes vehículo
            for vehicle in self.vehicle_agents.values():
                if vehicle.state.name != "SHUTDOWN":
                    try:
                        # Cada vehículo percibe y actúa de forma asíncrona
                        perception = await vehicle.perceive(environment_state)
                        decision = await vehicle.decide(perception)
                        await vehicle.act(decision)
                    except Exception as e:
                        self.logger.error(f"Error actualizando vehículo {vehicle.agent_id}: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error actualizando estado del entorno: {e}")

    async def _process_vehicle_spawning(self):
        """Procesa la creación de nuevos vehículos"""
        if len(self.vehicle_agents) >= self.simulation_config["max_vehicles"]:
            return
        
        # Probabilidad de crear nuevo vehículo
        spawn_probability = self.simulation_config["vehicle_spawn_rate"] * \
                           self.simulation_config["simulation_step"]
        
        if random.random() < spawn_probability:
            await self._spawn_vehicle()

    async def _cleanup_completed_vehicles(self):
        """Limpia vehículos que completaron su viaje"""
        to_remove = []
        
        for vehicle_id, vehicle in self.vehicle_agents.items():
            if (vehicle.vehicle_state.name == "IDLE" and 
                not vehicle.route and 
                vehicle.target_node is None):
                
                # Marcar para eliminación después de un tiempo
                idle_time = datetime.now() - vehicle.last_update
                if idle_time > timedelta(seconds=30):  # 30 segundos de idle
                    to_remove.append(vehicle_id)
        
        # Remover vehículos completados
        for vehicle_id in to_remove:
            vehicle = self.vehicle_agents.pop(vehicle_id, None)
            self.agents.pop(vehicle_id, None)
            
            if vehicle:
                await vehicle.stop()
                await communication_manager.unregister_agent(vehicle_id)
                self.simulation_stats["completed_trips"] += 1
                self.logger.info(f"Vehículo removido: {vehicle_id}")

    async def _weather_loop(self):
        """Bucle de actualización de condiciones climáticas"""
        while self._running:
            try:
                await self._update_weather_conditions()
                await asyncio.sleep(self.simulation_config["weather_change_interval"])
            except Exception as e:
                self.logger.error(f"Error actualizando clima: {e}")
                await asyncio.sleep(60)

    async def _update_weather_conditions(self):
        """Actualiza las condiciones climáticas"""
        weather = self.global_state["weather_conditions"]
        
        # Cambios graduales en el clima
        weather["temperature"] += random.uniform(-2, 2)
        weather["temperature"] = max(0, min(40, weather["temperature"]))
        
        weather["humidity"] += random.uniform(-5, 5)
        weather["humidity"] = max(0, min(100, weather["humidity"]))
        
        # Cambios en precipitación
        if random.random() < 0.1:  # 10% probabilidad de cambio
            weather["precipitation"] = random.uniform(0, 10)
        else:
            weather["precipitation"] *= 0.9  # Decaimiento gradual
        
        # Determinar condición general
        if weather["precipitation"] > 5:
            weather["condition"] = "heavy_rain"
        elif weather["precipitation"] > 1:
            weather["condition"] = "light_rain"
        elif weather["humidity"] > 85:
            weather["condition"] = "fog"
        else:
            weather["condition"] = "clear"
        
        # Notificar cambios a los agentes
        await communication_manager.send_to_topic(
            "weather",
            "environment",
            MessageType.NOTIFICATION,
            {"weather_update": weather}
        )

    async def _traffic_monitoring_loop(self):
        """Bucle de monitoreo de tráfico"""
        while self._running:
            try:
                await self._update_traffic_congestion()
                await asyncio.sleep(self.simulation_config["traffic_update_interval"])
            except Exception as e:
                self.logger.error(f"Error monitoreando tráfico: {e}")
                await asyncio.sleep(10)

    async def _update_traffic_congestion(self):
        """Actualiza la congestión de tráfico en las calles"""
        # Resetear congestión
        for edge in self.street_congestion:
            self.street_congestion[edge] = 0
        
        # Calcular congestión basada en posiciones de vehículos
        for vehicle in self.vehicle_agents.values():
            if hasattr(vehicle, 'current_node') and vehicle.current_node:
                # Incrementar congestión en aristas adyacentes
                neighbors = list(self.street_graph.neighbors(vehicle.current_node))
                for neighbor in neighbors:
                    edge_key = (vehicle.current_node, neighbor)
                    if edge_key in self.street_congestion:
                        self.street_congestion[edge_key] += 1

    def _update_simulation_metrics(self):
        """Actualiza las métricas de simulación"""
        self.simulation_stats["active_vehicles"] = len(self.vehicle_agents)
        
        # Calcular tiempo promedio de viaje (simplificado)
        if self.simulation_stats["completed_trips"] > 0:
            total_time = sum(
                (datetime.now() - vehicle.metrics["uptime_start"]).total_seconds()
                for vehicle in self.vehicle_agents.values()
            )
            if total_time > 0:
                self.simulation_stats["average_trip_time"] = total_time / len(self.vehicle_agents)

    def get_simulation_status(self) -> Dict[str, Any]:
        """Retorna el estado actual de la simulación"""
        return {
            "running": self._running,
            "current_time": self.global_state["current_time"].isoformat(),
            "stats": self.simulation_stats,
            "active_agents": len(self.agents),
            "vehicle_count": len(self.vehicle_agents),
            "weather": self.global_state["weather_conditions"],
            "communication_stats": communication_manager.get_communication_stats()
        }

    def get_vehicle_positions(self) -> List[Dict[str, Any]]:
        """Retorna las posiciones actuales de todos los vehículos"""
        return [
            {
                "id": vehicle_id,
                "lat": vehicle.position[0],
                "lon": vehicle.position[1],
                "behavior": vehicle.behavior_type.value,
                "state": vehicle.vehicle_state.value,
                "speed": vehicle.current_speed
            }
            for vehicle_id, vehicle in self.vehicle_agents.items()
        ]

    async def add_emergency_event(self, event_type: str, position: Tuple[float, float], 
                                 details: Dict[str, Any]):
        """Añade un evento de emergencia a la simulación"""
        emergency = {
            "id": f"emergency_{len(self.global_state['emergency_events']) + 1}",
            "type": event_type,
            "position": position,
            "details": details,
            "timestamp": datetime.now(),
            "active": True
        }
        
        self.global_state["emergency_events"].append(emergency)
        
        # Notificar a todos los agentes
        await communication_manager.emergency_broadcast(
            "environment",
            event_type,
            emergency
        )
        
        self.logger.warning(f"Evento de emergencia creado: {event_type}")

    async def spawn_vehicle(self) -> Optional[VehicleAgent]:
        """Método público para crear un vehículo desde fuera del entorno"""
        return await self._spawn_vehicle()
    
    def get_vehicle_count(self) -> int:
        """Retorna el número de vehículos activos"""
        return len([agent for agent in self.agents.values() if hasattr(agent, 'vehicle_type')])
    
    def get_communication_manager(self):
        """Retorna el administrador de comunicación"""
        return communication_manager

    async def _initialize_specialized_agents(self):
        """Inicializa todos los agentes especializados"""
        try:
            # Inicializar Agente de Control de Tráfico
            # Usar una posición central como ubicación del controlador principal
            center_position = (40.7128, -74.0060)  # Posición central predeterminada
            self.traffic_control_agent = TrafficControlAgent("traffic_controller", center_position)
            await communication_manager.register_agent(self.traffic_control_agent)
            await self.traffic_control_agent.start()
            self.specialized_agents["traffic_controller"] = self.traffic_control_agent
            self.logger.info("Agente de control de tráfico inicializado")
            
            # Inicializar Agente Meteorológico
            # Definir área de cobertura (lat, lon, radio_km)
            coverage_area = (40.7128, -74.0060, 50.0)  # Nueva York, 50km de radio
            self.weather_agent = WeatherAgent("weather_agent", coverage_area)
            await communication_manager.register_agent(self.weather_agent)
            await self.weather_agent.start()
            self.specialized_agents["weather_agent"] = self.weather_agent
            self.logger.info("Agente meteorológico inicializado")
            
            # Inicializar Optimizador de Rutas
            # Definir área de optimización (lat, lon, radio_km)
            optimization_area = (40.7128, -74.0060, 25.0)  # Nueva York, 25km de radio
            self.route_optimizer_agent = RouteOptimizerAgent("route_optimizer", self.street_graph, optimization_area)
            await communication_manager.register_agent(self.route_optimizer_agent)
            await self.route_optimizer_agent.start()
            self.specialized_agents["route_optimizer"] = self.route_optimizer_agent
            self.logger.info("Agente optimizador de rutas inicializado")
            
        except Exception as e:
            self.logger.error(f"Error inicializando agentes especializados: {e}")
            raise

    async def _update_specialized_agents(self):
        """Actualiza todos los agentes especializados"""
        try:
            # Actualizar agente meteorológico
            if self.weather_agent:
                weather_data = await self.weather_agent.get_current_weather()
                if weather_data:
                    self.global_state["weather_conditions"].update(weather_data)
            
            # Actualizar control de tráfico
            if self.traffic_control_agent:
                # Obtener información de tráfico actual
                traffic_info = {
                    "vehicle_count": len(self.vehicle_agents),
                    "congestion_data": self.street_congestion,
                    "active_vehicles": {
                        vid: {
                            "position": v.position,
                            "current_node": getattr(v, 'current_node', None),
                            "state": v.vehicle_state.value if hasattr(v, 'vehicle_state') else "unknown"
                        }
                        for vid, v in self.vehicle_agents.items()
                    }
                }
                await self.traffic_control_agent.update_traffic_state(traffic_info)
            
            # Actualizar optimizador de rutas
            if self.route_optimizer_agent:
                # El optimizador trabaja bajo demanda cuando recibe solicitudes
                pass
                
        except Exception as e:
            self.logger.error(f"Error actualizando agentes especializados: {e}")
            raise

    # Métodos de utilidad para interactuar con agentes especializados
    
    async def request_route_optimization(self, start_node, end_node, vehicle_type="normal", priority="normal", constraints=None):
        """Solicita optimización de ruta al agente optimizador"""
        if not self.route_optimizer_agent:
            self.logger.warning("Optimizador de rutas no disponible")
            return None
            
        request = {
            "start_node": start_node,
            "end_node": end_node,
            "vehicle_type": vehicle_type,
            "priority": priority,
            "constraints": constraints or {}
        }
        
        return await self.route_optimizer_agent.optimize_route(request)
    
    async def get_weather_forecast(self, hours_ahead=24):
        """Obtiene pronóstico del tiempo del agente meteorológico"""
        if not self.weather_agent:
            self.logger.warning("Agente meteorológico no disponible")
            return None
            
        return await self.weather_agent.get_forecast(hours_ahead)
    
    async def trigger_weather_event(self, event_type, intensity=0.5, duration_minutes=30):
        """Desencadena un evento meteorológico específico"""
        if not self.weather_agent:
            self.logger.warning("Agente meteorológico no disponible")
            return False
            
        await self.weather_agent.trigger_event(event_type, intensity, duration_minutes)
        return True
    
    async def modify_traffic_light(self, intersection_id, state=None, timing=None):
        """Modifica el estado de un semáforo"""
        if not self.traffic_control_agent:
            self.logger.warning("Agente de control de tráfico no disponible")
            return False
            
        return await self.traffic_control_agent.modify_traffic_light(intersection_id, state, timing)
    
    async def trigger_emergency(self, emergency_type, location, severity="medium"):
        """Desencadena una emergencia en la simulación"""
        emergency_event = {
            "type": emergency_type,
            "location": location,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
            "id": f"emergency_{len(self.global_state.get('emergency_events', []))}"
        }
        
        self.global_state.setdefault("emergency_events", []).append(emergency_event)
        
        # Notificar a todos los agentes
        try:
            await communication_manager._broadcast_message({
                "type": MessageType.EMERGENCY.value,
                "content": emergency_event,
                "sender": "environment"
            }, topic="emergency")
        except:
            # Si no funciona el broadcast, continuar sin notificación
            pass
        
        self.logger.info(f"Emergencia activada: {emergency_type} en {location}")
        return emergency_event
    
    def get_simulation_statistics(self):
        """Retorna estadísticas detalladas de la simulación"""
        return {
            "basic_stats": self.simulation_stats,
            "agent_count": {
                "vehicles": len(self.vehicle_agents),
                "specialized": len(self.specialized_agents),
                "total": len(self.agents)
            },
            "weather_stats": self.global_state.get("weather_conditions", {}),
            "traffic_stats": {
                "total_intersections": len(getattr(self.traffic_control_agent, 'traffic_lights', {})) if self.traffic_control_agent else 0,
                "average_congestion": sum(self.street_congestion.values()) / len(self.street_congestion) if self.street_congestion else 0
            },
            "emergency_events": len(self.global_state.get("emergency_events", [])),
            "system_performance": {
                "running": self._running,
                "uptime_seconds": self.simulation_stats.get("total_simulation_time", 0)
            }
        }
# Instancia global del entorno de simulación
simulation_environment = None

def get_simulation_environment() -> Optional[SimulationEnvironment]:
    """Retorna la instancia global del entorno de simulación"""
    return simulation_environment

def create_simulation_environment(street_graph: nx.MultiDiGraph) -> SimulationEnvironment:
    """Crea una nueva instancia del entorno de simulación"""
    global simulation_environment
    simulation_environment = SimulationEnvironment(street_graph)
    return simulation_environment
