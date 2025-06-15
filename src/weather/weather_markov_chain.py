"""
Cadena de Markov para modelar patrones climáticos y su impacto en la logística
Utiliza datos históricos de open-meteo.com para entrenar el modelo
"""

import numpy as np
import pandas as pd
import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import pickle
from dataclasses import dataclass
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import time


@dataclass
class WeatherState:
    """Estado del clima para la cadena de Markov"""
    precipitation_level: str  # "none", "light", "moderate", "heavy"
    temperature_range: str    # "cold", "mild", "warm", "hot"
    wind_level: str          # "calm", "light", "moderate", "strong"
    cloud_cover: str         # "clear", "partial", "overcast"
    
    def to_string(self) -> str:
        """Convierte el estado a string para usar como clave"""
        return f"{self.precipitation_level}_{self.temperature_range}_{self.wind_level}_{self.cloud_cover}"
    
    @classmethod
    def from_weather_data(cls, data: Dict) -> 'WeatherState':
        """Crea un estado del clima desde datos de API"""
        # Clasificar precipitación
        precip = data.get('precipitation', 0)
        if precip == 0:
            precipitation_level = "none"
        elif precip < 2:
            precipitation_level = "light"
        elif precip < 10:
            precipitation_level = "moderate"
        else:
            precipitation_level = "heavy"
        
        # Clasificar temperatura
        temp = data.get('temperature_2m', 20)
        if temp < 15:
            temperature_range = "cold"
        elif temp < 25:
            temperature_range = "mild"
        elif temp < 30:
            temperature_range = "warm"
        else:
            temperature_range = "hot"
        
        # Clasificar viento
        wind = data.get('wind_speed_10m', 0)
        if wind < 10:
            wind_level = "calm"
        elif wind < 25:
            wind_level = "light"
        elif wind < 40:
            wind_level = "moderate"
        else:
            wind_level = "strong"
        
        # Clasificar cobertura de nubes
        clouds = data.get('cloud_cover', 0)
        if clouds < 25:
            cloud_cover = "clear"
        elif clouds < 75:
            cloud_cover = "partial"
        else:
            cloud_cover = "overcast"
        
        return cls(precipitation_level, temperature_range, wind_level, cloud_cover)


class WeatherMarkovChain:
    """
    Cadena de Markov para modelar transiciones de estados climáticos
    y predecir impactos en rutas de entrega
    """
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        self.transition_matrix = {}
        self.state_frequencies = {}
        self.states = set()
        self.weather_data_cache = os.path.join(cache_dir, "weather_historical_data.json")
        self.model_cache = os.path.join(cache_dir, "markov_model.pkl")
        
        # Coordenadas de La Habana
        self.latitude = 23.1136
        self.longitude = -82.3666
        
        # Crear directorio de caché si no existe
        os.makedirs(cache_dir, exist_ok=True)
    
    async def fetch_historical_weather_data(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Obtiene datos históricos del clima desde open-meteo.com
        
        Args:
            start_date: Fecha inicio en formato "YYYY-MM-DD"
            end_date: Fecha fin en formato "YYYY-MM-DD"
        """
        base_url = "https://api.open-meteo.com/v1/forecast"
        
        # Parámetros para datos históricos
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": [
                "temperature_2m",
                "precipitation",
                "wind_speed_10m",
                "cloud_cover",
                "weather_code",
                "visibility"
            ],
            "timezone": "America/Havana"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._process_api_response(data)
                    else:
                        print(f"Error en API: {response.status}")
                        return []
        except Exception as e:
            print(f"Error obteniendo datos del clima: {e}")
            return []
    
    def fetch_historical_weather_sync(self, start_date: str, end_date: str) -> List[Dict]:
        """Versión síncrona de fetch_historical_weather_data"""
        base_url = "https://api.open-meteo.com/v1/forecast"
        
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": [
                "temperature_2m",
                "precipitation",
                "wind_speed_10m",
                "cloud_cover",
                "weather_code",
                "visibility"
            ],
            "timezone": "America/Havana"
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return self._process_api_response(data)
            else:
                print(f"Error en API: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error obteniendo datos del clima: {e}")
            return []
    
    def _process_api_response(self, data: Dict) -> List[Dict]:
        """Procesa la respuesta de la API y convierte a lista de registros por hora"""
        if 'hourly' not in data:
            return []
        
        hourly_data = data['hourly']
        processed_data = []
        
        # Obtener las listas de datos por hora
        times = hourly_data.get('time', [])
        temperatures = hourly_data.get('temperature_2m', [])
        precipitations = hourly_data.get('precipitation', [])
        wind_speeds = hourly_data.get('wind_speed_10m', [])
        cloud_covers = hourly_data.get('cloud_cover', [])
        weather_codes = hourly_data.get('weather_code', [])
        visibilities = hourly_data.get('visibility', [])
        
        # Combinar los datos por timestamp
        for i, time_str in enumerate(times):
            record = {
                'timestamp': time_str,
                'temperature_2m': temperatures[i] if i < len(temperatures) else None,
                'precipitation': precipitations[i] if i < len(precipitations) else 0,
                'wind_speed_10m': wind_speeds[i] if i < len(wind_speeds) else 0,
                'cloud_cover': cloud_covers[i] if i < len(cloud_covers) else 0,
                'weather_code': weather_codes[i] if i < len(weather_codes) else 0,
                'visibility': visibilities[i] if i < len(visibilities) else 10000
            }
            processed_data.append(record)
        
        return processed_data
    
    def collect_training_data(self, force_refresh: bool = False) -> List[Dict]:
        """
        Recopila datos de entrenamiento de los últimos 2 años
        """
        # Verificar si ya tenemos datos en caché
        if os.path.exists(self.weather_data_cache) and not force_refresh:
            print("Cargando datos del clima desde caché...")
            with open(self.weather_data_cache, 'r') as f:
                return json.load(f)
        
        print("Recopilando datos históricos del clima...")
        
        # Calcular fechas (últimos 2 años)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)  # 2 años
        
        all_data = []
        
        # Dividir en chunks de 3 meses para evitar límites de API
        current_date = start_date
        while current_date < end_date:
            chunk_end = min(current_date + timedelta(days=90), end_date)
            
            start_str = current_date.strftime("%Y-%m-%d")
            end_str = chunk_end.strftime("%Y-%m-%d")
            
            print(f"Obteniendo datos desde {start_str} hasta {end_str}...")
            
            chunk_data = self.fetch_historical_weather_sync(start_str, end_str)
            all_data.extend(chunk_data)
            
            current_date = chunk_end + timedelta(days=1)
            
            # Pausa para no sobrecargar la API
            time.sleep(1)
        
        # Guardar en caché
        with open(self.weather_data_cache, 'w') as f:
            json.dump(all_data, f, indent=2)
        
        print(f"Datos recopilados: {len(all_data)} registros")
        return all_data
    
    def train_markov_model(self, weather_data: List[Dict] = None):
        """
        Entrena la cadena de Markov con datos históricos del clima
        """
        if weather_data is None:
            weather_data = self.collect_training_data()
        
        if not weather_data:
            print("No hay datos para entrenar el modelo")
            return
        
        print(f"Entrenando modelo de Markov con {len(weather_data)} registros...")
        
        # Convertir datos a estados
        states_sequence = []
        for record in weather_data:
            if record.get('temperature_2m') is not None:
                state = WeatherState.from_weather_data(record)
                states_sequence.append(state.to_string())
        
        if len(states_sequence) < 2:
            print("Insuficientes datos para entrenar el modelo")
            return
        
        # Obtener todos los estados únicos
        self.states = set(states_sequence)
        
        # Inicializar matrices
        self.transition_matrix = {state: {} for state in self.states}
        self.state_frequencies = {state: 0 for state in self.states}
        
        # Contar transiciones
        for i in range(len(states_sequence) - 1):
            current_state = states_sequence[i]
            next_state = states_sequence[i + 1]
            
            self.state_frequencies[current_state] += 1
            
            if next_state not in self.transition_matrix[current_state]:
                self.transition_matrix[current_state][next_state] = 0
            self.transition_matrix[current_state][next_state] += 1
        
        # Convertir conteos a probabilidades
        for current_state in self.transition_matrix:
            total_transitions = sum(self.transition_matrix[current_state].values())
            if total_transitions > 0:
                for next_state in self.transition_matrix[current_state]:
                    self.transition_matrix[current_state][next_state] /= total_transitions
        
        # Guardar modelo entrenado
        self._save_model()
        
        print(f"Modelo entrenado con {len(self.states)} estados únicos")
    
    def predict_next_state(self, current_state: str, steps: int = 1) -> Dict[str, float]:
        """
        Predice el próximo estado del clima
        
        Args:
            current_state: Estado actual como string
            steps: Número de pasos hacia adelante a predecir
            
        Returns:
            Diccionario con probabilidades de cada estado futuro
        """
        if current_state not in self.transition_matrix:
            return {}
        
        current_probs = {state: 0.0 for state in self.states}
        current_probs[current_state] = 1.0
        
        # Aplicar transiciones iterativamente
        for _ in range(steps):
            next_probs = {state: 0.0 for state in self.states}
            
            for state, prob in current_probs.items():
                if prob > 0 and state in self.transition_matrix:
                    for next_state, transition_prob in self.transition_matrix[state].items():
                        next_probs[next_state] += prob * transition_prob
            
            current_probs = next_probs
        
        return current_probs
    
    def get_weather_impact_factor(self, weather_conditions: Dict[str, Any]) -> float:
        """
        Calcula el factor de impacto del clima en las rutas usando la cadena de Markov
        
        Args:
            weather_conditions: Condiciones climáticas actuales
            
        Returns:
            Factor multiplicativo para el peso de las aristas (>1.0 = más lento)
        """
        # Convertir condiciones a estado
        current_state_obj = WeatherState.from_weather_data(weather_conditions)
        current_state = current_state_obj.to_string()
        
        # Predecir el siguiente estado (para considerar tendencias)
        future_states = self.predict_next_state(current_state, steps=1)
        
        # Calcular factor base según estado actual
        base_factor = self._calculate_base_impact_factor(current_state_obj)
        
        # Ajustar según tendencias futuras
        future_factor = 0.0
        for future_state_str, probability in future_states.items():
            if probability > 0:
                future_state_parts = future_state_str.split('_')
                if len(future_state_parts) == 4:
                    future_state_obj = WeatherState(
                        future_state_parts[0], future_state_parts[1],
                        future_state_parts[2], future_state_parts[3]
                    )
                    future_factor += probability * self._calculate_base_impact_factor(future_state_obj)
        
        # Combinar factor actual con tendencia futura (70% actual, 30% futuro)
        final_factor = 0.7 * base_factor + 0.3 * future_factor
        
        return max(1.0, final_factor)  # Mínimo factor de 1.0
    
    def _calculate_base_impact_factor(self, state: WeatherState) -> float:
        """Calcula el factor de impacto base para un estado del clima"""
        factor = 1.0
        
        # Impacto de precipitación
        precip_factors = {
            "none": 1.0,
            "light": 1.2,
            "moderate": 1.5,
            "heavy": 2.0
        }
        factor *= precip_factors.get(state.precipitation_level, 1.0)
        
        # Impacto del viento
        wind_factors = {
            "calm": 1.0,
            "light": 1.1,
            "moderate": 1.3,
            "strong": 1.6
        }
        factor *= wind_factors.get(state.wind_level, 1.0)
        
        # Impacto de la temperatura extrema
        temp_factors = {
            "cold": 1.2,    # Frío puede afectar vehículos
            "mild": 1.0,
            "warm": 1.0,
            "hot": 1.1      # Calor extremo puede ser problemático
        }
        factor *= temp_factors.get(state.temperature_range, 1.0)
        
        # Impacto de la visibilidad (cobertura de nubes como proxy)
        cloud_factors = {
            "clear": 1.0,
            "partial": 1.05,
            "overcast": 1.15
        }
        factor *= cloud_factors.get(state.cloud_cover, 1.0)
        
        return factor
    
    def _save_model(self):
        """Guarda el modelo entrenado en archivo"""
        model_data = {
            'transition_matrix': self.transition_matrix,
            'state_frequencies': self.state_frequencies,
            'states': list(self.states)
        }
        
        with open(self.model_cache, 'wb') as f:
            pickle.dump(model_data, f)
    
    def load_model(self) -> bool:
        """
        Carga el modelo previamente entrenado
        
        Returns:
            True si se cargó exitosamente, False en caso contrario
        """
        if not os.path.exists(self.model_cache):
            return False
        
        try:
            with open(self.model_cache, 'rb') as f:
                model_data = pickle.load(f)
            
            self.transition_matrix = model_data['transition_matrix']
            self.state_frequencies = model_data['state_frequencies']
            self.states = set(model_data['states'])
            
            print(f"Modelo cargado con {len(self.states)} estados")
            return True
        except Exception as e:
            print(f"Error cargando modelo: {e}")
            return False
    
    def get_model_statistics(self) -> Dict[str, Any]:
        """Retorna estadísticas del modelo entrenado"""
        if not self.states:
            return {"error": "Modelo no entrenado"}
        
        stats = {
            "total_states": len(self.states),
            "most_common_states": sorted(
                self.state_frequencies.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10],
            "transition_matrix_size": sum(
                len(transitions) for transitions in self.transition_matrix.values()
            )
        }
        
        return stats


if __name__ == "__main__":
    # Ejemplo de uso
    markov = WeatherMarkovChain()
    
    # Intentar cargar modelo existente
    if not markov.load_model():
        print("Entrenando nuevo modelo...")
        markov.train_markov_model()
    
    # Probar predicción
    test_conditions = {
        'temperature_2m': 28,
        'precipitation': 5,
        'wind_speed_10m': 15,
        'cloud_cover': 80,
        'weather_code': 61
    }
    
    impact_factor = markov.get_weather_impact_factor(test_conditions)
    print(f"Factor de impacto del clima: {impact_factor:.2f}")
    
    # Mostrar estadísticas
    stats = markov.get_model_statistics()
    print(f"Estadísticas del modelo: {stats}")
