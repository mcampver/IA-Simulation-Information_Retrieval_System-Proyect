// vrp_sa_py.cpp
// Compilar con:
//    c++ -O3 -std=c++11 -shared -fPIC $(python3 -m pybind11 --includes) vrp_sa_py.cpp -o vrp_sa_py$(python3-config --extension-suffix)
// Esto genera un módulo Python que se puede importar como `import vrp_sa_py`

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>
#include <chrono>
#include <limits>
#include <thread>
using namespace std;
namespace py = pybind11;

typedef long long ll;

// -----------------------------------------------------------
//   Variables globales de lectura (serán inicializadas en la función Python)
// -----------------------------------------------------------
static int N_g, T_g;
static vector<int> capacity_g;
static vector<int> demand_g;
static vector<vector<double>> distMat_g;
static double lambdaPen_g;

struct SolutionFast {
    vector<vector<int>> rutas;
    vector<double> routeCost;
    vector<int> routeDemand;
    double totalCost;
    int activeTrucks;
};

struct RevertInfo {
    int rA, posA, rB, posB;
    int u, v;
    double delta;
    int type; // 0=move,1=swap,2=2opt
    int i, j;
};

// -----------------------------------------------------------
//   Delta calculations
// -----------------------------------------------------------
inline double deltaMoveSolo(int rA, int posA, int rB, int posB, SolutionFast &sol) {
    int u = sol.rutas[rA][posA];
    double delta = 0;
    int prevA = (posA == 0 ? 0 : sol.rutas[rA][posA-1]);
    int nextA = (posA + 1 == (int)sol.rutas[rA].size() ? 0 : sol.rutas[rA][posA+1]);
    double oldA = distMat_g[prevA][u] + distMat_g[u][nextA];
    double newA = distMat_g[prevA][nextA];
    delta += (newA - oldA);
    int lenB = sol.rutas[rB].size();
    int prevB = (posB == 0 ? 0 : sol.rutas[rB][posB-1]);
    int nextB = (posB == lenB ? 0 : sol.rutas[rB][posB]);
    double oldB = distMat_g[prevB][nextB];
    double newB = distMat_g[prevB][u] + distMat_g[u][nextB];
    delta += (newB - oldB);
    return delta;
}

inline double deltaSwap(int rA, int posA, int rB, int posB, SolutionFast &sol) {
    int u = sol.rutas[rA][posA];
    int v = sol.rutas[rB][posB];
    double delta = 0;
    int prevA = (posA == 0 ? 0 : sol.rutas[rA][posA-1]);
    int nextA = (posA + 1 == (int)sol.rutas[rA].size() ? 0 : sol.rutas[rA][posA+1]);
    double oldA = distMat_g[prevA][u] + distMat_g[u][nextA];
    double newA = distMat_g[prevA][v] + distMat_g[v][nextA];
    delta += (newA - oldA);
    int prevB = (posB == 0 ? 0 : sol.rutas[rB][posB-1]);
    int nextB = (posB + 1 == (int)sol.rutas[rB].size() ? 0 : sol.rutas[rB][posB+1]);
    double oldB = distMat_g[prevB][v] + distMat_g[v][nextB];
    double newB = distMat_g[prevB][u] + distMat_g[u][nextB];
    delta += (newB - oldB);
    return delta;
}

inline double delta2Opt(int r, int i, int j, SolutionFast &sol) {
    int a = sol.rutas[r][i];
    int b = sol.rutas[r][j];
    int prevA = (i == 0 ? 0 : sol.rutas[r][i-1]);
    int nextB = (j + 1 == (int)sol.rutas[r].size() ? 0 : sol.rutas[r][j+1]);
    double oldCost = distMat_g[prevA][a] + distMat_g[b][nextB];
    double newCost = distMat_g[prevA][b] + distMat_g[a][nextB];
    return (newCost - oldCost);
}

// -----------------------------------------------------------
//   Initial Solution Simple Insertion at End
// -----------------------------------------------------------
SolutionFast initialSolutionFast() {
    SolutionFast sol;
    sol.rutas.assign(T_g, {});
    sol.routeCost.assign(T_g, 0.0);
    sol.routeDemand.assign(T_g, 0);
    sol.activeTrucks = 0;
    vector<int> nodos(N_g-1);
    for (int i = 0; i < N_g-1; i++) nodos[i] = i+1;
    for (int u : nodos) {
        double bestInc = 1e300;
        int bestTruck = -1;
        for (int i = 0; i < T_g; i++) {
            if (sol.routeDemand[i] + demand_g[u] > capacity_g[i]) continue;
            double inc;
            if (sol.rutas[i].empty()) {
                inc = 2.0 * distMat_g[0][u];
            } else {
                int tail = sol.rutas[i].back();
                inc = distMat_g[tail][u] + distMat_g[u][0] - distMat_g[tail][0];
            }
            if (inc < bestInc) { bestInc = inc; bestTruck = i; }
        }
        if (bestTruck == -1) {
            for (int i = 0; i < T_g; i++) {
                if (sol.routeDemand[i] + demand_g[u] <= capacity_g[i]) { bestTruck = i; break; }
            }
        }
        int i = bestTruck;
        if (sol.rutas[i].empty()) {
            sol.routeCost[i] = 2.0 * distMat_g[0][u];
            sol.activeTrucks++;
        } else {
            int tail = sol.rutas[i].back();
            sol.routeCost[i] += (distMat_g[tail][u] + distMat_g[u][0] - distMat_g[tail][0]);
        }
        sol.rutas[i].push_back(u);
        sol.routeDemand[i] += demand_g[u];
    }
    double sumC = 0.0;
    for (int i = 0; i < T_g; i++) sumC += sol.routeCost[i];
    sol.totalCost = sumC + lambdaPen_g * sol.activeTrucks;
    return sol;
}

// -----------------------------------------------------------
//   Apply and revert moves in-place
// -----------------------------------------------------------
inline void applyMoveSolo(SolutionFast &sol, const RevertInfo &rev) {
    int rA = rev.rA, posA = rev.posA;
    int rB = rev.rB, posB = rev.posB;
    int u = rev.u;
    sol.rutas[rA].erase(sol.rutas[rA].begin()+posA);
    sol.routeDemand[rA] -= demand_g[u];
    if (sol.rutas[rA].empty()) sol.activeTrucks--;
    sol.rutas[rB].insert(sol.rutas[rB].begin()+posB, u);
    if ((int)sol.rutas[rB].size() == 1) sol.activeTrucks++;
    sol.routeDemand[rB] += demand_g[u];
    sol.routeCost[rA] += rev.delta;
    sol.routeCost[rB] += (rev.delta - rev.delta);
}

inline void revertMoveSolo(SolutionFast &sol, const RevertInfo &rev) {
    int rA = rev.rA, posA = rev.posA;
    int rB = rev.rB, posB = rev.posB;
    int u = rev.u;
    sol.rutas[rB].erase(sol.rutas[rB].begin()+posB);
    sol.routeDemand[rB] -= demand_g[u];
    if (sol.rutas[rB].empty()) sol.activeTrucks--;
    sol.rutas[rA].insert(sol.rutas[rA].begin()+posA, u);
    if ((int)sol.rutas[rA].size() == 1) sol.activeTrucks++;
    sol.routeDemand[rA] += demand_g[u];
    sol.routeCost[rA] -= rev.delta;
    sol.routeCost[rB] -= (rev.delta - rev.delta);
}

inline void applySwap(SolutionFast &sol, const RevertInfo &rev) {
    int rA = rev.rA, posA = rev.posA;
    int rB = rev.rB, posB = rev.posB;
    int u = rev.u, v = rev.v;
    sol.rutas[rA][posA] = v;
    sol.rutas[rB][posB] = u;
    sol.routeDemand[rA] += (demand_g[v] - demand_g[u]);
    sol.routeDemand[rB] += (demand_g[u] - demand_g[v]);
    sol.routeCost[rA] += rev.delta;
    sol.routeCost[rB] += (rev.delta - rev.delta);
}

inline void revertSwap(SolutionFast &sol, const RevertInfo &rev) {
    int rA = rev.rA, posA = rev.posA;
    int rB = rev.rB, posB = rev.posB;
    int u = rev.u, v = rev.v;
    sol.rutas[rA][posA] = u;
    sol.rutas[rB][posB] = v;
    sol.routeDemand[rA] += (demand_g[u] - demand_g[v]);
    sol.routeDemand[rB] += (demand_g[v] - demand_g[u]);
    sol.routeCost[rA] -= rev.delta;
    sol.routeCost[rB] -= (rev.delta - rev.delta);
}

inline void apply2Opt(SolutionFast &sol, const RevertInfo &rev) {
    int r = rev.rA, i = rev.i, j = rev.j;
    reverse(sol.rutas[r].begin()+i, sol.rutas[r].begin()+j+1);
    sol.routeCost[r] += rev.delta;
}

inline void revert2Opt(SolutionFast &sol, const RevertInfo &rev) {
    int r = rev.rA, i = rev.i, j = rev.j;
    reverse(sol.rutas[r].begin()+i, sol.rutas[r].begin()+j+1);
    sol.routeCost[r] -= rev.delta;
}

// -----------------------------------------------------------
//   Generate neighbor in O(1) time complexity (delta) and apply
// -----------------------------------------------------------
bool neighborFast(SolutionFast &cur, RevertInfo &rev) {
    double rtype = (double)rand() / RAND_MAX;
    if (rtype < 0.3333) {
        vector<int> cand;
        for (int i = 0; i < T_g; i++) if (cur.rutas[i].size() >= 2) cand.push_back(i);
        if (cand.empty()) return false;
        int r = cand[rand() % cand.size()];
        int len = cur.rutas[r].size();
        int i = rand() % (len-1);
        int j = i + 1 + rand() % (len - i - 1);
        rev.type = 2; rev.rA = r; rev.i = i; rev.j = j;
        rev.delta = delta2Opt(r, i, j, cur);
        apply2Opt(cur, rev);
        return true;
    } else if (rtype < 0.6666) {
        vector<int> nonEmpty;
        for (int i = 0; i < T_g; i++) if (!cur.rutas[i].empty()) nonEmpty.push_back(i);
        if (nonEmpty.size() < 2) return false;
        int a = nonEmpty[rand() % nonEmpty.size()];
        int b = nonEmpty[rand() % nonEmpty.size()];
        if (a == b) return false;
        int posA = rand() % cur.rutas[a].size();
        int posB = rand() % cur.rutas[b].size();
        int u = cur.rutas[a][posA];
        int v = cur.rutas[b][posB];
        int newDemA = cur.routeDemand[a] - demand_g[u] + demand_g[v];
        int newDemB = cur.routeDemand[b] - demand_g[v] + demand_g[u];
        if (newDemA > capacity_g[a] || newDemB > capacity_g[b]) return false;
        rev.type = 1; rev.rA = a; rev.posA = posA; rev.rB = b; rev.posB = posB; rev.u = u; rev.v = v;
        rev.delta = deltaSwap(a, posA, b, posB, cur);
        applySwap(cur, rev);
        return true;
    } else {
        vector<int> nonEmpty;
        vector<int> nonFull;
        for (int i = 0; i < T_g; i++){
            if (!cur.rutas[i].empty()) nonEmpty.push_back(i);
            if (cur.routeDemand[i] < capacity_g[i]) nonFull.push_back(i);
        }
        if (nonEmpty.empty() || nonFull.empty()) return false;
        int a = nonEmpty[rand() % nonEmpty.size()];
        int b = nonFull[rand() % nonFull.size()];
        if (a == b) return false;
        int posA = rand() % cur.rutas[a].size();
        int u = cur.rutas[a][posA];
        if (cur.routeDemand[b] + demand_g[u] > capacity_g[b]) return false;
        int posB = rand() % (cur.rutas[b].size() + 1);
        rev.type = 0; rev.rA = a; rev.posA = posA; rev.rB = b; rev.posB = posB; rev.u = u;
        rev.delta = deltaMoveSolo(a, posA, b, posB, cur);
        applyMoveSolo(cur, rev);
        return true;
    }
}

// -----------------------------------------------------------
//   Main solver function exposed to Python
// -----------------------------------------------------------
vector<vector<int>> solve_vrp_py(
    int N, int T,
    const vector<int> &capacity,
    const vector<int> &demand,
    const vector<vector<double>> &distMat,
    double T0, double Tf, double alpha,
    int iterPerTemp, double lambdaPen, double maxSeconds,
    unsigned long long seed)
{
    // Inicializar globals
    N_g = N;
    T_g = T;
    capacity_g = capacity;
    demand_g = demand;
    distMat_g = distMat;
    lambdaPen_g = lambdaPen;
    srand(seed);
    
    // Crear solución inicial
    SolutionFast best = initialSolutionFast();
    SolutionFast current = best;
    double Tactual = T0;
    auto startTime = chrono::steady_clock::now();
    uniform_real_distribution<double> uni01(0.0, 1.0);
    
    RevertInfo rev;
    
    while (Tactual > Tf) {
        for (int iter = 0; iter < iterPerTemp; iter++) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - startTime).count();
            if (elapsed > maxSeconds) { Tactual = Tf; break; }
            SolutionFast backup = current;
            if (!neighborFast(current, rev)) continue;
            double sumC = 0;
            for (int i = 0; i < T_g; i++) sumC += current.routeCost[i];
            int active = 0;
            for (int i = 0; i < T_g; i++) if (!current.rutas[i].empty()) active++;
            current.activeTrucks = active;
            current.totalCost = sumC + lambdaPen * active;
            double dE = current.totalCost - best.totalCost;
            if (dE < 0) {
                best = current;
            } else if (((double)rand()/RAND_MAX) >= exp(-dE / Tactual)) {
                current = backup;
            }
        }
        Tactual *= alpha;
    }
    
    return best.rutas;
}

PYBIND11_MODULE(sa_solver, m) {
    m.doc() = "VRP solver con Simulated Annealing optimizado vía Pybind11";
    m.def("solve", &solve_vrp_py,
          py::arg("N"), py::arg("T"),
          py::arg("capacity"), py::arg("demand"), py::arg("distMat"),
          py::arg("T0"), py::arg("Tf"), py::arg("alpha"),
          py::arg("iterPerTemp"), py::arg("lambdaPen"), py::arg("maxSeconds"), py::arg("seed"),
          "Solve VRP returns list of routes (each a list of node indices)");
}
