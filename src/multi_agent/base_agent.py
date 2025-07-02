"""
Sistema Multi-Agente Base para Simulación de Tránsito
Implementa la arquitectura fundamental para agentes autónomos con lógica difusa
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
import logging

class AgentState(Enum):
    """Estados posibles de un agente"""
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    SHUTDOWN = "shutdown"

class MessageType(Enum):
    """Tipos de mensajes entre agentes"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    BROADCAST = "broadcast"
    EMERGENCY = "emergency"

class Message:
    """Estructura de mensaje entre agentes"""
    def __init__(self, 
                 sender_id: str, 
                 receiver_id: str, 
                 message_type: MessageType,
                 content: Dict[str, Any],
                 priority: int = 1):
        self.id = str(uuid.uuid4())
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.message_type = message_type
        self.content = content
        self.priority = priority  # 1=normal, 2=high, 3=emergency
        self.timestamp = datetime.now()
        self.processed = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "message_type": self.message_type.value,
            "content": self.content,
            "priority": self.priority,
            "timestamp": self.timestamp.isoformat(),
            "processed": self.processed
        }

class BaseAgent(ABC):
    """
    Clase base abstracta para todos los agentes del sistema.
    Implementa funcionalidades comunes como comunicación, estado y ciclo de vida.
    """
    
    def __init__(self, agent_id: str, agent_type: str, initial_position: Tuple[float, float] = None):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.state = AgentState.IDLE
        self.position = initial_position or (0.0, 0.0)
        self.last_update = datetime.now()
        
        # Sistema de mensajes
        self.inbox = asyncio.Queue()
        self.outbox = asyncio.Queue()
        
        # Memoria y conocimiento del agente
        self.memory = {}
        self.knowledge_base = {}
        
        # Configuración de logging
        self.logger = logging.getLogger(f"Agent-{agent_id}")
        
        # Métricas del agente
        self.metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "decisions_made": 0,
            "errors_count": 0,
            "uptime_start": datetime.now()
        }
        
        # Flag para control del ciclo de vida
        self._running = False
        self._tasks = []

    @abstractmethod
    async def perceive(self, environment_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Percibe el estado del entorno y actualiza el conocimiento del agente.
        Debe ser implementado por cada tipo de agente específico.
        """
        pass

    @abstractmethod
    async def decide(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """
        Toma decisiones basadas en la percepción del entorno.
        Aquí se implementará la lógica difusa específica de cada agente.
        """
        pass

    @abstractmethod
    async def act(self, decision: Dict[str, Any]) -> bool:
        """
        Ejecuta las acciones determinadas por el proceso de decisión.
        Retorna True si la acción fue exitosa.
        """
        pass

    async def send_message(self, receiver_id: str, message_type, 
                          content: Dict[str, Any], priority: int = 1):
        """Envía un mensaje a otro agente"""
        # Convertir string a MessageType si es necesario
        if isinstance(message_type, str):
            try:
                message_type = MessageType(message_type.lower())
            except ValueError:
                message_type = MessageType.NOTIFICATION
        
        message = Message(self.agent_id, receiver_id, message_type, content, priority)
        await self.outbox.put(message)
        self.metrics["messages_sent"] += 1
        self.logger.debug(f"Mensaje enviado a {receiver_id}: {message_type.value}")

    async def receive_message(self) -> Optional[Message]:
        """Recibe un mensaje de la bandeja de entrada"""
        try:
            message = await asyncio.wait_for(self.inbox.get(), timeout=0.1)
            self.metrics["messages_received"] += 1
            message.processed = True
            return message
        except asyncio.TimeoutError:
            return None

    async def process_messages(self):
        """Procesa todos los mensajes pendientes en la bandeja de entrada"""
        while not self.inbox.empty():
            message = await self.receive_message()
            if message:
                await self.handle_message(message)

    async def handle_message(self, message: Message):
        """
        Maneja un mensaje recibido. Puede ser sobrescrito por agentes específicos.
        """
        self.logger.info(f"Mensaje recibido de {message.sender_id}: {message.message_type.value}")
        
        # Lógica básica de manejo de mensajes
        if message.message_type == MessageType.EMERGENCY:
            await self.handle_emergency(message)
        elif message.message_type == MessageType.REQUEST:
            await self.handle_request(message)
        elif message.message_type == MessageType.NOTIFICATION:
            await self.handle_notification(message)

    async def handle_emergency(self, message: Message):
        """Maneja mensajes de emergencia con alta prioridad"""
        self.logger.warning(f"Emergencia recibida: {message.content}")
        # Los agentes específicos pueden sobrescribir este método

    async def handle_request(self, message: Message):
        """Maneja solicitudes de otros agentes"""
        self.logger.info(f"Solicitud recibida: {message.content}")
        # Los agentes específicos pueden sobrescribir este método

    async def handle_notification(self, message: Message):
        """Maneja notificaciones de otros agentes"""
        self.logger.debug(f"Notificación recibida: {message.content}")
        # Los agentes específicos pueden sobrescribir este método

    def update_position(self, new_position: Tuple[float, float]):
        """Actualiza la posición del agente"""
        self.position = new_position
        self.last_update = datetime.now()

    def get_distance_to(self, other_position: Tuple[float, float]) -> float:
        """Calcula la distancia euclidiana a otra posición"""
        return ((self.position[0] - other_position[0])**2 + 
                (self.position[1] - other_position[1])**2)**0.5

    def update_knowledge(self, key: str, value: Any):
        """Actualiza la base de conocimiento del agente"""
        self.knowledge_base[key] = {
            "value": value,
            "timestamp": datetime.now(),
            "source": "internal"
        }

    def get_knowledge(self, key: str) -> Any:
        """Obtiene información de la base de conocimiento"""
        return self.knowledge_base.get(key, {}).get("value")

    async def start(self):
        """Inicia el ciclo de vida del agente"""
        self.state = AgentState.ACTIVE
        self._running = True
        self.logger.info(f"Agente {self.agent_id} iniciado")
        
        # Crear tarea principal del agente
        main_task = asyncio.create_task(self._main_loop())
        self._tasks.append(main_task)
        
        return main_task

    async def stop(self):
        """Detiene el agente de forma segura"""
        self.state = AgentState.SHUTDOWN
        self._running = False
        
        # Cancelar todas las tareas
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # Esperar a que terminen las tareas
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self.logger.info(f"Agente {self.agent_id} detenido")

    async def _main_loop(self):
        """Ciclo principal del agente"""
        while self._running:
            try:
                # Procesar mensajes
                await self.process_messages()
                
                # Simular percepción, decisión y acción
                # Esto será sobrescrito por agentes específicos
                await asyncio.sleep(0.1)  # Evitar uso excesivo de CPU
                
            except Exception as e:
                self.metrics["errors_count"] += 1
                self.logger.error(f"Error en ciclo principal: {e}")
                await asyncio.sleep(1)  # Pausa antes de continuar

    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas del agente"""
        uptime = datetime.now() - self.metrics["uptime_start"]
        return {
            **self.metrics,
            "uptime_seconds": uptime.total_seconds(),
            "state": self.state.value,
            "position": self.position,
            "last_update": self.last_update.isoformat()
        }

    def __repr__(self):
        return f"BaseAgent(id={self.agent_id}, type={self.agent_type}, state={self.state.value})"
