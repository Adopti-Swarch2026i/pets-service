# Pets Service

Microservicio encargado de la gestión y publicación de reportes de mascotas perdidas y encontradas.

## Requisitos y Configuración

Configura las siguientes variables de entorno (puedes usar un archivo `.env`):

```env
# Conexión a PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/pets_db

# Credenciales de Firebase Admin SDK
FIREBASE_CREDENTIALS=./firebase-config/serviceAccountKey.json
```

Para ejecutar localmente:
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
*Swagger UI disponible en: `http://localhost:8000/docs`*

---

## Documentación de la API

Todas las rutas operan bajo el prefijo `/api/pets`. Los endpoints que requieren autenticación necesitan el header `Authorization: Bearer <Firebase-ID-Token>`.

### 1. Obtener Estadísticas
* **Ruta:** `GET /stats`
* **Auth:** No
* **Respuesta:**
  ```json
  {
    "total_reports": 10,
    "lost": 6,
    "found": 4
  }
  ```

### 2. Listar Reportes
* **Ruta:** `GET /`
* **Auth:** No
* **Query Params (Opcionales):**
  * `status` (String): "lost" o "found"
  * `type` (String): "dog", "cat", etc.
* **Respuesta:** Lista de objetos `Report`.

### 3. Obtener Reporte por ID
* **Ruta:** `GET /{id}`
* **Auth:** No
* **Respuesta:** Objeto `Report` detallado.

### 4. Crear un Reporte
* **Ruta:** `POST /`
* **Auth:** **Sí**
* **Body (JSON):**
  ```json
  {
    "name": "Firulais",
    "type": "dog",
    "breed": "Labrador",
    "color": "Dorado",
    "status": "lost",
    "location": "Parque Central",
    "description": "Llevaba collar rojo"
  }
  ```
* **Respuesta:** Objeto `Report` creado.

### 5. Actualizar un Reporte
* **Ruta:** `PUT /{id}`
* **Auth:** **Sí** (Solo el owner_id original)
* **Body:** Mismo formato que creación.

### 6. Eliminar un Reporte
* **Ruta:** `DELETE /{id}`
* **Auth:** **Sí** (Solo el owner_id original)
* **Respuesta:** `{"message": "Deleted"}`
