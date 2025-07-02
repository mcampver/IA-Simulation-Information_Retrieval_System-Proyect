# -*- coding: utf-8 -*-
"""
Handlers WebSocket para Agentes Especializados - Fase 2
Maneja interacciones con agentes de control de tráfico, meteorológicos y optimización
"""

import json
import asyncio
from typing import Dict, Any

async def handle_route_optimization_request(websocket, data, multi_agent_environment):
    """Maneja solicitudes de optimización de ruta usando agente especializado"""
    try:
        if not multi_agent_environment:
            await websocket.send(json.dumps({
                "type": "route_optimization_error",
                "message": "Sistema multi-agente no inicializado"
            }))
            return
        
        start_node = data.get('start_node')
        end_node = data.get('end_node')
        vehicle_type = data.get('vehicle_type', 'normal')
        priority = data.get('priority', 'normal')
        constraints = data.get('constraints', {})
        
        if not start_node or not end_node:
            await websocket.send(json.dumps({
                "type": "route_optimization_error",
                "message": "Se requieren nodos de inicio y fin"
            }))
            return
        
        # Solicitar optimización
        result = await multi_agent_environment.request_route_optimization(
            start_node, end_node, vehicle_type, priority, constraints
        )
        
        if result:
            await websocket.send(json.dumps({
                "type": "route_optimization_result",
                "data": result
            }))
        else:
            await websocket.send(json.dumps({
                "type": "route_optimization_error",
                "message": "No se pudo optimizar la ruta"
            }))
            
    except Exception as e:
        print(f"Error en optimización de ruta: {e}")
        await websocket.send(json.dumps({
            "type": "route_optimization_error",
            "message": f"Error: {str(e)}"
        }))

async def handle_weather_forecast_request(websocket, data, multi_agent_environment):
    """Maneja solicitudes de pronóstico del tiempo"""
    try:
        if not multi_agent_environment:
            await websocket.send(json.dumps({
                "type": "weather_forecast_error",
                "message": "Sistema multi-agente no inicializado"
            }))
            return
        
        hours_ahead = data.get('hours_ahead', 24)
        
        forecast = await multi_agent_environment.get_weather_forecast(hours_ahead)
        
        if forecast:
            await websocket.send(json.dumps({
                "type": "weather_forecast_result",
                "data": forecast
            }))
        else:
            await websocket.send(json.dumps({
                "type": "weather_forecast_error",
                "message": "No se pudo obtener el pronóstico"
            }))
            
    except Exception as e:
        print(f"Error en pronóstico del tiempo: {e}")
        await websocket.send(json.dumps({
            "type": "weather_forecast_error",
            "message": f"Error: {str(e)}"
        }))

async def handle_trigger_weather_event(websocket, data, multi_agent_environment):
    """Maneja solicitudes para desencadenar eventos meteorológicos"""
    try:
        if not multi_agent_environment:
            await websocket.send(json.dumps({
                "type": "weather_event_error",
                "message": "Sistema multi-agente no inicializado"
            }))
            return
        
        event_type = data.get('event_type')
        intensity = data.get('intensity', 0.5)
        duration_minutes = data.get('duration_minutes', 30)
        
        if not event_type:
            await websocket.send(json.dumps({
                "type": "weather_event_error",
                "message": "Tipo de evento requerido"
            }))
            return
        
        success = await multi_agent_environment.trigger_weather_event(
            event_type, intensity, duration_minutes
        )
        
        if success:
            await websocket.send(json.dumps({
                "type": "weather_event_result",
                "message": f"Evento {event_type} activado con éxito"
            }))
        else:
            await websocket.send(json.dumps({
                "type": "weather_event_error",
                "message": "No se pudo activar el evento"
            }))
            
    except Exception as e:
        print(f"Error activando evento meteorológico: {e}")
        await websocket.send(json.dumps({
            "type": "weather_event_error",
            "message": f"Error: {str(e)}"
        }))

async def handle_traffic_light_modification(websocket, data, multi_agent_environment):
    """Maneja modificaciones de semáforos"""
    try:
        if not multi_agent_environment:
            await websocket.send(json.dumps({
                "type": "traffic_light_error",
                "message": "Sistema multi-agente no inicializado"
            }))
            return
        
        intersection_id = data.get('intersection_id')
        state = data.get('state')
        timing = data.get('timing')
        
        if not intersection_id:
            await websocket.send(json.dumps({
                "type": "traffic_light_error",
                "message": "ID de intersección requerido"
            }))
            return
        
        success = await multi_agent_environment.modify_traffic_light(
            intersection_id, state, timing
        )
        
        if success:
            await websocket.send(json.dumps({
                "type": "traffic_light_result",
                "message": f"Semáforo {intersection_id} modificado con éxito"
            }))
        else:
            await websocket.send(json.dumps({
                "type": "traffic_light_error",
                "message": "No se pudo modificar el semáforo"
            }))
            
    except Exception as e:
        print(f"Error modificando semáforo: {e}")
        await websocket.send(json.dumps({
            "type": "traffic_light_error",
            "message": f"Error: {str(e)}"
        }))

async def handle_simulation_stats_request(websocket, data, multi_agent_environment):
    """Maneja solicitudes de estadísticas de simulación"""
    try:
        if not multi_agent_environment:
            await websocket.send(json.dumps({
                "type": "simulation_stats_error",
                "message": "Sistema multi-agente no inicializado"
            }))
            return
        
        stats = multi_agent_environment.get_simulation_statistics()
        
        await websocket.send(json.dumps({
            "type": "simulation_stats_result",
            "data": stats
        }))
        
    except Exception as e:
        print(f"Error obteniendo estadísticas: {e}")
        await websocket.send(json.dumps({
            "type": "simulation_stats_error",
            "message": f"Error: {str(e)}"
        }))

async def handle_emergency_event(websocket, data, multi_agent_environment):
    """Maneja eventos de emergencia"""
    try:
        if not multi_agent_environment:
            await websocket.send(json.dumps({
                "type": "emergency_error",
                "message": "Sistema multi-agente no inicializado"
            }))
            return
        
        emergency_type = data.get('type', 'accident')
        location = data.get('location', [0, 0])
        severity = data.get('severity', 'medium')
        
        emergency_event = await multi_agent_environment.trigger_emergency(
            emergency_type, location, severity
        )
        
        await websocket.send(json.dumps({
            "type": "emergency_created",
            "event": emergency_event
        }))
        
    except Exception as e:
        print(f"Error creando emergencia: {e}")
        await websocket.send(json.dumps({
            "type": "emergency_error",
            "message": f"Error: {str(e)}"
        }))

async def handle_spawn_vehicle(websocket, data, multi_agent_environment):
    """Maneja creación de nuevos vehículos"""
    try:
        if not multi_agent_environment:
            await websocket.send(json.dumps({
                "type": "spawn_vehicle_error",
                "message": "Sistema multi-agente no inicializado"
            }))
            return
        
        vehicle = await multi_agent_environment._spawn_vehicle()
        
        if vehicle:
            await websocket.send(json.dumps({
                "type": "vehicle_spawned",
                "vehicle_id": vehicle.agent_id,
                "position": vehicle.position
            }))
        else:
            await websocket.send(json.dumps({
                "type": "spawn_vehicle_error",
                "message": "No se pudo crear el vehículo"
            }))
        
    except Exception as e:
        print(f"Error creando vehículo: {e}")
        await websocket.send(json.dumps({
            "type": "spawn_vehicle_error",
            "message": f"Error: {str(e)}"
        }))

async def handle_start_simulation(websocket, data, multi_agent_environment):
    """Inicia la simulación multi-agente"""
    try:
        if not multi_agent_environment:
            await websocket.send(json.dumps({
                "type": "simulation_error",
                "message": "Sistema multi-agente no inicializado"
            }))
            return
        
        await multi_agent_environment.start_simulation()
        
        await websocket.send(json.dumps({
            "type": "simulation_started",
            "message": "Simulación multi-agente iniciada"
        }))
        
    except Exception as e:
        print(f"Error iniciando simulación: {e}")
        await websocket.send(json.dumps({
            "type": "simulation_error",
            "message": f"Error: {str(e)}"
        }))

async def handle_stop_simulation(websocket, data, multi_agent_environment):
    """Detiene la simulación multi-agente"""
    try:
        if not multi_agent_environment:
            await websocket.send(json.dumps({
                "type": "simulation_error",
                "message": "Sistema multi-agente no inicializado"
            }))
            return
        
        await multi_agent_environment.stop_simulation()
        
        await websocket.send(json.dumps({
            "type": "simulation_stopped",
            "message": "Simulación multi-agente detenida"
        }))
        
    except Exception as e:
        print(f"Error deteniendo simulación: {e}")
        await websocket.send(json.dumps({
            "type": "simulation_error",
            "message": f"Error: {str(e)}"
        }))
