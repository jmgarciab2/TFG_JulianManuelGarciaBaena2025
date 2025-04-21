```mermaid
graph TD
    %% Subgrafo para las interfaces (Frontend)
    subgraph Frontend
        A[FrontPantallaVisualizacion.py<br>Streamlit App]
    end

    %% Subgrafo para los servicios de Backend
    subgraph Servidores Backend
        B[Backend Autenticación<br>auth_backend.py<br>Flask :5002]
        C[Backend Procesamiento CVs<br>tu_backend_principal.py<br>Flask :5001]
    end

    %% Subgrafo para el almacenamiento persistente
    subgraph Almacenamiento
        D[usuarios.json<br>Datos de Usuario Hash]
        E[historial_ejecuciones.json<br>Historial Análisis IA]
        F[cvs_recibidos/<br>Archivos CV (Modo Manual)]
    end

    %% Conexiones desde el Frontend
    A -- Solicitud Login/Registro --> B;
    A -- Solicitud Procesar CV<br>Obtener Historial/Detalles --> C;

    %% Conexiones de los Backends al Almacenamiento
    B -- Leer/Escribir Datos --> D;

    %% Conexiones del Backend de CVs (depende del modo)
    %% Si el backend de CVs es el que usa IA:
    C -- Leer/Escribir Resultados Análisis --> E;

    %% Si el backend de CVs es el 'manual' (solo guarda archivos):
    C -- Guardar Archivos PDF --> F;


    %% Respuestas de los Backends al Frontend
    B -- Estado Login/Registro<br>Datos de Usuario --> A;
    C -- Resultados Análisis<br>Historial/Detalles<br>Confirmación Guardado --> A;

    %% Relaciones adicionales (opcional, no directas por API)
    %% E -- Leído por --> A; %% Historial se obtiene vía Backend C
    %% F -- Revisado manualmente --> Humano[Usuario/Reclutador]; %% Flujo de trabajo en modo manual
```
