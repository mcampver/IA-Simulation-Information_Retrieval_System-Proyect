import { useState, useEffect, useRef } from 'react';

function useWebSocket(url) {
  const [connectionStatus, setConnectionStatus] = useState("Conectando...");
  const [errorMessage, setErrorMessage] = useState("");
  const [vehicleData, setVehicleData] = useState({});
  const [trafficLights, setTrafficLights] = useState([]);
  
  const wsRef = useRef(null);
  const trailsRef = useRef({});

  useEffect(() => {
    const connectWebSocket = () => {
      try {
        console.log("Intentando conectar al WebSocket...");
        const ws = new WebSocket(url);
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
          } catch (err) {
            console.error("Error procesando mensaje:", err);
            setErrorMessage(`Error procesando datos: ${err.message}`);
          }
        };

        ws.onclose = () => {
          console.log("Conexión WebSocket cerrada");
          setConnectionStatus("Desconectado");
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
        setTimeout(connectWebSocket, 3000);
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [url]);

  // Función para enviar mensajes al servidor
  const sendMessage = (message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    } else {
      setErrorMessage("No hay conexión con el servidor");
      return false;
    }
  };

  return {
    connectionStatus,
    errorMessage,
    vehicleData,
    trafficLights,
    wsRef,
    sendMessage
  };
}

export default useWebSocket;