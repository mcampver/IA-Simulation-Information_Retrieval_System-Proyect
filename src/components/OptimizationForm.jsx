import React, { useState } from 'react';
import { basePanel, getZonePosition, Z_LAYERS } from './LayoutManager';

const OptimizationForm = ({ 
  onSubmit, 
  setOptimizedRoutes, 
  selectionMode, 
  setSelectionMode, 
  selectedDepot, 
  selectedTargets, 
  onClearSelection 
}) => {
  const [description, setDescription] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [showManualConfig, setShowManualConfig] = useState(false);
  const [selectedSolver, setSelectedSolver] = useState('vns_solver'); // Nuevo estado para el solver
  
  // Estados para configuración manual (fallback)
  const [numTrucks, setNumTrucks] = useState(2);
  const [capacities, setCapacities] = useState([100, 100]);
  const [demands, setDemands] = useState({});

  const panelStyles = {
    ...basePanel,
    ...getZonePosition('centerRight'), // Cambiado a la derecha
    zIndex: Z_LAYERS.panels,
    width: '380px', // Aumentado para más espacio
    maxHeight: '75vh',
    overflowY: 'auto'
  };

  const headerStyles = {
    background: 'linear-gradient(135deg, #dc2626, #ef4444)',
    color: 'white',
    padding: '12px 15px',
    borderRadius: '12px 12px 0 0',
    position: 'sticky',
    top: 0,
    zIndex: 1
  };

  const sectionStyles = {
    marginBottom: '20px',
    padding: '12px',
    backgroundColor: '#f9fafb',
    borderRadius: '8px',
    border: '1px solid #f3f4f6'
  };

  const sectionTitleStyles = {
    fontSize: '14px',
    fontWeight: '600',
    color: '#374151',
    marginBottom: '8px',
    display: 'flex',
    alignItems: 'center',
    gap: '6px'
  };

  const buttonStyles = {
    padding: '8px 12px',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: '500',
    transition: 'all 0.3s ease',
    margin: '2px'
  };

  const primaryButtonStyles = {
    ...buttonStyles,
    backgroundColor: '#3b82f6',
    color: 'white'
  };

  const secondaryButtonStyles = {
    ...buttonStyles,
    backgroundColor: '#f3f4f6',
    color: '#374151',
    border: '1px solid #d1d5db'
  };

  const inputStyles = {
    width: '100%',
    padding: '8px 12px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '14px',
    marginBottom: '8px'
  };

  const textareaStyles = {
    ...inputStyles,
    minHeight: '80px',
    resize: 'vertical',
    fontFamily: 'inherit'
  };

  // Función para analizar con IA
  const analyzeWithAI = async () => {
    if (!selectedDepot || selectedTargets.length === 0) {
      alert('Debe seleccionar un depósito y al menos un objetivo antes de analizar');
      return;
    }

    if (!description.trim()) {
      alert('Describe los requerimientos para tu problema de ruteo');
      return;
    }

    setIsAnalyzing(true);
    
    try {
      // Cambiar la URL para apuntar al servidor HTTP correcto
      const response = await fetch('http://localhost:8767/analyze_cvrp', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          depot_info: selectedDepot,
          targets_info: selectedTargets,
          user_description: description,
          solver: selectedSolver  // Incluir el solver seleccionado
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      
      if (result.success) {
        setAnalysisResult(result);
        // Auto-llenar los parámetros analizados
        setNumTrucks(result.params.num_trucks);
        setCapacities(result.params.truck_capacities);
        
        // Convertir demandas de array a objeto indexado por ID
        const demandsObj = {};
        selectedTargets.forEach((target, index) => {
          demandsObj[target.id] = result.params.target_demands[index] || 1;
        });
        setDemands(demandsObj);
        
      } else {
        alert(`Error en el análisis: ${result.message}`);
        setShowManualConfig(true); // Mostrar configuración manual como fallback
      }
    } catch (error) {
      console.error('Error al analizar con IA:', error);
      alert(`Error conectando con el servidor: ${error.message}`);
      setShowManualConfig(true);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleSubmit = () => {
    if (!selectedDepot || selectedTargets.length === 0) {
      alert('Debe seleccionar un depósito y al menos un objetivo');
      return;
    }

    // Preparar demandas como array en el orden correcto
    const target_demands = selectedTargets.map(target => demands[target.id] || 1);

    onSubmit({
      start_point: selectedDepot.id,
      target_points: selectedTargets.map(t => t.id),
      num_trucks: numTrucks,
      truck_capacities: capacities,
      target_demands: target_demands,
      solver: selectedSolver // Añadir el solver seleccionado
    });
  };

  // ...existing styles...

  return (
    <div style={panelStyles}>
      <div style={headerStyles}>
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>
          🤖 Optimización Inteligente
        </h3>
      </div>
      
      <div style={{ padding: '15px' }}>
        {/* Sección de Selección */}
        <div style={sectionStyles}>
          <div style={sectionTitleStyles}>
            <span>📍</span>
            Selección de Puntos
          </div>
          
          <div style={{ marginBottom: '12px' }}>
            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '6px' }}>
              Modo actual: {selectionMode === 'depot' ? '🏭 Depósito' : '🎯 Objetivos'}
            </div>
            
            <div style={{ display: 'flex', gap: '4px' }}>
              <button 
                style={{
                  ...buttonStyles,
                  backgroundColor: selectionMode === 'depot' ? '#3b82f6' : '#f3f4f6',
                  color: selectionMode === 'depot' ? 'white' : '#374151'
                }}
                onClick={() => setSelectionMode('depot')}
              >
                🏭 Depósito
              </button>
              <button 
                style={{
                  ...buttonStyles,
                  backgroundColor: selectionMode === 'targets' ? '#3b82f6' : '#f3f4f6',
                  color: selectionMode === 'targets' ? 'white' : '#374151'
                }}
                onClick={() => setSelectionMode('targets')}
              >
                🎯 Objetivos
              </button>
            </div>
          </div>
          
          {/* Estado de selección */}
          <div style={{ fontSize: '12px' }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '6px',
              marginBottom: '4px',
              color: selectedDepot ? '#059669' : '#9ca3af'
            }}>
              <span>{selectedDepot ? '✅' : '⭕'}</span>
              Depósito: {selectedDepot ? `Nodo ${selectedDepot.id}` : 'No seleccionado'}
            </div>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '6px',
              color: selectedTargets.length > 0 ? '#059669' : '#9ca3af'
            }}>
              <span>{selectedTargets.length > 0 ? '✅' : '⭕'}</span>
              Objetivos: {selectedTargets.length} seleccionados
            </div>
          </div>
          
          <button 
            style={{
              ...secondaryButtonStyles,
              width: '100%',
              marginTop: '8px'
            }}
            onClick={() => onClearSelection('all')}
          >
            🗑️ Limpiar Selección
          </button>
        </div>

        {/* Sección de Análisis IA */}
        <div style={sectionStyles}>
          <div style={sectionTitleStyles}>
            <span>🤖</span>
            Análisis Inteligente
          </div>
          
          <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '6px' }}>
            Describe tu problema de ruteo:
          </label>
          <textarea 
            style={textareaStyles}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Ej: Necesito repartir productos alimenticios a 3 tiendas. Cada tienda necesita entre 10-20 cajas. Tengo 2 camiones con capacidad de 50 cajas cada uno."
          />
          
          <button 
            style={{
              ...primaryButtonStyles,
              width: '100%',
              padding: '10px',
              backgroundColor: isAnalyzing ? '#9ca3af' : '#10b981',
              fontSize: '13px'
            }}
            onClick={analyzeWithAI}
            disabled={isAnalyzing || !selectedDepot || selectedTargets.length === 0}
          >
            {isAnalyzing ? '🔄 Analizando...' : '🧠 Analizar con IA'}
          </button>
          
          <button 
            style={{
              ...secondaryButtonStyles,
              width: '100%',
              marginTop: '6px',
              fontSize: '12px'
            }}
            onClick={() => setShowManualConfig(!showManualConfig)}
          >
            ⚙️ {showManualConfig ? 'Ocultar' : 'Mostrar'} Configuración Manual
          </button>
        </div>

        {/* Resultado del Análisis */}
        {analysisResult && (
          <div style={{
            ...sectionStyles,
            backgroundColor: '#f0fdf4',
            border: '1px solid #bbf7d0'
          }}>
            <div style={sectionTitleStyles}>
              <span>✅</span>
              Análisis Completado
            </div>
            
            <div style={{ fontSize: '12px', color: '#166534', lineHeight: 1.4 }}>
              <div><strong>Camiones:</strong> {analysisResult.params.num_trucks}</div>
              <div><strong>Capacidades:</strong> {analysisResult.params.truck_capacities.join(', ')}</div>
              <div><strong>Demandas:</strong> {analysisResult.params.target_demands.join(', ')}</div>
              
              {analysisResult.analysis.observations && (
                <div style={{ marginTop: '8px', fontStyle: 'italic' }}>
                  <strong>Observaciones:</strong> {analysisResult.analysis.observations}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Configuración Manual (cuando se solicita o falla la IA) */}
        {showManualConfig && (
          <div style={sectionStyles}>
            <div style={sectionTitleStyles}>
              <span>⚙️</span>
              Configuración Manual
            </div>
            
            <label style={{ fontSize: '12px', color: '#6b7280' }}>
              Número de camiones:
            </label>
            <input 
              type="number" 
              value={numTrucks}
              onChange={(e) => {
                const num = parseInt(e.target.value) || 1;
                setNumTrucks(num);
                setCapacities(Array(num).fill(100));
              }}
              min="1"
              max="999999999"
              style={inputStyles}
            />
            
            {Array.from({length: numTrucks}, (_, i) => (
              <div key={i} style={{ marginBottom: '8px' }}>
                <label style={{ fontSize: '12px', color: '#6b7280' }}>
                  Capacidad Camión {i + 1}:
                </label>
                <input 
                  type="number" 
                  value={capacities[i] || 100}
                  onChange={(e) => {
                    const newCapacities = [...capacities];
                    newCapacities[i] = parseInt(e.target.value) || 100;
                    setCapacities(newCapacities);
                  }}
                  style={inputStyles}
                />
              </div>
            ))}
            
            {/* Demandas por objetivo */}
            {selectedTargets.length > 0 && (
              <>
                <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginTop: '12px', marginBottom: '6px' }}>
                  Demandas por objetivo:
                </label>
                {selectedTargets.map((target, index) => (
                  <div key={target.id} style={{ marginBottom: '6px' }}>
                    <label style={{ fontSize: '11px', color: '#6b7280' }}>
                      Nodo {target.id}:
                    </label>
                    <input 
                      type="number" 
                      value={demands[target.id] || 1}
                      onChange={(e) => {
                        setDemands({
                          ...demands,
                          [target.id]: parseInt(e.target.value) || 1
                        });
                      }}
                      min="1"
                      style={{...inputStyles, marginBottom: '4px'}}
                    />
                  </div>
                ))}
              </>
            )}
          </div>
        )}

        {/* Nueva Sección de Solver */}
        <div style={sectionStyles}>
          <div style={sectionTitleStyles}>
            <span>⚙️</span>
            Algoritmo de Optimización
          </div>
          
          <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '6px' }}>
            Metaheurística:
          </label>
          <select 
            style={{
              ...inputStyles,
              marginBottom: '8px'
            }}
            value={selectedSolver}
            onChange={(e) => setSelectedSolver(e.target.value)}
          >
            <option value="vns_solver">VNS - Variable Neighborhood Search</option>
            <option value="ts_solver">Tabu Search</option>
            <option value="sa_solver">Simulated Annealing</option>
            <option value="ag_solver">Algoritmo Genético</option>
          </select>
          
          {/* Descripción del algoritmo seleccionado */}
          <div style={{
            fontSize: '11px',
            color: '#6b7280',
            backgroundColor: '#f9fafb',
            padding: '8px',
            borderRadius: '6px',
            marginBottom: '8px'
          }}>
            {getSolverDescription(selectedSolver)}
          </div>
        </div>

        {/* Botones de Acción */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            style={{
              ...primaryButtonStyles,
              flex: 1,
              padding: '12px'
            }}
            onClick={handleSubmit}
          >
            🚀 Optimizar
          </button>
          <button 
            style={{
              ...secondaryButtonStyles,
              flex: 1,
              padding: '12px'
            }}
            onClick={() => onSubmit(null)}
          >
            🗑️ Limpiar
          </button>
        </div>
        
        <div style={{
          fontSize: '11px',
          color: '#9ca3af',
          textAlign: 'center',
          marginTop: '12px',
          lineHeight: 1.4
        }}>
          💡 Describe tu problema y la IA configurará automáticamente los parámetros
        </div>
      </div>
    </div>
  );
};

// Función para obtener la descripción del solver
const getSolverDescription = (solver) => {
  const descriptions = {
    'vns_solver': '🔍 Búsqueda en Vecindario Variable: Explora diferentes estructuras de vecindario sistemáticamente. Bueno para problemas medianos con soluciones de calidad.',
    'ts_solver': '🚫 Búsqueda Tabú: Usa memoria para evitar ciclos y explorar nuevas regiones. Excelente para escape de óptimos locales.',
    'sa_solver': '🌡️ Recocido Simulado: Acepta soluciones peores ocasionalmente para explorar el espacio. Robusto para problemas complejos.',
    'ag_solver': '🧬 Algoritmo Genético: Evoluciona poblaciones de soluciones mediante selección y cruce. Bueno para exploración global.'
  };
  return descriptions[solver] || 'Algoritmo de optimización seleccionado';
};

export default OptimizationForm;