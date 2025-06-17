// src/data/trucks.js
export const INITIAL_TRUCKS = Array.from({ length: 5 }, (_, i) => ({
    id: `truck_${i + 1}`,
    capacity: 100,          // capacidad máxima en “unidades”
    currentLoad: 0,         // carga actual
    assignedOrders: [],     // pedidos asignados
    position: null,         // [lon, lat], se inicializa luego
    color: null             // se le dará un color único
}));
