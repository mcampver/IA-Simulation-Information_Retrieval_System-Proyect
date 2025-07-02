"""
Script Ejecutor Principal - Análisis de Prompt Engineering para CVRP
===================================================================

Este script principal permite ejecutar todos los análisis de prompt engineering
disponibles de forma sencilla e interactiva.

Opciones disponibles:
1. Análisis completo de estrategias de prompt engineering
2. Comparación específica: prompt actual vs optimizados
3. Análisis rápido con casos básicos
4. Generación de reportes personalizados

Autor: Sistema de Análisis de Prompt Engineering
Fecha: 2025-07-02
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Añadir el directorio raíz al path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

try:
    from src.NLP.prompt_engineering_analyzer import CVRPPromptAnalyzer, PromptStrategy
    from src.NLP.prompt_comparison_analyzer import PromptComparator
except ImportError as e:
    logger.error(f"Error importando módulos: {e}")
    logger.error("Asegúrese de que todos los archivos estén en su lugar y que las dependencias estén instaladas")
    sys.exit(1)

class PromptAnalysisOrchestrator:
    """Coordinador principal para todos los análisis de prompt engineering"""
    
    def __init__(self):
        self.results_dir = Path(__file__).parent / "analysis_results"
        self.results_dir.mkdir(exist_ok=True)
        
        self.comparison_dir = Path(__file__).parent / "comparison_results"
        self.comparison_dir.mkdir(exist_ok=True)
    
    def run_complete_analysis(self) -> dict:
        """Ejecuta análisis completo con todas las estrategias"""
        
        print("🚀 ANÁLISIS COMPLETO DE ESTRATEGIAS DE PROMPT ENGINEERING")
        print("=" * 60)
        
        # Crear analizador
        analyzer = CVRPPromptAnalyzer()
        
        # Ejecutar análisis con todas las estrategias
        print("📊 Evaluando todas las estrategias disponibles...")
        print("⏳ Esto puede tomar varios minutos...")
        
        strategies = list(PromptStrategy)
        report = analyzer.run_comprehensive_analysis(strategies)
        
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"complete_analysis_{timestamp}.json"
        viz_file = f"complete_analysis_viz_{timestamp}.png"
        
        report_path = analyzer.save_analysis_report(report_file)
        viz_path = analyzer.create_visualization(self.results_dir / viz_file)
        
        print(f"\n✅ Análisis completo finalizado")
        print(f"📄 Reporte: {report_path}")
        print(f"📊 Visualización: {viz_path}")
        
        return {
            'type': 'complete_analysis',
            'report': report,
            'files': {
                'report': report_path,
                'visualization': viz_path
            }
        }
    
    def run_comparison_analysis(self) -> dict:
        """Ejecuta comparación entre prompt actual y optimizados"""
        
        print("🔍 COMPARACIÓN: PROMPT ACTUAL VS OPTIMIZADOS")
        print("=" * 45)
        
        # Crear comparador
        comparator = PromptComparator()
        
        # Ejecutar comparación
        print("⚙️ Comparando prompt actual con versiones optimizadas...")
        print("⏳ Evaluando múltiples estrategias...")
        
        report = comparator.run_comparison_analysis()
        
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"comparison_analysis_{timestamp}.json"
        viz_file = f"comparison_viz_{timestamp}.png"
        
        report_path = comparator.save_comparison_report(report_file)
        viz_path = comparator.create_comparison_visualization(self.comparison_dir / viz_file)
        
        print(f"\n✅ Comparación finalizada")
        print(f"📄 Reporte: {report_path}")
        print(f"📊 Visualización: {viz_path}")
        
        return {
            'type': 'comparison_analysis',
            'report': report,
            'files': {
                'report': report_path,
                'visualization': viz_path
            }
        }
    
    def run_quick_analysis(self) -> dict:
        """Ejecuta análisis rápido con estrategias clave"""
        
        print("⚡ ANÁLISIS RÁPIDO - ESTRATEGIAS CLAVE")
        print("=" * 40)
        
        # Estrategias clave para análisis rápido
        key_strategies = [
            PromptStrategy.ZERO_SHOT,
            PromptStrategy.FEW_SHOT,
            PromptStrategy.CHAIN_OF_THOUGHT,
            PromptStrategy.STRUCTURED_OUTPUT
        ]
        
        # Crear analizador
        analyzer = CVRPPromptAnalyzer()
        
        print("📊 Evaluando estrategias clave...")
        report = analyzer.run_comprehensive_analysis(key_strategies)
        
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"quick_analysis_{timestamp}.json"
        viz_file = f"quick_analysis_viz_{timestamp}.png"
        
        report_path = analyzer.save_analysis_report(report_file)
        viz_path = analyzer.create_visualization(self.results_dir / viz_file)
        
        print(f"\n✅ Análisis rápido finalizado")
        print(f"📄 Reporte: {report_path}")
        print(f"📊 Visualización: {viz_path}")
        
        return {
            'type': 'quick_analysis',
            'report': report,
            'files': {
                'report': report_path,
                'visualization': viz_path
            }
        }
    
    def run_custom_analysis(self, strategies: list, test_cases: list = None) -> dict:
        """Ejecuta análisis personalizado con estrategias específicas"""
        
        print(f"🎯 ANÁLISIS PERSONALIZADO - {len(strategies)} ESTRATEGIAS")
        print("=" * 50)
        
        # Crear analizador
        analyzer = CVRPPromptAnalyzer()
        
        # Si se especifican casos de prueba, filtrar
        if test_cases:
            original_cases = analyzer.test_cases
            analyzer.test_cases = [case for case in original_cases if case.id in test_cases]
            print(f"📋 Usando {len(analyzer.test_cases)} casos de prueba específicos")
        
        print(f"📊 Evaluando estrategias: {[s.value for s in strategies]}")
        report = analyzer.run_comprehensive_analysis(strategies)
        
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        strategy_names = "_".join([s.value[:3] for s in strategies])
        report_file = f"custom_analysis_{strategy_names}_{timestamp}.json"
        viz_file = f"custom_analysis_{strategy_names}_{timestamp}.png"
        
        report_path = analyzer.save_analysis_report(report_file)
        viz_path = analyzer.create_visualization(self.results_dir / viz_file)
        
        print(f"\n✅ Análisis personalizado finalizado")
        print(f"📄 Reporte: {report_path}")
        print(f"📊 Visualización: {viz_path}")
        
        return {
            'type': 'custom_analysis',
            'report': report,
            'files': {
                'report': report_path,
                'visualization': viz_path
            }
        }
    
    def generate_summary_report(self, analyses: list) -> str:
        """Genera un reporte resumen de múltiples análisis"""
        
        print("📋 Generando reporte resumen...")
        
        summary = {
            'meta': {
                'generated_at': datetime.now().isoformat(),
                'analyses_included': len(analyses),
                'analysis_types': [a['type'] for a in analyses]
            },
            'executive_summary': {},
            'key_findings': [],
            'recommendations': [],
            'detailed_analyses': analyses
        }
        
        # Extraer hallazgos clave de cada análisis
        all_recommendations = []
        best_strategies = {}
        
        for analysis in analyses:
            if 'report' in analysis and 'recommendations' in analysis['report']:
                all_recommendations.extend(analysis['report']['recommendations'])
            
            if 'report' in analysis and 'executive_summary' in analysis['report']:
                exec_summary = analysis['report']['executive_summary']
                if 'best_strategy_overall' in exec_summary:
                    strategy = exec_summary['best_strategy_overall']
                    best_strategies[strategy] = best_strategies.get(strategy, 0) + 1
        
        # Encontrar estrategia más recomendada
        if best_strategies:
            most_recommended = max(best_strategies.keys(), key=lambda k: best_strategies[k])
            summary['executive_summary']['most_recommended_strategy'] = most_recommended
            summary['executive_summary']['recommendation_frequency'] = best_strategies[most_recommended]
        
        # Compilar recomendaciones únicas
        unique_recommendations = list(set(all_recommendations))
        summary['recommendations'] = unique_recommendations[:10]  # Top 10
        
        # Hallazgos clave
        summary['key_findings'] = [
            f"Se evaluaron {len(set(a['type'] for a in analyses))} tipos de análisis diferentes",
            f"La estrategia '{most_recommended}' fue la mejor en {best_strategies[most_recommended]} análisis" if best_strategies else "No se encontraron patrones consistentes",
            f"Se generaron {sum(len(a.get('report', {}).get('detailed_results', [])) for a in analyses)} evaluaciones individuales",
            f"Los análisis produjeron {len(unique_recommendations)} recomendaciones únicas"
        ]
        
        # Guardar reporte resumen
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = self.results_dir / f"summary_report_{timestamp}.json"
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✅ Reporte resumen guardado: {summary_file}")
        return str(summary_file)

def interactive_menu():
    """Menú interactivo para seleccionar tipo de análisis"""
    
    print("\n🎯 ANÁLISIS DE PROMPT ENGINEERING PARA CVRP")
    print("=" * 45)
    print("\nSeleccione el tipo de análisis que desea realizar:")
    print("\n1. 🚀 Análisis Completo - Todas las estrategias (más lento)")
    print("2. 🔍 Comparación - Prompt actual vs optimizados")
    print("3. ⚡ Análisis Rápido - Estrategias clave (más rápido)")
    print("4. 🎯 Análisis Personalizado - Seleccionar estrategias")
    print("5. 📊 Ejecutar todos los análisis y generar resumen")
    print("6. ❌ Salir")
    
    while True:
        try:
            choice = input("\nIngrese su opción (1-6): ").strip()
            
            if choice in ['1', '2', '3', '4', '5', '6']:
                return int(choice)
            else:
                print("❌ Opción inválida. Ingrese un número del 1 al 6.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Análisis cancelado por el usuario.")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Error: {e}")

def select_custom_strategies():
    """Permite seleccionar estrategias específicas para análisis personalizado"""
    
    strategies = list(PromptStrategy)
    
    print("\n🎯 SELECCIÓN DE ESTRATEGIAS PERSONALIZADAS")
    print("=" * 40)
    print("\nEstrategias disponibles:")
    
    for i, strategy in enumerate(strategies, 1):
        print(f"{i}. {strategy.value.replace('_', ' ').title()}")
    
    print(f"{len(strategies) + 1}. Seleccionar todas")
    
    selected = []
    
    while True:
        try:
            choice = input(f"\nSeleccione estrategias (1-{len(strategies)+1}, separadas por comas): ").strip()
            
            if choice == str(len(strategies) + 1):
                return strategies
            
            indices = [int(x.strip()) for x in choice.split(',')]
            
            if all(1 <= i <= len(strategies) for i in indices):
                return [strategies[i-1] for i in indices]
            else:
                print(f"❌ Números inválidos. Use números del 1 al {len(strategies)}.")
                
        except ValueError:
            print("❌ Formato inválido. Use números separados por comas (ej: 1,3,5).")
        except KeyboardInterrupt:
            print("\n\n👋 Selección cancelada.")
            return []

def main():
    """Función principal del script"""
    
    # Verificar que los módulos se puedan importar
    try:
        orchestrator = PromptAnalysisOrchestrator()
    except Exception as e:
        logger.error(f"Error inicializando el sistema: {e}")
        sys.exit(1)
    
    # Manejar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Análisis de Prompt Engineering para CVRP')
    parser.add_argument('--mode', choices=['complete', 'comparison', 'quick', 'custom', 'all'],
                       help='Modo de análisis a ejecutar')
    parser.add_argument('--non-interactive', action='store_true',
                       help='Ejecutar en modo no interactivo')
    
    args = parser.parse_args()
    
    executed_analyses = []
    
    try:
        if args.non_interactive and args.mode:
            # Modo no interactivo
            if args.mode == 'complete':
                result = orchestrator.run_complete_analysis()
                executed_analyses.append(result)
            elif args.mode == 'comparison':
                result = orchestrator.run_comparison_analysis()
                executed_analyses.append(result)
            elif args.mode == 'quick':
                result = orchestrator.run_quick_analysis()
                executed_analyses.append(result)
            elif args.mode == 'all':
                print("🔄 Ejecutando todos los análisis...")
                executed_analyses.append(orchestrator.run_complete_analysis())
                executed_analyses.append(orchestrator.run_comparison_analysis())
                executed_analyses.append(orchestrator.run_quick_analysis())
        else:
            # Modo interactivo
            while True:
                choice = interactive_menu()
                
                if choice == 1:
                    result = orchestrator.run_complete_analysis()
                    executed_analyses.append(result)
                    
                elif choice == 2:
                    result = orchestrator.run_comparison_analysis()
                    executed_analyses.append(result)
                    
                elif choice == 3:
                    result = orchestrator.run_quick_analysis()
                    executed_analyses.append(result)
                    
                elif choice == 4:
                    strategies = select_custom_strategies()
                    if strategies:
                        result = orchestrator.run_custom_analysis(strategies)
                        executed_analyses.append(result)
                    else:
                        print("❌ No se seleccionaron estrategias.")
                        
                elif choice == 5:
                    print("🔄 Ejecutando todos los análisis disponibles...")
                    executed_analyses.append(orchestrator.run_complete_analysis())
                    executed_analyses.append(orchestrator.run_comparison_analysis())
                    executed_analyses.append(orchestrator.run_quick_analysis())
                    break
                    
                elif choice == 6:
                    break
                
                # Preguntar si quiere continuar
                if choice != 5:
                    continue_choice = input("\n¿Desea realizar otro análisis? (s/n): ").strip().lower()
                    if continue_choice not in ['s', 'sí', 'si', 'y', 'yes']:
                        break
        
        # Generar reporte resumen si se ejecutaron múltiples análisis
        if len(executed_analyses) > 1:
            print("\n📋 Generando reporte resumen de todos los análisis...")
            summary_path = orchestrator.generate_summary_report(executed_analyses)
            print(f"✅ Reporte resumen disponible en: {summary_path}")
        
        print("\n🎉 ¡Análisis completado exitosamente!")
        print("\n📂 Todos los archivos se han guardado en:")
        print(f"   📊 Análisis generales: {orchestrator.results_dir}")
        print(f"   🔍 Comparaciones: {orchestrator.comparison_dir}")
        
    except KeyboardInterrupt:
        print("\n\n👋 Análisis interrumpido por el usuario.")
    except Exception as e:
        logger.error(f"Error durante la ejecución: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
