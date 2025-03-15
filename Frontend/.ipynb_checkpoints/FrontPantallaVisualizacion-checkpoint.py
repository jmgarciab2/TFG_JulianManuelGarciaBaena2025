import streamlit as st
import os
import pandas as pd
import requests
import json

# Rutas de archivos y carpetas
RUTA_CARPETA_CV = os.path.join("C:/Users", os.getlogin(), "Documents/TFG/Documentacion/Pruebas")
RUTA_ARCHIVO_PROFESIONES = "./Profesiones.csv"
ENDPOINT_PROCESAR_PDF = "http://127.0.0.1:5001/procesar_pdf"

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
            mostrar_respuesta_servidor(response)
    except FileNotFoundError:
        st.error(f"No se encontró el archivo: {ruta_cv}")

def mostrar_respuesta_servidor(response):
    """Muestra la respuesta del servidor en la interfaz de Streamlit."""
    if response.status_code == 200:
        st.success("CV y profesión enviados correctamente.")
    else:
        st.error(f"Error al enviar el CV: {response.status_code}")
    try:
        respuesta_json = response.json()
        st.write(respuesta_json)
    except json.JSONDecodeError:
        st.write("Respuesta del servidor no es un JSON válido.")
        st.write(response.text)

def main():
    """Función principal para ejecutar la aplicación Streamlit."""
    st.title("Procesamiento de Currículums Vitae (CVs)")
    nombres_cv = obtener_nombres_cv(RUTA_CARPETA_CV)
    profesiones = cargar_profesiones(RUTA_ARCHIVO_PROFESIONES)

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
                enviar_cv_y_profesion(nombre_cv_seleccionado, profesion_seleccionada)
    else:
        st.write("No se encontraron archivos CVs en la carpeta.")

if __name__ == "__main__":
    main()