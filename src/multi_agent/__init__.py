"""
Sistema Multi-Agente para Simulación de Tránsito
Implementa arquitectura de agentes autónomos con lógica difusa
"""

from .base_agent import BaseAgent, Message, MessageType, AgentState
from .communication import CommunicationManager, EventBus, communication_manager
from .vehicle_agent import VehicleAgent, VehicleBehavior, VehicleState, FuzzyLogicController
from .simulation_environment import SimulationEnvironment, create_simulation_environment, get_simulation_environment

__version__ = "1.0.0"
__author__ = "Sistema Multi-Agente CVRP"

__all__ = [
    # Clases base
    "BaseAgent",
    "Message", 
    "MessageType",
    "AgentState",
    
    # Sistema de comunicación
    "CommunicationManager",
    "EventBus", 
    "communication_manager",
    
    # Agente vehículo
    "VehicleAgent",
    "VehicleBehavior",
    "VehicleState", 
    "FuzzyLogicController",
    
    # Entorno de simulación
    "SimulationEnvironment",
    "create_simulation_environment",
    "get_simulation_environment"
]
