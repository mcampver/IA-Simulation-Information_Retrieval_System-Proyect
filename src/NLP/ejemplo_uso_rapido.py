"""
Ejemplo de Uso Rápido - Sistema de Análisis de Prompt Engineering CVRP
=====================================================================

Este script demuestra cómo usar el sistema de análisis de prompt engineering
de forma rápida y sencilla para casos específicos.

Autor: Sistema de Análisis de Prompt Engineering
Fecha: 2025-07-02
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Añadir el directorio raíz al path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

try:
    from src.NLP.prompt_engineering_analyzer import CVRPPromptAnalyzer, PromptStrategy
    from src.NLP.prompt_comparison_analyzer import PromptComparator
    from src.NLP.cvrp_assistant import analyze_cvrp_requirements
except ImportError as e:
    print(f"Error importando módulos: {e}")
    print("Asegúrese de que todos los archivos estén en su lugar")
    sys.exit(1)

def ejemplo_basico():
    """Ejemplo básico de análisis de una sola estrategia"""
    
    print("🎯 EJEMPLO BÁSICO - ANÁLISIS DE UNA ESTRATEGIA")
    print("=" * 50)
    
    # Crear analizador
    analyzer = CVRPPromptAnalyzer()
    
    # Seleccionar solo Chain of Thought como ejemplo
    estrategias = [PromptStrategy.CHAIN_OF_THOUGHT]
    
    print("📊 Analizando estrategia Chain of Thought...")
    print("⏳ Esto tomará unos minutos...")
    
    # Ejecutar análisis
    reporte = analyzer.run_comprehensive_analysis(estrategias)
    
    # Mostrar resultados básicos
    print("\n✅ RESULTADOS:")
    if reporte and 'executive_summary' in reporte:
        summary = reporte['executive_summary']
        print(f"📈 Puntuación promedio: {summary.get('average_overall_score', 'N/A'):.3f}")
        print(f"🎯 Mejor estrategia: {summary.get('best_strategy_overall', 'N/A')}")
        print(f"📋 Total de pruebas: {summary.get('total_tests', 'N/A')}")
    
    # Guardar reporte
    report_path = analyzer.save_analysis_report("ejemplo_basico.json")
    print(f"💾 Reporte guardado en: {report_path}")
    
    return reporte

def ejemplo_comparacion_rapida():
    """Ejemplo de comparación rápida entre 2 estrategias"""
    
    print("\n🔍 EJEMPLO COMPARACIÓN - DOS ESTRATEGIAS")
    print("=" * 45)
    
    # Crear analizador
    analyzer = CVRPPromptAnalyzer()
    
    # Comparar Zero-Shot vs Few-Shot
    estrategias = [PromptStrategy.ZERO_SHOT, PromptStrategy.FEW_SHOT]
    
    print("📊 Comparando Zero-Shot vs Few-Shot...")
    
    # Ejecutar análisis
    reporte = analyzer.run_comprehensive_analysis(estrategias)
    
    # Mostrar comparación
    if reporte and 'strategy_performance' in reporte:
        performance = reporte['strategy_performance']
        
        print("\n📈 COMPARACIÓN DE RENDIMIENTO:")
        for strategy, metrics in performance.items():
            if isinstance(metrics, dict) and 'overall_score' in metrics:
                score = metrics['overall_score']
                if isinstance(score, dict) and 'mean' in score:
                    print(f"  {strategy}: {score['mean']:.3f}")
    
    return reporte

def ejemplo_caso_especifico():
    """Ejemplo con un caso específico usando el asistente original"""
    
    print("\n🎪 EJEMPLO ESPECÍFICO - CASO REAL")
    print("=" * 35)
    
    # Datos de ejemplo
    depot = {"id": 12345, "position": [-82.3666, 23.1136]}
    targets = [
        {"id": 101, "position": [-82.3656, 23.1146]},
        {"id": 102, "position": [-82.3676, 23.1126]},
        {"id": 103, "position": [-82.3686, 23.1156]}
    ]
    descripcion = "Tengo 2 camiones medianos para repartir comida a 3 restaurantes en La Habana"
    
    print(f"📍 Depot: {depot['id']}")
    print(f"🎯 Destinos: {len(targets)}")
    print(f"💬 Descripción: '{descripcion}'")
    
    print("\n⚙️ Procesando con el asistente CVRP original...")
    
    # Usar el asistente original
    resultado = analyze_cvrp_requirements(depot, targets, descripcion, 'vns_solver')
    
    print("\n✅ RESULTADO:")
    if resultado.get('success'):
        params = resultado['params']
        print(f"🚛 Camiones: {params['num_trucks']}")
        print(f"📦 Capacidades: {params['truck_capacities']}")
        print(f"📍 Demandas: {params['target_demands']}")
        print("\n💡 Análisis:", resultado.get('message', 'Sin mensaje')[:200] + "...")
    else:
        print(f"❌ Error: {resultado.get('error', 'Error desconocido')}")
    
    return resultado

def ejemplo_comparacion_con_actual():
    """Ejemplo de comparación específica con el prompt actual"""
    
    print("\n🔄 EJEMPLO COMPARACIÓN CON PROMPT ACTUAL")
    print("=" * 45)
    
    # Crear comparador
    comparator = PromptComparator()
    
    print("🔍 Comparando prompt actual vs versiones optimizadas...")
    print("⏳ Esto puede tomar varios minutos...")
    
    # Ejecutar comparación
    reporte = comparator.run_comparison_analysis()
    
    # Mostrar resultados clave
    if reporte and 'executive_summary' in reporte:
        summary = reporte['executive_summary']
        print("\n📊 RESUMEN DE COMPARACIÓN:")
        print(f"  🎯 Mejor estrategia: {summary.get('best_overall_strategy', 'N/A')}")
        print(f"  📈 Máxima mejora: {summary.get('max_improvement_percent', 0):.1f}%")
        print(f"  ⚡ Más rápida: {summary.get('fastest_strategy', 'N/A')}")
    
    # Mostrar recomendaciones
    if reporte and 'recommendations' in reporte:
        print("\n💡 RECOMENDACIONES CLAVE:")
        for i, rec in enumerate(reporte['recommendations'][:3], 1):
            print(f"  {i}. {rec}")
    
    # Guardar reporte
    report_path = comparator.save_comparison_report("ejemplo_comparacion.json")
    print(f"\n💾 Reporte completo guardado en: {report_path}")
    
    return reporte

def mostrar_menu_ejemplos():
    """Muestra menú de ejemplos disponibles"""
    
    print("\n🎯 EJEMPLOS DE USO - ANÁLISIS DE PROMPT ENGINEERING")
    print("=" * 55)
    print("\nSeleccione un ejemplo para ejecutar:")
    print("\n1. 🎯 Básico - Análisis de una estrategia (Chain of Thought)")
    print("2. 🔍 Comparación - Zero-Shot vs Few-Shot")
    print("3. 🎪 Caso Específico - Usar asistente original")
    print("4. 🔄 Comparación Completa - Prompt actual vs optimizados")
    print("5. 🚀 Ejecutar todos los ejemplos")
    print("6. ❌ Salir")
    
    while True:
        try:
            choice = input("\nIngrese su opción (1-6): ").strip()
            
            if choice in ['1', '2', '3', '4', '5', '6']:
                return int(choice)
            else:
                print("❌ Opción inválida. Ingrese un número del 1 al 6.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Ejemplos cancelados.")
            sys.exit(0)

def main():
    """Función principal de ejemplos"""
    
    print("🎓 EJEMPLOS DE USO - ANÁLISIS DE PROMPT ENGINEERING CVRP")
    print("=" * 60)
    print("\nEste script demuestra diferentes formas de usar el sistema")
    print("de análisis de prompt engineering para el problema CVRP.\n")
    
    resultados = []
    
    try:
        while True:
            opcion = mostrar_menu_ejemplos()
            
            if opcion == 1:
                resultado = ejemplo_basico()
                resultados.append(('basico', resultado))
                
            elif opcion == 2:
                resultado = ejemplo_comparacion_rapida()
                resultados.append(('comparacion_rapida', resultado))
                
            elif opcion == 3:
                resultado = ejemplo_caso_especifico()
                resultados.append(('caso_especifico', resultado))
                
            elif opcion == 4:
                resultado = ejemplo_comparacion_con_actual()
                resultados.append(('comparacion_completa', resultado))
                
            elif opcion == 5:
                print("🚀 Ejecutando todos los ejemplos...")
                resultados.append(('basico', ejemplo_basico()))
                resultados.append(('comparacion_rapida', ejemplo_comparacion_rapida()))
                resultados.append(('caso_especifico', ejemplo_caso_especifico()))
                resultados.append(('comparacion_completa', ejemplo_comparacion_con_actual()))
                break
                
            elif opcion == 6:
                break
            
            if opcion != 5:
                continuar = input("\n¿Desea ejecutar otro ejemplo? (s/n): ").strip().lower()
                if continuar not in ['s', 'sí', 'si', 'y', 'yes']:
                    break
        
        # Resumen final
        if resultados:
            print(f"\n🎉 EJEMPLOS COMPLETADOS - {len(resultados)} ejecutados")
            print("=" * 40)
            print("✅ Archivos generados:")
            
            # Mostrar archivos creados (aproximación)
            results_dir = Path(__file__).parent / "analysis_results"
            comparison_dir = Path(__file__).parent / "comparison_results"
            
            if results_dir.exists():
                json_files = list(results_dir.glob("*.json"))
                png_files = list(results_dir.glob("*.png"))
                print(f"  📊 Análisis: {len(json_files)} reportes, {len(png_files)} gráficos")
            
            if comparison_dir.exists():
                comp_files = list(comparison_dir.glob("*.json"))
                comp_viz = list(comparison_dir.glob("*.png"))
                print(f"  🔍 Comparaciones: {len(comp_files)} reportes, {len(comp_viz)} gráficos")
            
            print(f"\n📂 Ubicaciones:")
            print(f"  📊 {results_dir}")
            print(f"  🔍 {comparison_dir}")
        
        print("\n👋 ¡Gracias por probar los ejemplos!")
        
    except KeyboardInterrupt:
        print("\n\n👋 Ejemplos interrumpidos por el usuario.")
    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")
        print("Verifique que todas las dependencias estén instaladas.")

if __name__ == "__main__":
    main()
