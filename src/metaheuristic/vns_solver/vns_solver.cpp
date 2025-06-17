#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <vector>
#include <algorithm>
#include <random>
#include <limits>
#include <numeric>
#include <chrono>
#include <unordered_map>  // Para caching de distancias frecuentes
#include <stdexcept>      // Para manejo de excepciones
#include <string>         // Para mensajes de error
#include <memory>         // Para punteros inteligentes
#include <cassert>        // Para aserciones

#ifdef _OPENMP
#include <omp.h>
#endif

namespace py = pybind11;
using namespace std;
using Clock = chrono::steady_clock;

// --- Configuración global del algoritmo (ahora parametrizable) ---
struct VNSConfig {
    int openmp_threshold = 5;   // Umbral para paralelización
    int top_k_insert = 20;      // Candidatos a considerar para inserción
    double intensification_factor = 1.2;  // Factor de intensificación para operadores exitosos
    double diversification_factor = 0.9;  // Factor de diversificación
    double initial_shake_intensity = 2.0; // Intensidad inicial de perturbación
    double max_shake_intensity = 10.0;    // Intensidad máxima de perturbación
    double shake_increase = 1.05;         // Aumento de intensidad por estancamiento
    int max_stagnation = 10;     // Máximas iteraciones sin mejora (0 = max_iter/5)
    bool use_caching = true;    // Usar caché para distancias frecuentes
    
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

// --- Estructuras de datos principales (mejoradas) ---
struct Route {
    vector<int> nodes;
    double cost;
    int load;
    vector<double> prefix_cost;
    int vehicle_id;
    
    // Constructor con valores por defecto
    Route(vector<int> _nodes = {}, double _cost = 0.0, int _load = 0, 
          vector<double> _prefix = {}, int _vid = -1) 
        : nodes(std::move(_nodes)), cost(_cost), load(_load), 
          prefix_cost(std::move(_prefix)), vehicle_id(_vid) {}
    
    // Método para validar ruta
    bool is_valid(const vector<int>& demands, const vector<int>& capacities) const {
        if (vehicle_id < 0 || vehicle_id >= capacities.size()) 
            return false;
        return load <= capacities[vehicle_id];
    }
    
    // Método para realizar deep copy
    Route clone() const {
        return {nodes, cost, load, prefix_cost, vehicle_id};
    }
};

struct Solution {
    vector<Route> routes;
    double total_cost;
    
    // Constructor
    Solution(vector<Route> _routes = {}, double _cost = 0.0)
        : routes(std::move(_routes)), total_cost(_cost) {}
    
    // Validación de solución
    bool is_valid(const vector<int>& demands, const vector<int>& capacities) const {
        for (const auto& route : routes) {
            if (!route.is_valid(demands, capacities))
                return false;
        }
        return true;
    }
    
    // Método para realizar deep copy
    Solution clone() const {
        vector<Route> new_routes;
        new_routes.reserve(routes.size());
        for (const auto& r : routes) {
            new_routes.push_back(r.clone());
        }
        return {std::move(new_routes), total_cost};
    }
};

// Cache de distancias para mejorar rendimiento en matrices grandes
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

// --- Funciones Auxiliares mejoradas ---

// Actualiza el coste total y los costes acumulados de una ruta
void update_route(Route &r, DistanceCache& D) {
    int n = r.nodes.size();
    r.prefix_cost.resize(n+1);
    double acc = 0.0; 
    int prev = 0;  // Comenzamos en el depósito (nodo 0)
    r.prefix_cost[0] = 0.0;
    
    for (int i = 0; i < n; ++i) {
        // Acumulamos la distancia del nodo anterior al actual
        acc += D.get(prev, r.nodes[i]);
        prev = r.nodes[i];
        r.prefix_cost[i+1] = acc;  // Guardamos coste acumulado hasta este punto
    }
    // Añadimos el retorno al depósito
    acc += D.get(prev, 0);
    r.cost = acc;  // Coste total de la ruta
}

// Validación de datos de entrada
void validate_input(
    const vector<vector<double>>& D,
    const vector<int>& dem,
    const vector<int>& caps)
{
    // Validar dimensiones
    if (D.empty() || D[0].empty())
        throw invalid_argument("La matriz de distancias no puede estar vacía");
    
    if (D.size() != D[0].size())
        throw invalid_argument("La matriz de distancias debe ser cuadrada");
    
    if (dem.empty() || dem[0] != 0)
        throw invalid_argument("El vector de demandas debe comenzar con 0 (depósito)");
    
    if (dem.size() != D.size())
        throw invalid_argument("El tamaño del vector de demandas no coincide con la matriz de distancias");
    
    if (caps.empty())
        throw invalid_argument("El vector de capacidades no puede estar vacío");
    
    // Validar valores
    for (const auto& row : D) {
        if (row.size() != D.size())
            throw invalid_argument("Matriz de distancias mal formada (filas de longitud desigual)");
        
        for (double val : row) {
            if (val < 0)
                throw invalid_argument("Las distancias no pueden ser negativas");
        }
    }
    
    for (int i = 1; i < dem.size(); ++i) {
        if (dem[i] <= 0)
            throw invalid_argument("Las demandas de los clientes deben ser positivas");
    }
    
    for (int cap : caps) {
        if (cap <= 0)
            throw invalid_argument("Las capacidades de los vehículos deben ser positivas");
    }
}

// --- Operadores de búsqueda local (mejorados y con mejores nombres) ---
enum OpType { SWAP=0, RELOCATE=1, TWO_OPT=2, OP_COUNT=3 };

// Operador SWAP: intercambia un cliente aleatorio entre dos rutas
bool apply_swap(Route &source, Route &target, 
               const vector<int>& demands, const vector<int>& capacities) {
    if (source.nodes.empty() || target.nodes.empty()) return false;
    
    static thread_local mt19937 gen(random_device{}());
    uniform_int_distribution<> dist_source(0, source.nodes.size()-1);
    uniform_int_distribution<> dist_target(0, target.nodes.size()-1);
    
    int pos_source = dist_source(gen);
    int pos_target = dist_target(gen);
    
    int node_source = source.nodes[pos_source];
    int node_target = target.nodes[pos_target];
    
    // Verificar factibilidad antes de realizar el intercambio
    int new_load_source = source.load - demands[node_source] + demands[node_target];
    int new_load_target = target.load - demands[node_target] + demands[node_source];
    
    if (new_load_source > capacities[source.vehicle_id] ||
        new_load_target > capacities[target.vehicle_id]) {
        return false; // El intercambio no es factible
    }
    
    // Realizar el intercambio
    swap(source.nodes[pos_source], target.nodes[pos_target]);
    source.load = new_load_source;
    target.load = new_load_target;
    
    return true;
}

// Operador RELOCATE: mueve un cliente de una ruta a otra
bool apply_relocate(Route &source, Route &target, 
                   const vector<int>& demands, const vector<int>& capacities) {
    if (source.nodes.empty()) return false;
    
    static thread_local mt19937 gen(random_device{}());
    uniform_int_distribution<> dist_source(0, source.nodes.size()-1);
    
    int pos_source = dist_source(gen);
    int node = source.nodes[pos_source];
    
    // Verificar factibilidad antes de realizar la reubicación
    if (target.load + demands[node] > capacities[target.vehicle_id]) {
        return false; // La reubicación no es factible
    }
    
    // Eliminar de la ruta fuente
    source.nodes.erase(source.nodes.begin() + pos_source);
    source.load -= demands[node];
    
    // Insertar en la ruta destino
    uniform_int_distribution<> dist_target(0, target.nodes.size());
    int pos_target = dist_target(gen);
    target.nodes.insert(target.nodes.begin() + pos_target, node);
    target.load += demands[node];
    
    return true;
}

// Operador 2-OPT: invierte un segmento de la ruta para mejorar el orden
bool apply_two_opt(Route &route) {
    int n = route.nodes.size(); 
    if (n < 4) return false;
    
    static thread_local mt19937 gen(random_device{}());
    uniform_int_distribution<> dist_i(0, n-3);
    int i = dist_i(gen);
    uniform_int_distribution<> dist_j(i+2, n-1);
    int j = dist_j(gen);
    
    // Invertir el segmento [i+1, j]
    reverse(route.nodes.begin()+i+1, route.nodes.begin()+j+1);
    
    return true;
}

// Clase base para operadores (mejora la modularidad y extensibilidad)
class Operator {
public:
    virtual ~Operator() = default;
    virtual bool apply(Route& source, Route& target, 
                      const vector<int>& demands, const vector<int>& capacities) const = 0;
    virtual string name() const = 0;
};

class SwapOperator : public Operator {
public:
    bool apply(Route& source, Route& target, 
              const vector<int>& demands, const vector<int>& capacities) const override {
        return apply_swap(source, target, demands, capacities);
    }
    string name() const override { return "SWAP"; }
};

class RelocateOperator : public Operator {
public:
    bool apply(Route& source, Route& target, 
              const vector<int>& demands, const vector<int>& capacities) const override {
        return apply_relocate(source, target, demands, capacities);
    }
    string name() const override { return "RELOCATE"; }
};

class TwoOptOperator : public Operator {
public:
    bool apply(Route& source, Route& target, 
              const vector<int>& demands, const vector<int>& capacities) const override {
        if (&source != &target) return false; // Two-opt solo funciona en una misma ruta
        return apply_two_opt(source);
    }
    string name() const override { return "TWO-OPT"; }
};

// --- Algoritmo de construcción inicial mejorado ---
Solution initial_solution_hetero_savings(
    DistanceCache& D,
    const vector<int>& demands,
    const vector<int>& capacities,
    const VNSConfig& config)
{
    int m = demands.size() - 1;  // Número de clientes (sin contar el depósito)
    int K = capacities.size();   // Número de vehículos disponibles
    
    // Inicializamos las rutas vacías, una por cada vehículo
    vector<Route> routes;
    routes.reserve(K);
    for (int i = 0; i < K; ++i)
        routes.push_back(Route{{}, 0.0, 0, {}, i});
    
    // Calculamos los ahorros (savings) para cada par de clientes
    struct Saving {int i, j; double value;};
    vector<Saving> savings;
    savings.reserve(m * (m-1) / 2);
    
    for (int i = 1; i <= m; ++i) {
        for (int j = i+1; j <= m; ++j) {
            double saving = D.get(0, i) + D.get(0, j) - D.get(i, j);
            savings.push_back({i, j, saving});
        }
    }
    
    // Ordenamos los ahorros de mayor a menor
    sort(savings.begin(), savings.end(), 
         [](const Saving& a, const Saving& b) { return a.value > b.value; });
    
    // Inicialmente, cada cliente está en su propia ruta temporal
    vector<Route> temp;
    temp.reserve(m);
    for (int i = 1; i <= m; ++i) {
        double cost = D.get(0, i) * 2; // Ida y vuelta al depósito
        temp.push_back(Route{{i}, cost, demands[i], {0.0, D.get(0, i)}, -1});
    }
    
    // Fusionamos rutas según los ahorros calculados, respetando capacidades
    for (const auto& saving : savings) {
        int route_i = -1, route_j = -1;
        
        // Buscamos las rutas que tienen los clientes i y j en sus extremos
        for (int k = 0; k < temp.size(); ++k) {
            const auto& nodes = temp[k].nodes;
            if (nodes.empty()) continue;
            
            if (nodes.front() == saving.i) route_i = k;
            if (nodes.back() == saving.j) route_j = k;
        }
        
        // Si encontramos ambos clientes y están en rutas diferentes
        if (route_i >= 0 && route_j >= 0 && route_i != route_j) {
            int combined_load = temp[route_i].load + temp[route_j].load;
            
            // Intentamos asignar a un vehículo con capacidad suficiente
            for (int v = 0; v < K; ++v) {
                if (combined_load <= capacities[v]) {
                    // Fusionamos las rutas
                    temp[route_i].nodes.insert(
                        temp[route_i].nodes.end(),
                        temp[route_j].nodes.begin(), temp[route_j].nodes.end());
                    temp[route_i].load = combined_load;
                    update_route(temp[route_i], D);
                    temp[route_i].vehicle_id = v;
                    
                    // Eliminamos la ruta j (swap con el último y pop_back para eficiencia)
                    if (route_j < temp.size() - 1)
                        temp[route_j] = std::move(temp.back());
                    temp.pop_back();
                    break;
                }
            }
        }
    }
    
    // Insertamos los clientes no asignados con el método de mejor inserción
    vector<bool> used(m + 1, false);
    for (const auto& route : temp) {
        for (int node : route.nodes) {
            used[node] = true;
        }
    }
    
    vector<int> unassigned;
    for (int i = 1; i <= m; ++i) {
        if (!used[i]) unassigned.push_back(i);
    }
    
    // Para cada cliente sin asignar
    for (int client : unassigned) {
        struct Insertion {
            double cost_increase;
            int route_index;
            int position;
            int vehicle_id;
        };
        vector<Insertion> candidates;
        
        // Evaluamos todas las posibles inserciones
        for (int v = 0; v < K; ++v) {
            if (demands[client] > capacities[v]) continue;
            
            for (int r = 0; r < temp.size(); ++r) {
                auto& route = temp[r];
                if (route.vehicle_id != -1 && route.vehicle_id != v) continue;
                if (route.load + demands[client] > capacities[v]) continue;
                
                int n = route.nodes.size();
                for (int pos = 0; pos <= n; ++pos) {
                    int prev = (pos > 0 ? route.nodes[pos-1] : 0);
                    int next = (pos < n ? route.nodes[pos] : 0);
                    
                    double delta = D.get(prev, client) + D.get(client, next) - D.get(prev, next);
                    candidates.push_back({delta, r, pos, v});
                }
            }
        }
        
        // Si no hay candidatos factibles, creamos una nueva ruta
        if (candidates.empty()) {
            // Buscamos el vehículo con menor capacidad que pueda llevar al cliente
            int best_v = -1;
            int min_cap = numeric_limits<int>::max();
            
            for (int v = 0; v < K; ++v) {
                if (demands[client] <= capacities[v] && capacities[v] < min_cap) {
                    min_cap = capacities[v];
                    best_v = v;
                }
            }
            
            if (best_v != -1) {
                double cost = D.get(0, client) * 2;
                temp.push_back(Route{{client}, cost, demands[client], {0.0, D.get(0, client)}, best_v});
            } else {
                throw runtime_error("No se puede asignar el cliente " + to_string(client) + 
                                   ". Demanda: " + to_string(demands[client]));
            }
        } else {
            // Ordenamos candidatos por menor incremento de coste
            sort(candidates.begin(), candidates.end(), 
                 [](const Insertion& a, const Insertion& b) { return a.cost_increase < b.cost_increase; });
            
            // Insertamos en la mejor posición
            const auto& best = candidates.front();
            auto& route = temp[best.route_index];
            
            route.nodes.insert(route.nodes.begin() + best.position, client);
            route.load += demands[client];
            route.vehicle_id = best.vehicle_id;
            update_route(route, D);
        }
    }
    
    // Asignamos las rutas temporales a la solución final
    int route_index = 0;
    for (auto& temp_route : temp) {
        if (route_index < K) {
            routes[route_index] = std::move(temp_route);
            route_index++;
        }
    }
    
    // Calculamos el coste total de la solución
    double total_cost = 0.0;
    for (auto& route : routes) {
        update_route(route, D);
        total_cost += route.cost;
    }
    
    return {std::move(routes), total_cost};
}

// --- VND (Variable Neighborhood Descent) mejorado ---
void VND(Route &route,
         DistanceCache& D,
         const vector<int>& demands,
         const vector<int>& capacities,
         vector<double>& op_weights,
         const VNSConfig& config)
{
    vector<unique_ptr<Operator>> operators;
    operators.push_back(make_unique<SwapOperator>());
    operators.push_back(make_unique<RelocateOperator>());
    operators.push_back(make_unique<TwoOptOperator>());
    
    int k = 0;
    while (k < OP_COUNT) {
        Route candidate = route.clone();
        bool success = false;
        
        // Aplicamos el operador k-ésimo
        success = operators[k]->apply(candidate, candidate, demands, capacities);
        
        if (success) {
            update_route(candidate, D);
            
            // Si la nueva ruta es factible y mejor, la aceptamos
            if (candidate.is_valid(demands, capacities) && candidate.cost < route.cost) {
                route = std::move(candidate);
                op_weights[k] *= config.intensification_factor;
                k = 0;  // Reiniciamos desde el primer operador
                continue;
            }
        }
        
        ++k;  // Pasamos al siguiente operador
    }
}

// --- VNS (Variable Neighborhood Search) mejorado ---
Solution vns_hetero_improved(
    const vector<vector<double>>& distance_matrix,
    const vector<int>& demands,
    const vector<int>& capacities,
    int max_iterations = 2000,
    double time_limit = 10.0,
    const VNSConfig& config = VNSConfig())
{
    // Validar entradas
    try {
        validate_input(distance_matrix, demands, capacities);
        config.validate();
    } catch (const exception& e) {
        throw runtime_error(string("Error en los datos de entrada: ") + e.what());
    }
    
    auto start = Clock::now();
    int num_vehicles = capacities.size();
    
    // Inicializar caché de distancias
    DistanceCache D(distance_matrix, config.use_caching);
    
    // Construir solución inicial
    Solution best_solution;
    try {
        best_solution = initial_solution_hetero_savings(D, demands, capacities, config);
    } catch (const exception& e) {
        throw runtime_error(string("Error al construir solución inicial: ") + e.what());
    }
    
    Solution current_solution = best_solution.clone();
    
    // Inicializar pesos de operadores
    vector<double> op_weights(OP_COUNT, 1.0);
    
    // Generador aleatorio
    mt19937 gen(random_device{}());
    uniform_real_distribution<> probability(0.0, 1.0);
    
    // Configurar máximo estancamiento
    int max_stagnation = config.max_stagnation > 0 ? config.max_stagnation : max_iterations / 5;
    int stagnation_counter = 0;
    double shake_intensity = config.initial_shake_intensity;
    
    // Configurar operadores
    vector<unique_ptr<Operator>> operators;
    operators.push_back(make_unique<SwapOperator>());
    operators.push_back(make_unique<RelocateOperator>());
    operators.push_back(make_unique<TwoOptOperator>());
    
    // Bucle principal de VNS
    for (int iteration = 0; iteration < max_iterations && stagnation_counter < max_stagnation; ++iteration) {
        // Verificar límite de tiempo
        double elapsed = chrono::duration<double>(Clock::now() - start).count();
        if (elapsed > time_limit) break;
        
        // Número de perturbaciones basado en la intensidad actual
        int num_perturbations = max(1, static_cast<int>(shake_intensity));
        Solution trial_solution = current_solution.clone();
        
        // Fase de perturbación (Shaking)
        for (int s = 0; s < num_perturbations; ++s) {
            // Selección adaptativa de operador según pesos
            double sum_weights = accumulate(op_weights.begin(), op_weights.end(), 0.0);
            double r = probability(gen) * sum_weights;
            double acc = 0.0;
            int chosen_op = 0;
            
            for (int op = 0; op < OP_COUNT; ++op) {
                acc += op_weights[op];
                if (r <= acc) {
                    chosen_op = op;
                    break;
                }
            }
            
            // Selección aleatoria de rutas
            uniform_int_distribution<> route_dist(0, num_vehicles - 1);
            int route_i = route_dist(gen);
            int route_j = route_dist(gen);
            
            // Aplicamos el operador elegido
            operators[chosen_op]->apply(
                trial_solution.routes[route_i], 
                trial_solution.routes[route_j],
                demands, 
                capacities
            );
        }
        
        // Fase de búsqueda local: VND en cada ruta
        if (num_vehicles >= config.openmp_threshold) {
            #pragma omp parallel for schedule(dynamic)
            for (int i = 0; i < num_vehicles; ++i) {
                VND(trial_solution.routes[i], D, demands, capacities, op_weights, config);
            }
        } else {
            for (int i = 0; i < num_vehicles; ++i) {
                VND(trial_solution.routes[i], D, demands, capacities, op_weights, config);
            }
        }
        
        // Recalculamos el coste total
        trial_solution.total_cost = 0.0;
        for (auto& route : trial_solution.routes) {
            update_route(route, D);
            trial_solution.total_cost += route.cost;
        }
        
        // Evaluación de la solución
        if (trial_solution.total_cost < best_solution.total_cost) {
            // Si es mejor que la mejor conocida, actualizamos
            best_solution = trial_solution.clone();
            current_solution = trial_solution;
            stagnation_counter = 0;
            
            // Reducimos pesos de operadores para diversificar
            for (auto& weight : op_weights) {
                weight = max(1.0, weight * config.diversification_factor);
            }
            
            shake_intensity = config.initial_shake_intensity;
        } else {
            // Si no mejora, seguimos explorando
            current_solution = trial_solution;
            stagnation_counter++;
            
            // Aumentamos intensidad de perturbación
            shake_intensity = min(config.max_shake_intensity, 
                                  shake_intensity * config.shake_increase);
        }
    }
    
    return best_solution;
}

// --- Interfaz Python mejorada ---
PYBIND11_MODULE(vns_solver, m) {
    // Documentación del módulo
    m.doc() = "Módulo de resolución VNS para problemas de enrutamiento de vehículos con flota heterogénea";
    
    // Exponemos la configuración de VNS
    py::class_<VNSConfig>(m, "VNSConfig")
        .def(py::init<>())
        .def_readwrite("openmp_threshold", &VNSConfig::openmp_threshold)
        .def_readwrite("top_k_insert", &VNSConfig::top_k_insert)
        .def_readwrite("intensification_factor", &VNSConfig::intensification_factor)
        .def_readwrite("diversification_factor", &VNSConfig::diversification_factor)
        .def_readwrite("initial_shake_intensity", &VNSConfig::initial_shake_intensity)
        .def_readwrite("max_shake_intensity", &VNSConfig::max_shake_intensity)
        .def_readwrite("shake_increase", &VNSConfig::shake_increase)
        .def_readwrite("max_stagnation", &VNSConfig::max_stagnation)
        .def_readwrite("use_caching", &VNSConfig::use_caching)
        .def("validate", &VNSConfig::validate);
    
    // Exponemos las estructuras de datos
    py::class_<Route>(m, "Route")
        .def_readonly("nodes", &Route::nodes)
        .def_readonly("cost", &Route::cost)
        .def_readonly("load", &Route::load)
        .def_readonly("vehicle_id", &Route::vehicle_id)
        .def("is_valid", &Route::is_valid);
    
    py::class_<Solution>(m, "Solution")
        .def_readonly("routes", &Solution::routes)
        .def_readonly("total_cost", &Solution::total_cost)
        .def("is_valid", &Solution::is_valid);
    
    // Exponemos la función principal
    m.def("vns_hetero_improved", &vns_hetero_improved,
          py::arg("distance_matrix"),
          py::arg("demands"),
          py::arg("capacities"),
          py::arg("max_iterations") = 2000,
          py::arg("time_limit") = 10.0,
          py::arg("config") = VNSConfig(),
          "Resuelve un problema de enrutamiento de vehículos con flota heterogénea usando VNS");
    
    // Función simplificada para compatibilidad
    m.def("vns_hetero_simplified", [](
        const vector<vector<double>>& distance_matrix,
        const vector<int>& demands,
        const vector<int>& capacities,
        int max_iterations,
        double time_limit,
        const VNSConfig& config = VNSConfig()) 
    {
        Solution solution = vns_hetero_improved(
            distance_matrix, demands, capacities, 
            max_iterations, time_limit, config);
        
        vector<vector<int>> routes_nodes;
        for (const auto& route : solution.routes) {
            routes_nodes.push_back(route.nodes);
        }
        return routes_nodes;
    },
    py::arg("distance_matrix"),
    py::arg("demands"),
    py::arg("capacities"),
    py::arg("max_iterations") = 2000,
    py::arg("time_limit") = 10.0,
    py::arg("config") = VNSConfig(),
    "Versión simplificada que devuelve solo las listas de nodos");
}
