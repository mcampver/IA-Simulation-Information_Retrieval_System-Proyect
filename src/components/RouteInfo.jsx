import React from 'react';
import { basePanel, getZonePosition, Z_LAYERS } from './LayoutManager';

const RouteInfo = ({ routes, onSelectRoute }) => {
  const panelStyles = {
    ...basePanel,
    ...getZonePosition('bottomRight'),
    zIndex: Z_LAYERS.panels,
    minWidth: '280px',
    maxWidth: '340px',
    maxHeight: '40vh',
    overflowY: 'auto'
  };

  const headerStyles = {
    background: 'linear-gradient(135deg, #059669, #10b981)',
    color: 'white',
    padding: '12px 15px',
    borderRadius: '12px 12px 0 0',
    position: 'sticky',
    top: 0,
    zIndex: 1
  };

  const contentStyles = {
    padding: '15px'
  };

  const routeItemStyles = {
    padding: '12px',
    margin: '8px 0',
    borderRadius: '8px',
    border: '1px solid #e5e7eb',
    backgroundColor: 'white',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    transition: 'all 0.3s ease'
  };

  const colorIndicatorStyles = (color) => ({
    width: '16px',
    height: '16px',
    borderRadius: '50%',
    backgroundColor: `rgb(${color.join(',')})`,
    border: '2px solid white',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)'
  });

  const routeInfoStyles = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '2px'
  };

  const routeTitleStyles = {
    fontWeight: '600',
    fontSize: '14px',
    color: '#111827'
  };

  const routeDetailsStyles = {
    fontSize: '12px',
    color: '#6b7280'
  };

  return (
    <div style={panelStyles}>
      <div style={headerStyles}>
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>
          🗺️ Rutas Optimizadas ({routes.length})
        </h3>
      </div>
      
      <div style={contentStyles}>
        {routes.map((route, index) => (
          <div 
            key={route.id}
            style={{
              ...routeItemStyles,
              backgroundColor: route.selected ? '#f0f9ff' : 'white',
              borderColor: route.selected ? '#3b82f6' : '#e5e7eb',
              transform: route.selected ? 'scale(1.02)' : 'scale(1)'
            }}
            onClick={() => onSelectRoute(route.id)}
            onMouseOver={(e) => {
              if (!route.selected) {
                e.currentTarget.style.backgroundColor = '#f9fafb';
                e.currentTarget.style.transform = 'scale(1.01)';
              }
            }}
            onMouseOut={(e) => {
              if (!route.selected) {
                e.currentTarget.style.backgroundColor = 'white';
                e.currentTarget.style.transform = 'scale(1)';
              }
            }}
          >
            <div style={colorIndicatorStyles(route.color)} />
            <div style={routeInfoStyles}>
              <div style={routeTitleStyles}>
                {route.vehicleId || `Ruta ${index + 1}`}
              </div>
              {route.distance && (
                <div style={routeDetailsStyles}>
                  📏 {route.distance.toFixed(2)} km • 📍 {route.path.length} puntos
                </div>
              )}
            </div>
            {route.selected && (
              <div style={{ color: '#3b82f6', fontSize: '16px' }}>✓</div>
            )}
          </div>
        ))}
        
        <div style={{
          fontSize: '11px',
          color: '#9ca3af',
          textAlign: 'center',
          marginTop: '12px',
          paddingTop: '12px',
          borderTop: '1px solid #f3f4f6'
        }}>
          💡 Haz clic en una ruta para resaltarla
        </div>
      </div>
    </div>
  );
};

export default RouteInfo;