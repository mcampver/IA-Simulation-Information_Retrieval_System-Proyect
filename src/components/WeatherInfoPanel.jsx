import React, { useEffect, useState } from 'react';

const WeatherInfoPanel = ({ 
  weatherInfo, 
  showWeatherModal, 
  setShowWeatherModal 
}) => {
  const [animatedFactor, setAnimatedFactor] = useState(1.0);

  useEffect(() => {
    if (weatherInfo?.impact_factor) {
      // Animar el factor gradualmente para efecto visual
      const targetFactor = weatherInfo.impact_factor;
      const duration = 1000; // 1 segundo
      const steps = 60;
      const increment = (targetFactor - animatedFactor) / steps;
      
      let currentStep = 0;
      const interval = setInterval(() => {
        currentStep++;
        setAnimatedFactor(prev => prev + increment);
        
        if (currentStep >= steps) {
          setAnimatedFactor(targetFactor);
          clearInterval(interval);
        }
      }, duration / steps);
      
      return () => clearInterval(interval);
    }
  }, [weatherInfo?.impact_factor]);

  if (!showWeatherModal) return null;

  const getImpactColor = (factor) => {
    if (factor <= 1.1) return { bg: '#22c55e', text: '#ffffff' }; // Verde - sin impacto
    if (factor <= 1.3) return { bg: '#84cc16', text: '#ffffff' }; // Verde claro - impacto mínimo
    if (factor <= 1.6) return { bg: '#eab308', text: '#000000' }; // Amarillo - impacto moderado
    if (factor <= 2.0) return { bg: '#f97316', text: '#ffffff' }; // Naranja - impacto alto
    return { bg: '#ef4444', text: '#ffffff' }; // Rojo - impacto severo
  };

  const getImpactLevel = (factor) => {
    if (factor <= 1.1) return 'ÓPTIMO';
    if (factor <= 1.3) return 'BUENO';
    if (factor <= 1.6) return 'MODERADO';
    if (factor <= 2.0) return 'ADVERSO';
    return 'SEVERO';
  };

  const getProgressPercentage = (factor) => {
    // Convertir factor de impacto a porcentaje para barra de progreso
    const minFactor = 1.0;
    const maxFactor = 3.0;
    return Math.min(100, ((factor - minFactor) / (maxFactor - minFactor)) * 100);
  };

  const formatTemperature = (temp) => {
    return temp ? `${temp.toFixed(1)}°C` : 'N/A';
  };

  const formatSpeed = (speed) => {
    return speed ? `${speed.toFixed(1)} km/h` : 'N/A';
  };

  const formatPrecipitation = (precip) => {
    return precip ? `${precip.toFixed(1)} mm` : '0 mm';
  };

  const impactColors = getImpactColor(animatedFactor);
  const progressPercent = getProgressPercentage(animatedFactor);

  const weatherGridStyles = {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '10px',
    marginBottom: '20px'
  };

  const weatherItemStyles = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '12px',
    background: '#f9fafb',
    borderRadius: '8px',
    border: '1px solid #e5e7eb'
  };

  const gaugeContainerStyles = {
    width: '100%',
    height: '20px',
    backgroundColor: '#e5e7eb',
    borderRadius: '10px',
    overflow: 'hidden',
    marginBottom: '10px',
    position: 'relative'
  };

  const gaugeFillStyles = {
    height: '100%',
    backgroundColor: impactColors.bg,
    transition: 'width 1s ease-out',
    width: `${progressPercent}%`
  };

  const impactBadgeStyles = {
    backgroundColor: impactColors.bg,
    color: impactColors.text,
    padding: '12px 20px',
    borderRadius: '25px',
    textAlign: 'center',
    marginBottom: '15px',
    fontWeight: 'bold'
  };

  return (
    <>
      {/* Backdrop */}
      <div 
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0, 0, 0, 0.4)",
          zIndex: 450,
          backdropFilter: "blur(2px)"
        }}
        onClick={() => setShowWeatherModal(false)}
      />
      
      {/* Modal Content */}
      <div style={{
        position: "fixed",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        zIndex: 500,
        maxWidth: "600px",
        width: "90vw",
        maxHeight: "85vh",
        overflowY: "auto",
        padding: "0",
        backgroundColor: "rgba(255, 255, 255, 0.98)",
        borderRadius: "12px",
        boxShadow: "0 8px 25px rgba(0,0,0,0.2)",
        backdropFilter: "blur(10px)",
        border: "1px solid rgba(255, 255, 255, 0.3)",
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
      }}>
        <div style={{
          position: "sticky",
          top: 0,
          background: "linear-gradient(135deg, #4f46e5, #7c3aed)",
          color: "white",
          padding: "15px 20px",
          borderRadius: "12px 12px 0 0",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          zIndex: 501
        }}>
          <h2 style={{ margin: 0, fontSize: "18px", fontWeight: "600" }}>
            🌤️ Análisis Climático en Tiempo Real
          </h2>
          <button 
            onClick={() => setShowWeatherModal(false)}
            style={{
              background: "rgba(255, 255, 255, 0.2)",
              border: "none",
              color: "white",
              fontSize: "18px",
              cursor: "pointer",
              borderRadius: "50%",
              width: "32px",
              height: "32px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "all 0.3s ease"
            }}
            onMouseOver={(e) => e.target.style.backgroundColor = "rgba(255, 255, 255, 0.3)"}
            onMouseOut={(e) => e.target.style.backgroundColor = "rgba(255, 255, 255, 0.2)"}
          >
            ✕
          </button>
        </div>
        
        <div style={{ padding: "20px" }}>
          {weatherInfo ? (
            <>
              {/* Indicador Principal de Impacto */}
              <div style={{ marginBottom: '20px' }}>
                <div style={gaugeContainerStyles}>
                  <div style={gaugeFillStyles}></div>
                  <div style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '0 8px',
                    fontSize: '10px',
                    color: '#6b7280'
                  }}>
                    <span>ÓPTIMO</span>
                    <span>SEVERO</span>
                  </div>
                </div>
                
                <div style={impactBadgeStyles}>
                  <div style={{ fontSize: '18px', fontWeight: 'bold' }}>
                    {animatedFactor.toFixed(2)}x
                  </div>
                  <div style={{ fontSize: '12px', marginTop: '4px' }}>
                    {getImpactLevel(animatedFactor)}
                  </div>
                </div>
                
                <div style={{ 
                  fontSize: '13px', 
                  color: '#4b5563', 
                  textAlign: 'center',
                  lineHeight: '1.4'
                }}>
                  {weatherInfo.interpretation || 'Evaluando condiciones...'}
                </div>
              </div>

              {/* Visualización de Velocidad */}
              <div style={{ marginBottom: '20px' }}>
                <h4 style={{ 
                  margin: '0 0 12px 0', 
                  fontSize: '14px', 
                  color: '#374151', 
                  fontWeight: '600' 
                }}>
                  📍 Impacto en Velocidad
                </h4>
                
                <div style={{ marginBottom: '8px' }}>
                  <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '4px' }}>
                    Velocidad Normal
                  </div>
                  <div style={{
                    width: '100%',
                    height: '8px',
                    backgroundColor: '#e5e7eb',
                    borderRadius: '4px',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      width: '100%',
                      height: '100%',
                      backgroundColor: '#22c55e'
                    }}></div>
                  </div>
                </div>
                
                <div style={{ marginBottom: '8px' }}>
                  <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '4px' }}>
                    Velocidad con Clima
                  </div>
                  <div style={{
                    width: '100%',
                    height: '8px',
                    backgroundColor: '#e5e7eb',
                    borderRadius: '4px',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      width: `${Math.max(20, 100 / animatedFactor)}%`,
                      height: '100%',
                      backgroundColor: impactColors.bg,
                      transition: 'width 1s ease-out'
                    }}></div>
                  </div>
                </div>
                
                <div style={{ 
                  fontSize: '12px', 
                  color: '#4b5563', 
                  textAlign: 'center',
                  fontWeight: '600'
                }}>
                  {((100 / animatedFactor)).toFixed(0)}% de velocidad normal
                </div>
              </div>

              {/* Condiciones Meteorológicas */}
              {weatherInfo.weather_summary && (
                <div style={{ marginBottom: '20px' }}>
                  <h4 style={{ 
                    margin: '0 0 12px 0', 
                    fontSize: '14px', 
                    color: '#374151', 
                    fontWeight: '600' 
                  }}>
                    🌡️ Condiciones Actuales
                  </h4>
                  
                  <div style={weatherGridStyles}>
                    <div style={weatherItemStyles}>
                      <div style={{ fontSize: '20px', marginBottom: '4px' }}>
                        {weatherInfo.weather_summary.temperature_2m > 30 ? '🌡️🔥' : 
                         weatherInfo.weather_summary.temperature_2m < 15 ? '🌡️❄️' : '🌡️'}
                      </div>
                      <span style={{ fontSize: '11px', color: '#6b7280', marginBottom: '2px' }}>
                        Temperatura
                      </span>
                      <span style={{ fontSize: '13px', fontWeight: '600', color: '#111827' }}>
                        {formatTemperature(weatherInfo.weather_summary.temperature_2m)}
                      </span>
                    </div>
                    
                    <div style={weatherItemStyles}>
                      <div style={{ fontSize: '20px', marginBottom: '4px' }}>
                        {weatherInfo.weather_summary.precipitation > 10 ? '🌧️⛈️' :
                         weatherInfo.weather_summary.precipitation > 2 ? '🌧️' :
                         weatherInfo.weather_summary.precipitation > 0 ? '🌦️' : '☀️'}
                      </div>
                      <span style={{ fontSize: '11px', color: '#6b7280', marginBottom: '2px' }}>
                        Precipitación
                      </span>
                      <span style={{ fontSize: '13px', fontWeight: '600', color: '#111827' }}>
                        {formatPrecipitation(weatherInfo.weather_summary.precipitation)}
                      </span>
                    </div>
                    
                    <div style={weatherItemStyles}>
                      <div style={{ fontSize: '20px', marginBottom: '4px' }}>
                        {weatherInfo.weather_summary.wind_speed_10m > 40 ? '💨🌪️' :
                         weatherInfo.weather_summary.wind_speed_10m > 25 ? '💨' : '🍃'}
                      </div>
                      <span style={{ fontSize: '11px', color: '#6b7280', marginBottom: '2px' }}>
                        Viento
                      </span>
                      <span style={{ fontSize: '13px', fontWeight: '600', color: '#111827' }}>
                        {formatSpeed(weatherInfo.weather_summary.wind_speed_10m)}
                      </span>
                    </div>
                    
                    <div style={weatherItemStyles}>
                      <div style={{ fontSize: '20px', marginBottom: '4px' }}>
                        {weatherInfo.weather_summary.cloud_cover > 75 ? '☁️⛅' :
                         weatherInfo.weather_summary.cloud_cover > 25 ? '⛅' : '☀️'}
                      </div>
                      <span style={{ fontSize: '11px', color: '#6b7280', marginBottom: '2px' }}>
                        Nubosidad
                      </span>
                      <span style={{ fontSize: '13px', fontWeight: '600', color: '#111827' }}>
                        {weatherInfo.weather_summary.cloud_cover ? 
                          `${weatherInfo.weather_summary.cloud_cover}%` : 'N/A'}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Recomendaciones */}
              <div>
                <h4 style={{ 
                  margin: '0 0 10px 0', 
                  fontSize: '14px', 
                  color: '#374151', 
                  fontWeight: '600' 
                }}>
                  💡 Recomendaciones
                </h4>
                <ul style={{ 
                  margin: 0, 
                  paddingLeft: '16px', 
                  listStyleType: 'disc' 
                }}>
                  {animatedFactor <= 1.1 && (
                    <li style={{ fontSize: '12px', color: '#4b5563', lineHeight: '1.4', marginBottom: '6px' }}>
                      Condiciones óptimas para el transporte
                    </li>
                  )}
                  {animatedFactor > 1.1 && animatedFactor <= 1.3 && (
                    <>
                      <li style={{ fontSize: '12px', color: '#4b5563', lineHeight: '1.4', marginBottom: '6px' }}>
                        Ligero impacto en tiempos de entrega
                      </li>
                      <li style={{ fontSize: '12px', color: '#4b5563', lineHeight: '1.4', marginBottom: '6px' }}>
                        Mantener precaución normal
                      </li>
                    </>
                  )}
                  {animatedFactor > 1.3 && animatedFactor <= 1.6 && (
                    <>
                      <li style={{ fontSize: '12px', color: '#4b5563', lineHeight: '1.4', marginBottom: '6px' }}>
                        Considerar rutas alternativas
                      </li>
                      <li style={{ fontSize: '12px', color: '#4b5563', lineHeight: '1.4', marginBottom: '6px' }}>
                        Aumentar tiempo estimado de entrega
                      </li>
                    </>
                  )}
                  {animatedFactor > 1.6 && animatedFactor <= 2.0 && (
                    <>
                      <li style={{ fontSize: '12px', color: '#4b5563', lineHeight: '1.4', marginBottom: '6px' }}>
                        Reducir velocidad de vehículos
                      </li>
                      <li style={{ fontSize: '12px', color: '#4b5563', lineHeight: '1.4', marginBottom: '6px' }}>
                        Evaluar postponer entregas no urgentes
                      </li>
                      <li style={{ fontSize: '12px', color: '#4b5563', lineHeight: '1.4', marginBottom: '6px' }}>
                        Mantener comunicación constante con conductores
                      </li>
                    </>
                  )}
                  {animatedFactor > 2.0 && (
                    <>
                      <li style={{ fontSize: '12px', color: '#4b5563', lineHeight: '1.4', marginBottom: '6px' }}>
                        ⚠️ Considerar suspender operaciones
                      </li>
                      <li style={{ fontSize: '12px', color: '#4b5563', lineHeight: '1.4', marginBottom: '6px' }}>
                        Solo entregas de emergencia
                      </li>
                      <li style={{ fontSize: '12px', color: '#4b5563', lineHeight: '1.4', marginBottom: '6px' }}>
                        Activar protocolos de seguridad especiales
                      </li>
                    </>
                  )}
                </ul>
              </div>

              {/* Error handling */}
              {weatherInfo.error && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px',
                  background: '#fef2f2',
                  border: '1px solid #fecaca',
                  borderRadius: '6px',
                  fontSize: '12px',
                  color: '#dc2626',
                  marginTop: '15px'
                }}>
                  <span style={{ fontSize: '16px' }}>⚠️</span>
                  <span>Error obteniendo datos climáticos: {weatherInfo.error}</span>
                </div>
              )}
            </>
          ) : (
            <div style={{
              textAlign: 'center',
              padding: '40px 20px',
              color: '#6b7280'
            }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>🌤️</div>
              <h3 style={{ margin: '0 0 8px 0', color: '#374151' }}>
                No hay datos climáticos disponibles
              </h3>
              <p style={{ margin: 0, fontSize: '14px' }}>
                Los datos meteorológicos se cargarán automáticamente cuando estén disponibles.
              </p>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default WeatherInfoPanel;
