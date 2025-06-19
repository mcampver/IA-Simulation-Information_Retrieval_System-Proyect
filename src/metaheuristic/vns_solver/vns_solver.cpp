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
#include <stdexcept>
#include <string>
#include <memory>
#include <cassert>

#ifdef _OPENMP
#include <omp.h>
#endif

namespace py = pybind11;
using namespace std;
using Clock = chrono::steady_clock;

// --- Configuración global del algoritmo (ahora parametrizable) ---
struct VNSConfig {
    int openmp_threshold = 5;
    int top_k_insert = 20;
    double intensification_factor = 1.2;
    double diversification_factor = 0.9;
    double initial_shake_intensity = 2.0;
    double max_shake_intensity = 10.0;
    double shake_increase = 1.05;
    int max_stagnation = 10;
    bool use_caching = true;
    
    // Validación de configuración
    void validate() const {
        if (openmp_threshold < 1) throw invalid_argument("openmp_threshold debe ser positivo");
        if (top_k_insert < 1) throw invalid_argument("top_k_insert debe ser positivo");
        if (intensification_factor <= 1.0) throw invalid_argument("intensification_factor debe ser > 1.0");
        if (diversification_factor >= 1.0) throw invalid_argument("diversification_factor debe ser < 1.0");
        if (initial_shake_intensity <= 0) throw invalid_argument("initial_shake_intensity debe ser positivo");
        if (max_shake_intensity <= initial_shake_intensity) 
            throw invalid_argument("max_shake_intensity debe ser mayor que initial_shake_intensity");
        if (shake_increase <= 1.0) throw invalid_argument("shake_increase debe ser > 1.0");
    }
};

// --- Estructura de datos compatible con ts_solver ---
struct Solution {
    vector<vector<int>> routes;   // rutas por camión (lista de nodos, sin depósito 0)
    vector<int> loads;            // carga total en cada camión
    vector<double> route_dists;   // distancia de cada ruta (incluye ida y vuelta a 0)
    double total_distance;        // suma de route_dists
};

// Cache de distancias para mejorar rendimiento
class DistanceCache {
private:
    const vector<vector<double>>& D;
    unordered_map<size_t, double> cache;
    bool enabled;
    
    // Función hash para pares (i,j)
    size_t hash_pair(int i, int j) const {
        return (static_cast<size_t>(i) << 32) | static_cast<size_t>(j);
    }
    
public:
    DistanceCache(const vector<vector<double>>& distances, bool use_cache)
        : D(distances), enabled(use_cache) {}
    
    double get(int i, int j) {
        if (!enabled) return D[i][j];
        
        size_t key = hash_pair(i, j);
        auto it = cache.find(key);
        if (it != cache.end()) {
            return it->second;
        }
        double dist = D[i][j];
        cache[key] = dist;
        return dist;
    }
    
    void clear() {
        if (enabled) cache.clear();
    }
};

// Calcula la distancia de una ruta (incluye ida/vuelta al depósito 0)
double compute_route_distance(const vector<int>& route, const vector<vector<double>>& dist) {
    if (route.empty()) return 0.0;
    double d = dist[0][route.front()];
    for (size_t i = 0; i + 1 < route.size(); ++i) {
        d += dist[route[i]][route[i+1]];
    }
    d += dist[route.back()][0];
    return d;
}

inline void update_total_distance(Solution &sol) {
    double sum = 0.0;
    for (double x : sol.route_dists) sum += x;
    sol.total_distance = sum;
}

// Genera solución inicial usando algoritmo de ahorros
Solution generate_initial_solution_vns(
    const vector<int>& objectives,
    const vector<int>& demands,
    const vector<int>& capacities,
    int num_trucks,
    const vector<vector<double>>& dist)
{
    Solution sol;
    sol.routes.assign(num_trucks, {});
    sol.loads.assign(num_trucks, 0);
    sol.route_dists.assign(num_trucks, 0.0);

    // Inicialización greedy mejorada
    vector<bool> assigned(objectives.size(), false);
    
    for (int obj : objectives) {
        bool placed = false;
        int best_truck = -1;
        double best_cost_increase = numeric_limits<double>::infinity();
        
        // Encontrar el mejor camión para este objetivo
        for (int t = 0; t < num_trucks; ++t) {
            if (sol.loads[t] + demands[obj] <= capacities[t]) {
                // Calcular incremento de costo
                double cost_increase;
                if (sol.routes[t].empty()) {
                    cost_increase = dist[0][obj] * 2; // Ida y vuelta al depósito
                } else {
                    int last_node = sol.routes[t].back();
                    cost_increase = dist[last_node][obj] + dist[obj][0] - dist[last_node][0];
                }
                
                if (cost_increase < best_cost_increase) {
                    best_cost_increase = cost_increase;
                    best_truck = t;
                    placed = true;
                }
            }
        }
        
        if (placed && best_truck >= 0) {
            sol.routes[best_truck].push_back(obj);
            sol.loads[best_truck] += demands[obj];
        } else {
            // Si no cabe en ningún camión, usar round-robin
            int t = obj % num_trucks;
            sol.routes[t].push_back(obj);
            sol.loads[t] += demands[obj];
        }
    }

    // Calcular distancias de rutas
    for (int t = 0; t < num_trucks; ++t) {
        sol.route_dists[t] = compute_route_distance(sol.routes[t], dist);
    }
    update_total_distance(sol);
    return sol;
}

// Operadores de búsqueda local
enum OpType { SWAP=0, RELOCATE=1, TWO_OPT=2, OP_COUNT=3 };

bool apply_swap_vns(Solution& sol, const vector<int>& demands, const vector<int>& capacities, 
                    const vector<vector<double>>& dist, mt19937& gen) {
    if (sol.routes.size() < 2) return false;
    
    uniform_int_distribution<> truck_dist(0, sol.routes.size() - 1);
    int t1 = truck_dist(gen);
    int t2 = truck_dist(gen);
    if (t1 == t2) t2 = (t1 + 1) % sol.routes.size();
    
    if (sol.routes[t1].empty() || sol.routes[t2].empty()) return false;
    
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
    
    // Aplicar swap
    swap(sol.routes[t1][pos1], sol.routes[t2][pos2]);
    sol.loads[t1] = new_load1;
    sol.loads[t2] = new_load2;
    
    // Recalcular distancias
    sol.route_dists[t1] = compute_route_distance(sol.routes[t1], dist);
    sol.route_dists[t2] = compute_route_distance(sol.routes[t2], dist);
    update_total_distance(sol);
    
    return true;
}

bool apply_relocate_vns(Solution& sol, const vector<int>& demands, const vector<int>& capacities,
                        const vector<vector<double>>& dist, mt19937& gen) {
    if (sol.routes.size() < 2) return false;
    
    uniform_int_distribution<> truck_dist(0, sol.routes.size() - 1);
    int t1 = truck_dist(gen);
    int t2 = truck_dist(gen);
    if (t1 == t2) t2 = (t1 + 1) % sol.routes.size();
    
    if (sol.routes[t1].empty()) return false;
    
    uniform_int_distribution<> pos_dist(0, sol.routes[t1].size() - 1);
    int pos = pos_dist(gen);
    int node = sol.routes[t1][pos];
    
    // Verificar factibilidad
    if (sol.loads[t2] + demands[node] > capacities[t2]) {
        return false;
    }
    
    // Aplicar relocate
    sol.routes[t1].erase(sol.routes[t1].begin() + pos);
    sol.loads[t1] -= demands[node];
    
    if (!sol.routes[t2].empty()) {
        uniform_int_distribution<> insert_dist(0, sol.routes[t2].size());
        int insert_pos = insert_dist(gen);
        sol.routes[t2].insert(sol.routes[t2].begin() + insert_pos, node);
    } else {
        sol.routes[t2].push_back(node);
    }
    sol.loads[t2] += demands[node];
    
    // Recalcular distancias
    sol.route_dists[t1] = compute_route_distance(sol.routes[t1], dist);
    sol.route_dists[t2] = compute_route_distance(sol.routes[t2], dist);
    update_total_distance(sol);
    
    return true;
}

bool apply_two_opt_vns(Solution& sol, const vector<vector<double>>& dist, mt19937& gen) {
    if (sol.routes.empty()) return false;
    
    uniform_int_distribution<> truck_dist(0, sol.routes.size() - 1);
    int t = truck_dist(gen);
    
    if (sol.routes[t].size() < 4) return false;
    
    int n = sol.routes[t].size();
    uniform_int_distribution<> i_dist(0, n - 3);
    int i = i_dist(gen);
    uniform_int_distribution<> j_dist(i + 2, n - 1);
    int j = j_dist(gen);
    
    // Aplicar 2-opt
    reverse(sol.routes[t].begin() + i, sol.routes[t].begin() + j + 1);
    
    // Recalcular distancia
    sol.route_dists[t] = compute_route_distance(sol.routes[t], dist);
    update_total_distance(sol);
    
    return true;
}

// --- Algoritmo VNS principal ---
Solution vns_search(
    const vector<vector<double>>& dist,
    const vector<int>& objectives,
    const vector<int>& demands,
    const vector<int>& capacities,
    int num_trucks,
    int max_iter = 1000,
    double time_limit = 30.0,
    const VNSConfig& config = VNSConfig())
{
    auto start = Clock::now();
    mt19937 gen(random_device{}());
    
    // Generar solución inicial
    Solution current = generate_initial_solution_vns(objectives, demands, capacities, num_trucks, dist);
    Solution best = current;
    
    int stagnation = 0;
    int max_stagnation = config.max_stagnation > 0 ? config.max_stagnation : max_iter / 5;
    double shake_intensity = config.initial_shake_intensity;
    
    for (int iter = 0; iter < max_iter && stagnation < max_stagnation; ++iter) {
        // Verificar límite de tiempo
        double elapsed = chrono::duration<double>(Clock::now() - start).count();
        if (elapsed > time_limit) break;
        
        Solution trial = current;
        
        // Fase de perturbación (shaking)
        int num_perturbations = max(1, static_cast<int>(shake_intensity));
        for (int p = 0; p < num_perturbations; ++p) {
            int op = gen() % OP_COUNT;
            
            switch (op) {
                case SWAP:
                    apply_swap_vns(trial, demands, capacities, dist, gen);
                    break;
                case RELOCATE:
                    apply_relocate_vns(trial, demands, capacities, dist, gen);
                    break;
                case TWO_OPT:
                    apply_two_opt_vns(trial, dist, gen);
                    break;
            }
        }
        
        // Búsqueda local simple (VND)
        bool improved = true;
        while (improved) {
            improved = false;
            Solution candidate = trial;
            
            // Probar cada operador
            for (int op = 0; op < OP_COUNT; ++op) {
                bool success = false;
                switch (op) {
                    case SWAP:
                        success = apply_swap_vns(candidate, demands, capacities, dist, gen);
                        break;
                    case RELOCATE:
                        success = apply_relocate_vns(candidate, demands, capacities, dist, gen);
                        break;
                    case TWO_OPT:
                        success = apply_two_opt_vns(candidate, dist, gen);
                        break;
                }
                
                if (success && candidate.total_distance < trial.total_distance) {
                    trial = candidate;
                    improved = true;
                    break;
                }
            }
        }
        
        // Evaluar solución
        if (trial.total_distance < best.total_distance) {
            best = trial;
            current = trial;
            stagnation = 0;
            shake_intensity = config.initial_shake_intensity;
        } else {
            current = trial;
            stagnation++;
            shake_intensity = min(config.max_shake_intensity, 
                                  shake_intensity * config.shake_increase);
        }
    }
    
    return best;
}

// Función principal compatible con ts_solver
py::list solve_vrp(
    py::array_t<double, py::array::c_style | py::array::forcecast> dist_matrix_np,
    py::array_t<int,    py::array::c_style | py::array::forcecast> objectives_np,
    py::array_t<int,    py::array::c_style | py::array::forcecast> demands_np,
    py::array_t<int,    py::array::c_style | py::array::forcecast> capacities_np,
    int num_trucks,
    int max_iter = 1000,
    double time_limit = 30.0)
{
    // Validar entrada
    auto buf_dist = dist_matrix_np.request();
    if (buf_dist.ndim != 2 || buf_dist.shape[0] != buf_dist.shape[1]) {
        throw runtime_error("dist_matrix must be a square 2D array");
    }
    int n_points = buf_dist.shape[0];

    auto buf_obj = objectives_np.request();
    if (buf_obj.ndim != 1) {
        throw runtime_error("objectives must be a 1D array");
    }
    int m = buf_obj.shape[0];

    auto buf_dem = demands_np.request();
    if (buf_dem.ndim != 1 || buf_dem.shape[0] != n_points) {
        throw runtime_error("demands must be a 1D array of length n_points");
    }

    auto buf_cap = capacities_np.request();
    if (buf_cap.ndim != 1 || buf_cap.shape[0] != num_trucks) {
        throw runtime_error("capacities must be a 1D array of length num_trucks");
    }

    // Construir matriz de distancias
    vector<vector<double>> dist(n_points, vector<double>(n_points));
    const double* dist_ptr = static_cast<double*>(buf_dist.ptr);
    for (int i = 0; i < n_points; ++i) {
        for (int j = 0; j < n_points; ++j) {
            dist[i][j] = dist_ptr[i * n_points + j];
        }
    }

    // Extraer objetivos
    vector<int> objectives(m);
    const int* obj_ptr = static_cast<int*>(buf_obj.ptr);
    for (int i = 0; i < m; ++i) {
        int v = obj_ptr[i];
        if (v <= 0 || v >= n_points) {
            throw runtime_error("each objective must be in [1, n_points-1]");
        }
        objectives[i] = v;
    }

    // Extraer demandas
    vector<int> demands(n_points);
    const int* dem_ptr = static_cast<int*>(buf_dem.ptr);
    for (int i = 0; i < n_points; ++i) {
        if (dem_ptr[i] < 0) {
            throw runtime_error("demands must be >= 0 for each node");
        }
        demands[i] = dem_ptr[i];
    }

    // Extraer capacidades
    vector<int> capacities(num_trucks);
    const int* cap_ptr = static_cast<int*>(buf_cap.ptr);
    for (int i = 0; i < num_trucks; ++i) {
        if (cap_ptr[i] <= 0) {
            throw runtime_error("capacities must be > 0 for each truck");
        }
        capacities[i] = cap_ptr[i];
    }

    // Ejecutar VNS
    Solution best = vns_search(
        dist, objectives, demands, capacities, num_trucks,
        max_iter, time_limit
    );

    // Convertir routes a py::list (mismo formato que ts_solver)
    py::list py_routes;
    for (auto &r : best.routes) {
        py::list rr;
        for (int node : r) {
            rr.append(node);
        }
        py_routes.append(rr);
    }
    return py_routes;
}

PYBIND11_MODULE(vns_solver, m) {
    m.doc() = "VRP con Variable Neighborhood Search (VNS) - formato compatible con ts_solver";
    
    // Función principal compatible
    m.def(
        "solve_vrp",
        &solve_vrp,
        py::arg("dist_matrix"),
        py::arg("objectives"),
        py::arg("demands"),
        py::arg("capacities"),
        py::arg("num_trucks"),
        py::arg("max_iter") = 1000,
        py::arg("time_limit") = 30.0,
        R"pbdoc(
            Resuelve un VRP con Variable Neighborhood Search.

            Args:
                dist_matrix (ndarray[double, 2D]): Matriz de distancias n_points×n_points.
                objectives   (ndarray[int, 1D]): Índices de nodos objetivos (1..n_points-1).
                demands      (ndarray[int, 1D]): Demanda de cada nodo (longitud n_points).
                capacities   (ndarray[int, 1D]): Capacidad de cada camión.
                num_trucks   (int): Número de camiones.
                max_iter     (int, opcional): Iteraciones máximas (por defecto 1000).
                time_limit   (double, opcional): Tiempo límite en segundos (por defecto 30.0).

            Returns:
                List[List[int]]: Lista de rutas, cada ruta es un array de nodos (sin incluir depósito).
        )pbdoc"
    );
    
    // Mantener funciones legacy para compatibilidad con código existente
    py::class_<VNSConfig>(m, "VNSConfig")
        .def(py::init<>())
        .def_readwrite("openmp_threshold", &VNSConfig::openmp_threshold)
        .def_readwrite("max_stagnation", &VNSConfig::max_stagnation)
        .def("validate", &VNSConfig::validate);
}
