import streamlit as st
import os
import pandas as pd
import requests
import json

# Configuración de la página
st.set_page_config(page_title="CVisualizer", page_icon="")

# Rutas de archivos y carpetas
RUTA_CARPETA_CV = os.path.join("C:/Users", os.getlogin(), "Documents/TFG/Documentacion/Pruebas")
RUTA_ARCHIVO_PROFESIONES = "./Profesiones.csv"
ENDPOINT_PROCESAR_PDF = "http://127.0.0.1:5001/procesar_pdf"

# Estilos personalizados (sin cambios)
st.markdown(
    """
    <style>
    body {
        background-color: #f4f4f4;
        color: #333;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin: 0;
    }
    .stApp {
        max-width: 100%;
        margin: 0;
        padding: 20px;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        padding: 10px 20px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
    }
    .stTextInput>div>div>input {
        border: 1px solid #ccc;
        border-radius: 5px;
        padding: 8px;
    }
    .stSelectbox>div>div>div>div {
        border: 1px solid #ccc;
        border-radius: 5px;
    }
    .info-box {
        border: 1px solid #ccc;
        padding: 10px;
        margin-bottom: 10px;
        border-radius: 5px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def obtener_nombres_cv(ruta_carpeta):
    """Obtiene una lista de nombres de archivos CVs desde la carpeta especificada."""
    try:
        archivos = os.listdir(ruta_carpeta)
        return [archivo for archivo in archivos if archivo.lower().endswith(".pdf")]
    except FileNotFoundError:
        st.error(f"No se encontró la carpeta: {ruta_carpeta}")
        return []

def cargar_profesiones(ruta_archivo):
    """Carga las profesiones desde el archivo CSV."""
    try:
        df = pd.read_csv(ruta_archivo)
        return df["Profesion"].tolist()
    except FileNotFoundError:
        return []

def guardar_profesiones(ruta_archivo, profesiones):
    """Guarda las profesiones en el archivo CSV."""
    df = pd.DataFrame({"Profesion": profesiones})
    df.to_csv(ruta_archivo, index=False)

def agregar_nueva_profesion(nueva_profesion, profesiones):
    """Agrega una nueva profesión a la lista y guarda los cambios."""
    if nueva_profesion:
        profesiones.append(nueva_profesion)
        guardar_profesiones(RUTA_ARCHIVO_PROFESIONES, profesiones)
        st.success(f"Profesión '{nueva_profesion}' añadida correctamente.")
        st.rerun()  # Forzar la actualización de la lista desplegable
    else:
        st.warning("Por favor, introduce una profesión.")

def enviar_cv_y_profesion(nombre_cv, profesion):
    """Envía el CV y la profesión al endpoint para procesamiento."""
    ruta_cv = os.path.join(RUTA_CARPETA_CV, nombre_cv)
    try:
        with open(ruta_cv, "rb") as archivo_pdf:
            files = {"pdf": (nombre_cv, archivo_pdf, "application/pdf")}
            data = {"puesto": profesion}
            response = requests.post(ENDPOINT_PROCESAR_PDF, files=files, data=data)
            return response
    except FileNotFoundError:
        st.error(f"No se encontró el archivo: {ruta_cv}")
        return None

def mostrar_respuesta_servidor(response):
    """Muestra la respuesta del servidor en recuadros."""
    if response and response.status_code == 200:
        try:
            respuesta_json = response.json()
            nombre = respuesta_json.get("nombre", "Nombre no encontrado")
            apellidos = respuesta_json.get("apellidos", "Apellidos no encontrados")
            apto = respuesta_json.get("apto", False)
            resumen_candidato = respuesta_json.get("resumenCandidato", "")
            razones_no_aptitud = respuesta_json.get("razonesNoAptitud", "")

            if apto:
                indicador_aptitud = "🟢 Apto"
                resumen = resumen_candidato
            else:
                indicador_aptitud = " No apto"
                resumen = razones_no_aptitud

            st.success("CV y profesión enviados correctamente.")

            st.markdown(f'<div class="info-box"><strong>Nombre:</strong> {nombre} {apellidos}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="info-box"><strong>Aptitud:</strong> {indicador_aptitud}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="info-box"><strong>Resumen:</strong> {resumen}</div>', unsafe_allow_html=True)

        except json.JSONDecodeError:
            st.error("Respuesta del servidor no es un JSON válido.")
            st.write(response.text)
        except KeyError as e:
            st.error(f"Error al acceder a la clave: {e}")
        except TypeError as e:
            st.error(f"Error de tipo de datos: {e}")
    elif response:
        st.error(f"Error al enviar el CV: {response.status_code}")
        st.write(response.text)

def procesar_cvs_masivamente(nombres_cv, profesion):
    """Procesa todos los CVs en la carpeta y devuelve los resultados."""
    resultados = []
    for nombre_cv in nombres_cv:
        response = enviar_cv_y_profesion(nombre_cv, profesion)
        if response and response.status_code == 200:
            try:
                respuesta_json = response.json()
                nombre = respuesta_json.get("nombre", "Nombre no encontrado")
                apellidos = respuesta_json.get("apellidos", "Apellidos no encontrados")
                apto = respuesta_json.get("apto", False)
                resultados.append({"nombre_completo": f"{nombre} {apellidos}", "apto": "🟢 Apto" if apto else " No apto", "respuesta_json": respuesta_json})
            except json.JSONDecodeError:
                st.error(f"Error al procesar {nombre_cv}: Respuesta del servidor no es un JSON válido.")
            except KeyError as e:
                st.error(f"Error al procesar {nombre_cv}: Error al acceder a la clave: {e}")
            except TypeError as e:
                st.error(f"Error al procesar {nombre_cv}: Error de tipo de datos: {e}")
        else:
            st.error(f"Error al procesar {nombre_cv}: Error al enviar el CV.")
    return resultados

def main():
    """Función principal para ejecutar la aplicación Streamlit."""
    st.title("CVisualizer")
    nombres_cv = obtener_nombres_cv(RUTA_CARPETA_CV)
    profesiones = cargar_profesiones(RUTA_ARCHIVO_PROFESIONES)

    # Barra lateral para seleccionar la pantalla
    pantalla = st.sidebar.radio("Seleccionar Pantalla", ("Procesador de CVs Individual", "Procesador de CVs Masivo"))

    if pantalla == "Procesador de CVs Individual":
        if nombres_cv:
            nombre_cv_seleccionado = st.selectbox("Seleccionar CV", nombres_cv)
            st.write(f"CV seleccionado: {nombre_cv_seleccionado}")
            profesion_seleccionada = st.selectbox("Seleccionar Profesión", ["Otro"] + profesiones)

            if profesion_seleccionada == "Otro":
                nueva_profesion = st.text_input("Nueva Profesión")
                if st.button("Añadir Profesión"):
                    agregar_nueva_profesion(nueva_profesion, profesiones)
            else:
                st.write(f"Profesión seleccionada: {profesion_seleccionada}")
                if st.button("Enviar CV y Profesión"):
                    response = enviar_cv_y_profesion(nombre_cv_seleccionado, profesion_seleccionada)
                    mostrar_respuesta_servidor(response)
        else:
            st.write("No se encontraron archivos CVs en la carpeta.")
    else:  # Procesador de CVs Masivo
        if nombres_cv:
            profesion_masiva = st.selectbox("Seleccionar Profesión para Procesamiento Masivo", ["Otro"] + profesiones)

            if profesion_masiva == "Otro":
                nueva_profesion_masiva = st.text_input("Nueva Profesión para Procesamiento Masivo")
                if st.button("Añadir Profesión Masiva"):
                    agregar_nueva_profesion(nueva_profesion_masiva, profesiones)
            else:
                if st.button("Procesar CVs Masivamente"):
                    resultados = procesar_cvs_masivamente(nombres_cv, profesion_masiva)
                    if resultados:
                        df_resultados = pd.DataFrame(resultados, columns=["nombre_completo", "apto", "respuesta_json"])
                        st.dataframe(df_resultados[["nombre_completo", "apto"]])
        else:
            st.write("No se encontraron archivos CVs en la carpeta.")

if __name__ == "__main__":
    main()