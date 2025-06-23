import sys
import os
import random
import networkx as nx
import numpy as np
import time
from pathlib import Path

# Configurar correctamente las rutas de importación
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.append(str(PROJECT_ROOT))  # Ruta raíz del proyecto
sys.path.append(str(PROJECT_ROOT / "src"))  # Carpeta src
sys.path.append(str(PROJECT_ROOT / "src/traffic_events"))  # Para traffic_events_analyzer
sys.path.append(str(PROJECT_ROOT / "src/crawler"))  # Para traffic_events_crawler
sys.path.append(str(PROJECT_ROOT / "src/metaheuristic/ag_solver"))
sys.path.append(str(PROJECT_ROOT / "src/metaheuristic/vns_solver"))
sys.path.append(str(PROJECT_ROOT / "src/metaheuristic/sa_solver"))
sys.path.append(str(PROJECT_ROOT / "src/metaheuristic/ts_solver"))

# Ahora importamos los módulos después de configurar las rutas
import matplotlib.pyplot as plt
import folium
from folium.plugins import HeatMap
from tqdm import tqdm

from src.optimized_route import optimize_delivery_routes
from src.vehicle import initialize_vehicles, update_vehicle_positions
from server import load_streets

def generar_rutas_aleatorias(street_graph, num_rutas, puntos_por_ruta, seed=42):
    """Genera rutas aleatorias con puntos conectados en el grafo"""
    random.seed(seed)
    rutas = []
    all_nodes = list(street_graph.nodes())
    
    for _ in tqdm(range(num_rutas), desc="Generando rutas aleatorias"):
        # Seleccionar punto de inicio aleatorio que tenga buena conectividad
        candidatos = [n for n in all_nodes if len(list(street_graph.neighbors(n))) > 2]
        if not candidatos:
            candidatos = all_nodes
        
        start_point = random.choice(candidatos)
        
        # Intentar encontrar puntos objetivo alcanzables
        targets = []
        attempts = 0
        while len(targets) < puntos_por_ruta and attempts < 50:
            candidate = random.choice(all_nodes)
            attempts += 1
            
            # Evitar duplicados y asegurar conectividad
            if (candidate != start_point and 
                candidate not in targets and 
                nx.has_path(street_graph, start_point, candidate)):
                targets.append(candidate)
        
        if targets:  # Solo añadir ruta si tiene al menos un punto objetivo
            rutas.append((start_point, targets))
    
    print(f"✅ Generadas {len(rutas)} rutas aleatorias con {puntos_por_ruta} puntos cada una")
    return rutas

def simular_recorrido(street_graph, rutas):
    """Simula el recorrido de las rutas y devuelve la densidad de tráfico"""
    # Inicializar densidad de tráfico
    densidad = {}
    for u, v in street_graph.edges():
        densidad[(u, v)] = 0
    
    # Recorrer cada ruta y acumular densidad
    for start_point, targets in tqdm(rutas, desc="Simulando recorridos"):
        for target in targets:
            try:
                # Encontrar camino más corto entre puntos
                path = nx.shortest_path(street_graph, start_point, target, weight='weight')
                
                # Incrementar densidad en cada arista del camino
                for i in range(len(path) - 1):
                    edge = (path[i], path[i+1])
                    if edge in densidad:
                        densidad[edge] += 1
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                print(f"⚠️ No hay camino entre {start_point} y {target}")
    
    return densidad

def aplicar_optimizacion(street_graph, rutas, solver='vns_solver'):
    """Aplica optimización a las rutas y devuelve las rutas optimizadas"""
    rutas_optimizadas = []
    total_cost_original = 0
    total_cost_optimized = 0
    
    for start_point, targets in tqdm(rutas, desc=f"Optimizando con {solver}"):
        # Calcular costo de ruta original
        original_cost = 0
        for target in targets:
            try:
                cost = nx.shortest_path_length(street_graph, start_point, target, weight='weight')
                original_cost += cost
            except:
                pass
        
        # Optimizar ruta
        routes, cost = optimize_delivery_routes(
            street_graph=street_graph,
            start_point=start_point,
            target_points=targets,
            num_trucks=1,
            truck_capacities=[100],
            target_demands=[1] * len(targets),
            use_weather_impact=False,
            use_traffic_impact=False,
            solver=solver
        )
        
        if routes:
            rutas_optimizadas.append((start_point, routes[0]))
            total_cost_optimized += cost
            total_cost_original += original_cost
    
    # Calcular mejora
    if total_cost_original > 0:
        mejora = (1 - total_cost_optimized / total_cost_original) * 100
        print(f"✅ Optimización con {solver} completada. Mejora: {mejora:.2f}%")
    else:
        print(f"✅ Optimización con {solver} completada.")
    
    return rutas_optimizadas

def simular_recorrido_optimizado(street_graph, rutas_optimizadas):
    """Simula el recorrido de rutas optimizadas y devuelve la densidad"""
    densidad = {}
    for u, v in street_graph.edges():
        densidad[(u, v)] = 0
    
    for start_point, route in tqdm(rutas_optimizadas, desc="Simulando rutas optimizadas"):
        for i in range(len(route) - 1):
            edge = (route[i], route[i+1])
            if edge in densidad:
                densidad[edge] += 1
    
    return densidad

def generar_mapa_calor(street_graph, densidad, nombre_archivo, titulo):
    """Genera un mapa de calor interactivo usando folium"""
    # Normalizar densidad para visualización
    valores = list(densidad.values())
    if valores:
        max_densidad = max(valores)
        densidad_norm = {k: v/max_densidad for k, v in densidad.items()}
    else:
        densidad_norm = densidad
    
    # Crear puntos para el mapa de calor
    puntos_calor = []
    for (u, v), valor in densidad_norm.items():
        if valor > 0:
            # Obtener coordenadas
            try:
                u_data = street_graph.nodes[u]
                v_data = street_graph.nodes[v]
                
                # Punto medio de la arista
                lat = (u_data.get('lat', 0) + v_data.get('lat', 0)) / 2
                lon = (u_data.get('lon', 0) + v_data.get('lon', 0)) / 2
                
                puntos_calor.append([lat, lon, valor])
            except:
                pass
    
    # Encontrar centro del mapa (promedio de coordenadas)
    lats = [street_graph.nodes[n].get('lat', 0) for n in street_graph.nodes()]
    lons = [street_graph.nodes[n].get('lon', 0) for n in street_graph.nodes()]
    
    if lats and lons:
        centro = [sum(lats)/len(lats), sum(lons)/len(lons)]
    else:
        centro = [0, 0]  # Fallback
    
    # Crear mapa
    mapa = folium.Map(location=centro, zoom_start=13, tiles='CartoDB positron')
    
    # Añadir título
    folium.TileLayer(
        tiles='CartoDB positron',
        name='Mapa Base',
        overlay=True
    ).add_to(mapa)
    
    # Añadir capa de mapa de calor
    HeatMap(
        puntos_calor,
        radius=15,
        blur=10,
        max_zoom=13,
        gradient={0.2: 'blue', 0.4: 'lime', 0.6: 'yellow', 0.8: 'orange', 1: 'red'}
    ).add_to(mapa)
    
    # Añadir control de capas
    folium.LayerControl().add_to(mapa)
    
    # Guardar mapa
    mapa.save(nombre_archivo)
    print(f"✅ Mapa de calor guardado en {nombre_archivo}")
    
    return nombre_archivo

def generar_mapa_calor_mejorado(street_graph, densidad, rutas, nombre_archivo, titulo, solver=None):
    """Genera un mapa de calor interactivo mejorado usando folium"""
    # Normalizar densidad para visualización
    valores = list(densidad.values())
    if valores:
        max_densidad = max(valores)
        densidad_norm = {k: v/max_densidad for k, v in densidad.items() if v > 0}
    else:
        densidad_norm = {}
    
    # Encontrar centro del mapa (promedio de coordenadas)
    lats = [street_graph.nodes[n].get('lat', 0) for n in street_graph.nodes()]
    lons = [street_graph.nodes[n].get('lon', 0) for n in street_graph.nodes()]
    
    if lats and lons:
        centro = [sum(lats)/len(lats), sum(lons)/len(lons)]
    else:
        centro = [0, 0]  # Fallback
    
    # Crear mapa
    mapa = folium.Map(location=centro, zoom_start=13, tiles='CartoDB positron')
    
    # Añadir título y leyenda
    title_html = f'''
        <div style="position: fixed; 
                    top: 10px; left: 50px; width: 500px; height: 30px; 
                    background-color: white; border-radius: 5px;
                    z-index: 900; font-size: 16px; font-weight: bold;
                    padding: 10px; box-shadow: 0 0 5px rgba(0,0,0,0.3);">
            {titulo}
        </div>
    '''
    mapa.get_root().html.add_child(folium.Element(title_html))
    
    # Crear puntos para el mapa de calor
    puntos_calor = []
    for (u, v), valor in densidad_norm.items():
        try:
            u_data = street_graph.nodes[u]
            v_data = street_graph.nodes[v]
            
            # Punto medio de la arista
            lat = (u_data.get('lat', 0) + v_data.get('lat', 0)) / 2
            lon = (u_data.get('lon', 0) + v_data.get('lon', 0)) / 2
            
            puntos_calor.append([lat, lon, valor])
        except:
            pass
    
    # 1. Grupo de capas para el mapa base
    base_group = folium.FeatureGroup(name='Mapas Base')
    folium.TileLayer('CartoDB positron', name='Claro').add_to(base_group)
    folium.TileLayer('CartoDB dark_matter', name='Oscuro').add_to(base_group)
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(base_group)
    base_group.add_to(mapa)
    
    # 2. Grupo para el mapa de calor
    heat_group = folium.FeatureGroup(name='Mapa de Calor', show=True)
    HeatMap(
        puntos_calor,
        radius=13,  # Ajustado para mejor visualización
        blur=12,
        max_zoom=13,
        gradient={0.2: 'blue', 0.4: 'lime', 0.6: 'yellow', 0.8: 'orange', 1: 'red'},
        min_opacity=0.5,
    ).add_to(heat_group)
    heat_group.add_to(mapa)
    
    # 3. Grupo para rutas individuales (opcional)
    if rutas:
        routes_group = folium.FeatureGroup(name='Rutas Individuales', show=False)
        
        # Crear colores únicos para cada ruta
        colores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        # Añadir cada ruta como una línea en el mapa
        for i, (start_point, targets) in enumerate(rutas):
            color = colores[i % len(colores)]
            
            # Si son rutas optimizadas, los targets ya son la ruta completa
            if solver:
                # Convertir IDs de nodos a coordenadas
                coords = []
                for node_id in targets:
                    try:
                        lat = street_graph.nodes[node_id].get('lat', 0)
                        lon = street_graph.nodes[node_id].get('lon', 0)
                        coords.append((lat, lon))
                    except:
                        pass
                
                # Dibujar la ruta como una línea
                if coords:
                    folium.PolyLine(
                        coords,
                        color=color,
                        weight=3,
                        opacity=0.8,
                        tooltip=f"Ruta {i+1} ({solver})"
                    ).add_to(routes_group)
            else:
                # Para rutas originales, necesitamos calcular los caminos más cortos
                for target in targets:
                    try:
                        path = nx.shortest_path(street_graph, start_point, target, weight='weight')
                        coords = []
                        for node_id in path:
                            lat = street_graph.nodes[node_id].get('lat', 0)
                            lon = street_graph.nodes[node_id].get('lon', 0)
                            coords.append((lat, lon))
                        
                        if coords:
                            folium.PolyLine(
                                coords,
                                color=color,
                                weight=3,
                                opacity=0.8,
                                tooltip=f"Ruta {i+1} (Original)"
                            ).add_to(routes_group)
                    except:
                        pass
        
        routes_group.add_to(mapa)
    
    # 4. Añadir marcadores para puntos de alta densidad
    markers_group = folium.FeatureGroup(name='Puntos Críticos', show=False)
    # Obtener los 10 puntos con mayor densidad
    top_densidad = sorted([(k, v) for k, v in densidad.items() if v > 0], key=lambda x: x[1], reverse=True)[:10]
    
    for (u, v), valor in top_densidad:
        try:
            u_data = street_graph.nodes[u]
            v_data = street_graph.nodes[v]
            
            lat = (u_data.get('lat', 0) + v_data.get('lat', 0)) / 2
            lon = (u_data.get('lon', 0) + v_data.get('lon', 0)) / 2
            
            # Usar valor normalizado para escalar el color
            color = 'red' if valor/max(valores) > 0.7 else 'orange'
            
            folium.CircleMarker(
                location=[lat, lon],
                radius=valor/max(valores) * 15,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                tooltip=f"Densidad: {valor}",
                popup=f"<b>Punto crítico</b><br>Densidad: {valor}<br>Segmento: {u} → {v}"
            ).add_to(markers_group)
        except:
            pass
    
    markers_group.add_to(mapa)
    
    # 5. Añadir mini-estadísticas
    if valores:
        stats_html = f'''
            <div style="position: fixed; 
                        bottom: 50px; right: 10px; width: 200px;
                        background-color: white; border-radius: 5px;
                        z-index: 900; font-size: 12px;
                        padding: 10px; box-shadow: 0 0 5px rgba(0,0,0,0.3);">
                <h4 style="margin-top:0">Estadísticas</h4>
                <p>Máxima densidad: {max(valores)}</p>
                <p>Densidad media: {sum(valores)/len(valores):.2f}</p>
                <p>Aristas transitadas: {sum(1 for v in valores if v > 0)}</p>
                <p>Total aristas: {len(valores)}</p>
                <p>Cobertura: {sum(1 for v in valores if v > 0)/len(valores)*100:.1f}%</p>
            </div>
        '''
        mapa.get_root().html.add_child(folium.Element(stats_html))
    
    # Añadir control de capas
    folium.LayerControl(collapsed=False).add_to(mapa)
    
    # Guardar mapa
    mapa.save(nombre_archivo)
    print(f"✅ Mapa de calor mejorado guardado en {nombre_archivo}")
    
    return nombre_archivo

def generar_mapa_comparativo(street_graph, densidad_original, densidades_optimizadas, resultados_dir):
    """Genera un mapa que compara las densidades de tráfico entre soluciones"""
    # Crear un mapa base
    lats = [street_graph.nodes[n].get('lat', 0) for n in street_graph.nodes()]
    lons = [street_graph.nodes[n].get('lon', 0) for n in street_graph.nodes()]
    
    if lats and lons:
        centro = [sum(lats)/len(lats), sum(lons)/len(lons)]
    else:
        centro = [0, 0]
    
    mapa = folium.Map(location=centro, zoom_start=13, tiles='CartoDB positron')
    
    # Añadir título
    title_html = f'''
        <div style="position: fixed; 
                    top: 10px; left: 50px; width: 500px; height: 30px; 
                    background-color: white; border-radius: 5px;
                    z-index: 900; font-size: 16px; font-weight: bold;
                    padding: 10px; box-shadow: 0 0 5px rgba(0,0,0,0.3);">
            Comparativa de Optimización de Rutas
        </div>
    '''
    mapa.get_root().html.add_child(folium.Element(title_html))
    
    # Calcular diferencia entre densidades para cada solver
    diferencias = {}
    for solver, densidad_opt in densidades_optimizadas.items():
        # Calcular diferencia: valores positivos = mejora, negativos = empeora
        diff = {}
        for edge in street_graph.edges():
            if edge in densidad_original and edge in densidad_opt:
                diff[edge] = densidad_original[edge] - densidad_opt[edge]
        
        diferencias[solver] = diff
    
    # Añadir cada capa de diferencia al mapa
    for solver, diff in diferencias.items():
        # Separar mejoras y empeoramientos
        mejoras = []
        empeoramientos = []
        
        for (u, v), valor in diff.items():
            try:
                u_data = street_graph.nodes[u]
                v_data = street_graph.nodes[v]
                
                lat = (u_data.get('lat', 0) + v_data.get('lat', 0)) / 2
                lon = (u_data.get('lon', 0) + v_data.get('lon', 0)) / 2
                
                if valor > 0:  # Mejora
                    mejoras.append([lat, lon, abs(valor)])
                elif valor < 0:  # Empeoramiento
                    empeoramientos.append([lat, lon, abs(valor)])
            except:
                pass
        
        # Crear grupo para este solver
        solver_group = folium.FeatureGroup(name=f'Comparativa {solver}', show=(solver == list(densidades_optimizadas.keys())[0]))
        
        # Mapa de calor para mejoras (verde)
        if mejoras:
            HeatMap(
                mejoras,
                name=f'Mejoras {solver}',
                radius=15,
                blur=10,
                max_zoom=13,
                gradient={0.2: '#ceffce', 0.4: '#97ff97', 0.6: '#5eff5e', 0.8: '#00cc00', 1: '#009900'},
                min_opacity=0.5
            ).add_to(solver_group)
        
        # Mapa de calor para empeoramientos (rojo)
        if empeoramientos:
            HeatMap(
                empeoramientos,
                name=f'Empeoramientos {solver}',
                radius=15,
                blur=10,
                max_zoom=13,
                gradient={0.2: '#ffcece', 0.4: '#ff9797', 0.6: '#ff5e5e', 0.8: '#cc0000', 1: '#990000'},
                min_opacity=0.5
            ).add_to(solver_group)
        
        solver_group.add_to(mapa)
    
    # Añadir control de capas
    folium.LayerControl(collapsed=False).add_to(mapa)
    
    # Guardar mapa comparativo
    nombre_archivo = resultados_dir / "mapa_comparativo.html"
    mapa.save(nombre_archivo)
    print(f"✅ Mapa comparativo guardado en {nombre_archivo}")
    
    return nombre_archivo

def crear_dashboard_estadistico(densidad_original, densidades_optimizadas, resultados_dir):
    """Genera un dashboard HTML con estadísticas de la optimización"""
    # Calcular estadísticas para cada solver
    estadisticas = {}
    
    # Stats para la densidad original
    valores_orig = list(densidad_original.values())
    aristas_transitadas_orig = sum(1 for v in valores_orig if v > 0)
    max_densidad_orig = max(valores_orig) if valores_orig else 0
    densidad_media_orig = sum(valores_orig)/len(valores_orig) if valores_orig else 0
    
    estadisticas['original'] = {
        'max_densidad': max_densidad_orig,
        'densidad_media': densidad_media_orig,
        'aristas_transitadas': aristas_transitadas_orig,
        'total_aristas': len(valores_orig),
        'cobertura_pct': aristas_transitadas_orig/len(valores_orig)*100 if valores_orig else 0
    }
    
    # Stats para cada solver
    for solver, densidad in densidades_optimizadas.items():
        valores = list(densidad.values())
        aristas_transitadas = sum(1 for v in valores if v > 0)
        
        estadisticas[solver] = {
            'max_densidad': max(valores) if valores else 0,
            'densidad_media': sum(valores)/len(valores) if valores else 0,
            'aristas_transitadas': aristas_transitadas,
            'total_aristas': len(valores),
            'cobertura_pct': aristas_transitadas/len(valores)*100 if valores else 0
        }
    
    # Generar gráficos usando matplotlib
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Estadísticas de Optimización de Rutas', fontsize=16)
    
    # Gráfico 1: Densidad máxima
    max_densidades = [stats['max_densidad'] for solver, stats in estadisticas.items()]
    axs[0, 0].bar(estadisticas.keys(), max_densidades, color=['gray'] + ['blue', 'green', 'purple', 'orange'][:len(densidades_optimizadas)])
    axs[0, 0].set_title('Densidad Máxima')
    axs[0, 0].set_ylabel('Número de vehículos')
    
    # Gráfico 2: Densidad media
    medias = [stats['densidad_media'] for solver, stats in estadisticas.items()]
    axs[0, 1].bar(estadisticas.keys(), medias, color=['gray'] + ['blue', 'green', 'purple', 'orange'][:len(densidades_optimizadas)])
    axs[0, 1].set_title('Densidad Media')
    axs[0, 1].set_ylabel('Número de vehículos')
    
    # Gráfico 3: Aristas transitadas
    aristas = [stats['aristas_transitadas'] for solver, stats in estadisticas.items()]
    axs[1, 0].bar(estadisticas.keys(), aristas, color=['gray'] + ['blue', 'green', 'purple', 'orange'][:len(densidades_optimizadas)])
    axs[1, 0].set_title('Aristas Transitadas')
    axs[1, 0].set_ylabel('Número de aristas')
    
    # Gráfico 4: Cobertura
    coberturas = [stats['cobertura_pct'] for solver, stats in estadisticas.items()]
    axs[1, 1].bar(estadisticas.keys(), coberturas, color=['gray'] + ['blue', 'green', 'purple', 'orange'][:len(densidades_optimizadas)])
    axs[1, 1].set_title('Cobertura (%)')
    axs[1, 1].set_ylabel('Porcentaje')
    
    plt.tight_layout()
    
    # Guardar gráfico
    stats_file = resultados_dir / "estadisticas.png"
    plt.savefig(stats_file)
    plt.close()
    
    # Generar HTML con las estadísticas
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard de Optimización</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2 {{ color: #333; }}
            .dashboard {{ display: flex; flex-direction: column; align-items: center; }}
            .stats {{ display: flex; justify-content: space-around; flex-wrap: wrap; margin: 20px 0; }}
            .stat-card {{ background: #f5f5f5; border-radius: 8px; padding: 15px; margin: 10px; min-width: 200px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .stat-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
            .stat-label {{ font-size: 14px; color: #7f8c8d; }}
            .graph {{ margin: 20px 0; text-align: center; }}
            .solver-section {{ margin-bottom: 30px; padding: 15px; background: #f9f9f9; border-radius: 8px; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <div class="dashboard">
            <h1>Dashboard de Optimización de Rutas</h1>
            
            <div class="graph">
                <img src="estadisticas.png" alt="Estadísticas de Optimización" width="800">
            </div>
            
            <h2>Resumen de Resultados</h2>
            <table>
                <tr>
                    <th>Método</th>
                    <th>Densidad Máxima</th>
                    <th>Densidad Media</th>
                    <th>Aristas Transitadas</th>
                    <th>Cobertura (%)</th>
                </tr>
    """
    
    # Añadir fila para cada solver
    for solver, stats in estadisticas.items():
        solver_name = "Original" if solver == "original" else solver
        html_content += f"""
                <tr>
                    <td>{solver_name}</td>
                    <td>{stats['max_densidad']:.2f}</td>
                    <td>{stats['densidad_media']:.2f}</td>
                    <td>{stats['aristas_transitadas']}</td>
                    <td>{stats['cobertura_pct']:.1f}%</td>
                </tr>
        """
    
    # Cerrar tabla y añadir links a los mapas
    html_content += """
            </table>
            
            <h2>Enlaces a Mapas</h2>
            <ul>
    """
    
    # Añadir link al mapa original
    html_content += f'<li><a href="mapa_calor_original.html" target="_blank">Mapa de Calor - Rutas Originales</a></li>\n'
    
    # Añadir links a los mapas de cada solver
    for solver in densidades_optimizadas.keys():
        html_content += f'<li><a href="mapa_calor_{solver}.html" target="_blank">Mapa de Calor - {solver}</a></li>\n'
    
    # Añadir link al mapa comparativo
    html_content += f'<li><a href="mapa_comparativo.html" target="_blank">Mapa Comparativo</a></li>\n'
    
    # Cerrar HTML
    html_content += """
            </ul>
        </div>
    </body>
    </html>
    """
    
    # Guardar HTML
    dashboard_file = resultados_dir / "dashboard.html"
    with open(dashboard_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Dashboard estadístico guardado en {dashboard_file}")
    return dashboard_file

def ejecutar_experimento_mejorado(street_graph, num_rutas=50, puntos_por_ruta=5, solvers=None):
    """Ejecuta el experimento completo con visualizaciones mejoradas"""
    if solvers is None:
        solvers = ['vns_solver', 'ts_solver', 'sa_solver']
    
    resultados_dir = Path("resultados_experimento")
    resultados_dir.mkdir(exist_ok=True)
    
    print(f"🚀 Iniciando experimento con {num_rutas} rutas, {puntos_por_ruta} puntos por ruta")
    
    # 1. Generar rutas aleatorias
    rutas = generar_rutas_aleatorias(street_graph, num_rutas, puntos_por_ruta)
    
    # 2. Simular recorrido de rutas aleatorias
    densidad_original = simular_recorrido(street_graph, rutas)
    
    # 3. Generar mapa de calor mejorado para rutas originales
    generar_mapa_calor_mejorado(
        street_graph, 
        densidad_original,
        rutas,  # Pasar las rutas originales
        resultados_dir / "mapa_calor_original.html",
        "Densidad de Tráfico - Rutas Originales"
    )
    
    # 4. Para cada solver, optimizar rutas y generar mapa de calor mejorado
    densidades_optimizadas = {}
    rutas_optimizadas = {}
    
    for solver in solvers:
        # Optimizar ruta
        rutas_opt = aplicar_optimizacion(street_graph, rutas, solver)
        rutas_optimizadas[solver] = rutas_opt
        
        # Simular recorrido optimizado
        densidad_opt = simular_recorrido_optimizado(street_graph, rutas_opt)
        densidades_optimizadas[solver] = densidad_opt
        
        # Generar mapa de calor mejorado
        generar_mapa_calor_mejorado(
            street_graph,
            densidad_opt,
            rutas_opt,  # Pasar las rutas optimizadas
            resultados_dir / f"mapa_calor_{solver}.html",
            f"Densidad de Tráfico - Rutas Optimizadas con {solver}",
            solver
        )
    
    # 5. Generar mapa comparativo
    generar_mapa_comparativo(
        street_graph, 
        densidad_original, 
        densidades_optimizadas, 
        resultados_dir
    )
    
    # 6. Crear dashboard con estadísticas
    dashboard_file = crear_dashboard_estadistico(
        densidad_original,
        densidades_optimizadas,
        resultados_dir
    )
    
    print(f"✅ Experimento mejorado completado. Resultados en {resultados_dir}")
    print(f"🌐 Abre el dashboard para ver todos los resultados: {dashboard_file}")
    
    # Intentar abrir el dashboard automáticamente si estamos en un entorno adecuado
    try:
        import webbrowser
        webbrowser.open(str(dashboard_file))
    except:
        pass
    
    return resultados_dir

def cargar_grafo_para_experimento(cache_path=None):
    """Carga el grafo de calles o crea uno de prueba si no existe el archivo"""
    import networkx as nx
    import random
    import json
    import os
    
    # Valores por defecto
    lat_base, lon_base = 23.1136, -82.3666  # Coordenadas de La Habana
    
    # Crear grafo
    street_graph = nx.MultiDiGraph()
    
    # Intentar cargar desde caché
    if cache_path is None:
        cache_path = os.path.join(PROJECT_ROOT, "cache", "479c34c9f9679cb8467293e0403a0250c7ef8556.json")
    
    try:
        print(f"Intentando abrir archivo de caché: {cache_path}")
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                osm_data = json.load(f)
            
            # Extraer nodos y crear grafo
            nodes = {}
            for element in osm_data.get('elements', []):
                if element.get('type') == 'node':
                    node_id = element.get('id')
                    lat = element.get('lat')
                    lon = element.get('lon')
                    if node_id and lat and lon:
                        nodes[node_id] = (float(lat), float(lon)) 
                        street_graph.add_node(node_id, lat=float(lat), lon=float(lon))
            
            print(f"Nodos extraídos: {len(nodes)}")
            
            # Extraer vías y crear aristas
            edge_count = 0
            for element in osm_data.get('elements', []):
                if element.get('type') == 'way' and element.get('tags', {}).get('highway'):
                    way_nodes = element.get('nodes', [])
                    oneway = element.get('tags', {}).get('oneway', 'no')
                    
                    for i in range(len(way_nodes) - 1):
                        if way_nodes[i] in nodes and way_nodes[i+1] in nodes:
                            node1, node2 = way_nodes[i], way_nodes[i+1]
                            lat1, lon1 = nodes[node1]
                            lat2, lon2 = nodes[node2]
                            
                            # Calcular distancia
                            dlat = lat2 - lat1
                            dlon = lon2 - lon1
                            distance = (dlat*dlat + dlon*dlon)**0.5 * 111  # ~111km por grado
                            
                            if oneway == 'yes':
                                street_graph.add_edge(node1, node2, weight=distance)
                                edge_count += 1
                            else:
                                street_graph.add_edge(node1, node2, weight=distance)
                                street_graph.add_edge(node2, node1, weight=distance)
                                edge_count += 2
            
            print(f"Grafo cargado con {len(nodes)} nodos y {edge_count} aristas")
        else:
            raise FileNotFoundError(f"Archivo no encontrado: {cache_path}")
            
    except Exception as e:
        print(f"Error cargando datos de calles: {e}")
        print("Creando grafo de desarrollo...")
        
        # Crear un grafo de prueba con 100 nodos para el experimento
        for i in range(100):
            lat = lat_base + random.uniform(-0.05, 0.05)
            lon = lon_base + random.uniform(-0.05, 0.05)
            street_graph.add_node(i, lat=lat, lon=lon)
        
        # Crear conexiones aleatorias entre nodos
        for i in range(100):
            # Conectar cada nodo con 3-5 vecinos aleatorios
            num_neighbors = random.randint(3, 5)
            neighbors = random.sample(range(100), min(num_neighbors, 100))
            
            for neighbor in neighbors:
                if i != neighbor:
                    # Calcular distancia entre nodos
                    lat1 = street_graph.nodes[i]['lat']
                    lon1 = street_graph.nodes[i]['lon']
                    lat2 = street_graph.nodes[neighbor]['lat']
                    lon2 = street_graph.nodes[neighbor]['lon']
                    
                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    distance = (dlat*dlat + dlon*dlon)**0.5 * 111
                    
                    street_graph.add_edge(i, neighbor, weight=distance)
        
        print(f"Grafo de desarrollo creado con {street_graph.number_of_nodes()} nodos y {street_graph.number_of_edges()} aristas")
    
    return street_graph

if __name__ == "__main__":
    # Usar nuestra función personalizada en lugar de load_streets()
    print("Cargando grafo de calles...")
    street_graph = cargar_grafo_para_experimento()
    
    # Verificar que el grafo se cargó correctamente
    if street_graph is None or street_graph.number_of_nodes() == 0:
        print("❌ Error: No se pudo cargar o crear un grafo válido.")
        sys.exit(1)
    
    print(f"✅ Grafo listo con {street_graph.number_of_nodes()} nodos y {street_graph.number_of_edges()} aristas")
    
    # Ejecutar experimento mejorado
    ejecutar_experimento_mejorado(
        street_graph,
        num_rutas=50,
        puntos_por_ruta=20,
        solvers=['vns_solver', 'sa_solver', 'ts_solver']  
    )