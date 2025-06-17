// Filename: tabu_vrp_pybind_refined_routes_only.cpp

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <vector>
#include <algorithm>
#include <random>
#include <limits>
#include <unordered_map>

namespace py = pybind11;
using namespace std;

struct Solution {
    vector<vector<int>> routes;   // rutas por camión (lista de nodos, sin depósito 0)
    vector<int> loads;            // carga total en cada camión
    vector<double> route_dists;   // distancia de cada ruta (incluye ida y vuelta a 0)
    double total_distance;        // suma de route_dists
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

// Genera solución inicial greedy (asigna cada objetivo al primer camión con espacio)
Solution generate_initial_solution(
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

    int idx = 0;
    for (int obj : objectives) {
        bool placed = false;
        for (int t = 0; t < num_trucks; ++t) {
            if (sol.loads[t] + demands[obj] <= capacities[t]) {
                sol.routes[t].push_back(obj);
                sol.loads[t] += demands[obj];
                placed = true;
                break;
            }
        }
        if (!placed) {
            int t = idx % num_trucks;
            sol.routes[t].push_back(obj);
            sol.loads[t] += demands[obj];
        }
        ++idx;
    }

    for (int t = 0; t < num_trucks; ++t) {
        sol.route_dists[t] = compute_route_distance(sol.routes[t], dist);
    }
    update_total_distance(sol);
    return sol;
}

// Encuentra la mejor mejora 2-opt en una ruta; devuelve true si hubo mejora y
// suministra (best_i, best_j, best_delta).
bool best_improve_2opt(
    vector<int>& route,
    const vector<vector<double>>& dist,
    double& best_delta,
    int& best_i,
    int& best_j)
{
    int n = route.size();
    if (n < 2) return false;

    best_delta = 0.0;
    best_i = best_j = -1;

    for (int i = 0; i < n - 1; ++i) {
        int a = (i == 0 ? 0 : route[i - 1]);
        int b = route[i];
        for (int j = i + 1; j < n; ++j) {
            int c = route[j];
            int d = (j + 1 < n ? route[j + 1] : 0);

            double before = dist[a][b] + dist[c][d];
            double after  = dist[a][c] + dist[b][d];
            double delta = before - after;
            if (delta > best_delta) {
                best_delta = delta;
                best_i = i;
                best_j = j;
            }
        }
    }

    if (best_i >= 0) {
        reverse(route.begin() + best_i, route.begin() + best_j + 1);
        return true;
    }
    return false;
}

Solution tabu_search_refined(
    const vector<vector<double>>& dist,
    const vector<int>& objectives,
    const vector<int>& demands,
    const vector<int>& capacities,
    int num_trucks,
    int max_iter = 1000,
    int base_tabu_tenure = 20,
    int no_improve_limit = 200,
    int diversification_interval = 500)
{
    mt19937 rng(random_device{}());
    uniform_int_distribution<int> truck_dist(0, num_trucks - 1);

    Solution current = generate_initial_solution(objectives, demands, capacities, num_trucks, dist);
    Solution best = current;

    unordered_map<string,int> tabu_list;
    int no_improve = 0;

    for (int iter = 0; iter < max_iter && no_improve < no_improve_limit; ++iter) {
        Solution best_candidate = current;
        double best_candidate_dist = numeric_limits<double>::infinity();
        string best_move_key;

        // 1) 2-opt intra-ruta (best improvement)
        for (int t = 0; t < num_trucks; ++t) {
            auto &route = current.routes[t];
            double old_d = current.route_dists[t];

            double delta;
            int i, j;
            if (best_improve_2opt(route, dist, delta, i, j)) {
                double new_d = old_d - delta;
                double candidate_total = current.total_distance - old_d + new_d;
                string move_key = "2opt_" + to_string(t) + "_" + to_string(i) + "_" + to_string(j);
                bool is_tabu = (tabu_list.count(move_key) > 0);

                if ((!is_tabu && candidate_total < best_candidate_dist) ||
                    (candidate_total < best.total_distance))
                {
                    best_candidate = current;
                    best_candidate.route_dists[t] = new_d;
                    update_total_distance(best_candidate);
                    best_candidate_dist = candidate_total;
                    best_move_key = move_key;
                }
                // revertir movimiento
                reverse(route.begin() + i, route.begin() + j + 1);
            }
        }

        // 2) swap inter-rutas
        for (int t1 = 0; t1 < num_trucks; ++t1) {
            for (int t2 = t1 + 1; t2 < num_trucks; ++t2) {
                auto &r1 = current.routes[t1];
                auto &r2 = current.routes[t2];
                for (int idx1 = 0; idx1 < (int)r1.size(); ++idx1) {
                    for (int idx2 = 0; idx2 < (int)r2.size(); ++idx2) {
                        int n1 = r1[idx1];
                        int n2 = r2[idx2];
                        int load1_new = current.loads[t1] - demands[n1] + demands[n2];
                        int load2_new = current.loads[t2] - demands[n2] + demands[n1];
                        if (load1_new > capacities[t1] || load2_new > capacities[t2]) continue;

                        double old_d1 = current.route_dists[t1];
                        double old_d2 = current.route_dists[t2];

                        swap(r1[idx1], r2[idx2]);
                        current.loads[t1] = load1_new;
                        current.loads[t2] = load2_new;
                        double new_d1 = compute_route_distance(r1, dist);
                        double new_d2 = compute_route_distance(r2, dist);
                        double candidate_total = current.total_distance - old_d1 - old_d2 + new_d1 + new_d2;
                        string move_key = "swap_" + to_string(t1) + "_" + to_string(t2)
                                         + "_" + to_string(n1) + "_" + to_string(n2);
                        bool is_tabu = (tabu_list.count(move_key) > 0);

                        if ((!is_tabu && candidate_total < best_candidate_dist) ||
                            (candidate_total < best.total_distance))
                        {
                            best_candidate = current;
                            best_candidate.route_dists[t1] = new_d1;
                            best_candidate.route_dists[t2] = new_d2;
                            update_total_distance(best_candidate);
                            best_candidate_dist = candidate_total;
                            best_move_key = move_key;
                        }

                        // revertir swap
                        swap(r1[idx1], r2[idx2]);
                        current.loads[t1] += demands[n1] - demands[n2];
                        current.loads[t2] += demands[n2] - demands[n1];
                    }
                }
            }
        }

        // 3) mover un nodo (move) entre rutas
        for (int t1 = 0; t1 < num_trucks; ++t1) {
            for (int idx1 = 0; idx1 < (int)current.routes[t1].size(); ++idx1) {
                int node = current.routes[t1][idx1];
                for (int t2 = 0; t2 < num_trucks; ++t2) {
                    if (t1 == t2) continue;
                    if (current.loads[t2] + demands[node] > capacities[t2]) continue;

                    double old_d1 = current.route_dists[t1];
                    double old_d2 = current.route_dists[t2];

                    // aplicar move
                    current.routes[t2].push_back(node);
                    current.loads[t1] -= demands[node];
                    current.loads[t2] += demands[node];
                    current.routes[t1].erase(current.routes[t1].begin() + idx1);

                    double new_d1 = compute_route_distance(current.routes[t1], dist);
                    double new_d2 = compute_route_distance(current.routes[t2], dist);
                    double candidate_total = current.total_distance - old_d1 - old_d2 + new_d1 + new_d2;
                    string move_key = "move_" + to_string(node)
                                     + "_" + to_string(t1) + "_" + to_string(t2);
                    bool is_tabu = (tabu_list.count(move_key) > 0);

                    if ((!is_tabu && candidate_total < best_candidate_dist) ||
                        (candidate_total < best.total_distance))
                    {
                        best_candidate = current;
                        best_candidate.route_dists[t1] = new_d1;
                        best_candidate.route_dists[t2] = new_d2;
                        update_total_distance(best_candidate);
                        best_candidate_dist = candidate_total;
                        best_move_key = move_key;
                    }

                    // revertir move
                    current.routes[t1].insert(current.routes[t1].begin() + idx1, node);
                    current.loads[t1] += demands[node];
                    current.loads[t2] -= demands[node];
                    current.routes[t2].pop_back();
                }
            }
        }

        // 4) relocate intra-ruta (extraer y reinsertar en distinta posición)
        for (int t = 0; t < num_trucks; ++t) {
            auto &r = current.routes[t];
            int sz = r.size();
            if (sz < 2) continue;
            for (int i = 0; i < sz; ++i) {
                int node = r[i];
                for (int j = 0; j < sz; ++j) {
                    if (j == i) continue;

                    double old_d = current.route_dists[t];
                    // extraer
                    r.erase(r.begin() + i);
                    r.insert(r.begin() + (j < i ? j : j), node);
                    double new_d = compute_route_distance(r, dist);
                    double candidate_total = current.total_distance - old_d + new_d;
                    string move_key = "relocate_" + to_string(t) + "_" + to_string(node)
                                     + "_" + to_string(i) + "_" + to_string(j);
                    bool is_tabu = (tabu_list.count(move_key) > 0);

                    if ((!is_tabu && candidate_total < best_candidate_dist) ||
                        (candidate_total < best.total_distance))
                    {
                        best_candidate = current;
                        best_candidate.route_dists[t] = new_d;
                        update_total_distance(best_candidate);
                        best_candidate_dist = candidate_total;
                        best_move_key = move_key;
                    }
                    // revertir relocate
                    r.erase(r.begin() + (j < i ? j : j));
                    r.insert(r.begin() + i, node);
                }
            }
        }

        // Si no hallamos ningún movimiento válido, diversificamos levemente
        if (best_move_key.empty()) {
            int rt1 = truck_dist(rng), rt2 = truck_dist(rng);
            if (rt1 == rt2) rt2 = (rt1 + 1) % num_trucks;
            if (!current.routes[rt1].empty() && !current.routes[rt2].empty()) {
                int i1 = uniform_int_distribution<int>(0, (int)current.routes[rt1].size() - 1)(rng);
                int i2 = uniform_int_distribution<int>(0, (int)current.routes[rt2].size() - 1)(rng);
                swap(current.routes[rt1][i1], current.routes[rt2][i2]);
                current.route_dists[rt1] = compute_route_distance(current.routes[rt1], dist);
                current.route_dists[rt2] = compute_route_distance(current.routes[rt2], dist);
                update_total_distance(current);
            }
            continue;
        }

        // Aplicar el mejor movimiento: asignar current = best_candidate
        current = best_candidate;
        if (current.total_distance < best.total_distance) {
            best = current;
            no_improve = 0;
        } else {
            ++no_improve;
        }

        // Reducir tenencia tabú
        for (auto it = tabu_list.begin(); it != tabu_list.end();) {
            if (--(it->second) <= 0) it = tabu_list.erase(it);
            else ++it;
        }

        int dynamic_tenure = base_tabu_tenure + (rng() % 5);
        tabu_list[best_move_key] = dynamic_tenure;

        // Diversificación periódica
        if (iter > 0 && iter % diversification_interval == 0) {
            for (int t = 0; t < num_trucks; ++t) {
                auto &r = current.routes[t];
                int sz = r.size();
                if (sz < 3) continue;
                int a = uniform_int_distribution<int>(0, sz - 2)(rng);
                int b = uniform_int_distribution<int>(a + 1, sz - 1)(rng);
                reverse(r.begin() + a, r.begin() + b + 1);
                current.route_dists[t] = compute_route_distance(r, dist);
            }
            update_total_distance(current);
            tabu_list["diversify_" + to_string(iter)] = base_tabu_tenure;
        }
    }

    return best;
}

// Binding a Python: devuelve solo lista de rutas (vector<vector<int>>)
py::list solve_vrp(
    py::array_t<double, py::array::c_style | py::array::forcecast> dist_matrix_np,
    py::array_t<int,    py::array::c_style | py::array::forcecast> objectives_np,
    py::array_t<int,    py::array::c_style | py::array::forcecast> demands_np,
    py::array_t<int,    py::array::c_style | py::array::forcecast> capacities_np,
    int num_trucks,
    int max_iter = 1000,
    int base_tabu_tenure = 20,
    int no_improve_limit = 200,
    int diversification_interval = 500)
{
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

    // Ejecutar Tabu Search refinado
    Solution best = tabu_search_refined(
        dist, objectives, demands, capacities, num_trucks,
        max_iter, base_tabu_tenure, no_improve_limit, diversification_interval
    );

    // Convertir routes a py::list
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

PYBIND11_MODULE(ts_solver, m) {
    m.doc() = "VRP con Tabu Search refinado (2-opt best, swap, move, relocate, diversificación)";
    m.def(
        "solve_vrp",
        &solve_vrp,
        py::arg("dist_matrix"),
        py::arg("objectives"),
        py::arg("demands"),
        py::arg("capacities"),
        py::arg("num_trucks"),
        py::arg("max_iter") = 1000,
        py::arg("base_tabu_tenure") = 20,
        py::arg("no_improve_limit") = 200,
        py::arg("diversification_interval") = 500,
        R"pbdoc(
            Resuelve un VRP con Tabu Search refinado.

            Args:
                dist_matrix (ndarray[double, 2D]): Matriz de distancias n_points×n_points.
                objectives   (ndarray[int, 1D]): Índices de nodos objetivos (1..n_points-1).
                demands      (ndarray[int, 1D]): Demanda de cada nodo (longitud n_points).
                capacities   (ndarray[int, 1D]): Capacidad de cada camión.
                num_trucks   (int): Número de camiones.
                max_iter     (int, opcional): Iteraciones máximas (por defecto 1000).
                base_tabu_tenure (int, opcional): Tenencia base para Tabú (por defecto 20).
                no_improve_limit (int, opcional): Iteraciones sin mejora antes de parar (por defecto 200).
                diversification_interval (int, opcional): Frecuencia de diversificación (por defecto 500).

            Returns:
                List[List[int]]: Lista de rutas, cada ruta es un array de nodos (sin incluir depósito).
        )pbdoc"
    );
}
