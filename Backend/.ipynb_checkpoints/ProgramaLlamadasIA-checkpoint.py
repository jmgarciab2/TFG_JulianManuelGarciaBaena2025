from google import genai
from google.genai import types
from flask import Flask, request, jsonify
import os
import pathlib
import json
from typing import List, Optional
from pydantic import BaseModel, Field

client = genai.Client(api_key="AIzaSyC2vz6Z8d7Q67M02SUS2tnkZzHa8S_P8vU")

class Resultado(BaseModel):
    nombre: str
    apellidos: str
    experiencia_trabajo: List[str]
    educacion: List[str]
    apto: bool
    resumenCandidato: Optional[str] = None
    puntuacionPuesto: int
    razonesNoAptitud: Optional[str] = None

# Doble verificacion de json
def pasarStringaJson(text):
    start_index = text.find("{")
    if start_index != -1:
        end_index = text.rfind("}") + 1
        if end_index != 0:
            json_string = text[start_index:end_index]
            try:
                json_object = json.loads(json_string)
                print(json.dumps(json_object, indent=2, ensure_ascii=False))
            except json.JSONDecodeError as e:
                print(f"Error al parsear JSON: {e}")
                print(json_string)
        else:
            print(text)
    else:
        print(text)

def process_pdf(filepath_name, nombre_puesto):
    file = pathlib.Path(filepath_name)
    pdf_bytes = file.read_bytes()
    prompt = f"""
        Actúa como un reclutador experto en selección de talento y analiza el currículum de un candidato para el puesto de {nombre_puesto}. El objetivo es determinar si el candidato cumple con los requisitos necesarios para el puesto, basándote únicamente en la información proporcionada en el currículum y el nombre del puesto.

        Proceso de Análisis:

        1.  Identificación de Requisitos:
            * Basándote en el nombre del puesto de {nombre_puesto}, identifica los requisitos clave que un candidato ideal debería cumplir.
            * Identificar segun el tipo de puesto al que se va a aplicar si es necesario identificar la experiencia academica.
            * En caso de que el puesto no requiera de estudios, observar las habilidades blandas, y la experiencia en el sector mas general del puesto de trabajo.
            * Considera tanto las habilidades técnicas como las habilidades blandas, la experiencia laboral, la formación académica y cualquier otro factor relevante.
            * Es necesario que el candidato posea una fuerte experiencia laboral para puestos de alta responsabilidad
        2.  Evaluación del Currículum:
            * Analiza el currículum del candidato para identificar la información relevante que se relaciona con los requisitos identificados.
            * Prioriza la experiencia laboral sobre la académica, pero considera ambos aspectos en tu evaluación, solo en el caso de que el puesto requiera experiencia.
            * Prioriza la experiencia academica sobre la laboral para puestos que requieran un grado de responsabilidad baja, en gran medida.
            * Evalúa la relevancia de cada experiencia, habilidad y formación para el puesto de {nombre_puesto}.
        3.  Resumen y Evaluación Final:
            * Si el candidato cumple con los requisitos necesarios, genera un resumen breve de sus principales fortalezas y logros, destacando su idoneidad para el puesto.
            * Si el candidato no cumple con los requisitos necesarios, explica las razones de manera clara y concisa.
            * Asigna una puntuación del 0 al 10 para la idoneidad del candidato.

        * Tener en cuenta que si el puesto de trabajo esta dedicado o relacionado con el ambito de atencion al cliente, es necesario evaluar las habilidades del candidato para poder emplear el analisis debido

        Formato de Salida JSON:

        Genera un objeto JSON puro con los siguientes campos, sin texto adicional antes o después del JSON:

        nombre (string): Nombre del candidato.
        apellidos (string): Apellidos del candidato.
        experiencia_trabajo (list[string]): Lista de experiencias laborales relevantes.
        educacion (list[string]): Lista de experiencias académicas relevantes.
        apto (boolean): Indica si el candidato es apto para el puesto (True/False).
        resumenCandidato (string): Un resumen breve de las fortalezas del candidato (solo si es apto).
        puntuacionPuesto (integer): Puntuación del 0 al 10 para la idoneidad del candidato.
        razonesNoAptitud (string): Razones por las que no se le ha seleccionado para el puesto (solo si no es apto) indicar tambien si no existen soft skills que complementen al puesto de trabajo.

        Requisitos Adicionales:

        Las razones de no aptitud se muestran en el JSON solo si el candidato no es apto.
        El idioma del JSON debe ser siempre español.
        La respuesta debe ser un objeto JSON válido, sin texto adicional.
        La experiencia laboral se debe de mostrar independientemente del puesto al que aplica.
        Asegúrate de que la respuesta se pueda analizar directamente como JSON.
    """

    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=[
            types.Part.from_bytes(
                data=pdf_bytes,
                mime_type='application/pdf',
            ),
            prompt
        ],
        config={'response_mime_type': 'application/json',
                'response_schema': Resultado}
    )

    text = response.text
    pasarStringaJson(text)
    
