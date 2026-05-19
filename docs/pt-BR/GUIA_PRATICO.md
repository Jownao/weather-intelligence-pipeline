# Guia Prático — Como Usar o Projeto Diariamente

Este guia explica como o projeto funciona, como executar e customizar para uso efetivo.

## O Que o Projeto Faz (Em Poucas Palavras)

```
Open-Meteo API → Airflow extrai → Pandas transforma → BigQuery armazena
```

Basicamente:
1. **Extract**: Busca dados climáticos de uma API pública (Open-Meteo)
2. **Transform**: Limpa, padroniza e calcula métricas
3. **Load**: Armazena em camadas (Bronze/Silver/Gold) no BigQuery
4. **Schedule**: Tudo roda automaticamente todos os dias (via Airflow)

## Como Rodar Diariamente

### Opção 1: Via Docker (Recomendado para produção local)

1. **Iniciar a stack** (Airflow + Postgres):
```bash
docker-compose up -d
```

2. **Acessar Airflow Web UI**:
   - URL: `http://localhost:8080`
   - Usuário: `admin` / Senha: `admin`

3. **Monitorar DAGs**:
   - Na UI, clique em "DAGs" no menu esquerdo
   - Procure por `weather_etl_daily` — mostra histórico de execuções
   - Clique na DAG → "Graph" para ver o fluxo (extract → transform → load)

4. **Ver logs de erros**:
   - Na DAG, clique em uma task (ex: `extract_weather_data`)
   - Abra a aba "Logs" para ver o que aconteceu

### Opção 2: Rodar scripts manualmente (Dev/testes)

Se quiser testar sem Airflow:

```bash
# Setup inicial (criar tabelas no BigQuery)
python scripts/setup_bigquery.py

# Simular uma extração
python -c "from pipeline.extractors.open_meteo import OpenMeteoClient; client = OpenMeteoClient(); data = client.get_last_30_days(-23.5505, -46.6333); print(f'Fetched {len(data)} records')"
```

## Como Customizar

### 1. Adicionar Uma Nova Região

Exemplo: monitorar São Paulo e Rio de Janeiro

**Editar `config/regions.yaml`**:
```yaml
regions:
  - name: "Sao Paulo"
    latitude: -23.5505
    longitude: -46.6333
    region_code: "SP"
    user_segment: "metropolitan"
    
  - name: "Rio de Janeiro"
    latitude: -22.9068
    longitude: -43.1729
    region_code: "RJ"
    user_segment: "metropolitan"
```

**Depois**:
- A DAG `weather_etl_daily` vai iterar sobre essas regiões automaticamente
- Dados de ambas vão para Bronze/Silver/Gold

### 2. Mudar Frequência de Execução

A pipeline roda **diariamente às 02:00 UTC** por padrão. Para mudar:

**Editar `dags/weather_etl_dag.py`**:
```python
# Procure por:
default_args = {
    "schedule_interval": "0 2 * * *",  # Este é o horário
    ...
}

# Exemplos de outras frequências:
# "0 */6 * * *"    → A cada 6 horas
# "0 12 * * *"     → Diariamente ao meio-dia
# "0 0 * * MON"    → Toda segunda-feira
# "*/15 * * * *"   → A cada 15 minutos
```

Salve, reinicie o Airflow:
```bash
docker-compose restart airflow-scheduler
```

### 3. Monitorar Dados no BigQuery

Via console do Google Cloud ou via CLI:

```bash
# Contar linhas na tabela Bronze
bq query --use_legacy_sql=false '
  SELECT COUNT(*) as total
  FROM `seu-projeto.weather_bronze.weather_raw`
'

# Ver últimas 10 linhas
bq query --use_legacy_sql=false '
  SELECT extraction_timestamp, region_name, temperature_2m
  FROM `seu-projeto.weather_bronze.weather_raw`
  ORDER BY extraction_timestamp DESC
  LIMIT 10
'
```

### 4. Adicionar Alertas de Erro (Email/Slack)

**Editar `dags/weather_etl_dag.py`**:
```python
default_args = {
    "owner": "data-team",
    "email_on_failure": True,
    "email": ["seu-email@empresa.com"],
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    # Para Slack (requer conexão):
    # "on_failure_callback": slack_notify,
}
```

Depois reinicie:
```bash
docker-compose restart airflow-scheduler
```

## Estrutura do Projeto (Para Navegar)

```
dags/
  └─ weather_etl_dag.py          ← Fluxo principal (extract → transform → load)

pipeline/
  ├─ extractors/open_meteo.py    ← Busca dados da API
  ├─ transformers/weather_transformer.py  ← Limpa e padroniza
  ├─ loaders/bigquery_loader.py  ← Escreve no BigQuery
  └─ validators/data_quality.py  ← Valida qualidade dos dados

config/
  ├─ regions.yaml                ← Regiões a monitorar
  └─ schema/                     ← Schemas das tabelas
      ├─ bronze_schema.json      ← Dados brutos
      ├─ silver_schema.json      ← Dados limpos
      └─ gold_schema.json        ← Dados agregados

tests/
  └─ unit/
      └─ test_loader_schema.py   ← Testa validação de schema

scripts/
  ├─ setup_bigquery.py           ← Cria datasets/tabelas (rodar uma vez)
  └─ generate_demo_gif.py        ← Gera GIF de demo

.env                             ← Credenciais e configurações (local)
docker-compose.yml               ← Stack local (Airflow + Postgres)
```

## Troubleshooting Rápido

### Problema: "Task extract_weather_data falhou"

1. Abra Airflow → clique na DAG → clique na task → aba "Logs"
2. Procure pela mensagem de erro
3. Causes comuns:
   - **Open-Meteo API indisponível**: espere alguns minutos e retry
   - **BigQuery permission denied**: check `.env` com `GCP_KEY_PATH` correto
   - **Coluna faltando em schema**: se adicionou campo novo, edite `config/schema/*.json`

### Problema: "ModuleNotFoundError: No module named 'pipeline'"

Dentro do Docker:
```bash
docker-compose exec airflow-webserver bash
echo $PYTHONPATH
```

Deve incluir `/opt/airflow:/opt/airflow/pipeline`. Se não, check `docker-compose.yml`.

### Problema: Nenhuma DAG aparece no Airflow

Reinicie o scheduler:
```bash
docker-compose restart airflow-scheduler
```

Depois espere 30s e recarregue a página do Airflow.

## Exemplo Prático: Monitore São Paulo + Rio

1. **Editar `config/regions.yaml`** (adicionar RJ):
```yaml
regions:
  - name: "Sao Paulo"
    latitude: -23.5505
    longitude: -46.6333
    region_code: "SP"
  
  - name: "Rio de Janeiro"
    latitude: -22.9068
    longitude: -43.1729
    region_code: "RJ"
```

2. **Reiniciar Airflow**:
```bash
docker-compose restart airflow-scheduler
```

3. **Trigger DAG manualmente** no Airflow:
   - Clique na DAG `weather_etl_daily`
   - Botão "Trigger DAG"
   - Monitore na aba "Graph"

4. **Ver dados no BigQuery**:
```bash
bq query '
  SELECT DISTINCT region_name, COUNT(*) as records
  FROM `seu-projeto.weather_bronze.weather_raw`
  GROUP BY region_name
'
```

Resultado esperado:
```
region_name      records
Sao Paulo        30
Rio de Janeiro   30
```

## Comandos Úteis do Dia-a-Dia

```bash
# Ver logs em tempo real
docker-compose logs -f airflow-scheduler

# Verificar status do container
docker-compose ps

# Rodar um teste unitário
python -m pytest tests/unit/test_loader_schema.py -v

# Executar um script fora do Airflow (local)
python scripts/setup_bigquery.py

# Parar a stack (sem deletar dados)
docker-compose down

# Reiniciar tudo
docker-compose down && docker-compose up -d
```

## Próximos Passos Para Produção

Se quiser levar para produção real:

1. **Migrar credenciais**: usar GCP Secret Manager em vez de arquivo local
2. **Auto-scaling**: colocar Airflow em Cloud Run ou GKE
3. **Data quality**: expandir `pipeline/validators/` com Great Expectations
4. **Alertas robustos**: integrar Slack/PagerDuty
5. **Backup**: configurar snapshots diários das tabelas BigQuery

Dúvidas? Verifique logs do Airflow ou rode `pytest -v` para validar.
