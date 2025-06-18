import React from 'react';
import { Z_LAYERS } from './LayoutManager';

const FloatingControls = ({ 
  showDetailedStats, 
  setShowDetailedStats, 
  showWeatherPanel, 
  setShowWeatherPanel,
  weatherInfo 
}) => {
  const controlsStyles = {
    position: 'fixed',
    bottom: '20px',
    left: '20px',
    zIndex: Z_LAYERS.panels,
    display: 'flex',
    flexDirection: 'column',
    gap: '12px'
  };

  const buttonBaseStyles = {
    width: '56px',
    height: '56px',
    borderRadius: '50%',
    border: 'none',
    cursor: 'pointer',
    fontSize: '20px',
    transition: 'all 0.3s ease',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
    backdropFilter: 'blur(10px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  };

  const statsButtonStyles = {
    ...buttonBaseStyles,
    background: showDetailedStats 
      ? 'linear-gradient(135deg, #3b82f6, #1d4ed8)' 
      : 'rgba(59, 130, 246, 0.9)',
    color: 'white'
  };

  const weatherButtonStyles = {
    ...buttonBaseStyles,
    background: showWeatherPanel 
      ? 'linear-gradient(135deg, #059669, #047857)' 
      : 'rgba(5, 150, 105, 0.9)',
    color: 'white'
  };

  return (
    <div style={controlsStyles}>
      <button 
        style={statsButtonStyles}
        onClick={() => setShowDetailedStats(!showDetailedStats)}
        onMouseEnter={(e) => e.target.style.transform = 'scale(1.1)'}
        onMouseLeave={(e) => e.target.style.transform = 'scale(1)'}
        title={showDetailedStats ? 'Ocultar estadísticas' : 'Ver estadísticas'}
      >
        📊
      </button>
      
      {weatherInfo && (
        <button 
          style={weatherButtonStyles}
          onClick={() => setShowWeatherPanel(!showWeatherPanel)}
          onMouseEnter={(e) => e.target.style.transform = 'scale(1.1)'}
          onMouseLeave={(e) => e.target.style.transform = 'scale(1)'}
          title={showWeatherPanel ? 'Ocultar clima' : 'Mostrar clima'}
        >
          {showWeatherPanel ? '🌤️' : '🌦️'}
        </button>
      )}
    </div>
  );
};

export default FloatingControls;