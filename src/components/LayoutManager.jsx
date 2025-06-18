import React from 'react';

// Sistema de grid para posicionamiento consistente
const LAYOUT_ZONES = {
  topLeft: { top: '20px', left: '20px' },
  topCenter: { top: '20px', left: '50%', transform: 'translateX(-50%)' },
  topRight: { top: '20px', right: '20px' },
  centerLeft: { top: '50%', left: '20px', transform: 'translateY(-50%)' },
  centerRight: { top: '50%', right: '20px', transform: 'translateY(-50%)' },
  bottomLeft: { bottom: '20px', left: '20px' },
  bottomCenter: { bottom: '20px', left: '50%', transform: 'translateX(-50%)' },
  bottomRight: { bottom: '20px', right: '20px' }
};

// Estilo base común para todos los paneles
export const basePanel = {
  position: 'fixed',
  background: 'rgba(255, 255, 255, 0.95)',
  borderRadius: '12px',
  boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
  backdropFilter: 'blur(10px)',
  border: '1px solid rgba(0, 0, 0, 0.1)',
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  transition: 'all 0.3s ease'
};

export const getZonePosition = (zone) => {
  const positions = {
    topLeft: {
      position: 'fixed',
      left: '20px',
      top: '20px'
    },
    topCenter: {
      position: 'fixed',
      left: '50%',
      top: '20px',
      transform: 'translateX(-50%)'
    },
    topRight: {
      position: 'fixed',
      right: '20px',
      top: '20px'
    },
    centerLeft: {
      position: 'fixed',
      left: '20px',
      top: '50%',
      transform: 'translateY(-50%)'
    },
    centerRight: {
      position: 'fixed',
      right: '20px',
      top: '50%',
      transform: 'translateY(-50%)'
    },
    bottomLeft: {
      position: 'fixed',
      left: '20px',
      bottom: '20px'
    },
    bottomCenter: {
      position: 'fixed',
      left: '50%',
      bottom: '20px',
      transform: 'translateX(-50%)'
    },
    bottomRight: {
      position: 'fixed',
      right: '20px',
      bottom: '20px'
    }
  };
  
  return positions[zone] || positions.topLeft;
};

// Z-index consistente
export const Z_LAYERS = {
  background: 100,
  panels: 200,
  overlays: 300,
  modals: 400,
  tooltips: 500
};