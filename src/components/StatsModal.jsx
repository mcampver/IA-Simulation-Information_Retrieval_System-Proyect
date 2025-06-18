import React from 'react';
import RouteStats from './RouteStats';

const StatsModal = ({ 
  showDetailedStats, 
  setShowDetailedStats, 
  optimizedRoutes, 
  selectedRouteId, 
  onSelectRoute 
}) => {
  if (!showDetailedStats) return null;
  
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
        onClick={() => setShowDetailedStats(false)}
      />
      
      {/* Modal Content */}
      <div style={{
        position: "fixed",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        zIndex: 500,
        maxWidth: "800px", // Aumentado para más espacio
        width: "90vw",
        maxHeight: "85vh",
        overflowY: "auto",
        padding: "0",
        backgroundColor: "rgba(255, 255, 255, 0.98)",
        borderRadius: "12px",
        boxShadow: "0 8px 25px rgba(0,0,0,0.2)",
        backdropFilter: "blur(10px)",
        border: "1px solid rgba(255, 255, 255, 0.3)"
      }}>
        <div style={{
          position: "sticky",
          top: 0,
          background: "linear-gradient(135deg, #059669, #10b981)",
          color: "white",
          padding: "15px 20px",
          borderRadius: "12px 12px 0 0",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          zIndex: 501
        }}>
          <h2 style={{ margin: 0, fontSize: "18px" }}>
            📊 Estadísticas de Rutas {optimizedRoutes?.length > 0 && `(${optimizedRoutes.length})`}
          </h2>
          <button 
            onClick={() => setShowDetailedStats(false)}
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
          {optimizedRoutes && optimizedRoutes.length > 0 ? (
            <RouteStats 
              optimizedRoutes={optimizedRoutes}
              onSelectRoute={onSelectRoute} // Habilitar selección en modal
              selectedRouteId={selectedRouteId}
            />
          ) : (
            <div style={{
              textAlign: 'center',
              padding: '40px 20px',
              color: '#6b7280'
            }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>📈</div>
              <h3 style={{ margin: '0 0 8px 0', color: '#374151' }}>
                No hay rutas optimizadas
              </h3>
              <p style={{ margin: 0, fontSize: '14px' }}>
                Utiliza el formulario de optimización para generar rutas y ver las estadísticas aquí.
              </p>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default StatsModal;