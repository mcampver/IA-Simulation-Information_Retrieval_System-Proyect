"""
Visualizador Simple para el Grafo de Conocimiento Extendido
Crea visualizaciones del grafo que incluye tipos de calles, superficies y factores
"""

import json
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import seaborn as sns
import os

def load_knowledge_graph(json_file_path):
    """Carga el grafo de conocimiento desde un archivo JSON"""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    G = nx.DiGraph()
    entity_types = {}
    
    # Agregar nodos
    for entity in data['entities']:
        G.add_node(
            entity['id'],
            name=entity['name'],
            type=entity['type'],
            properties=entity.get('properties', {})
        )
        entity_types[entity['id']] = entity['type']
    
    # Agregar aristas
    for relation in data['relations']:
        G.add_edge(
            relation['source'],
            relation['target'],
            relation_type=relation['relation_type'],
            weight=relation['weight'],
            confidence=relation.get('properties', {}).get('confidence', 1.0)
        )
    
    return G, entity_types

def create_hierarchical_layout(G, entity_types):
    """Crea un layout jerárquico por tipos de entidades"""
    pos = {}
    
    # Separar nodos por tipo
    node_types = {
        'weather_condition': [],
        'road_type': [],
        'surface_type': [],
        'transport_factor': [],
        'transport_impact': [],
        'vehicle_type': []
    }
    
    for node, node_type in entity_types.items():
        if node_type in node_types:
            node_types[node_type].append(node)
    
    # Posicionar en columnas
    x_positions = [0, 1, 2, 3, 4, 5]
    type_names = list(node_types.keys())
    
    for i, type_name in enumerate(type_names):
        nodes = node_types[type_name]
        if nodes:
            y_positions = np.linspace(1, 0, len(nodes))
            for j, node in enumerate(nodes):
                pos[node] = (x_positions[i], y_positions[j])
    
    return pos

def create_circular_layout(G, entity_types):
    """Crea un layout circular agrupado por tipos"""
    pos = {}
    
    # Obtener tipos únicos
    types = list(set(entity_types.values()))
    type_angles = np.linspace(0, 2*np.pi, len(types), endpoint=False)
    
    for i, entity_type in enumerate(types):
        nodes_of_type = [n for n, t in entity_types.items() if t == entity_type]
        
        base_angle = type_angles[i]
        node_angles = np.linspace(
            base_angle - 0.4, 
            base_angle + 0.4, 
            len(nodes_of_type)
        )
        
        radius = 3 if entity_type == 'weather_condition' else 2
        
        for j, node in enumerate(nodes_of_type):
            x = radius * np.cos(node_angles[j])
            y = radius * np.sin(node_angles[j])
            pos[node] = (x, y)
    
    return pos

def visualize_extended_graph(json_file_path, output_dir="extended_visualizations"):
    """Crea visualizaciones del grafo extendido"""
    
    # Cargar el grafo
    G, entity_types = load_knowledge_graph(json_file_path)
    
    # Crear directorio de salida
    os.makedirs(output_dir, exist_ok=True)
    
    # Paleta de colores
    color_palette = {
        'weather_condition': '#3498db',  # Azul
        'road_type': '#2ecc71',         # Verde
        'surface_type': '#9b59b6',      # Púrpura
        'transport_factor': '#f1c40f',  # Amarillo
        'transport_impact': '#e74c3c',  # Rojo
        'vehicle_type': '#f39c12'       # Naranja
    }
    
    # === VISUALIZACIÓN JERÁRQUICA ===
    plt.figure(figsize=(18, 12))
    pos_hier = create_hierarchical_layout(G, entity_types)
    
    # Colores de nodos
    node_colors = [color_palette.get(entity_types[node], '#95a5a6') for node in G.nodes()]
    
    # Dibujar el grafo
    nx.draw_networkx_nodes(G, pos_hier, node_color=node_colors, 
                          node_size=800, alpha=0.8)
    nx.draw_networkx_labels(G, pos_hier, font_size=8, font_weight='bold')
    nx.draw_networkx_edges(G, pos_hier, edge_color='gray', 
                          alpha=0.6, arrows=True, arrowsize=15)
    
    plt.title('Grafo de Conocimiento Extendido - Optimización de Rutas\\n'
              'Incluye tipos de calles, superficies y factores de transporte', 
              fontsize=16, fontweight='bold')
    
    # Crear leyenda
    legend_elements = []
    for entity_type, color in color_palette.items():
        if any(entity_types[node] == entity_type for node in G.nodes()):
            legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', 
                                            markerfacecolor=color, markersize=10, 
                                            label=entity_type.replace('_', ' ').title()))
    
    plt.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1, 1))
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'extended_graph_hierarchical.png'), 
                dpi=300, bbox_inches='tight')
    plt.close()
    
    # === VISUALIZACIÓN CIRCULAR ===
    plt.figure(figsize=(14, 14))
    pos_circ = create_circular_layout(G, entity_types)
    
    nx.draw_networkx_nodes(G, pos_circ, node_color=node_colors, 
                          node_size=600, alpha=0.8)
    nx.draw_networkx_labels(G, pos_circ, font_size=7, font_weight='bold')
    nx.draw_networkx_edges(G, pos_circ, edge_color='gray', 
                          alpha=0.5, arrows=True, arrowsize=12)
    
    plt.title('Grafo de Conocimiento Extendido - Vista Circular', 
              fontsize=16, fontweight='bold')
    plt.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1, 1))
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'extended_graph_circular.png'), 
                dpi=300, bbox_inches='tight')
    plt.close()
    
    # === ANÁLISIS DE CONECTIVIDAD POR TIPO ===
    plt.figure(figsize=(12, 8))
    
    # Contar conexiones por tipo
    connection_counts = {}
    for entity_type in color_palette.keys():
        nodes_of_type = [n for n in G.nodes() if entity_types[n] == entity_type]
        total_connections = sum(G.degree(node) for node in nodes_of_type)
        connection_counts[entity_type] = total_connections
    
    types = list(connection_counts.keys())
    counts = list(connection_counts.values())
    colors = [color_palette[t] for t in types]
    
    plt.bar(range(len(types)), counts, color=colors, alpha=0.8)
    plt.xlabel('Tipo de Entidad')
    plt.ylabel('Total de Conexiones')
    plt.title('Conectividad por Tipo de Entidad')
    plt.xticks(range(len(types)), [t.replace('_', ' ').title() for t in types], 
               rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'connectivity_analysis.png'), 
                dpi=300, bbox_inches='tight')
    plt.close()
    
    # === MATRIZ DE RELACIONES ===
    plt.figure(figsize=(10, 8))
    
    # Crear matriz de adyacencia por tipos
    type_list = list(color_palette.keys())
    matrix = np.zeros((len(type_list), len(type_list)))
    
    for source, target in G.edges():
        source_type = entity_types[source]
        target_type = entity_types[target]
        if source_type in type_list and target_type in type_list:
            i = type_list.index(source_type)
            j = type_list.index(target_type)
            matrix[i][j] += 1
    
    # Crear heatmap
    sns.heatmap(matrix, 
                xticklabels=[t.replace('_', ' ').title() for t in type_list],
                yticklabels=[t.replace('_', ' ').title() for t in type_list],
                annot=True, fmt='g', cmap='Blues')
    plt.title('Matriz de Relaciones entre Tipos de Entidades')
    plt.xlabel('Tipo de Destino')
    plt.ylabel('Tipo de Origen')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'relations_matrix.png'), 
                dpi=300, bbox_inches='tight')
    plt.close()
    
    # Mostrar estadísticas
    print(f"\\n=== ESTADÍSTICAS DEL GRAFO EXTENDIDO ===")
    print(f"Nodos totales: {G.number_of_nodes()}")
    print(f"Relaciones totales: {G.number_of_edges()}")
    
    print("\\nDistribución de entidades:")
    entity_counts = {}
    for entity_type in entity_types.values():
        entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
    
    for entity_type, count in sorted(entity_counts.items()):
        print(f"  {entity_type.replace('_', ' ').title()}: {count}")
    
    print(f"\\nTodas las visualizaciones guardadas en: {output_dir}")
    
    return G, entity_types

if __name__ == "__main__":
    # Verificar que existe el archivo del grafo extendido
    extended_file = "extended_knowledge_graph.json"
    
    if not os.path.exists(extended_file):
        print(f"Error: No se encontró {extended_file}")
        print("Ejecuta primero: python extended_knowledge_graph.py")
    else:
        print("Generando visualizaciones del grafo de conocimiento extendido...")
        G, entity_types = visualize_extended_graph(extended_file)
        
        print("\\n¡Visualizaciones completadas exitosamente!")
