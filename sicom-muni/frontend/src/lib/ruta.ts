"use client";

import { useEffect, useState } from "react";

/** Identificador de la URL real (…/<base>/<id>/). La pantalla exportada es estatica: no se puede confiar en useParams. */
export function useIdDeRuta(base: string): string {
  const [id, setId] = useState("");
  useEffect(() => {
    const partes = window.location.pathname.split("/").filter(Boolean);
    const i = partes.indexOf(base);
    setId(i >= 0 && partes[i + 1] ? decodeURIComponent(partes[i + 1]) : "");
  }, [base]);
  return id;
}
