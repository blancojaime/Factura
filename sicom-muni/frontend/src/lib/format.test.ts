import { describe, expect, it } from "vitest";
import { bs, ESTADOS, ESTADO_LABEL, ROL_LABEL } from "./format";

describe("format", () => {
  it("formatea bolivianos con separador de miles y 2 decimales", () => {
    expect(bs("18500")).toMatch(/18\.500,00|18\s?500,00/);
    expect(bs(null)).toBe("—");
  });
  it("todos los estados tienen etiqueta", () => {
    for (const e of ESTADOS) expect(ESTADO_LABEL[e]).toBeTruthy();
  });
  it("hay 6 roles", () => {
    expect(Object.keys(ROL_LABEL)).toHaveLength(6);
  });
});
