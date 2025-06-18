import React, { useEffect, useState, useRef } from "react";
import { DeckGL } from "deck.gl";
import { Map } from "react-map-gl/maplibre";
import { ScatterplotLayer, IconLayer, PathLayer } from "@deck.gl/layers";
import { PickingInfo } from "@deck.gl/core";
import OptimizationForm from "./components/OptimizationForm";
// Eliminar esta importación ya que solo se usará en el modal
// import RouteStats from "./components/RouteStats";
import StatusPanel from "./components/StatusPanel";
import StatsModal from "./components/StatsModal";
import WeatherInfoPanel from "./components/WeatherInfoPanel";
import WeatherOverlay from "./components/WeatherOverlay";
import RouteWeatherEffects from "./components/RouteWeatherEffects";
import FloatingControls from "./components/FloatingControls";
import { calculateRouteDistance } from "./utils/distance";
import { getRouteColor } from "./utils/colors";

// Mapa MapLibre
const MAP_STYLE = `https://api.maptiler.com/maps/streets/style.json?key=MZjUAQpw10B8E0nsKVQP`;

// Vista inicial: Almacenes San José, La Habana
const INITIAL_VIEW_STATE = {
  latitude: 23.1298784,
  longitude: -82.3490351,
  zoom: 15,
  bearing: 0,
  pitch: 0,
};

function App() {
  const [products, setProducts] = useState([]);
  const [trucks, setTrucks] = useState([]);
  const [vehicleData, setVehicleData] = useState({});
  const [trafficLights, setTrafficLights] = useState([]);
  const [connectionStatus, setConnectionStatus] = useState("Conectando...");
  const [errorMessage, setErrorMessage] = useState("");
  const [optimizedRoutes, setOptimizedRoutes] = useState([]);
  const [showOptimizationForm, setShowOptimizationForm] = useState(false);
  const [optimizationParams, setOptimizationParams] = useState({
    start_point: "",
    target_points: [],
    num_trucks: 0,
    truck_capacities: [],
    target_demands: {}
  });  const [selectedRouteId, setSelectedRouteId] = useState(null);
  const [showDetailedStats, setShowDetailedStats] = useState(false);
  const [weatherInfo, setWeatherInfo] = useState(null); // Nueva estado para información climática
  const [showWeatherPanel, setShowWeatherPanel] = useState(true); // Control de visibilidad del panel
  const [selectionMode, setSelectionMode] = useState("depot"); // "depot" o "targets"
  const [selectedDepot, setSelectedDepot] = useState(null);
  const [selectedTargets, setSelectedTargets] = useState([]);
  const [mapNodes, setMapNodes] = useState([]);
  
  const trailsRef = useRef({});
  const wsRef = useRef(null);

  // Función para manejar clics en el mapa - MOVER DENTRO DEL COMPONENTE
  const handleMapClick = (info) => {
    // Solo procesamos clics que efectivamente hayan seleccionado un nodo
    if (!info.object) return;
    
    // Extraemos el nodo seleccionado (necesitamos el ID y la posición)
    const nodeId = info.object.id;
    const position = [info.object.lon, info.object.lat];
    
    if (!nodeId) return;
    
    const selectedNode = {
      id: nodeId,
      position: position
    };
    
    if (selectionMode === "depot") {
      // Si estamos seleccionando el depósito, reemplazamos el actual
      setSelectedDepot(selectedNode);
      // Automáticamente cambiamos al modo de selección de objetivos
      setSelectionMode("targets");
    } else {
      // Si estamos seleccionando objetivos, verificamos que no esté ya seleccionado
      // y que no sea el depósito
      if (selectedDepot && selectedNode.id === selectedDepot.id) {
        return; // No permitimos seleccionar el depósito como objetivo
      }
      
      const alreadySelected = selectedTargets.some(target => target.id === selectedNode.id);
      if (!alreadySelected) {
        setSelectedTargets([...selectedTargets, selectedNode]);
      }
    }
  };

  // Función para limpiar selecciones - MOVER DENTRO DEL COMPONENTE
  const handleClearSelection = (type, index) => {
    if (!type || type === "all") {
      setSelectedDepot(null);
      setSelectedTargets([]);
    } else if (type === "depot") {
      setSelectedDepot(null);
    } else if (type === "target" && typeof index === 'number') {
      const newTargets = [...selectedTargets];
      newTargets.splice(index, 1);
      setSelectedTargets(newTargets);
    }
  };

  // 1) Cargamos pedidos de demo
  useEffect(() => {
    // Manejo mejorado de la conexión WebSocket
    const connectWebSocket = () => {
      try {
        console.log("Intentando conectar al WebSocket...");
        const ws = new WebSocket("ws://localhost:8765");
        wsRef.current = ws;

        ws.onopen = () => {
          console.log("Conexión WebSocket establecida");
          setConnectionStatus("Conectado");
          setErrorMessage("");
          
          // Solicitar los nodos del mapa
          ws.send(JSON.stringify({
            type: 'request_map_nodes'
          }));
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            // Si es una actualización de posiciones
            if (data.vehicles) {
              console.log(`Recibidos datos para ${data.vehicles.length} vehículos`);
              
              const updated = {};
              data.vehicles.forEach((v) => {
                const prevTrail = trailsRef.current[v.id] || [];
                const newTrail = [...prevTrail.slice(-20), [v.lon, v.lat]];
                trailsRef.current[v.id] = newTrail;

                updated[v.id] = {
                  id: v.id,
                  position: [v.lon, v.lat],
                  trail: newTrail,
                  color: 0,
                };
              });

              setVehicleData(updated);
              setTrafficLights(data.traffic_lights || []);            }
              // Si es un error de optimización
            if (data.type === 'optimization_error') {
              console.error("Error de optimización:", data.message);
              setErrorMessage(`Error: ${data.message}`);
              setConnectionStatus("Error en optimización");
            }
            
            // Si es un mensaje de progreso de optimización
            if (data.type === 'optimization_progress') {
              console.log("Progreso de optimización:", data.message);
              setConnectionStatus(`Optimizando: ${data.message}`);
            }
              
            // Si es una respuesta de optimización
            if (data.type === 'optimization_result') {
              console.log("Recibidos resultados de optimización:", data);
              setConnectionStatus("Conectado");  // Resetear estado de conexión
              
              // Guardar información climática si está disponible
              if (data.weather_info) {
                setWeatherInfo(data.weather_info);
                console.log("Información climática:", data.weather_info);
              }
              
              // Transformar las rutas al formato esperado por PathLayer
              // y calcular la distancia una sola vez
              const routes = data.routes.map((route, idx) => {
                const path = route.map(point => [point.lon, point.lat]);
                return {
                  id: `route-${idx}`,
                  path: path,
                  color: getRouteColor(idx),
                  distance: calculateRouteDistance(path), // Calculamos la distancia una sola vez
                  vehicleId: `Camión ${idx + 1}`
                };
              });
              
              setOptimizedRoutes(routes);
            }
            
            // Si hay un error de optimización
            if (data.type === 'optimization_error') {
              setErrorMessage(data.message);
            }
            
            // Si es una respuesta con los nodos del mapa
            if (data.type === 'map_nodes') {
              setMapNodes(data.nodes.map(node => ({
                id: node.id,
                position: [node.lon, node.lat],
                lon: node.lon,
                lat: node.lat
              })));
            }
            
          } catch (err) {
            console.error("Error procesando mensaje:", err);
            setErrorMessage(`Error procesando datos: ${err.message}`);
          }
        };

        ws.onclose = () => {
          console.log("Conexión WebSocket cerrada");
          setConnectionStatus("Desconectado");
          // Reintentar conexión después de 3 segundos
          setTimeout(connectWebSocket, 3000);
        };

        ws.onerror = (error) => {
          console.error("Error en WebSocket:", error);
          setConnectionStatus("Error");
          setErrorMessage("Error en la conexión WebSocket");
        };
      } catch (err) {
        console.error("Error creando WebSocket:", err);
        setConnectionStatus("Error");
        setErrorMessage(`Error de conexión: ${err.message}`);
        // Reintentar conexión después de 3 segundos
        setTimeout(connectWebSocket, 3000);
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Función para enviar solicitud de optimización
  const requestOptimization = (params) => {
    // Si params es null, solo limpiamos las rutas sin enviar petición
    if (params === null) {
      setOptimizedRoutes([]);
      return;
    }
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      // Limpiar rutas antiguas antes de solicitar nuevas
      setOptimizedRoutes([]);
      
      wsRef.current.send(JSON.stringify({
        type: 'optimization_request',
        ...params
      }));
    } else {
      setErrorMessage("No hay conexión con el servidor");
    }
  };
  

  // Función para manejar la selección de rutas
  const handleRouteSelect = (routeId) => {
    setSelectedRouteId(routeId === selectedRouteId ? null : routeId);
  };

  // Preparar rutas con propiedad de selección
  const routesWithSelection = optimizedRoutes.map(route => ({
    ...route,
    selected: route.id === selectedRouteId
  }));
  const layers = [
    // Capa para rutas optimizadas con efectos climáticos
    new PathLayer({
      id: 'optimized-routes',
      data: optimizedRoutes,
      pickable: true,
      widthScale: 1,
      widthMinPixels: 2,
      getPath: d => d.path,      getColor: d => {
        // Si la ruta está seleccionada, usar blanco
        if (d.id === selectedRouteId) {
          return [255, 255, 255, 255];
        }
        
        // Obtener el color base único para cada vehículo
        const routeIndex = parseInt(d.id.split('-')[1]) || 0;
        const baseColor = getRouteColor(routeIndex);
        
        // Aplicar modificaciones sutiles por clima MANTENIENDO la diferenciación por vehículo
        if (weatherInfo && weatherInfo.impact_factor > 1.6) {
          // Condiciones adversas: oscurecer levemente pero mantener diferencias
          return [
            Math.max(baseColor[0] * 0.8, 80),
            Math.max(baseColor[1] * 0.8, 80),
            Math.max(baseColor[2] * 0.8, 80),
            255
          ];
        } else if (weatherInfo && weatherInfo.impact_factor > 1.3) {
          // Condiciones moderadas: ajuste muy sutil 
          return [
            Math.min(255, baseColor[0] * 1.05),
            Math.min(255, baseColor[1] * 1.02),
            Math.min(255, baseColor[2] * 0.98),
            255
          ];
        }
        
        // Clima normal: usar color original con alpha completo
        return [...baseColor, 255];
      },
      getWidth: d => {
        // Ancho de línea basado en clima
        const baseWidth = d.id === selectedRouteId ? 8 : 5;
        if (weatherInfo && weatherInfo.impact_factor > 1.6) {
          return baseWidth + 2; // Líneas más gruesas para condiciones adversas
        }
        return baseWidth;
      },
      onHover: (info) => {
        // Actualiza el tooltip si se necesita
      },
      // Información que se mostrará al pasar el cursor
      getTooltip: (obj) => {
        if (obj.object) {
          return {
            html: `
              <div>
                <b>${obj.object.vehicleId}</b><br/>
                Distancia: ${obj.object.distance.toFixed(2)} km<br/>
                Puntos: ${obj.object.path.length}
              </div>
            `
          };
        }
        return null;
      }
    }),
    
    // Capa para nodos seleccionados
    new ScatterplotLayer({
      id: 'selected-nodes',
      data: [
        ...(selectedDepot ? [{...selectedDepot, type: 'depot'}] : []),
        ...selectedTargets.map(target => ({...target, type: 'target'}))
      ],
      pickable: true,
      stroked: true,
      filled: true,
      lineWidthUnits: 'pixels',
      lineWidthScale: 2,
      getPosition: d => d.position,
      getRadius: d => d.type === 'depot' ? 15 : 10,
      getFillColor: d => d.type === 'depot' ? [0, 255, 0, 200] : [0, 128, 255, 200],
      getLineColor: [255, 255, 255],
      getLineWidth: 2,
      onHover: (info) => {
        // Mostrar tooltip con información del nodo si se desea
      }
    }),

    // Capas existentes
    new IconLayer({
      id: "vehicle-icons",
      data: Object.values(vehicleData),
      getIcon: (d) => ({
        url: "/icons/car.png",
        width: 128,
        height: 128,
        anchorY: 128,
      }),
      getPosition: (d) => d.position,
      getSize: 2, // escala del ícono
      sizeScale: 10,
      getAngle: 0,
      getColor: 0,
      pickable: true,
    }),

    new ScatterplotLayer({
      id: "traffic-lights",
      data: trafficLights,
      getPosition: (d) => [d.lon, d.lat],
      getFillColor: (d) => d.state === "red" ? [255, 0, 0] : [0, 255, 0],
      getRadius: 10,
      radiusMinPixels: 2,
    }),

    // Modificar tu capa de semáforos o añadir una capa específica para nodos clickeables
    new ScatterplotLayer({
      id: "map-nodes",
      data: mapNodes,
      pickable: true,
      stroked: true,
      filled: true,
      opacity: 0.4,
      getPosition: d => d.position,
      getRadius: 5,
      getFillColor: [100, 100, 100],
      onClick: handleMapClick
    }),
  ];
  
  // Agregamos un panel para mostrar la información de las rutas
  return (
    <>
      {/* Panel de estado extraído como componente */}
      <StatusPanel 
        connectionStatus={connectionStatus}
        errorMessage={errorMessage}
        vehicleCount={Object.keys(vehicleData).length}
        showOptimizationForm={showOptimizationForm}
        setShowOptimizationForm={setShowOptimizationForm}
      />
      
      {/* Formulario de optimización */}
      {showOptimizationForm && 
        <OptimizationForm 
          onSubmit={requestOptimization}
          setOptimizedRoutes={setOptimizedRoutes}
          selectionMode={selectionMode}
          setSelectionMode={setSelectionMode}
          selectedDepot={selectedDepot}
          selectedTargets={selectedTargets}
          onClearSelection={handleClearSelection}
        />
      }
      
      {/* REMOVER: Panel de estadísticas de rutas - ahora solo en modal */}
      {/* {optimizedRoutes.length > 0 && (
        <RouteStats 
          optimizedRoutes={optimizedRoutes}
          onSelectRoute={handleRouteSelect}
          selectedRouteId={selectedRouteId}
        />
      )} */}
      
      {/* Panel de información climática */}
      <WeatherInfoPanel 
        weatherInfo={weatherInfo}
        isVisible={showWeatherPanel && weatherInfo !== null}
      />
      
      {/* Overlay climático compacto */}
      <WeatherOverlay 
        weatherInfo={weatherInfo}
        position="topRight"
      />
      
      {/* Efectos visuales de clima */}
      <RouteWeatherEffects 
        routes={optimizedRoutes}
        weatherInfo={weatherInfo}
      />
      
      {/* Controles flotantes unificados */}
      <FloatingControls 
        showDetailedStats={showDetailedStats}
        setShowDetailedStats={setShowDetailedStats}
        showWeatherPanel={showWeatherPanel}
        setShowWeatherPanel={setShowWeatherPanel}
        weatherInfo={weatherInfo}
        // Agregar prop para mostrar estadísticas solo cuando hay rutas
        hasRoutes={optimizedRoutes.length > 0}
      />
      
      {/* Modal de estadísticas - solo aquí se mostrarán las estadísticas de rutas */}
      <StatsModal 
        showDetailedStats={showDetailedStats}
        setShowDetailedStats={setShowDetailedStats}
        optimizedRoutes={optimizedRoutes}
        selectedRouteId={selectedRouteId}
        onSelectRoute={handleRouteSelect}
      />
      
      {/* Mapa principal */}
      <DeckGL
        initialViewState={INITIAL_VIEW_STATE}
        controller
        layers={layers}
      >
        <Map reuseMaps mapLib={import("maplibre-gl")} mapStyle={MAP_STYLE} />
      </DeckGL>
    </>
  );
}

export default App;

