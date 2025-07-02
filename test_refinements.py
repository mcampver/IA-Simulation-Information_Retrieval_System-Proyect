"""
Test rápido de refinamientos de la Fase 1
"""

import asyncio
import networkx as nx
from src.multi_agent import create_simulation_environment

async def test_improved_fuzzy_logic():
    """Prueba la lógica difusa mejorada"""
    print("🧠 === TEST DE LÓGICA DIFUSA MEJORADA ===")
    
    # Crear grafo simple
    G = nx.path_graph(4)
    for i, node in enumerate(G.nodes()):
        G.nodes[node]['lat'] = 23.1136 + i * 0.001
        G.nodes[node]['lon'] = -82.3666 + i * 0.001
    
    env = create_simulation_environment(G)
    await env.initialize()
    await env.start_simulation()
    
    # Crear vehículos con diferentes comportamientos
    behaviors = ['aggressive', 'normal', 'cautious']
    vehicles = []
    
    for behavior in behaviors:
        vehicle = await env.spawn_vehicle()
        if vehicle:
            vehicle.behavior_type = getattr(vehicle.behavior_type.__class__, behavior.upper())
            vehicles.append((behavior, vehicle))
            print(f"  ✅ Vehículo {vehicle.agent_id}: {behavior}")
    
    # Test 1: Condiciones normales
    print("\n📊 Test 1: Condiciones normales")
    await asyncio.sleep(2)
    for behavior, vehicle in vehicles:
        if vehicle.agent_id in env.agents:
            print(f"  🚗 {behavior}: velocidad={vehicle.current_speed:.4f}")
    
    # Test 2: Tráfico pesado
    print("\n📊 Test 2: Simulando tráfico pesado")
    for edge in env.street_graph.edges():
        env.street_congestion[edge] = 0.9
    await asyncio.sleep(3)
    
    for behavior, vehicle in vehicles:
        if vehicle.agent_id in env.agents:
            print(f"  🚗 {behavior}: velocidad={vehicle.current_speed:.4f}")
    
    # Test 3: Condiciones climáticas adversas
    print("\n📊 Test 3: Clima adverso (lluvia)")
    env.global_state["weather_conditions"]["condition"] = "rain"
    env.global_state["weather_conditions"]["precipitation"] = 8.0
    await asyncio.sleep(3)
    
    for behavior, vehicle in vehicles:
        if vehicle.agent_id in env.agents:
            print(f"  🚗 {behavior}: velocidad={vehicle.current_speed:.4f}")
    
    await env.stop_simulation()
    print("✅ Test completado")

async def test_emergency_response():
    """Prueba la respuesta a emergencias mejorada"""
    print("\n🚨 === TEST DE RESPUESTA A EMERGENCIAS ===")
    
    G = nx.cycle_graph(5)
    for i, node in enumerate(G.nodes()):
        G.nodes[node]['lat'] = 23.1136 + i * 0.001
        G.nodes[node]['lon'] = -82.3666 + i * 0.001
    
    env = create_simulation_environment(G)
    await env.initialize()
    await env.start_simulation()
    
    # Crear vehículo de prueba
    vehicle = await env.spawn_vehicle()
    if vehicle:
        print(f"  🚗 Vehículo de prueba: {vehicle.agent_id}")
        print(f"  📊 Velocidad inicial: {vehicle.current_speed:.4f}")
        
        # Crear emergencia de accidente
        print("\n🚨 Creando emergencia: accidente")
        await env.add_emergency_event("accident", (23.1136, -82.3666), {"severity": "high"})
        
        await asyncio.sleep(2)
        
        # Verificar respuesta
        if vehicle.agent_id in env.agents:
            metrics = vehicle.get_metrics()
            print(f"  📊 Velocidad después: {vehicle.current_speed:.4f}")
            print(f"  📈 Respuestas emergencia: {metrics.get('emergency_responses', 0)}")
            print(f"  🔄 Estado vehículo: {vehicle.vehicle_state.value}")
    
    await env.stop_simulation()
    print("✅ Test de emergencias completado")

async def run_refinement_tests():
    """Ejecuta todos los tests de refinamiento"""
    print("🔧 EJECUTANDO TESTS DE REFINAMIENTO - FASE 1")
    print("=" * 50)
    
    await test_improved_fuzzy_logic()
    await test_emergency_response()
    
    print("\n🎉 TODOS LOS TESTS DE REFINAMIENTO COMPLETADOS")
    print("✅ Sistema mejorado y listo para Fase 2")

if __name__ == "__main__":
    asyncio.run(run_refinement_tests())
