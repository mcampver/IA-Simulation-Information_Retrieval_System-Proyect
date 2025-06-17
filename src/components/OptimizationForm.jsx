import React, { useState, memo } from "react";

const OptimizationForm = memo(({ onSubmit, setOptimizedRoutes }) => {
  const [localStartPoint, setLocalStartPoint] = useState("");
  const [localTargetPoints, setLocalTargetPoints] = useState("");
  const [localNumTrucks, setLocalNumTrucks] = useState(3);
  
  const handleOptimize = () => {
    // Validación local antes de enviar
    if (
      localStartPoint.trim() === "" ||
      localTargetPoints.split(",").map(p => p.trim()).filter(p => p).length === 0
    ) {
      alert("Por favor, escriba un punto de inicio y al menos un nodo objetivo.");
      return;
    }

    const optimizationData = {
      start_point: localStartPoint.trim(),
      target_points: localTargetPoints
        .split(",")
        .map((p) => p.trim())
        .filter((p) => p),
      num_trucks: parseInt(localNumTrucks, 10),
      truck_capacities: [10, 10, 10],
      target_demands: {}
    };
    
    onSubmit(optimizationData);
  };
  
  const handleClear = () => {
    // Solo limpiamos las rutas en el mapa, sin tocar los valores del formulario
    setOptimizedRoutes([]);
  };
  
  return (
    <div style={{
      position: "absolute",
      top: "10px",
      right: "10px",
      zIndex: 100,
      padding: "15px",
      backgroundColor: "rgba(255,255,255,0.8)",
      borderRadius: "4px",
      maxWidth: "100%"
    }}>
      <h3>Configuración de Optimización</h3>
      
      <div style={{ marginBottom: "10px" }}>
        <label>
          Punto de inicio:
          <input 
            type="text" 
            value={localStartPoint} 
            onChange={e => setLocalStartPoint(e.target.value)}
            style={{ width: "100%", padding: "5px", marginTop: "5px" }}
          />
        </label>
      </div>
      
      <div style={{ marginBottom: "10px" }}>
        <label>
          Puntos objetivo (separados por coma):
          <input 
            type="text" 
            value={localTargetPoints} 
            onChange={e => setLocalTargetPoints(e.target.value)}
            style={{ width: "100%", padding: "5px", marginTop: "5px" }}
          />
        </label>
      </div>
      
      <div style={{ marginBottom: "15px" }}>
        <label>
          Número de camiones:
          <input 
            type="number" 
            value={localNumTrucks} 
            onChange={e => setLocalNumTrucks(e.target.value)}
            min="1"
            style={{ width: "100%", padding: "5px", marginTop: "5px" }}
          />
        </label>
      </div>
      
      <div style={{ display: "flex", gap: "10px" }}>
        <button 
          onClick={handleOptimize}
          style={{
            flex: 1,
            padding: "8px",
            backgroundColor: "#2196F3",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer"
          }}
        >
          Optimizar Rutas
        </button>
        
        <button 
          onClick={handleClear}
          style={{
            flex: 1,
            padding: "8px",
            backgroundColor: "#f44336",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer"
          }}
        >
          Limpiar Rutas
        </button>
      </div>
    </div>
  );
});

export default OptimizationForm;