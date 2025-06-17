// improved_genetic_vrp_param.cpp
// VRP con GA parametrizable desde Python mediante pybind11

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>
#include <chrono>
#include <limits>
#include <thread>

namespace py = pybind11;
using Matrix = std::vector<std::vector<double>>;
using Route  = std::vector<int>;
using Demand = std::vector<int>;

static std::mt19937 base_rng((unsigned)std::chrono::high_resolution_clock::now()
                            .time_since_epoch().count());

// --- 1. Evaluación de ruta (retorno al depósito) ---

double route_distance(const Route &r, const Matrix &dist) {
    double d = 0.0;
    int prev = 0;
    for (int node : r) {
        d += dist[prev][node];
        prev = node;
    }
    d += dist[prev][0];
    return d;
}

// --- 2. 2-opt local ---

void two_opt(Route &r, const Matrix &dist) {
    bool improved = true;
    int n = r.size();
    while (improved) {
        improved = false;
        for (int i = 0; i < n - 1 && !improved; ++i) {
            for (int k = i + 1; k < n; ++k) {
                int a = (i ? r[i - 1] : 0);
                int b = r[i];
                int c = r[k];
                int d = (k + 1 < n ? r[k + 1] : 0);
                double before = dist[a][b] + dist[c][d];
                double after  = dist[a][c] + dist[b][d];
                if (after + 1e-6 < before) {
                    std::reverse(r.begin() + i, r.begin() + k + 1);
                    improved = true;
                    break;
                }
            }
        }
    }
}

// --- 3. Order Crossover (OX) ---

Route order_crossover(const Route &p1, const Route &p2, std::mt19937 &rng) {
    int n = p1.size();
    std::uniform_int_distribution<int> dist(0, n - 1);
    int i = dist(rng), j = dist(rng);
    if (i > j) std::swap(i, j);
    Route child(n, -1);
    // copia segmento
    for (int k = i; k <= j; ++k) child[k] = p1[k];
    // rellena resto
    int idx = (j + 1) % n;
    for (int k = 0; k < n; ++k) {
        int g = p2[(j + 1 + k) % n];
        if (std::find(child.begin() + i, child.begin() + j + 1, g) == child.begin() + j + 1) {
            child[idx] = g;
            idx = (idx + 1) % n;
        }
    }
    return child;
}

// --- 4. Clarke–Wright con capacidades específicas ---

struct Saving { int i, j; double val; };

std::vector<Route> clarke_wright(const Matrix &dist,
                                 const Demand &dem,
                                 const std::vector<int> &cap) {
    int n = dem.size() - 1;
    int k = cap.size();
    std::vector<Saving> savings;
    savings.reserve(n * (n - 1) / 2);
    for (int i = 1; i <= n; ++i)
        for (int j = i + 1; j <= n; ++j)
            savings.push_back({i, j, dist[0][i] + dist[0][j] - dist[i][j]});
    std::sort(savings.begin(), savings.end(), [](auto &a, auto &b){ return a.val > b.val; });

    std::vector<Route> routes(n);
    std::vector<int> rid(n+1), load(n);
    for (int i = 1; i <= n; ++i) {
        routes[i-1] = {i};
        rid[i] = i-1;
        load[i-1] = dem[i];
    }

    for (auto &s : savings) {
        int r1 = rid[s.i], r2 = rid[s.j];
        if (r1 == r2) continue;
        int new_load = load[r1] + load[r2];
        bool feasible = false;
        for (int c : cap) {
            if (c >= new_load) { feasible = true; break; }
        }
        if (!feasible) continue;
        auto &R1 = routes[r1], &R2 = routes[r2];
        bool e1 = (R1.front()==s.i || R1.back()==s.i);
        bool e2 = (R2.front()==s.j || R2.back()==s.j);
        if (!e1 || !e2) continue;
        if (R1.back()==s.i) {
            if (R2.front()==s.j)           R1.insert(R1.end(),   R2.begin(), R2.end());
            else { std::reverse(R2.begin(), R2.end()); R1.insert(R1.end(), R2.begin(), R2.end()); }
        } else {
            if (R2.back()==s.j) {
                std::reverse(R2.begin(), R2.end());
                R1.insert(R1.begin(), R2.begin(), R2.end());
            } else
                R1.insert(R1.begin(), R2.begin(), R2.end());
        }
        load[r1] = new_load;
        for (int nd : R2) rid[nd] = r1;
        routes[r2].clear(); load[r2] = 0;
        int cnt = 0;
        for (auto &R : routes) if (!R.empty()) ++cnt;
        if (cnt <= k) break;
    }

    std::vector<Route> out;
    out.reserve(k);
    for (auto &R : routes) if (!R.empty()) {
        out.push_back(R);
        if ((int)out.size() == k) break;
    }
    while ((int)out.size() < k) out.push_back({});
    return out;
}

// --- 5. GA local con parámetros ---

Route local_ga(const Route &init,
               const Matrix &dist,
               int pop_size,
               int sel_size,
               int max_gen,
               int no_improve_limit,
               double mut_rate,
               unsigned seed) {
    int m = init.size();
    if (m < 2) return init;
    std::mt19937 rng(seed);

    int sel = sel_size;
    int no_improve = 0;
    double best_overall = std::numeric_limits<double>::infinity();
    Route best_route;

    // inicializar población
    std::vector<Route> P;
    P.reserve(pop_size);
    P.push_back(init);
    Route base = init;
    for (int i = 1; i < pop_size; ++i) {
        std::shuffle(base.begin(), base.end(), rng);
        P.push_back(base);
    }

    auto fitness = [&](const Route &r){ return route_distance(r, dist); };

    for (int gen = 0; gen < max_gen; ++gen) {
        std::vector<std::pair<double, Route>> scored;
        scored.reserve(pop_size);
        for (auto &r : P) scored.emplace_back(fitness(r), r);
        std::sort(scored.begin(), scored.end(), [](auto &a, auto &b){ return a.first < b.first; });

        if (scored[0].first + 1e-6 < best_overall) {
            best_overall = scored[0].first;
            best_route = scored[0].second;
            no_improve = 0;
        } else if (++no_improve >= no_improve_limit) break;

        std::vector<Route> selected;
        selected.reserve(sel);
        for (int i = 0; i < sel; ++i) selected.push_back(scored[i].second);

        P = selected;
        std::uniform_real_distribution<double> unif(0, 1);
        std::uniform_int_distribution<int> idx_dist(0, sel - 1);
        while ((int)P.size() < pop_size) {
            auto &p1 = selected[idx_dist(rng)];
            auto &p2 = selected[idx_dist(rng)];
            Route c = order_crossover(p1, p2, rng);
            if (unif(rng) < mut_rate) two_opt(c, dist);
            P.push_back(c);
        }
    }
    return best_route;
}

// --- 6. Inter-relocation y swap inter-cluster ---

void inter_improve(std::vector<Route> &C,
                   const Matrix &dist,
                   const Demand &dem,
                   const std::vector<int> &cap) {
    bool moved = true;
    int k = C.size();
    while (moved) {
        moved = false;
        // relocation
        for (int a = 0; a < k && !moved; ++a) {
            for (int b = 0; b < k && !moved; ++b) {
                if (a == b) continue;
                int load_a = std::accumulate(C[a].begin(), C[a].end(), 0,
                                [&](int s, int x){ return s + dem[x]; });
                int load_b = std::accumulate(C[b].begin(), C[b].end(), 0,
                                [&](int s, int x){ return s + dem[x]; });
                for (int i = 0; i < (int)C[a].size(); ++i) {
                    int node = C[a][i];
                    if (load_b + dem[node] > cap[b]) continue;
                    auto Ra = C[a]; Ra.erase(Ra.begin() + i);
                    auto Rb = C[b]; Rb.push_back(node);
                    double oldd = route_distance(C[a], dist) + route_distance(C[b], dist);
                    double newd = route_distance(Ra, dist) + route_distance(Rb, dist);
                    if (newd + 1e-6 < oldd) { C[a] = Ra; C[b] = Rb; moved = true; break; }
                }
            }
        }
        if (moved) continue;
        // swap inter-cluster similar a antes...
        // (sin cambios)
        int la, lb;
        for (int a = 0; a < k && !moved; ++a) for (int b = a+1; b < k && !moved; ++b) {
            la = std::accumulate(C[a].begin(), C[a].end(), 0, [&](int s,int x){return s+dem[x];});
            lb = std::accumulate(C[b].begin(), C[b].end(), 0, [&](int s,int x){return s+dem[x];});
            for (int i = 0; i < (int)C[a].size() && !moved; ++i) for (int j = 0; j < (int)C[b].size(); ++j) {
                int na = C[a][i], nb = C[b][j];
                if (la - dem[na] + dem[nb] > cap[a] || lb - dem[nb] + dem[na] > cap[b]) continue;
                auto Ra = C[a], Rb = C[b]; std::swap(Ra[i], Rb[j]);
                double oldd = route_distance(C[a],dist)+route_distance(C[b],dist);
                double newd = route_distance(Ra,dist)+route_distance(Rb,dist);
                if (newd +1e-6<oldd) { C[a]=Ra; C[b]=Rb; moved=true; break; }
            }
        }
    }
}

// --- 7. Solver integrado y paralelizable ---

std::vector<Route> solve_vrp(const Matrix &dist,
                              const Demand &dem,
                              const std::vector<int> &cap,
                              int pop_size = 50,
                              int sel_size = 20,
                              int max_gen = 100,
                              int no_improve_limit = 20,
                              double mut_rate = 0.3) {
    int k = cap.size();
    // clustering inicial
    auto clusters = clarke_wright(dist, dem, cap);
    // GA local en paralelo
    std::vector<std::thread> threads;
    threads.reserve(k);
    for (int i = 0; i < k; ++i) {
        unsigned seed = base_rng();
        threads.emplace_back([&, i, seed]() {
            clusters[i] = local_ga(clusters[i], dist,
                                   pop_size, sel_size, max_gen,
                                   no_improve_limit, mut_rate,
                                   seed);
        });
    }
    for (auto &t : threads) t.join();
    // mejoras inter-cluster
    inter_improve(clusters, dist, dem, cap);
    // refinamiento final 2-opt en paralelo
    threads.clear(); threads.reserve(k);
    for (int i = 0; i < k; ++i) {
        threads.emplace_back([&, i]() { two_opt(clusters[i], dist); });
    }
    for (auto &t : threads) t.join();
    return clusters;
}

PYBIND11_MODULE(ag_solver, m) {
    m.doc() = "VRP avanzado multi-hilo con GA parametrizable";
    m.def("solve_vrp", &solve_vrp,
          py::arg("dist_matrix"), py::arg("demand"), py::arg("capacity"),
          py::arg("pop_size") = 50,
          py::arg("sel_size") = 20,
          py::arg("max_gen") = 100,
          py::arg("no_improve_limit") = 20,
          py::arg("mut_rate") = 0.3,
          "Solver VRP con parámetros GA ajustables desde Python");
}
