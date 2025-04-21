```mermaid
graph TD
    %% Definición de los componentes principales (Subgraphs)
    subgraph Frontend (Interfaz de Usuario - Streamlit)
        A[Inicio Usuario] --> B{¿Usuario Autenticado?}
        B -- No --> C[Mostrar Formulario<br/>Registro o Login]
        C -- Login --> D[Ingresar Credenciales<br/>Login]
        D -- Enviar Login --> BackendAuth
        C -- Registro --> E[Ingresar Datos<br/>Registro]
        E -- Enviar Registro --> BackendAuth

        B -- Sí --> F[Mostrar Interfaz Principal<br/>(Pestañas)]
        F --> G[Pestaña Procesamiento Masivo]
        G --> H[Seleccionar/Añadir Puesto<br/>y Configurar Filtros]
        H --> I[Identificar Archivos PDF<br/>Carpeta Local]
        I --> J[Click Procesar CVs Masivamente]

        J --> K{Para cada CV (PDF):}
        K --> L[Leer Contenido Archivo PDF]
        L -- Enviar PDF + Config --> BackendCVProc

        K -- Fin Bucle --> M[Recopilar Resultados Individuales]
        M -- Envía Lote Completo --> BackendCVProcHist

        M --> N[Mostrar Tabla<br/>Resultados Resumidos (AgGrid)]
        N --> O[Click en "Ver Detalles"<br/>en AgGrid]
        O --> P[Mostrar Detalles Completos<br/>del Candidato]

        F --> Q[Pestaña Historial<br/>(Si implementada UI)]
        Q --> R[Solicitar Historial<br/>de Ejecuciones]
        R -- Pide Historial --> BackendCVProcHist
        R <-- Recibe Resumen -- BackendCVProcHist
        Q --> S[Mostrar Historial<br/>(Resumen de Ejecuciones)]
        S --> T[Seleccionar Ejecución<br/>del Historial]
        T -- Pide Detalles --> BackendCVProcHist
        T <-- Recibe Counts -- BackendCVProcHist
        S --> U[Mostrar Resumen de Counts<br/>de Ejecución Seleccionada]
    end

    subgraph BackendAuth (Backend de Autenticación - Flask)
        BackendAuth(Servicio de<br/>Autenticación :5002)
        BackendAuth -- Recibe /register --> V[Validar Datos<br/>Registro]
        V --> W{Usuario Existe?}
        W -- Sí --> W_Err[Responder 409<br/>(Conflicto)]
        W -- No --> X[Hashear Contraseña<br/>(bcrypt)]
        X --> Y[Guardar Usuario y Hash<br/>en usuarios.json]
        Y --> Z[Responder 201<br/>(Creado)]

        BackendAuth -- Recibe /login --> AA[Validar Datos<br/>Login]
        AA --> AB{Usuario Existe?}
        AB -- No --> AB_Err[Responder 404<br/>(No Encontrado)]
        AB -- Sí --> AC[Verificar Contraseña<br/>(bcrypt)]
        AC -- Correcta --> AD[Responder 200<br/>(OK)]
        AD -- Envía User/Empresa --> Frontend
        AC -- Incorrecta --> AE[Responder 401<br/>(No Autorizado)]

        Y -.-> AF(usuarios.json)
        AB -.-> AF
        W -.-> AF
    end

    subgraph BackendCVProc (Backend de Procesamiento CVs - Flask)
        BackendCVProc(Servicio de<br/>Procesamiento :5001)

        BackendCVProc -- Recibe /procesar_pdf --> BA[Guardar PDF<br/>Temporalmente]
        BA --> BB[Construir Prompt Detallado<br/>(Puesto + Filtros)]
        BB -- Enviar Prompt + PDF --> GoogleGenAI
        BB <-- Recibe Respuesta AI -- GoogleGenAI
        BB --> BC[Parsear y Validar<br/>Respuesta JSON]
        BC --> BD[Eliminar PDF<br/>Temporal]
        BD --> BE[Responder 200 OK<br/>(Resultado Candidato)]
        BC -- Error Parseo/Validación --> BF[Responder 500<br/>(Error Interno)]
        GoogleGenAI -- Error API --> BF

        BackendCVProcHist(Servicio Historial<br/>en Backend :5001)
        BackendCVProcHist -- Recibe /guardar_resultados_masivos --> CA[Cargar historial.json]
        CA --> CB[Añadir Nueva Ejecución<br/>(Timestamp, Puesto, Resultados Lote)]
        CB --> CC[Guardar historial.json]
        CC --> CD[Responder 200 OK]

        BackendCVProcHist -- Recibe /historial_ejecuciones --> DA[Cargar historial.json]
        DA --> DB[Generar Resumen<br/>Historial]
        DB --> DC[Responder 200 OK<br/>(Lista Resumen)]

        BackendCVProcHist -- Recibe /detalles_ejecucion/{ts} --> EA[Cargar historial.json]
        EA --> EB[Buscar Ejecución<br/>por Timestamp]
        EB -- No Encontrada --> EC[Responder 404]
        EB -- Encontrada --> ED[Contar Aptos/No Aptos/Errores<br/>en Resultados del Lote]
        ED --> EE[Responder 200 OK<br/>(Counts)]

        CA -.-> FF(historial_ejecuciones.json)
        DA -.-> FF
        EA -.-> FF
        CB -.-> FF
        CC -.-> FF
    end

    subgraph GoogleAI (Servicio de IA)
        GoogleGenAI([Google GenAI API<br/>(Gemini 1.5 Flash)])
    end

    %% Conexiones entre Subgraphs
    BackendAuth --> Frontend
    BackendCVProc --> Frontend
    BackendCVProcHist --> Frontend
    GoogleGenAI --> BackendCVProc

    %% Conexiones de errores (ejemplos, no todas las posibles)
    W_Err --> Frontend
    Z --> Frontend
    AB_Err --> Frontend
    AE --> Frontend
    BE --> Frontend
    BF --> Frontend
    CD --> Frontend
    DC --> Frontend
    EC --> Frontend
    EE --> Frontend

    %% Flujo de datos/acciones adicionales
    I -.-> L
    O -.-> P %% P usa datos ya en Frontend
    R --> S %% Frontend actualiza UI con resumen
    T --> U %% Frontend actualiza UI con counts
