###### CODIGO ORIGINAL             ######
###### Julian Manuel García Baena  ######
###### TFG CVisualizer Backend IA  ######
###### Convocatoria Ordinaria 2025 ######

from google import genai
from google.genai import types
from flask import Flask, request, jsonify
import os
import pathlib
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
# No importamos bcrypt ni nada de autenticación aquí

# Asegúrate de que esta clave API es válida para Google GenAI
# Se recomienda usar variables de entorno para las claves sensibles
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_2_KEY")
if not GOOGLE_API_KEY:
    print("Advertencia: La variable de entorno 'GOOGLE_API_2_KEY' no está configurada.")
    print("Por favor, configura GOOGLE_API_2_KEY con tu clave de API de Google.")
    # Si la clave no está configurada, el cliente de GenAI fallará.

try:
    client = genai.Client(api_key=GOOGLE_API_KEY)
    # Opcional: Una pequeña prueba para verificar la conexión
    # print("Conectado a la API de Google GenAI.")
except Exception as e:
    print(f"Error al inicializar el cliente de Google GenAI: {e}")
    print("La funcionalidad de procesamiento de CVs NO funcionará sin una clave de API válida.")
    client = None # Establecer cliente a None si falla la inicialización

app = Flask(__name__)

# --- Rutas y Archivos ---
# Archivo para guardar el historial de EJECUCIONES DE ANÁLISIS AI
RUTA_HISTORIAL = "./historial_ejecuciones.json"

# --- Modelos Pydantic ---
# Modelo para validar y estructurar la salida esperada de Gemini
class Resultado(BaseModel):
    nombre: str
    apellidos: str
    experiencia_trabajo: List[str]
    educacion: List[str]
    apto: bool
    resumenCandidato: Optional[str] = None
    puntuacionPuesto: int
    razonesNoAptitud: Optional[str] = None
    porcentaje_experiencia: Optional[float] = None
    porcentaje_educacion: Optional[float] = None
    porcentaje_habilidades: Optional[float] = None
    porcentaje_idiomas: Optional[float] = None
    porcentaje_otros: Optional[float] = None


# --- Funciones Auxiliares ---

# Función para parsear JSON incrustado (mantenida por robustez)
def pasarStringaJson(text):
    """Extrae y parsea un objeto JSON de una cadena de texto."""
    start_index = text.find("{")
    if start_index != -1:
        end_index = text.rfind("}") + 1
        if end_index > start_index: # Asegurar que la llave de cierre está después de la de apertura
            json_string = text[start_index:end_index]
            try:
                json_object = json.loads(json_string)
                return json_object
            except json.JSONDecodeError as e:
                print(f"Error al parsear JSON incrustado: {e}")
                print(f"Cadena a parsear: {json_string}")
                return None
        else:
            print(f"Advertencia: No se encontró una llave de cierre JSON válida en la cadena.")
            print(f"Texto recibido: {text}")
            return None
    else:
        print(f"Advertencia: No se encontró una llave de apertura JSON en la cadena.")
        print(f"Texto recibido: {text}")
        return None


# --- Funciones para manejar el historial de Análisis AI ---

def cargar_historial():
    """Carga el historial de ejecuciones de análisis desde el archivo JSON."""
    if not os.path.exists(RUTA_HISTORIAL):
        return [] # Si el archivo no existe, retorna una lista vacía
    try:
        with open(RUTA_HISTORIAL, 'r', encoding='utf-8') as f:
            historial = json.load(f)
            # Asegurarse de que es una lista
            return historial if isinstance(historial, list) else []
    except json.JSONDecodeError:
        print(f"Advertencia: El archivo de historial '{RUTA_HISTORIAL}' está vacío o corrupto. Iniciando con historial vacío.")
        return []
    except Exception as e:
        print(f"Error al cargar el historial: {e}")
        return []

def guardar_historial(historial):
    """Guarda el historial de ejecuciones de análisis en el archivo JSON."""
    try:
        # Asegurarse de que lo que se guarda es una lista
        if not isinstance(historial, list):
             print(f"Advertencia: Intentando guardar un historial que no es una lista. No se guardará.")
             return

        with open(RUTA_HISTORIAL, 'w', encoding='utf-8') as f:
            json.dump(historial, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error al guardar el historial: {e}")

# --- Función de procesamiento AI (MODIFICADA para aceptar pesos) ---
def process_pdf_ai(
    filepath_name,
    nombre_puesto,
    filtro_idioma=None,
    filtro_experiencia_min=None,
    filtro_palabras_clave=None,
    filtro_nivel_educativo=None,
    filtro_sector=None,
    # NUEVO: Pesos recibidos del frontend
    peso_experiencia=40,
    peso_educacion=30,
    peso_habilidades=20,
    peso_idiomas=5,
    peso_otros=5
):
    """
    Procesa un PDF usando Google Gemini con filtros y pesos de evaluación personalizables.
    Devuelve el resultado estructurado o None en caso de error.
    """
    if client is None:
        print("Error: Cliente de Google GenAI no inicializado. La API no está disponible.")
        return None

    file = pathlib.Path(filepath_name)
    pdf_bytes = file.read_bytes()

    # Construir el prompt dinámicamente con los filtros
    prompt_filtros = ""
    if filtro_idioma:
        prompt_filtros += f"- El idioma principal del candidato debe ser {filtro_idioma}.\n"
    if filtro_experiencia_min is not None:
        prompt_filtros += f"- Considera solo candidatos con al menos {filtro_experiencia_min} años de experiencia laboral total.\n"
    if filtro_palabras_clave:
        prompt_filtros += f"- Busca específicamente las siguientes palabras clave en el currículum: {filtro_palabras_clave}.\n"
    if filtro_nivel_educativo:
        prompt_filtros += f"- Prioriza candidatos con un nivel educativo igual o superior a {filtro_nivel_educativo}.\n"
    if filtro_sector:
        prompt_filtros += f"- Busca candidatos con experiencia laboral relevante en el sector de {filtro_sector}.\n"

    # Añadir los pesos personalizables al prompt
    # Instruir a la IA a usar estos pesos para la evaluación y la puntuación
    prompt_pesos_instruccion = f"""
**Instrucciones de Evaluación Adicionales:**
- Evalúa al candidato para el puesto de {nombre_puesto} basándote en los siguientes pesos relativos para cada criterio:
    - Experiencia Laboral Relevante: {peso_experiencia}%
    - Formación Académica Relevante: {peso_educacion}%
    - Habilidades Técnicas y Soft Skills Aplicables: {peso_habilidades}%
    - Dominio de Idiomas Relevantes: {peso_idiomas}%
    - Otros Factores (consistencia del historial, logros específicos): {peso_otros}%
- Utiliza estos pesos para guiar tu evaluación y la determinación de la puntuación de idoneidad (0-10) y la aptitud (True/False).
"""

    prompt = f"""
**Tarea:** Analiza el currículum de un candidato y determina su idoneidad para el puesto de {nombre_puesto}.

**Instrucciones Generales:**
1. Actúa como un reclutador experto en selección de talento.
2. Evalúa el currículum basándote únicamente en la información proporcionada en el documento.
3. Compara el perfil del candidato con los mejores perfiles de CV con los que has sido entrenado.

{prompt_pesos_instruccion}

{"""**Filtros Aplicados (Considerar durante la evaluación):**
""" + prompt_filtros if prompt_filtros else ""}

4. Basado en el análisis y los pesos proporcionados, evalúa al candidato en cada criterio.
5. Determina una puntuación total de idoneidad (0-10) que refleje la evaluación general según los pesos.
6. Determina si el candidato es apto (`apto`: True/False).
7. Genera un resumen o las razones de no selección.
8. **Estima** los porcentajes individuales de contribución de cada criterio al perfil general según tu evaluación y los pesos dados (campos: porcentaje_experiencia, etc.).

**Formato de Salida:** Genera un objeto JSON puro con los siguientes campos:

nombre (string): Nombre del candidato (primera letra mayúscula).
apellidos (string): Apellidos del candidato (primera letra de cada apellido en mayúscula).
experiencia_trabajo (list[string]): Experiencias laborales relevantes (resumen conciso de roles, empresas, etc.).
educacion (list[string]): Experiencias académicas relevantes (grados, instituciones, etc.).
apto (boolean): ¿Es apto para el puesto? (True/False).
resumenCandidato (string, opcional): Resumen breve de fortalezas aplicadas al puesto (solo si es apto).
puntuacionPuesto (integer): Puntuación de idoneidad general (0-10).
razonesNoAptitud (string, opcional): Razones de no selección (solo si no es apto).
porcentaje_experiencia (float, opcional): Porcentaje de contribución estimado de la experiencia.
porcentaje_educacion (float, opcional): Porcentaje de contribución estimado de la educación.
porcentaje_habilidades (float, opcional): Porcentaje de contribución estimado de las habilidades.
porcentaje_idiomas (float, opcional): Porcentaje de contribución estimado de los idiomas.
porcentaje_otros (float, opcional): Porcentaje de contribución estimado de otros factores.

**Restricciones:**
- El idioma del JSON debe ser siempre español.
- La respuesta debe ser un objeto JSON válido, sin texto adicional.
- La experiencia laboral y educación deben ser listas de strings con items concisos.
- Asegúrate de que la respuesta sea directamente parseable como JSON y cumpla con el schema.
"""

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[
                types.Part.from_bytes(
                    data=pdf_bytes,
                    mime_type='application/pdf',
                ),
                prompt
            ],
            # Usando response_mime_type y response_schema, Gemini debería devolver JSON directo
            config={'response_mime_type': 'application/json',
                    'response_schema': Resultado} # Usamos el schema Resultado
        )

        # Intentar obtener el texto crudo y parsearlo por seguridad,
        # aunque response_mime_type y response_schema deberían dar un JSON string.
        text = response.text
        # print(f"Respuesta cruda de Gemini: {text}") # Para depuración

        # Intenta parsear directamente o usando la función auxiliar si es necesario
        json_result = None
        try:
            json_result = json.loads(text)
            # Opcional: Validar si el JSON cargado coincide con el schema
            Resultado(**json_result) # Esto lanzará un error si no coincide con el modelo
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error al parsear JSON o validar schema de la respuesta de Gemini: {e}")
            print(f"Texto recibido: {text}")
            # Si falla el parsing directo, intenta con la función auxiliar (menos fiable)
            json_result = pasarStringaJson(text)
            if json_result:
                 try:
                     Resultado(**json_result) # Re-validar si el parsing auxiliar tuvo éxito
                 except Exception as e_validar_aux:
                     print(f"Fallo de validación después de parsing auxiliar: {e_validar_aux}")
                     return None # Fallo total
            else:
                return None # Fallo total en el parsing

        return json_result

    except Exception as e:
        print(f"Error llamando a la API de Gemini: {e}")
        # Considerar devolver un objeto de error estructurado para manejo en frontend
        # return {"error": f"API Error: {e}"}
        return None # Devolver None para indicar fallo en el procesamiento


# --- Endpoints de la API ---

# El endpoint /procesar_pdf es MODIFICADO para recibir los pesos
@app.route('/procesar_pdf', methods=['POST'])
def procesar_pdf_route():
    """
    Recibe un archivo PDF, puesto, filtros y pesos, y lo procesa usando AI.
    """
    if 'pdf' not in request.files:
        return jsonify({'error': 'No se encontró el archivo PDF'}), 400

    pdf_file = request.files['pdf']
    nombre_puesto = request.form.get('puesto')

    # Obtener filtros
    filtro_idioma = request.form.get('filtro_idioma')
    filtro_experiencia_min_str = request.form.get('filtro_experiencia_min')
    filtro_experiencia_min = int(filtro_experiencia_min_str) if filtro_experiencia_min_str and filtro_experiencia_min_str.isdigit() else None
    filtro_palabras_clave = request.form.get('filtro_palabras_clave')
    filtro_nivel_educativo = request.form.get('filtro_nivel_educativo')
    filtro_sector = request.form.get('filtro_sector')

    # NUEVO: Obtener pesos del formulario. Usar get con valor por defecto si no vienen o son inválidos
    def get_peso(key, default=0):
        value_str = request.form.get(key)
        if value_str is None or value_str == '':
            return default # Usa el valor por defecto si no se proporciona o está vacío
        try:
            # Intentar convertir a float primero para mayor flexibilidad
            return float(value_str)
        except ValueError:
            print(f"Advertencia: Peso inválido para {key}: '{value_str}'. Usando por defecto {default}.")
            return default # Usa el valor por defecto si no es un número válido

    peso_experiencia = get_peso('peso_experiencia', 35.0) # Usar float por defecto
    peso_educacion = get_peso('peso_educacion', 30.0)
    peso_habilidades = get_peso('peso_habilidades', 20.0)
    peso_idiomas = get_peso('peso_idiomas', 10.0)
    peso_otros = get_peso('peso_otros', 5.0)


    if pdf_file.filename == '':
        return jsonify({'error': 'Nombre de archivo PDF inválido'}), 400

    if not nombre_puesto:
        return jsonify({'error': 'No se especificó el puesto de trabajo'}), 400

    filepath = None
    try:
        # Guardar archivo temporal
        # Usar un nombre más robusto para el archivo temporal
        temp_filename = f"temp_cv_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{pdf_file.filename.replace(' ', '_').replace('/', '_').replace('\\', '_')}"
        filepath = os.path.join(pathlib.Path(__file__).parent, temp_filename) # Guardar en el directorio del script
        pdf_file.save(filepath)

        # Llamar a process_pdf_ai con todos los parámetros, incluyendo los pesos
        resultado = process_pdf_ai(
            filepath,
            nombre_puesto,
            filtro_idioma,
            filtro_experiencia_min,
            filtro_palabras_clave,
            filtro_nivel_educativo,
            filtro_sector,
            peso_experiencia, # Pasar los pesos
            peso_educacion,
            peso_habilidades,
            peso_idiomas,
            peso_otros
        )

        if resultado:
            # Validar el resultado con el modelo Pydantic antes de enviar al frontend
            try:
                return jsonify(resultado), 200
            except Exception as e:
                print(f"Error final de validación Pydantic del resultado: {e}")
                print(f"Resultado que falló la validación final: {resultado}")
                return jsonify({'error': 'El formato del resultado del procesamiento AI es inesperado'}), 500
        else:
            # process_pdf_ai devolvió None (error de API, parsing, etc.)
            print("El procesamiento AI devolvió None.")
            return jsonify({'error': 'Error interno o de API al procesar el PDF con AI'}), 500

    except Exception as e:
        print(f"Error inesperado en la ruta /procesar_pdf (antes de llamar a process_pdf_ai): {e}")
        return jsonify({'error': f'Error inesperado al procesar el PDF: {e}'}), 500
    finally:
        # Elimina el archivo temporal si existe
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError as e:
                 print(f"Advertencia: No se pudo eliminar el archivo temporal {filepath}: {e}")


# --- Endpoints relacionados con historial de Análisis AI ---
# Estos endpoints guardan y sirven el historial de los RESULTADOS DEL ANÁLISIS AI

@app.route('/guardar_resultados_masivos', methods=['POST'])
def guardar_resultados_masivos_route():
    """
    Recibe y guarda los resultados de un batch de procesamiento AI en el historial.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400

        puesto = data.get('puesto')
        resultados_lista = data.get('resultados') # Lista de resultados de candidatos (espera estructura Resultado)

        if not puesto or not isinstance(resultados_lista, list):
             return jsonify({'error': 'Datos inválidos: falta puesto o resultados no es una lista'}), 400

        historial = cargar_historial()
        # Usar ISO format para mayor precisión y facilidad de ordenamiento/parsing
        timestamp = datetime.now().isoformat()

        nueva_ejecucion = {
            "timestamp": timestamp,
            "puesto": puesto,
            "resultados": resultados_lista # Guardamos la lista completa de resultados (válidos)
        }

        historial.append(nueva_ejecucion)
        guardar_historial(historial)

        return jsonify({'message': 'Resultados guardados exitosamente en historial', 'timestamp': timestamp}), 200

    except Exception as e:
        print(f"Error en la ruta /guardar_resultados_masivos: {e}")
        return jsonify({'error': f'Error al guardar resultados masivos en historial: {e}'}), 500


@app.route('/historial_ejecuciones', methods=['GET'])
def historial_ejecuciones_route():
    """
    Devuelve un resumen del historial de ejecuciones de análisis.
    """
    try:
        historial = cargar_historial()
        # Devolvemos un resumen de cada ejecución, no los resultados completos de cada candidato
        historial_resumen = [
            {
                "timestamp": ejecucion.get("timestamp"),
                "puesto": ejecucion.get("puesto"),
                "num_candidatos": len(ejecucion.get("resultados", [])) # Contar cuántos candidatos se procesaron
                # Opcional: Incluir los pesos usados en el resumen si se guardaron
                # "pesos_usados": ejecucion.get("pesos_usados")
            }
            for ejecucion in historial
        ]
        # Ordenar por timestamp descendente
        historial_resumen.sort(key=lambda x: x.get('timestamp', ''), reverse=True) # Asegurar que timestamp existe para ordenar

        return jsonify(historial_resumen), 200
    except Exception as e:
        print(f"Error en la ruta /historial_ejecuciones: {e}")
        return jsonify({'error': f'Error al obtener historial: {e}'}), 500

@app.route('/detalles_ejecucion/<timestamp>', methods=['GET'])
def detalles_ejecucion_route(timestamp):
    """
    Devuelve los detalles (counts de aptos/no aptos/error) de una ejecución de análisis específica.
    """
    try:
        historial = cargar_historial()
        # Buscar la ejecución por timestamp
        ejecucion = next((e for e in historial if e.get("timestamp") == timestamp), None)

        if not ejecucion:
            return jsonify({'error': 'Ejecución no encontrada en historial'}), 404

        resultados_candidatos = ejecucion.get("resultados", [])

        # Contar aptos, no aptos, y 'no procesados' (considerando errores si los guardamos así)
        apto_count = 0
        no_apto_count = 0
        no_procesado_count = 0 # Consideraremos 'no procesado' si el resultado en la lista es un objeto de error o no tiene la clave 'apto'

        for res in resultados_candidatos:
            # Intentar validar con el modelo para seguridad, pero contar incluso si la estructura es solo un error
            if isinstance(res, dict):
                 if 'error' in res:
                      no_procesado_count += 1 # Contar como no procesado si es un objeto de error
                 elif 'apto' in res: # Si no es un error, esperamos la clave 'apto'
                     if res['apto']:
                         apto_count += 1
                     else:
                         no_apto_count += 1
                 else:
                      # Si es un diccionario pero no tiene 'apto' ni 'error', es inesperado
                      no_procesado_count += 1
                      print(f"Advertencia: Resultado en historial con formato inesperado (falta 'apto'): {res}")
            else:
                # Si no es un diccionario, es un formato inesperado en la lista de resultados guardada
                no_procesado_count += 1
                print(f"Advertencia: Elemento en historial no es un diccionario: {res}")


        # Devolvemos los counts
        return jsonify({
            "puesto": ejecucion.get("puesto"),
            "timestamp": ejecucion.get("timestamp"),
            "counts": {
                "apto": apto_count,
                "no_apto": no_apto_count,
                "no_procesado": no_procesado_count
            },
            # Opcional: Devolver también los pesos usados para esta ejecución
            # "pesos_usados": ejecucion.get("pesos_usados")
        }), 200

    except Exception as e:
        print(f"Error en la ruta /detalles_ejecucion/{timestamp}: {e}")
        return jsonify({'error': f'Error al obtener detalles de la ejecución del historial: {e}'}), 500


if __name__ == '__main__':
    # Crear el archivo de historial si no existe al iniciar
    # Asegurarse de que SOLO creas el archivo de historial aquí
    if not os.path.exists(RUTA_HISTORIAL):
        guardar_historial([])

    # NO crees el archivo de usuarios ni la carpeta de CVs recibidos manualmente aquí

    # Corre en el puerto principal (ej. 5001)
    print(f"Iniciando Backend Principal (Procesamiento CVs) en el puerto 5001...")
    app.run(debug=True, port=5001)