"""Anexa un capítulo (docx generado en modo PLAIN) al final de un manual Word y corrige textos que cambiaron."""
import copy, sys, docx
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def reemplazar_parrafo(p, viejo, nuevo):
    runs = p.runs
    txt = ''.join(r.text for r in runs)
    i = txt.find(viejo)
    if i < 0: return False
    j = i + len(viejo); pos = 0; puesto = False
    for r in runs:
        a, b = pos, pos + len(r.text); pos = b
        if b <= i or a >= j: continue
        ini, fin = max(i, a) - a, min(j, b) - a
        r.text = r.text[:ini] + (nuevo if not puesto else '') + r.text[fin:]
        puesto = True
    return True

def todos_los_parrafos(d):
    for p in d.paragraphs: yield p
    def tablas(ts):
        for t in ts:
            for row in t.rows:
                for c in row.cells:
                    for p in c.paragraphs: yield p
                    yield from tablas(c.tables)
    yield from tablas(d.tables)

def anexar(destino, anexo, reemplazos=()):
    d = docx.Document(destino)
    n = 0
    for p in todos_los_parrafos(d):
        for viejo, nuevo in reemplazos:
            while reemplazar_parrafo(p, viejo, nuevo): n += 1
    a = docx.Document(anexo)
    body = d.element.body
    sect = body.find(qn('w:sectPr'))
    primero = True
    for el in list(a.element.body):
        if el.tag == qn('w:sectPr'): continue
        nuevo = copy.deepcopy(el)
        if primero and el.tag == qn('w:p'):
            ppr = nuevo.find(qn('w:pPr'))
            if ppr is None: ppr = OxmlElement('w:pPr'); nuevo.insert(0, ppr)
            if ppr.find(qn('w:pageBreakBefore')) is None: ppr.append(OxmlElement('w:pageBreakBefore'))
            primero = False
        if sect is not None: sect.addprevious(nuevo)
        else: body.append(nuevo)
    d.save(destino)
    return n

if __name__ == '__main__':
    reemplazos = [tuple(x.split('=>')) for x in sys.argv[3:]]
    print(destino := sys.argv[1], 'reemplazos:', anexar(sys.argv[1], sys.argv[2], reemplazos))
