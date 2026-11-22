import re
from datetime import datetime
from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

BASE_DIR = Path(__file__).resolve().parent
RUTA_PLANTILLA = BASE_DIR / "plantillas_maestras" / "SET_4_oficial.docx"


def _evitar_corte_fila(row):
    trPr = row._tr.get_or_add_trPr()
    if trPr.find(qn("w:cantSplit")) is None:
        trPr.append(OxmlElement("w:cantSplit"))


def _ajustar_alturas_filas(table, factor_alto: float = 0.72):
    if factor_alto >= 0.999:
        return
    for row in table.rows:
        trPr = row._tr.trPr
        if trPr is None:
            continue
        for trHeight in trPr.findall(qn("w:trHeight")):
            val = trHeight.get(qn("w:val"))
            if val is not None and val.isdigit():
                nuevo_val = max(100, int(int(val) * factor_alto))
                trHeight.set(qn("w:val"), str(nuevo_val))


def _compactar_parrafo(
    paragraph,
    tamano_pt: float | None = None,
    line_spacing: float = 0.95,
):
    pf = paragraph.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing = line_spacing
    pf.page_break_before = False
    pf.keep_with_next = False

    for br in paragraph._p.findall(".//" + qn("w:br")):
        if br.get(qn("w:type")) == "page":
            br.getparent().remove(br)

    if tamano_pt is not None:
        for r in paragraph.runs:
            r.font.size = Pt(tamano_pt)


def _compactar_aspectos_a_considerar(
    table,
    tamano_aspectos_pt: float = 7.5,
    factor_alto_aspectos: float = 0.55,
):
    """Reduce el tamaño de letra y el alto de fila en el bloque 'Aspectos a considerar'."""
    filas_marcadas = set()

    for r_idx, row in enumerate(table.rows):
        texto_fila = " ".join(c.text.lower() for c in row.cells)
        if "aspectos a considerar" in texto_fila:
            filas_marcadas.add(r_idx)
            # Incluye también la fila inmediata siguiente si forma parte del mismo bloque/recuadro
            if r_idx + 1 < len(table.rows):
                filas_marcadas.add(r_idx + 1)

    for r_idx in filas_marcadas:
        row = table.rows[r_idx]
        trPr = row._tr.trPr
        if trPr is not None:
            for trHeight in trPr.findall(qn("w:trHeight")):
                val = trHeight.get(qn("w:val"))
                if val is not None and val.isdigit():
                    nuevo_val = max(80, int(int(val) * factor_alto_aspectos))
                    trHeight.set(qn("w:val"), str(nuevo_val))

        for cell in row.cells:
            for p in cell.paragraphs:
                _compactar_parrafo(p, tamano_pt=tamano_aspectos_pt, line_spacing=0.85)


def _escribir_contiguo_en_parrafo(paragraph, valor: str, tamano_pt: float | None = None):
    valor_limpio = re.sub(r"\s+", " ", str(valor).strip())
    if not valor_limpio:
        return

    texto_actual = paragraph.text or ""
    if re.search(r"_{2,}", texto_actual):
        nuevo_texto = re.sub(r"_{2,}", valor_limpio, texto_actual, count=1)
        nuevo_texto = re.sub(r"\s*_{2,}\s*", " ", nuevo_texto)
    else:
        base = re.sub(r"\s+", " ", texto_actual).strip()
        if not base:
            nuevo_texto = valor_limpio
        elif valor_limpio in base:
            nuevo_texto = base
        elif base.endswith(":"):
            nuevo_texto = f"{base} {valor_limpio}"
        else:
            nuevo_texto = f"{base}: {valor_limpio}"

    nuevo_texto = re.sub(r"\s+", " ", nuevo_texto).strip()

    if paragraph.runs:
        paragraph.runs[0].text = nuevo_texto
        for r in paragraph.runs[1:]:
            r.text = ""
    else:
        run = paragraph.add_run(nuevo_texto)
        if tamano_pt is not None:
            run.font.size = Pt(tamano_pt)

    _compactar_parrafo(paragraph, tamano_pt=tamano_pt, line_spacing=0.95)


def _escribir_contiguo_en_celda(row, col_idx: int, valor: str, tamano_pt: float | None = None):
    valor_limpio = re.sub(r"\s+", " ", str(valor).strip())
    if not valor_limpio:
        return

    celdas = row.cells
    if col_idx >= len(celdas):
        return

    cell = celdas[col_idx]

    parrafo_objetivo = None
    for p in cell.paragraphs:
        if re.search(r"_{2,}", p.text or ""):
            parrafo_objetivo = p
            break

    if parrafo_objetivo is not None:
        _escribir_contiguo_en_parrafo(parrafo_objetivo, valor_limpio, tamano_pt=tamano_pt)
        for p in list(cell.paragraphs):
            if p is not parrafo_objetivo:
                limpio = re.sub(r"[_\s/]+", "", p.text or "")
                if not limpio:
                    p._element.getparent().remove(p._element)
        return

    for next_c in range(col_idx + 1, min(col_idx + 4, len(celdas))):
        next_cell = celdas[next_c]
        if next_cell._tc is cell._tc:
            continue
        txt_next = re.sub(r"[_\s]+", "", next_cell.text or "")
        if not txt_next:
            p_next = next_cell.paragraphs[0] if next_cell.paragraphs else next_cell.add_paragraph()
            _escribir_contiguo_en_parrafo(p_next, valor_limpio, tamano_pt=tamano_pt)
            return

    p0 = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
    _escribir_contiguo_en_parrafo(p0, valor_limpio, tamano_pt=tamano_pt)


def _buscar_celda_por_texto(table, pistas: list[str], fila_minima: int = 0):
    pistas_lower = [p.lower() for p in pistas]
    for r_idx in range(fila_minima, len(table.rows)):
        row = table.rows[r_idx]
        for c_idx, cell in enumerate(row.cells):
            txt = " ".join(cell.text.lower().split())
            if any(p in txt for p in pistas_lower):
                return r_idx, c_idx, row
    return None


def generar_set4(
    datos: dict,
    nombre_archivo_salida: str = "SET_4_completada.docx",
    margen_v_cm: float = 0.45,
    margen_h_cm: float = 0.7,
    factor_alto_fila: float = 0.72,
    tamano_pt: float | None = None,
    tamano_aspectos_pt: float = 7.5,
    factor_alto_aspectos: float = 0.55,
) -> Path:
    if not RUTA_PLANTILLA.exists():
        raise FileNotFoundError(f"No se encontró la plantilla en: {RUTA_PLANTILLA}")

    doc = Document(str(RUTA_PLANTILLA))

    for seccion in doc.sections:
        if margen_v_cm is not None:
            seccion.top_margin = Cm(margen_v_cm)
            seccion.bottom_margin = Cm(margen_v_cm)
        if margen_h_cm is not None:
            seccion.left_margin = Cm(margen_h_cm)
            seccion.right_margin = Cm(margen_h_cm)

    for tabla in doc.tables:
        _ajustar_alturas_filas(tabla, factor_alto=factor_alto_fila)
        for fila in tabla.rows:
            _evitar_corte_fila(fila)

    t = doc.tables[0]

    asistencias = int(datos.get("asistencias", 0) or 0)
    enfermedad = int(datos.get("inasist_enfermedad", 0) or 0)
    privadas = int(datos.get("inasist_privadas", 0) or 0)
    otras = int(datos.get("inasist_otras", 0) or 0)
    injustificadas = int(datos.get("inasist_injustificadas", 0) or 0)
    suma_total = enfermedad + privadas + otras + injustificadas

    lugar_fecha = str(
        datos.get("lugar_fecha") or f"Chacabuco, {datetime.now().strftime('%d/%m/%Y')}"
    ).strip()

    campos_fijos = [
        (3, 14, datos.get("periodo", "")),
        (5, 14, datos.get("apellido_nombre", "")),
        (6, 14, datos.get("cargo_titular", "")),
        (6, 25, datos.get("escuela_num", "")),
        (6, 31, datos.get("distrito", "")),
        (7, 14, datos.get("cargo_actual", "")),
        (8, 14, datos.get("organismo", "")),
        (9, 14, datos.get("desde_fecha", "")),
        (10, 14, datos.get("titulos_docentes", "")),
        (11, 14, datos.get("otros_titulos", "")),
        (13, 14, datos.get("estudios_actuales", "")),
        (15, 14, datos.get("obras_publicadas", "")),
        (17, 14, datos.get("comisiones_oficiales", "")),
        (19, 14, datos.get("actos_culturales", "")),
        (21, 14, datos.get("iniciativa", "")),
        (23, 14, datos.get("perfeccionamiento", "")),
    ]

    for fila, col, valor in campos_fijos:
        if valor is not None and str(valor).strip() != "" and fila < len(t.rows):
            _escribir_contiguo_en_celda(t.rows[fila], col, str(valor).strip(), tamano_pt=tamano_pt)

    campos_dinamicos = [
        (["14- asistencias", "asistencias"], 20, str(asistencias), (27, 14)),
        (["por enfermedad", "enfermedad"], 20, str(enfermedad), (27, 24)),
        (["causas privadas", "privadas"], 20, str(privadas), (28, 24)),
        (["otras causas", "otras"], 20, str(otras), (29, 24)),
        (["injustificadas"], 20, str(injustificadas), (30, 24)),
        (["suma"], 20, str(suma_total), (31, 24)),
        (["lugar y fecha"], 0, lugar_fecha, (33, 14)),
    ]

    for pistas, fila_min, valor_str, respaldo in campos_dinamicos:
        encontrado = _buscar_celda_por_texto(t, pistas, fila_minima=fila_min)
        if encontrado:
            r_idx, c_idx, fila_obj = encontrado
            _escribir_contiguo_en_celda(fila_obj, c_idx, valor_str, tamano_pt=tamano_pt)
        else:
            r_b, c_b = respaldo
            if r_b < len(t.rows):
                _escribir_contiguo_en_celda(t.rows[r_b], c_b, valor_str, tamano_pt=tamano_pt)

    for tabla in doc.tables:
        _compactar_aspectos_a_considerar(
            tabla,
            tamano_aspectos_pt=tamano_aspectos_pt,
            factor_alto_aspectos=factor_alto_aspectos,
        )

    carpeta_salida = BASE_DIR / "salida"
    carpeta_salida.mkdir(parents=True, exist_ok=True)
    ruta_final = carpeta_salida / nombre_archivo_salida
    doc.save(str(ruta_final))
    return ruta_final


if __name__ == "__main__":
    datos_prueba = {
        "periodo": "01/03/2026 al 30/11/2026",
        "apellido_nombre": "Ejemplo Docente",
        "cargo_titular": "Prof. Ed. Física",
        "escuela_num": "8",
        "distrito": "Chacabuco",
        "cargo_actual": "Prof. Ed. Física",
        "organismo": "E.E.S. N° 8",
        "desde_fecha": "01/03/2025",
        "titulos_docentes": "Prof. de Educación Física",
        "otros_titulos": "RCP y DEA",
        "estudios_actuales": "Actualización docente",
        "obras_publicadas": "—",
        "comisiones_oficiales": "—",
        "actos_culturales": "Jornada deportiva",
        "iniciativa": "Juegos cooperativos",
        "perfeccionamiento": "Seminario DGCyE",
        "asistencias": 140,
        "inasist_enfermedad": 2,
        "inasist_privadas": 1,
        "inasist_otras": 0,
        "inasist_injustificadas": 0,
        "lugar_fecha": f"Chacabuco, {datetime.now().strftime('%d/%m/%Y')}",
    }

    archivo_generado = generar_set4(datos_prueba)
    print(f"Listo! Archivo generado en: {archivo_generado.resolve()}")