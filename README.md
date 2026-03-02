# Pets Service - Sistema de Mascotas Perdidas y Encontradas

Servicio Backend para gestionar reportes de mascotas perdidas y encontradas. Desarrollado en Python con FastAPI y PostgreSQL. El proyecto también está containerizado con Docker para facilitar su despliegue y desarrollo local.

## 📖 Documentación

La documentación detallada con los endpoints de la API, carga útil esperada y configuraciones internas se encuentra en la carpeta del servicio principal:
👉 **[Ver Documentación y Endpoints de la API](./pets-service/README.md)**

## 🚀 Requerimientos

- **Docker** y **Docker Compose** (Para levantar la base de datos de manera automatizada).
- **Python 3.12+** (Si se ejecuta el servicio de manera nativa).
- Archivo `.env` configurado.
- Credenciales de Firebase Admin SDK.

## ⚙️ Cómo Ejecutarlo

El método más recomendado para este repositorio es utilizando Docker Compose para levantar la BBDD rápidamente.

1. **Configurar las credenciales:**
   Coloca tu archivo `serviceAccountKey.json` de Firebase dentro del directorio `./firebase-config/`.

2. **Levantar la base de datos:**
   ```bash
   docker-compose up -d db
   ```

3. **Ejecutar el backend:**
   Accede a la carpeta principal del servicio, instala dependencias e inicia el servidor de desarrollo:
   ```bash
   cd pets-service
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```

*Nota: Una vez en ejecución, la interfaz interactiva de Swagger estará en `http://localhost:8000/docs`.*
