'''mermaid
    %% Definición de los componentes principales (Subgraphs) - CORREGIDO
    subgraph Frontend ("Interfaz de Usuario - Streamlit")
        A[Inicio Usuario] --> B{¿Usuario Autenticado?}
        B -- No --> C[Mostrar Formulario<br/>Registro o Login]
        C -- Login --> D[Ingresar Credenciales<br/>Login]
        D -- Enviar Login --> BackendAuth_Node
        C -- Registro --> E[Ingresar Datos<br/>Registro]
        E -- Enviar Registro --> BackendAuth_Node

        B -- Sí --> F[Mostrar Interfaz Principal<br/>(Pestañas)]
        F --> G[Pestaña Procesamiento Masivo]
        G --> H[Seleccionar/Añadir Puesto<br/>y Configurar Filtros]
        H --> I[Identificar Archivos PDF<br/>Carpeta Local]
        I --> J[Click Procesar CVs Masivamente]

        J --> K{Para cada CV (PDF):}
        K --> L[Leer Contenido Archivo PDF]
        L -- Enviar PDF + Config --> BackendCVProc_PDF_Endpoint

        K -- Fin Bucle --> M[Recopilar Resultados Individuales]
        M -- Envía Lote Completo --> BackendCVProc_GuardarHist_Endpoint

        M --> N[Mostrar Tabla<br/>Resultados Resumidos (AgGrid)]
        N --> O[Click en "Ver Detalles"<br/>en AgGrid]
        O --> P[Mostrar Detalles Completos<br/>del Candidato]

        F --> Q[Pestaña Historial<br/>(Si implementada UI)]
        Q --> R[Solicitar Historial<br/>de Ejecuciones]
        R -- Pide Historial --> BackendCVProc_Hist_Endpoint
        R <-- Recibe Resumen -- BackendCVProc_Hist_Endpoint
        Q --> S[Mostrar Historial<br/>(Resumen de Ejecuciones)]
        S --> T[Seleccionar Ejecución<br/>del Historial]
        T -- Pide Detalles --> BackendCVProc_DetallesHist_Endpoint
        T <-- Recibe Counts -- BackendCVProc_DetallesHist_Endpoint
        S --> U[Mostrar Resumen de Counts<br/>de Ejecución Seleccionada]
    end

    subgraph BackendAuth ("Backend de Autenticación - Flask") %% CORREGIDO
        BackendAuth_Node(Servicio de<br/>Autenticación :5002)
        BackendAuth_Node -- Recibe /register --> V[Validar Datos<br/>Registro]
        V --> W{Usuario Existe?}
        W -- Sí --> W_Err[Responder 409<br/>(Conflicto)]
        W -- No --> X[Hashear Contraseña<br/>(bcrypt)]
        X --> Y[Guardar Usuario y Hash<br/>en usuarios.json]
        Y --> Z[Responder 201<br/>(Creado)]
        Z --> Frontend

        BackendAuth_Node -- Recibe /login --> AA[Validar Datos<br/>Login]
        AA --> AB{Usuario Existe?}
        AB -- No --> AB_Err[Responder 404<br/>(No Encontrado)]
        AB -- Sí --> AC[Verificar Contraseña<br/>(bcrypt)]
        AC -- Correcta --> AD[Responder 200<br/>(OK)]
        AD -- Envía User/Empresa --> Frontend
        AC -- Incorrecta --> AE[Responder 401<br/>(No Autorizado)]

        W_Err --> Frontend
        AB_Err --> Frontend
        AE --> Frontend

        Y -.-> AF[(usuarios.json)] %% CORREGIDO (Forma de base de datos)
        AB -.-> AF
        W -.-> AF
    end

    subgraph BackendCVProc ("Backend de Procesamiento CVs - Flask") %% CORREGIDO
        BackendCVProc_Node(Servicio de<br/>Procesamiento :5001)

        BackendCVProc_PDF_Endpoint[/procesar_pdf<br/>(POST)]
        BackendCVProc_Node -- Maneja --> BackendCVProc_PDF_Endpoint
        BackendCVProc_PDF_Endpoint --> BA[Guardar PDF<br/>Temporalmente]
        BA --> BB[Construir Prompt Detallado<br/>(Puesto + Filtros)]
        BB -- Enviar Prompt + PDF --> GoogleGenAI_API
        BB <-- Recibe Respuesta AI -- GoogleGenAI_API
        BB --> BC[Parsear y Validar<br/>Respuesta JSON]
        BC --> BD[Eliminar PDF<br/>Temporal]
        BD --> BE[Responder 200 OK<br/>(Resultado Candidato)]
        BE --> Frontend
        BC -- Error Parseo/Validación --> BF[Responder 500<br/>(Error Interno)]
        BF --> Frontend
        GoogleGenAI_API -- Error API --> BF

        BackendCVProc_GuardarHist_Endpoint[/guardar_resultados_masivos<br/>(POST)]
        BackendCVProc_Node -- Maneja --> BackendCVProc_GuardarHist_Endpoint
        BackendCVProc_GuardarHist_Endpoint --> CA[Cargar historial.json]
        CA --> CB[Añadir Nueva Ejecución<br/>(Timestamp, Puesto, Resultados Lote)]
        CB --> CC[Guardar historial.json]
        CC --> CD[Responder 200 OK]
        CD --> Frontend

        BackendCVProc_Hist_Endpoint[/historial_ejecuciones<br/>(GET)]
        BackendCVProc_Node -- Maneja --> BackendCVProc_Hist_Endpoint
        BackendCVProc_Hist_Endpoint --> DA[Cargar historial.json]
        DA --> DB[Generar Resumen<br/>Historial]
        DB --> DC[Responder 200 OK<br/>(Lista Resumen)]
        DC --> Frontend

        BackendCVProc_DetallesHist_Endpoint[/detalles_ejecucion/{ts}<br/>(GET)]
        BackendCVProc_Node -- Maneja --> BackendCVProc_DetallesHist_Endpoint
        BackendCVProc_DetallesHist_Endpoint --> EA[Cargar historial.json]
        EA --> EB[Buscar Ejecución<br/>por Timestamp]
        EB -- No Encontrada --> EC[Responder 404]
        EC --> Frontend
        EB -- Encontrada --> ED[Contar Aptos/No Aptos/Errores<br/>en Resultados del Lote]
        ED --> EE[Responder 200 OK<br/>(Counts)]
        EE --> Frontend


        CA -.-> FF[(historial_ejecuciones.json)] %% CORREGIDO (Forma de base de datos)
        DA -.-> FF
        EA -.-> FF
        CB -.-> FF
        CC -.-> FF
    end

    subgraph GoogleAI ("Servicio de IA") %% CORREGIDO
        GoogleGenAI_API([Google GenAI API<br/>(Gemini 1.5 Flash)])
    end

    %% Conexiones entre Subgraphs (Usando los nodos de servicio)
    BackendAuth_Node --> Frontend
    BackendCVProc_Node --> Frontend %% Conexión general, los endpoints específicos ya conectan

    %% Conexiones directas de Endpoints a Frontend (Reiteradas para claridad)
    BE --> Frontend
    BF --> Frontend
    CD --> Frontend
    DC --> Frontend
    EC --> Frontend
    EE --> Frontend

    %% Flujo de datos/acciones adicionales (Reiteradas)
    I -.-> L %% I lleva a la acción L
    O -.-> P %% O lleva a la acción P
    R --> S %% R lleva a la acción S (mostrar historial)
    T --> U %% T lleva a la acción U (mostrar detalles)
graph TD
