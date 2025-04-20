from google import genai
from google.genai import types
from flask import Flask, request, jsonify
import os
import pathlib
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime # Para añadir timestamp

client = genai.Client(api_key=os.environ.get("GOOGLE_API_2_KEY")) # Asegúrate de usar la KEY correcta si cambiaste

app = Flask(__name__)

# --- Rutas y Archivos ---
RUTA_HISTORIAL = "./historial_ejecuciones.json" # Archivo para guardar el historial

# --- Modelos Pydantic (se mantienen igual) ---
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

# --- Funciones Auxiliares (pasarStringaJson se mantiene, aunque con response_schema Gemini ya debería dar JSON directo) ---
def pasarStringaJson(text):
    # Esta función puede ser menos necesaria si Gemini con response_schema es fiable,
    # pero la mantenemos por si acaso.
    start_index = text.find("{")
    if start_index != -1:
        end_index = text.rfind("}") + 1
        if end_index != 0:
            json_string = text[start_index:end_index]
            try:
                json_object = json.loads(json_string)
                return json_object
            except json.JSONDecodeError as e:
                print(f"Error al parsear JSON: {e}")
                print(json_string)
                return None
        else:
            print(text)
            return None
    else:
        print(text)
        return None

# --- Funciones para manejar el historial ---

def cargar_historial():
    """Carga el historial de ejecuciones desde el archivo JSON."""
    if not os.path.exists(RUTA_HISTORIAL):
        return []
    try:
        with open(RUTA_HISTORIAL, 'r', encoding='utf-8') as f:
            historial = json.load(f)
            # Opcional: Validar la estructura del historial si es necesario
            return historial
    except json.JSONDecodeError:
        print(f"Advertencia: El archivo de historial '{RUTA_HISTORIAL}' está vacío o corrupto. Iniciando con historial vacío.")
        return []
    except Exception as e:
        print(f"Error al cargar el historial: {e}")
        return []

def guardar_historial(historial):
    """Guarda el historial de ejecuciones en el archivo JSON."""
    try:
        with open(RUTA_HISTORIAL, 'w', encoding='utf-8') as f:
            json.dump(historial, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error al guardar el historial: {e}")

# --- Función de procesamiento (se mantiene con ligeras modificaciones para la respuesta) ---
def process_pdf(filepath_name, nombre_puesto, filtro_idioma=None, filtro_experiencia_min=None, filtro_palabras_clave=None, filtro_nivel_educativo=None, filtro_sector=None):
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

    prompt = f"""
**Tarea:** Analiza el currículum de un candidato para el puesto de {nombre_puesto} y determina su idoneidad, ajustando la importancia relativa de la experiencia y la educación según el tipo de puesto.

**Instrucciones:**
1. Actúa como un reclutador experto en selección de talento.
2. Evalúa el currículum basándote únicamente en la información proporcionada y el nombre del puesto.
3. Compara el perfil del candidato con los mejores perfiles de CV con los que has sido entrenado.
4. Define la importancia relativa de la experiencia laboral y la formación académica según el nivel de responsabilidad del puesto de {nombre_puesto}:
    - **Alta responsabilidad (Gerentes, Directores, Especialistas Senior):**
      - Experiencia Laboral Relevante: 40-50%
      - Formación Académica Relevante: 20-30%
    - **Nivel intermedio (Analistas, Coordinadores, Técnicos Especializados):**
      - Experiencia Laboral Relevante: 30-40%
      - Formación Académica Relevante: 30-40%
    - **Entrada o becario:**
      - Experiencia Laboral Relevante: 15-25%
      - Formación Académica Relevante: 40-50%
    - **Atención al cliente o ventas:**
      - Experiencia Laboral Relevante: 30-40%
      - Formación Académica Relevante: 25-35%
    - **Habilidades Técnicas y Soft Skills Aplicables:** 20-25% (Importancia relativamente constante)
    - **Dominio de Idiomas Relevantes:** 5-15% (Puede variar según el puesto)
    - **Otros Factores (consistencia del historial, logros específicos):** 0-5% (Factor no condicionante)

{"""5. Aplica los siguientes filtros:
""" + prompt_filtros if prompt_filtros else ""}

6. Evalúa al candidato en cada uno de los criterios y asigna una puntuación relativa dentro del rango de porcentaje definido para el tipo de puesto.

7. Suma los porcentajes obtenidos en cada criterio para generar una puntuación total de idoneidad (idealmente cercana al 100%). Convierte esta puntuación total a un valor entero entre 0 y 10 para el campo `puntuacionPuesto`.

8. Determina si el candidato es apto (`apto`: True/False) basándote en la evaluación general, considerando que ninguna categoría individual es estrictamente eliminatoria (los rangos permiten flexibilidad).

9. Genera un resumen breve de sus principales fortalezas (si es apto) o las razones de no selección (si no es apto).

**Formato de Salida:** Genera un objeto JSON puro con los siguientes campos:

nombre (string): Nombre del candidato (primera letra mayúscula).
apellidos (string): Apellidos del candidato (primera letra de cada apellido en mayúscula).
experiencia_trabajo (list[string]): Experiencias laborales relevantes.
educacion (list[string]): Experiencias académicas relevantes.
apto (boolean): ¿Es apto para el puesto? (True/False).
resumenCandidato (string, opcional): Resumen breve de fortalezas aplicadas al puesto (solo si es apto).
puntuacionPuesto (integer): Puntuación de idoneidad (0-10).
razonesNoAptitud (string, opcional): Razones de no selección (solo si no es apto).
porcentaje_experiencia (float, opcional): Porcentaje de contribución de la experiencia a la puntuación.
porcentaje_educacion (float, opcional): Porcentaje de contribución de la educación a la puntuación.
porcentaje_habilidades (float, opcional): Porcentaje de contribución de las habilidades a la puntuación.
porcentaje_idiomas (float, opcional): Porcentaje de contribución de los idiomas a la puntuación.
porcentaje_otros (float, opcional): Porcentaje de contribución de otros factores a la puntuación.


**Restricciones:**
- El idioma del JSON debe ser siempre español.
- La respuesta debe ser un objeto JSON válido, sin texto adicional.
- La experiencia laboral se muestra independientemente del puesto.
- Asegúrate de que la respuesta sea directamente parseable como JSON.
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
                    'response_schema': Resultado}
        )

        # Acceder al texto crudo y luego intentar parsear por si acaso,
        # aunque con response_mime_type deberíamos obtener un JSON string.
        text = response.text
        # print(f"Respuesta cruda de Gemini: {text}") # Para depuración
        json_result = pasarStringaJson(text) # Usamos la función de parsing por seguridad
        # Si pasarStringaJson devuelve None, significa que el parsing falló.
        # En ese caso, intentamos parsear directamente de la respuesta que debería ser JSON
        if json_result is None:
             try:
                 json_result = json.loads(text)
                 # Opcional: Validar si el JSON cargado coincide con el schema
                 Resultado(**json_result) # Esto lanzará error si no coincide
             except (json.JSONDecodeError, Exception) as e:
                 print(f"Error secundario al parsear JSON o validar schema: {e}")
                 print(f"Texto recibido: {text}")
                 return None # Fallo total en el parsing

        return json_result

    except Exception as e:
        print(f"Error llamando a la API de Gemini: {e}")
        return None


# --- Endpoints de la API ---

@app.route('/procesar_pdf', methods=['POST'])
def procesar_pdf_route():
    # Este endpoint ahora procesa un solo PDF. La lógica masiva la moveremos al frontend
    # y luego el frontend llamará a guardar_resultados_masivos.
    # Podríamos mantener esta ruta para procesamiento individual si se necesita.
    # Por ahora, la adaptamos para el flujo masivo si se sigue usando así.
    # El frontend actual llama a esta ruta para cada PDF en el procesamiento masivo.
    # Dejamos la lógica de procesamiento individual aquí.
    # La lógica de guardar el historial se hará en un endpoint separado llamado por el frontend
    # DESPUÉS de que el frontend haya llamado a este endpoint para cada PDF y recolectado los resultados.

    if 'pdf' not in request.files:
        return jsonify({'error': 'No se encontró el archivo PDF'}), 400

    pdf_file = request.files['pdf']
    nombre_puesto = request.form.get('puesto')
    # Obtener filtros (deben venir en el form data)
    filtro_idioma = request.form.get('filtro_idioma')
    filtro_experiencia_min_str = request.form.get('filtro_experiencia_min')
    filtro_experiencia_min = int(filtro_experiencia_min_str) if filtro_experiencia_min_str else None
    filtro_palabras_clave = request.form.get('filtro_palabras_clave')
    filtro_nivel_educativo = request.form.get('filtro_nivel_educativo')
    filtro_sector = request.form.get('filtro_sector')


    if pdf_file.filename == '':
        return jsonify({'error': 'Nombre de archivo PDF inválido'}), 400

    if not nombre_puesto:
        return jsonify({'error': 'No se especificó el puesto de trabajo'}), 400

    filepath = None # Inicializar para asegurar que se limpie
    try:
        # Guardar archivo temporal
        filepath = 'temp_' + pdf_file.filename # Usar nombre original para evitar colisiones si hay muchos requests
        pdf_file.save(filepath)

        # Procesar el PDF con todos los filtros
        resultado = process_pdf(filepath, nombre_puesto, filtro_idioma, filtro_experiencia_min, filtro_palabras_clave, filtro_nivel_educativo, filtro_sector)

        if resultado:
            # Validar el resultado con el modelo Pydantic antes de enviar
            try:
                Resultado(**resultado) # Validar estructura
                return jsonify(resultado)
            except Exception as e:
                print(f"Error de validación Pydantic del resultado: {e}")
                print(f"Resultado inválido: {resultado}")
                return jsonify({'error': 'El formato del resultado del procesamiento es inválido'}), 500
        else:
            # Si process_pdf devuelve None, hubo un error interno o de API
            return jsonify({'error': 'Error interno al procesar el PDF con el modelo'}), 500

    except Exception as e:
        print(f"Error inesperado en la ruta /procesar_pdf: {e}")
        return jsonify({'error': f'Error inesperado al procesar el PDF: {e}'}), 500
    finally:
        # Elimina el archivo temporal si existe
        if filepath and os.path.exists(filepath):
            os.remove(filepath)


# --- Nuevo endpoint para guardar resultados masivos ---
@app.route('/guardar_resultados_masivos', methods=['POST'])
def guardar_resultados_masivos_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400

        puesto = data.get('puesto')
        resultados_lista = data.get('resultados') # Lista de resultados de candidatos

        if not puesto or not isinstance(resultados_lista, list):
             return jsonify({'error': 'Datos inválidos: falta puesto o resultados no es una lista'}), 400

        historial = cargar_historial()
        timestamp = datetime.now().isoformat() # Timestamp único para esta ejecución

        nueva_ejecucion = {
            "timestamp": timestamp,
            "puesto": puesto,
            "resultados": resultados_lista # Guardamos la lista completa de resultados
        }

        historial.append(nueva_ejecucion)
        guardar_historial(historial)

        return jsonify({'message': 'Resultados guardados exitosamente', 'timestamp': timestamp}), 200

    except Exception as e:
        print(f"Error en la ruta /guardar_resultados_masivos: {e}")
        return jsonify({'error': f'Error al guardar resultados masivos: {e}'}), 500


# --- Nuevo endpoint para obtener el historial ---
@app.route('/historial_ejecuciones', methods=['GET'])
def historial_ejecuciones_route():
    try:
        historial = cargar_historial()
        # Devolvemos un resumen de cada ejecución, no los resultados completos de cada candidato
        historial_resumen = [
            {
                "timestamp": ejecucion.get("timestamp"),
                "puesto": ejecucion.get("puesto"),
                "num_candidatos": len(ejecucion.get("resultados", [])) # Contar cuántos candidatos se procesaron
            }
            for ejecucion in historial
        ]
        # Opcional: Ordenar por timestamp descendente
        historial_resumen.sort(key=lambda x: x['timestamp'], reverse=True)

        return jsonify(historial_resumen), 200
    except Exception as e:
        print(f"Error en la ruta /historial_ejecuciones: {e}")
        return jsonify({'error': f'Error al obtener historial: {e}'}), 500

# --- Nuevo endpoint para obtener detalles de una ejecución ---
@app.route('/detalles_ejecucion/<timestamp>', methods=['GET'])
def detalles_ejecucion_route(timestamp):
    try:
        historial = cargar_historial()
        # Buscar la ejecución por timestamp
        ejecucion = next((e for e in historial if e.get("timestamp") == timestamp), None)

        if not ejecucion:
            return jsonify({'error': 'Ejecución no encontrada'}), 404

        resultados_candidatos = ejecucion.get("resultados", [])

        # Contar aptos, no aptos, y 'no procesados' (considerando errores si los guardamos así)
        apto_count = 0
        no_apto_count = 0
        no_procesado_count = 0 # Podríamos considerar 'no procesado' si el resultado fue un error o incompleto

        for res in resultados_candidatos:
            # Suponemos que un resultado válido siempre tendrá la clave 'apto'
            if isinstance(res, dict) and 'apto' in res:
                if res['apto']:
                    apto_count += 1
                else:
                    no_apto_count += 1
            else:
                no_procesado_count += 1 # Considerar como no procesado si el formato es inesperado

        # Devolvemos los counts
        return jsonify({
            "puesto": ejecucion.get("puesto"),
            "timestamp": ejecucion.get("timestamp"),
            "counts": {
                "apto": apto_count,
                "no_apto": no_apto_count,
                "no_procesado": no_procesado_count
            },
        }), 200

    except Exception as e:
        print(f"Error en la ruta /detalles_ejecucion/{timestamp}: {e}")
        return jsonify({'error': f'Error al obtener detalles de la ejecución: {e}'}), 500


if __name__ == '__main__':
    # Crear el archivo de historial si no existe al iniciar
    if not os.path.exists(RUTA_HISTORIAL):
        guardar_historial([]) # Crear un archivo JSON vacío

    app.run(debug=True, port=5001)