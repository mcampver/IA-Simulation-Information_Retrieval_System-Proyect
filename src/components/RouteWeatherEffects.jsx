import React from 'react';

const RouteWeatherEffects = ({ routes, weatherInfo }) => {
  if (!routes || !weatherInfo) return null;

  const getStatusClass = (factor) => {
    if (factor <= 1.1) return 'optimal';
    if (factor <= 1.3) return 'good';
    if (factor <= 1.6) return 'moderate';
    if (factor <= 2.0) return 'adverse';
    return 'severe';
  };

  const generateRouteParticles = (weatherFactor) => {
    if (weatherFactor <= 1.3) return [];
    
    const particleCount = Math.min(20, Math.floor((weatherFactor - 1.0) * 10));
    const particles = [];
    
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        id: i,
        type: weatherFactor > 2.0 ? 'storm' : 
              weatherFactor > 1.6 ? 'rain' : 'cloud',
        x: Math.random() * 100,
        y: Math.random() * 100,
        delay: Math.random() * 3
      });
    }
    
    return particles;
  };

  const particles = generateRouteParticles(weatherInfo.impact_factor);

  const particleOverlayStyles = {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    pointerEvents: 'none',
    zIndex: 998
  };

  const particleStyles = {
    position: 'absolute',
    fontSize: '16px',
    opacity: 0.6,
    animation: 'weatherParticle 3s ease-in-out infinite'
  };

  const statusIndicatorStyles = {
    position: 'fixed',
    bottom: '20px',
    right: '20px',
    zIndex: 1000,
    background: 'rgba(255, 255, 255, 0.95)',
    borderRadius: '12px',
    padding: '12px 16px',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    backdropFilter: 'blur(10px)',
    border: '1px solid rgba(0, 0, 0, 0.1)'
  };

  const getStatusColor = (factor) => {
    if (factor <= 1.1) return '#22c55e';
    if (factor <= 1.3) return '#84cc16';
    if (factor <= 1.6) return '#eab308';
    if (factor <= 2.0) return '#f97316';
    return '#ef4444';
  };

  const statusLightStyles = {
    width: '12px',
    height: '12px',
    borderRadius: '50%',
    backgroundColor: getStatusColor(weatherInfo.impact_factor),
    position: 'relative',
    animation: 'statusPulse 2s ease-in-out infinite'
  };

  const statusTextStyles = {
    display: 'flex',
    flexDirection: 'column'
  };

  const statusTitleStyles = {
    fontSize: '12px',
    fontWeight: '600',
    color: '#374151',
    marginBottom: '2px'
  };

  const statusDescriptionStyles = {
    fontSize: '11px',
    color: '#6b7280'
  };

  const alertStyles = {
    position: 'fixed',
    top: '20px',
    left: '50%',
    transform: 'translateX(-50%)',
    zIndex: 1001,
    background: weatherInfo.impact_factor > 2.0 ? 
      'linear-gradient(135deg, #ef4444, #dc2626)' : 
      'linear-gradient(135deg, #f97316, #ea580c)',
    color: 'white',
    borderRadius: '12px',
    padding: '12px 20px',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    animation: 'alertPulse 2s ease-in-out infinite'
  };

  const alertIconStyles = {
    fontSize: '20px',
    animation: 'alertIcon 1s ease-in-out infinite'
  };

  const alertContentStyles = {
    display: 'flex',
    flexDirection: 'column'
  };

  const alertTitleStyles = {
    fontSize: '14px',
    fontWeight: 'bold',
    marginBottom: '2px'
  };

  const alertMessageStyles = {
    fontSize: '12px',
    opacity: 0.9
  };

  return (
    <>
      {/* Overlay de partículas climáticas */}
      {particles.length > 0 && (
        <div style={particleOverlayStyles}>
          {particles.map(particle => (
            <div
              key={particle.id}
              style={{
                ...particleStyles,
                left: `${particle.x}%`,
                top: `${particle.y}%`,
                animationDelay: `${particle.delay}s`
              }}
            >
              {particle.type === 'storm' ? '⚡' :
               particle.type === 'rain' ? '💧' : '☁️'}
            </div>
          ))}
        </div>
      )}

      {/* Indicador de estado de rutas */}
      <div style={statusIndicatorStyles}>
        <div style={statusLightStyles}></div>
        <div style={statusTextStyles}>
          <div style={statusTitleStyles}>Estado de Rutas</div>
          <div style={statusDescriptionStyles}>
            {weatherInfo.impact_factor <= 1.1 ? 'Tránsito Normal' :
             weatherInfo.impact_factor <= 1.3 ? 'Leve Reducción' :
             weatherInfo.impact_factor <= 1.6 ? 'Moderadamente Afectado' :
             weatherInfo.impact_factor <= 2.0 ? 'Severamente Afectado' :
             'Condiciones Críticas'}
          </div>
        </div>
      </div>

      {/* Alertas visuales */}
      {weatherInfo.impact_factor > 1.6 && (
        <div style={alertStyles}>
          <div style={alertIconStyles}>
            {weatherInfo.impact_factor > 2.0 ? '🚨' : '⚠️'}
          </div>
          <div style={alertContentStyles}>
            <div style={alertTitleStyles}>
              {weatherInfo.impact_factor > 2.0 ? 'ALERTA CLIMÁTICA' : 'PRECAUCIÓN'}
            </div>
            <div style={alertMessageStyles}>
              {weatherInfo.impact_factor > 2.0 ? 
                'Condiciones climáticas severas detectadas' :
                'Condiciones climáticas adversas'}
            </div>
          </div>
        </div>
      )}

      {/* CSS animations via style tag */}
      <style>{`
        @keyframes weatherParticle {
          0% { transform: translateY(-20px) rotate(0deg); opacity: 0; }
          20% { opacity: 0.6; }
          80% { opacity: 0.6; }
          100% { transform: translateY(20px) rotate(360deg); opacity: 0; }
        }

        @keyframes statusPulse {
          0%, 100% { opacity: 0.8; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.1); }
        }

        @keyframes alertPulse {
          0%, 100% { transform: translateX(-50%) scale(1); }
          50% { transform: translateX(-50%) scale(1.02); }
        }

        @keyframes alertIcon {
          0%, 100% { transform: rotate(0deg); }
          25% { transform: rotate(-5deg); }
          75% { transform: rotate(5deg); }
        }
      `}</style>
    </>
  );
};

export default RouteWeatherEffects;
