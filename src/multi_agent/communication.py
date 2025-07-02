"""
Motor de Comunicación Multi-Agente
Maneja la comunicación asíncrona y coordinación entre todos los agentes del sistema
"""

import asyncio
import logging
from typing import Dict, List, Set, Any, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
import json

from .base_agent import BaseAgent, Message, MessageType, AgentState

class EventBus:
    """
    Bus de eventos para comunicación publish-subscribe entre agentes
    """
    
    def __init__(self):
        self.subscribers = defaultdict(list)  # topic -> [agent_ids]
        self.logger = logging.getLogger("EventBus")
        self.message_history = deque(maxlen=1000)  # Historial de mensajes
        
    def subscribe(self, topic: str, agent_id: str):
        """Suscribe un agente a un topic específico"""
        if agent_id not in self.subscribers[topic]:
            self.subscribers[topic].append(agent_id)
            self.logger.debug(f"Agente {agent_id} suscrito a topic '{topic}'")
    
    def unsubscribe(self, topic: str, agent_id: str):
        """Desuscribe un agente de un topic"""
        if agent_id in self.subscribers[topic]:
            self.subscribers[topic].remove(agent_id)
            self.logger.debug(f"Agente {agent_id} desuscrito de topic '{topic}'")
    
    async def publish(self, topic: str, message: Message, sender_agent: BaseAgent):
        """Publica un mensaje a todos los suscriptores de un topic"""
        subscribers = self.subscribers.get(topic, [])
        self.logger.debug(f"Publicando mensaje en topic '{topic}' a {len(subscribers)} suscriptores")
        
        # Registrar en historial
        self.message_history.append({
            "timestamp": datetime.now(),
            "topic": topic,
            "sender": sender_agent.agent_id,
            "subscribers_count": len(subscribers),
            "message_type": message.message_type.value
        })
        
        # Enviar a suscriptores
        for subscriber_id in subscribers:
            if subscriber_id != sender_agent.agent_id:  # No enviarse a sí mismo
                await sender_agent.send_message(
                    subscriber_id, 
                    message.message_type, 
                    {**message.content, "topic": topic}
                )

class CommunicationManager:
    """
    Administrador central de comunicación entre agentes
    """
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.message_queue = asyncio.Queue()
        self.event_bus = EventBus()
        self.logger = logging.getLogger("CommunicationManager")
        
        # Estadísticas de comunicación
        self.stats = {
            "total_messages": 0,
            "messages_by_type": defaultdict(int),
            "agents_registered": 0,
            "failed_deliveries": 0
        }
        
        self._running = False
        self._message_processor_task = None

    async def register_agent(self, agent: BaseAgent):
        """Registra un agente en el sistema de comunicación"""
        self.agents[agent.agent_id] = agent
        self.stats["agents_registered"] += 1
        self.logger.info(f"Agente registrado: {agent.agent_id} ({agent.agent_type})")
        
        # Suscribir a topics por defecto según el tipo de agente
        await self._setup_default_subscriptions(agent)

    async def unregister_agent(self, agent_id: str):
        """Desregistra un agente del sistema"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            self.logger.info(f"Agente desregistrado: {agent_id}")

    async def _setup_default_subscriptions(self, agent: BaseAgent):
        """Configura suscripciones por defecto según el tipo de agente"""
        # Todos los agentes se suscriben a mensajes de emergencia
        self.event_bus.subscribe("emergency", agent.agent_id)
        
        # Suscripciones específicas por tipo de agente
        if agent.agent_type == "vehicle":
            self.event_bus.subscribe("traffic", agent.agent_id)
            self.event_bus.subscribe("weather", agent.agent_id)
            self.event_bus.subscribe("route", agent.agent_id)
        
        # Suscripciones específicas por tipo de agente
        if agent.agent_type == "vehicle":
            self.event_bus.subscribe("traffic", agent.agent_id)
            self.event_bus.subscribe("weather", agent.agent_id)
            self.event_bus.subscribe("route", agent.agent_id)
        elif agent.agent_type == "traffic_control":
            self.event_bus.subscribe("vehicle_updates", agent.agent_id)
            self.event_bus.subscribe("congestion", agent.agent_id)
        elif agent.agent_type == "weather":
            self.event_bus.subscribe("weather_requests", agent.agent_id)
        elif agent.agent_type == "route_optimizer":
            self.event_bus.subscribe("optimization_requests", agent.agent_id)
            self.event_bus.subscribe("vehicle_updates", agent.agent_id)

    async def start(self):
        """Inicia el procesador de mensajes"""
        self._running = True
        self._message_processor_task = asyncio.create_task(self._process_messages())
        self.logger.info("Motor de comunicación iniciado")

    async def stop(self):
        """Detiene el procesador de mensajes"""
        self._running = False
        if self._message_processor_task:
            self._message_processor_task.cancel()
            try:
                await self._message_processor_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Motor de comunicación detenido")

    async def _process_messages(self):
        """Procesa los mensajes en cola de forma asíncrona"""
        while self._running:
            try:
                # Recopilar mensajes de todos los agentes
                await self._collect_outgoing_messages()
                
                # Procesar mensajes en cola
                await self._deliver_messages()
                
                await asyncio.sleep(0.05)  # 50ms de intervalo
                
            except Exception as e:
                self.logger.error(f"Error procesando mensajes: {e}")
                await asyncio.sleep(1)

    async def _collect_outgoing_messages(self):
        """Recopila mensajes salientes de todos los agentes"""
        for agent in self.agents.values():
            while not agent.outbox.empty():
                try:
                    message = await asyncio.wait_for(agent.outbox.get(), timeout=0.01)
                    await self.message_queue.put((agent.agent_id, message))
                except asyncio.TimeoutError:
                    break

    async def _deliver_messages(self):
        """Entrega mensajes a sus destinatarios"""
        processed_count = 0
        
        while not self.message_queue.empty() and processed_count < 100:  # Límite por ciclo
            try:
                sender_id, message = await asyncio.wait_for(
                    self.message_queue.get(), timeout=0.01
                )
                
                await self._deliver_single_message(sender_id, message)
                processed_count += 1
                
            except asyncio.TimeoutError:
                break

    async def _deliver_single_message(self, sender_id: str, message: Message):
        """Entrega un mensaje individual"""
        self.stats["total_messages"] += 1
        self.stats["messages_by_type"][message.message_type.value] += 1
        
        # Mensaje broadcast
        if message.receiver_id == "ALL" or message.receiver_id == "*":
            await self._broadcast_message(sender_id, message)
            return
        
        # Mensaje directo
        target_agent = self.agents.get(message.receiver_id)
        if target_agent:
            await target_agent.inbox.put(message)
            self.logger.debug(f"Mensaje entregado: {sender_id} -> {message.receiver_id}")
        else:
            self.stats["failed_deliveries"] += 1
            self.logger.warning(f"Agente destinatario no encontrado: {message.receiver_id}")

    async def _broadcast_message(self, sender_id: str, message: Message):
        """Envía un mensaje a todos los agentes registrados"""
        sender_agent = self.agents.get(sender_id)
        if not sender_agent:
            return
            
        delivered_count = 0
        for agent_id, agent in self.agents.items():
            if agent_id != sender_id:  # No enviarse a sí mismo
                await agent.inbox.put(message)
                delivered_count += 1
        
        self.logger.debug(f"Mensaje broadcast entregado a {delivered_count} agentes")

    async def send_to_topic(self, topic: str, sender_id: str, message_type: MessageType, 
                           content: Dict[str, Any], priority: int = 1):
        """Envía un mensaje a todos los suscriptores de un topic"""
        sender_agent = self.agents.get(sender_id)
        if not sender_agent:
            self.logger.error(f"Agente emisor no encontrado: {sender_id}")
            return
        
        message = Message(sender_id, "TOPIC", message_type, content, priority)
        await self.event_bus.publish(topic, message, sender_agent)

    def get_communication_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas detalladas de comunicación"""
        return {
            "total_messages": self.stats["total_messages"],
            "messages_by_type": dict(self.stats["messages_by_type"]),
            "agents_registered": self.stats["agents_registered"],
            "failed_deliveries": self.stats["failed_deliveries"],
            "active_agents": len(self.agents),
            "queue_size": self.message_queue.qsize()
        }

    def get_agent_list(self) -> List[Dict[str, Any]]:
        """Retorna lista de agentes registrados con su información"""
        return [
            {
                "agent_id": agent.agent_id,
                "agent_type": agent.agent_type,
                "state": agent.state.value,
                "position": agent.position,
                "metrics": agent.get_metrics()
            }
            for agent in self.agents.values()
        ]

    async def emergency_broadcast(self, sender_id: str, emergency_type: str, 
                                 details: Dict[str, Any]):
        """Envía un mensaje de emergencia a todos los agentes"""
        await self.send_to_topic(
            "emergency", 
            sender_id, 
            MessageType.EMERGENCY,
            {
                "emergency_type": emergency_type,
                "details": details,
                "timestamp": datetime.now().isoformat()
            },
            priority=3
        )

    async def register_agent_id(self, agent_id: str, agent_type: str = "system"):
        """Registra un ID de agente sin objeto agente completo (para sistemas)"""
        # Crear un objeto mock simple para el entorno o sistemas especiales
        class MockAgent:
            def __init__(self, aid, atype):
                self.agent_id = aid
                self.agent_type = atype
                self.outbox = asyncio.Queue()
            
            async def send_message(self, *args, **kwargs):
                # Mock method - no hace nada para agentes del sistema
                pass
        
        mock_agent = MockAgent(agent_id, agent_type)
        self.agents[agent_id] = mock_agent
        self.stats["agents_registered"] += 1
        self.logger.info(f"Agente registrado: {agent_id} ({agent_type})")

# Instancia global del administrador de comunicación
communication_manager = CommunicationManager()
