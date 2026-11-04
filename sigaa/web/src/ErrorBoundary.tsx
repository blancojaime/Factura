import { Component, ReactNode } from 'react';

/** Si una pantalla falla por un error inesperado, se muestra un aviso con salida en vez de dejar la página en blanco. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, { error: string }> {
  state = { error: '' };
  static getDerivedStateFromError(e: unknown) { return { error: e instanceof Error ? e.message : String(e) }; }
  componentDidCatch(e: unknown) { console.error('Error de pantalla:', e); }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div style={{ maxWidth: 560, margin: '12vh auto', padding: 24, fontFamily: 'system-ui, sans-serif' }}>
        <h2>Ocurrió un problema en esta pantalla</h2>
        <p>Sus datos guardados están a salvo. Pulse el botón para volver a cargar el sistema; si se repite, anote lo que estaba haciendo y avise al administrador.</p>
        <p style={{ color: '#7a1f3d', fontSize: 13 }}>{this.state.error}</p>
        <button onClick={() => { window.location.href = '/'; }} style={{ padding: '8px 16px' }}>Volver al inicio</button>
      </div>
    );
  }
}
