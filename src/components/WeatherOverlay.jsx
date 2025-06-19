import React from 'react';
import { Z_LAYERS } from './LayoutManager';

const WeatherOverlay = ({ weatherInfo, position = 'top-right' }) => {
  if (!weatherInfo) return null;

  const getImpactColor = (factor) => {
    if (factor <= 1.1) return '#22c55e';
    if (factor <= 1.3) return '#84cc16';
    if (factor <= 1.6) return '#eab308';
    if (factor <= 2.0) return '#f97316';
    return '#ef4444';
  };

  const getWeatherIcon = (weatherData) => {
    if (!weatherData) return '🌤️';
    
    const { precipitation, temperature_2m, wind_speed_10m, cloud_cover } = weatherData;
    
    if (precipitation > 10) return '⛈️';
    if (precipitation > 2) return '🌧️';
    if (precipitation > 0) return '🌦️';
    if (wind_speed_10m > 40) return '💨';
    if (cloud_cover > 75) return '☁️';
    if (temperature_2m > 30) return '☀️';
    return '🌤️';
  };

  // Posicionamiento específico arriba del formulario de optimización
  const overlayStyles = {
    position: 'fixed',
    top: '20px', // Misma coordenada Y que otros paneles
    right: '20px', // Alineado a la derecha
    zIndex: Z_LAYERS.overlays, // Mayor que panels pero menor que modals
    pointerEvents: 'none'
  };

  const indicatorStyles = {
    display: 'flex',
    alignItems: 'center',
    gap: '10px', // Reducido para compactar
    background: 'rgba(255, 255, 255, 0.95)',
    backdropFilter: 'blur(10px)',
    border: `2px solid ${getImpactColor(weatherInfo.impact_factor)}`,
    borderRadius: '25px', // Más compacto
    padding: '8px 12px', // Reducido
    boxShadow: '0 4px 15px rgba(0, 0, 0, 0.1)',
    transition: 'all 0.3s ease',
    minWidth: 'auto', // Permitir ancho automático
    width: 'fit-content'
  };

  const iconStyles = {
    fontSize: '20px', // Reducido
    filter: 'drop-shadow(0 1px 2px rgba(0, 0, 0, 0.1))'
  };

  const infoStyles = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    gap: '1px' // Compactar información
  };

  const factorStyles = {
    fontSize: '14px', // Reducido
    fontWeight: 'bold',
    lineHeight: 1,
    color: getImpactColor(weatherInfo.impact_factor),
    textShadow: '0 1px 2px rgba(0, 0, 0, 0.1)'
  };

  const statusStyles = {
    fontSize: '9px', // Muy pequeño
    fontWeight: '600',
    opacity: 0.8,
    lineHeight: 1,
    color: '#374151'
  };

  const getStatusText = (factor) => {
    if (factor <= 1.1) return 'ÓPTIMO';
    if (factor <= 1.3) return 'BUENO';
    if (factor <= 1.6) return 'MODERADO';
    if (factor <= 2.0) return 'ADVERSO';
    return 'SEVERO';
  };

  return (
    <>
      <div style={overlayStyles}>
        <div style={indicatorStyles}>
          <div style={iconStyles}>
            {getWeatherIcon(weatherInfo.weather_summary)}
          </div>
          <div style={infoStyles}>
            <div style={factorStyles}>
              {weatherInfo.impact_factor?.toFixed(2)}x
            </div>
            <div style={statusStyles}>
              {getStatusText(weatherInfo.impact_factor)}
            </div>
          </div>
        </div>
      </div>

      {/* Efecto Visual de Impacto en el Mapa */}
      {weatherInfo.impact_factor > 1.3 && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          pointerEvents: 'none',
          zIndex: 50 // Muy bajo para no interferir
        }}>
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: `radial-gradient(circle, ${getImpactColor(weatherInfo.impact_factor)}15 0%, transparent 70%)`,
            opacity: 0.2 // Reducido para menor interferencia
          }} />
        </div>
      )}
    </>
  );
};

export default WeatherOverlay;
