"""
Script para entrenar el modelo de cadena de Markov con datos históricos del clima
Ejecutar este script para inicializar el sistema de análisis climático
"""

import sys
import os
from datetime import datetime, timedelta

# Añadir ruta del proyecto al path de Python
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

try:
    from src.weather.weather_markov_chain import WeatherMarkovChain
    from src.weather.weather_impact_analyzer import WeatherImpactAnalyzer
    from src.knowledge_graph.weather_knowledge_graph import WeatherKnowledgeGraph
    print("✅ Módulos importados correctamente")
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("Verificando dependencias...")
    
    # Verificar dependencias críticas
    missing_deps = []
    try:
        import requests
    except ImportError:
        missing_deps.append("requests")
    
    try:
        import aiohttp
    except ImportError:
        missing_deps.append("aiohttp")
    
    try:
        import networkx
    except ImportError:
        missing_deps.append("networkx")
    
    if missing_deps:
        print(f"Dependencias faltantes: {', '.join(missing_deps)}")
        print("Instala con: pip install " + " ".join(missing_deps))
    
    sys.exit(1)


def main():
    """Función principal para entrenar e inicializar el sistema climático"""
    print("="*60)
    print("INICIALIZACIÓN DEL SISTEMA DE ANÁLISIS CLIMÁTICO")
    print("="*60)
    
    try:
        # 1. Entrenar modelo de cadena de Markov
        print("\n1. Entrenando modelo de cadena de Markov...")
        markov = WeatherMarkovChain()
        
        if not markov.load_model():
            print("   Modelo no encontrado. Entrenando nuevo modelo...")
            print("   NOTA: Este proceso puede tomar varios minutos...")
            print("   Se van a descargar datos climáticos de los últimos 2 años...")
            
            # Entrenar modelo
            markov.train_markov_model()
            print("   ✅ Modelo de Markov entrenado exitosamente")
        else:
            print("   ✅ Modelo de Markov cargado desde caché")
        
        # Mostrar estadísticas del modelo
        stats = markov.get_model_statistics()
        print(f"   📊 Estados únicos: {stats.get('total_states', 'N/A')}")
        
        # 2. Inicializar grafo de conocimiento
        print("\n2. Inicializando grafo de conocimiento...")
        kg = WeatherKnowledgeGraph()
        print("   ✅ Grafo de conocimiento inicializado")
        
        # Exportar grafo para referencia
        kg.export_knowledge_graph("weather_knowledge_graph.json")
        print("   📄 Grafo exportado a weather_knowledge_graph.json")
        
        # 3. Probar sistema integrado
        print("\n3. Probando sistema integrado...")
        analyzer = WeatherImpactAnalyzer()
        
        # Obtener clima actual y calcular impacto
        try:
            factor, info = analyzer.calculate_weather_impact_factor()
            print(f"   🌤️  Factor de impacto actual: {factor:.2f}")
            print(f"   📝 Interpretación: {info.get('interpretation', 'N/A')}")
            
            # Mostrar datos climáticos actuales
            weather_data = info.get('weather_data', {})
            if weather_data:
                temp = weather_data.get('temperature_2m', 'N/A')
                precip = weather_data.get('precipitation', 'N/A')
                wind = weather_data.get('wind_speed_10m', 'N/A')
                print(f"   🌡️  Temperatura: {temp}°C")
                print(f"   🌧️  Precipitación: {precip} mm")
                print(f"   💨 Viento: {wind} km/h")
            
        except Exception as e:
            print(f"   ⚠️  Error obteniendo clima actual: {e}")
            print("   ℹ️  El sistema funcionará con datos por defecto")
        
        # 4. Generar reporte de prueba
        print("\n4. Generando reporte de prueba...")
        try:
            analyzer.export_analysis_report("weather_analysis_report.json")
            print("   📊 Reporte generado: weather_analysis_report.json")
        except Exception as e:
            print(f"   ⚠️  Error generando reporte: {e}")
        
        # 5. Mostrar información de uso
        print("\n" + "="*60)
        print("✅ SISTEMA DE ANÁLISIS CLIMÁTICO LISTO")
        print("="*60)
        print("\nCómo usar el sistema:")
        print("1. El servidor automáticamente usará el análisis climático")
        print("2. Los factores climáticos se aplicarán a las rutas optimizadas")
        print("3. La información climática aparecerá en la interfaz web")
        print("\nArchivos generados:")
        print("- cache/weather_historical_data.json (datos históricos)")
        print("- cache/markov_model.pkl (modelo entrenado)")
        print("- weather_knowledge_graph.json (grafo de conocimiento)")
        print("- weather_analysis_report.json (reporte de prueba)")
        
        # Información adicional
        print("\nConfiguración del sistema:")
        print(f"- Ubicación: La Habana, Cuba")
        print(f"- Coordenadas: {analyzer.latitude:.4f}, {analyzer.longitude:.4f}")
        print(f"- Fuente de datos: open-meteo.com")
        print(f"- Período de entrenamiento: Últimos 2 años")
        
    except KeyboardInterrupt:
        print("\n⚠️  Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error durante la inicialización: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    print("\n" + "="*60)
    if exit_code == 0:
        print("Proceso completado exitosamente")
    else:
        print("Proceso terminado con errores")
    print("="*60)
    sys.exit(exit_code)
