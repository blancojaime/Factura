import { Alert, Card, CardBody, CardHeader, CardTitle } from "@/components/ui";
import { fecha, METODO_LABEL, MODALIDAD_LABEL, TIPO_OBJETO_LABEL } from "@/lib/format";
import type { Contratacion } from "@/lib/tipos";
import { Dato } from "./comun";
import ItemsTabla from "./ItemsTabla";

export default function Resumen({ c }: { c: Contratacion }) {
  return (
    <div className="space-y-5">
      <Card>
        <CardHeader><CardTitle>Datos de la contratación</CardTitle></CardHeader>
        <CardBody>
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Dato etiqueta="Unidad solicitante">{c.unidad_solicitante}</Dato>
            <Dato etiqueta="Tipo de objeto">{TIPO_OBJETO_LABEL[c.tipo_objeto]}</Dato>
            <Dato etiqueta="Plazo">{c.plazo_dias_calendario} días calendario</Dato>
            <Dato etiqueta="Lugar de entrega">{c.lugar_entrega}</Dato>
            <Dato etiqueta="Modalidad por cuantía">{c.modalidad_cuantia ? MODALIDAD_LABEL[c.modalidad_cuantia] : ""}</Dato>
            <Dato etiqueta="Formalización">{c.metodo_formalizacion ? METODO_LABEL[c.metodo_formalizacion] : ""}</Dato>
            <Dato etiqueta="N° Formulario 110">{c.nro_formulario_110}</Dato>
            <Dato etiqueta="CUCE">{c.cuce}</Dato>
            <Dato etiqueta="N° preventivo C-31">{c.preventivo_c31_nro}</Dato>
            <Dato etiqueta="Creado">{fecha(c.created_at)}</Dato>
          </dl>
          <div className="mt-5 space-y-4">
            <div><h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">Justificación de la necesidad</h3><p className="mt-1 whitespace-pre-wrap text-sm">{c.justificacion}</p></div>
            <div><h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">Especificaciones técnicas / Términos de referencia</h3><p className="mt-1 whitespace-pre-wrap text-sm">{c.especificaciones_tecnicas}</p></div>
          </div>
        </CardBody>
      </Card>
      {c.requiere_excepcion_chb && (
        <Alert tipo="warning" titulo="Compra fuera del Catálogo CHB (D.S. 4505 / D.S. 0181)">
          <p className="whitespace-pre-wrap">{c.justificacion_excepcion_chb}</p>
          {c.codigo_autorizacion_chb && <p>Autorización: <b>{c.codigo_autorizacion_chb}</b></p>}
        </Alert>
      )}
      <Card>
        <CardHeader><CardTitle>Ítems</CardTitle></CardHeader>
        <ItemsTabla items={c.items} total={c.monto_referencial_total} />
      </Card>
    </div>
  );
}
