import React, { useState, useRef, useEffect } from 'react';

const RAGAssistantPanel = ({ 
  optimizedRoutes, 
  weatherInfo, 
  connectionStatus,
  showRAGPanel,
  setShowRAGPanel 
}) => {
  const [question, setQuestion] = useState('');
  const [response, setResponse] = useState('');
  const [isAsking, setIsAsking] = useState(false);
  const [conversationHistory, setConversationHistory] = useState([]);
  const responseRef = useRef(null);

  // Auto-scroll cuando hay nueva respuesta - MOVER ANTES DEL RETURN
  useEffect(() => {
    if (responseRef.current && response) {
      responseRef.current.scrollTop = responseRef.current.scrollHeight;
    }
  }, [response, conversationHistory]);

  // Si no está visible, no renderizar nada - DESPUÉS DE TODOS LOS HOOKS
  if (!showRAGPanel) return null;

  const historyItemStyles = {
    marginBottom: '15px',
    padding: '10px',
    backgroundColor: '#ffffff',
    border: '1px solid #e5e7eb',
    borderRadius: '6px'
  };

  const questionStyles = {
    fontWeight: '600',
    color: '#374151',
    marginBottom: '8px'
  };

  const answerStyles = {
    color: '#6b7280',
    fontSize: '13px',
    lineHeight: '1.5'
  };

  // Preguntas sugeridas
  const suggestedQuestions = [
    "¿Cómo está afectando el clima actual a mis rutas de entrega?",
    "¿Cuál es la eficiencia de mis rutas optimizadas?",
    "¿Hay eventos de tráfico que puedan impactar mis entregas?",
    "¿Qué recomendaciones tienes para mejorar mis rutas?",
    "¿Cuál es el rendimiento del sistema de optimización?"
  ];

  // Función para enviar pregunta al RAG
  const askRAG = async () => {
    if (!question.trim()) {
      alert('Por favor, escribe una pregunta');
      return;
    }

    setIsAsking(true);
    
    try {
      // Preparar datos contextuales
      const contextData = {
        routes: optimizedRoutes,
        weather: weatherInfo,
        system_status: connectionStatus,
        timestamp: new Date().toISOString()
      };

      const response = await fetch('http://localhost:8767/ask_rag', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          context_data: contextData
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      
      if (result.success) {
        const newConversation = {
          question: question,
          response: result.response,
          metrics: result.relevant_metrics,
          timestamp: new Date().toLocaleTimeString(),
          category: result.question_category
        };

        setConversationHistory(prev => [...prev, newConversation]);
        setResponse(result.response);
        setQuestion('');
        
        // Scroll al final de la respuesta
        setTimeout(() => {
          if (responseRef.current) {
            responseRef.current.scrollTop = responseRef.current.scrollHeight;
          }
        }, 100);
      } else {
        setResponse(`Error: ${result.message}`);
      }
    } catch (error) {
      console.error('Error consultando RAG:', error);
      setResponse(`Error conectando con el asistente: ${error.message}`);
    } finally {
      setIsAsking(false);
    }
  };

  // Función para usar pregunta sugerida
  const useSuggestedQuestion = (suggestedQ) => {
    setQuestion(suggestedQ);
  };

  // Función para limpiar conversación
  const clearConversation = () => {
    setConversationHistory([]);
    setResponse('');
    setQuestion('');
  };

  return (
    <>
      {/* Backdrop con blur */}
      <div 
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0, 0, 0, 0.4)",
          zIndex: 450,
          backdropFilter: "blur(2px)"
        }}
        onClick={() => setShowRAGPanel(false)}
      />
      
      {/* Modal Content */}
      <div style={{
        position: "fixed",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        zIndex: 500,
        maxWidth: "600px",
        width: "90vw",
        maxHeight: "85vh",
        overflowY: "auto",
        padding: "0",
        backgroundColor: "rgba(255, 255, 255, 0.98)",
        borderRadius: "12px",
        boxShadow: "0 8px 25px rgba(0,0,0,0.2)",
        backdropFilter: "blur(10px)",
        border: "1px solid rgba(255, 255, 255, 0.3)",
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
      }}>
        {/* Header sticky */}
        <div style={{
          position: "sticky",
          top: 0,
          background: "linear-gradient(135deg, #7c3aed, #a855f7)",
          color: "white",
          padding: "15px 20px",
          borderRadius: "12px 12px 0 0",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          zIndex: 501
        }}>
          <h2 style={{ margin: 0, fontSize: "18px", fontWeight: "600" }}>
            🧠 Asistente RAG VRP
          </h2>
          <button 
            onClick={() => setShowRAGPanel(false)}
            style={{
              background: "rgba(255, 255, 255, 0.2)",
              border: "none",
              color: "white",
              fontSize: "18px",
              cursor: "pointer",
              borderRadius: "50%",
              width: "32px",
              height: "32px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "all 0.3s ease"
            }}
            onMouseOver={(e) => e.target.style.backgroundColor = "rgba(255, 255, 255, 0.3)"}
            onMouseOut={(e) => e.target.style.backgroundColor = "rgba(255, 255, 255, 0.2)"}
          >
            ✕
          </button>
        </div>
        
        {/* Content */}
        <div style={{ padding: "20px" }}>
          {/* Área de respuesta */}
          <div style={{ marginBottom: '20px' }}>
            <div style={{
              fontSize: '14px',
              fontWeight: '600',
              color: '#374151',
              marginBottom: '8px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <span>💬 Conversación</span>
              {conversationHistory.length > 0 && (
                <button
                  onClick={clearConversation}
                  style={{
                    background: '#f3f4f6',
                    border: '1px solid #d1d5db',
                    color: '#6b7280',
                    fontSize: '11px',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  🗑️ Limpiar
                </button>
              )}
            </div>
            
            <div 
              ref={responseRef} 
              style={{
                backgroundColor: '#f8fafc',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                padding: '15px',
                overflowY: 'auto',
                maxHeight: '300px',
                fontSize: '14px',
                lineHeight: '1.6'
              }}
            >
              {conversationHistory.length === 0 && !response ? (
                <div style={{ 
                  textAlign: 'center', 
                  color: '#9ca3af', 
                  fontSize: '13px',
                  marginTop: '40px' 
                }}>
                  <div style={{ fontSize: '48px', marginBottom: '16px' }}>🤖</div>
                  <h4 style={{ margin: '0 0 8px 0', color: '#6b7280' }}>
                    Asistente VRP con RAG
                  </h4>
                  <p style={{ margin: 0, lineHeight: '1.4' }}>
                    Pregúntame sobre rutas, clima, tráfico, optimización o rendimiento del sistema.
                    Uso toda la información contextual disponible para darte respuestas precisas.
                  </p>
                </div>
              ) : (
                <>
                  {/* Historial de conversación */}
                  {conversationHistory.map((conv, index) => (
                    <div key={index} style={historyItemStyles}>
                      <div style={questionStyles}>
                        🙋‍♂️ {conv.question}
                      </div>
                      <div style={answerStyles}>
                        🤖 {conv.response}
                      </div>
                      <div style={{
                        fontSize: '11px',
                        color: '#9ca3af',
                        marginTop: '6px',
                        display: 'flex',
                        justifyContent: 'space-between'
                      }}>
                        <span>{conv.timestamp}</span>
                        <span>📊 {conv.category}</span>
                      </div>
                    </div>
                  ))}
                  
                  {/* Respuesta actual */}
                  {response && conversationHistory.length === 0 && (
                    <div style={{ 
                      whiteSpace: 'pre-wrap',
                      color: '#374151'
                    }}>
                      {response}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Preguntas sugeridas */}
          <div style={{ marginBottom: '20px' }}>
            <div style={{
              fontSize: '12px',
              fontWeight: '600',
              color: '#6b7280',
              marginBottom: '8px'
            }}>
              💡 Preguntas sugeridas:
            </div>
            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '6px'
            }}>
              {suggestedQuestions.slice(0, 3).map((q, index) => (
                <button
                  key={index}
                  onClick={() => useSuggestedQuestion(q)}
                  style={{
                    background: '#f3f4f6',
                    border: '1px solid #d1d5db',
                    color: '#374151',
                    fontSize: '11px',
                    padding: '4px 8px',
                    borderRadius: '12px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseOver={(e) => {
                    e.target.style.backgroundColor = '#e5e7eb';
                  }}
                  onMouseOut={(e) => {
                    e.target.style.backgroundColor = '#f3f4f6';
                  }}
                >
                  {q.length > 40 ? q.substring(0, 40) + '...' : q}
                </button>
              ))}
            </div>
          </div>

          {/* Área de entrada */}
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '10px'
          }}>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Pregúntame sobre rutas, clima, tráfico, optimización o rendimiento del sistema..."
              style={{
                width: '100%',
                minHeight: '80px',
                padding: '12px',
                border: '1px solid #d1d5db',
                borderRadius: '8px',
                fontSize: '14px',
                resize: 'vertical',
                fontFamily: 'inherit',
                outline: 'none',
                transition: 'border-color 0.3s ease'
              }}
              onFocus={(e) => e.target.style.borderColor = '#7c3aed'}
              onBlur={(e) => e.target.style.borderColor = '#d1d5db'}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && e.ctrlKey) {
                  askRAG();
                }
              }}
            />
            
            <button 
              onClick={askRAG}
              disabled={isAsking || !question.trim()}
              style={{
                padding: '10px 16px',
                backgroundColor: isAsking || !question.trim() ? '#9ca3af' : '#7c3aed',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: isAsking || !question.trim() ? 'not-allowed' : 'pointer',
                fontSize: '14px',
                fontWeight: '600',
                transition: 'all 0.3s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px'
              }}
              onMouseOver={(e) => {
                if (!isAsking && question.trim()) {
                  e.target.style.backgroundColor = '#6d28d9';
                }
              }}
              onMouseOut={(e) => {
                if (!isAsking && question.trim()) {
                  e.target.style.backgroundColor = '#7c3aed';
                }
              }}
            >
              {isAsking ? (
                <>
                  <div style={{
                    width: '14px',
                    height: '14px',
                    border: '2px solid #ffffff',
                    borderTop: '2px solid transparent',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite'
                  }} />
                  Procesando...
                </>
              ) : (
                <>
                  🚀 Preguntar
                  <span style={{ fontSize: '11px', opacity: 0.8 }}>
                    (Ctrl+Enter)
                  </span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* CSS para animación */}
      <style jsx>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </>
  );
};

export default RAGAssistantPanel;