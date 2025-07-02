# Análisis de Prompt Engineering para CVRP
## Sistema de Evaluación y Optimización de Prompts

Este sistema proporciona un análisis completo de técnicas de prompt engineering aplicadas al problema de extracción de parámetros CVRP (Capacitated Vehicle Routing Problem) usando procesamiento de lenguaje natural.

## 📋 Tabla de Contenidos

- [Descripción General](#-descripción-general)
- [Arquitectura del Sistema](#-arquitectura-del-sistema)
- [Estrategias de Prompt Engineering](#-estrategias-de-prompt-engineering)
- [Casos de Prueba](#-casos-de-prueba)
- [Métricas de Evaluación](#-métricas-de-evaluación)
- [Instalación y Uso](#-instalación-y-uso)
- [Resultados y Análisis](#-resultados-y-análisis)
- [Archivos Generados](#-archivos-generados)

## 🎯 Descripción General

El sistema evalúa diferentes estrategias de prompt engineering para mejorar la extracción automática de parámetros CVRP a partir de descripciones en lenguaje natural. Los parámetros clave que se extraen son:

- **Número de camiones/vehículos**
- **Capacidades de los vehículos**
- **Demandas de cada ubicación de destino**

### Objetivos del Análisis

1. **Comparar estrategias**: Evaluar diferentes técnicas de prompt engineering
2. **Optimizar precisión**: Mejorar la exactitud en la extracción de parámetros
3. **Mejorar robustez**: Manejar casos ambiguos y complejos
4. **Evaluar eficiencia**: Considerar tiempo de respuesta y uso de tokens

## 🏗️ Arquitectura del Sistema

```
src/NLP/
├── prompt_engineering_analyzer.py     # Analizador principal de estrategias
├── prompt_comparison_analyzer.py      # Comparador prompt actual vs optimizados
├── run_prompt_analysis.py            # Script ejecutor principal
├── cvrp_assistant.py                 # Asistente CVRP original
├── Gemini.py                         # Interface con LLM
└── README_prompt_analysis.md         # Esta documentación
```

### Componentes Principales

#### 1. `CVRPPromptAnalyzer`
- Evaluación de múltiples estrategias de prompt engineering
- Casos de prueba variados (simple, medio, complejo)
- Métricas de evaluación comprehensivas

#### 2. `PromptComparator`
- Comparación específica entre prompt actual y versiones optimizadas
- Análisis de mejoras y degradaciones
- Recomendaciones de implementación

#### 3. `PromptAnalysisOrchestrator`
- Coordinador principal de todos los análisis
- Generación de reportes integrados
- Interface de usuario interactiva

## 🎨 Estrategias de Prompt Engineering

### 1. **Zero-Shot**
```
Estrategia directa sin ejemplos previos
- Instrucciones claras y concisas
- Formato de salida específico
- Contexto mínimo necesario
```

### 2. **Few-Shot**
```
Incluye ejemplos de casos similares
- 2-3 ejemplos representativos
- Patrón de entrada → análisis → salida
- Mejora comprensión del formato esperado
```

### 3. **Chain of Thought (CoT)**
```
Razonamiento paso a paso explícito
- Descomposición del problema
- Justificación de cada decisión
- Proceso de validación incluido
```

### 4. **Role Playing**
```
Asume rol de experto en logística
- Contexto profesional de 15 años
- Experiencia en optimización de rutas
- Recomendaciones basadas en expertise
```

### 5. **Structured Output**
```
Formato de salida altamente estructurado
- Metadatos de análisis
- Validaciones incorporadas
- Estructura jerárquica clara
```

### 6. **Context Aware**
```
Incorpora contexto geográfico y cultural
- Consideraciones locales (Habana, Cuba)
- Factores infraestructura y clima
- Prácticas comerciales regionales
```

### 7. **Step by Step Enhanced**
```
Proceso detallado con validación
- 5 pasos claramente definidos
- Verificaciones en cada etapa
- Correcciones automáticas
```

## 🧪 Casos de Prueba

### Clasificación por Complejidad

#### **Casos Simples**
- Parámetros explícitamente mencionados
- Números claros y específicos
- Contexto directo y sin ambigüedad

```
Ejemplo: "Tengo 2 camiones de 50 cajas cada uno para repartir a 3 tiendas 
que necesitan 20, 15 y 10 cajas respectivamente"
```

#### **Casos Medianos**
- Algunos parámetros explícitos, otros implícitos
- Restricciones múltiples mencionadas
- Requiere inferencia contextual

```
Ejemplo: "Tengo 3 camiones para repartir medicinas a 5 farmacias. 
Cada farmacia necesita diferente cantidad según su tamaño: 2 son grandes y 3 pequeñas"
```

#### **Casos Complejos**
- Información ambigua o contradictoria
- Múltiples interpretaciones posibles
- Requiere razonamiento avanzado

```
Ejemplo: "Tengo 1 camión pequeño pero necesito entregar grandes volúmenes 
a 8 puntos de venta para el fin de semana"
```

### Clasificación por Tipo de Escenario

- **Explícito**: Todos los parámetros claramente especificados
- **Implícito**: Algunos parámetros requieren inferencia
- **Ambiguo**: Información contradictoria o insuficiente

## 📊 Métricas de Evaluación

### Métricas Principales

1. **Precisión del Conteo de Camiones** (25%)
   - Exactitud en el número de vehículos
   - Métrica clave para validación de usuario

2. **Precisión de Capacidades** (20%)
   - Aproximación a capacidades realistas
   - Consistencia entre vehículos

3. **Precisión de Demandas** (20%)
   - Distribución realista entre destinos
   - Suma compatible con capacidades

4. **Completitud de Respuesta** (15%)
   - Presencia de todos los campos requeridos
   - Estructura JSON válida

5. **Validez del JSON** (10%)
   - Formato parseable correctamente
   - Cumplimiento del esquema

6. **Calidad del Razonamiento** (10%)
   - Presencia de explicaciones
   - Lógica coherente en decisiones

### Métricas Secundarias

- **Tiempo de Ejecución**: Eficiencia de respuesta
- **Eficiencia de Tokens**: Uso óptimo del contexto
- **Factibilidad Matemática**: Capacidad ≥ Demanda total

## 🚀 Instalación y Uso

### Prerrequisitos

```bash
# Dependencias requeridas
pip install pandas numpy matplotlib seaborn
```

### Ejecución Interactiva

```bash
# Ejecutar menú principal
python src/NLP/run_prompt_analysis.py
```

### Ejecución por Línea de Comandos

```bash
# Análisis completo
python src/NLP/run_prompt_analysis.py --mode complete --non-interactive

# Análisis rápido
python src/NLP/run_prompt_analysis.py --mode quick --non-interactive

# Comparación de prompts
python src/NLP/run_prompt_analysis.py --mode comparison --non-interactive

# Todos los análisis
python src/NLP/run_prompt_analysis.py --mode all --non-interactive
```

### Ejecución Programática

```python
from src.NLP.prompt_engineering_analyzer import CVRPPromptAnalyzer, PromptStrategy
from src.NLP.prompt_comparison_analyzer import PromptComparator

# Análisis de estrategias específicas
analyzer = CVRPPromptAnalyzer()
strategies = [PromptStrategy.CHAIN_OF_THOUGHT, PromptStrategy.FEW_SHOT]
report = analyzer.run_comprehensive_analysis(strategies)

# Comparación con prompt actual
comparator = PromptComparator()
comparison = comparator.run_comparison_analysis()
```

## 📈 Resultados y Análisis

### Estructura de Reportes

Los reportes generados incluyen:

#### Resumen Ejecutivo
```json
{
  "total_tests": 21,
  "strategies_evaluated": 7,
  "average_overall_score": 0.756,
  "best_strategy_overall": "chain_of_thought",
  "best_strategy_truck_accuracy": "validation_focused"
}
```

#### Análisis por Estrategia
- Rendimiento promedio por métrica
- Desviación estándar
- Comparación relativa

#### Análisis por Complejidad
- Rendimiento según dificultad del caso
- Degradación con complejidad creciente
- Estrategias más robustas

#### Recomendaciones
- Estrategia óptima identificada
- Mejoras específicas sugeridas
- Consideraciones de implementación

### Visualizaciones Generadas

1. **Gráfico de Barras**: Rendimiento por estrategia
2. **Heatmap**: Rendimiento vs complejidad
3. **Comparación Temporal**: Velocidad de respuesta
4. **Análisis de Mejoras**: Comparación con baseline

## 📁 Archivos Generados

### Directorio `analysis_results/`
```
analysis_results/
├── complete_analysis_YYYYMMDD_HHMMSS.json
├── complete_analysis_viz_YYYYMMDD_HHMMSS.png
├── quick_analysis_YYYYMMDD_HHMMSS.json
├── quick_analysis_viz_YYYYMMDD_HHMMSS.png
└── summary_report_YYYYMMDD_HHMMSS.json
```

### Directorio `comparison_results/`
```
comparison_results/
├── comparison_analysis_YYYYMMDD_HHMMSS.json
├── comparison_viz_YYYYMMDD_HHMMSS.png
└── prompt_comparison_report_YYYYMMDD_HHMMSS.json
```

### Contenido de Archivos JSON

#### Reporte de Análisis
```json
{
  "executive_summary": {...},
  "strategy_performance": {...},
  "complexity_analysis": {...},
  "best_strategies": {...},
  "recommendations": [...],
  "detailed_results": [...],
  "analysis_timestamp": "2025-07-02T..."
}
```

#### Reporte de Comparación
```json
{
  "executive_summary": {...},
  "strategy_performance": {...},
  "improvements_over_current": {...},
  "detailed_results": [...],
  "recommendations": [...],
  "analysis_timestamp": "2025-07-02T..."
}
```

## 🔧 Configuración y Personalización

### Modificación de Casos de Prueba

Para agregar nuevos casos de prueba, edite el método `_create_test_cases()` en `CVRPPromptAnalyzer`:

```python
TestCase(
    id="custom_01",
    name="Mi Caso Personalizado",
    description="Descripción del caso",
    user_input="Descripción del usuario...",
    expected_trucks=2,
    expected_capacities=[100, 80],
    expected_demands=[40, 30, 50],
    complexity_level="medium",
    scenario_type="implicit",
    depot_info={"id": 123, "position": [-82.36, 23.11]},
    targets_info=[...]
)
```

### Nuevas Estrategias de Prompt

Para implementar nuevas estrategias:

1. Agregar nueva entrada al enum `PromptStrategy`
2. Implementar método `_generate_nueva_estrategia()` en `PromptEngineering`
3. Agregar al diccionario `self.strategies`

### Personalización de Métricas

Modifique el método `evaluate_prompt_response()` para ajustar:
- Pesos de métricas individuales
- Nuevas métricas de evaluación
- Criterios de validación

## 📊 Interpretación de Resultados

### Puntuaciones Típicas

- **0.8-1.0**: Excelente rendimiento
- **0.6-0.8**: Buen rendimiento
- **0.4-0.6**: Rendimiento aceptable
- **0.0-0.4**: Rendimiento deficiente

### Factores de Éxito

1. **Claridad del Prompt**: Instrucciones específicas y no ambiguas
2. **Ejemplos Efectivos**: Casos representativos en few-shot
3. **Validación Incorporada**: Verificaciones de consistencia
4. **Contexto Apropiado**: Información geográfica y cultural relevante

### Mejores Prácticas Identificadas

1. **Usar validación explícita** de parámetros extraídos
2. **Incluir ejemplos variados** en complejidad
3. **Proporcionar contexto local** para mejor inferencia
4. **Estructurar salida** de forma clara y parseable
5. **Implementar correcciones automáticas** para casos inconsistentes

## 🤝 Contribución y Extensión

Para extender el sistema:

1. **Fork** el repositorio
2. **Implemente** nuevas estrategias o métricas
3. **Teste** con casos de prueba existentes
4. **Documente** cambios realizados
5. **Envíe** pull request con descripción detallada

## 📝 Notas Adicionales

- Los análisis requieren conexión a internet para acceso al LLM
- Los resultados pueden variar entre ejecuciones debido a la naturaleza estocástica de los LLMs
- Se recomienda ejecutar múltiples iteraciones para resultados más robustos
- El sistema está optimizado para el dominio CVRP pero puede adaptarse a otros problemas de optimización

---

**Fecha de creación**: 2 de Julio, 2025
**Versión**: 1.0
**Autores**: Sistema de Análisis de Prompt Engineering
