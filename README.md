# lcel-structured-extraction

Pipeline de extracción de entidades técnicas construido con **LangChain (LCEL)** y **Pydantic**.
Recibe un párrafo de texto sin procesar (una descripción de arquitectura, un log de error, etc.) y devuelve un objeto validado con las tecnologías mencionadas, el nivel de criticidad y un resumen técnico.

## Estructura del proyecto

```
.
├── schemas.py              # Contrato de salida (ExtraccionTecnica) y configuración del LLM (LLMConfig)
├── chain.py                # Prompt template, cadena LCEL, validación, reintentos y process_text()
├── run_tests.py            # Mini-script de prueba asíncrono
├── clients/
│   ├── langchain_factory.py  # Devuelve el chat model según el proveedor configurado
│   ├── openai_model.py       # ChatOpenAI (OpenAI y NVIDIA NIM)
│   ├── anthropic_model.py    # ChatAnthropic
│   └── gemini_model.py       # ChatGoogleGenerativeAI
├── requirements.txt
└── .env.example
```

## Componentes

### 1. Esquema Pydantic (`schemas.py`)

```python
class Criticidad(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"

class ExtraccionTecnica(BaseModel):
    tecnologias: list[str]            # min_length=1 -> la lista no puede estar vacía
    nivel_de_criticidad: Criticidad   # enum: baja | media | alta
    resumen_tecnico: str              # entre 20 y 256 caracteres
```

Restricciones del contrato:
- `tecnologias` debe tener al menos un elemento.
- `nivel_de_criticidad` solo acepta `baja`, `media` o `alta`.
- `resumen_tecnico` debe tener entre 20 y 256 caracteres.

### 2. Prompt Template (`chain.py`)

Se usa `ChatPromptTemplate.from_messages(...)` con un mensaje de sistema que define las reglas de extracción y un mensaje humano con la variable `{text}`.

### 3. Cadena LCEL (`chain.py`)

```python
structured_model = model.with_structured_output(ExtraccionTecnica, include_raw=True)

chain = PROMPT | structured_model | RunnableLambda(_validar_salida)
```

Se usa `include_raw=True` para tener acceso al mensaje crudo del modelo y poder inspeccionar el `finish_reason` antes de aceptar el objeto.

### 4. Lógica de resiliencia

`_validar_salida` revisa la respuesta antes de devolverla y lanza una excepción si:
- el modelo cortó la respuesta por falta de tokens (`finish_reason` / `stop_reason` igual a `length`, `max_tokens` o `MAX_TOKENS`) → `RespuestaIncompletaError`;
- la salida no cumple el esquema (JSON mal formado o incompleto) → `OutputParserException` / `ValidationError`;
- el modelo no devolvió una salida estructurada.

La cadena completa se envuelve con `.with_retry()`:

```python
chain.with_retry(
    retry_if_exception_type=(OutputParserException, ValidationError, RespuestaIncompletaError),
    stop_after_attempt=3,
    wait_exponential_jitter=True,
)
```

Es decir, hasta **3 intentos** con espera exponencial ante cualquiera de esos errores.

### 5. Función asíncrona `process_text`

```python
async def process_text(text: str) -> ExtraccionTecnica:
    ...
    resultado = await build_chain().ainvoke({"text": text})
```

Ejecuta la cadena con `.ainvoke()` y registra con `logging` el proveedor/modelo usado, la validación con Pydantic, los reintentos (respuesta truncada o fuera de esquema) y el error final si se agotan los intentos.

## Instalación

Requiere Python 3.10+ (probado con 3.13).

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

## Configuración

Copiar `.env.example` a `.env` y completar:

```env
LLM_PROVIDER=openai          
LLM_MODEL=gpt-4o-mini        
LLM_API_KEY=tu-api-key
```

Variables opcionales:

| Variable          | Default | Descripción                     |
|-------------------|---------|---------------------------------|
| `LLM_TEMPERATURE` | `0`     | Temperatura del modelo          |
| `LLM_MAX_TOKENS`  | `1024`  | Máximo de tokens de la respuesta |

## Uso

### Mini-script de prueba

Corre la cadena contra 5 textos de ejemplo (caída de servicio, degradación de rendimiento, descripción de arquitectura, incidente de seguridad y un **texto ambiguo** como prueba de estrés) y compara la criticidad obtenida con la esperada:

```bash
python run_tests.py
```

Procesar un texto puntual:

```bash
python run_tests.py "WARN [api] Redis sin memoria, la API en FastAPI responde lento"
```

### Desde código

```python
import asyncio
from chain import process_text

resultado = asyncio.run(process_text(
    "La API en FastAPI usa Redis como caché y PostgreSQL como base de datos. "
    "Bajo carga alta, el pool de conexiones a PostgreSQL se agota y las requests fallan."
))
print(resultado.model_dump_json(indent=2))
```

## Ejemplo de salida

Entrada:

```
La API en FastAPI usa Redis como caché y PostgreSQL como base de datos.
Bajo carga alta, el pool de conexiones a PostgreSQL se agota y las requests fallan.
```

Salida (objeto `ExtraccionTecnica` validado):

```json
{
  "tecnologias": ["FastAPI", "Redis", "PostgreSQL"],
  "nivel_de_criticidad": "alta",
  "resumen_tecnico": "API con caché en Redis y persistencia en PostgreSQL; cuello de botella en conexiones concurrentes."
}
```

Ejemplo de salida de `python run_tests.py`:

```
[1/5] Caída de servicio
  tecnologias:         PostgreSQL, Kubernetes
  nivel_de_criticidad: alta
  resumen_tecnico:     El payment-service no puede conectarse a PostgreSQL y el pod entra en CrashLoopBackOff, impidiendo completar pagos.
  -> OK (2.1s)
...
Resultado: 5/5 casos OK
```