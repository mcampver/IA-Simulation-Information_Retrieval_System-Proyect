import React from "react";

const RouteStats = ({ optimizedRoutes, onSelectRoute, selectedRouteId }) => {
  if (!optimizedRoutes || optimizedRoutes.length === 0) {
    return null;
  }

  // Calcular estadísticas generales
  const totalDistance = optimizedRoutes.reduce((sum, route) => sum + route.distance, 0);
  const totalPoints = optimizedRoutes.reduce((sum, route) => sum + route.path.length, 0);
  const avgDistance = totalDistance / optimizedRoutes.length;

  // Estilos adaptados para uso en modal (sin posicionamiento fijo)
  const containerStyles = {
    width: '100%',
    maxHeight: '60vh',
    overflowY: 'auto'
  };

  const summaryStyles = {
    backgroundColor: '#f0fdf4',
    border: '1px solid #bbf7d0',
    borderRadius: '8px',
    padding: '16px',
    marginBottom: '20px'
  };

  const summaryTitleStyles = {
    fontSize: '16px',
    fontWeight: '600',
    color: '#166534',
    marginBottom: '12px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  };

  const summaryGridStyles = {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px'
  };

  const summaryItemStyles = {
    fontSize: '14px',
    color: '#166534',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px'
  };

  const routeItemStyles = {
    padding: '16px',
    margin: '12px 0',
    borderRadius: '8px',
    border: '1px solid #e5e7eb',
    backgroundColor: 'white',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    transition: 'all 0.3s ease'
  };

  const colorIndicatorStyles = (color) => ({
    width: '20px',
    height: '20px',
    borderRadius: '50%',
    backgroundColor: `rgb(${color.join(',')})`,
    border: '3px solid white',
    boxShadow: '0 2px 6px rgba(0, 0, 0, 0.15)',
    flexShrink: 0
  });

  const routeInfoStyles = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '6px'
  };

  const routeTitleStyles = {
    fontWeight: '600',
    fontSize: '16px',
    color: '#111827'
  };

  const routeDetailsStyles = {
    fontSize: '14px',
    color: '#6b7280',
    lineHeight: '1.4'
  };

  const routeMetricsStyles = {
    fontSize: '12px',
    color: '#9ca3af',
    display: 'flex',
    gap: '16px',
    marginTop: '4px'
  };

  // Preparar rutas con información de selección
  const routesWithSelection = optimizedRoutes.map(route => ({
    ...route,
    selected: route.id === selectedRouteId
  }));

  return (
    <div style={containerStyles}>
      {/* Resumen General */}
      <div style={summaryStyles}>
        <div style={summaryTitleStyles}>
          <span>📈</span>
          Resumen General
        </div>
        <div style={summaryGridStyles}>
          <div style={summaryItemStyles}>
            <span style={{ fontSize: '12px', fontWeight: '500' }}>Total de rutas</span>
            <strong style={{ fontSize: '18px' }}>{optimizedRoutes.length}</strong>
          </div>
          <div style={summaryItemStyles}>
            <span style={{ fontSize: '12px', fontWeight: '500' }}>Distancia total</span>
            <strong style={{ fontSize: '18px' }}>{totalDistance.toFixed(2)} km</strong>
          </div>
          <div style={summaryItemStyles}>
            <span style={{ fontSize: '12px', fontWeight: '500' }}>Distancia promedio</span>
            <strong style={{ fontSize: '18px' }}>{avgDistance.toFixed(2)} km</strong>
          </div>
          <div style={summaryItemStyles}>
            <span style={{ fontSize: '12px', fontWeight: '500' }}>Total de puntos</span>
            <strong style={{ fontSize: '18px' }}>{totalPoints}</strong>
          </div>
        </div>
      </div>

      {/* Lista de Rutas Individuales */}
      <div style={{
        fontSize: '16px',
        fontWeight: '600',
        color: '#374151',
        marginBottom: '16px',
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        <span>🚛</span>
        Rutas Individuales
      </div>

      {routesWithSelection.map((route, index) => (
        <div 
          key={route.id}
          style={{
            ...routeItemStyles,
            backgroundColor: route.selected ? '#f0f9ff' : 'white',
            borderColor: route.selected ? '#3b82f6' : '#e5e7eb',
            transform: route.selected ? 'scale(1.02)' : 'scale(1)',
            boxShadow: route.selected ? '0 6px 16px rgba(59, 130, 246, 0.15)' : '0 2px 6px rgba(0, 0, 0, 0.05)'
          }}
          onClick={() => onSelectRoute && onSelectRoute(route.id)}
          onMouseOver={(e) => {
            if (!route.selected) {
              e.currentTarget.style.backgroundColor = '#f9fafb';
              e.currentTarget.style.transform = 'scale(1.01)';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.1)';
            }
          }}
          onMouseOut={(e) => {
            if (!route.selected) {
              e.currentTarget.style.backgroundColor = 'white';
              e.currentTarget.style.transform = 'scale(1)';
              e.currentTarget.style.boxShadow = '0 2px 6px rgba(0, 0, 0, 0.05)';
            }
          }}
        >
          <div style={colorIndicatorStyles(route.color)} />
          <div style={routeInfoStyles}>
            <div style={routeTitleStyles}>
              {route.vehicleId || `Ruta ${index + 1}`}
            </div>
            <div style={routeDetailsStyles}>
              📏 {route.distance.toFixed(2)} km • 📍 {route.path.length} puntos
            </div>
            <div style={routeMetricsStyles}>
              <span>⏱️ ~{(route.distance * 2).toFixed(0)} min</span>
              <span>⚡ {((route.distance / totalDistance) * 100).toFixed(1)}% del total</span>
            </div>
          </div>
          {route.selected && (
            <div style={{ 
              color: '#3b82f6', 
              fontSize: '20px',
              flexShrink: 0,
              animation: 'pulse 2s infinite'
            }}>
              ✓
            </div>
          )}
        </div>
      ))}
      
      <div style={{
        fontSize: '12px',
        color: '#9ca3af',
        textAlign: 'center',
        marginTop: '20px',
        paddingTop: '16px',
        borderTop: '1px solid #f3f4f6',
        lineHeight: '1.4'
      }}>
        💡 Haz clic en una ruta para resaltarla en el mapa
      </div>

      {/* CSS para animaciones */}
      <style jsx>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
};

export default RouteStats;