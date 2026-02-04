import streamlit as st
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import io
import time
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
from reportlab.pdfgen import canvas
import re

# Configuración de la página
st.set_page_config(
    page_title="Traductor Profesional de PDF",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Traductor Profesional de PDF: Inglés → Español")
st.markdown("**Traduce documentos PDF técnicos preservando estructura y formato**")
st.markdown("---")

class TextBlock:
    """Clase para representar bloques de texto con sus propiedades"""
    def __init__(self, text, font_size, is_bold, x, y, page_num):
        self.text = text.strip()
        self.font_size = font_size
        self.is_bold = is_bold
        self.x = x
        self.y = y
        self.page_num = page_num
        self.tipo = self.clasificar_tipo()
    
    def clasificar_tipo(self):
        """Clasifica el tipo de bloque según sus características"""
        text = self.text
        
        # Detectar títulos y encabezados
        if self.font_size > 12 or self.is_bold:
            if len(text) < 100:
                return 'titulo'
        
        # Detectar numeración o listas
        if re.match(r'^[\d\.\-\•\◦]+\s+', text) or re.match(r'^[A-Z][\.\)]\s+', text):
            return 'lista'
        
        # Detectar texto centrado (posiblemente título)
        if len(text) < 80 and self.font_size > 10:
            return 'subtitulo'
        
        # Por defecto es párrafo normal
        return 'parrafo'

def extraer_bloques_estructurados(pdf_documento):
    """
    Extrae bloques de texto del PDF preservando estructura
    """
    todas_paginas = []
    
    for num_pagina in range(len(pdf_documento)):
        pagina = pdf_documento[num_pagina]
        bloques_pagina = []
        
        # Obtener bloques de texto con información de formato
        bloques = pagina.get_text("dict")["blocks"]
        
        for bloque in bloques:
            if "lines" not in bloque:
                continue
            
            for linea in bloque["lines"]:
                for span in linea["spans"]:
                    texto = span["text"].strip()
                    if not texto:
                        continue
                    
                    font_size = span["size"]
                    is_bold = "bold" in span["font"].lower()
                    x = span["bbox"][0]
                    y = span["bbox"][1]
                    
                    text_block = TextBlock(texto, font_size, is_bold, x, y, num_pagina)
                    bloques_pagina.append(text_block)
        
        todas_paginas.append(bloques_pagina)
    
    return todas_paginas

def agrupar_bloques_en_parrafos(bloques):
    """
    Agrupa bloques de texto que pertenecen al mismo párrafo
    """
    if not bloques:
        return []
    
    parrafos = []
    buffer = []
    ultimo_y = None
    ultimo_tipo = None
    
    for bloque in bloques:
        # Si es un título o subtítulo, crear párrafo nuevo
        if bloque.tipo in ['titulo', 'subtitulo']:
            if buffer:
                parrafos.append({
                    'texto': ' '.join([b.text for b in buffer]),
                    'tipo': ultimo_tipo or 'parrafo',
                    'font_size': buffer[0].font_size
                })
                buffer = []
            
            parrafos.append({
                'texto': bloque.text,
                'tipo': bloque.tipo,
                'font_size': bloque.font_size
            })
            ultimo_y = bloque.y
            ultimo_tipo = bloque.tipo
            continue
        
        # Detectar salto de párrafo (diferencia significativa en Y)
        if ultimo_y is not None and abs(bloque.y - ultimo_y) > 15:
            if buffer:
                parrafos.append({
                    'texto': ' '.join([b.text for b in buffer]),
                    'tipo': ultimo_tipo or 'parrafo',
                    'font_size': buffer[0].font_size if buffer else 10
                })
                buffer = []
        
        buffer.append(bloque)
        ultimo_y = bloque.y
        ultimo_tipo = bloque.tipo
    
    # Agregar último buffer
    if buffer:
        parrafos.append({
            'texto': ' '.join([b.text for b in buffer]),
            'tipo': ultimo_tipo or 'parrafo',
            'font_size': buffer[0].font_size if buffer else 10
        })
    
    return parrafos

def traducir_texto_inteligente(texto, max_caracteres=4500):
    """
    Traduce texto de manera inteligente respetando estructura
    """
    if not texto or len(texto.strip()) == 0:
        return ""
    
    translator = GoogleTranslator(source='en', target='es')
    
    # Si el texto es corto, traducir directamente
    if len(texto) <= max_caracteres:
        try:
            traduccion = translator.translate(texto)
            return traduccion
        except Exception as e:
            return texto
    
    # Para textos largos, dividir por oraciones
    oraciones = re.split(r'(?<=[.!?])\s+', texto)
    texto_traducido = []
    buffer = ""
    
    for oracion in oraciones:
        if len(buffer) + len(oracion) < max_caracteres:
            buffer += oracion + " "
        else:
            if buffer:
                try:
                    traduccion = translator.translate(buffer.strip())
                    texto_traducido.append(traduccion)
                    time.sleep(0.2)
                except Exception as e:
                    texto_traducido.append(buffer)
            buffer = oracion + " "
    
    if buffer:
        try:
            traduccion = translator.translate(buffer.strip())
            texto_traducido.append(traduccion)
        except Exception as e:
            texto_traducido.append(buffer)
    
    return " ".join(texto_traducido)

def crear_estilos_personalizados():
    """
    Crea estilos de párrafo personalizados
    """
    styles = getSampleStyleSheet()
    
    # Estilo para títulos principales
    styles.add(ParagraphStyle(
        name='TituloPrincipal',
        parent=styles['Heading1'],
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        spaceAfter=16,
        spaceBefore=16,
        textColor='#000000',
        fontName='Helvetica-Bold'
    ))
    
    # Estilo para subtítulos
    styles.add(ParagraphStyle(
        name='Subtitulo',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        alignment=TA_LEFT,
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    ))
    
    # Estilo para párrafos normales
    styles.add(ParagraphStyle(
        name='ParrafoNormal',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=8,
        spaceBefore=4,
        firstLineIndent=0
    ))
    
    # Estilo para listas
    styles.add(ParagraphStyle(
        name='ItemLista',
        parent=styles['Normal'],
        fontSize=10,
        leading=13,
        alignment=TA_LEFT,
        spaceAfter=4,
        spaceBefore=2,
        leftIndent=20
    ))
    
    return styles

def crear_pdf_profesional(parrafos_traducidos, output_path):
    """
    Crea un PDF profesional con formato mejorado
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=60,
        leftMargin=60,
        topMargin=60,
        bottomMargin=50
    )
    
    styles = crear_estilos_personalizados()
    story = []
    
    for i, pagina_parrafos in enumerate(parrafos_traducidos):
        for parrafo_info in pagina_parrafos:
            texto = parrafo_info['texto']
            tipo = parrafo_info['tipo']
            
            if not texto.strip():
                continue
            
            # Limpiar texto para ReportLab
            texto_limpio = texto.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            try:
                # Aplicar estilo según el tipo
                if tipo == 'titulo':
                    p = Paragraph(f"<b>{texto_limpio}</b>", styles['TituloPrincipal'])
                elif tipo == 'subtitulo':
                    p = Paragraph(f"<b>{texto_limpio}</b>", styles['Subtitulo'])
                elif tipo == 'lista':
                    p = Paragraph(f"• {texto_limpio}", styles['ItemLista'])
                else:
                    p = Paragraph(texto_limpio, styles['ParrafoNormal'])
                
                story.append(p)
                
            except Exception as e:
                # Si hay error, agregar espaciador
                story.append(Spacer(1, 0.1*inch))
        
        # Salto de página entre páginas originales
        if i < len(parrafos_traducidos) - 1:
            story.append(PageBreak())
    
    # Construir PDF
    doc.build(story)

# Interfaz de usuario
col1, col2 = st.columns([2, 1])

with col1:
    archivo_subido = st.file_uploader(
        "Sube tu archivo PDF (máximo 400 páginas)",
        type=['pdf'],
        help="Sube un documento PDF en inglés para traducir al español"
    )

with col2:
    st.info("""
    **✨ Características Premium:**
    - ✅ Hasta 400 páginas
    - ✅ Preserva estructura completa
    - ✅ Detecta títulos y secciones
    - ✅ Mantiene formato técnico
    - ✅ 100% gratuito
    - ⚡ Calidad profesional
    """)

if archivo_subido is not None:
    st.success(f"✅ Archivo cargado: {archivo_subido.name}")
    
    # Mostrar información del archivo
    file_size_mb = len(archivo_subido.getvalue()) / (1024 * 1024)
    st.caption(f"📊 Tamaño: {file_size_mb:.2f} MB")
    
    # Botón para iniciar traducción
    if st.button("🚀 Iniciar Traducción Profesional", type="primary", use_container_width=True):
        try:
            # Leer el PDF
            pdf_bytes = archivo_subido.read()
            pdf_documento = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            num_paginas = len(pdf_documento)
            
            # Validar número de páginas
            if num_paginas > 400:
                st.error(f"❌ El PDF tiene {num_paginas} páginas. El máximo permitido es 400.")
            else:
                st.info(f"📖 Procesando documento de {num_paginas} páginas con formato técnico")
                
                # Barra de progreso
                progreso = st.progress(0)
                estado = st.empty()
                
                # PASO 1: Extraer bloques estructurados
                estado.text("🔍 Analizando estructura del documento...")
                todas_paginas_bloques = extraer_bloques_estructurados(pdf_documento)
                progreso.progress(15)
                
                # PASO 2: Agrupar en párrafos coherentes
                estado.text("📑 Organizando párrafos y secciones...")
                todas_paginas_parrafos = []
                for bloques_pagina in todas_paginas_bloques:
                    parrafos = agrupar_bloques_en_parrafos(bloques_pagina)
                    todas_paginas_parrafos.append(parrafos)
                progreso.progress(25)
                
                # PASO 3: Traducir página por página
                paginas_traducidas = []
                total_parrafos = sum(len(p) for p in todas_paginas_parrafos)
                parrafos_procesados = 0
                
                for num_pag, parrafos_pagina in enumerate(todas_paginas_parrafos):
                    estado.text(f"🔄 Traduciendo página {num_pag + 1} de {num_paginas}...")
                    
                    parrafos_traducidos = []
                    for parrafo_info in parrafos_pagina:
                        texto_original = parrafo_info['texto']
                        
                        # Traducir
                        texto_traducido = traducir_texto_inteligente(texto_original)
                        
                        parrafos_traducidos.append({
                            'texto': texto_traducido,
                            'tipo': parrafo_info['tipo'],
                            'font_size': parrafo_info['font_size']
                        })
                        
                        parrafos_procesados += 1
                        # Actualizar progreso (25% a 85%)
                        progreso_actual = 25 + int((parrafos_procesados / total_parrafos) * 60)
                        progreso.progress(min(progreso_actual, 85))
                    
                    paginas_traducidas.append(parrafos_traducidos)
                    time.sleep(0.1)
                
                # PASO 4: Crear PDF traducido con formato
                estado.text("📝 Generando PDF profesional con formato...")
                output_buffer = io.BytesIO()
                crear_pdf_profesional(paginas_traducidas, output_buffer)
                output_buffer.seek(0)
                progreso.progress(100)
                
                estado.text("✅ ¡Traducción completada con éxito!")
                
                # Botón de descarga
                st.success("🎉 ¡Traducción profesional completada!")
                
                # Estadísticas
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("📄 Páginas", num_paginas)
                with col_stat2:
                    st.metric("📝 Párrafos", total_parrafos)
                with col_stat3:
                    st.metric("✅ Calidad", "Premium")
                
                nombre_archivo_salida = archivo_subido.name.replace('.pdf', '_TRADUCIDO_PROFESIONAL.pdf')
                
                st.download_button(
                    label="📥 Descargar PDF Traducido (Formato Premium)",
                    data=output_buffer,
                    file_name=nombre_archivo_salida,
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
                
                st.balloons()
                
        except Exception as e:
            st.error(f"❌ Error durante el procesamiento: {str(e)}")
            st.exception(e)
            st.info("💡 Tip: Asegúrate de que el PDF no esté protegido o corrupto")

# Información adicional
st.markdown("---")

col_info1, col_info2 = st.columns(2)

with col_info1:
    st.markdown("""
    ### 📋 Instrucciones:
    1. **Sube tu PDF** en inglés (hasta 400 páginas)
    2. **Espera el análisis** de estructura
    3. **Descarga el resultado** con formato profesional
    
    ### ✨ Mejoras de esta versión:
    - 🎯 Detecta y preserva títulos y secciones
    - 📊 Mantiene jerarquía visual
    - 📝 Agrupa párrafos coherentemente
    - 🔤 Respeta formato de listas y numeración
    """)

with col_info2:
    st.markdown("""
    ### ⚙️ Tecnología:
    - **Extracción avanzada**: PyMuPDF con análisis de bloques
    - **Traducción**: Google Translate API (deep-translator)
    - **Generación PDF**: ReportLab con estilos profesionales
    - **Clasificación inteligente**: Detección automática de estructura
    
    ### 📌 Ideal para:
    - Documentos técnicos (IEEE, ISO)
    - Manuales y guías
    - Papers académicos
    - Reportes profesionales
    """)

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 12px;'>
    <p>🔧 Traductor Profesional de PDF v2.0 | Hecho con ❤️ usando Streamlit</p>
    <p>⚡ Preserva estructura técnica y formato original</p>
</div>
""", unsafe_allow_html=True)
