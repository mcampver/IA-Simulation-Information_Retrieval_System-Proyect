// src/utils/assignOrders.js
/**
 * Asigna cada pedido a un camión que tenga suficiente capacidad.
 * Usa First-Fit Decreasing (ordenamos pedidos más grandes primero).
 */
export function assignOrdersToTrucks(orders, trucks) {
    // clonamos para no mutar original
    const trucksCopy = trucks.map(t => ({ ...t, assignedOrders: [], currentLoad: 0 }));
    // orden descendente por cantidad
    const sorted = [...orders].sort((a, b) => b.quantity - a.quantity);

    for (let order of sorted) {
        // buscamos primer camión donde quepa
        const truck = trucksCopy.find(t => t.currentLoad + order.quantity <= t.capacity);
        if (truck) {
            truck.assignedOrders.push(order);
            truck.currentLoad += order.quantity;
        } else {
            console.warn(`Pedido ${order.id} (${order.quantity}) no cabe en ningún camión`);
        }
    }

    return trucksCopy;
}
