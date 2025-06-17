# Sistema de Análisis Climático para Logística Urbana

## 📝 Descripción General

Este sistema integra **representación del conocimiento** y **cadenas de Markov** para analizar el impacto del clima en las rutas de entrega, basado en los principios del paper de referencia sobre grafos de conocimiento.

## 🏗️ Arquitectura del Sistema

### 1. Grafo de Conocimiento del Clima (`weather_knowledge_graph.py`)
- **Entidades**: Condiciones climáticas (lluvia, viento, temperatura, etc.)
- **Relaciones**: Conexiones causa-efecto entre clima y transporte
- **Propiedades**: Factores de impacto, niveles de confianza
- **Consultas**: Análisis directo de impacto basado en reglas expertas

### 2. Cadena de Markov (`weather_markov_chain.py`)
- **Estados**: Combinaciones de condiciones climáticas discretizadas
- **Transiciones**: Probabilidades de cambio entre estados climáticos
- **Entrenamiento**: Datos históricos de 2 años desde open-meteo.com
- **Predicción**: Factores de impacto basados en tendencias temporales

### 3. Analizador Integrado (`weather_impact_analyzer.py`)
- **Combinación**: Fusiona análisis del grafo (60%) y Markov (40%)
- **API**: Conexión con open-meteo.com para datos en tiempo real
- **Reporting**: Genera reportes detallados de análisis climático

## 🔧 Instalación y Configuración

### Paso 1: Instalar Dependencias
```bash
pip install -r requirements_weather.txt
```

### Paso 2: Entrenar el Sistema
```bash
python setup_weather_system.py
```

Este proceso:
- Descarga datos climáticos históricos (2 años)
- Entrena la cadena de Markov
- Inicializa el grafo de conocimiento
- Genera archivos de configuración

### Paso 3: Verificar Instalación
El sistema genera los siguientes archivos:
- `cache/weather_historical_data.json` - Datos históricos
- `cache/markov_model.pkl` - Modelo entrenado
- `weather_knowledge_graph.json` - Estructura del grafo
- `weather_analysis_report.json` - Reporte de prueba

## 🌦️ Funcionamiento del Sistema

### Estados Climáticos (Cadena de Markov)
Los estados se definen por combinación de:
- **Precipitación**: none, light, moderate, heavy
- **Temperatura**: cold, mild, warm, hot  
- **Viento**: calm, light, moderate, strong
- **Nubosidad**: clear, partial, overcast

Ejemplo: `"light_mild_calm_partial"`

### Factores de Impacto
El sistema calcula multiplicadores de peso para las aristas del grafo:
- **1.0 - 1.1**: Condiciones ideales
- **1.1 - 1.3**: Impacto mínimo  
- **1.3 - 1.6**: Impacto moderado
- **1.6 - 2.0**: Impacto alto
- **>2.0**: Condiciones severas

### Integración con Optimización
```python
# En optimized_route.py
adjusted_distance = base_distance * weather_factor
```

## 📊 API del Sistema

### Uso Básico
```python
from src.weather.weather_impact_analyzer import WeatherImpactAnalyzer

analyzer = WeatherImpactAnalyzer()
factor, info = analyzer.calculate_weather_impact_factor()
print(f"Factor de impacto: {factor:.2f}")
```

### Función de Conveniencia
```python
from src.weather.weather_impact_analyzer import get_weather_impact_for_routes

# Para usar en optimización de rutas
weather_factor = get_weather_impact_for_routes()
```

### Pronóstico por Horas
```python
forecast = analyzer.get_hourly_forecast_impact(hours=24)
for hour in forecast:
    print(f"{hour['time']}: Factor {hour['impact_factor']:.2f}")
```

## 🎯 Integración en el Sistema Principal

### 1. Backend (server.py)
- Inicializa automáticamente el analizador climático
- Incluye información climática en respuestas de optimización
- Aplica factores climáticos a las rutas calculadas

### 2. Frontend (App.jsx)
- Muestra panel de información climática
- Visualiza factor de impacto con código de colores
- Presenta recomendaciones basadas en condiciones

### 3. Optimización (optimized_route.py)
- Aplica factores climáticos a matriz de distancias
- Modifica pesos de aristas según condiciones meteorológicas
- Integra análisis en algoritmos metaheurísticos

## 📈 Datos y Fuentes

### Open-Meteo API
- **URL**: https://api.open-meteo.com/v1/forecast
- **Ubicación**: La Habana, Cuba (23.1136, -82.3666)
- **Variables**: temperatura, precipitación, viento, nubosidad, visibilidad
- **Frecuencia**: Datos horarios
- **Histórico**: Últimos 2 años para entrenamiento

### Procesamiento de Datos
1. **Descarga**: Chunks de 3 meses para evitar límites de API
2. **Discretización**: Conversión a estados categóricos
3. **Entrenamiento**: Cálculo de matriz de transiciones
4. **Validación**: Pruebas de coherencia estadística

## 🔍 Ejemplos de Uso

### Escenario 1: Día Despejado
```json
{
  "impact_factor": 1.02,
  "interpretation": "Condiciones ideales - Sin impacto significativo",
  "weather_data": {
    "temperature_2m": 26.5,
    "precipitation": 0.0,
    "wind_speed_10m": 8.2,
    "cloud_cover": 15
  }
}
```

### Escenario 2: Lluvia Intensa
```json
{
  "impact_factor": 2.15,
  "interpretation": "Condiciones severas - Retrasos significativos",
  "weather_data": {
    "temperature_2m": 24.1,
    "precipitation": 12.5,
    "wind_speed_10m": 35.0,
    "cloud_cover": 95
  }
}
```

## 🛠️ Mantenimiento y Mejoras

### Actualización de Datos
```bash
# Forzar reentrenamiento con datos frescos
python -c "
from src.weather.weather_markov_chain import WeatherMarkovChain
markov = WeatherMarkovChain()
markov.train_markov_model(force_refresh=True)
"
```

### Ajuste de Parámetros
- Modificar factores en `weather_knowledge_graph.py`
- Ajustar ponderación en `weather_impact_analyzer.py` (60% grafo, 40% Markov)
- Cambiar discretización en `weather_markov_chain.py`

### Extensiones Futuras
- Agregar más variables meteorológicas
- Implementar predicción a largo plazo
- Incluir eventos meteorológicos extremos
- Integrar datos de tráfico en tiempo real

## 🚨 Manejo de Errores

El sistema incluye múltiples niveles de tolerancia a fallos:
- **Fallback**: Si no hay conexión a API, usa datos por defecto
- **Cache**: Almacena datos históricos localmente
- **Degradación**: Si falla Markov, usa solo grafo de conocimiento
- **Logging**: Registra errores para depuración

## 📋 Referencias

- Paper base: "Representación del conocimiento con grafos" (Redalyc)
- API meteorológica: [Open-Meteo.com](https://open-meteo.com/)
- Teoría de Markov: Aplicada a modelado meteorológico
- VRP: Vehicle Routing Problem con restricciones dinámicas
