// src/components/TruckList.jsx
import React from 'react';

export default function TruckList({ trucks }) {
    return (
        <div style={{ marginTop: 10, fontSize: '0.9rem' }}>
            <h3 style={{ margin: '0 0 5px 0' }}>Camiones activos</h3>
            <ul style={{ padding: 0, listStyle: 'none' }}>
                {trucks.map(t => (
                    <li key={t.id} style={{ marginBottom: 6 }}>
                        <strong>{t.id}</strong>: {t.currentLoad}/{t.capacity} unidades
                        <div style={{ fontSize: '0.8rem', color: '#555' }}>
                            Pedidos: {t.assignedOrders.length}
                        </div>
                    </li>
                ))}
            </ul>
        </div>
    );
}
