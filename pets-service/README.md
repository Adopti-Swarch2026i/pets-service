# Pets Service

Microservicio encargado de la gestión y publicación de mascotas perdidas/encontradas. Construido con FastAPI y estructurado siguiendo principios de **Arquitectura Hexagonal / Capas**.

## Requisitos Previos

- Python 3.12+
- PostgreSQL
- Credenciales de Firebase Admin SDK (`firebase-config/`)

## Configuración del Entorno

Configura las siguientes variables de entorno (puedes usar un archivo `.env`):

```env
# URL de conexión a la base de datos PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/pets_db

# Ruta al archivo JSON con las credenciales de Firebase
FIREBASE_CREDENTIALS=./firebase-config/serviceAccountKey.json
```

## Ejecución Local

1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

2. Ejecutar el servidor de desarrollo:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

## Arquitectura (Hexagonal)

El servicio está organizado en capas para asegurar el desacoplamiento (SRP, DRY):

- `api/`: Controladores HTTP (Routers pasivos).
- `services/`: Lógica de negocio (Reglas y orquestación).
- `crud/`: Repositorio (Capa de abstracción de datos con SQLAlchemy).
- `models/` & `schemas/`: Modelos de BD y DTOs (Pydantic).
- `exceptions/`: Manejo unificado de errores (excepciones de dominio -> respuestas HTTP).
- `core/`: Configuración y Seguridad (Firebase Auth).
