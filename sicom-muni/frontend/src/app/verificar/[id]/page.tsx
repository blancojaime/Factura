import Verificacion from "./Verificacion";

// La pantalla se exporta como archivos estaticos: se genera una sola pagina con el marcador "_"
// y el navegador lee el identificador real de la URL (ver lib/ruta.ts).
export const dynamicParams = false;
export function generateStaticParams() {
  return [{ id: "_" }];
}

export default function Pagina() {
  return <Verificacion />;
}
