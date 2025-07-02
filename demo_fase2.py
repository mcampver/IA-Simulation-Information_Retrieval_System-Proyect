# -*- coding: utf-8 -*-
"""
Demostración de Fase 2: Agentes Especializados
Sistema Multi-Agente con Control de Tráfico, Meteorología y Optimización Avanzada
"""

import asyncio
import logging
import json
from datetime import datetime
import sys
import os

# Añadir directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def demo_fase2():
    """Demostración completa de la Fase 2"""
    print("🚀 DEMOSTRACIÓN FASE 2: AGENTES ESPECIALIZADOS")
    print("=" * 60)
    
    try:
        # Importar componentes necesarios
        import networkx as nx
        from src.multi_agent.simulation_environment import create_simulation_environment
        from src.multi_agent.communication import communication_manager
        
        print("📊 Creando grafo de calles de demostración...")
        # Crear un grafo simple para demostración
        street_graph = nx.MultiDiGraph()
        
        # Añadir nodos con coordenadas
        nodes_data = [
            (1, {"lat": 40.7128, "lon": -74.0060}),  # NYC
            (2, {"lat": 40.7589, "lon": -73.9851}),  # Times Square  
            (3, {"lat": 40.7614, "lon": -73.9776}),  # Central Park
            (4, {"lat": 40.7505, "lon": -73.9934}),  # Penn Station
            (5, {"lat": 40.7484, "lon": -73.9857}),  # Empire State
            (6, {"lat": 40.7411, "lon": -74.0024}),  # SoHo
            (7, {"lat": 40.7282, "lon": -73.9942}),  # Washington Square
            (8, {"lat": 40.7178, "lon": -74.0431}),  # Battery Park
        ]
        
        for node_id, data in nodes_data:
            street_graph.add_node(node_id, **data)
        
        # Añadir aristas bidireccionales
        edges = [
            (1, 2, 1.2), (2, 3, 0.8), (3, 4, 1.0), (4, 5, 0.5),
            (5, 6, 1.1), (6, 7, 0.9), (7, 8, 1.3), (8, 1, 1.4),
            (2, 5, 0.7), (3, 6, 1.5), (4, 7, 1.0), (1, 5, 1.6)
        ]
        
        for n1, n2, weight in edges:
            street_graph.add_edge(n1, n2, weight=weight, max_speed=50, min_speed=30)
            street_graph.add_edge(n2, n1, weight=weight, max_speed=50, min_speed=30)
        
        print(f"   Nodos: {street_graph.number_of_nodes()}")
        print(f"   Aristas: {street_graph.number_of_edges()}")
        
        print("\n🏗️ Creando entorno de simulación...")
        env = create_simulation_environment(street_graph)
        
        print("🔧 Inicializando sistema multi-agente...")
        await env.initialize()
        
        print("✅ Sistema inicializado con éxito!")
        print(f"   - Agentes especializados: {len(env.specialized_agents)}")
        print(f"   - Agente de control de tráfico: {'✓' if env.traffic_control_agent else '✗'}")
        print(f"   - Agente meteorológico: {'✓' if env.weather_agent else '✗'}")
        print(f"   - Optimizador de rutas: {'✓' if env.route_optimizer_agent else '✗'}")
        
        print("\n🚗 Iniciando simulación...")
        await env.start_simulation()
        
        # Demostrar funcionalidades de Fase 2
        await demo_weather_agent(env)
        await demo_traffic_control(env)
        await demo_route_optimization(env)
        await demo_emergency_scenario(env)
        await demo_agent_interactions(env)
        
        print("\n📈 Recopilando estadísticas finales...")
        stats = env.get_simulation_statistics()
        print_simulation_stats(stats)
        
        print("\n⏹️ Deteniendo simulación...")
        await env.stop_simulation()
        
        print("✅ Demostración de Fase 2 completada con éxito!")
        
    except Exception as e:
        print(f"❌ Error durante la demostración: {e}")
        import traceback
        traceback.print_exc()

async def demo_weather_agent(env):
    """Demuestra las capacidades del agente meteorológico"""
    print("\n🌤️ DEMOSTRACIÓN: AGENTE METEOROLÓGICO")
    print("-" * 40)
    
    if not env.weather_agent:
        print("❌ Agente meteorológico no disponible")
        return
    
    # Obtener estado actual del tiempo
    print("☀️ Estado actual del tiempo:")
    current_weather = await env.weather_agent.get_current_weather()
    if current_weather:
        for key, value in current_weather.items():
            print(f"   {key}: {value}")
    
    # Obtener pronóstico
    print("\n🔮 Pronóstico a 12 horas:")
    forecast = await env.get_weather_forecast(12)
    if forecast:
        print(f"   Eventos previstos: {len(forecast.get('events', []))}")
        for event in forecast.get('events', [])[:3]:  # Mostrar solo 3
            print(f"   - {event.get('type', 'unknown')} a las {event.get('hour', 0)}h")
    
    # Desencadenar eventos meteorológicos
    print("\n🌧️ Desencadenando evento de lluvia...")
    await env.trigger_weather_event("rain", intensity=0.7, duration_minutes=10)
    
    await asyncio.sleep(2)  # Esperar un poco
    
    print("❄️ Desencadenando evento de nieve...")
    await env.trigger_weather_event("snow", intensity=0.4, duration_minutes=5)
    
    await asyncio.sleep(1)
    print("✅ Eventos meteorológicos activados")

async def demo_traffic_control(env):
    """Demuestra las capacidades del agente de control de tráfico"""
    print("\n🚦 DEMOSTRACIÓN: CONTROL DE TRÁFICO")
    print("-" * 40)
    
    if not env.traffic_control_agent:
        print("❌ Agente de control de tráfico no disponible")
        return
    
    # Información de tráfico actual
    traffic_lights = getattr(env.traffic_control_agent, 'traffic_lights', {})
    print(f"🔍 Semáforos gestionados: {len(traffic_lights)}")
    
    # Modificar algunos semáforos si existen
    if traffic_lights:
        intersection_id = list(traffic_lights.keys())[0]
        print(f"🔧 Modificando semáforo {intersection_id}...")
        
        success = await env.modify_traffic_light(intersection_id, state="red", timing=30)
        if success:
            print(f"✅ Semáforo {intersection_id} modificado a rojo (30s)")
        else:
            print(f"❌ No se pudo modificar el semáforo {intersection_id}")
    
    # Mostrar información de congestión
    avg_congestion = sum(env.street_congestion.values()) / len(env.street_congestion) if env.street_congestion else 0
    print(f"📊 Congestión promedio: {avg_congestion:.2%}")
    
    print("✅ Demostración de control de tráfico completada")

async def demo_route_optimization(env):
    """Demuestra las capacidades del optimizador de rutas"""
    print("\n🗺️ DEMOSTRACIÓN: OPTIMIZACIÓN DE RUTAS")
    print("-" * 40)
    
    if not env.route_optimizer_agent:
        print("❌ Optimizador de rutas no disponible")
        return
    
    # Obtener nodos aleatorios para demostración
    all_nodes = list(env.street_graph.nodes())
    if len(all_nodes) < 2:
        print("❌ No hay suficientes nodos para optimización")
        return
    
    start_node = all_nodes[0]
    end_node = all_nodes[min(10, len(all_nodes) - 1)]
    
    print(f"🎯 Optimizando ruta de {start_node} a {end_node}")
    
    # Probar diferentes tipos de optimización
    algorithms = ["dijkstra", "astar", "genetic", "ant_colony"]
    
    for algo in algorithms:
        print(f"\n🔄 Probando algoritmo: {algo}")
        
        result = await env.request_route_optimization(
            start_node, end_node, 
            vehicle_type="normal", 
            priority="normal",
            constraints={"algorithm": algo}
        )
        
        if result:
            route = result.get("route", [])
            cost = result.get("total_cost", 0)
            algorithm_used = result.get("algorithm", "unknown")
            
            print(f"   ✅ Ruta encontrada ({algorithm_used})")
            print(f"   📏 Longitud: {len(route)} nodos")
            print(f"   💰 Costo: {cost:.2f}")
            print(f"   ⏱️ Tiempo: {result.get('computation_time', 0):.3f}s")
        else:
            print(f"   ❌ No se encontró ruta con {algo}")
    
    print("✅ Demostración de optimización completada")

async def demo_emergency_scenario(env):
    """Demuestra manejo de escenarios de emergencia"""
    print("\n🚨 DEMOSTRACIÓN: ESCENARIOS DE EMERGENCIA")
    print("-" * 40)
    
    # Crear emergencia
    emergency_location = [40.7128, -74.0060]  # Coordenadas de ejemplo
    
    print("🆘 Activando emergencia: Accidente de tráfico")
    emergency = await env.trigger_emergency(
        "traffic_accident", 
        emergency_location, 
        severity="high"
    )
    
    if emergency:
        print(f"   ID: {emergency.get('id')}")
        print(f"   Ubicación: {emergency.get('location')}")
        print(f"   Severidad: {emergency.get('severity')}")
        print(f"   Hora: {emergency.get('timestamp')}")
    
    await asyncio.sleep(3)  # Simular tiempo de respuesta
    
    print("\n🔥 Activando emergencia: Incendio")
    fire_emergency = await env.trigger_emergency(
        "fire", 
        [40.7500, -73.9850], 
        severity="critical"
    )
    
    if fire_emergency:
        print(f"   Emergencia de incendio activada: {fire_emergency.get('id')}")
    
    # Mostrar estadísticas de emergencias
    total_emergencies = len(env.global_state.get("emergency_events", []))
    print(f"\n📊 Total de emergencias activas: {total_emergencies}")
    
    print("✅ Demostración de emergencias completada")

async def demo_agent_interactions(env):
    """Demuestra interacciones entre agentes"""
    print("\n🤝 DEMOSTRACIÓN: INTERACCIONES ENTRE AGENTES")
    print("-" * 40)
    
    print(f"👥 Agentes activos:")
    print(f"   - Vehículos: {len(env.vehicle_agents)}")
    print(f"   - Especializados: {len(env.specialized_agents)}")
    print(f"   - Total: {len(env.agents)}")
    
    # Crear algunos vehículos adicionales
    print("\n🚗 Creando vehículos adicionales...")
    for i in range(3):
        vehicle = await env._spawn_vehicle()
        if vehicle:
            print(f"   ✅ Vehículo {vehicle.agent_id} creado")
        await asyncio.sleep(0.5)
    
    # Simular comunicación entre agentes
    print(f"\n📡 Estado de comunicación:")
    print(f"   - Sistema de comunicación activo: ✓")
    print(f"   - Agentes pueden intercambiar mensajes")
    
    print("✅ Demostración de interacciones completada")

def print_simulation_stats(stats):
    """Imprime estadísticas de simulación de forma legible"""
    print("\n📊 ESTADÍSTICAS DE SIMULACIÓN")
    print("-" * 40)
    
    basic_stats = stats.get("basic_stats", {})
    print(f"🔢 Estadísticas básicas:")
    print(f"   - Vehículos creados: {basic_stats.get('total_vehicles_spawned', 0)}")
    print(f"   - Tiempo de simulación: {basic_stats.get('total_simulation_time', 0):.1f}s")
    
    agent_count = stats.get("agent_count", {})
    print(f"\n👥 Conteo de agentes:")
    print(f"   - Vehículos: {agent_count.get('vehicles', 0)}")
    print(f"   - Especializados: {agent_count.get('specialized', 0)}")
    print(f"   - Total: {agent_count.get('total', 0)}")
    
    weather_stats = stats.get("weather_stats", {})
    print(f"\n🌤️ Estado meteorológico:")
    print(f"   - Temperatura: {weather_stats.get('temperature', 0)}°C")
    print(f"   - Humedad: {weather_stats.get('humidity', 0)}%")
    print(f"   - Precipitación: {weather_stats.get('precipitation', 0)}mm")
    print(f"   - Visibilidad: {weather_stats.get('visibility', 0)}km")
    
    traffic_stats = stats.get("traffic_stats", {})
    print(f"\n🚦 Estadísticas de tráfico:")
    print(f"   - Intersecciones: {traffic_stats.get('total_intersections', 0)}")
    print(f"   - Congestión promedio: {traffic_stats.get('average_congestion', 0):.2%}")
    
    print(f"\n🆘 Eventos de emergencia: {stats.get('emergency_events', 0)}")
    
    performance = stats.get("system_performance", {})
    print(f"\n⚡ Rendimiento del sistema:")
    print(f"   - Estado: {'Activo' if performance.get('running', False) else 'Inactivo'}")
    print(f"   - Tiempo activo: {performance.get('uptime_seconds', 0):.1f}s")

if __name__ == "__main__":
    print("🚀 Iniciando demostración de Fase 2...")
    try:
        asyncio.run(demo_fase2())
    except KeyboardInterrupt:
        print("\n⚠️ Demostración interrumpida por el usuario")
    except Exception as e:
        print(f"\n❌ Error en la demostración: {e}")
        import traceback
        traceback.print_exc()
