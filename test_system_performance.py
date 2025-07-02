#!/usr/bin/env python3
"""
Script de prueba de rendimiento para el sistema multi-agente.
Evalúa el comportamiento y métricas del sistema bajo diferentes condiciones.
"""

import asyncio
import time
import matplotlib.pyplot as plt
import networkx as nx
import json
from datetime import datetime, timedelta
from src.multi_agent import SimulationEnvironment
from src.multi_agent.communication import MessageType

async def test_system_scalability():
    """Prueba la escalabilidad del sistema con diferentes números de vehículos"""
    print("=== PRUEBA DE ESCALABILIDAD ===")
    
    # Crear un grafo más grande para las pruebas
    G = nx.grid_2d_graph(10, 10)  # Malla 10x10 = 100 nodos
    
    # Convertir nodos a formato (x, y) y agregar atributos
    for node in G.nodes():
        G.nodes[node]['x'] = node[0] * 100
        G.nodes[node]['y'] = node[1] * 100
    
    vehicle_counts = [5, 10, 20, 30, 50]
    performance_metrics = []
    
    for vehicle_count in vehicle_counts:
        print(f"\n🚗 Probando con {vehicle_count} vehículos...")
        
        # Crear entorno
        env = SimulationEnvironment(G)
        await env.initialize()
        
        # Medir tiempo de inicio
        start_time = time.time()
        await env.start_simulation()
        
        # Crear vehículos
        for i in range(vehicle_count):
            await env.spawn_vehicle()
        
        # Ejecutar simulación por 30 segundos
        await asyncio.sleep(30)
        
        # Obtener métricas
        status = env.get_simulation_status()
        end_time = time.time()
        
        metrics = {
            'vehicle_count': vehicle_count,
            'execution_time': end_time - start_time,
            'active_vehicles': status['active_agents'],
            'communication_stats': status.get('communication_stats', {}),
            'memory_usage': status.get('memory_usage', 0),
            'cpu_usage': status.get('cpu_usage', 0)
        }
        
        performance_metrics.append(metrics)
        print(f"  ✅ Completado - Tiempo: {metrics['execution_time']:.2f}s")
        
        # Detener simulación
        await env.stop_simulation()
    
    return performance_metrics

async def test_fuzzy_logic_behavior():
    """Prueba el comportamiento de la lógica difusa bajo diferentes condiciones"""
    print("\n=== PRUEBA DE LÓGICA DIFUSA ===")
    
    # Crear grafo simple
    G = nx.cycle_graph(20)
    for i, node in enumerate(G.nodes()):
        G.nodes[node]['x'] = i * 50
        G.nodes[node]['y'] = 0
    
    env = SimulationEnvironment(G)
    await env.initialize()
    await env.start_simulation()
    
    # Crear vehículos con diferentes comportamientos
    behaviors = ['normal', 'aggressive', 'cautious', 'slow', 'fast']
    test_vehicles = []
    
    for behavior in behaviors:
        vehicle = await env.spawn_vehicle()
        if vehicle:
            # Cambiar comportamiento del vehículo
            vehicle.behavior_type = behavior
            test_vehicles.append((behavior, vehicle))
    
    # Simular diferentes condiciones
    conditions = [
        {'traffic_density': 0.1, 'weather': 'clear', 'description': 'Condiciones ideales'},
        {'traffic_density': 0.5, 'weather': 'rain', 'description': 'Tráfico medio con lluvia'},
        {'traffic_density': 0.8, 'weather': 'fog', 'description': 'Tráfico pesado con niebla'},
        {'traffic_density': 0.9, 'weather': 'rain', 'description': 'Tráfico muy pesado'},
    ]
    
    results = []
    
    for condition in conditions:
        print(f"\n🌤️  Probando: {condition['description']}")
        
        # Establecer condiciones
        env.global_state['weather_conditions']['condition'] = condition['weather']
        
        # Simular por 10 segundos
        await asyncio.sleep(10)
        
        # Recopilar datos de comportamiento
        vehicle_data = []
        for behavior, vehicle in test_vehicles:
            if vehicle.agent_id in env.agents:
                vehicle_data.append({
                    'behavior': behavior,
                    'speed': vehicle.state.get('speed', 0),
                    'stress_level': vehicle.state.get('stress_level', 0),
                    'route_changes': vehicle.metrics.get('route_changes', 0),
                    'messages_sent': vehicle.metrics.get('messages_sent', 0)
                })
        
        results.append({
            'condition': condition['description'],
            'vehicles': vehicle_data
        })
    
    await env.stop_simulation()
    return results

async def test_communication_system():
    """Prueba el sistema de comunicación entre agentes"""
    print("\n=== PRUEBA DE COMUNICACIÓN ===")
    
    G = nx.complete_graph(10)
    for i, node in enumerate(G.nodes()):
        G.nodes[node]['x'] = i * 30
        G.nodes[node]['y'] = 0
    
    env = SimulationEnvironment(G)
    await env.initialize()
    await env.start_simulation()
    
    # Crear varios vehículos
    vehicles = []
    for i in range(5):
        vehicle = await env.spawn_vehicle()
        if vehicle:
            vehicles.append(vehicle)
    
    # Probar diferentes tipos de mensajes
    print("📡 Enviando mensajes de prueba...")
    
    # Mensaje directo
    if len(vehicles) >= 2:
        await vehicles[0].send_message(
            vehicles[1].agent_id,
            MessageType.NOTIFICATION,
            {"message": "Hola desde vehicle_0"}
        )
    
    # Mensaje a topic
    await env.get_communication_manager().send_to_topic(
        "traffic",
        "environment",
        MessageType.NOTIFICATION,
        {"traffic_update": "Heavy traffic detected"}
    )
    
    # Mensaje de emergencia
    await env.add_emergency_event("road_closure", (0, 0), {"location": "Main Street"})
    
    await asyncio.sleep(5)
    
    # Obtener estadísticas de comunicación
    comm_stats = env.get_communication_manager().get_communication_stats()
    print(f"📊 Estadísticas de comunicación:")
    print(f"  Total mensajes: {comm_stats['total_messages']}")
    print(f"  Mensajes por tipo: {dict(comm_stats['messages_by_type'])}")
    print(f"  Entregas fallidas: {comm_stats['failed_deliveries']}")
    
    await env.stop_simulation()
    return comm_stats

async def run_comprehensive_test():
    """Ejecuta todas las pruebas y genera un reporte"""
    print("🧪 INICIANDO PRUEBAS COMPLETAS DEL SISTEMA MULTI-AGENTE")
    print("=" * 60)
    
    # Ejecutar pruebas
    scalability_results = await test_system_scalability()
    fuzzy_results = await test_fuzzy_logic_behavior()
    communication_results = await test_communication_system()
    
    # Generar reporte
    report = {
        'timestamp': datetime.now().isoformat(),
        'scalability_test': scalability_results,
        'fuzzy_logic_test': fuzzy_results,
        'communication_test': communication_results
    }
    
    # Guardar reporte
    with open('system_performance_report.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print("\n📈 RESUMEN DE RESULTADOS:")
    print(f"✅ Prueba de escalabilidad: {len(scalability_results)} configuraciones probadas")
    print(f"✅ Prueba de lógica difusa: {len(fuzzy_results)} condiciones evaluadas")
    print(f"✅ Prueba de comunicación: {communication_results['total_messages']} mensajes procesados")
    print("📄 Reporte detallado guardado en: system_performance_report.json")
    
    return report

if __name__ == "__main__":
    asyncio.run(run_comprehensive_test())
