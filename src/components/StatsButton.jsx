import React from 'react';

const StatsButton = ({ showDetailedStats, setShowDetailedStats }) => {
  return (
    <div style={{
      position: "absolute",
      bottom: "20px",
      left: "20px",
      zIndex: 100
    }}>
      <button 
        onClick={() => setShowDetailedStats(!showDetailedStats)}
        style={{
          padding: "8px 12px",
          backgroundColor: "#4285F4",
          color: "white",
          border: "none",
          borderRadius: "4px",
          cursor: "pointer",
          boxShadow: "0 2px 4px rgba(0,0,0,0.2)",
          transition: "background-color 0.3s"
        }}
        onMouseOver={(e) => e.currentTarget.style.backgroundColor = "#3367D6"}
        onMouseOut={(e) => e.currentTarget.style.backgroundColor = "#4285F4"}
      >
        {showDetailedStats ? "Ocultar estadísticas" : "Ver estadísticas detalladas"}
      </button>
    </div>
  );
};

export default StatsButton;