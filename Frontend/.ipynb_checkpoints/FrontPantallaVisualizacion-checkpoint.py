import streamlit as st
import os
import pandas as pd
import requests
import json
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode
import plotly.express as px
from datetime import datetime
# Nota: bcrypt no es necesario en el frontend

# Configuración de la página principal
st.set_page_config(page_title="CVisualizer", page_icon="")

# --- Rutas de Archivos y Endpoints ---
RUTA_CARPETA_CV = os.path.join("C:/Users", os.getlogin(), "Documents/TFG/Documentacion/Pruebas")
RUTA_ARCHIVO_PROFESIONES = "./Profesiones.csv"
# Endpoint del backend principal (procesamiento de CVs) - Asumimos puerto 5001
BACKEND_CV_URL = "http://127.0.0.1:5001"
ENDPOINT_PROCESAR_PDF = f"{BACKEND_CV_URL}/procesar_pdf"
# Endpoint para guardar historial (si usas el backend con historial)
# Si estás usando el backend manual (solo guarda archivos), estos endpoints ya no existen o devuelven error 501
ENDPOINT_GUARDAR_HISTORIAL = f"{BACKEND_CV_URL}/guardar_resultados_masivos"
ENDPOINT_HISTORIAL_EJECUCIONES = f"{BACKEND_CV_URL}/historial_ejecuciones"
ENDPOINT_DETALLES_EJECUCION = f"{BACKEND_CV_URL}/detalles_ejecucion"


# Endpoint del backend de autenticación - ASEGÚRATE que este puerto coincide con auth_backend.py
AUTH_BACKEND_URL = "http://127.0.0.1:5002" # <--- PUERTO DEL BACKEND DE AUTENTICACIÓN
ENDPOINT_REGISTER = f"{AUTH_BACKEND_URL}/register"
ENDPOINT_LOGIN = f"{AUTH_BACKEND_URL}/login"

# --- Estilos personalizados ---
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
        padding: 5px 10px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        font-size: 0.9em;
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
    /* Estilo para el botón 'Ver Detalles' en AgGrid */
    .ag-cell-content {
        text-align: center; /* Centra el contenido de la celda si lo deseas */
    }
    .ag-cell-content button {
        background-color: #008CBA; /* Un color azul para diferenciar */
        color: white;
        padding: 3px 8px;
        border: none;
        border-radius: 3px;
        cursor: pointer;
        font-size: 0.8em;
    }
     /* Estilo para el selectbox del historial */
    .stSelectbox > label {
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Inicializar el estado de sesión para la autenticación y la vista ---
# Esto es clave para mantener el estado a través de reruns
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'company' not in st.session_state:
    st.session_state['company'] = None
if 'auth_view' not in st.session_state: # 'login' o 'register'
    st.session_state['auth_view'] = 'login'
if 'auth_message' not in st.session_state: # Mensaje de feedback para login/register
    st.session_state['auth_message'] = None


# --- Funciones para llamar a la API del Backend de Autenticación ---
# Adaptadas para usar el estado de sesión de este script

def call_register_api(username, password, company):
    """Llama al endpoint de registro del backend de autenticación."""
    st.session_state['auth_message'] = None # Limpiar mensaje anterior
    try:
        response = requests.post(ENDPOINT_REGISTER, json={
            "username": username,
            "password": password,
            "company": company
        })
        if response.status_code == 201:
            st.session_state['auth_message'] = {"text": "Usuario registrado exitosamente. Ahora puedes iniciar sesión.", "type": "success"}
            st.session_state['auth_view'] = 'login' # Cambiar a la vista de login
        elif response.status_code == 400:
             error_data = response.json()
             st.session_state['auth_message'] = {"text": f"Error: {error_data.get('error', 'Datos inválidos')}", "type": "error"}
        elif response.status_code == 409:
            error_data = response.json()
            st.session_state['auth_message'] = {"text": f"Error: {error_data.get('error', 'El usuario ya existe')}", "type": "warning"}
        else:
            st.session_state['auth_message'] = {"text": f"Error en el registro: Estado {response.status_code}. Mensaje: {response.text}", "type": "error"}
    except requests.exceptions.ConnectionError:
        st.session_state['auth_message'] = {"text": f"Error: No se pudo conectar con el servidor de autenticación en {AUTH_BACKEND_URL}.", "type": "error"}
    except Exception as e:
        st.session_state['auth_message'] = {"text": f"Ocurrió un error inesperado: {e}", "type": "error"}


def call_login_api(username, password):
    """Llama al endpoint de inicio de sesión del backend de autenticación."""
    st.session_state['auth_message'] = None # Limpiar mensaje anterior
    try:
        response = requests.post(ENDPOINT_LOGIN, json={
            "username": username,
            "password": password
        })
        if response.status_code == 200:
            login_data = response.json()
            st.session_state['logged_in'] = True
            st.session_state['username'] = login_data.get('username')
            st.session_state['company'] = login_data.get('company')
            # st.session_state['auth_message'] = {"text": "Inicio de sesión exitoso.", "type": "success"} # Opcional: mensaje de éxito al loguear

            # Limpiar mensajes de auth y rerun para mostrar la app principal
            st.session_state['auth_message'] = None
            st.session_state['auth_view'] = 'login' # Reset view
            st.rerun() # <-- Rerun para entrar en el estado logueado

        elif response.status_code == 401:
             error_data = response.json()
             st.session_state['auth_message'] = {"text": f"Error: {error_data.get('error', 'Credenciales inválidas')}", "type": "error"}
        elif response.status_code == 404:
             error_data = response.json()
             st.session_state['auth_message'] = {"text": f"Error: {error_data.get('error', 'Usuario no encontrado')}", "type": "error"}
        else:
            st.session_state['auth_message'] = {"text": f"Error en el inicio de sesión: Estado {response.status_code}. Mensaje: {response.text}", "type": "error"}
    except requests.exceptions.ConnectionError:
        st.session_state['auth_message'] = {"text": f"Error: No se pudo conectar con el servidor de autenticación en {AUTH_BACKEND_URL}.", "type": "error"}
    except Exception as e:
        st.session_state['auth_message'] = {"text": f"Ocurrió un error inesperado: {e}", "type": "error"}

# --- Funciones para mostrar formularios de autenticación ---

def show_register_form():
    """Muestra el formulario de registro."""
    st.title("Registro de Nuevo Usuario")

    with st.form("register_form"):
        reg_username = st.text_input("Usuario", key="reg_username_main")
        reg_password = st.text_input("Contraseña", type="password", key="reg_password_main")
        reg_company = st.text_input("Empresa", key="reg_company_main")

        submit_button = st.form_submit_button("Registrar")

        if submit_button:
            call_register_api(reg_username, reg_password, reg_company)
            # st.rerun() # Ya se hace dentro de call_register_api si cambia la vista

    # Mostrar mensaje de feedback (usamos pop para consumirlo)
    if 'auth_message' in st.session_state and st.session_state['auth_message']:
        message = st.session_state.pop('auth_message')
        if message['type'] == 'success':
            st.success(message['text'])
        elif message['type'] == 'warning':
            st.warning(message['text'])
        else:
            st.error(message['text'])

    st.markdown("¿Ya tienes cuenta? [Iniciar sesión](#inicio-de-sesion)")
    if st.button("Ir a Iniciar Sesión", key="goto_login_btn_main"):
         st.session_state['auth_view'] = 'login'
         st.session_state['auth_message'] = None # Limpiar mensaje al cambiar de vista
         st.rerun()


def show_login_form():
    """Muestra el formulario de inicio de sesión."""
    st.title("Inicio de Sesión")

    with st.form("login_form"):
        login_username = st.text_input("Usuario", key="login_username_main")
        login_password = st.text_input("Contraseña", type="password", key="login_password_main")

        submit_button = st.form_submit_button("Iniciar Sesión")

        if submit_button:
            call_login_api(login_username, login_password)
            # st.rerun() # Ya se hace dentro de call_login_api si el login es exitoso


    # Mostrar mensaje de feedback (usamos pop para consumirlo)
    if 'auth_message' in st.session_state and st.session_state['auth_message']:
        message = st.session_state.pop('auth_message')
        if message['type'] == 'success':
            st.success(message['text'])
        else:
            st.error(message['text'])


    st.markdown("¿No tienes cuenta? [Regístrate aquí](#registro-de-nuevo-usuario)")
    if st.button("Ir a Registro", key="goto_register_btn_main"):
         st.session_state['auth_view'] = 'register'
         st.session_state['auth_message'] = None # Limpiar mensaje al cambiar de vista
         st.rerun()


# --- Funciones Auxiliares Existentes (Se mantienen sin cambios) ---

def obtener_nombres_cv(ruta_carpeta):
    """Obtiene una lista de nombres de archivos CVs desde la carpeta especificada."""
    # ... (código existente de obtener_nombres_cv)
    try:
        archivos = os.listdir(ruta_carpeta)
        return [archivo for archivo in archivos if archivo.lower().endswith(".pdf")]
    except FileNotFoundError:
        st.error(f"No se encontró la carpeta: {ruta_carpeta}")
        return []
    except Exception as e:
        st.error(f"Error al listar archivos en la carpeta {ruta_carpeta}: {e}")
        return []


def cargar_profesiones(ruta_archivo):
    """Carga las profesiones desde el archivo CSV."""
    # ... (código existente de cargar_profesiones)
    try:
        if not os.path.exists(ruta_archivo):
             df = pd.DataFrame({"Profesion": []})
             df.to_csv(ruta_archivo, index=False)
             return []

        df = pd.read_csv(ruta_archivo)
        if "Profesion" in df.columns:
            return df["Profesion"].dropna().astype(str).tolist()
        else:
            st.warning(f"El archivo CSV {ruta_archivo} no contiene la columna 'Profesion'. Se creará uno nuevo.")
            df = pd.DataFrame({"Profesion": []})
            df.to_csv(ruta_archivo, index=False)
            return []
    except FileNotFoundError:
        st.error(f"Error interno: No se encontró el archivo de profesiones después de verificar: {ruta_archivo}")
        return []
    except pd.errors.EmptyDataError:
        return []
    except Exception as e:
        st.error(f"Error al cargar las profesiones desde {ruta_archivo}: {e}")
        return []


def guardar_profesiones(ruta_archivo, profesiones):
    """Guarda las profesiones en el archivo CSV."""
    # ... (código existente de guardar_profesiones)
    try:
        df = pd.DataFrame({"Profesion": profesiones})
        df.to_csv(ruta_archivo, index=False)
    except Exception as e:
        st.error(f"Error al guardar las profesiones en {ruta_archivo}: {e}")


def agregar_nueva_profesion(nueva_profesion, profesiones):
    """Agrega una nueva profesión a la lista y guarda los cambios."""
    # ... (código existente de agregar_nueva_profesion)
    nueva_profesion_limpia = nueva_profesion.strip()

    if nueva_profesion_limpia and nueva_profesion_limpia not in profesiones:
        profesiones.append(nueva_profesion_limpia)
        guardar_profesiones(RUTA_ARCHIVO_PROFESIONES, profesiones)
        st.success(f"Profesión '{nueva_profesion_limpia}' añadida correctamente.")
    elif not nueva_profesion_limpia:
         st.warning("Por favor, introduce una profesión.")
    else:
         st.info(f"La profesión '{nueva_profesion_limpia}' ya existe.")


def enviar_cv_y_profesion(nombre_cv, profesion, filtro_idioma=None, filtro_experiencia_min=None, filtro_palabras_clave=None, filtro_nivel_educativo=None, filtro_sector=None):
    """Envía el CV y la profesión al endpoint para procesamiento, incluyendo filtros."""
    # ... (código existente de enviar_cv_y_profesion)
    ruta_cv = os.path.join(RUTA_CARPETA_CV, nombre_cv)
    try:
        with open(ruta_cv, "rb") as archivo_pdf:
            files = {"pdf": (nombre_cv, archivo_pdf, "application/pdf")}
            data = {"puesto": profesion}

            if filtro_idioma:
                data["filtro_idioma"] = filtro_idioma
            if filtro_experiencia_min is not None:
                 data["filtro_experiencia_min"] = filtro_experiencia_min
            if filtro_palabras_clave:
                 data["filtro_palabras_clave"] = filtro_palabras_clave
            if filtro_nivel_educativo:
                 data["filtro_nivel_educativo"] = filtro_nivel_educativo
            if filtro_sector:
                 data["filtro_sector"] = filtro_sector

            # Usamos BACKEND_CV_URL para el procesamiento de CVs
            response = requests.post(ENDPOINT_PROCESAR_PDF, files=files, data=data)

            if response.status_code != 200:
                print(f"Error al procesar {nombre_cv}. Estado: {response.status_code}. Respuesta: {response.text}")

            return response
    except FileNotFoundError:
        st.error(f"No se encontró el archivo: {ruta_cv}")
        return None
    except requests.exceptions.ConnectionError:
        st.error(f"Error: No se pudo conectar con el servidor backend de CVs en {BACKEND_CV_URL}.")
        return None
    except Exception as e:
        st.error(f"Ocurrió un error al enviar el CV {nombre_cv}: {e}")
        print(f"Excepción al enviar CV {nombre_cv}: {e}")
        return None


def guardar_resultados_en_historial(puesto, resultados_lista):
    """Envía la lista de resultados de procesamiento masivo al backend para guardar historial."""
    # ... (código existente de guardar_resultados_en_historial)
    # Nota: Este endpoint depende de si tu backend principal (CV) incluye la funcionalidad de historial (con IA).
    # Si el backend de CV es "manual" (solo guarda archivos), este endpoint puede no existir o devolver 501.
    try:
        data = {
            "puesto": puesto,
            "resultados": resultados_lista
        }
        # Usamos BACKEND_CV_URL para el historial
        response = requests.post(ENDPOINT_GUARDAR_HISTORIAL, json=data)
        if response.status_code == 200:
            return True
        elif response.status_code == 501:
             st.warning("El backend de CV no tiene habilitada la funcionalidad de guardar historial.")
             return False
        else:
            st.error(f"Error al guardar historial en backend. Estado: {response.status_code}. Mensaje: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        st.error(f"Error: No se pudo conectar con el servidor backend de CVs en {BACKEND_CV_URL} para guardar el historial.")
        return False
    except Exception as e:
        st.error(f"Error inesperado al guardar historial: {e}")
        return False


@st.cache_data(ttl=60)
def obtener_historial_ejecuciones():
    """Obtiene la lista de ejecuciones pasadas desde el backend."""
    # ... (código existente de obtener_historial_ejecuciones)
    # Nota: Este endpoint depende de si tu backend principal (CV) incluye la funcionalidad de historial (con IA).
    try:
        # Usamos BACKEND_CV_URL para el historial
        response = requests.get(ENDPOINT_HISTORIAL_EJECUCIONES)
        if response.status_code == 200:
            historial_data = response.json()
            for ejecucion in historial_data:
                try:
                     dt_object = datetime.fromisoformat(ejecucion['timestamp'])
                     ejecucion['fecha_hora'] = dt_object.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                     ejecucion['fecha_hora'] = ejecucion['timestamp']
            return historial_data
        elif response.status_code == 501:
             st.warning("El historial de análisis no está disponible en el backend de CV.")
             return []
        else:
            st.error(f"Error al obtener historial del backend de CV. Estado: {response.status_code}. Mensaje: {response.text}")
            return []
    except requests.exceptions.ConnectionError:
        st.error(f"Error: No se pudo conectar con el servidor backend de CVs en {BACKEND_CV_URL} para obtener el historial.")
        return []
    except Exception as e:
        st.error(f"Error inesperado al obtener historial: {e}")
        return []


def obtener_detalles_ejecucion(timestamp):
    """Obtiene los detalles (counts) de una ejecución específica desde el backend."""
    # ... (código existente de obtener_detalles_ejecucion)
    # Nota: Este endpoint depende de si tu backend principal (CV) incluye la funcionalidad de historial (con IA).
    try:
        # Usamos BACKEND_CV_URL para los detalles del historial
        response = requests.get(f"{ENDPOINT_DETALLES_EJECUCION}/{timestamp}")
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            st.warning("La ejecución solicitada no fue encontrada en el historial.")
            return None
        elif response.status_code == 501:
             st.warning("Los detalles de análisis no están disponibles en el backend de CV.")
             return None
        else:
            st.error(f"Error al obtener detalles de la ejecución del backend de CV. Estado: {response.status_code}. Mensaje: {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        st.error(f"Error: No se pudo conectar con el servidor backend de CVs en {BACKEND_CV_URL} para obtener detalles.")
        return None
    except Exception as e:
        st.error(f"Error inesperado al obtener detalles de la ejecución: {e}")
        return None


def procesar_cvs_masivamente(nombres_cv, profesion, filtro_idioma=None, filtro_experiencia_min=None, filtro_palabras_clave=None, filtro_nivel_educativo=None, filtro_sector=None):
    """Procesa todos los CVs en la carpeta y devuelve los resultados."""
    # ... (código existente de procesar_cvs_masivamente)
    resultados = []
    for nombre_cv in nombres_cv:
        response = enviar_cv_y_profesion(nombre_cv, profesion, filtro_idioma, filtro_experiencia_min, filtro_palabras_clave, filtro_nivel_educativo, filtro_sector)
        if response and response.status_code == 200:
            try:
                respuesta_json = response.json()
                if isinstance(respuesta_json, dict):
                    respuesta_json['nombre_archivo_cv'] = nombre_cv # Añadir nombre del archivo original
                    resultados.append(respuesta_json)
                else:
                     st.error(f"Error al procesar {nombre_cv}: La respuesta del servidor no tiene el formato esperado (no es un diccionario).")
                     print(f"Respuesta recibida para {nombre_cv}: {respuesta_json}")
                     resultados.append({"error": "Formato de respuesta inesperado", "nombre_cv": nombre_cv, "respuesta_raw": respuesta_json})
            except json.JSONDecodeError:
                st.error(f"Error al procesar {nombre_cv}: Respuesta del servidor no es un JSON válido. Respuesta: {response.text[:200]}...")
                resultados.append({"error": "JSON inválido", "nombre_cv": nombre_cv, "respuesta_raw": response.text})
            except Exception as e:
                 st.error(f"Error inesperado al procesar la respuesta de {nombre_cv}: {e}")
                 print(f"Excepción al procesar respuesta de {nombre_cv}: {e}. Respuesta: {response.text}")
                 resultados.append({"error": f"Excepción al procesar respuesta: {e}", "nombre_cv": nombre_cv, "respuesta_raw": response.text})
        else:
            status_code = response.status_code if response else 'N/A'
            error_text = response.text if response else 'Sin respuesta o error de conexión'
            st.error(f"Error al procesar {nombre_cv}. Código de estado: {status_code}. Mensaje: {error_text[:200]}...")
            resultados.append({"error": f"Error HTTP {status_code}", "nombre_cv": nombre_cv, "error_message": error_text})

    if resultados:
        st.info("Guardando resultados en el historial...")
        # Llamamos a guardar resultados en el historial del backend de CVs
        success = guardar_resultados_en_historial(profesion, resultados)
        if success:
            st.success("Historial de procesamiento guardado.")
        else:
            # Mensaje de error ya mostrado dentro de guardar_resultados_en_historial
            pass

    return resultados


def mostrar_respuesta_servidor_masivo(resultados):
    """Muestra la respuesta del servidor para el procesamiento masivo en un AgGrid con botón de resumen."""
    # ... (código existente de mostrar_respuesta_servidor_masivo)
    if resultados:
        df_resultados_tabla = []
        for res in resultados:
            if 'error' not in res:
                 df_resultados_tabla.append({
                     "Nombre Completo": f"{res.get('nombre', 'N/A')} {res.get('apellidos', 'N/A')}",
                     "Apto": "🟢 Apto" if res.get('apto', False) else "🔴 No apto",
                     "Puntuación": res.get('puntuacionPuesto', 'N/A'),
                     "respuesta_json": res # Guardamos la respuesta completa
                 })
            else:
                 df_resultados_tabla.append({
                      "Nombre Completo": f"{res.get('nombre_archivo_cv', 'Error')}",
                      "Apto": "❌ Error",
                      "Puntuación": "N/A",
                      "respuesta_json": res # Guardar el objeto de error completo
                 })

        df_resultados = pd.DataFrame(df_resultados_tabla)

        gb = GridOptionsBuilder.from_dataframe(df_resultados)
        gb.configure_column("respuesta_json", hide=True)

        gb.configure_column("Acciones",
                           header_name="Detalles",
                           cellRenderer='''
                               class BtnCellRenderer {
                                   init(params) {
                                       this.eGui = document.createElement('div');
                                       const rowData = params.data;
                                       if (rowData && rowData.Apto !== '❌ Error') {
                                          this.eGui.innerHTML = `<button class="btn-details">Ver Detalles</button>`;
                                          this.btn = this.eGui.querySelector('.btn-details');
                                          this.btn.addEventListener('click', () => {
                                              parent.postMessage({ event: 'streamlit:selectRow', rowData: rowData }, '*');
                                          });
                                       } else {
                                           this.eGui.innerHTML = 'Error';
                                       }
                                   }
                                   getGui() {
                                       return this.eGui;
                                   }
                                   destroy() {
                                       if (this.btn) {
                                            this.btn.removeEventListener('click', this.onClick);
                                       }
                                   }
                               }
                           ''',
                           autoHeight=True, suppressMenu=True, suppressFilter=True,
                           resizable=False, sortable=False, editable=False,
                           flex=1, minWidth=120
                          )

        gridOptions = gb.build()

        grid_response = AgGrid(
            df_resultados,
            gridOptions=gridOptions,
            data_return_mode='AS_INPUT',
            update_mode='MODEL_CHANGED',
            fit_columns_on_grid_load=False,
            allow_unsafe_jscode=True,
            enable_enterprise_modules=False,
            height=350,
            width='100%',
            reload_data=True,
            columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS
        )

    else:
        # Este mensaje ahora también cubre el caso de 501 del backend si no tiene historial
        if 'button_procesar_masivo' in st.session_state and st.session_state.button_procesar_masivo and \
           ('resultados_procesamiento_masivo' not in st.session_state or not st.session_state['resultados_procesamiento_masivo']):
           st.info("Proceso de CVs masivo completado. No se encontraron candidatos que cumplan con los filtros especificados, hubo errores, o el backend no devolvió resultados de análisis.")
        else:
           st.info("Presiona 'Procesar CVs Masivamente' para ver los resultados.")


# --- Contenido de la primera pestaña (Procesamiento Masivo) - Se mantiene sin cambios funcionales ---
def tab_procesamiento_masivo():
    """Contenido de la pestaña de Procesamiento Masivo."""
    st.title("CVisualizer - Procesamiento Masivo")

    profesiones = cargar_profesiones(RUTA_ARCHIVO_PROFESIONES)
    nombres_cv = obtener_nombres_cv(RUTA_CARPETA_CV)

    if not nombres_cv:
        st.warning(f"No se encontraron archivos CVs (.pdf) en la carpeta especificada: {RUTA_CARPETA_CV}")
        st.info("Por favor, asegúrate de que la ruta es correcta y contiene archivos PDF.")
        # No return, permitimos que el usuario añada profesión incluso sin CVs presentes
        # return

    st.subheader("Configuración del Puesto")
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_profesion = st.selectbox("Seleccionar Profesión para Procesamiento Masivo", ["Otro"] + profesiones, key="select_profesion_masiva")

    nueva_profesion_masiva_input = ""
    if selected_profesion == "Otro":
        with col2:
            nueva_profesion_masiva_input = st.text_input("Nueva Profesión", key="input_nueva_profesion_masiva")
            if st.button("Añadir", key="button_add_profesion_masiva"):
                 agregar_nueva_profesion(nueva_profesion_masiva_input, profesiones)
                 profesiones_actualizadas = cargar_profesiones(RUTA_ARCHIVO_PROFESIONES)
                 if nueva_profesion_masiva_input.strip() in profesiones_actualizadas:
                      st.session_state.select_profesion_masiva = nueva_profesion_masiva_input.strip()
                 st.rerun()

    profesion_a_usar = selected_profesion if selected_profesion != "Otro" else nueva_profesion_masiva_input.strip()

    st.subheader("Filtros Adicionales")
    col3, col4 = st.columns(2)
    with col3:
        filtro_idioma = st.text_input("Filtrar por idioma (ej: Inglés, Francés):", key="filtro_idioma_masivo")
        filtro_palabras_clave = st.text_input("Filtrar por palabras clave (separadas por comas):", key="filtro_palabras_clave_masivo")
        filtro_sector = st.text_input("Filtrar por sector profesional:", key="filtro_sector_masivo")
    with col4:
        filtro_experiencia_min = st.number_input("Experiencia mínima (años)", min_value=0, value=None, placeholder="Mínimo", key="filtro_experiencia_min_masivo", format="%d")
        filtro_nivel_educativo_options = ["Todos", "Bachillerato", "Técnico Superior", "Grado", "Máster", "Doctorado"]
        filtro_nivel_educativo = st.selectbox("Filtrar por nivel educativo", filtro_nivel_educativo_options, key="filtro_nivel_educativo_masivo")


    if st.button("Procesar CVs Masivamente", key="button_procesar_masivo"):
        if not profesion_a_usar:
            st.warning("Por favor, selecciona o añade una profesión para el procesamiento masivo.")
        elif not nombres_cv: # Añadimos verificación de si hay CVs para procesar
             st.warning("No hay archivos CVs (.pdf) encontrados en la carpeta para procesar.")
        else:
            st.session_state['resultados_procesamiento_masivo'] = []
            st.session_state['selected_row_data'] = None
            st.session_state['ejecucion_seleccionada_historial'] = None

            with st.spinner(f"Procesando {len(nombres_cv)} CVs para el puesto '{profesion_a_usar}'... Esto puede tomar un tiempo."):
                 resultados = procesar_cvs_masivamente(
                    nombres_cv,
                    profesion_a_usar,
                    filtro_idioma=filtro_idioma if filtro_idioma else None,
                    filtro_experiencia_min=filtro_experiencia_min,
                    filtro_palabras_clave=filtro_palabras_clave if filtro_palabras_clave else None,
                    filtro_nivel_educativo=(filtro_nivel_educativo if filtro_nivel_educativo != "Todos" else None),
                    filtro_sector=filtro_sector if filtro_sector else None
                 )
            st.session_state['resultados_procesamiento_masivo'] = resultados

    if 'resultados_procesamiento_masivo' in st.session_state and st.session_state['resultados_procesamiento_masivo']:
        mostrar_respuesta_servidor_masivo(st.session_state['resultados_procesamiento_masivo'])
    elif 'button_procesar_masivo' in st.session_state and st.session_state.button_procesar_masivo and \
         ('resultados_procesamiento_masivo' not in st.session_state or not st.session_state['resultados_procesamiento_masivo']):
         st.info("Proceso de CVs masivo completado. No se encontraron candidatos que cumplan con los filtros especificados, hubo errores, o el backend no devolvió resultados de análisis.")


    # Lógica para mostrar detalles del candidato seleccionado en AgGrid (dentro de esta pestaña)
    # Esto se activa después de que un clic en el botón "Ver Detalles" causa un rerun
    if 'selected_row_data' in st.session_state and st.session_state.selected_row_data:
         selected_row_data = st.session_state.pop('selected_row_data') # Consumir el evento
         respuesta_detallada = selected_row_data.get("respuesta_json", {})

         st.subheader(f"Detalles de {selected_row_data.get('Nombre Completo', 'Candidato')}")

         st.write(f"**Apto:** {selected_row_data.get('Apto', 'N/A')}")
         st.write(f"**Puntuación (0-10):** {selected_row_data.get('Puntuación', 'N/A')}")

         experiencia = respuesta_detallada.get("experiencia_trabajo", [])
         if experiencia:
             st.write("**Experiencia Laboral:**")
             for item in experiencia:
                 st.write(f"- {item}")
         else:
             st.write("**Experiencia Laboral:** No especificada o no extraída.")

         educacion = respuesta_detallada.get("educacion", [])
         if educacion:
             st.write("**Educación:**")
             for item in educacion:
                  st.write(f"- {item}")
         else:
             st.write("**Educación:** No especificada o no extraída.")

         if respuesta_detallada.get("apto"):
             resumen = respuesta_detallada.get("resumenCandidato")
             if resumen:
                st.write("**Resumen del Candidato:**")
                st.info(resumen)
         else:
             razones = respuesta_detallada.get("razonesNoAptitud")
             if razones:
                st.write("**Razones de No Aptitud:**")
                st.warning(razones)
             elif 'error' in respuesta_detallada:
                 st.error(f"Error de procesamiento para este candidato: {respuesta_detallada.get('error', 'Error desconocido')}")
                 if 'error_message' in respuesta_detallada:
                      st.text(f"Mensaje del servidor: {respuesta_detallada['error_message']}")
                 # Opcional: mostrar raw response si el error lo incluye para depuración
                 # if 'respuesta_raw' in respuesta_detallada:
                 #      st.json(respuesta_detallada['respuesta_raw'])
             else:
                st.write("**Razones de No Aptitud:** No especificadas.")

         st.write("**Evaluación por Criterios (Porcentajes Estimados si disponibles):**")
         st.write(f"- Experiencia: {respuesta_detallada.get('porcentaje_experiencia', 'N/A')}%")
         st.write(f"- Educación: {respuesta_detallada.get('porcentaje_educacion', 'N/A')}%")
         st.write(f"- Habilidades: {respuesta_detallada.get('porcentaje_habilidades', 'N/A')}%")
         st.write(f"- Idiomas: {respuesta_detallada.get('porcentaje_idiomas', 'N/A')}%")
         st.write(f"- Otros: {respuesta_detallada.get('porcentaje_otros', 'N/A')}%")


# --- Contenido de la segunda pestaña (Historial) - Se mantiene sin cambios funcionales ---
def tab_historial():
    """Contenido de la pestaña de Historial."""
    st.title("Historial de Ejecuciones")
    st.write("Selecciona una ejecución del historial para ver el resumen de aptitud.")

    historial = obtener_historial_ejecuciones()

    if not historial:
        st.info("No hay ejecuciones en el historial.")
        # No return, permitimos que el usuario vea el mensaje de "sin historial" incluso si no hay datos
        # return

    if historial: # Solo mostrar el selectbox si hay historial cargado
        opciones_historial = [
            f"{ejecucion.get('fecha_hora', 'Fecha/Hora Desconocida')} - {ejecucion.get('puesto', 'Puesto Desconocido')} ({ejecucion.get('num_candidatos', 0)} candidatos)"
            for ejecucion in historial
        ]

        seleccion_indice = st.selectbox(
            "Seleccionar Ejecución",
            options=range(len(opciones_historial)),
            format_func=lambda x: opciones_historial[x],
            key="select_historial_ejecucion_main"
        )

        if seleccion_indice is not None and 0 <= seleccion_indice < len(historial): # Asegurar que el índice es válido
            ejecucion_seleccionada = historial[seleccion_indice]
            timestamp_seleccionado = ejecucion_seleccionada.get("timestamp")

            if timestamp_seleccionado:
                detalles_ejecucion = obtener_detalles_ejecucion(timestamp_seleccionado)

                if detalles_ejecucion and 'counts' in detalles_ejecucion:
                    counts = detalles_ejecucion['counts']
                    apto = counts.get('apto', 0)
                    no_apto = counts.get('no_apto', 0)
                    no_procesado = counts.get('no_procesado', 0)

                    st.subheader(f"Resumen para el puesto: {detalles_ejecucion.get('puesto', 'N/A')}")
                    st.write(f"Fecha y Hora: {ejecucion_seleccionada.get('fecha_hora', 'N/A')}")
                    st.write(f"Total Candidatos Procesados: {ejecucion_seleccionada.get('num_candidatos', 0)}")

                    data_pie = {
                        'Categoría': ['Aptos', 'No Aptos', 'No Procesados'],
                        'Cantidad': [apto, no_apto, no_procesado]
                    }
                    df_pie = pd.DataFrame(data_pie)

                    df_pie = df_pie[df_pie['Cantidad'] > 0]

                    if not df_pie.empty:
                        fig = px.pie(df_pie,
                                     values='Cantidad',
                                     names='Categoría',
                                     title='Distribución de Candidatos por Resultado',
                                     color='Categoría',
                                     color_discrete_map={
                                         'Aptos': 'green',
                                         'No Aptos': 'red',
                                         'No Procesados': 'gray'
                                     }
                                    )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No hay datos válidos para mostrar en el gráfico para esta ejecución.")

                elif detalles_ejecucion is None:
                    pass
                else:
                     st.warning("No se pudieron obtener los detalles completos para esta ejecución.")
                     print(f"Detalles recibidos (formato inesperado): {detalles_ejecucion}")

            else:
                st.warning("No se pudo determinar el timestamp de la ejecución seleccionada.")
        # No necesitamos else aquí, el mensaje de "Selecciona una ejecución" ya se muestra si historial existe pero seleccion_indice es None
        # else:
        #    st.info("Selecciona una ejecución del historial arriba.")


# --- Función Principal ---

def main():
    """Función principal para ejecutar la aplicación Streamlit con autenticación y pestañas."""

    # Listener para capturar eventos del AgGrid botón 'Ver Detalles'
    # Esto debe estar fuera de los bloques condicionales logged_in para que el evento se capture
    event = st.session_state.get('streamlit:selectRow')
    if event:
        st.session_state.selected_row_data = event['rowData']
        st.rerun() # Rerun para procesar el estado actualizado y mostrar detalles


    # --- Lógica de Autenticación ---
    if st.session_state['logged_in']:
        # --- Contenido de la Aplicación Principal (Pestañas) ---
        st.sidebar.write(f"Usuario: **{st.session_state['username']}**")
        st.sidebar.write(f"Empresa: **{st.session_state['company']}**")
        if st.sidebar.button("Cerrar Sesión"):
            st.session_state['logged_in'] = False
            st.session_state['username'] = None
            st.session_state['company'] = None
            st.session_state['resultados_procesamiento_masivo'] = [] # Limpiar resultados al cerrar sesión
            st.session_state['selected_row_data'] = None # Limpiar detalles
            # st.session_state['select_historial_ejecucion_main'] = None # Reiniciar selección historial
            # st.cache_data.clear() # Opcional: Limpiar cache de historial
            st.rerun() # Rerun para volver a la pantalla de login

        # Mostrar las pestañas si está logueado
        tab1, tab2 = st.tabs(["Procesamiento Masivo", "Historial y Estadísticas"])

        with tab1:
            tab_procesamiento_masivo()
            # Los detalles del candidato seleccionado se muestran dentro de tab_procesamiento_masivo
            # debido a la lógica copiada allí.

        with tab2:
            tab_historial()

    else:
        # --- Contenido de Autenticación (Formularios) ---
        if st.session_state['auth_view'] == 'login':
            show_login_form()
        elif st.session_state['auth_view'] == 'register':
            show_register_form()


# Ejecutar la aplicación
if __name__ == "__main__":
    # Inicializar otros estados de sesión que no sean de auth
    # Mover inicializaciones de estado no relacionadas con auth aquí
    if 'selected_row_data' not in st.session_state:
        st.session_state['selected_row_data'] = None
    if 'resultados_procesamiento_masivo' not in st.session_state:
         st.session_state['resultados_procesamiento_masivo'] = []
    # Inicializar el estado para la selección de profesión si es necesario
    if 'select_profesion_masiva' not in st.session_state:
        st.session_state['select_profesion_masiva'] = 'Otro' # Valor por defecto
    # Inicializar el estado para la selección de historial (usar key_main)
    if 'select_historial_ejecucion_main' not in st.session_state:
         st.session_state['select_historial_ejecucion_main'] = None # Ninguna selección inicial

    main()