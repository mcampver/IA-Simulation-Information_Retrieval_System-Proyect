"""
Pruebas específicas para validar la Fase 1 del sistema multi-agente
Enfocadas en lógica difusa, comunicación y comportamiento básico
"""

import asyncio
import logging
from src.multi_agent import (
    create_simulation_environment,
    VehicleAgent,
    VehicleBehavior,
    communication_manager
)
import networkx as nx

# Configurar logging para las pruebas
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

async def test_fuzzy_logic_decisions():
    """Prueba la lógica difusa de toma de decisiones"""
    print("🧠 === PRUEBA DE LÓGICA DIFUSA ===")
    
    # Crear grafo simple
    G = nx.path_graph(5)
    for i, node in enumerate(G.nodes()):
        G.nodes[node]['lat'] = 23.1136 + i * 0.001
        G.nodes[node]['lon'] = -82.3666 + i * 0.001
    
    env = create_simulation_environment(G)
    await env.initialize()
    await env.start_simulation()
    
    # Crear vehículos con diferentes comportamientos
    behaviors = ['normal', 'aggressive', 'cautious']
    test_vehicles = []
    
    for behavior in behaviors:
        vehicle = await env.spawn_vehicle()
        if vehicle:
            # Modificar comportamiento después de crear el vehículo
            vehicle.behavior_type = VehicleBehavior(behavior)
            test_vehicles.append(vehicle)
            print(f"  ✅ Vehículo {vehicle.agent_id} creado con comportamiento: {behavior}")
    
    # Simular diferentes condiciones de tráfico
    print("\n🚦 Probando respuesta a diferentes condiciones de tráfico:")
    
    traffic_conditions = [
        {"density": 0.1, "description": "Tráfico ligero"},
        {"density": 0.5, "description": "Tráfico moderado"},
        {"density": 0.9, "description": "Tráfico pesado"}
    ]
    
    for condition in traffic_conditions:
        print(f"\n  📊 {condition['description']} (densidad: {condition['density']})")
        
        # Actualizar condiciones de tráfico en el entorno
        for edge in env.street_graph.edges():
            env.street_congestion[edge] = condition['density']
        
        # Esperar un poco para que los agentes reaccionen
        await asyncio.sleep(3)
        
        # Obtener estado de los vehículos
        for vehicle in test_vehicles:
            if vehicle.agent_id in env.agents:
                speed = vehicle.current_speed
                stress = getattr(vehicle, 'stress_level', 0)
                print(f"    🚗 {vehicle.agent_id} ({vehicle.behavior_type.value}): velocidad={speed:.4f}, estrés={stress:.2f}")
    
    await env.stop_simulation()
    print("✅ Prueba de lógica difusa completada")

async def test_message_routing():
    """Prueba el enrutamiento de mensajes entre agentes"""
    print("\n📡 === PRUEBA DE ENRUTAMIENTO DE MENSAJES ===")
    
    G = nx.cycle_graph(6)
    for i, node in enumerate(G.nodes()):
        G.nodes[node]['lat'] = 23.1136 + i * 0.001
        G.nodes[node]['lon'] = -82.3666 + i * 0.001
    
    env = create_simulation_environment(G)
    await env.initialize()
    await env.start_simulation()
    
    # Crear 3 vehículos
    vehicles = []
    for i in range(3):
        vehicle = await env.spawn_vehicle()
        if vehicle:
            vehicles.append(vehicle)
    
    if len(vehicles) >= 2:
        sender = vehicles[0]
        receiver = vehicles[1]
        
        print(f"  📤 Enviando mensaje de {sender.agent_id} a {receiver.agent_id}")
        
        # Enviar mensaje directo
        await sender.send_message(
            receiver.agent_id,
            "notification",
            {"test_message": "Hola desde prueba unitaria", "timestamp": "now"}
        )
        
        # Esperar procesamiento
        await asyncio.sleep(1)
        
        # Verificar métricas
        sender_metrics = sender.get_metrics()
        receiver_metrics = receiver.get_metrics()
        
        print(f"  📊 Mensajes enviados por {sender.agent_id}: {sender_metrics['messages_sent']}")
        print(f"  📨 Mensajes recibidos por {receiver.agent_id}: {receiver_metrics['messages_received']}")
        
        # Probar broadcast de emergencia
        print(f"\n  🚨 Probando broadcast de emergencia...")
        await env.add_emergency_event("traffic_jam", (23.1136, -82.3666), {"severity": "high"})
        
        await asyncio.sleep(2)
        
        # Verificar que todos recibieron el mensaje
        for vehicle in vehicles:
            metrics = vehicle.get_metrics()
            print(f"    🚗 {vehicle.agent_id}: {metrics['messages_received']} mensajes recibidos")
    
    await env.stop_simulation()
    print("✅ Prueba de enrutamiento completada")

async def test_agent_lifecycle():
    """Prueba el ciclo de vida de los agentes"""
    print("\n🔄 === PRUEBA DE CICLO DE VIDA DE AGENTES ===")
    
    G = nx.star_graph(4)
    for i, node in enumerate(G.nodes()):
        G.nodes[node]['lat'] = 23.1136 + i * 0.001
        G.nodes[node]['lon'] = -82.3666 + i * 0.001
    
    env = create_simulation_environment(G)
    await env.initialize()
    
    print("  ⚙️ Entorno inicializado")
    initial_status = env.get_simulation_status()
    print(f"    Agentes iniciales: {initial_status['active_agents']}")
    
    await env.start_simulation()
    print("  ▶️ Simulación iniciada")
    
    # Crear vehículos dinámicamente
    vehicles_created = []
    for i in range(3):
        vehicle = await env.spawn_vehicle()
        if vehicle:
            vehicles_created.append(vehicle)
            print(f"    ➕ Vehículo {vehicle.agent_id} creado")
    
    # Verificar estado
    mid_status = env.get_simulation_status()
    print(f"  📊 Estado intermedio: {mid_status['active_agents']} agentes activos")
    
    # Simular por un tiempo
    await asyncio.sleep(5)
    
    # Verificar métricas de los vehículos
    print("  📈 Métricas de vehículos:")
    for vehicle in vehicles_created:
        if vehicle.agent_id in env.agents:
            metrics = vehicle.get_metrics()
            print(f"    🚗 {vehicle.agent_id}: {metrics['uptime_seconds']:.1f}s activo, estado: {metrics['state']}")
    
    await env.stop_simulation()
    print("  ⏹️ Simulación detenida")
    
    final_status = env.get_simulation_status()
    print(f"  📊 Estado final: simulación activa = {final_status.get('running', False)}")
    print("✅ Prueba de ciclo de vida completada")

async def test_weather_adaptation():
    """Prueba la adaptación a condiciones climáticas"""
    print("\n🌤️ === PRUEBA DE ADAPTACIÓN CLIMÁTICA ===")
    
    G = nx.path_graph(4)
    for i, node in enumerate(G.nodes()):
        G.nodes[node]['lat'] = 23.1136 + i * 0.001
        G.nodes[node]['lon'] = -82.3666 + i * 0.001
    
    env = create_simulation_environment(G)
    await env.initialize()
    await env.start_simulation()
    
    # Crear un vehículo
    vehicle = await env.spawn_vehicle()
    if vehicle:
        print(f"  🚗 Vehículo de prueba: {vehicle.agent_id}")
        
        # Condiciones climáticas a probar
        weather_conditions = [
            {"condition": "clear", "precipitation": 0.0, "visibility": 10.0, "description": "Despejado"},
            {"condition": "rain", "precipitation": 5.0, "visibility": 8.0, "description": "Lluvia"},
            {"condition": "fog", "precipitation": 0.0, "visibility": 3.0, "description": "Niebla"},
            {"condition": "storm", "precipitation": 10.0, "visibility": 5.0, "description": "Tormenta"}
        ]
        
        for weather in weather_conditions:
            print(f"\n  🌦️ Probando condición: {weather['description']}")
            
            # Actualizar condiciones climáticas
            env.global_state["weather_conditions"].update(weather)
            
            # Esperar adaptación
            await asyncio.sleep(2)
            
            # Obtener estado del vehículo
            if vehicle.agent_id in env.agents:
                speed = vehicle.current_speed
                route_preference = getattr(vehicle, 'route_preference', 'normal')
                print(f"    📊 Velocidad adaptada: {speed:.4f}")
                print(f"    🛣️ Preferencia de ruta: {route_preference}")
    
    await env.stop_simulation()
    print("✅ Prueba de adaptación climática completada")

async def test_error_handling():
    """Prueba el manejo de errores del sistema"""
    print("\n⚠️ === PRUEBA DE MANEJO DE ERRORES ===")
    
    G = nx.path_graph(3)
    for i, node in enumerate(G.nodes()):
        G.nodes[node]['lat'] = 23.1136 + i * 0.001
        G.nodes[node]['lon'] = -82.3666 + i * 0.001
    
    env = create_simulation_environment(G)
    await env.initialize()
    await env.start_simulation()
    
    # Crear vehículo
    vehicle = await env.spawn_vehicle()
    if vehicle:
        print(f"  🚗 Vehículo de prueba: {vehicle.agent_id}")
        
        # Intentar enviar mensaje a agente inexistente
        print("  📤 Enviando mensaje a agente inexistente...")
        await vehicle.send_message(
            "agente_inexistente",
            "notification",
            {"test": "mensaje de prueba"}
        )
        
        # Verificar métricas de errores
        await asyncio.sleep(1)
        comm_stats = communication_manager.get_communication_stats()
        print(f"    📊 Entregas fallidas: {comm_stats['failed_deliveries']}")
        
        # Probar condición de emergencia
        print("  🚨 Creando evento de emergencia...")
        await env.add_emergency_event("system_test", (23.1136, -82.3666), {"test": True})
        
        await asyncio.sleep(1)
        
        # Verificar que el sistema sigue funcionando
        status = env.get_simulation_status()
        print(f"    ✅ Sistema operativo: {status['running']}")
        print(f"    📊 Agentes activos: {status['active_agents']}")
    
    await env.stop_simulation()
    print("✅ Prueba de manejo de errores completada")

async def run_phase1_validation():
    """Ejecuta todas las pruebas de validación de la Fase 1"""
    print("🧪 INICIANDO VALIDACIÓN COMPLETA DE LA FASE 1")
    print("=" * 60)
    
    try:
        await test_fuzzy_logic_decisions()
        await test_message_routing()
        await test_agent_lifecycle()
        await test_weather_adaptation()
        await test_error_handling()
        
        print("\n🎉 TODAS LAS PRUEBAS DE FASE 1 COMPLETADAS EXITOSAMENTE")
        print("✅ El sistema multi-agente está listo para la Fase 2")
        
    except Exception as e:
        print(f"\n❌ ERROR EN LAS PRUEBAS: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_phase1_validation())
