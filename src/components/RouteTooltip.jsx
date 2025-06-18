import React from 'react';

const RouteTooltip = ({ hoveredRoute, position }) => {
  if (!hoveredRoute || !position) return null;

  const tooltipStyles = {
    position: 'fixed',
    left: position.x + 10,
    top: position.y - 10,
    backgroundColor: 'rgba(17, 24, 39, 0.95)',
    color: 'white',
    padding: '12px 16px',
    borderRadius: '8px',
    boxShadow: '0 10px 25px rgba(0, 0, 0, 0.3)',
    backdropFilter: 'blur(10px)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    fontSize: '13px',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    zIndex: 1000,
    maxWidth: '250px',
    pointerEvents: 'none'
  };

  const headerStyles = {
    fontSize: '14px',
    fontWeight: '600',
    marginBottom: '8px',
    color: '#f3f4f6',
    borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
    paddingBottom: '4px'
  };

  const itemStyles = {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '4px',
    color: '#d1d5db'
  };

  const valueStyles = {
    fontWeight: '500',
    color: '#f9fafb'
  };

  return (
    <div style={tooltipStyles}>
      <div style={headerStyles}>
        🚛 {hoveredRoute.vehicleId || `Ruta ${hoveredRoute.id}`}
      </div>
      
      <div style={itemStyles}>
        <span>📏 Distancia:</span>
        <span style={valueStyles}>{hoveredRoute.distance?.toFixed(2)} km</span>
      </div>
      
      <div style={itemStyles}>
        <span>📍 Paradas:</span>
        <span style={valueStyles}>{hoveredRoute.path?.length - 2}</span>
      </div>
      
      <div style={itemStyles}>
        <span>⏱️ Tiempo estimado:</span>
        <span style={valueStyles}>~{Math.round(hoveredRoute.distance * 2)} min</span>
      </div>
      
      {hoveredRoute.id === hoveredRoute.selectedId && (
        <div style={{
          marginTop: '8px',
          padding: '4px 8px',
          backgroundColor: 'rgba(59, 130, 246, 0.2)',
          borderRadius: '4px',
          fontSize: '11px',
          color: '#93c5fd',
          textAlign: 'center'
        }}>
          ✓ Ruta seleccionada
        </div>
      )}
    </div>
  );
};

export default RouteTooltip;