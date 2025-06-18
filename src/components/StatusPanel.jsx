import React from 'react';
import { basePanel, getZonePosition, Z_LAYERS } from './LayoutManager';

const StatusPanel = ({ 
  connectionStatus, 
  errorMessage, 
  vehicleCount, 
  showOptimizationForm, 
  setShowOptimizationForm 
}) => {
  const getStatusColor = (status) => {
    if (status.includes('Conectado')) return '#22c55e';
    if (status.includes('Error')) return '#ef4444';
    if (status.includes('Optimizando')) return '#3b82f6';
    return '#6b7280';
  };

  const panelStyles = {
    ...basePanel,
    ...getZonePosition('topLeft'),
    zIndex: Z_LAYERS.panels,
    minWidth: '280px',
    maxWidth: '340px'
  };

  const headerStyles = {
    background: 'linear-gradient(135deg, #4f46e5, #7c3aed)',
    color: 'white',
    padding: '12px 15px',
    borderRadius: '12px 12px 0 0',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  };

  const contentStyles = {
    padding: '15px'
  };

  const statusItemStyles = {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginBottom: '12px',
    fontSize: '14px'
  };

  const statusIndicatorStyles = {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    backgroundColor: getStatusColor(connectionStatus)
  };

  const buttonStyles = {
    width: '100%',
    padding: '12px 16px',
    backgroundColor: '#4f46e5',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '600',
    transition: 'all 0.3s ease',
    marginTop: '8px'
  };

  return (
    <div style={panelStyles}>
      <div style={headerStyles}>
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>
          🚛 Sistema de Transporte
        </h3>
      </div>
      
      <div style={contentStyles}>
        <div style={statusItemStyles}>
          <div style={statusIndicatorStyles}></div>
          <span style={{ color: '#374151' }}>Estado: {connectionStatus}</span>
        </div>
        
        <div style={statusItemStyles}>
          <span style={{ fontSize: '16px' }}>🚗</span>
          <span style={{ color: '#374151' }}>Vehículos: {vehicleCount}</span>
        </div>
        
        {errorMessage && (
          <div style={{
            ...statusItemStyles,
            backgroundColor: '#fef2f2',
            padding: '8px',
            borderRadius: '6px',
            border: '1px solid #fecaca',
            marginBottom: '12px'
          }}>
            <span style={{ fontSize: '16px' }}>⚠️</span>
            <span style={{ color: '#dc2626', fontSize: '12px' }}>{errorMessage}</span>
          </div>
        )}
        
        <button 
          style={buttonStyles}
          onClick={() => setShowOptimizationForm(!showOptimizationForm)}
          onMouseOver={(e) => e.target.style.backgroundColor = '#3730a3'}
          onMouseOut={(e) => e.target.style.backgroundColor = '#4f46e5'}
        >
          {showOptimizationForm ? '📋 Ocultar Optimización' : '🎯 Optimizar Rutas'}
        </button>
      </div>
    </div>
  );
};

export default StatusPanel;