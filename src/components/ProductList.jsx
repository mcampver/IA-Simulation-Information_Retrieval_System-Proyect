// src/components/ProductList.jsx
import React from 'react';

const ProductList = ({ products }) => (
    <div style={{
        marginTop: '10px',
        maxHeight: '200px',
        overflowY: 'auto',
        fontSize: '0.9rem'
    }}>
        <h3 style={{ margin: '0 0 5px 0' }}>Pedidos pendientes</h3>
        <ul style={{ padding: 0, listStyle: 'none' }}>
            {products.map(p => (
                <li key={p.id} style={{ marginBottom: '4px' }}>
                    <strong>{p.name}</strong> x {p.quantity}
                    {p.express && (
                        <span style={{
                            marginLeft: '6px',
                            color: '#E91E63',
                            fontWeight: 'bold'
                        }}>
                            (Express)
                        </span>
                    )}
                </li>
            ))}
            {products.length === 0 && <li style={{ fontStyle: 'italic' }}>No hay pedidos</li>}
        </ul>
    </div>
);

export default ProductList;
