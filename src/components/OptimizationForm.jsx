import React, { useState, memo } from "react";

const OptimizationForm = memo(({ 
  onSubmit, 
  setOptimizedRoutes, 
  selectionMode, 
  setSelectionMode, 
  selectedDepot, 
  selectedTargets,
  onClearSelection
}) => {
  const [localNumTrucks, setLocalNumTrucks] = useState(3);
  
  const handleOptimize = () => {
    // Validación antes de enviar
    if (!selectedDepot || selectedTargets.length === 0) {
      alert("Por favor, seleccione un punto de inicio y al menos un nodo objetivo en el mapa.");
      return;
    }

    const optimizationData = {
      start_point: selectedDepot.id,
      target_points: selectedTargets.map(target => target.id),
      num_trucks: parseInt(localNumTrucks, 10),
      truck_capacities: [],
      target_demands: {}
    };
    
    onSubmit(optimizationData);
  };
  
  const handleClear = () => {
    // Limpiar rutas y selecciones
    setOptimizedRoutes([]);
    onClearSelection();
  };
  
  return (
    <div style={{
      position: "absolute",
      top: "10px",
      right: "10px",
      zIndex: 100,
      padding: "15px",
      backgroundColor: "rgba(255,255,255,0.9)",
      borderRadius: "8px",
      boxShadow: "0 2px 6px rgba(0,0,0,0.3)",
      maxWidth: "350px"
    }}>
      <h3 style={{ marginTop: 0 }}>Optimización de Rutas</h3>
      
      <div style={{ marginBottom: "15px" }}>
        <div style={{ display: "flex", gap: "10px", marginBottom: "10px" }}>
          <button 
            onClick={() => setSelectionMode("depot")}
            style={{
              flex: 1,
              padding: "8px",
              backgroundColor: selectionMode === "depot" ? "#4CAF50" : "#e0e0e0",
              color: selectionMode === "depot" ? "white" : "black",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
              fontWeight: selectionMode === "depot" ? "bold" : "normal"
            }}
          >
            Seleccionar Depósito
          </button>
          
          <button 
            onClick={() => setSelectionMode("targets")}
            style={{
              flex: 1,
              padding: "8px",
              backgroundColor: selectionMode === "targets" ? "#2196F3" : "#e0e0e0",
              color: selectionMode === "targets" ? "white" : "black",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
              fontWeight: selectionMode === "targets" ? "bold" : "normal"
            }}
          >
            Seleccionar Objetivos
          </button>
        </div>
        
        <p style={{ fontSize: "0.9rem", margin: "5px 0", color: "#666" }}>
          {selectionMode === "depot" 
            ? "Haga clic en el mapa para seleccionar el depósito" 
            : "Haga clic en el mapa para añadir nodos objetivo"}
        </p>
      </div>
      
      <div style={{ marginBottom: "15px" }}>
        <h4 style={{ margin: "0 0 5px 0", fontSize: "1rem" }}>Nodos Seleccionados:</h4>
        
        {selectedDepot && (
          <div style={{ 
            padding: "5px", 
            backgroundColor: "#e8f5e9", 
            borderRadius: "4px", 
            marginBottom: "5px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center" 
          }}>
            <span>Depósito: {selectedDepot.id}</span>
            <button 
              onClick={() => onClearSelection("depot")} 
              style={{ border: "none", background: "none", cursor: "pointer", color: "#f44336" }}
            >
              ✕
            </button>
          </div>
        )}
        
        {selectedTargets.length > 0 && (
          <div style={{ 
            maxHeight: "150px", 
            overflowY: "auto", 
            border: "1px solid #e0e0e0", 
            borderRadius: "4px",
            marginBottom: "5px"
          }}>
            {selectedTargets.map((target, index) => (
              <div key={index} style={{ 
                padding: "5px", 
                borderBottom: index < selectedTargets.length - 1 ? "1px solid #e0e0e0" : "none",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center"
              }}>
                <span>Objetivo {index + 1}: {target.id}</span>
                <button 
                  onClick={() => onClearSelection("target", index)} 
                  style={{ border: "none", background: "none", cursor: "pointer", color: "#f44336" }}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
      
      <div style={{ marginBottom: "15px" }}>
        <label>
          Número de camiones:
          <input 
            type="number" 
            value={localNumTrucks} 
            onChange={e => setLocalNumTrucks(e.target.value)}
            min="1"
            style={{ width: "100%", padding: "8px", marginTop: "5px", borderRadius: "4px", border: "1px solid #ccc" }}
          />
        </label>
      </div>
      
      <div style={{ display: "flex", gap: "10px" }}>
        <button 
          onClick={handleOptimize}
          style={{
            flex: 1,
            padding: "10px",
            backgroundColor: "#2196F3",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
            fontWeight: "bold"
          }}
        >
          Optimizar Rutas
        </button>
        
        <button 
          onClick={handleClear}
          style={{
            flex: 1,
            padding: "10px",
            backgroundColor: "#f44336",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer"
          }}
        >
          Limpiar Todo
        </button>
      </div>
    </div>
  );
});

export default OptimizationForm;