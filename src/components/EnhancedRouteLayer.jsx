import React from 'react';
import { PathLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers';

const EnhancedRouteLayer = ({ 
  routes, 
  selectedRouteId, 
  weatherInfo,
  onRouteClick 
}) => {
  if (!routes || routes.length === 0) return [];

  // Función para calcular puntos de flecha considerando TODOS los segmentos
  const calculateArrowPoints = (path, routeId) => {
    const arrows = [];
    if (path.length < 2) return arrows;
    
    // Calcular la longitud total de la ruta para distribuir flechas uniformemente
    let totalDistance = 0;
    const segmentDistances = [];
    
    for (let i = 0; i < path.length - 1; i++) {
      const start = path[i];
      const end = path[i + 1];
      const dx = end[0] - start[0];
      const dy = end[1] - start[1];
      const distance = Math.sqrt(dx * dx + dy * dy);
      segmentDistances.push(distance);
      totalDistance += distance;
    }
    
    // Número de flechas basado en la longitud de la ruta
    const numArrows = Math.min(12, Math.max(3, Math.floor(totalDistance * 1000))); // Ajustar multiplicador según escala
    const arrowInterval = totalDistance / (numArrows + 1);
    
    let currentDistance = arrowInterval;
    let segmentIndex = 0;
    let accumulatedDistance = 0;
    
    for (let arrow = 0; arrow < numArrows; arrow++) {
      // Encontrar en qué segmento debe ir esta flecha
      while (segmentIndex < segmentDistances.length && 
             accumulatedDistance + segmentDistances[segmentIndex] < currentDistance) {
        accumulatedDistance += segmentDistances[segmentIndex];
        segmentIndex++;
      }
      
      if (segmentIndex >= path.length - 1) break;
      
      // Calcular posición exacta dentro del segmento
      const remainingDistance = currentDistance - accumulatedDistance;
      const segmentDistance = segmentDistances[segmentIndex];
      const ratio = segmentDistance > 0 ? remainingDistance / segmentDistance : 0;
      
      const start = path[segmentIndex];
      const end = path[segmentIndex + 1];
      
      // Interpolación lineal para la posición
      const position = [
        start[0] + (end[0] - start[0]) * ratio,
        start[1] + (end[1] - start[1]) * ratio
      ];
      
      // Calcular ángulo de dirección
      const dx = end[0] - start[0];
      const dy = end[1] - start[1];
      const angle = Math.atan2(dy, dx) * 180 / Math.PI;
      
      arrows.push({
        id: `${routeId}-arrow-${arrow}`,
        routeId,
        position: position,
        angle: angle,
        segment: segmentIndex,
        progress: ratio
      });
      
      currentDistance += arrowInterval;
    }
    
    return arrows;
  };

  // Función mejorada para calcular puntos de numeración considerando paradas reales
  const calculateNumberPoints = (path, routeId, vehicleId) => {
    const numbers = [];
    if (path.length === 0) return numbers;
    
    // Depot (punto inicial) - siempre el primer punto
    numbers.push({
      id: `${routeId}-depot-start`,
      routeId,
      position: path[0],
      text: '🏠',
      type: 'depot',
      subtype: 'start',
      size: 22
    });
    
    // Función para detectar si dos puntos son "iguales" (muy cercanos)
    const arePointsEqual = (p1, p2, threshold = 0.0001) => {
      return Math.abs(p1[0] - p2[0]) < threshold && Math.abs(p1[1] - p2[1]) < threshold;
    };
    
    // Detectar paradas reales (puntos donde el vehículo se detiene)
    const deliveryStops = [];
    const visitedPoints = new Set();
    
    // Analizar la ruta para encontrar puntos de entrega únicos
    for (let i = 1; i < path.length - 1; i++) {
      const currentPoint = path[i];
      const pointKey = `${currentPoint[0].toFixed(6)}_${currentPoint[1].toFixed(6)}`;
      
      // Si es un punto que no hemos visitado como parada
      if (!visitedPoints.has(pointKey)) {
        // Verificar si este punto es diferente del depot
        if (!arePointsEqual(currentPoint, path[0])) {
          deliveryStops.push({
            position: currentPoint,
            index: i,
            key: pointKey
          });
          visitedPoints.add(pointKey);
        }
      }
    }
    
    // Numerar las paradas de entrega
    deliveryStops.forEach((stop, index) => {
      numbers.push({
        id: `${routeId}-delivery-${index}`,
        routeId,
        position: stop.position,
        text: (index + 1).toString(),
        type: 'delivery',
        order: index + 1,
        size: 18,
        originalIndex: stop.index
      });
    });
    
    // Depot final (si es diferente del inicial)
    const lastPoint = path[path.length - 1];
    if (!arePointsEqual(lastPoint, path[0])) {
      numbers.push({
        id: `${routeId}-depot-end`,
        routeId,
        position: lastPoint,
        text: '🏁',
        type: 'depot',
        subtype: 'end',
        size: 20
      });
    }
    
    return numbers;
  };

  // Generar todos los puntos de flecha y numeración
  const allArrows = [];
  const allNumbers = [];
  
  routes.forEach(route => {
    if (route.path && route.path.length > 1) {
      allArrows.push(...calculateArrowPoints(route.path, route.id));
      allNumbers.push(...calculateNumberPoints(route.path, route.id, route.vehicleId));
    }
  });

  // Función para obtener color según clima y selección
  const getRouteColor = (route) => {
    if (route.id === selectedRouteId) {
      return [255, 255, 255, 255]; // Blanco para seleccionada
    }
    
    const routeIndex = parseInt(route.id.split('-')[1]) || 0;
    const baseColors = [
      [255, 0, 0],    // Rojo
      [0, 128, 255],  // Azul
      [0, 204, 0],    // Verde
      [255, 102, 0],  // Naranja
      [153, 51, 255], // Púrpura
      [255, 204, 0],  // Amarillo
      [0, 204, 204],  // Turquesa
      [255, 0, 255],  // Magenta
    ];
    
    const baseColor = baseColors[routeIndex % baseColors.length];
    
    // Aplicar modificaciones por clima
    if (weatherInfo && weatherInfo.impact_factor > 1.6) {
      return [
        Math.max(baseColor[0] * 0.8, 80),
        Math.max(baseColor[1] * 0.8, 80),
        Math.max(baseColor[2] * 0.8, 80),
        255
      ];
    } else if (weatherInfo && weatherInfo.impact_factor > 1.3) {
      return [
        Math.min(255, baseColor[0] * 1.05),
        Math.min(255, baseColor[1] * 1.02),
        Math.min(255, baseColor[2] * 0.98),
        255
      ];
    }
    
    return [...baseColor, 255];
  };

  return [
    // 1. Capa principal de rutas con gradiente
    new PathLayer({
      id: 'enhanced-routes-main',
      data: routes,
      pickable: true,
      widthScale: 1,
      widthMinPixels: 4,
      capRounded: true,
      jointRounded: true,
      getPath: d => d.path,
      getColor: getRouteColor,
      getWidth: d => {
        const baseWidth = d.id === selectedRouteId ? 10 : 6;
        if (weatherInfo && weatherInfo.impact_factor > 1.6) {
          return baseWidth + 2;
        }
        return baseWidth;
      },
      onClick: (info) => {
        if (info.object && onRouteClick) {
          onRouteClick(info.object.id);
        }
      },
      updateTriggers: {
        getColor: [selectedRouteId, weatherInfo?.impact_factor],
        getWidth: [selectedRouteId, weatherInfo?.impact_factor]
      }
    }),

    // 2. Capa de sombra/borde para mejor visibilidad de la ruta seleccionada
    new PathLayer({
      id: 'enhanced-routes-shadow',
      data: routes.filter(route => route.id === selectedRouteId),
      widthScale: 1,
      widthMinPixels: 8,
      capRounded: true,
      jointRounded: true,
      getPath: d => d.path,
      getColor: [0, 0, 0, 120], // Sombra negra semi-transparente
      getWidth: d => (d.id === selectedRouteId ? 14 : 0),
      updateTriggers: {
        getWidth: [selectedRouteId]
      }
    }),

    // 3. Puntos de numeración y depots
    new ScatterplotLayer({
      id: 'route-numbers',
      data: allNumbers.filter(point => 
        !selectedRouteId || point.routeId === selectedRouteId
      ),
      pickable: true,
      stroked: true,
      filled: true,
      getPosition: d => d.position,
      getRadius: d => d.size,
      getFillColor: d => {
        if (d.type === 'depot') {
          if (d.subtype === 'start') return [34, 197, 94, 230]; // Verde para inicio
          if (d.subtype === 'end') return [239, 68, 68, 230];   // Rojo para final
          return [34, 197, 94, 230];
        }
        const route = routes.find(r => r.id === d.routeId);
        if (route) {
          const color = getRouteColor(route);
          return [color[0], color[1], color[2], 230];
        }
        return [100, 100, 100, 230];
      },
      getLineColor: [255, 255, 255],
      getLineWidth: 3,
      updateTriggers: {
        getFillColor: [selectedRouteId, weatherInfo?.impact_factor]
      }
    }),

    // 4. Texto de numeración y símbolos
    new TextLayer({
      id: 'route-text',
      data: allNumbers.filter(point => 
        !selectedRouteId || point.routeId === selectedRouteId
      ),
      pickable: false,
      getPosition: d => d.position,
      getText: d => d.text,
      getSize: d => {
        if (d.type === 'depot') return d.size === 22 ? 18 : 16;
        return 14;
      },
      getColor: [255, 255, 255],
      getAngle: 0,
      getTextAnchor: 'middle',
      getAlignmentBaseline: 'center',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      fontWeight: 'bold',
      updateTriggers: {
        getData: [selectedRouteId]
      }
    }),

    // 5. Flechas direccionales mejoradas
    new ScatterplotLayer({
      id: 'direction-arrows',
      data: allArrows.filter(arrow => 
        !selectedRouteId || arrow.routeId === selectedRouteId
      ),
      pickable: false,
      stroked: false,
      filled: true,
      radiusScale: 1,
      getPosition: d => d.position,
      getRadius: 10,
      getFillColor: d => {
        const route = routes.find(r => r.id === d.routeId);
        if (route) {
          const color = getRouteColor(route);
          return [color[0], color[1], color[2], 200];
        }
        return [100, 100, 100, 200];
      },
      updateTriggers: {
        getFillColor: [selectedRouteId, weatherInfo?.impact_factor]
      }
    }),

    // 6. Símbolos de flecha usando TextLayer
    new TextLayer({
      id: 'arrow-symbols',
      data: allArrows.filter(arrow => 
        !selectedRouteId || arrow.routeId === selectedRouteId
      ),
      pickable: false,
      getPosition: d => d.position,
      getText: '▶',
      getSize: 12,
      getColor: [255, 255, 255],
      getAngle: d => d.angle,
      getTextAnchor: 'middle',
      getAlignmentBaseline: 'center',
      fontFamily: 'Arial, sans-serif',
      fontWeight: 'bold',
      updateTriggers: {
        getData: [selectedRouteId]
      }
    })
  ];
};

export default EnhancedRouteLayer;