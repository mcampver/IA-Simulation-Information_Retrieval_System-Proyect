import React from 'react';

const StatusPanel = ({ 
  connectionStatus, 
  errorMessage, 
  vehicleCount,
  showOptimizationForm, 
  setShowOptimizationForm,
  weatherInfo
}) => {
  const getConnectionStatusColor = (status) => {
    switch(status.toLowerCase()) {
      case 'conectado': return '#22c55e';
      case 'conectando...': return '#eab308';
      case 'desconectado': case 'error': return '#ef4444';
      default: return '#6b7280';
    }
  };

  return (
    <div className="status-panel">
      {/* Estado de Conexión */}
      <div className="status-item">
        <div className="status-indicator">
          <div 
            className="status-dot"
            style={{ backgroundColor: getConnectionStatusColor(connectionStatus) }}
          ></div>
          <strong>Estado:</strong> {connectionStatus}
        </div>
      </div>

      {/* Error Messages */}
      {errorMessage && (
        <div className="status-item error">
          <span className="error-icon">⚠️</span>
          {errorMessage}
        </div>
      )}

      {/* Vehicle Count */}
      {/* <div className="status-item">
        <strong>🚛 Vehículos:</strong> {vehicleCount}
      </div> */}

      {/* Weather Summary */}
      {weatherInfo && (
        <div className="status-item weather-summary">
          <div className="weather-quick-info">
            <span className="weather-icon">
              {weatherInfo.impact_factor <= 1.1 ? '☀️' :
               weatherInfo.impact_factor <= 1.3 ? '⛅' :
               weatherInfo.impact_factor <= 1.6 ? '🌧️' :
               weatherInfo.impact_factor <= 2.0 ? '⛈️' : '🌪️'}
            </span>
            <div className="weather-text">
              <strong>Clima:</strong> Factor {weatherInfo.impact_factor?.toFixed(2)}x
              <div className="weather-status">
                {weatherInfo.impact_factor <= 1.1 ? 'Óptimo' :
                 weatherInfo.impact_factor <= 1.3 ? 'Bueno' :
                 weatherInfo.impact_factor <= 1.6 ? 'Moderado' :
                 weatherInfo.impact_factor <= 2.0 ? 'Adverso' : 'Severo'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Optimization Button */}
      <button 
        className="optimization-button"
        onClick={() => setShowOptimizationForm(!showOptimizationForm)}
      >
        {showOptimizationForm ? "Ocultar Optimización" : "Mostrar Optimización"}
      </button>      <style jsx>{`
        .status-panel {
          position: fixed;
          top: 10px;
          left: 10px;
          z-index: 250;
          padding: 16px;
          background: rgba(255, 255, 255, 0.95);
          backdrop-filter: blur(10px);
          border-radius: 12px;
          max-width: 320px;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.2);
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        .status-item {
          margin-bottom: 12px;
          font-size: 14px;
          color: #374151;
        }

        .status-item:last-child {
          margin-bottom: 0;
        }

        .status-indicator {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          animation: statusPulse 2s ease-in-out infinite;
        }

        @keyframes statusPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }

        .status-item.error {
          color: #dc2626;
          background: #fef2f2;
          padding: 8px;
          border-radius: 6px;
          border: 1px solid #fecaca;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .error-icon {
          font-size: 16px;
        }

        .weather-summary {
          background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
          padding: 12px;
          border-radius: 8px;
          border: 1px solid #bae6fd;
        }

        .weather-quick-info {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .weather-icon {
          font-size: 24px;
        }

        .weather-text {
          flex: 1;
        }

        .weather-status {
          font-size: 12px;
          color: #6b7280;
          margin-top: 2px;
        }

        .optimization-button {
          width: 100%;
          padding: 10px 16px;
          margin-top: 12px;
          background: linear-gradient(135deg, #4f46e5, #7c3aed);
          color: white;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
          transition: all 0.3s ease;
          box-shadow: 0 2px 8px rgba(79, 70, 229, 0.3);
        }

        .optimization-button:hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(79, 70, 229, 0.4);
          background: linear-gradient(135deg, #4338ca, #6d28d9);
        }

        .optimization-button:active {
          transform: translateY(0);
        }

        /* Responsive */
        @media (max-width: 768px) {
          .status-panel {
            max-width: 280px;
            padding: 12px;
          }
          
          .status-item {
            font-size: 13px;
          }
          
          .weather-icon {
            font-size: 20px;
          }
        }
      `}</style>
    </div>
  );
};

export default StatusPanel;