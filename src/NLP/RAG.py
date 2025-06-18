from dotenv import load_dotenv
import os
import json
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Añadir rutas necesarias
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.append(str(project_root))

from src.NLP.Gemini import Gemini

load_dotenv()

class VRPKnowledgeRAG:
    """
    Sistema RAG especializado en problemas de ruteo de vehículos (VRP)
    con información contextual del clima, rutas optimizadas y análisis de rendimiento
    """
    
    def __init__(self):
        self.gemini = Gemini()
        self.knowledge_base = {
            "weather_data": {},
            "route_statistics": {},
            "traffic_events": [],
            "optimization_history": [],
            "system_performance": {},
            "crawler_data": {},
            "markov_insights": {},
            "knowledge_graph_rules": {}
        }
        
        # Contexto especializado para VRP
        self.vrp_context = {
            "location": "La Habana, Cuba",
            "coordinates": {"lat": 23.1136, "lon": -82.3666},
            "optimization_methods": ["Genetic Algorithm", "Tabu Search", "VNS", "Simulated Annealing"],
            "weather_factors": ["precipitation", "wind_speed", "visibility", "temperature"],
            "road_types": ["motorway", "primary", "secondary", "residential", "unpaved"]
        }
    
    def update_knowledge_base(self, data_source: str, data: Dict[str, Any]):
        """
        Actualiza la base de conocimientos con nueva información
        
        Args:
            data_source: Tipo de datos ("weather", "routes", "traffic", etc.)
            data: Información a agregar
        """
        timestamp = datetime.now().isoformat()
        
        if data_source == "weather":
            self.knowledge_base["weather_data"] = {
                **data,
                "timestamp": timestamp,
                "impact_analysis": self._analyze_weather_impact(data)
            }
        
        elif data_source == "routes":
            self.knowledge_base["route_statistics"] = {
                **data,
                "timestamp": timestamp,
                "efficiency_metrics": self._calculate_route_efficiency(data)
            }
        
        elif data_source == "traffic_events":
            self.knowledge_base["traffic_events"].append({
                **data,
                "timestamp": timestamp
            })
            # Mantener solo los últimos 50 eventos
            self.knowledge_base["traffic_events"] = self.knowledge_base["traffic_events"][-50:]
        
        elif data_source == "optimization":
            self.knowledge_base["optimization_history"].append({
                **data,
                "timestamp": timestamp
            })
            # Mantener solo las últimas 20 optimizaciones
            self.knowledge_base["optimization_history"] = self.knowledge_base["optimization_history"][-20:]
        
        elif data_source == "performance":
            self.knowledge_base["system_performance"] = {
                **data,
                "timestamp": timestamp
            }
        
        elif data_source == "crawler":
            self.knowledge_base["crawler_data"] = {
                **data,
                "timestamp": timestamp
            }
    
    def generate_context_prompt(self, user_question: str) -> str:
        """
        Genera un prompt contextualizado con toda la información relevante
        """
        # Información del sistema actual
        current_weather = self.knowledge_base.get("weather_data", {})
        current_routes = self.knowledge_base.get("route_statistics", {})
        recent_events = self.knowledge_base.get("traffic_events", [])[-5:]  # Últimos 5 eventos
        optimization_stats = self._get_optimization_summary()
        
        context_prompt = f"""
Eres un asistente especializado en sistemas de ruteo de vehículos (VRP) para logística urbana en La Habana, Cuba.

INFORMACIÓN CONTEXTUAL ACTUAL:

🌍 UBICACIÓN Y CONFIGURACIÓN:
- Ciudad: {self.vrp_context['location']}
- Coordenadas: {self.vrp_context['coordinates']}
- Métodos de optimización disponibles: {', '.join(self.vrp_context['optimization_methods'])}

🌤️ INFORMACIÓN CLIMÁTICA ACTUAL:
{self._format_weather_context(current_weather)}

📊 ESTADÍSTICAS DE RUTAS ACTUALES:
{self._format_route_context(current_routes)}

🚦 EVENTOS DE TRÁFICO RECIENTES:
{self._format_traffic_context(recent_events)}

📈 HISTORIAL DE OPTIMIZACIÓN:
{optimization_stats}

🔍 DATOS DEL CRAWLER:
{self._format_crawler_context()}

🧠 ANÁLISIS PREDICTIVO:
{self._format_markov_context()}

PREGUNTA DEL USUARIO:
{user_question}

INSTRUCCIONES:
1. Analiza la pregunta en el contexto de nuestro sistema VRP en La Habana
2. Utiliza toda la información contextual disponible para dar una respuesta precisa
3. Si es relevante, menciona el impacto del clima actual en las rutas
4. Proporciona recomendaciones específicas basadas en los datos
5. Si falta información, menciona qué datos adicionales serían útiles
6. Mantén un tono profesional pero accesible
7. Incluye métricas específicas cuando sea apropiado

Responde de manera estructurada y completa:
"""
        
        return context_prompt
    
    def ask_with_context(self, user_question: str) -> Dict[str, Any]:
        """
        Procesa una pregunta del usuario con todo el contexto disponible
        
        Args:
            user_question: Pregunta del usuario
            
        Returns:
            Respuesta estructurada con análisis y recomendaciones
        """
        try:
            # Generar prompt contextualizado
            context_prompt = self.generate_context_prompt(user_question)
            
            # Obtener respuesta de Gemini
            response = self.gemini.ask(context_prompt)
            
            # Analizar el tipo de pregunta para métricas
            question_category = self._categorize_question(user_question)
            
            # Generar métricas relevantes
            relevant_metrics = self._generate_relevant_metrics(question_category)
            
            return {
                "success": True,
                "response": response,
                "question_category": question_category,
                "relevant_metrics": relevant_metrics,
                "context_used": {
                    "weather_available": bool(self.knowledge_base.get("weather_data")),
                    "routes_available": bool(self.knowledge_base.get("route_statistics")),
                    "traffic_events_count": len(self.knowledge_base.get("traffic_events", [])),
                    "optimization_history_count": len(self.knowledge_base.get("optimization_history", []))
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Error procesando la consulta. Por favor, intenta reformular tu pregunta."
            }
    
    def _analyze_weather_impact(self, weather_data: Dict) -> Dict:
        """Analiza el impacto del clima en las rutas"""
        impact_factor = weather_data.get('impact_factor', 1.0)
        
        if impact_factor <= 1.1:
            impact_level = "Mínimo"
            recommendation = "Condiciones ideales para entregas"
        elif impact_factor <= 1.3:
            impact_level = "Bajo"
            recommendation = "Ligero aumento en tiempos de entrega"
        elif impact_factor <= 1.6:
            impact_level = "Moderado"
            recommendation = "Considerar rutas alternativas"
        elif impact_factor <= 2.0:
            impact_level = "Alto"
            recommendation = "Retrasos esperados, ajustar horarios"
        else:
            impact_level = "Severo"
            recommendation = "Considerar postponer entregas no urgentes"
        
        return {
            "impact_level": impact_level,
            "recommendation": recommendation,
            "factor": impact_factor
        }
    
    def _calculate_route_efficiency(self, route_data: Dict) -> Dict:
        """Calcula métricas de eficiencia de rutas"""
        routes = route_data.get('routes', [])
        
        if not routes:
            return {"efficiency": 0, "metrics": {}}
        
        total_distance = sum(route.get('distance', 0) for route in routes)
        total_points = sum(len(route.get('path', [])) for route in routes)
        avg_distance = total_distance / len(routes) if routes else 0
        
        return {
            "total_distance": round(total_distance, 2),
            "average_distance_per_route": round(avg_distance, 2),
            "total_delivery_points": total_points,
            "routes_count": len(routes),
            "efficiency_score": round((total_points / total_distance * 100) if total_distance > 0 else 0, 2)
        }
    
    def _get_optimization_summary(self) -> str:
        """Genera resumen del historial de optimización"""
        history = self.knowledge_base.get("optimization_history", [])
        
        if not history:
            return "No hay historial de optimización disponible"
        
        recent_optimization = history[-1] if history else {}
        avg_time = np.mean([opt.get('computation_time', 0) for opt in history[-5:]])
        
        return f"""
- Última optimización: {recent_optimization.get('timestamp', 'N/A')}
- Método utilizado: {recent_optimization.get('method', 'N/A')}
- Tiempo promedio de cálculo: {avg_time:.2f}s
- Optimizaciones realizadas: {len(history)}
"""
    
    def _format_weather_context(self, weather_data: Dict) -> str:
        """Formatea el contexto climático"""
        if not weather_data:
            return "No hay información climática disponible"
        
        impact_factor = weather_data.get('impact_factor', 1.0)
        interpretation = weather_data.get('interpretation', 'Sin análisis')
        weather_summary = weather_data.get('weather_summary', {})
        
        temp = weather_summary.get('temperature_2m', 'N/A')
        precip = weather_summary.get('precipitation', 'N/A')
        wind = weather_summary.get('wind_speed_10m', 'N/A')
        
        return f"""
- Factor de impacto: {impact_factor:.2f}x
- Interpretación: {interpretation}
- Temperatura: {temp}°C
- Precipitación: {precip}mm
- Viento: {wind}km/h
"""
    
    def _format_route_context(self, route_data: Dict) -> str:
        """Formatea el contexto de rutas"""
        if not route_data:
            return "No hay rutas optimizadas disponibles"
        
        efficiency = route_data.get('efficiency_metrics', {})
        routes = route_data.get('routes', [])
        
        return f"""
- Número de rutas: {len(routes)}
- Distancia total: {efficiency.get('total_distance', 0):.2f} km
- Distancia promedio por ruta: {efficiency.get('average_distance_per_route', 0):.2f} km
- Puntos de entrega totales: {efficiency.get('total_delivery_points', 0)}
- Puntuación de eficiencia: {efficiency.get('efficiency_score', 0):.2f}/100
"""
    
    def _format_traffic_context(self, traffic_events: List) -> str:
        """Formatea el contexto de eventos de tráfico"""
        if not traffic_events:
            return "No hay eventos de tráfico recientes"
        
        events_summary = []
        for event in traffic_events[-3:]:  # Últimos 3 eventos
            events_summary.append(f"- {event.get('type', 'Evento')}: {event.get('description', 'Sin descripción')}")
        
        return "\n".join(events_summary)
    
    def _format_crawler_context(self) -> str:
        """Formatea el contexto de datos del crawler"""
        crawler_data = self.knowledge_base.get("crawler_data", {})
        
        if not crawler_data:
            return "No hay datos del crawler disponibles"
        
        return f"""
- Última actualización: {crawler_data.get('timestamp', 'N/A')}
- Fuentes consultadas: {len(crawler_data.get('sources', []))}
- Eventos relevantes encontrados: {crawler_data.get('relevant_events_count', 0)}
"""
    
    def _format_markov_context(self) -> str:
        """Formatea el contexto del análisis de Markov"""
        markov_data = self.knowledge_base.get("markov_insights", {})
        
        if not markov_data:
            return "Análisis predictivo no disponible"
        
        return f"""
- Predicción climática próximas 6h: {markov_data.get('weather_trend', 'Estable')}
- Probabilidad de condiciones adversas: {markov_data.get('adverse_probability', 0)*100:.1f}%
- Recomendación temporal: {markov_data.get('timing_recommendation', 'Sin recomendación')}
"""
    
    def _categorize_question(self, question: str) -> str:
        """Categoriza el tipo de pregunta del usuario"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['clima', 'tiempo', 'lluvia', 'viento', 'temperatura']):
            return "weather"
        elif any(word in question_lower for word in ['ruta', 'optimización', 'camión', 'entrega', 'distancia']):
            return "routing"
        elif any(word in question_lower for word in ['tráfico', 'congestion', 'eventos', 'incidentes']):
            return "traffic"
        elif any(word in question_lower for word in ['rendimiento', 'estadísticas', 'métricas', 'eficiencia']):
            return "performance"
        elif any(word in question_lower for word in ['predicción', 'futuro', 'tendencia', 'pronóstico']):
            return "prediction"
        else:
            return "general"
    
    def _generate_relevant_metrics(self, category: str) -> Dict:
        """Genera métricas relevantes según la categoría de pregunta"""
        current_weather = self.knowledge_base.get("weather_data", {})
        current_routes = self.knowledge_base.get("route_statistics", {})
        
        base_metrics = {
            "system_status": "Operativo",
            "last_update": datetime.now().strftime("%H:%M:%S")
        }
        
        if category == "weather":
            base_metrics.update({
                "weather_impact_factor": current_weather.get('impact_factor', 1.0),
                "current_conditions": current_weather.get('weather_summary', {})
            })
        
        elif category == "routing":
            efficiency = current_routes.get('efficiency_metrics', {})
            base_metrics.update({
                "active_routes": efficiency.get('routes_count', 0),
                "total_distance": efficiency.get('total_distance', 0),
                "efficiency_score": efficiency.get('efficiency_score', 0)
            })
        
        elif category == "performance":
            optimization_history = self.knowledge_base.get("optimization_history", [])
            base_metrics.update({
                "optimizations_completed": len(optimization_history),
                "avg_computation_time": np.mean([opt.get('computation_time', 0) 
                                               for opt in optimization_history[-5:]]) if optimization_history else 0
            })
        
        return base_metrics

# Función de conveniencia para usar en otros módulos
def create_vrp_rag_assistant() -> VRPKnowledgeRAG:
    """Crea una instancia del asistente RAG para VRP"""
    return VRPKnowledgeRAG()

if __name__ == "__main__":
    # Ejemplo de uso
    rag = VRPKnowledgeRAG()
    
    # Simular datos de prueba
    rag.update_knowledge_base("weather", {
        "impact_factor": 1.3,
        "interpretation": "Condiciones moderadas",
        "weather_summary": {
            "temperature_2m": 28,
            "precipitation": 2,
            "wind_speed_10m": 15
        }
    })
    
    rag.update_knowledge_base("routes", {
        "routes": [
            {"distance": 15.5, "path": [1, 2, 3, 4, 5]},
            {"distance": 12.3, "path": [1, 6, 7, 8]}
        ]
    })
    
    # Probar consulta
    response = rag.ask_with_context("¿Cómo está afectando el clima actual a mis rutas de entrega?")
    print(json.dumps(response, indent=2, ensure_ascii=False))