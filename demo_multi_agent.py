"""
Demo y documentación del Sistema Multi-Agente con Lógica Difusa
Este archivo muestra cómo usar el nuevo sistema implementado
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

# Configurar logging
logging.basicConfig(level=logging.INFO)

async def demo_multi_agent_system():
    """Demostración del sistema multi-agente"""
    print("🚀 Iniciando demo del sistema multi-agente...")
    
    # 1. Crear un grafo de ejemplo
    print("📊 Creando grafo de ejemplo...")
    G = nx.Graph()
    
    # Añadir nodos con coordenadas
    nodes = [
        (1, {"lat": 23.1136, "lon": -82.3666}),
        (2, {"lat": 23.1146, "lon": -82.3656}),
        (3, {"lat": 23.1156, "lon": -82.3646}),
        (4, {"lat": 23.1126, "lon": -82.3676}),
        (5, {"lat": 23.1116, "lon": -82.3686})
    ]
    
    for node_id, data in nodes:
        G.add_node(node_id, **data)
    
    # Añadir aristas
    edges = [(1, 2), (2, 3), (1, 4), (4, 5), (2, 4)]
    for edge in edges:
        G.add_edge(edge[0], edge[1], weight=1.0)
    
    print(f"✅ Grafo creado con {len(G.nodes)} nodos y {len(G.edges)} aristas")
    
    # 2. Crear entorno de simulación
    print("🌍 Creando entorno de simulación...")
    env = create_simulation_environment(G)
    
    # 3. Inicializar y comenzar simulación
    print("⚙️ Inicializando simulación...")
    await env.initialize()
    await env.start_simulation()
    
    # 4. Ejecutar por unos segundos para ver la actividad
    print("🔄 Ejecutando simulación por 10 segundos...")
    await asyncio.sleep(10)
    
    # 5. Mostrar estadísticas
    print("\n📈 Estado de la simulación:")
    status = env.get_simulation_status()
    for key, value in status.items():
        if key != "communication_stats":
            print(f"  {key}: {value}")
    
    print("\n🚗 Vehículos activos:")
    vehicles = env.get_vehicle_positions()
    for vehicle in vehicles:
        print(f"  {vehicle['id']}: {vehicle['behavior']} - {vehicle['state']}")
    
    # 6. Crear evento de emergencia
    print("\n🚨 Creando evento de emergencia...")
    await env.add_emergency_event(
        "accident", 
        (23.1136, -82.3666), 
        {"severity": "high", "lanes_blocked": 2}
    )
    
    # Esperar un poco más para ver el efecto
    await asyncio.sleep(5)
    
    # 7. Detener simulación
    print("\n⏹️ Deteniendo simulación...")
    await env.stop_simulation()
    
    print("✅ Demo completada exitosamente!")

def show_architecture_info():
    """Muestra información sobre la arquitectura implementada"""
    print("\n" + "="*60)
    print("🏗️  ARQUITECTURA MULTI-AGENTE IMPLEMENTADA")
    print("="*60)
    
    print("\n📋 COMPONENTES PRINCIPALES:")
    print("  1. BaseAgent - Clase base para todos los agentes")
    print("  2. CommunicationManager - Sistema de mensajería")
    print("  3. EventBus - Comunicación publish-subscribe")
    print("  4. VehicleAgent - Agente vehículo con lógica difusa")
    print("  5. FuzzyLogicController - Controlador de lógica difusa")
    print("  6. SimulationEnvironment - Entorno de coordinación")
    
    print("\n🧠 CAPACIDADES DE LÓGICA DIFUSA:")
    print("  • Control de velocidad basado en densidad de tráfico")
    print("  • Adaptación a condiciones climáticas")
    print("  • Selección inteligente de rutas")
    print("  • Comportamientos diferenciados por vehículo")
    print("  • Toma de decisiones con incertidumbre")
    
    print("\n💬 SISTEMA DE COMUNICACIÓN:")
    print("  • Mensajes asíncronos entre agentes")
    print("  • Topics temáticos (tráfico, clima, emergencias)")
    print("  • Broadcast de emergencias")
    print("  • Historial de mensajes")
    
    print("\n🎯 TIPOS DE AGENTES:")
    print("  • VehicleAgent - Vehículos autónomos")
    print("  • (Futuro) TrafficControlAgent - Control de semáforos")
    print("  • (Futuro) WeatherAgent - Análisis climático")
    print("  • (Futuro) RouteOptimizerAgent - Optimización dinámica")
    
    print("\n🚗 COMPORTAMIENTOS DE VEHÍCULOS:")
    for behavior in VehicleBehavior:
        print(f"  • {behavior.value.upper()}")
    
    print("\n⚡ GENERACIÓN DE VARIABLES ALEATORIAS:")
    print("  • Spawning estocástico de vehículos")
    print("  • Cambios climáticos probabilísticos")
    print("  • Eventos de emergencia aleatorios")
    print("  • Rutas con variabilidad controlada")

if __name__ == "__main__":
    # Mostrar información de la arquitectura
    show_architecture_info()
    
    # Ejecutar demo
    print("\n" + "="*60)
    print("🎮 EJECUTANDO DEMOSTRACIÓN")
    print("="*60)
    
    try:
        asyncio.run(demo_multi_agent_system())
    except KeyboardInterrupt:
        print("\n❌ Demo interrumpida por el usuario")
    except Exception as e:
        print(f"\n❌ Error en demo: {e}")
