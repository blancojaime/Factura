import { ESTADO_CLASE, ESTADO_LABEL } from "@/lib/format";
import type { Estado } from "@/lib/tipos";
import { Badge } from "./ui";

export default function EstadoBadge({ estado }: { estado: Estado }) {
  return <Badge className={ESTADO_CLASE[estado]}>{ESTADO_LABEL[estado]}</Badge>;
}
