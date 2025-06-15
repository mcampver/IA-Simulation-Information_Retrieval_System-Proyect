import React, { useEffect, useState, useRef } from "react";
import { DeckGL } from "deck.gl";
import { Map } from "react-map-gl/maplibre";
import { IconLayer, ScatterplotLayer, PathLayer } from "@deck.gl/layers";
import OptimizationForm from "./components/OptimizationForm";
import RouteInfo from "./components/RouteInfo";
import StatusPanel from "./components/StatusPanel";
import StatsButton from "./components/StatsButton";
import StatsModal from "./components/StatsModal";
import WeatherInfoPanel from "./components/WeatherInfoPanel";
import WeatherOverlay from "./components/WeatherOverlay";
import RouteWeatherEffects from "./components/RouteWeatherEffects";
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
    num_trucks: 3,
    truck_capacities: [10, 10, 10],
    target_demands: {}
  });  const [selectedRouteId, setSelectedRouteId] = useState(null);
  const [showDetailedStats, setShowDetailedStats] = useState(false);
  const [weatherInfo, setWeatherInfo] = useState(null); // Nueva estado para información climática
  const [showWeatherPanel, setShowWeatherPanel] = useState(true); // Control de visibilidad del panel
  
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
      getPath: d => d.path,
      getColor: d => {
        // Aplicar efectos de color basados en clima
        if (weatherInfo && weatherInfo.impact_factor > 1.6) {
          // Rutas más rojas/naranjas para condiciones adversas
          return d.id === selectedRouteId ? [255, 255, 255] : [255, 100, 100];
        } else if (weatherInfo && weatherInfo.impact_factor > 1.3) {
          // Rutas amarillas para condiciones moderadas
          return d.id === selectedRouteId ? [255, 255, 255] : [255, 180, 0];
        }
        // Color normal
        return d.id === selectedRouteId ? [255, 255, 255] : d.color;
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
          initialValues={{
            start_point: "",
            target_points: [],
            num_trucks: 3,
            truck_capacities: [10, 10, 10],
            target_demands: {},
            ...(optimizationParams || {})
          }} 
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
            {/* Panel de información climática */}
          <WeatherInfoPanel 
            weatherInfo={weatherInfo}
            isVisible={showWeatherPanel && weatherInfo !== null}
          />
        </>
      )}
      
      {/* Overlay climático compacto en el mapa */}
      <WeatherOverlay 
        weatherInfo={weatherInfo}
        position="top-right"
      />
      
      {/* Efectos visuales de clima en rutas */}
      <RouteWeatherEffects 
        routes={optimizedRoutes}
        weatherInfo={weatherInfo}
      />
      
      <DeckGL
        initialViewState={INITIAL_VIEW_STATE}
        controller
        layers={layers}
      >
        <Map reuseMaps mapLib={import("maplibre-gl")} mapStyle={MAP_STYLE} />
      </DeckGL>
      
      {/* Botón para toggle del panel climático */}
      {weatherInfo && (
        <button 
          className="weather-toggle-btn"
          onClick={() => setShowWeatherPanel(!showWeatherPanel)}
          style={{
            position: 'fixed',
            bottom: '20px',
            left: '20px',
            zIndex: 1000,
            background: 'rgba(79, 70, 229, 0.9)',
            color: 'white',
            border: 'none',
            borderRadius: '50%',
            width: '50px',
            height: '50px',
            fontSize: '20px',
            cursor: 'pointer',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
            transition: 'all 0.3s ease'
          }}
          onMouseEnter={(e) => {
            e.target.style.transform = 'scale(1.1)';
            e.target.style.background = 'rgba(79, 70, 229, 1)';
          }}
          onMouseLeave={(e) => {
            e.target.style.transform = 'scale(1)';
            e.target.style.background = 'rgba(79, 70, 229, 0.9)';
          }}
        >
          {showWeatherPanel ? '🌤️' : '🌦️'}
        </button>
      )}
    </>
  );
}

export default App;

