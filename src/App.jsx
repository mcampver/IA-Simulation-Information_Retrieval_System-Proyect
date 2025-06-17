// src/App.jsx
import React, { useEffect, useState, useRef } from "react";
import { DeckGL } from "deck.gl";
import { Map } from "react-map-gl/maplibre";
import { ScatterplotLayer, IconLayer, PathLayer } from "@deck.gl/layers";
import { PickingInfo } from "@deck.gl/core";
import OptimizationForm from "./components/OptimizationForm";
import RouteInfo from "./components/RouteInfo";
import StatusPanel from "./components/StatusPanel";
import StatsButton from "./components/StatsButton";
import StatsModal from "./components/StatsModal";
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
  });
  const [selectedRouteId, setSelectedRouteId] = useState(null);
  const [showDetailedStats, setShowDetailedStats] = useState(false);
  const [selectionMode, setSelectionMode] = useState("depot"); // "depot" o "targets"
  const [selectedDepot, setSelectedDepot] = useState(null);
  const [selectedTargets, setSelectedTargets] = useState([]);
  const [mapNodes, setMapNodes] = useState([]);
  
  const trailsRef = useRef({});
  const wsRef = useRef(null);

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
              setTrafficLights(data.traffic_lights || []);
            }
            
            // Si es una respuesta de optimización
            if (data.type === 'optimization_result') {
              console.log("Recibidos resultados de optimización:", data);
              
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
    // Capa para rutas optimizadas
    new PathLayer({
      id: 'optimized-routes',
      data: optimizedRoutes,
      pickable: true,
      widthScale: 1,
      widthMinPixels: 2,
      getPath: d => d.path,
      getColor: d => d.id === selectedRouteId ? [255, 255, 255] : d.color,
      getWidth: d => d.id === selectedRouteId ? 8 : 5,
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
      
      {/* Panel mejorado para mostrar información de rutas */}
      {optimizedRoutes.length > 0 && (
        <>
          <RouteInfo 
            routes={routesWithSelection} 
            onSelectRoute={handleRouteSelect} 
          />
          
          {/* Botón para mostrar/ocultar estadísticas detalladas */}
          <StatsButton 
            showDetailedStats={showDetailedStats}
            setShowDetailedStats={setShowDetailedStats}
          />
          
          {/* Panel de estadísticas detalladas */}
          <StatsModal 
            showDetailedStats={showDetailedStats}
            setShowDetailedStats={setShowDetailedStats}
            optimizedRoutes={optimizedRoutes}
          />
        </>
      )}
      
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

// Función para manejar clics en el mapa
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

// Función para limpiar selecciones
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

export default App;

