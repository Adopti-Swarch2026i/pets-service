# Auditoría de Seguridad - Pets Service

Basado en la teoría de Seguridad (CIA Triad, Tácticas y Patrones Arquitectónicos):

## Cumple

### Tácticas: Resistir Ataques
*   **Encrypt Data:** FastAPI/Uvicorn expone únicamente el puerto **8443** con TLS mutuo (`--ssl-keyfile`, `--ssl-certfile`, `--ssl-ca-certs`, `--ssl-cert-reqs 2`). El flag `2` equivale a `CERT_REQUIRED` en Python/OpenSSL, exigiendo que el cliente presente un certificado válido (mTLS). La versión mínima de TLS está implícita en la configuración de Uvicorn/OpenSSL del contenedor base.
*   **Authenticate Actor:** 
    *   **mTLS mutua:** `--ssl-cert-reqs 2` fuerza la presentación y validación del certificado de cliente contra la CA interna.
    *   **Aplicación (JWT/Firebase):** `app/core/security.py` utiliza `firebase_admin` para verificar tokens ID de Firebase en el header `Authorization`. Si las credenciales no están configuradas, el servicio falla en el arranque (`fail-fast`).
*   **Limit Access:** 
    *   En docker-compose solo se expone el puerto **8443** internamente; no hay mapeo de puerto al host. El tráfico entra únicamente vía gateway NGINX.
    *   CORS configurado mediante variable de entorno `CORS_ALLOWED_ORIGINS`.
*   **Change Default Settings:** 
    *   No hay passwords hardcodeadas en el código fuente; todas las credenciales se inyectan por variables de entorno.
    *   PostgreSQL se conecta con `sslmode=verify-full` y `sslrootcert=/app/certs/ca.crt`, validando tanto el cifrado como la identidad del servidor de base de datos.
    *   RabbitMQ se conecta vía **AMQPS 5671** (`amqps://...`). El publisher (`app/messaging/publisher.py`) detecta automáticamente el esquema `amqps://` y construye un `ssl.SSLContext` con el CA correcto.

### Tácticas: Detectar Ataques / Recuperar
*   **Maintain Audit Trail:** Logs estructurados de FastAPI/Uvicorn. Endpoint de healthcheck (`/health`) disponible. Healthcheck en docker-compose realiza petición HTTPS con certificado de cliente (`curl -fk --cert ... --key ... https://localhost:8443/health`).

## No Cumple / Gaps conocidos
*   **Healthcheck del Dockerfile:** El Dockerfile actual no incluye instrucción `HEALTHCHECK`. El healthcheck se define únicamente en `Compose/docker-compose.yml`. Recomendación: añadir `HEALTHCHECK` al Dockerfile para portabilidad.
*   **Usuario root en contenedor:** El Dockerfile no define un usuario no privilegiado (`USER`). El proceso Uvicorn corre como root dentro del contenedor.

## Decisiones del Laboratorio 5
*   **Aplicación del Secure Channel Pattern en este servicio:** Se migró el servicio de HTTP plano a HTTPS en el puerto 8443 con autenticación mutua (mTLS) usando Uvicorn con `--ssl-cert-reqs 2`. La conexión a PostgreSQL se endureció a `sslmode=verify-full` con certificado CA raíz. La comunicación con RabbitMQ se migró a AMQPS 5671 con `SSLContext` personalizado en el publisher, cerrando completamente el canal de eventos en texto plano.
