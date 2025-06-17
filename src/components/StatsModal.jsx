import React from 'react';
import RouteStats from './RouteStats';

const StatsModal = ({ showDetailedStats, setShowDetailedStats, optimizedRoutes }) => {
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
        zIndex: 500,  // Muy alto para modal
        maxWidth: "600px",
        maxHeight: "80vh",
        overflowY: "auto",
        padding: "20px",
        backgroundColor: "rgba(255, 255, 255, 0.98)",
        borderRadius: "12px",
        boxShadow: "0 8px 25px rgba(0,0,0,0.2)",
        backdropFilter: "blur(10px)",
        border: "1px solid rgba(255, 255, 255, 0.3)"
      }}>
        <button 
          onClick={() => setShowDetailedStats(false)}
          style={{
            position: "absolute",
            top: "10px",
            right: "10px",
            background: "none",
            border: "none",
            fontSize: "18px",
            cursor: "pointer",
            zIndex: 501
          }}
        >
          ✕
        </button>
        <RouteStats optimizedRoutes={optimizedRoutes} />
      </div>
    </>
  );
};

export default StatsModal;