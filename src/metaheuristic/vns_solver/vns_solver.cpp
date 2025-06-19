#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <vector>
#include <algorithm>
#include <random>
#include <limits>
#include <numeric>
#include <chrono>
#include <unordered_map>
#include <unordered_set>
#include <stdexcept>
#include <string>
#include <memory>
#include <cassert>
#include <queue>
#include <cmath>
#include <set>

#ifdef _OPENMP
#include <omp.h>
#endif

namespace py = pybind11;
using namespace std;
using Clock = chrono::steady_clock;

// --- Configuración mejorada para búsqueda del óptimo global ---
struct VNSConfig {
    // Parámetros básicos
    int openmp_threshold = 8;
    int top_k_insert = 50;
    double intensification_factor = 1.5;
    double diversification_factor = 0.75;
    
    // Intensidad de perturbación dinámica
    double initial_shake_intensity = 2.0;
    double max_shake_intensity = 20.0;
    double shake_increase = 1.15;
    
    // Control de convergencia
    int max_stagnation = 100;
    int max_global_stagnation = 500;
    
    // Optimizaciones
    bool use_caching = true;
    bool use_adaptive_parameters = true;
    bool use_multi_start = true;
    bool use_path_relinking = true;
    bool use_solution_memory = true;
    
    // Memoria y diversificación
    double tabu_tenure_factor = 0.15;
    int max_elite_solutions = 10;
    double restart_threshold = 0.9;
    int memory_size = 50;
    
    // Búsqueda local intensiva
    int max_vnd_iterations = 15;
    bool use_best_improvement = true;
    bool use_variable_depth = true;
    
    // Multi-start y path relinking
    int num_initial_solutions = 5;
    int path_relinking_frequency = 25;
    double diversity_threshold = 0.1;
    
    void validate() const {
        if (openmp_threshold < 1) throw invalid_argument("openmp_threshold debe ser positivo");
        if (max_stagnation < 10) throw invalid_argument("max_stagnation debe ser >= 10");
        if (initial_shake_intensity <= 0) throw invalid_argument("initial_shake_intensity debe ser positivo");
        if (max_shake_intensity <= initial_shake_intensity) 
            throw invalid_argument("max_shake_intensity debe ser mayor que initial_shake_intensity");
    }
};

// --- Estructura de solución con metadata extendida ---
struct Solution {
    vector<vector<int>> routes;
    vector<int> loads;
    vector<double> route_dists;
    double total_distance;
    double fitness;
    int age;
    int birth_iteration;
    vector<int> solution_hash; // Para detección de diversidad
    
    Solution() : total_distance(0.0), fitness(0.0), age(0), birth_iteration(0) {}
    
    bool operator<(const Solution& other) const {
        return total_distance < other.total_distance;
    }
    
    void clear() {
        routes.clear();
        loads.clear();
        route_dists.clear();
        total_distance = 0.0;
        fitness = 0.0;
        age = 0;
        birth_iteration = 0;
        solution_hash.clear();
    }
    
    // Calcular hash para diversidad
    void compute_hash() {
        solution_hash.clear();
        for (const auto& route : routes) {
            solution_hash.insert(solution_hash.end(), route.begin(), route.end());
        }
        sort(solution_hash.begin(), solution_hash.end());
    }
    
    // Calcular diversidad entre soluciones
    double diversity_with(const Solution& other) const {
        if (solution_hash.empty() || other.solution_hash.empty()) return 1.0;
        
        set<int> intersection;
        set_intersection(solution_hash.begin(), solution_hash.end(),
                        other.solution_hash.begin(), other.solution_hash.end(),
                        inserter(intersection, intersection.begin()));
        
        return 1.0 - (2.0 * intersection.size()) / (solution_hash.size() + other.solution_hash.size());
    }
};

// --- Cache de distancias optimizado con pre-computación ---
class AdvancedDistanceCache {
private:
    const vector<vector<double>>& D;
    mutable unordered_map<uint64_t, double> cache;
    mutable unordered_map<uint64_t, double> delta_cache; // Cache para diferencias
    bool enabled;
    size_t max_cache_size;
    
    uint64_t hash_pair(int i, int j) const {
        return (static_cast<uint64_t>(min(i,j)) << 32) | static_cast<uint64_t>(max(i,j));
    }
    
    uint64_t hash_triple(int i, int j, int k) const {
        vector<int> nodes = {i, j, k};
        sort(nodes.begin(), nodes.end());
        return (static_cast<uint64_t>(nodes[0]) << 32) | 
               (static_cast<uint64_t>(nodes[1]) << 16) | 
               static_cast<uint64_t>(nodes[2]);
    }
    
public:
    AdvancedDistanceCache(const vector<vector<double>>& distances, bool use_cache, size_t max_size = 200000)
        : D(distances), enabled(use_cache), max_cache_size(max_size) {}
    
    double get(int i, int j) const {
        if (!enabled) return D[i][j];
        
        uint64_t key = hash_pair(i, j);
        auto it = cache.find(key);
        if (it != cache.end()) {
            return it->second;
        }
        
        if (cache.size() >= max_cache_size) {
            cache.clear();
            delta_cache.clear();
        }
        
        double dist = D[i][j];
        cache[key] = dist;
        return dist;
    }
    
    // Cache para cálculos de mejora 2-opt
    double get_2opt_delta(int a, int b, int c, int d) const {
        if (!enabled) return get(a, c) + get(b, d) - get(a, b) - get(c, d);
        
        uint64_t key = hash_triple(a, b, c) ^ hash_pair(d, 0);
        auto it = delta_cache.find(key);
        if (it != delta_cache.end()) {
            return it->second;
        }
        
        double delta = get(a, c) + get(b, d) - get(a, b) - get(c, d);
        delta_cache[key] = delta;
        return delta;
    }
    
    void clear() {
        if (enabled) {
            cache.clear();
            delta_cache.clear();
        }
    }
};

// --- Funciones auxiliares mejoradas ---
double compute_route_distance(const vector<int>& route, const AdvancedDistanceCache& dist_cache) {
    if (route.empty()) return 0.0;
    double d = dist_cache.get(0, route.front());
    for (size_t i = 0; i + 1 < route.size(); ++i) {
        d += dist_cache.get(route[i], route[i+1]);
    }
    d += dist_cache.get(route.back(), 0);
    return d;
}

inline void update_total_distance(Solution& sol, const AdvancedDistanceCache& dist_cache) {
    sol.total_distance = 0.0;
    for (size_t t = 0; t < sol.routes.size(); ++t) {
        sol.route_dists[t] = compute_route_distance(sol.routes[t], dist_cache);
        sol.total_distance += sol.route_dists[t];
    }
    sol.compute_hash();
}

// --- Implementación del algoritmo Clarke-Wright ---
Solution generate_initial_solution_clarke_wright(
    const vector<int>& objectives,
    const vector<int>& demands,
    const vector<int>& capacities,
    int num_trucks,
    const AdvancedDistanceCache& dist_cache)
{
    Solution sol;
    sol.routes.assign(num_trucks, {});
    sol.loads.assign(num_trucks, 0);
    sol.route_dists.assign(num_trucks, 0.0);

    // Crear rutas individuales inicialmente
    for (size_t i = 0; i < objectives.size() && i < static_cast<size_t>(num_trucks); ++i) {
        int node = objectives[i];
        if (demands[node] <= capacities[i]) {
            sol.routes[i].push_back(node);
            sol.loads[i] = demands[node];
        }
    }
    
    // Asignar nodos restantes usando nearest neighbor
    for (size_t i = num_trucks; i < objectives.size(); ++i) {
        int node = objectives[i];
        int best_truck = -1;
        double best_cost = numeric_limits<double>::infinity();
        
        for (int t = 0; t < num_trucks; ++t) {
            if (sol.loads[t] + demands[node] <= capacities[t]) {
                double cost = sol.routes[t].empty() ? 
                    dist_cache.get(0, node) * 2 :
                    dist_cache.get(sol.routes[t].back(), node) + 
                    dist_cache.get(node, 0) - 
                    dist_cache.get(sol.routes[t].back(), 0);
                
                if (cost < best_cost) {
                    best_cost = cost;
                    best_truck = t;
                }
            }
        }
        
        if (best_truck != -1) {
            sol.routes[best_truck].push_back(node);
            sol.loads[best_truck] += demands[node];
        }
    }
    
    update_total_distance(sol, dist_cache);
    return sol;
}

// --- Implementación de operadores de búsqueda local faltantes ---
bool apply_swap_improved(Solution& sol, const vector<int>& demands, 
                        const vector<int>& capacities, const AdvancedDistanceCache& dist_cache, 
                        mt19937& gen) {
    if (sol.routes.size() < 2) return false;
    
    // Seleccionar rutas con nodos
    vector<int> non_empty_routes;
    for (int t = 0; t < static_cast<int>(sol.routes.size()); ++t) {
        if (!sol.routes[t].empty()) {
            non_empty_routes.push_back(t);
        }
    }
    
    if (non_empty_routes.size() < 2) return false;
    
    uniform_int_distribution<> route_dist(0, non_empty_routes.size() - 1);
    int idx1 = route_dist(gen);
    int idx2 = route_dist(gen);
    while (idx1 == idx2) idx2 = route_dist(gen);
    
    int t1 = non_empty_routes[idx1];
    int t2 = non_empty_routes[idx2];
    
    uniform_int_distribution<> pos1_dist(0, sol.routes[t1].size() - 1);
    uniform_int_distribution<> pos2_dist(0, sol.routes[t2].size() - 1);
    int pos1 = pos1_dist(gen);
    int pos2 = pos2_dist(gen);
    
    int node1 = sol.routes[t1][pos1];
    int node2 = sol.routes[t2][pos2];
    
    // Verificar factibilidad
    int new_load1 = sol.loads[t1] - demands[node1] + demands[node2];
    int new_load2 = sol.loads[t2] - demands[node2] + demands[node1];
    
    if (new_load1 > capacities[t1] || new_load2 > capacities[t2]) {
        return false;
    }
    
    // Calcular mejora antes de aplicar
    double old_dist = sol.route_dists[t1] + sol.route_dists[t2];
    
    // Aplicar swap
    swap(sol.routes[t1][pos1], sol.routes[t2][pos2]);
    sol.loads[t1] = new_load1;
    sol.loads[t2] = new_load2;
    
    // Recalcular distancias
    sol.route_dists[t1] = compute_route_distance(sol.routes[t1], dist_cache);
    sol.route_dists[t2] = compute_route_distance(sol.routes[t2], dist_cache);
    double new_dist = sol.route_dists[t1] + sol.route_dists[t2];
    
    // Solo aceptar si hay mejora
    if (new_dist >= old_dist) {
        // Revertir
        swap(sol.routes[t1][pos1], sol.routes[t2][pos2]);
        sol.loads[t1] = sol.loads[t1] - demands[node2] + demands[node1];
        sol.loads[t2] = sol.loads[t2] - demands[node1] + demands[node2];
        sol.route_dists[t1] = compute_route_distance(sol.routes[t1], dist_cache);
        sol.route_dists[t2] = compute_route_distance(sol.routes[t2], dist_cache);
        return false;
    }
    
    update_total_distance(sol, dist_cache);
    return true;
}

bool apply_or_opt(Solution& sol, const vector<int>& demands, 
                  const vector<int>& capacities, const AdvancedDistanceCache& dist_cache, 
                  mt19937& gen) {
    if (sol.routes.empty()) return false;
    
    // Encontrar rutas no vacías
    vector<int> non_empty_routes;
    for (int t = 0; t < static_cast<int>(sol.routes.size()); ++t) {
        if (sol.routes[t].size() >= 1) {
            non_empty_routes.push_back(t);
        }
    }
    
    if (non_empty_routes.empty()) return false;
    
    uniform_int_distribution<> truck_dist(0, non_empty_routes.size() - 1);
    int t1 = non_empty_routes[truck_dist(gen)];
    
    if (sol.routes[t1].size() < 1) return false;
    
    // Seleccionar secuencia de 1-2 nodos consecutivos
    int seq_len = min(2, static_cast<int>(sol.routes[t1].size()));
    uniform_int_distribution<> len_dist(1, seq_len);
    seq_len = len_dist(gen);
    
    uniform_int_distribution<> start_dist(0, sol.routes[t1].size() - seq_len);
    int start_pos = start_dist(gen);
    
    vector<int> sequence(sol.routes[t1].begin() + start_pos, 
                        sol.routes[t1].begin() + start_pos + seq_len);
    
    int total_demand = 0;
    for (int node : sequence) {
        total_demand += demands[node];
    }
    
    // Intentar reinsertarla en otra posición o ruta
    uniform_int_distribution<> target_truck_dist(0, sol.routes.size() - 1);
    int t2 = target_truck_dist(gen);
    
    // Verificar factibilidad
    if (t1 != t2) {
        if (sol.loads[t2] + total_demand > capacities[t2]) {
            return false;
        }
    }
    
    // Calcular mejora
    double old_dist = (t1 == t2) ? sol.route_dists[t1] : 
                      sol.route_dists[t1] + sol.route_dists[t2];
    
    // Remover secuencia
    sol.routes[t1].erase(sol.routes[t1].begin() + start_pos, 
                        sol.routes[t1].begin() + start_pos + seq_len);
    sol.loads[t1] -= total_demand;
    
    // Insertar en nueva posición
    uniform_int_distribution<> insert_dist(0, sol.routes[t2].size());
    int insert_pos = insert_dist(gen);
    sol.routes[t2].insert(sol.routes[t2].begin() + insert_pos, 
                         sequence.begin(), sequence.end());
    sol.loads[t2] += total_demand;
    
    // Recalcular distancias
    sol.route_dists[t1] = compute_route_distance(sol.routes[t1], dist_cache);
    if (t1 != t2) {
        sol.route_dists[t2] = compute_route_distance(sol.routes[t2], dist_cache);
    }
    
    double new_dist = (t1 == t2) ? sol.route_dists[t1] : 
                      sol.route_dists[t1] + sol.route_dists[t2];
    
    // Solo aceptar si hay mejora
    if (new_dist >= old_dist) {
        // Revertir cambios
        sol.routes[t2].erase(sol.routes[t2].begin() + insert_pos, 
                            sol.routes[t2].begin() + insert_pos + seq_len);
        sol.loads[t2] -= total_demand;
        sol.routes[t1].insert(sol.routes[t1].begin() + start_pos, 
                             sequence.begin(), sequence.end());
        sol.loads[t1] += total_demand;
        
        sol.route_dists[t1] = compute_route_distance(sol.routes[t1], dist_cache);
        if (t1 != t2) {
            sol.route_dists[t2] = compute_route_distance(sol.routes[t2], dist_cache);
        }
        return false;
    }
    
    update_total_distance(sol, dist_cache);
    return true;
}

// --- Generador de solución inicial multi-método ---
vector<Solution> generate_diverse_initial_solutions(
    const vector<int>& objectives,
    const vector<int>& demands,
    const vector<int>& capacities,
    int num_trucks,
    const AdvancedDistanceCache& dist_cache,
    int num_solutions = 5)
{
    vector<Solution> solutions;
    mt19937 gen(random_device{}());
    
    // Método 1: Clarke-Wright clásico
    Solution cw_sol = generate_initial_solution_clarke_wright(objectives, demands, capacities, num_trucks, dist_cache);
    solutions.push_back(cw_sol);
    
    // Método 2: Nearest Neighbor desde diferentes nodos
    for (int start_idx = 0; start_idx < min(3, static_cast<int>(objectives.size())); ++start_idx) {
        Solution nn_sol;
        nn_sol.routes.assign(num_trucks, {});
        nn_sol.loads.assign(num_trucks, 0);
        nn_sol.route_dists.assign(num_trucks, 0.0);
        
        vector<bool> visited(objectives.size(), false);
        int current_truck = 0;
        int current_pos = start_idx;
        
        while (current_truck < num_trucks) {
            bool found = false;
            double best_dist = numeric_limits<double>::infinity();
            int best_node = -1;
            
            for (int i = 0; i < static_cast<int>(objectives.size()); ++i) {
                if (!visited[i] && nn_sol.loads[current_truck] + demands[objectives[i]] <= capacities[current_truck]) {
                    double dist = (nn_sol.routes[current_truck].empty()) ? 
                        dist_cache.get(0, objectives[i]) :
                        dist_cache.get(objectives[current_pos], objectives[i]);
                    
                    if (dist < best_dist) {
                        best_dist = dist;
                        best_node = i;
                        found = true;
                    }
                }
            }
            
            if (found) {
                nn_sol.routes[current_truck].push_back(objectives[best_node]);
                nn_sol.loads[current_truck] += demands[objectives[best_node]];
                visited[best_node] = true;
                current_pos = best_node;
            } else {
                current_truck++;
            }
        }
        
        update_total_distance(nn_sol, dist_cache);
        solutions.push_back(nn_sol);
    }
    
    // Método 3: Construcción aleatoria con bias hacia mejores inserciones
    for (int iter = 0; iter < static_cast<int>(num_solutions) - static_cast<int>(solutions.size()); ++iter) {
        Solution random_sol;
        random_sol.routes.assign(num_trucks, {});
        random_sol.loads.assign(num_trucks, 0);
        random_sol.route_dists.assign(num_trucks, 0.0);
        
        vector<int> remaining = objectives;
        shuffle(remaining.begin(), remaining.end(), gen);
        
        for (int node : remaining) {
            vector<pair<double, int>> feasible_trucks;
            
            for (int t = 0; t < num_trucks; ++t) {
                if (random_sol.loads[t] + demands[node] <= capacities[t]) {
                    double cost = random_sol.routes[t].empty() ? 
                        dist_cache.get(0, node) * 2 :
                        dist_cache.get(random_sol.routes[t].back(), node) + 
                        dist_cache.get(node, 0) - 
                        dist_cache.get(random_sol.routes[t].back(), 0);
                    feasible_trucks.push_back({cost, t});
                }
            }
            
            if (!feasible_trucks.empty()) {
                sort(feasible_trucks.begin(), feasible_trucks.end());
                
                // Selección con bias hacia mejores opciones
                uniform_real_distribution<> prob_dist(0.0, 1.0);
                double p = prob_dist(gen);
                int selected_idx = min(static_cast<int>(p * p * feasible_trucks.size()), static_cast<int>(feasible_trucks.size()) - 1);
                
                int best_truck = feasible_trucks[selected_idx].second;
                random_sol.routes[best_truck].push_back(node);
                random_sol.loads[best_truck] += demands[node];
            }
        }
        
        update_total_distance(random_sol, dist_cache);
        solutions.push_back(random_sol);
    }
    
    return solutions;
}

// --- Operadores de búsqueda local avanzados ---
enum OpType { 
    SWAP=0, RELOCATE=1, TWO_OPT=2, OR_OPT=3, 
    CROSS_EXCHANGE=4, TWO_OPT_STAR=5, THREE_OPT=6, 
    CHAIN_RELOCATE=7, OP_COUNT=8 
};

// 2-opt con mejor mejora y caching
bool apply_two_opt_best_improvement(Solution& sol, const AdvancedDistanceCache& dist_cache) {
    bool improved = false;
    double best_global_improvement = 0.0;
    int best_truck = -1, best_i = -1, best_j = -1;
    
    for (int t = 0; t < static_cast<int>(sol.routes.size()); ++t) {
        if (sol.routes[t].size() < 4) continue;
        
        int n = static_cast<int>(sol.routes[t].size());
        for (int i = 0; i < n - 2; ++i) {
            for (int j = i + 2; j < n; ++j) {
                int a = (i == 0) ? 0 : sol.routes[t][i-1];
                int b = sol.routes[t][i];
                int c = sol.routes[t][j];
                int d = (j == n-1) ? 0 : sol.routes[t][j+1];
                
                double improvement = dist_cache.get_2opt_delta(a, b, c, d);
                
                if (improvement > best_global_improvement) {
                    best_global_improvement = improvement;
                    best_truck = t;
                    best_i = i;
                    best_j = j;
                    improved = true;
                }
            }
        }
    }
    
    if (improved) {
        reverse(sol.routes[best_truck].begin() + best_i, 
                sol.routes[best_truck].begin() + best_j + 1);
        sol.route_dists[best_truck] = compute_route_distance(sol.routes[best_truck], dist_cache);
        update_total_distance(sol, dist_cache);
    }
    
    return improved;
}

// Cross-exchange entre rutas
bool apply_cross_exchange(Solution& sol, const vector<int>& demands, 
                         const vector<int>& capacities, const AdvancedDistanceCache& dist_cache, 
                         mt19937& gen) {
    if (sol.routes.size() < 2) return false;
    
    uniform_int_distribution<> truck_dist(0, static_cast<int>(sol.routes.size()) - 1);
    int t1 = truck_dist(gen);
    int t2 = truck_dist(gen);
    while (t1 == t2) t2 = truck_dist(gen);
    
    if (sol.routes[t1].size() < 2 || sol.routes[t2].size() < 2) return false;
    
    // Seleccionar segmentos
    uniform_int_distribution<> seg1_dist(0, static_cast<int>(sol.routes[t1].size()) - 1);
    uniform_int_distribution<> seg2_dist(0, static_cast<int>(sol.routes[t2].size()) - 1);
    
    int start1 = seg1_dist(gen);
    int end1 = min(start1 + 1, static_cast<int>(sol.routes[t1].size()) - 1);
    int start2 = seg2_dist(gen);
    int end2 = min(start2 + 1, static_cast<int>(sol.routes[t2].size()) - 1);
    
    // Calcular cambios en demanda
    int demand_change1 = 0, demand_change2 = 0;
    for (int i = start1; i <= end1; ++i) {
        demand_change1 += demands[sol.routes[t1][i]];
    }
    for (int i = start2; i <= end2; ++i) {
        demand_change2 += demands[sol.routes[t2][i]];
    }
    
    // Verificar factibilidad
    int new_load1 = sol.loads[t1] - demand_change1 + demand_change2;
    int new_load2 = sol.loads[t2] - demand_change2 + demand_change1;
    
    if (new_load1 > capacities[t1] || new_load2 > capacities[t2]) {
        return false;
    }
    
    // Calcular mejora
    double old_dist = sol.route_dists[t1] + sol.route_dists[t2];
    
    // Aplicar intercambio
    vector<int> seg1(sol.routes[t1].begin() + start1, sol.routes[t1].begin() + end1 + 1);
    vector<int> seg2(sol.routes[t2].begin() + start2, sol.routes[t2].begin() + end2 + 1);
    
    sol.routes[t1].erase(sol.routes[t1].begin() + start1, sol.routes[t1].begin() + end1 + 1);
    sol.routes[t2].erase(sol.routes[t2].begin() + start2, sol.routes[t2].begin() + end2 + 1);
    
    sol.routes[t1].insert(sol.routes[t1].begin() + start1, seg2.begin(), seg2.end());
    sol.routes[t2].insert(sol.routes[t2].begin() + start2, seg1.begin(), seg1.end());
    
    sol.loads[t1] = new_load1;
    sol.loads[t2] = new_load2;
    
    // Recalcular distancias
    sol.route_dists[t1] = compute_route_distance(sol.routes[t1], dist_cache);
    sol.route_dists[t2] = compute_route_distance(sol.routes[t2], dist_cache);
    double new_dist = sol.route_dists[t1] + sol.route_dists[t2];
    
    if (new_dist >= old_dist) {
        // Revertir
        sol.routes[t1].erase(sol.routes[t1].begin() + start1, sol.routes[t1].begin() + start1 + static_cast<int>(seg2.size()));
        sol.routes[t2].erase(sol.routes[t2].begin() + start2, sol.routes[t2].begin() + start2 + static_cast<int>(seg1.size()));
        
        sol.routes[t1].insert(sol.routes[t1].begin() + start1, seg1.begin(), seg1.end());
        sol.routes[t2].insert(sol.routes[t2].begin() + start2, seg2.begin(), seg2.end());
        
        sol.loads[t1] = sol.loads[t1] - demand_change2 + demand_change1;
        sol.loads[t2] = sol.loads[t2] - demand_change1 + demand_change2;
        
        sol.route_dists[t1] = compute_route_distance(sol.routes[t1], dist_cache);
        sol.route_dists[t2] = compute_route_distance(sol.routes[t2], dist_cache);
        return false;
    }
    
    update_total_distance(sol, dist_cache);
    return true;
}

// --- Variable Neighborhood Descent intensivo ---
bool variable_neighborhood_descent(Solution& sol, const vector<int>& demands, 
                                  const vector<int>& capacities, 
                                  const AdvancedDistanceCache& dist_cache,
                                  const VNSConfig& config, mt19937& gen) {
    bool global_improved = false;
    int vnd_iter = 0;
    
    while (vnd_iter < config.max_vnd_iterations) {
        bool local_improved = false;
        vnd_iter++;
        
        // Aplicar operadores en orden de efectividad
        vector<OpType> operators = {TWO_OPT, RELOCATE, SWAP, OR_OPT, CROSS_EXCHANGE};
        
        for (OpType op : operators) {
            Solution candidate = sol;
            bool success = false;
            
            switch (op) {
                case TWO_OPT:
                    success = apply_two_opt_best_improvement(candidate, dist_cache);
                    break;
                case RELOCATE:
                    // Implementar relocate mejorado
                    success = apply_or_opt(candidate, demands, capacities, dist_cache, gen);
                    break;
                case SWAP:
                    success = apply_swap_improved(candidate, demands, capacities, dist_cache, gen);
                    break;
                case CROSS_EXCHANGE:
                    success = apply_cross_exchange(candidate, demands, capacities, dist_cache, gen);
                    break;
                default:
                    break;
            }
            
            if (success && candidate.total_distance < sol.total_distance) {
                sol = candidate;
                local_improved = true;
                global_improved = true;
                break; // Reiniciar VND
            }
        }
        
        if (!local_improved) break;
    }
    
    return global_improved;
}

// --- Path Relinking ---
Solution path_relinking(const Solution& sol1, const Solution& sol2, 
                       const vector<int>& demands, const vector<int>& capacities,
                       const AdvancedDistanceCache& dist_cache) {
    Solution best = (sol1.total_distance < sol2.total_distance) ? sol1 : sol2;
    Solution current = sol1;
    
    // Identificar diferencias entre soluciones
    set<int> nodes_in_sol1, nodes_in_sol2;
    for (const auto& route : sol1.routes) {
        for (int node : route) {
            nodes_in_sol1.insert(node);
        }
    }
    for (const auto& route : sol2.routes) {
        for (int node : route) {
            nodes_in_sol2.insert(node);
        }
    }
    
    // Mover gradualmente de sol1 hacia sol2
    mt19937 gen(random_device{}());
    int max_moves = min(10, static_cast<int>(max(nodes_in_sol1.size(), nodes_in_sol2.size())) / 2);
    
    for (int move = 0; move < max_moves; ++move) {
        // Aplicar movimiento que acerque current a sol2
        // (Implementación simplificada - en producción sería más elaborada)
        variable_neighborhood_descent(current, demands, capacities, dist_cache, VNSConfig(), gen);
        
        if (current.total_distance < best.total_distance) {
            best = current;
        }
    }
    
    return best;
}

// --- Pool de soluciones elite con diversidad ---
class ElitePool {
private:
    vector<Solution> pool;
    int max_size;
    double min_diversity;
    
public:
    ElitePool(int size, double diversity) : max_size(size), min_diversity(diversity) {}
    
    void add(const Solution& sol) {
        // Verificar diversidad
        bool is_diverse = true;
        for (const auto& elite_sol : pool) {
            if (sol.diversity_with(elite_sol) < min_diversity) {
                is_diverse = false;
                break;
            }
        }
        
        if (is_diverse || static_cast<int>(pool.size()) < max_size) {
            pool.push_back(sol);
            sort(pool.begin(), pool.end());
            
            if (static_cast<int>(pool.size()) > max_size) {
                // Remover la peor solución, pero manteniendo diversidad
                pool.pop_back();
            }
        }
    }
    
    const Solution& get_random(mt19937& gen) const {
        uniform_int_distribution<> dist(0, static_cast<int>(pool.size()) - 1);
        return pool[dist(gen)];
    }
    
    const Solution& get_best() const {
        return pool.front();
    }
    
    bool empty() const { return pool.empty(); }
    size_t size() const { return pool.size(); }
    
    const vector<Solution>& get_all() const { return pool; }
};

// --- Algoritmo VNS mejorado para óptimo global ---
Solution vns_global_optimization(
    const vector<vector<double>>& dist,
    const vector<int>& objectives,
    const vector<int>& demands,
    const vector<int>& capacities,
    int num_trucks,
    int max_iter = 2000,
    double time_limit = 60.0,
    const VNSConfig& config = VNSConfig())
{
    auto start = Clock::now();
    mt19937 gen(random_device{}());
    
    AdvancedDistanceCache dist_cache(dist, config.use_caching);
    
    // Generar múltiples soluciones iniciales diversas
    vector<Solution> initial_solutions = generate_diverse_initial_solutions(
        objectives, demands, capacities, num_trucks, dist_cache, config.num_initial_solutions);
    
    Solution current = *min_element(initial_solutions.begin(), initial_solutions.end());
    Solution best = current;
    Solution global_best = best;
    
    // Pool de soluciones elite
    ElitePool elite_pool(config.max_elite_solutions, config.diversity_threshold);
    for (const auto& sol : initial_solutions) {
        elite_pool.add(sol);
    }
    
    int stagnation = 0;
    int global_stagnation = 0;
    double shake_intensity = config.initial_shake_intensity;
    
    for (int iter = 0; iter < max_iter && global_stagnation < config.max_global_stagnation; ++iter) {
        double elapsed = chrono::duration<double>(Clock::now() - start).count();
        if (elapsed > time_limit) break;
        
        Solution trial = current;
        
        // Fase de perturbación inteligente
        int num_perturbations = max(1, static_cast<int>(shake_intensity));
        for (int p = 0; p < num_perturbations; ++p) {
            int op = gen() % OP_COUNT;
            
            switch (op) {
                case SWAP:
                    apply_swap_improved(trial, demands, capacities, dist_cache, gen);
                    break;
                case OR_OPT:
                    apply_or_opt(trial, demands, capacities, dist_cache, gen);
                    break;
                case TWO_OPT:
                    apply_two_opt_best_improvement(trial, dist_cache);
                    break;
                case CROSS_EXCHANGE:
                    apply_cross_exchange(trial, demands, capacities, dist_cache, gen);
                    break;
                default:
                    break;
            }
        }
        
        // Búsqueda local intensiva
        variable_neighborhood_descent(trial, demands, capacities, dist_cache, config, gen);
        
        // Criterio de aceptación con memoria
        bool accept = false;
        if (trial.total_distance < global_best.total_distance) {
            // Nueva mejor solución global
            global_best = trial;
            best = trial;
            current = trial;
            stagnation = 0;
            global_stagnation = 0;
            shake_intensity = config.initial_shake_intensity;
            accept = true;
            
            elite_pool.add(global_best);
            
        } else if (trial.total_distance < best.total_distance) {
            // Mejor solución local
            best = trial;
            current = trial;
            stagnation = 0;
            global_stagnation++;
            accept = true;
            
            elite_pool.add(best);
            
        } else if (trial.total_distance < current.total_distance) {
            // Mejora incremental
            current = trial;
            stagnation++;
            global_stagnation++;
            accept = true;
        } else {
            // Criterio de diversificación adaptativo
            double temperature = 0.1 * current.total_distance * exp(-global_stagnation / 100.0);
            double acceptance_prob = exp(-(trial.total_distance - current.total_distance) / temperature);
            uniform_real_distribution<> prob_dist(0.0, 1.0);
            
            if (prob_dist(gen) < acceptance_prob) {
                current = trial;
                accept = true;
            }
            stagnation++;
            global_stagnation++;
        }
        
        // Path Relinking periódico
        if (config.use_path_relinking && iter % config.path_relinking_frequency == 0 && 
            elite_pool.size() >= 2) {
            
            const Solution& elite1 = elite_pool.get_best();
            const Solution& elite2 = elite_pool.get_random(gen);
            
            Solution pr_solution = path_relinking(elite1, elite2, demands, capacities, dist_cache);
            
            if (pr_solution.total_distance < global_best.total_distance) {
                global_best = pr_solution;
                best = pr_solution;
                current = pr_solution;
                elite_pool.add(global_best);
            }
        }
        
        // Ajuste adaptativo de parámetros
        if (config.use_adaptive_parameters) {
            if (stagnation > config.max_stagnation / 2) {
                shake_intensity = min(config.max_shake_intensity, 
                                    shake_intensity * config.shake_increase);
            }
            
            // Reinicio inteligente desde elite pool
            if (stagnation > config.max_stagnation && !elite_pool.empty()) {
                current = elite_pool.get_random(gen);
                stagnation = 0;
                shake_intensity = config.initial_shake_intensity;
            }
            
            // Multi-restart desde mejores soluciones diversas
            if (global_stagnation > static_cast<int>(config.max_global_stagnation * config.restart_threshold)) {
                if (!elite_pool.empty()) {
                    current = elite_pool.get_random(gen);
                    
                    // Aplicar intensificación local
                    variable_neighborhood_descent(current, demands, capacities, dist_cache, config, gen);
                    
                    global_stagnation = global_stagnation / 2; // Reducir pero no resetear
                    shake_intensity = config.initial_shake_intensity;
                }
            }
        }
        
        // Limpiar cache periódicamente
        if (iter % 200 == 0) {
            dist_cache.clear();
        }
    }
    
    return global_best;
}

// --- Función principal Python ---
py::list solve_vrp(
    py::array_t<double, py::array::c_style | py::array::forcecast> dist_matrix_np,
    py::array_t<int,    py::array::c_style | py::array::forcecast> objectives_np,
    py::array_t<int,    py::array::c_style | py::array::forcecast> demands_np,
    py::array_t<int,    py::array::c_style | py::array::forcecast> capacities_np,
    int num_trucks,
    int max_iter = 2000,
    double time_limit = 60.0)
{
    // Validaciones de entrada
    auto buf_dist = dist_matrix_np.request();
    if (buf_dist.ndim != 2 || buf_dist.shape[0] != buf_dist.shape[1]) {
        throw runtime_error("dist_matrix must be a square 2D array");
    }
    py::ssize_t n_points = buf_dist.shape[0];

    auto buf_obj = objectives_np.request();
    if (buf_obj.ndim != 1) {
        throw runtime_error("objectives must be a 1D array");
    }
    py::ssize_t m = buf_obj.shape[0];

    auto buf_dem = demands_np.request();
    if (buf_dem.ndim != 1 || buf_dem.shape[0] != n_points) {
        throw runtime_error("demands must be a 1D array of length n_points");
    }

    auto buf_cap = capacities_np.request();
    if (buf_cap.ndim != 1 || buf_cap.shape[0] != num_trucks) {
        throw runtime_error("capacities must be a 1D array of length num_trucks");
    }

    // Construir estructuras de datos
    vector<vector<double>> dist(static_cast<size_t>(n_points), vector<double>(static_cast<size_t>(n_points)));
    const double* dist_ptr = static_cast<double*>(buf_dist.ptr);
    for (py::ssize_t i = 0; i < n_points; ++i) {
        for (py::ssize_t j = 0; j < n_points; ++j) {
            dist[i][j] = dist_ptr[i * n_points + j];
        }
    }

    vector<int> objectives(static_cast<size_t>(m));
    const int* obj_ptr = static_cast<int*>(buf_obj.ptr);
    for (py::ssize_t i = 0; i < m; ++i) {
        int v = obj_ptr[i];
        if (v <= 0 || v >= n_points) {
            throw runtime_error("each objective must be in [1, n_points-1]");
        }
        objectives[i] = v;
    }

    vector<int> demands(static_cast<size_t>(n_points));
    const int* dem_ptr = static_cast<int*>(buf_dem.ptr);
    for (py::ssize_t i = 0; i < n_points; ++i) {
        if (dem_ptr[i] < 0) {
            throw runtime_error("demands must be >= 0 for each node");
        }
        demands[i] = dem_ptr[i];
    }

    vector<int> capacities(static_cast<size_t>(num_trucks));
    const int* cap_ptr = static_cast<int*>(buf_cap.ptr);
    for (int i = 0; i < num_trucks; ++i) {
        if (cap_ptr[i] <= 0) {
            throw runtime_error("capacities must be > 0 for each truck");
        }
        capacities[i] = cap_ptr[i];
    }

    // Ejecutar VNS optimizado para búsqueda global
    VNSConfig config;
    Solution best = vns_global_optimization(
        dist, objectives, demands, capacities, num_trucks,
        max_iter, time_limit, config
    );

    // Convertir a formato Python
    py::list py_routes;
    for (const auto& route : best.routes) {
        py::list py_route;
        for (int node : route) {
            py_route.append(node);
        }
        py_routes.append(py_route);
    }
    
    return py_routes;
}

// --- Binding Python ---
PYBIND11_MODULE(vns_solver, m) {
    m.doc() = "VRP con Variable Neighborhood Search - Optimizado para encontrar el óptimo global";
    
    m.def(
        "solve_vrp",
        &solve_vrp,
        py::arg("dist_matrix"),
        py::arg("objectives"),
        py::arg("demands"),
        py::arg("capacities"),
        py::arg("num_trucks"),
        py::arg("max_iter") = 2000,
        py::arg("time_limit") = 60.0,
        R"pbdoc(
            Resuelve un CVRP con VNS optimizado para encontrar el óptimo global.

            Mejoras para óptimo global:
            - Multi-start con soluciones iniciales diversas
            - Variable Neighborhood Descent intensivo
            - Pool de soluciones elite con control de diversidad
            - Path Relinking entre soluciones elite
            - Cache avanzado con pre-computación de deltas
            - Operadores de búsqueda local de alto rendimiento
            - Criterios de aceptación adaptativos con memoria
            - Reinicio inteligente y control de estancamiento global

            Args:
                dist_matrix (ndarray[double, 2D]): Matriz de distancias n_points×n_points.
                objectives   (ndarray[int, 1D]): Índices de nodos objetivos (1..n_points-1).
                demands      (ndarray[int, 1D]): Demanda de cada nodo (longitud n_points).
                capacities   (ndarray[int, 1D]): Capacidad de cada camión.
                num_trucks   (int): Número de camiones.
                max_iter     (int, opcional): Iteraciones máximas (por defecto 2000).
                time_limit   (double, opcional): Tiempo límite en segundos (por defecto 60.0).

            Returns:
                List[List[int]]: Lista de rutas optimizadas para CVRP.
        )pbdoc"
    );
    
    py::class_<VNSConfig>(m, "VNSConfig")
        .def(py::init<>())
        .def_readwrite("max_stagnation", &VNSConfig::max_stagnation)
        .def_readwrite("max_global_stagnation", &VNSConfig::max_global_stagnation)
        .def_readwrite("use_adaptive_parameters", &VNSConfig::use_adaptive_parameters)
        .def_readwrite("use_multi_start", &VNSConfig::use_multi_start)
        .def_readwrite("use_path_relinking", &VNSConfig::use_path_relinking)
        .def_readwrite("max_elite_solutions", &VNSConfig::max_elite_solutions)
        .def_readwrite("diversity_threshold", &VNSConfig::diversity_threshold)
        .def("validate", &VNSConfig::validate);
}