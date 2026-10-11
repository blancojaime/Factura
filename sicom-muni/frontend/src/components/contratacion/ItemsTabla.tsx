import { Badge, Tabla, Td, Th } from "@/components/ui";
import { bs, CHB_LABEL } from "@/lib/format";
import type { Item } from "@/lib/tipos";
import { cn } from "@/lib/utils";

export function ChbBadge({ estado }: { estado: Item["estado_chb"] }) {
  const clase =
    estado === "COMPRA_CHB_OBLIGATORIA" ? "bg-red-100 text-red-800 ring-red-300"
    : estado === "NO_APLICA" ? "bg-slate-100 text-slate-600 ring-slate-300" : "bg-amber-100 text-amber-800 ring-amber-300";
  return <Badge className={clase}>{CHB_LABEL[estado]}</Badge>;
}

export default function ItemsTabla({ items, total, acciones }: {
  items: Item[]; total: string; acciones?: (i: Item) => React.ReactNode;
}) {
  return (
    <Tabla aria-label="Ítems de la contratación">
      <thead>
        <tr><Th>N°</Th><Th>UNSPSC</Th><Th>Partida</Th><Th>Descripción</Th><Th>Unidad</Th><Th className="text-right">Cantidad</Th>
          <Th className="text-right">P. unit. (Bs)</Th><Th className="text-right">Subtotal (Bs)</Th><Th>CHB</Th>{acciones && <Th />}</tr>
      </thead>
      <tbody>
        {items.length === 0 && <tr><Td colSpan={10} className="py-6 text-center text-slate-500">Aún no hay ítems.</Td></tr>}
        {items.map((i) => (
          <tr key={i.id} className={cn(i.estado_chb === "COMPRA_CHB_OBLIGATORIA" && "bg-red-50/50")}>
            <Td>{i.numero}</Td><Td className="num">{i.codigo_unspsc || "—"}</Td><Td className="num">{i.partida_gasto}</Td>
            <Td className="max-w-sm">{i.descripcion_especifica}</Td><Td>{i.unidad_medida}</Td>
            <Td className="num text-right">{Number(i.cantidad).toLocaleString("es-BO", { maximumFractionDigits: 3 })}</Td>
            <Td className="num text-right">{bs(i.precio_unitario_ref)}</Td><Td className="num text-right font-medium">{bs(i.subtotal)}</Td>
            <Td><ChbBadge estado={i.estado_chb} /></Td>{acciones && <Td>{acciones(i)}</Td>}
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr><Td colSpan={7} className="text-right font-semibold">Total referencial (Bs)</Td><Td className="num text-right text-base font-bold">{bs(total)}</Td><Td /></tr>
      </tfoot>
    </Tabla>
  );
}
