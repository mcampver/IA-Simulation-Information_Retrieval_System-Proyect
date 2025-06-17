import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
import sys
import os
from tqdm import tqdm
import itertools

# Asegúrate de que el solver esté en el path
sys.path.append("src/ag_solver")
try:
    import ag_solver
except ImportError:
    raise ImportError(
        "No se pudo importar 'ag_solver'. "
        "Verifica que 'src/ag_solver' esté en sys.path y que el módulo exista."
    )

# ----- CONFIGURACIÓN DE VISUALIZACIONES -----
# Se usa seaborn para estilos; ajusta o elimina si no quieres depender de seaborn.
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("paper", font_scale=1.2)


# 1. GENERACIÓN DE INSTANCIAS PEQUEÑAS CON ÓPTIMO VERDADERO
def generate_small_instance(num_nodes=15, num_clients=5, seed=42):
    """
    Genera un grafo dirigido con coordenadas aleatorias y extrae una subinstancia
    para VRP (depósito + clientes). Calcula el costo óptimo exacto recorriendo todas
    las permutaciones de clientes (TSP) dado que num_clients es pequeño.
    
    Retorna un dict con:
      - 'graph': el grafo completo (NetworkX) de num_nodes.
      - 'dist_matrix': lista de listas con la matriz de distancias reducida (dim = num_clients+1).
      - 'demands': lista de demandas [0, 1, 1, ..., 1] (depósito + clientes).
      - 'clients': lista de nodos originales que son clientes.
      - 'optimal_cost': costo mínimo encontrado (float).
      - 'coords': diccionario {nodo: (x, y)} del grafo completo.
      - 'subset_indices': lista de nodos originales [0] + clientes, para mapping.
    """
    np.random.seed(seed)

    # 1) Crear grafo completo con coordenadas
    G = nx.DiGraph()
    coords = {}
    for i in range(num_nodes):
        coords[i] = (np.random.uniform(0, 100), np.random.uniform(0, 100))
        G.add_node(i, pos=coords[i])

    # 2) Añadir aristas con peso = distancia euclidiana
    for i in range(num_nodes):
        for j in range(num_nodes):
            if i == j:
                continue
            xi, yi = coords[i]
            xj, yj = coords[j]
            dist = np.hypot(xi - xj, yi - yj)
            G.add_edge(i, j, weight=dist)

    # 3) Elegir aleatoriamente num_clients nodos (excluyendo el nodo 0 que será depósito)
    all_candidates = list(range(1, num_nodes))
    clients = list(np.random.choice(all_candidates, size=num_clients, replace=False))

    # 4) Construir la lista de índices de la subinstancia: depósito (0) + clientes
    subset = [0] + clients  # tamaño = num_clients + 1

    # 5) Construir la matriz de distancias reducida (dim = len(subset) x len(subset))
    full_dm = np.zeros((num_nodes, num_nodes), dtype=float)
    for i, j in G.edges():
        full_dm[i, j] = G[i][j]['weight']

    dm_reduced = np.zeros((len(subset), len(subset)), dtype=float)
    for i_r, i_orig in enumerate(subset):
        for j_r, j_orig in enumerate(subset):
            if i_orig == j_orig:
                dm_reduced[i_r, j_r] = 0.0
            else:
                dm_reduced[i_r, j_r] = full_dm[i_orig, j_orig]

    # 6) Demandas: depósito = 0, cada cliente = 1
    demands = [0] + [1] * num_clients

    # 7) Calcular costo óptimo exacto (TSP) por fuerza bruta
    #    Los índices en dm_reduced son 0 = depósito, 1..num_clients = clientes
    best_cost = float('inf')
    for perm in itertools.permutations(range(1, num_clients + 1)):
        cost = 0.0
        prev = 0
        for node in perm:
            cost += dm_reduced[prev, node]
            prev = node
        cost += dm_reduced[prev, 0]  # regresar al depósito
        if cost < best_cost:
            best_cost = cost

    return {
        'graph': G,
        'dist_matrix': dm_reduced.tolist(),
        'demands': demands,
        'clients': clients,
        'optimal_cost': best_cost,
        'coords': coords,
        'subset_indices': subset
    }


# 2. FUNCIÓN PARA EJECUTAR EXPERIMENTOS EN INSTANCIAS PEQUEÑAS
def run_small_instance_experiments(instances, params_list, n_runs=200, n_boot=5000, ci_level=0.95):
    """
    Para cada instancia y cada configuración de parámetros:
      - Ejecuta el solver VRP n_runs veces, midiendo costo y tiempo.
      - Calcula gap% contra el costo óptimo exacto.
      - Obtiene intervalos de confianza por bootstrapping (n_boot).
    Devuelve un DataFrame con estadísticas agregadas y datos brutos (listas).
    """
    results = []

    for instance_id, instance in enumerate(instances):
        dist_matrix = instance['dist_matrix']
        demands = instance['demands']
        optimal_cost = instance['optimal_cost']

        # Capacidad amplia para cubrir todos los clientes con un solo camión
        total_demand = sum(demands)
        truck_capacities = [total_demand * 2]

        for params in tqdm(params_list, desc=f"Instancia {instance_id + 1}/{len(instances)}"):
            pop_size = params['pop_size']
            sel_size = params['sel_size']
            max_gen = params['max_gen']

            scores, times, gaps = [], [], []

            for run in range(n_runs):
                try:
                    t0 = time.time()
                    routes = ag_solver.solve_vrp(
                        dist_matrix,
                        demands,
                        truck_capacities,
                        pop_size=pop_size,
                        sel_size=sel_size,
                        max_gen=max_gen,
                        no_improve_limit=20,
                        mut_rate=0.3
                    )
                    elapsed = time.time() - t0

                    total_cost = compute_total_distance(routes, dist_matrix)
                    gap = (total_cost - optimal_cost) / optimal_cost * 100

                    scores.append(total_cost)
                    times.append(elapsed)
                    gaps.append(gap)
                except Exception as e:
                    # Si falla el solver, guardamos un log y continuamos
                    print(f"[ERROR] Instancia {instance_id}, params {params}, run {run}: {e}")
                    # Para que la longitud de las listas no cambie, agregamos valores grandes:
                    scores.append(np.nan)
                    times.append(np.nan)
                    gaps.append(np.nan)

            # Filtrar NaNs antes del bootstrap
            scores_arr = np.array(scores)[~np.isnan(scores)]
            times_arr = np.array(times)[~np.isnan(times)]
            gaps_arr = np.array(gaps)[~np.isnan(gaps)]

            # Si todos los valores son NaN (fallos constantes), colocamos NaN
            if len(scores_arr) == 0:
                score_ci = (np.nan, np.nan)
                time_ci = (np.nan, np.nan)
                gap_ci = (np.nan, np.nan)
                mean_score = np.nan
                mean_time = np.nan
                mean_gap = np.nan
            else:
                score_ci = bootstrap_ci(scores_arr.tolist(), n_boot, ci_level)
                time_ci = bootstrap_ci(times_arr.tolist(), n_boot, ci_level)
                gap_ci = bootstrap_ci(gaps_arr.tolist(), n_boot, ci_level)
                mean_score = float(np.mean(scores_arr))
                mean_time = float(np.mean(times_arr))
                mean_gap = float(np.mean(gaps_arr))

            results.append({
                'instance': instance_id,
                'pop_size': pop_size,
                'sel_size': sel_size,
                'max_gen': max_gen,
                'mean_score': mean_score,
                'score_ci_lower': score_ci[0],
                'score_ci_upper': score_ci[1],
                'mean_time': mean_time,
                'time_ci_lower': time_ci[0],
                'time_ci_upper': time_ci[1],
                'mean_gap': mean_gap,
                'gap_ci_lower': gap_ci[0],
                'gap_ci_upper': gap_ci[1],
                'optimal_cost': optimal_cost,
                'raw_scores': scores,
                'raw_times': times,
                'raw_gaps': gaps
            })

    return pd.DataFrame(results)


# 3. FUNCIONES AUXILIARES
def compute_total_distance(routes, dist_matrix):
    """
    Calcula la distancia total recorrida por todas las rutas.
    Se asume que cada ruta es una lista de índices en dist_matrix, y que 0 es el depósito.
    """
    total = 0.0
    for r in routes:
        prev = 0
        for node in r:
            total += dist_matrix[prev][node]
            prev = node
        total += dist_matrix[prev][0]
    return total


def bootstrap_ci(data, n_boot=1000, ci=0.95):
    """
    Calcula intervalos de confianza para la media usando bootstrapping.
    data: lista o array de valores (floats).
    n_boot: número de muestras bootstrap.
    ci: nivel de confianza (por ejemplo, 0.95).
    Retorna (lower, upper).
    """
    boot_means = []
    n = len(data)
    for _ in range(n_boot):
        sample = np.random.choice(data, size=n, replace=True)
        boot_means.append(np.mean(sample))
    lower = np.percentile(boot_means, (1 - ci) / 2 * 100)
    upper = np.percentile(boot_means, (1 + ci) / 2 * 100)
    return lower, upper


# 4. VISUALIZACIONES
def create_visualizations(results_df, instances, output_dir="experiment_results"):
    """
    Genera y guarda varios gráficos:
      1) Gap promedio vs. configuración
      2) Boxplot de gaps por configuración
      3) Scatter tiempo vs. gap con anotaciones
      4) Histogramas de puntuaciones (mejor y peor configuración)
      5) Grafo de la mejor instancia (solo nodos; no se dibujan rutas como aristas)
      6) Intervalos de confianza del gap para cada configuración
    """
    os.makedirs(output_dir, exist_ok=True)

    # --- Preparar DataFrame "largo" para boxplots ---
    temp_list = []
    for _, row in results_df.iterrows():
        gaps = row['raw_gaps']
        # Filtrar NaNs para evitar warnings
        gaps_clean = [g for g in gaps if not np.isnan(g)]
        if len(gaps_clean) == 0:
            continue
        df_temp = pd.DataFrame({
            'gap': gaps_clean,
            'pop_size': [row['pop_size']] * len(gaps_clean),
            'max_gen': [row['max_gen']] * len(gaps_clean)
        })
        temp_list.append(df_temp)
    if temp_list:
        results_long = pd.concat(temp_list, ignore_index=True)
    else:
        results_long = pd.DataFrame(columns=['gap', 'pop_size', 'max_gen'])

    # 1. Gráfico de barras: gap promedio vs configuración
    plt.figure(figsize=(12, 7))
    g = sns.barplot(
        data=results_df,
        x='pop_size',
        y='mean_gap',
        hue='max_gen'
    )
    g.set_title('Gap porcentual respecto al óptimo por configuración')
    g.set_xlabel('Tamaño de población')
    g.set_ylabel('Gap (%)')
    plt.axhline(y=1, color='r', linestyle='--', label='Umbral de éxito (1%)')
    plt.legend(title='Generaciones')
    plt.savefig(f"{output_dir}/gap_by_configuration.png", dpi=300, bbox_inches='tight')
    plt.close()

    # 2. Boxplot de gaps por configuración
    plt.figure(figsize=(14, 8))
    sns.boxplot(
        data=results_long,
        x='pop_size',
        y='gap',
        hue='max_gen'
    )
    plt.title('Distribución de gaps por configuración')
    plt.xlabel('Tamaño de población')
    plt.ylabel('Gap respecto al óptimo (%)')
    plt.axhline(y=1, color='r', linestyle='--', label='Umbral de éxito (1%)')
    plt.legend(title='Generaciones')
    plt.savefig(f"{output_dir}/gap_boxplot.png", dpi=300, bbox_inches='tight')
    plt.close()

    # 3. Gráfico de dispersión: tiempo vs calidad
    plt.figure(figsize=(10, 8))
    scatter = plt.scatter(
        results_df['mean_time'],
        results_df['mean_gap'],
        c=results_df['pop_size'],
        s=results_df['max_gen'] / 5,
        alpha=0.7,
        cmap='viridis'
    )
    plt.colorbar(scatter, label='Tamaño de población')
    plt.title('Relación entre tiempo de cómputo y calidad de solución')
    plt.xlabel('Tiempo promedio (s)')
    plt.ylabel('Gap promedio (%)')
    plt.xscale('log')
    for _, row in results_df.iterrows():
        plt.annotate(
            f"P{row['pop_size']},G{row['max_gen']}",
            (row['mean_time'], row['mean_gap']),
            fontsize=8
        )
    plt.savefig(f"{output_dir}/time_vs_quality.png", dpi=300, bbox_inches='tight')
    plt.close()

    # 4. Histogramas de distribución de soluciones (mejor vs peor configuración)
    if not results_df.empty:
        best_config = results_df.loc[results_df['mean_gap'].idxmin()]
        worst_config = results_df.loc[results_df['mean_gap'].idxmax()]

        plt.figure(figsize=(12, 6))
        plt.subplot(1, 2, 1)
        gaps_best = [s for s in best_config['raw_scores'] if not np.isnan(s)]
        sns.histplot(gaps_best, kde=True)
        optimal = instances[best_config['instance']]['optimal_cost']
        plt.axvline(x=optimal, color='r', linestyle='--', label='Óptimo')
        plt.title(f'Mejor configuración\nP={best_config["pop_size"]}, G={best_config["max_gen"]}')
        plt.xlabel('Costo total')
        plt.ylabel('Frecuencia')
        plt.legend()

        plt.subplot(1, 2, 2)
        gaps_worst = [s for s in worst_config['raw_scores'] if not np.isnan(s)]
        sns.histplot(gaps_worst, kde=True)
        plt.axvline(x=optimal, color='r', linestyle='--', label='Óptimo')
        plt.title(f'Peor configuración\nP={worst_config["pop_size"]}, G={worst_config["max_gen"]}')
        plt.xlabel('Costo total')
        plt.ylabel('Frecuencia')
        plt.legend()

        plt.tight_layout()
        plt.savefig(f"{output_dir}/solution_distributions.png", dpi=300, bbox_inches='tight')
        plt.close()

        # 5. Grafo de la mejor instancia (solo nodos: depósito y clientes)
        best_instance = instances[best_config['instance']]
        G_best = best_instance['graph']
        coords = best_instance['coords']
        clients_orig = best_instance['clients']

        plt.figure(figsize=(10, 8))
        pos = nx.get_node_attributes(G_best, 'pos')
        nx.draw(
            G_best,
            pos,
            node_size=30,
            alpha=0.3,
            node_color='gray',
            with_labels=False
        )
        nx.draw_networkx_nodes(
            G_best,
            pos,
            nodelist=[0],
            node_color='red',
            node_size=200,
            label='Depósito'
        )
        nx.draw_networkx_nodes(
            G_best,
            pos,
            nodelist=clients_orig,
            node_color='blue',
            node_size=100,
            label='Clientes'
        )
        labels = {i: str(i) for i in coords}
        nx.draw_networkx_labels(G_best, pos, labels=labels, font_size=10)
        plt.title(f'Instancia #{best_config["instance"]} con {len(clients_orig)} clientes')
        plt.legend()
        plt.savefig(f"{output_dir}/best_instance_graph.png", dpi=300, bbox_inches='tight')
        plt.close()

    # 6. Intervalos de confianza del gap por configuración
    plt.figure(figsize=(12, 6))
    plot_df = results_df.sort_values('mean_gap').reset_index(drop=True)
    x_labels = [f'P{row.pop_size},G{row.max_gen}' for _, row in plot_df.iterrows()]

    plt.errorbar(
        range(len(plot_df)),
        plot_df['mean_gap'],
        yerr=[
            plot_df['mean_gap'] - plot_df['gap_ci_lower'],
            plot_df['gap_ci_upper'] - plot_df['mean_gap']
        ],
        fmt='o',
        capsize=5,
        ecolor='gray',
        markersize=8
    )
    plt.xticks(range(len(plot_df)), x_labels, rotation=90)
    plt.title('Intervalos de confianza del gap (%) por configuración')
    plt.ylabel('Gap respecto al óptimo (%)')
    plt.xlabel('Configuración (P, G)')
    plt.axhline(y=1, color='r', linestyle='--', label='Umbral de éxito (1%)')
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{output_dir}/confidence_intervals.png", dpi=300, bbox_inches='tight')
    plt.close()

    # Mostrar lista de archivos generados
    print("Gráficos generados en:", output_dir)
    for fname in sorted(os.listdir(output_dir)):
        print(f"  - {fname}")


# 5. FUNCIÓN PRINCIPAL
def main():
    # Configuración de instancias
    num_instances = 5
    instances = [generate_small_instance(num_nodes=150, num_clients=5, seed=i) for i in range(num_instances)]

    # Configuración de parámetros a probar
    pop_sizes = [20, 100, 200]
    max_gens = [50, 100, 500]
    params_list = []
    for pop_size in pop_sizes:
        for max_gen in max_gens:
            params_list.append({
                'pop_size': pop_size,
                'sel_size': max(1, int(pop_size * 0.2)),
                'max_gen': max_gen
            })

    # Ejecutar experimentos (con n_runs y n_boot moderados para no tardar demasiado)
    results = run_small_instance_experiments(
        instances,
        params_list,
        n_runs=200,     # se redujo de 1000 para rapidez
        n_boot=5000,    # se redujo de 100000 para rapidez
        ci_level=0.95
    )

    # Crear carpeta de resultados
    os.makedirs('experiment_results', exist_ok=True)
    results.to_csv('experiment_results/small_instance_results.csv', index=False)

    # Generar visualizaciones
    create_visualizations(results, instances, output_dir='experiment_results')

    print("Experimento completado. Resultados guardados en 'experiment_results/'.")


if __name__ == "__main__":
    main()
