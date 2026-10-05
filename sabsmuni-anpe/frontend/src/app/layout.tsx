import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = { title: 'SABSMUNI-ANPE', description: 'Gestión y documentación de contrataciones estatales ANPE' };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="es"><body>{children}</body></html>;
}
