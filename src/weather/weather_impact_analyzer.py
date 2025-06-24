"""
Integrador de Clima para Logística Urbana
Combina el grafo de conocimiento y la cadena de Markov para 
proporcionar análisis completo del impacto climático en las rutas
"""

import sys
import os
from typing import Dict, Any, Tuple, Optional, List
import asyncio
import requests
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from crawler.weather_crawler import OpenMeteoCrawler

# Añadir rutas al path
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)

sys.path.insert(0, os.path.join(parent_dir, 'knowledge_graph'))
sys.path.insert(0, current_dir)

try:
    from weather_knowledge_graph import WeatherKnowledgeGraph
    from weather_markov_chain import WeatherMarkovChain
except ImportError as e:
    print(f"Error importando módulos locales: {e}")
    # Intentar importación relativa
    try:
        from .weather_knowledge_graph import WeatherKnowledgeGraph
        from .weather_markov_chain import WeatherMarkovChain
    except ImportError:
        # Fallback: importar desde rutas absolutas
        sys.path.append(os.path.join(project_root, 'src', 'knowledge_graph'))
        sys.path.append(os.path.join(project_root, 'src', 'weather'))
        from weather_knowledge_graph import WeatherKnowledgeGraph
        from weather_markov_chain import WeatherMarkovChain


class WeatherImpactAnalyzer:
    """
    Analizador integrado que combina grafo de conocimiento y cadena de Markov
    para evaluar el impacto del clima en rutas de entrega
    """
    
    def __init__(self, cache_dir: str = "cache"):
        self.knowledge_graph = WeatherKnowledgeGraph()
        self.markov_chain = WeatherMarkovChain(cache_dir)
        self.cache_dir = cache_dir
        
        # Coordenadas de La Habana
        self.latitude = 23.1136
        self.longitude = -82.3666
        
        # Inicializar el modelo de Markov
        self._initialize_markov_model()
    
    def _initialize_markov_model(self):
        """Inicializa el modelo de Markov, entrenándolo si es necesario"""
        print("Inicializando modelo de Markov...")
        
        if not self.markov_chain.load_model():
            print("Modelo no encontrado. Entrenando nuevo modelo...")
            try:
                self.markov_chain.train_markov_model()
                print("Modelo entrenado exitosamente")
            except Exception as e:
                print(f"Error entrenando modelo: {e}")
                print("Continuando con solo el grafo de conocimiento...")
    
    def calculate_weather_impact_factor(self, weather_data: Dict[str, Any] = None) -> Tuple[float, Dict[str, Any]]:
        """
        Calcula el factor de impacto del clima combinando ambos enfoques
        
        Args:
            weather_data: Datos del clima (si no se proporcionan, se obtienen de la API)
            
        Returns:
            Tupla con (factor_de_impacto, información_detallada)
        """
        # Obtener datos del clima si no se proporcionan
        if weather_data is None:
            OpenMeteoAPI = OpenMeteoCrawler(self.latitude, self.longitude, 3, 1)
            weather_data = OpenMeteoAPI.get_current_weather_sync()
            if weather_data is None:
                # Usar datos por defecto si no se puede obtener clima actual
                weather_data = {
                    'temperature_2m': 25.0,
                    'precipitation': 0.0,
                    'wind_speed_10m': 10.0,
                    'cloud_cover': 50.0,
                    'weather_code': 0,
                    'visibility': 10000.0
                }
                print("Usando datos climáticos por defecto")
        
        # Análisis con grafo de conocimiento
        kg_impact = self.knowledge_graph.query_weather_impact(weather_data)
        kg_factor = self.knowledge_graph.get_route_weight_multiplier(weather_data)
        
        # Análisis con cadena de Markov
        markov_factor = 1.0
        markov_info = {"error": "Modelo no disponible"}
        
        try:
            if self.markov_chain.states:  # Verificar que el modelo esté entrenado
                markov_factor = self.markov_chain.get_weather_impact_factor(weather_data)
                markov_info = {"factor": markov_factor, "model_available": True}
            else:
                markov_info = {"error": "Modelo de Markov no entrenado"}
        except Exception as e:
            markov_info = {"error": f"Error en modelo de Markov: {e}"}
        
        # Combinar factores (ponderación: 60% grafo de conocimiento, 40% Markov)
        if markov_factor > 1.0:
            combined_factor = 0.6 * kg_factor + 0.4 * markov_factor
        else:
            combined_factor = kg_factor  # Solo usar grafo de conocimiento si Markov no está disponible
        
        # Información detallada
        detailed_info = {
            "timestamp": datetime.now().isoformat(),
            "weather_data": weather_data,
            "knowledge_graph": {
                "impact": kg_impact,
                "factor": kg_factor
            },
            "markov_chain": markov_info,
            "combined_factor": combined_factor,
            "interpretation": self._interpret_impact_factor(combined_factor)
        }
        
        return combined_factor, detailed_info
    
    def _interpret_impact_factor(self, factor: float) -> str:
        """Interpreta el factor de impacto en términos comprensibles"""
        if factor <= 1.1:
            return "Condiciones ideales - Sin impacto significativo en entregas"
        elif factor <= 1.3:
            return "Condiciones buenas - Impacto mínimo en tiempos de entrega"
        elif factor <= 1.6:
            return "Condiciones moderadas - Posibles retrasos menores"
        elif factor <= 2.0:
            return "Condiciones adversas - Retrasos esperados"
        else:
            return "Condiciones severas - Retrasos significativos o suspensión recomendada"
    
    def get_hourly_forecast_impact(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Obtiene el pronóstico de impacto climático para las próximas horas
        
        Args:
            hours: Número de horas a pronosticar (máximo 168 = 7 días)
            
        Returns:
            Lista con información de impacto por hora
        """
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "hourly": [
                    "temperature_2m",
                    "precipitation",
                    "wind_speed_10m",
                    "cloud_cover",
                    "weather_code",
                    "visibility"
                ],
                "forecast_days": min(7, (hours // 24) + 1),
                "timezone": "America/Havana"
            }
            
            response = requests.get(url, params=params, timeout=15)
            if response.status_code != 200:
                return []
            
            data = response.json()
            hourly_data = data.get('hourly', {})
            
            forecast_impacts = []
            times = hourly_data.get('time', [])
            
            for i in range(min(hours, len(times))):
                hour_data = {
                    'temperature_2m': hourly_data.get('temperature_2m', [])[i] if i < len(hourly_data.get('temperature_2m', [])) else 25,
                    'precipitation': hourly_data.get('precipitation', [])[i] if i < len(hourly_data.get('precipitation', [])) else 0,
                    'wind_speed_10m': hourly_data.get('wind_speed_10m', [])[i] if i < len(hourly_data.get('wind_speed_10m', [])) else 10,
                    'cloud_cover': hourly_data.get('cloud_cover', [])[i] if i < len(hourly_data.get('cloud_cover', [])) else 50,
                    'weather_code': hourly_data.get('weather_code', [])[i] if i < len(hourly_data.get('weather_code', [])) else 0,
                    'visibility': hourly_data.get('visibility', [])[i] if i < len(hourly_data.get('visibility', [])) else 10000
                }
                
                factor, info = self.calculate_weather_impact_factor(hour_data)
                
                forecast_impacts.append({
                    'time': times[i],
                    'impact_factor': factor,
                    'interpretation': info['interpretation'],
                    'weather_summary': self._summarize_weather(hour_data)
                })
            
            return forecast_impacts
            
        except Exception as e:
            print(f"Error obteniendo pronóstico: {e}")
            return []
    
    def _summarize_weather(self, weather_data: Dict[str, Any]) -> str:
        """Genera un resumen textual del clima"""
        temp = weather_data.get('temperature_2m', 25)
        precip = weather_data.get('precipitation', 0)
        wind = weather_data.get('wind_speed_10m', 10)
        clouds = weather_data.get('cloud_cover', 50)
        
        summary_parts = []
        
        # Temperatura
        if temp < 15:
            summary_parts.append("frío")
        elif temp > 30:
            summary_parts.append("caluroso")
        else:
            summary_parts.append("templado")
        
        # Precipitación
        if precip > 10:
            summary_parts.append("lluvia intensa")
        elif precip > 2:
            summary_parts.append("lluvia moderada")
        elif precip > 0:
            summary_parts.append("lluvia ligera")
        
        # Nubosidad
        if clouds > 75:
            summary_parts.append("muy nuboso")
        elif clouds > 25:
            summary_parts.append("parcialmente nuboso")
        else:
            summary_parts.append("despejado")
        
        # Viento
        if wind > 40:
            summary_parts.append("viento fuerte")
        elif wind > 25:
            summary_parts.append("viento moderado")
        
        return f"{temp:.1f}°C, {', '.join(summary_parts)}"
    
    def export_analysis_report(self, filepath: str):
        """Exporta un reporte completo del análisis climático"""
        try:
            factor, info = self.calculate_weather_impact_factor()
            forecast = self.get_hourly_forecast_impact(48)  # 48 horas
            
            report = {
                "generated_at": datetime.now().isoformat(),
                "location": {
                    "city": "La Habana, Cuba",
                    "latitude": self.latitude,
                    "longitude": self.longitude
                },
                "current_analysis": info,
                "forecast_48h": forecast,
                "model_statistics": self.markov_chain.get_model_statistics()
            }
            
            import json
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            print(f"Reporte exportado a: {filepath}")
            
        except Exception as e:
            print(f"Error exportando reporte: {e}")
    
    def get_differentiated_weather_factors(self, weather_data: Dict[str, Any] = None) -> Dict[str, float]:
        """
        Obtiene factores de impacto climático diferenciados por tipo de carretera
        
        Returns:
            Dict con factores específicos para diferentes tipos de infraestructura
        """
        # Obtener datos del clima si no se proporcionan
        if weather_data is None:
            OpenMeteoAPI = OpenMeteoCrawler(self.latitude, self.longitude, 3, 1)
            weather_data = OpenMeteoAPI.get_current_weather_sync()
            if weather_data is None:
                return {
                    'motorway': 1.0,
                    'primary': 1.0,
                    'secondary': 1.0,
                    'residential': 1.0,
                    'unpaved': 1.0
                }
        
        precipitation = weather_data.get('precipitation', 0)
        wind_speed = weather_data.get('wind_speed_10m', 0)
        visibility = weather_data.get('visibility', 10000)
        temperature = weather_data.get('temperature_2m', 25)
        cloud_cover = weather_data.get('cloud_cover', 0)
        
        # Factores base por condiciones específicas
        factors = {
            'motorway': 1.0,      # Autopistas base
            'primary': 1.0,       # Carreteras principales base
            'secondary': 1.0,     # Carreteras secundarias base
            'residential': 1.0,   # Calles residenciales base
            'unpaved': 1.0        # Caminos sin pavimentar base
        }
        
        # Ajustes por precipitación (afecta más a caminos sin pavimentar)
        if precipitation > 0:
            rain_intensity = min(precipitation / 20.0, 1.0)  # Normalizar
            factors['motorway'] += rain_intensity * 0.2      # +20% máximo
            factors['primary'] += rain_intensity * 0.3       # +30% máximo
            factors['secondary'] += rain_intensity * 0.5     # +50% máximo
            factors['residential'] += rain_intensity * 0.7   # +70% máximo
            factors['unpaved'] += rain_intensity * 1.2       # +120% máximo
        
        # Ajustes por viento (afecta más a carreteras expuestas)
        if wind_speed > 20:  # Viento moderado a fuerte
            wind_intensity = min((wind_speed - 20) / 30.0, 1.0)  # Normalizar
            factors['motorway'] += wind_intensity * 0.4      # Más expuestas
            factors['primary'] += wind_intensity * 0.3
            factors['secondary'] += wind_intensity * 0.2
            factors['residential'] += wind_intensity * 0.1   # Más protegidas
            factors['unpaved'] += wind_intensity * 0.6       # Muy afectadas
        
        # Ajustes por visibilidad (niebla, etc.)
        if visibility < 5000:  # Visibilidad reducida
            visibility_factor = 1.0 - (visibility / 5000.0)
            factors['motorway'] += visibility_factor * 0.8    # Velocidades altas = más peligroso
            factors['primary'] += visibility_factor * 0.6
            factors['secondary'] += visibility_factor * 0.4
            factors['residential'] += visibility_factor * 0.3  # Velocidades bajas
            factors['unpaved'] += visibility_factor * 0.5
        
        # Ajustes por temperatura extrema
        if temperature < 5 or temperature > 40:
            temp_stress = 0.1 if abs(temperature - 22.5) < 17.5 else 0.2
            for road_type in factors:
                factors[road_type] += temp_stress
        
        # Ajustes por nubosidad (puede indicar tormentas próximas)
        if cloud_cover > 80:
            storm_risk = 0.1
            for road_type in factors:
                factors[road_type] += storm_risk
        
        return factors


# Función de conveniencia para usar en otros módulos
def get_weather_impact_for_routes() -> float:
    """
    Función simple para obtener el factor de impacto climático actual
    Para usar en el módulo de optimización de rutas
    """
    try:
        analyzer = WeatherImpactAnalyzer()
        factor, _ = analyzer.calculate_weather_impact_factor()
        return factor
    except Exception as e:
        print(f"Error obteniendo factor climático: {e}")
        return 1.0  # Factor neutral si hay error

def get_differentiated_weather_factors() -> Dict[str, float]:
    """
    Función para obtener factores climáticos diferenciados por tipo de carretera
    Para usar en el módulo de optimización de rutas
    """
    try:
        analyzer = WeatherImpactAnalyzer()
        factors = analyzer.get_differentiated_weather_factors()
        return factors
    except Exception as e:
        print(f"Error obteniendo factores climáticos diferenciados: {e}")
        return {
            'motorway': 1.0,
            'primary': 1.0,
            'secondary': 1.0,
            'residential': 1.0,
            'unpaved': 1.0
        }


if __name__ == "__main__":
    # Ejemplo de uso
    analyzer = WeatherImpactAnalyzer()
    
    # Análisis actual
    factor, info = analyzer.calculate_weather_impact_factor()
    print(f"Factor de impacto actual: {factor:.2f}")
    print(f"Interpretación: {info['interpretation']}")
    
    # Pronóstico para las próximas 12 horas
    forecast = analyzer.get_hourly_forecast_impact(12)
    print(f"\nPronóstico de impacto (próximas 12 horas):")
    for hour_info in forecast[:6]:  # Mostrar solo las primeras 6 horas
        print(f"  {hour_info['time']}: Factor {hour_info['impact_factor']:.2f} - {hour_info['weather_summary']}")
    
    # Exportar reporte completo
    analyzer.export_analysis_report("weather_impact_report.json")
