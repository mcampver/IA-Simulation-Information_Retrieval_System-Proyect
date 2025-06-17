
// Colores predefinidos para rutas
export const routeColors = [
  [255, 0, 0],    // Rojo
  [0, 128, 255],  // Azul
  [0, 204, 0],    // Verde
  [255, 102, 0],  // Naranja
  [153, 51, 255], // Púrpura
  [255, 204, 0],  // Amarillo
  [0, 204, 204],  // Turquesa
  [255, 0, 255],  // Magenta
];

// Función para obtener un color según el índice
export function getRouteColor(index) {
  return routeColors[index % routeColors.length];
}