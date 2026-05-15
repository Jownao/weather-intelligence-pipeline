# 🌦️ Weather Intelligence Pipeline - SaaS Edition

**Enterprise-grade ELT pipeline** para análise climática em tempo real com Apache Airflow, Google BigQuery e Open-Meteo API gratuita.

## 📊 Visão Geral

Este projeto demonstra como construir uma **pipeline de dados em produção** que:

- ✅ Coleta dados climáticos em tempo real (Open-Meteo API)
- ✅ Processa com Airflow em DAGs gerenciáveis
- ✅ Implementa padrão **medallion architecture** (Bronze → Silver → Gold)
- ✅ Executa em containers Docker (pronto para qualquer cloud)
- ✅ Valida qualidade de dados com Great Expectations
- ✅ Gera insights analíticos por região e vertical SaaS

### Por que este projeto é diferente?

Diferente de tutoriais básicos, este projeto implementa:

- **Padrão Enterprise**: Medallion architecture como usado em Databricks/Delta Lake
- **Airflow Real**: DAGs com retry, alertas, logs estruturados
- **BigQuery Nativo**: Schemas definidos, particionamento, otimizações
- **Qualidade Garantida**: Validação em cada etapa com Great Expectations
- **Escalável**: Pronto para adicionar mais regiões e verticais de negócio

## 🏗️ Arquitetura

```
┌─────────────────┐
│  Open-Meteo API │  (Dados climáticos gratuitos)
└────────┬────────┘
         │
         ▼
┌──────────────────────────────────────┐
│     Apache Airflow (Orquestração)    │
│  ┌──────────────────────────────────┐│
│  │  DAG: weather_etl_daily          ││
│  │  ├─ Extract (Open-Meteo)         ││
│  │  ├─ Transform (Pandas)           ││
│  │  └─ Load (BigQuery)              ││
│  └──────────────────────────────────┘│
└──────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│        Google BigQuery (Data Warehouse)      │
│  ┌─────────────────────────────────────────┐ │
│  │ BRONZE: Raw Data (Imutável)             │ │
│  │ ├─ weather_raw (dados brutos)           │ │
│  └─────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────┐ │
│  │ SILVER: Cleaned Data (Transformado)     │ │
│  │ ├─ weather_cleaned (dados limpos)       │ │
│  └─────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────┐ │
│  │ GOLD: Analytics Ready (Agregado)        │ │
│  │ ├─ weather_aggregates (por região)      │ │
│  └─────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│   BI / Aplicações (Power BI, etc)    │
│   - Delivery: volume x chuva         │
│   - Fitness: demanda x temperatura   │
│   - Agro: produtividade x clima      │
└──────────────────────────────────────┘
```

## 📁 Estrutura do Projeto

```
weather-intelligence-pipeline/
├── dags/                              # Apache Airflow DAGs
│   ├── weather_etl_dag.py            # DAG principal (diária)
│   └── backfill_dag.py                # DAG para backfill histórico
│
├── pipeline/                          # Core de negócio (reutilizável)
│   ├── extractors/
│   │   └── open_meteo.py             # Client da API
│   ├── transformers/
│   │   └── weather_transformer.py    # Limpeza e enriquecimento
│   ├── loaders/
│   │   └── bigquery_loader.py        # Escrita BigQuery
│   └── validators/
│       └── data_quality.py           # Great Expectations + checks custom
│
├── config/
│   ├── regions.yaml                  # Regiões SaaS monitoradas
│   └── schema/
│       ├── bronze_schema.json        # Schema raw
│       ├── silver_schema.json        # Schema limpo
│       └── gold_schema.json          # Schema agregado
│
├── sql/                               # Queries BigQuery (ELT)
│   ├── silver_transform.sql          # Raw → Limpo
│   └── gold_aggregations.sql         # Agregações analíticas
│
├── tests/
│   ├── unit/                         # Testes unitários
│   └── integration/                  # Testes E2E
│
├── scripts/
│   ├── setup_bigquery.py             # Cria datasets e tabelas
│   └── generate_mock_data.py         # Dados para testes
│
├── docker/
│   ├── Dockerfile.airflow            # Imagem customizada
│   └── entrypoint.sh
│
├── docker-compose.yml                # Stack local (Airflow + Postgres)
├── requirements.txt                  # Python dependencies
├── .env.example                      # Template de variáveis
├── Makefile                          # Comandos convenientes
└── README.md                         # Este arquivo
```

## 🚀 Quick Start

### 1. Clone e prepare o ambiente

```bash
cd weather-intelligence-pipeline
cp .env.example .env

# Edite .env com suas credenciais GCP
# GCP_PROJECT_ID=seu-projeto
```

### 2. Setup local (com Docker)

```bash
# Build e inicia containers
make docker-build
make docker-up

# Airflow Web UI
# http://localhost:8080
# Usuário: admin / Senha: admin
```

### 3. Setup BigQuery

```bash
# Configure credenciais GCP primeiro
gcloud auth login
gcloud config set project seu-projeto-id

# Cria datasets e tabelas
python scripts/setup_bigquery.py
```

### 4. Teste a pipeline

```bash
# Execute testes unitários
make test

# Execute testes de integração
make test-integration
```

### 5. Trigger manual da DAG

```bash
# No Airflow Web UI:
# 1. Localize "weather_etl_daily"
# 2. Clique em "Trigger DAG"
# 3. Monitore a execução em "Graph"
```

## 📚 Componentes Principais

### 1. **Extractor** (`pipeline/extractors/open_meteo.py`)

Cliente HTTP para Open-Meteo API com:
- Retry automático com backoff exponencial
- Suporte para dados históricos e forecast
- Logging estruturado

```python
from pipeline.extractors.open_meteo import OpenMeteoClient

client = OpenMeteoClient()
data = client.get_historical_weather(
    latitude=-23.5505,
    longitude=-46.6333,
    start_date="2024-01-01",
    end_date="2024-01-31"
)
```

### 2. **Transformer** (`pipeline/transformers/weather_transformer.py`)

Limpeza e enriquecimento com:
- Normalização de campos
- Tratamento de valores faltantes
- Cálculo de quality scores
- Categorização de condições climáticas

```python
from pipeline.transformers.weather_transformer import WeatherTransformer

df_clean, metrics = WeatherTransformer.clean_weather_data(df_raw)
print(metrics)  # {"initial_rows": 30, "rows_removed": 1, "invalid_rows": 0}
```

### 3. **Loader** (`pipeline/loaders/bigquery_loader.py`)

Carregamento em camadas:

```python
from pipeline.loaders.bigquery_loader import BigQueryLoader

loader = BigQueryLoader()

# Bronze (raw)
loader.load_to_bronze(df_raw)

# Silver (cleaned) via SQL transformations
# Gold (aggregated) via SQL transformations
```

### 4. **Validators** (`pipeline/validators/data_quality.py`)

Validação em tempo real:

```python
from pipeline.validators.data_quality import DataQualityValidator

validator = DataQualityValidator(min_quality_score=70.0)
report = validator.validate_cleaned_data(df, region="São Paulo")
```

## 🔄 DAG Principal: `weather_etl_daily`

Executa **diariamente às 02:00 UTC**:

```
Extract (Open-Meteo)
      ↓
Transform (Pandas)
      ↓
Load (BigQuery Bronze)
      ↓
[Trigger SQL] Silver & Gold
```

### Configuração

```python
# dags/weather_etl_dag.py
schedule_interval="0 2 * * *"    # Diário às 02:00 UTC
retries=2                         # 2 tentativas
retry_delay=5 minutes
```

## 🗄️ Camadas de Dados

### Bronze (Raw)
- ✅ **Dados brutos** da Open-Meteo API
- ✅ Imutável (append-only)
- ✅ Particionado por data
- ✅ Retenção: 1 ano

**Tabela**: `weather_bronze.weather_raw`

```sql
SELECT
  extraction_timestamp,
  region_name,
  date,
  temperature_2m,
  precipitation_sum,
  relative_humidity_2m,
  raw_response  -- JSON completo
FROM `project.weather_bronze.weather_raw`
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
```

### Silver (Cleaned)
- ✅ **Dados limpos e padronizados**
- ✅ Valores faltantes tratados
- ✅ Outliers removidos
- ✅ Quality scores calculados
- ✅ Particionado por data

**Tabela**: `weather_silver.weather_cleaned`

```sql
SELECT
  weather_id,
  region_name,
  date,
  temperature_celsius,
  humidity_percentage,
  precipitation_mm,
  wind_speed_kmh,
  weather_condition,
  data_quality_score,
  is_valid
FROM `project.weather_silver.weather_cleaned`
WHERE is_valid = TRUE
```

### Gold (Analytics Ready)
- ✅ **Agregações por região e período**
- ✅ Métricas de negócio calculadas
- ✅ Pronto para BI e dashboards
- ✅ Particionado por data

**Tabela**: `weather_gold.weather_aggregates`

```sql
SELECT
  metric_date,
  region_name,
  saas_vertical,
  avg_temperature_celsius,
  total_precipitation_mm,
  rainy_days,
  extreme_temperature_days
FROM `project.weather_gold.weather_aggregates`
ORDER BY metric_date DESC, region_name
```

## 🎯 Casos de Uso SaaS

### 1. **Delivery Apps** 📦
Correlaciona clima com volume de pedidos:

```sql
SELECT
  g.metric_date,
  g.region_name,
  g.rainy_days,
  g.avg_temperature_celsius,
  -- JOIN com métricas de negócio
  -- Para encontrar padrões: "Chuva aumenta pedidos em 30%"
FROM weather_gold.weather_aggregates g
WHERE g.saas_vertical = 'delivery'
```

### 2. **Fitness Apps** 🏃
Entende demanda por atividades outdoor:

```sql
SELECT
  g.metric_date,
  g.region_name,
  g.avg_temperature_celsius,
  g.cloudcover_percentage,
  -- Usuários evitam exercícios quando muito quente/frio/nublado
FROM weather_gold.weather_aggregates g
WHERE g.saas_vertical = 'fitness'
```

### 3. **Agronegócio** 🌾
Prediz produtividade e necessidade de irrigação:

```sql
SELECT
  g.metric_date,
  g.region_name,
  g.total_precipitation_mm,
  g.avg_temperature_celsius,
  -- Modelos de ML correlacionam com produção esperada
FROM weather_gold.weather_aggregates g
WHERE g.saas_vertical = 'agronegocio'
```

## 🧪 Testes

### Unit Tests

```bash
# Rodar todos os testes unitários
make test

# Com coverage
pytest tests/unit -v --cov=pipeline
```

**Testes inclusos:**
- ✅ `test_extractor.py`: API client, retry logic, parsing
- ✅ `test_transformer.py`: Limpeza, outliers, quality scores
- ✅ `test_loader.py`: BigQuery integration (placeholder)

### Integration Tests

```bash
make test-integration
```

Testa pipeline E2E com dados mock.

### Testes Manuais

```bash
# Gera dados mock para testes
python scripts/generate_mock_data.py

# Testa transformação localmente
python -c "
from pipeline.extractors.open_meteo import OpenMeteoClient
from pipeline.transformers.weather_transformer import WeatherTransformer

client = OpenMeteoClient()
data = client.get_last_30_days(latitude=-23.5505, longitude=-46.6333)
df = WeatherTransformer.transform_open_meteo_response(data, 'São Paulo', 'SP')
print(f'Transformed {len(df)} records')
"
```

## 📋 Checklist de Setup Completo

- [ ] Clonar repositório
- [ ] Copiar `.env.example` → `.env` e configurar GCP
- [ ] Executar `gcloud auth login` (autenticação GCP)
- [ ] Executar `make docker-build && make docker-up`
- [ ] Acessar Airflow em `http://localhost:8080`
- [ ] Executar `python scripts/setup_bigquery.py`
- [ ] Executar `make test` para validar
- [ ] Trigger manual da DAG `weather_etl_daily`
- [ ] Verificar dados em BigQuery
- [ ] Customizar `config/regions.yaml` com suas regiões

## 🔧 Configuração Avançada

### Adicionar Nova Região

**1. Editar `config/regions.yaml`:**

```yaml
- name: "Brasília"
  latitude: -15.8267
  longitude: -47.8711
  region_code: "DF"
  user_segment: "metropolitan"
```

**2. Atualizar DAG para iterar regiões:**

```python
# dags/weather_etl_dag.py (próximas versões)
regions = load_regions_from_yaml()
for region in regions:
    # Criar task dinamicamente
```

### Mudar Frequência da Pipeline

```python
# dags/weather_etl_dag.py
schedule_interval="0 */6 * * *"  # A cada 6 horas
schedule_interval="0 12 * * *"   # Diariamente ao meio-dia
schedule_interval="0 0 * * MON"  # Toda segunda-feira
```

### Ativar Alertas

```python
# dags/weather_etl_dag.py
default_args = {
    "email_on_failure": True,
    "email": ["seu-email@empresa.com"],
    ...
}
```

## 📊 Monitoramento

### BigQuery Logs

```sql
-- Ver últimas cargas
SELECT
  creation_time,
  project_id,
  dataset_id,
  table_id,
  TIMESTAMP_MILLIS(load_time) as load_duration_ms
FROM `project.region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE job_type = 'LOAD'
ORDER BY creation_time DESC
LIMIT 10
```

### Airflow Logs

```bash
# Logs em tempo real
docker-compose logs -f airflow-scheduler

# Logs de uma task específica
docker-compose logs airflow-webserver | grep extract_weather
```

## 🚨 Troubleshooting

### Erro: "No module named 'pipeline'"

```bash
# Adicione ao PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/weather-intelligence-pipeline"

# Ou no docker-compose.yml (já está configurado)
PYTHONPATH=/opt/airflow:/opt/airflow/pipeline
```

### Erro: "Google Cloud credentials not found"

```bash
# Configure credenciais
gcloud auth application-default login

# Ou aponte para arquivo de chave
export GOOGLE_APPLICATION_CREDENTIALS=/caminho/para/gcp-key.json
```

### DAG não aparece no Airflow

```bash
# Verifique sintaxe Python
python -m py_compile dags/weather_etl_dag.py

# Reinicie scheduler
docker-compose restart airflow-scheduler
```

## 📚 Recursos

- **Open-Meteo API**: https://open-meteo.com
- **Apache Airflow Docs**: https://airflow.apache.org
- **BigQuery SQL Docs**: https://cloud.google.com/bigquery/docs
- **Great Expectations**: https://greatexpectations.io

## 📄 Licença

MIT License - veja LICENSE para detalhes.

## 👤 Autor

Desenvolvido como projeto de portfólio para demonstrar conhecimento em:
- ELT pipelines com Airflow
- BigQuery e arquitetura de dados
- Data quality e validação
- Docker e orquestração
- SaaS data analytics

---

**⭐ Dúvidas ou sugestões?** Abra uma issue ou discussion!

## 🧭 Instalação: local vs Docker

- Para desenvolvimento local leve (scripts, transformer, testes): use o `requirements.txt` (arquivo leve, sem Airflow/GCP).
- Para rodar o stack completo (Airflow + BigQuery providers) utilize Docker — o container usa `requirements-docker.txt`.

Comandos recomendados:

```bash
# Instalação local (venv)
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
.venv\Scripts\activate     # Windows Powershell
pip install -r requirements.txt

# Build e subir stack via Docker (recomendado para Airflow)
make docker-build
make docker-up
```

Se ocorrerem erros ao instalar pacotes pesados no Windows (por exemplo `apache-airflow` ou `google-cloud-*`), prefira a opção Docker.
