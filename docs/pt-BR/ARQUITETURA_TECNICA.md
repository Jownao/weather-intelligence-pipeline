# Arquitetura Técnica — Como os Componentes Funcionam

Este documento explica o fluxo técnico de ponta a ponta e como cada componente se comunica.

## Fluxo de Dados (Visualizado)

```
┌──────────────────────┐
│  Open-Meteo API      │  (Dados climáticos públicos)
│  get_historical_...  │
└──────────┬───────────┘
           │ JSON payload
           ▼
┌──────────────────────────────────────────────┐
│  Airflow DAG: weather_etl_daily              │
│  ┌─────────────────────────────────────────┐ │
│  │ Task 1: extract_weather_data            │ │
│  │ - Chama OpenMeteoClient                 │ │
│  │ - Busca últimos 30 dias                 │ │
│  │ - Retorna lista de dicts (JSON)         │ │
│  │ - Pusha para XCom (exchange entre tasks)│ │
│  └─────────────────────────────────────────┘ │
│         │ XCom: raw data
│         ▼
│  ┌─────────────────────────────────────────┐ │
│  │ Task 2: transform_weather_data          │ │
│  │ - Pega dados do XCom                    │ │
│  │ - Converte para DataFrame pandas        │ │
│  │ - Limpa, valida, calcula quality_score │ │
│  │ - Retorna DF normalizado (Records)      │ │
│  │ - Pusha para XCom (JSON-safe)           │ │
│  └─────────────────────────────────────────┘ │
│         │ XCom: clean records
│         ▼
│  ┌─────────────────────────────────────────┐ │
│  │ Task 3: load_to_bigquery                │ │
│  │ - Pega DataFrame limpo                  │ │
│  │ - Valida schema (REQUIRED cols, types)  │ │
│  │ - Load para weather_bronze.weather_raw  │ │
│  │ - Parte-se o DF por schema columns      │ │
│  └─────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  Google BigQuery                             │
│  ┌──────────────────┐                       │
│  │ BRONZE Layer     │  (raw, imutável)      │
│  │ weather_bronze.  │                       │
│  │   weather_raw    │  ← Dados carregados   │
│  └──────────────────┘                       │
│  ┌──────────────────┐                       │
│  │ SILVER Layer     │  (limpo, via SQL)     │
│  │ weather_silver.  │                       │
│  │   weather_...    │  ← Transformações SQL │
│  └──────────────────┘                       │
│  ┌──────────────────┐                       │
│  │ GOLD Layer       │  (agregado, pronto BI)│
│  │ weather_gold.    │                       │
│  │   aggregates     │  ← Métricas finais    │
│  └──────────────────┘                       │
└──────────────────────────────────────────────┘
```

## Detalhamento de Cada Componente

### 1. OpenMeteoClient (`pipeline/extractors/open_meteo.py`)

**O que faz**: Busca dados da Open-Meteo API

**Métodos principais**:
```python
client = OpenMeteoClient()

# Buscar últimos 30 dias (histórico)
data = client.get_last_30_days(
    latitude=-23.5505, 
    longitude=-46.6333
)
# Retorna: Lista de dicts com chaves como 'date', 'temperature_2m', etc.

# Buscar previsão (forecast)
forecast = client.get_forecast(latitude, longitude)
```

**Características**:
- Retry automático (se API falhar, tenta de novo)
- Timeout de 10s por requisição
- Retorna JSON estruturado direto da API

### 2. WeatherTransformer (`pipeline/transformers/weather_transformer.py`)

**O que faz**: Limpa e padroniza dados

**Fluxo**:
```python
from pipeline.transformers.weather_transformer import WeatherTransformer

# Input: lista bruta da API
raw_data = [
    {"date": "2024-01-01", "temperature_2m": 25.5, ...},
    {"date": "2024-01-02", "temperature_2m": 26.0, ...},
]

# Transform
df, metrics = WeatherTransformer.clean_weather_data(raw_data)
# df = DataFrame limpo com colunas padronizadas
# metrics = dict com estatísticas (ex: "rows_removed": 2, "quality_score": 92.5)
```

**Operações de limpeza**:
1. Remove valores faltantes
2. Remove outliers (ex: temperatura > 60°C)
3. Calcula quality_score por linha (0-100)
4. Categoriza condição climática (sunny, rainy, cloudy, etc.)

**Output**: DataFrame com colunas:
- `date`, `region_name`, `latitude`, `longitude`
- `temperature_2m`, `humidity_2m`, `precipitation_sum`, `windspeed_10m`, `cloudcover`
- `weather_condition`, `data_quality_score`, `is_valid`

### 3. BigQueryLoader (`pipeline/loaders/bigquery_loader.py`)

**O que faz**: Escreve dados em camadas diferentes do BigQuery

**Métodos principais**:
```python
loader = BigQueryLoader(
    project_id="seu-projeto",
    dataset_bronze="weather_bronze",
    dataset_silver="weather_silver",
    dataset_gold="weather_gold"
)

# Load para Bronze (raw)
loader.load_to_bronze(df, table_name="weather_raw")

# Load para Silver (já limpo)
loader.load_to_silver(df, table_name="weather_cleaned")

# Load para Gold (agregado)
loader.load_to_gold(df, table_name="weather_aggregates")
```

**Validações**:
- Valida schema antes do load (checa colunas REQUIRED)
- Converte tipos (STRING → TIMESTAMP, INT64, FLOAT64)
- Cria dataset se não existir
- Particiona por data (`date` ou `metric_date`)

**Schemas** (em `config/schema/*.json`):
```json
{
  "fields": [
    {"name": "date", "type": "DATE", "mode": "REQUIRED"},
    {"name": "temperature_2m", "type": "FLOAT64", "mode": "NULLABLE"},
    ...
  ]
}
```

### 4. DAG Principal (`dags/weather_etl_dag.py`)

**O que é**: Orquestração das tasks via Airflow

**Estrutura**:
```python
dag = DAG(
    'weather_etl_daily',
    schedule_interval='0 2 * * *',  # Diariamente às 02:00 UTC
    default_args={
        'retries': 2,
        'retry_delay': timedelta(minutes=5),
    }
)

# Task 1: Extract
extract_task = PythonOperator(
    task_id='extract_weather_data',
    python_callable=extract_weather_data,  # Chama função
    op_kwargs={'regions': load_regions_yaml()}  # Passa regiões
)

# Task 2: Transform (depende de Task 1)
transform_task = PythonOperator(
    task_id='transform_weather_data',
    python_callable=transform_weather_data,
)

# Task 3: Load (depende de Task 2)
load_task = PythonOperator(
    task_id='load_to_bigquery',
    python_callable=load_to_bigquery,
)

# Dependências
extract_task >> transform_task >> load_task
```

**XCom (comunicação entre tasks)**:
- Task 1 pusha resultado para XCom com chave "weather_data"
- Task 2 puxa de XCom, processa, pusha "transformed_data"
- Task 3 puxa e carrega em BigQuery

**Exemplo de XCom**:
```python
# Task 1: push
ti.xcom_push(key="weather_data", value=extracted_list)

# Task 2: pull
extracted_data = ti.xcom_pull(task_ids="extract_weather_data", key="weather_data")
```

## Fluxo de Dados Hora-a-Hora

### 02:00 UTC (início da execução)
1. Airflow scheduler acorda
2. Dispara DAG `weather_etl_daily`
3. Task 1 começa

### 02:00 UTC até 02:05 (extração)
- OpenMeteoClient busca 30 dias para cada região em `config/regions.yaml`
- Resultado (lista de dicts) é pushed para XCom
- Exemplo: 31 dias × 3 regiões = 93 registros

### 02:05 até 02:10 (transformação)
- Transformer pega XCom
- Converte para DataFrame
- Limpa (remove NaNs, outliers)
- Calcula quality_score
- Pusha DataFrame limpo para XCom

### 02:10 até 02:15 (carga)
- Loader pega DataFrame
- Valida schema (checa REQUIRED columns)
- Escreve 93 linhas em `weather_bronze.weather_raw`
- BigQuery partição automática por `date`

### 02:15 em diante (pós-execução)
- DAG marca-se como SUCCESS no Airflow
- Dados pronto em BigQuery para consultas
- Próxima execução: amanhã às 02:00 UTC

## Particionamento e Retenção

### Bronze
- Particionado por `date`
- Retenção: 1 ano (365 dias)
- Tamanho estimado: ~100MB/ano para 3 regiões

### Silver
- Limpo + enriquecido
- Particionado por `date`
- Retenção: 2 anos

### Gold
- Agregado por `region_name` + `metric_date`
- Particionado por `metric_date`
- Retenção: 5 anos (para histórico analítico)

## Como Debugar

### Ver logs da DAG
```bash
# Logs em tempo real
docker-compose logs -f airflow-scheduler

# Logs de uma task específica
docker-compose logs airflow-webserver | grep extract_weather
```

### Testar transform localmente
```python
from pipeline.transformers.weather_transformer import WeatherTransformer
import pandas as pd

# Dados fake
df = pd.DataFrame({
    'date': ['2024-01-01', '2024-01-02'],
    'temperature_2m': [25.0, 26.0],
    'humidity_2m': [60, 65],
})

df_clean, metrics = WeatherTransformer.clean_weather_data(df)
print(f"Rows removed: {metrics['rows_removed']}")
print(f"Quality score: {df_clean['data_quality_score'].mean()}")
```

### Validar schema antes de load
```python
from pipeline.loaders.bigquery_loader import BigQueryLoader

loader = BigQueryLoader()
try:
    loader.validate_df_schema(df, "weather_bronze", "weather_raw")
    print("Schema OK!")
except ValueError as e:
    print(f"Schema error: {e}")
```

## Próximas Arquiteturas Possíveis

Se crescer para produção:

1. **Cloud Composer** (Airflow gerenciado no GCP)
2. **Pub/Sub** para queueing assíncrono
3. **Cloud Functions** para transformações em tempo real
4. **Looker** para BI integrado ao BigQuery
5. **dbt** para transformações Silver/Gold em SQL
