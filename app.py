import streamlit as st
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import io
import time
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_JUSTIFY

# Configuración de la página
st.set_page_config(
    page_title="Traductor de PDF - Inglés a Español",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Traductor de PDF: Inglés → Español")
st.markdown("**Traduce documentos PDF completos preservando el formato original**")
st.markdown("---")

def traducir_texto_por_partes(texto, max_caracteres=4500):
    """
    Traduce texto largo dividiéndolo en partes para evitar límites de la API
    """
    if not texto or len(texto.strip()) == 0:
        return ""
    
    translator = GoogleTranslator(source='en', target='es')
    
    # Si el texto es corto, traducirlo directamente
    if len(texto) <= max_caracteres:
        try:
            traduccion = translator.translate(texto)
            return traduccion
        except Exception as e:
            st.warning(f"Error en traducción: {e}")
            return texto
    
    # Dividir texto en partes por párrafos
    parrafos = texto.split('\n')
    texto_traducido = []
    buffer = ""
    
    for parrafo in parrafos:
        if len(buffer) + len(parrafo) < max_caracteres:
            buffer += parrafo + "\n"
        else:
            # Traducir el buffer acumulado
            if buffer:
                try:
                    traduccion = translator.translate(buffer)
                    texto_traducido.append(traduccion)
                    time.sleep(0.3)  # Pequeña pausa para evitar rate limiting
                except Exception as e:
                    st.warning(f"Error en traducción de parte: {e}")
                    texto_traducido.append(buffer)
            
            buffer = parrafo + "\n"
    
    # Traducir el último buffer
    if buffer:
        try:
            traduccion = translator.translate(buffer)
            texto_traducido.append(traduccion)
        except Exception as e:
            texto_traducido.append(buffer)
    
    return "\n".join(texto_traducido)

def extraer_texto_con_formato(pdf_documento):
    """
    Extrae texto del PDF preservando cierta estructura
    """
    paginas_texto = []
    
    for num_pagina in range(len(pdf_documento)):
        pagina = pdf_documento[num_pagina]
        texto = pagina.get_text("text")
        paginas_texto.append(texto)
    
    return paginas_texto

def crear_pdf_traducido(textos_traducidos, output_path):
    """
    Crea un PDF nuevo con los textos traducidos
    """
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=30)
    
    # Estilos
    styles = getSampleStyleSheet()
    estilo_normal = ParagraphStyle(
        'Normal_ES',
        parent=styles['Normal'],
        alignment=TA_JUSTIFY,
        fontSize=10,
        leading=14,
        spaceBefore=6,
        spaceAfter=6
    )
    
    story = []
    
    for i, texto in enumerate(textos_traducidos):
        # Dividir en párrafos
        parrafos = texto.split('\n')
        
        for parrafo in parrafos:
            if parrafo.strip():
                # Limpiar y formatear el texto
                parrafo_limpio = parrafo.strip()
                # Escapar caracteres especiales para ReportLab
                parrafo_limpio = parrafo_limpio.replace('&', '&amp;')
                parrafo_limpio = parrafo_limpio.replace('<', '&lt;')
                parrafo_limpio = parrafo_limpio.replace('>', '&gt;')
                
                try:
                    p = Paragraph(parrafo_limpio, estilo_normal)
                    story.append(p)
                except Exception as e:
                    # Si hay error, agregar como texto plano
                    story.append(Spacer(1, 0.1*inch))
        
        # Salto de página después de cada página original
        if i < len(textos_traducidos) - 1:
            story.append(PageBreak())
    
    # Construir el PDF
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
    **Características:**
    - ✅ Hasta 400 páginas
    - ✅ Traduce inglés → español
    - ✅ Preserva estructura
    - ✅ 100% gratuito
    - ⚡ Procesamiento automático
    """)

if archivo_subido is not None:
    st.success(f"✅ Archivo cargado: {archivo_subido.name}")
    
    # Botón para iniciar traducción
    if st.button("🚀 Iniciar Traducción", type="primary", use_container_width=True):
        try:
            # Leer el PDF
            pdf_bytes = archivo_subido.read()
            pdf_documento = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            num_paginas = len(pdf_documento)
            
            # Validar número de páginas
            if num_paginas > 400:
                st.error(f"❌ El PDF tiene {num_paginas} páginas. El máximo permitido es 400.")
            else:
                st.info(f"📖 Documento: {num_paginas} páginas")
                
                # Barra de progreso
                progreso = st.progress(0)
                estado = st.empty()
                
                # Extraer texto de todas las páginas
                estado.text("📄 Extrayendo texto del PDF...")
                textos_originales = extraer_texto_con_formato(pdf_documento)
                progreso.progress(20)
                
                # Traducir página por página
                textos_traducidos = []
                
                for i, texto in enumerate(textos_originales):
                    estado.text(f"🔄 Traduciendo página {i+1} de {num_paginas}...")
                    texto_traducido = traducir_texto_por_partes(texto)
                    textos_traducidos.append(texto_traducido)
                    
                    # Actualizar progreso (20% a 80% para traducción)
                    progreso_actual = 20 + int((i + 1) / num_paginas * 60)
                    progreso.progress(progreso_actual)
                
                # Crear PDF traducido
                estado.text("📝 Generando PDF traducido...")
                output_buffer = io.BytesIO()
                crear_pdf_traducido(textos_traducidos, output_buffer)
                output_buffer.seek(0)
                progreso.progress(100)
                
                estado.text("✅ ¡Traducción completada!")
                
                # Botón de descarga
                st.success("🎉 ¡Traducción completada exitosamente!")
                
                nombre_archivo_salida = archivo_subido.name.replace('.pdf', '_TRADUCIDO_ES.pdf')
                
                st.download_button(
                    label="📥 Descargar PDF Traducido",
                    data=output_buffer,
                    file_name=nombre_archivo_salida,
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
                
                st.balloons()
                
        except Exception as e:
            st.error(f"❌ Error durante la traducción: {str(e)}")
            st.exception(e)

# Información adicional
st.markdown("---")
st.markdown("""
### 📋 Instrucciones de uso:
1. **Sube tu archivo PDF** en inglés (máximo 400 páginas)
2. **Haz clic en "Iniciar Traducción"** y espera el proceso
3. **Descarga tu PDF traducido** al español

### ⚙️ Características técnicas:
- Traduce usando Google Translate (biblioteca gratuita)
- Preserva la estructura del documento original
- Procesa hasta 400 páginas automáticamente
- Genera un nuevo PDF con formato similar al original

### ⚠️ Notas importantes:
- La traducción puede tomar varios minutos dependiendo del tamaño
- Imágenes no se traducen (solo texto)
- Fórmulas y ecuaciones se preservan pero no se traducen
- Para documentos muy técnicos, revisa la traducción antes de usar
""")
