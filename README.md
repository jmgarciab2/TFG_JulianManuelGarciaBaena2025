```mermaid
graph TD
    subgraph Frontend
        A[FrontPantallaVisualizacion.py<br>Streamlit App]
    end

    subgraph Servidores Backend
        B[Backend Autenticación<br>auth_backend.py<br>Flask :5002]
        C[Backend Procesamiento CVs<br>tu_backend_principal.py<br>Flask :5001]
    end

    subgraph Almacenamiento
        D[usuarios.json<br>Datos de Usuario Hash]
        E[historial_ejecuciones.json<br>Historial Análisis IA]
        F[cvs_recibidos/<br>Archivos CV (Modo Manual)]
    end

    %% Conexiones principales
    A --> B; %% Interacción Frontend <-> Auth Backend
    A --> C; %% Interacción Frontend <-> CV Backend

    B --> D; %% Auth Backend <-> Almacenamiento Usuarios

    %% Conexiones del CV Backend a Almacenamiento (depende del modo)
    C --> E; %% CV Backend <-> Almacenamiento Historial (Modo IA)
    C --> F; %% CV Backend <-> Almacenamiento Archivos (Modo Manual)

    %% Flujo de respuestas (para claridad adicional)
    B -- Respuesta Login/Registro --> A;
    C -- Resultados Procesamiento<br>Historial/Detalles<br>Confirmación Guardado --> A;
```
