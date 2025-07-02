"""
Script de Prueba Rápida - Verificación de Correcciones
====================================================

Este script ejecuta una prueba rápida para verificar que los errores 
han sido corregidos antes de ejecutar el análisis completo.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Añadir el directorio raíz al path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

def prueba_rapida():
    """Ejecuta una prueba rápida con un solo caso para verificar correcciones"""
    
    print("🔧 PRUEBA RÁPIDA - VERIFICACIÓN DE CORRECCIONES")
    print("=" * 50)
    
    try:
        from src.NLP.prompt_engineering_analyzer import CVRPPromptAnalyzer, PromptStrategy
        print("✅ Importación de analizador exitosa")
        
        # Crear analizador
        analyzer = CVRPPromptAnalyzer()
        print("✅ Creación de analizador exitosa")
        
        # Verificar que los casos de prueba se crean correctamente
        test_cases = analyzer.test_cases
        print(f"✅ Se crearon {len(test_cases)} casos de prueba")
        
        # Ejecutar análisis con solo una estrategia y un caso
        print("\n📊 Ejecutando prueba con Zero-Shot en un caso simple...")
        
        # Modificar temporalmente para usar solo el primer caso
        original_cases = analyzer.test_cases
        analyzer.test_cases = [original_cases[0]]  # Solo el primer caso (simple)
        
        strategies = [PromptStrategy.ZERO_SHOT]
        
        # Ejecutar análisis
        report = analyzer.run_comprehensive_analysis(strategies)
        
        if report and 'executive_summary' in report:
            print("✅ Análisis completado sin errores")
            summary = report['executive_summary']
            print(f"   📈 Puntuación: {summary.get('average_overall_score', 'N/A')}")
            print(f"   📋 Pruebas: {summary.get('total_tests', 'N/A')}")
            return True
        else:
            print("❌ El análisis no generó resultados válidos")
            return False
            
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")
        import traceback
        traceback.print_exc()
        return False

def prueba_comparador():
    """Prueba rápida del comparador"""
    
    print("\n🔍 PRUEBA RÁPIDA - COMPARADOR")
    print("=" * 35)
    
    try:
        from src.NLP.prompt_comparison_analyzer import PromptComparator
        print("✅ Importación de comparador exitosa")
        
        # Crear comparador
        comparator = PromptComparator()
        print("✅ Creación de comparador exitosa")
        
        # Verificar casos de prueba
        test_cases = comparator.test_cases
        print(f"✅ Se crearon {len(test_cases)} casos de comparación")
        
        # Probar evaluación de respuesta
        test_response = '{"num_trucks": 2, "truck_capacities": [50, 60], "target_demands": [30, 25, 35]}'
        test_expected = {
            "num_trucks": 2,
            "truck_capacities": [50, 60],
            "target_demands": [30, 25, 35]
        }
        
        metrics = comparator._evaluate_response(test_response, test_expected)
        print("✅ Evaluación de respuesta exitosa")
        print(f"   🎯 Precisión camiones: {metrics['truck_accuracy']}")
        print(f"   📦 Precisión capacidades: {metrics['capacity_accuracy']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba de comparador: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal de prueba"""
    
    print("🧪 VERIFICACIÓN RÁPIDA DE CORRECCIONES")
    print("=" * 40)
    print("Este script verifica que los errores han sido corregidos\n")
    
    # Verificar dependencias primero
    try:
        import pandas
        import matplotlib
        import seaborn
        print("✅ Todas las dependencias están instaladas")
    except ImportError as e:
        print(f"❌ Dependencia faltante: {e}")
        print("Ejecute: pip install matplotlib>=3.5.0 seaborn>=0.11.0")
        return False
    
    # Ejecutar pruebas
    prueba1 = prueba_rapida()
    prueba2 = prueba_comparador()
    
    print("\n" + "=" * 40)
    if prueba1 and prueba2:
        print("🎉 ¡TODAS LAS PRUEBAS PASARON!")
        print("✨ El sistema está listo para el análisis completo")
        print("\n💡 Puede ejecutar ahora:")
        print("   python src/NLP/run_prompt_analysis.py")
        return True
    else:
        print("❌ ALGUNAS PRUEBAS FALLARON")
        print("🔧 Revise los errores anteriores antes de continuar")
        return False

if __name__ == "__main__":
    main()
