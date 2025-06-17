// src/components/CompanyMarker.jsx
import React from 'react';
import { Marker } from 'react-map-gl/maplibre';

const CompanyMarker = ({ company }) => (
    <Marker longitude={company.lon} latitude={company.lat} anchor="bottom">
        {/* Marcador simple con un círculo */}
        <div
            style={{
                backgroundColor: '#FF5722',
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                border: '2px solid white',
                boxShadow: '0 0 4px rgba(0,0,0,0.3)'
            }}
            title={company.name}
        />
    </Marker>
);

export default CompanyMarker;
