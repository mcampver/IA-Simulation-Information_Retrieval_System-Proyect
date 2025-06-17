"""
Visualización del Grafo de Conocimiento Climático
Genera una representación visual del knowledge graph para el sistema de rutas logísticas
"""

import json
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.patches import FancyBboxPatch
import seaborn as sns
from typing import Dict, List, Tuple
import os

class WeatherKnowledgeGraphVisualizer:
    def __init__(self, json_file_path: str):
        """
        Inicializa el visualizador del grafo de conocimiento
        
        Args:
            json_file_path: Ruta al archivo JSON del grafo de conocimiento
        """
        self.json_file_path = json_file_path
        self.graph = nx.DiGraph()
        self.entity_types = {}
        self.load_knowledge_graph()
        
        # Paleta de colores para diferentes tipos de entidades
        self.color_palette = {
            'weather_condition': '#3498db',  # Azul para condiciones climáticas
            'transport_impact': '#e74c3c',  # Rojo para impactos de transporte
            'road_type': '#2ecc71',         # Verde para tipos de carretera
            'vehicle_type': '#f39c12',      # Naranja para tipos de vehículo
            'surface_type': '#9b59b6',      # Púrpura para tipos de superficie
            'transport_factor': '#f1c40f'   # Amarillo para factores de transporte
        }
        
        # Configuración de estilo
        plt.style.use('seaborn-v0_8-whitegrid')
        sns.set_palette("husl")
    
    def load_knowledge_graph(self):
        """Carga el grafo de conocimiento desde el archivo JSON"""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Agregar nodos (entidades)
            for entity in data['entities']:
                self.graph.add_node(
                    entity['id'],
                    name=entity['name'],
                    type=entity['type'],
                    properties=entity.get('properties', {})
                )
                self.entity_types[entity['id']] = entity['type']
            
            # Agregar aristas (relaciones)
            for relation in data['relations']:                self.graph.add_edge(
                    relation['source'],
                    relation['target'],
                    relation_type=relation['relation_type'],
                    weight=relation['weight'],
                    confidence=relation.get('properties', {}).get('confidence', 1.0)
                )
                
            print(f"Grafo cargado: {self.graph.number_of_nodes()} nodos, {self.graph.number_of_edges()} aristas")
            
        except FileNotFoundError:
            print(f"Error: No se pudo encontrar el archivo {self.json_file_path}")
            raise
        except json.JSONDecodeError as e:
            print(f"Error al decodificar JSON: {e}")
            raise
    
    def create_hierarchical_layout(self) -> Dict[str, Tuple[float, float]]:
        """
        Crea un layout jerárquico del grafo basado en los tipos de entidades
        """
        # Separar nodos por tipo para el grafo extendido
        weather_nodes = [n for n, d in self.graph.nodes(data=True) if d['type'] == 'weather_condition']
        road_nodes = [n for n, d in self.graph.nodes(data=True) if d['type'] == 'road_type']
        surface_nodes = [n for n, d in self.graph.nodes(data=True) if d['type'] == 'surface_type']
        factor_nodes = [n for n, d in self.graph.nodes(data=True) if d['type'] == 'transport_factor']
        impact_nodes = [n for n, d in self.graph.nodes(data=True) if d['type'] == 'transport_impact']
        vehicle_nodes = [n for n, d in self.graph.nodes(data=True) if d['type'] == 'vehicle_type']
        
        pos = {}
        
        # Layout en columnas para mejor organización
        # Columna 1: Condiciones climáticas (izquierda)
        if weather_nodes:
            y_positions_weather = np.linspace(1, 0, len(weather_nodes))
            for i, node in enumerate(weather_nodes):
                pos[node] = (0, y_positions_weather[i])
        
        # Columna 2: Tipos de carretera
        if road_nodes:
            y_positions_road = np.linspace(1, 0, len(road_nodes))
            for i, node in enumerate(road_nodes):
                pos[node] = (1, y_positions_road[i])
        
        # Columna 3: Tipos de superficie
        if surface_nodes:
            y_positions_surface = np.linspace(1, 0, len(surface_nodes))
            for i, node in enumerate(surface_nodes):
                pos[node] = (2, y_positions_surface[i])
        
        # Columna 4: Factores de transporte
        if factor_nodes:
            y_positions_factor = np.linspace(1, 0, len(factor_nodes))
            for i, node in enumerate(factor_nodes):
                pos[node] = (3, y_positions_factor[i])
        
        # Columna 5: Impactos de transporte (derecha)
        if impact_nodes:
            y_positions_impact = np.linspace(1, 0, len(impact_nodes))
            for i, node in enumerate(impact_nodes):
                pos[node] = (4, y_positions_impact[i])
        
        # Columna 6: Tipos de vehículo (si existen)
        if vehicle_nodes:
            y_positions_vehicle = np.linspace(1, 0, len(vehicle_nodes))
            for i, node in enumerate(vehicle_nodes):
                pos[node] = (5, y_positions_vehicle[i])
        
        return pos
    
    def create_circular_layout(self) -> Dict[str, Tuple[float, float]]:
        """Crea un layout circular agrupado por tipos"""
        pos = {}
        
        # Obtener tipos únicos
        types = list(set(self.entity_types.values()))
        
        # Ángulos para cada tipo
        type_angles = np.linspace(0, 2*np.pi, len(types), endpoint=False)
        
        for i, entity_type in enumerate(types):
            # Nodos de este tipo
            nodes_of_type = [n for n, t in self.entity_types.items() if t == entity_type]
            
            # Radio y ángulos para nodos de este tipo
            base_angle = type_angles[i]
            node_angles = np.linspace(
                base_angle - 0.3, 
                base_angle + 0.3, 
                len(nodes_of_type)
            )
            radius = 2 if entity_type == 'weather_condition' else 1.5
            
            for j, node in enumerate(nodes_of_type):
                x = radius * np.cos(node_angles[j])
                y = radius * np.sin(node_angles[j])
                pos[node] = (x, y)
        
        return pos
    
    def visualize_basic_graph(self, layout_type='hierarchical', save_path=None, title=None):
        """
        Crea una visualización básica del grafo de conocimiento
        
        Args:
            layout_type: 'hierarchical', 'circular', 'spring'
            save_path: Ruta donde guardar la imagen (opcional)
            title: Título personalizado para el gráfico (opcional)
        """
        plt.figure(figsize=(16, 12))
        
        # Seleccionar layout
        if layout_type == 'hierarchical':
            pos = self.create_hierarchical_layout()
        elif layout_type == 'circular':
            pos = self.create_circular_layout()
        else:
            pos = nx.spring_layout(self.graph, k=3, iterations=50)
        
        # Colores de nodos basados en tipo
        node_colors = [self.color_palette.get(self.entity_types[node], '#95a5a6') 
                      for node in self.graph.nodes()]
        
        # Tamaños de nodos basados en grado
        node_sizes = [300 + 100 * self.graph.degree(node) for node in self.graph.nodes()]
        
        # Dibujar nodos
        nx.draw_networkx_nodes(
            self.graph, pos,
            node_color=node_colors,
            node_size=node_sizes,
            alpha=0.8,
            edgecolors='black',
            linewidths=1
        )
        
        # Dibujar aristas con grosor basado en peso
        edges = self.graph.edges(data=True)
        edge_weights = [d['weight'] * 3 for _, _, d in edges]
        edge_colors = [d.get('confidence', 0.5) for _, _, d in edges]
        
        nx.draw_networkx_edges(
            self.graph, pos,
            width=edge_weights,
            alpha=0.6,
            edge_color=edge_colors,
            edge_cmap=plt.cm.Reds,
            arrows=True,
            arrowsize=20,
            arrowstyle='->'
        )
        
        # Etiquetas de nodos (nombres cortos)
        labels = {node: data['name'][:15] + ('...' if len(data['name']) > 15 else '') 
                 for node, data in self.graph.nodes(data=True)}
        
        nx.draw_networkx_labels(
            self.graph, pos,
            labels=labels,
            font_size=8,
            font_weight='bold',
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8)
        )
        
        # Leyenda
        legend_elements = [
            plt.Line2D([0], [0], marker='o', color='w', 
                      markerfacecolor=color, markersize=15, alpha=0.8,
                      label=entity_type.replace('_', ' ').title())
            for entity_type, color in self.color_palette.items()
            if entity_type in self.entity_types.values()
        ]
        
        plt.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0, 1))
        
        plt.title("Grafo de Conocimiento Climático - Sistema de Rutas Logísticas", 
                 fontsize=16, fontweight='bold', pad=20)
        plt.axis('off')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            print(f"Gráfico guardado en: {save_path}")
        
        plt.show()
    
    def visualize_detailed_graph(self, save_path=None):
        """
        Crea una visualización detallada con información adicional
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
        
        # Gráfico principal
        pos = self.create_hierarchical_layout()
        
        # Colores y tamaños
        node_colors = [self.color_palette.get(self.entity_types[node], '#95a5a6') 
                      for node in self.graph.nodes()]
        node_sizes = [400 + 150 * self.graph.degree(node) for node in self.graph.nodes()]
        
        # Dibujar en el primer subplot
        nx.draw_networkx_nodes(
            self.graph, pos, ax=ax1,
            node_color=node_colors,
            node_size=node_sizes,
            alpha=0.9,
            edgecolors='black',
            linewidths=2
        )
        
        # Aristas con información de peso
        edges = self.graph.edges(data=True)
        edge_weights = [d['weight'] * 4 for _, _, d in edges]
        edge_colors = [d.get('confidence', 0.5) for _, _, d in edges]
        
        nx.draw_networkx_edges(
            self.graph, pos, ax=ax1,
            width=edge_weights,
            alpha=0.7,
            edge_color=edge_colors,
            edge_cmap=plt.cm.Reds,
            arrows=True,
            arrowsize=25,
            arrowstyle='->'
        )
        
        # Etiquetas mejoradas
        labels = {node: data['name'] for node, data in self.graph.nodes(data=True)}
        nx.draw_networkx_labels(
            self.graph, pos, ax=ax1,
            labels=labels,
            font_size=9,
            font_weight='bold',
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.9)
        )
        
        ax1.set_title("Grafo de Conocimiento Climático", fontsize=14, fontweight='bold')
        ax1.axis('off')
        
        # Gráfico de estadísticas en el segundo subplot
        self.plot_statistics(ax2)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            print(f"Gráfico detallado guardado en: {save_path}")
        
        plt.show()
    
    def plot_statistics(self, ax):
        """Grafica estadísticas del grafo"""
        # Contar tipos de entidades
        type_counts = {}
        for entity_type in self.entity_types.values():
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
        
        # Gráfico de barras
        types = list(type_counts.keys())
        counts = list(type_counts.values())
        colors = [self.color_palette.get(t, '#95a5a6') for t in types]
        
        bars = ax.bar(range(len(types)), counts, color=colors, alpha=0.8, edgecolor='black')
        
        # Etiquetas
        ax.set_xticks(range(len(types)))
        ax.set_xticklabels([t.replace('_', ' ').title() for t in types], rotation=45)
        ax.set_ylabel('Número de Entidades')
        ax.set_title('Distribución de Tipos de Entidades', fontweight='bold')
        
        # Agregar valores en las barras
        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                   f'{count}', ha='center', va='bottom', fontweight='bold')
        
        ax.grid(True, alpha=0.3)
    
    def create_matrix_visualization(self, save_path=None):
        """Crea una visualización de matriz de adyacencia"""
        # Crear matriz de adyacencia
        nodes = list(self.graph.nodes())
        n = len(nodes)
        matrix = np.zeros((n, n))
        
        for i, source in enumerate(nodes):
            for j, target in enumerate(nodes):
                if self.graph.has_edge(source, target):
                    matrix[i, j] = self.graph[source][target]['weight']
        
        plt.figure(figsize=(12, 10))
        
        # Crear heatmap
        sns.heatmap(matrix, 
                   xticklabels=[self.graph.nodes[n]['name'][:10] for n in nodes],
                   yticklabels=[self.graph.nodes[n]['name'][:10] for n in nodes],
                   annot=True, 
                   fmt='.2f',
                   cmap='Reds',
                   square=True,
                   linewidths=0.5)
        
        plt.title("Matriz de Adyacencia - Pesos de Relaciones", 
                 fontsize=14, fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        plt.tight_layout()
        
        if save_path:
            matrix_path = save_path.replace('.png', '_matrix.png')
            plt.savefig(matrix_path, dpi=300, bbox_inches='tight')
            print(f"Matriz guardada en: {matrix_path}")
        
        plt.show()
    
    def generate_all_visualizations(self, output_dir='knowledge_graph_visualizations'):
        """Genera todas las visualizaciones del grafo de conocimiento"""
        os.makedirs(output_dir, exist_ok=True)
        
        print("Generando visualizaciones del grafo de conocimiento...")
        
        # Visualización básica jerárquica
        self.visualize_basic_graph(
            layout_type='hierarchical',
            save_path=os.path.join(output_dir, 'knowledge_graph_hierarchical.png')
        )
        
        # Visualización circular
        self.visualize_basic_graph(
            layout_type='circular',
            save_path=os.path.join(output_dir, 'knowledge_graph_circular.png')
        )
        
        # Visualización detallada
        self.visualize_detailed_graph(
            save_path=os.path.join(output_dir, 'knowledge_graph_detailed.png')
        )
        
        # Matriz de adyacencia
        self.create_matrix_visualization(
            save_path=os.path.join(output_dir, 'knowledge_graph_matrix.png')
        )
        
        print(f"Todas las visualizaciones guardadas en: {output_dir}")

def main():
    """Función principal para generar las visualizaciones"""
    # Ruta al archivo del grafo de conocimiento
    kg_file = "weather_knowledge_graph.json"
    
    # Verificar que existe el archivo
    if not os.path.exists(kg_file):
        print(f"Error: No se encontró el archivo {kg_file}")
        return
    
    # Crear visualizador
    visualizer = WeatherKnowledgeGraphVisualizer(kg_file)
    
    # Generar todas las visualizaciones
    visualizer.generate_all_visualizations()
    
    # También generar una visualización interactiva simple
    print("\nMostrando visualización interactiva básica...")
    visualizer.visualize_basic_graph(layout_type='hierarchical')

def visualize_extended_knowledge_graph():
    """Función específica para visualizar el grafo de conocimiento extendido"""
    # Ruta al archivo del grafo extendido
    extended_kg_file = "extended_knowledge_graph.json"
    
    # Verificar que existe el archivo
    if not os.path.exists(extended_kg_file):
        print(f"Error: No se encontró el archivo {extended_kg_file}")
        print("Ejecuta primero: python extended_knowledge_graph.py")
        return
    
    # Crear visualizador para el grafo extendido
    print("Cargando grafo de conocimiento extendido...")
    visualizer = WeatherKnowledgeGraphVisualizer(extended_kg_file)
    
    # Crear directorio para visualizaciones extendidas
    output_dir = "extended_knowledge_graph_visualizations"
    os.makedirs(output_dir, exist_ok=True)
    
    print("Generando visualizaciones del grafo extendido...")
    
    # Visualización jerárquica extendida
    plt.figure(figsize=(16, 12))
    visualizer.visualize_basic_graph(
        title='Grafo de Conocimiento Extendido - Optimización de Rutas\n(Incluye tipos de calles, superficies y factores de transporte)',
        layout_type='hierarchical',
        save_path=os.path.join(output_dir, 'extended_knowledge_graph_hierarchical.png')
    )
    
    # Visualización circular extendida
    plt.figure(figsize=(14, 14))
    visualizer.visualize_basic_graph(
        title='Grafo de Conocimiento Extendido - Vista Circular',
        layout_type='circular',
        save_path=os.path.join(output_dir, 'extended_knowledge_graph_circular.png')
    )
    
    # Visualización detallada con todas las etiquetas
    visualizer.visualize_detailed_graph(
        save_path=os.path.join(output_dir, 'extended_knowledge_graph_detailed.png')
    )
    
    # Matriz de relaciones
    visualizer.create_matrix_visualization(
        save_path=os.path.join(output_dir, 'extended_knowledge_graph_matrix.png')
    )
    
    print(f"\nTodas las visualizaciones del grafo extendido guardadas en: {output_dir}")
    
    # Mostrar estadísticas del grafo extendido
    print("\n=== ESTADÍSTICAS DEL GRAFO EXTENDIDO ===")
    print(f"Nodos totales: {visualizer.graph.number_of_nodes()}")
    print(f"Relaciones totales: {visualizer.graph.number_of_edges()}")
    
    # Contar entidades por tipo
    entity_types = {}
    for node, data in visualizer.graph.nodes(data=True):
        entity_type = data.get('type', 'unknown')
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
    
    print("\nDistribución de entidades:")
    for entity_type, count in sorted(entity_types.items()):
        print(f"  {entity_type}: {count}")
    
    # Contar relaciones por tipo
    relation_types = {}
    for _, _, data in visualizer.graph.edges(data=True):
        relation_type = data.get('relation_type', 'unknown')
        relation_types[relation_type] = relation_types.get(relation_type, 0) + 1
    
    print("\nTipos de relaciones:")
    for relation_type, count in sorted(relation_types.items()):
        print(f"  {relation_type}: {count}")

if __name__ == "__main__":
    # Ejecutar ambas visualizaciones
    print("=== VISUALIZACIÓN DEL GRAFO CLIMÁTICO ORIGINAL ===")
    main()
    
    print("\n" + "="*60)
    print("=== VISUALIZACIÓN DEL GRAFO EXTENDIDO ===")
    visualize_extended_knowledge_graph()
