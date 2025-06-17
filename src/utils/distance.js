
// Función para calcular la distancia aproximada en kilómetros usando Haversine
export function calculateRouteDistance(path) {
  if (!path || path.length < 2) return 0;
  
  try {
    let distance = 0;
    for (let i = 0; i < path.length - 1; i++) {
      const [lon1, lat1] = path[i];
      const [lon2, lat2] = path[i + 1];
      
      if (lon1 === undefined || lat1 === undefined || lon2 === undefined || lat2 === undefined) {
        console.warn("Coordenadas indefinidas en el cálculo de distancia", { 
          punto1: path[i], 
          punto2: path[i + 1] 
        });
        continue;
      }
      
      // Fórmula Haversine simplificada
      const R = 6371; // Radio de la Tierra en km
      const dLat = (lat2 - lat1) * Math.PI / 180;
      const dLon = (lon2 - lon1) * Math.PI / 180;
      const a = 
        Math.sin(dLat/2) * Math.sin(dLat/2) +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
        Math.sin(dLon/2) * Math.sin(dLon/2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
      distance += R * c;
    }
    
    return distance;
  } catch (err) {
    console.error("Error calculando la distancia de la ruta:", err);
    return 0; // Valor por defecto en caso de error
  }
}