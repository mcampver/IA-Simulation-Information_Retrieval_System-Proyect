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
  const [showAIPanel, setShowAIPanel] = useState(false);
  const [aiDescription, setAiDescription] = useState("");
  const [aiResponse, setAiResponse] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [aiParams, setAiParams] = useState(null);
  const [aiError, setAiError] = useState("");
  
  const handleOptimize = () => {
    // Validación antes de enviar
    if (!selectedDepot || selectedTargets.length === 0) {
      alert("Por favor, seleccione un punto de inicio y al menos un nodo objetivo en el mapa.");
      return;
    }

    // Usar parámetros de la IA si están disponibles, sino usar valores por defecto
    const optimizationData = {
      start_point: selectedDepot.id,
      target_points: selectedTargets.map(target => target.id),
      num_trucks: aiParams ? aiParams.num_trucks : parseInt(localNumTrucks, 10),
      truck_capacities: aiParams ? aiParams.truck_capacities : [],
      target_demands: aiParams ? aiParams.target_demands : {}
    };
    
    onSubmit(optimizationData);
  };
  
  const handleClear = () => {
    // Limpiar rutas y selecciones
    setOptimizedRoutes([]);
    onClearSelection();
    setAiParams(null);
    setAiResponse("");
    setAiDescription("");
    setAiError("");
  };

  const handleAIAnalysis = async () => {
    if (!selectedDepot || selectedTargets.length === 0) {
      alert("Por favor, seleccione primero el depósito y los puntos objetivo en el mapa.");
      return;
    }

    if (!aiDescription.trim()) {
      alert("Por favor, describe los requerimientos de tu problema de ruteo.");
      return;
    }

    setIsAnalyzing(true);
    setAiResponse("");
    setAiError("");
    setAiParams(null);

    try {
      console.log("Enviando solicitud a la IA...");
      
      // Cambiar la URL del fetch para usar el puerto correcto
      const response = await fetch('http://localhost:8767/analyze_cvrp', {  // Puerto 8766, no 8765
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          depot_info: selectedDepot,
          targets_info: selectedTargets,
          user_description: aiDescription
        })
      });

      console.log("Respuesta recibida:", response.status);

      if (!response.ok) {
        throw new Error(`Error del servidor: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      console.log("Resultado del análisis:", result);

      if (result.success) {
        setAiParams(result.params);
        setAiResponse(result.message);
        setLocalNumTrucks(result.params.num_trucks);
        setAiError("");
      } else {
        setAiError(result.message || "Error en el análisis");
        setAiParams(null);
        setAiResponse("");
      }

    } catch (error) {
      console.error('Error en análisis de IA:', error);
      setAiError(`Error de conexión: ${error.message}`);
      setAiParams(null);
      setAiResponse("");
    } finally {
      setIsAnalyzing(false);
    }
  };
  
  return (
    <div style={{
      position: "absolute",
      top: "10px",
      right: "10px",
      zIndex: 100,
      padding: "15px",
      backgroundColor: "rgba(255,255,255,0.95)",
      borderRadius: "8px",
      boxShadow: "0 2px 6px rgba(0,0,0,0.3)",
      maxWidth: showAIPanel ? "550px" : "350px",
      maxHeight: "85vh",
      overflowY: "auto"
    }}>
      <h3 style={{ marginTop: 0 }}>Optimización de Rutas</h3>
      
      {/* Sección de selección de nodos */}
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
      
      {/* Nodos seleccionados */}
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
            maxHeight: "120px", 
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

      {/* Panel de Asistente IA */}
      <div style={{ marginBottom: "15px" }}>
        <button 
          onClick={() => setShowAIPanel(!showAIPanel)}
          style={{
            width: "100%",
            padding: "10px",
            backgroundColor: "#9C27B0",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
            fontWeight: "bold",
            marginBottom: "10px"
          }}
        >
          🤖 {showAIPanel ? "Ocultar" : "Mostrar"} Asistente IA
        </button>

        {showAIPanel && (
          <div style={{ 
            border: "2px solid #9C27B0", 
            borderRadius: "8px", 
            padding: "15px", 
            backgroundColor: "#fafafa" 
          }}>
            <h4 style={{ margin: "0 0 10px 0", color: "#9C27B0" }}>Asistente IA para CVRP</h4>
            
            <div style={{ marginBottom: "15px" }}>
              <label style={{ display: "block", marginBottom: "5px", fontWeight: "bold" }}>
                Describe tu problema de ruteo:
              </label>
              <textarea
                value={aiDescription}
                onChange={(e) => setAiDescription(e.target.value)}
                placeholder="Ej: Necesito repartir productos alimenticios a 5 tiendas. Cada tienda necesita entre 15-25 cajas. Tengo 2 camiones con capacidad de 100 cajas cada uno..."
                style={{
                  width: "100%",
                  height: "80px",
                  padding: "8px",
                  borderRadius: "4px",
                  border: "1px solid #ccc",
                  resize: "vertical",
                  fontSize: "0.9rem"
                }}
              />
            </div>

            <button
              onClick={handleAIAnalysis}
              disabled={isAnalyzing || !selectedDepot || selectedTargets.length === 0}
              style={{
                width: "100%",
                padding: "10px",
                backgroundColor: isAnalyzing ? "#ccc" : "#9C27B0",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: isAnalyzing ? "not-allowed" : "pointer",
                marginBottom: "15px"
              }}
            >
              {isAnalyzing ? "🔄 Analizando..." : "🚀 Analizar con IA"}
            </button>

            {/* Panel de estado de análisis */}
            {isAnalyzing && (
              <div style={{
                backgroundColor: "#e3f2fd",
                border: "1px solid #2196F3",
                borderRadius: "4px",
                padding: "10px",
                marginBottom: "10px",
                textAlign: "center"
              }}>
                <div>🤖 La IA está analizando tu descripción...</div>
                <div style={{ fontSize: "0.8rem", color: "#666", marginTop: "5px" }}>
                  Esto puede tomar unos segundos
                </div>
              </div>
            )}

            {/* Panel de respuesta exitosa */}
            {aiResponse && !aiError && (
              <div style={{
                backgroundColor: "#e8f5e9",
                border: "1px solid #4CAF50",
                borderRadius: "4px",
                padding: "10px",
                marginBottom: "10px"
              }}>
                <h5 style={{ margin: "0 0 10px 0", color: "#2E7D32" }}>✅ Análisis Completado</h5>
                <div style={{
                  maxHeight: "200px",
                  overflowY: "auto",
                  whiteSpace: "pre-line",
                  fontSize: "0.9rem",
                  lineHeight: "1.4"
                }}>
                  {aiResponse}
                </div>
              </div>
            )}

            {/* Panel de error */}
            {aiError && (
              <div style={{
                backgroundColor: "#ffebee",
                border: "1px solid #f44336",
                borderRadius: "4px",
                padding: "10px",
                marginBottom: "10px"
              }}>
                <h5 style={{ margin: "0 0 10px 0", color: "#c62828" }}>❌ Error en el Análisis</h5>
                <div style={{
                  fontSize: "0.9rem",
                  color: "#c62828"
                }}>
                  {aiError}
                </div>
                <div style={{
                  fontSize: "0.8rem",
                  color: "#666",
                  marginTop: "5px"
                }}>
                  Intenta reformular tu descripción o verifica la conexión con el servidor.
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* Campo manual de número de camiones (solo visible si no hay parámetros de IA) */}
      {!aiParams && (
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
      )}

      {/* Mostrar resumen de parámetros de IA si están disponibles */}
      {aiParams && (
        <div style={{ 
          marginBottom: "15px", 
          padding: "10px", 
          backgroundColor: "#e8f5e9", 
          borderRadius: "4px",
          border: "1px solid #4CAF50"
        }}>
          <h4 style={{ margin: "0 0 5px 0", color: "#2E7D32", fontSize: "0.9rem" }}>✅ Parámetros configurados por IA:</h4>
          <div style={{ fontSize: "0.8rem", color: "#2E7D32" }}>
            <div>🚛 Camiones: {aiParams.num_trucks}</div>
            <div>📦 Capacidades: [{aiParams.truck_capacities.join(", ")}]</div>
            <div>📍 Demandas: [{aiParams.target_demands.join(", ")}]</div>
          </div>
        </div>
      )}
      
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