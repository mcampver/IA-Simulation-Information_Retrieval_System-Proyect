import React from 'react';
import { basePanel, getZonePosition, Z_LAYERS } from './LayoutManager';

const StatusPanel = ({ 
  connectionStatus, 
  errorMessage, 
  vehicleCount, 
  showOptimizationForm, 
  setShowOptimizationForm,
  showWeatherModal,
  setShowWeatherModal,
  weatherInfo,
  // Props para estadísticas
  showDetailedStats,
  setShowDetailedStats,
  hasRoutes,
  // NUEVO: Props para RAG
  showRAGPanel,
  setShowRAGPanel
}) => {
  const getStatusColor = (status) => {
    if (status.includes('Conectado')) return '#22c55e';
    if (status.includes('Error')) return '#ef4444';
    if (status.includes('Optimizando')) return '#3b82f6';
    return '#6b7280';
  };

  const getWeatherButtonColor = () => {
    if (!weatherInfo) return '#9ca3af';
    
    const factor = weatherInfo.impact_factor || 1.0;
    if (factor <= 1.1) return '#22c55e';
    if (factor <= 1.3) return '#84cc16';
    if (factor <= 1.6) return '#eab308';
    if (factor <= 2.0) return '#f97316';
    return '#ef4444';
  };

  const getStatsButtonColor = () => {
    return hasRoutes ? '#3b82f6' : '#9ca3af';
  };

  const getRAGButtonColor = () => {
    return '#7c3aed'; // Color púrpura para el asistente RAG
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
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '600',
    transition: 'all 0.3s ease',
    marginBottom: '8px'
  };

  const primaryButtonStyles = {
    ...buttonStyles,
    backgroundColor: '#4f46e5',
    color: 'white'
  };

  const weatherButtonStyles = {
    ...buttonStyles,
    backgroundColor: getWeatherButtonColor(),
    color: 'white'
  };

  const statsButtonStyles = {
    ...buttonStyles,
    backgroundColor: getStatsButtonColor(),
    color: 'white',
    opacity: hasRoutes ? 1 : 0.6,
    cursor: hasRoutes ? 'pointer' : 'not-allowed'
  };

  const ragButtonStyles = {
    ...buttonStyles,
    backgroundColor: getRAGButtonColor(),
    color: 'white'
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
        
        {weatherInfo && (
          <div style={statusItemStyles}>
            <span style={{ fontSize: '16px' }}>🌤️</span>
            <span style={{ color: '#374151' }}>
              Impacto Climático: {weatherInfo.impact_factor?.toFixed(2)}x
            </span>
          </div>
        )}

        {hasRoutes && (
          <div style={statusItemStyles}>
            <span style={{ fontSize: '16px' }}>📊</span>
            <span style={{ color: '#374151' }}>
              Rutas Activas: {hasRoutes}
            </span>
          </div>
        )}
        
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
          style={primaryButtonStyles}
          onClick={() => setShowOptimizationForm(!showOptimizationForm)}
          onMouseOver={(e) => e.target.style.backgroundColor = '#3730a3'}
          onMouseOut={(e) => e.target.style.backgroundColor = '#4f46e5'}
        >
          {showOptimizationForm ? '📋 Ocultar Optimización' : '🎯 Optimizar Rutas'}
        </button>

        <button 
          style={weatherButtonStyles}
          onClick={() => setShowWeatherModal(!showWeatherModal)}
          onMouseOver={(e) => e.target.style.opacity = '0.9'}
          onMouseOut={(e) => e.target.style.opacity = '1'}
        >
          🌤️ Análisis Climático
        </button>

        <button 
          style={statsButtonStyles}
          onClick={() => hasRoutes && setShowDetailedStats(!showDetailedStats)}
          onMouseOver={(e) => hasRoutes && (e.target.style.opacity = '0.9')}
          onMouseOut={(e) => hasRoutes && (e.target.style.opacity = '1')}
          disabled={!hasRoutes}
        >
          📊 {showDetailedStats ? 'Ocultar Estadísticas' : 'Ver Estadísticas'}
        </button>

        <button 
          style={ragButtonStyles}
          onClick={() => setShowRAGPanel(!showRAGPanel)}
          onMouseOver={(e) => e.target.style.backgroundColor = '#6d28d9'}
          onMouseOut={(e) => e.target.style.backgroundColor = '#7c3aed'}
        >
          🧠 {showRAGPanel ? 'Ocultar Asistente' : 'Asistente IA'}
        </button>
      </div>
    </div>
  );
};

export default StatusPanel;