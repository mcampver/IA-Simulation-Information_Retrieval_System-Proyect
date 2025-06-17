import React from "react";

const RouteStats = ({ optimizedRoutes }) => {
  if (!optimizedRoutes || optimizedRoutes.length === 0) {
    return null;
  }

  // Calcular estadísticas generales
  const totalDistance = optimizedRoutes.reduce((sum, route) => sum + route.distance, 0);
  const totalPoints = optimizedRoutes.reduce((sum, route) => sum + route.path.length, 0);

  return (
    <div style={{
      backgroundColor: "rgba(255,255,255,0.8)",
      padding: "10px",
      marginTop: "10px",
      borderRadius: "4px"
    }}>
      <h3>Estadísticas de Rutas</h3>
      <div><strong>Total de rutas:</strong> {optimizedRoutes.length}</div>
      <div><strong>Distancia total:</strong> {totalDistance.toFixed(2)} km</div>
      <div><strong>Total de puntos:</strong> {totalPoints}</div>
      
      <h4 style={{ marginTop: "10px" }}>Rutas individuales:</h4>
      {optimizedRoutes.map((route) => (
        <div key={route.id} style={{ 
          marginTop: "5px",
          padding: "5px",
          borderLeft: `4px solid rgb(${route.color[0]}, ${route.color[1]}, ${route.color[2]})`
        }}>
          <div><strong>{route.vehicleId}</strong></div>
          <div>Distancia: {route.distance.toFixed(2)} km</div>
          <div>Puntos: {route.path.length}</div>
        </div>
      ))}
    </div>
  );
};

export default RouteStats;