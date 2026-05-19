# FAQ & Troubleshooting

Respostas para dúvidas comuns e soluções de problemas.

## FAQ

### P: Quantas vezes por dia a pipeline roda?

**R**: Por padrão, **1 vez por dia às 02:00 UTC** (conforme `schedule_interval` na DAG).

Para mudar frequência, edite `dags/weather_etl_dag.py`:
```python
schedule_interval="0 2 * * *"  # Diário às 02:00 UTC
# Mude para:
schedule_interval="0 */4 * * *"  # A cada 4 horas
```

Depois reinicie:
```bash
docker-compose restart airflow-scheduler
```

### P: Quantos dias de histórico a pipeline coleta?

**R**: **Últimos 30 dias** (configurado em `OpenMeteoClient.get_last_30_days()`).

Se quiser mais, edite `pipeline/extractors/open_meteo.py`:
```python
def get_last_30_days(self, latitude, longitude):
    # Mude o número 30 para, ex, 90 (para últimos 90 dias)
    start_date = (date.today() - timedelta(days=30)).isoformat()
    ...
```

### P: Por que os dados aparecem em 3 tabelas (Bronze/Silver/Gold)?

**R**: Padrão Medallion (usado em Databricks/Delta Lake):

- **Bronze**: Raw data (imutável, backup histórico)
- **Silver**: Limpo, validado (dados confiáveis)
- **Gold**: Agregado, pronto para BI (métricas, dashboards)

Assim, se houver erro em produção, você pode "voltar" aos dados brutos (Bronze) e reprocessar.

### P: Posso rodar a pipeline manualmente?

**R**: Sim, via Airflow UI:

1. Abra `http://localhost:8080`
2. Procure DAG `weather_etl_daily`
3. Botão "Trigger DAG" (ou ícone play)
4. Executa imediatamente

Ou via CLI:
```bash
docker-compose exec airflow-webserver airflow dags trigger weather_etl_daily
```

### P: Como adiciono uma nova região?

**R**: Edit `config/regions.yaml` e adicione entrada:
```yaml
regions:
  - name: "Brasilia"
    latitude: -15.8267
    longitude: -47.8711
    region_code: "DF"
    user_segment: "metropolitan"
```

Na próxima execução, a pipeline coleta dados para Brasília também.

### P: Onde vejo erros se alguma coisa der errado?

**R**: 3 opções:

1. **Airflow Web UI** (recomendado):
   - Clique na DAG → Task → Logs
   - Mostra exatamente o que deu erro

2. **Docker logs**:
```bash
docker-compose logs -f airflow-scheduler
```

3. **BigQuery logs** (se erro for na carga):
```bash
bq ls -j | head  # Últimos jobs
bq show -j <job_id>  # Detalhes de um job
```

### P: Posso mudar o horário de execução?

**R**: Sim. No `dags/weather_etl_dag.py`:
```python
schedule_interval="0 2 * * *"  # Hora = 2 (02:00 UTC)

# Exemplos:
"0 12 * * *"     # Meio-dia (12:00 UTC)
"0 0 * * *"      # Meia-noite (00:00 UTC)
"0 */6 * * *"    # A cada 6 horas
"*/30 * * * *"   # A cada 30 minutos
```

Reinicie:
```bash
docker-compose restart airflow-scheduler
```

### P: Como limpo dados ou deleto uma execução errada?

**R**: Cuidado ao deletar — os dados Bronze são append-only (histórico).

Para remover registros de um dia específico:
```bash
bq query --use_legacy_sql=false "
DELETE FROM \`seu-projeto.weather_bronze.weather_raw\`
WHERE DATE(date) = '2024-05-18'
"
```

Ou recrie a tabela:
```bash
# Backup primeiro!
bq cp seu-projeto:weather_bronze.weather_raw seu-projeto:weather_bronze.weather_raw_backup

# Delete tabela
bq rm seu-projeto:weather_bronze.weather_raw

# Recrie (via script)
python scripts/setup_bigquery.py
```

## Troubleshooting

### Erro: "No module named 'google.cloud'"

**Causa**: Dependências não instaladas

**Solução**:
```bash
pip install -r requirements-dev.txt
# Ou apenas:
pip install google-cloud-bigquery
```

### Erro: "Permission denied" ao carregar em BigQuery

**Causa**: Credenciais GCP não configuradas ou inválidas

**Solução**:

1. Check `.env`:
```bash
cat .env | grep GCP_
# Deve ter:
# GCP_PROJECT_ID=seu-projeto
# GCP_KEY_PATH=C:/gcp/gcp-key.json (ou /path/to/key.json)
# GCP_REGION=US
```

2. Verifique arquivo de chave:
```bash
ls -la C:/gcp/gcp-key.json  # Deve existir
```

3. Teste credenciais:
```bash
python -c "from google.oauth2 import service_account; sa = service_account.Credentials.from_service_account_file('C:/gcp/gcp-key.json'); print('OK')"
```

4. Se usar Docker, verifique mount em `docker-compose.yml`:
```yaml
airflow-webserver:
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS=/opt/airflow/.config/gcp-key.json
  volumes:
    - C:/gcp/gcp-key.json:/opt/airflow/.config/gcp-key.json:ro
```

### Erro: "Dataset not found" no BigQuery

**Causa**: Dataset não existe em BigQuery

**Solução**:

Rode setup_bigquery.py:
```bash
python scripts/setup_bigquery.py
```

Ou crie manualmente:
```bash
bq mk --dataset seu-projeto:weather_bronze
bq mk --dataset seu-projeto:weather_silver
bq mk --dataset seu-projeto:weather_gold
```

### Erro: "Provided Schema does not match Table"

**Causa**: Colunas do DataFrame não coincidem com schema da tabela

**Solução**:

1. Verifique schema esperado:
```bash
cat config/schema/bronze_schema.json
```

2. Rode teste local:
```python
from pipeline.loaders.bigquery_loader import BigQueryLoader
loader = BigQueryLoader()
try:
    loader.validate_df_schema(df, "weather_bronze", "weather_raw")
    print("OK")
except ValueError as e:
    print(f"Erro: {e}")
```

3. Se adicionou coluna nova:
   - Edite `config/schema/*.json`
   - Delete a tabela no BigQuery
   - Recrie via `scripts/setup_bigquery.py`

### DAG não aparece no Airflow após editar arquivo

**Causa**: Scheduler não recarregou os DAGs

**Solução**:
```bash
docker-compose restart airflow-scheduler

# Aguarde 30s, depois recarregue Airflow UI
# http://localhost:8080
```

Ou force parse:
```bash
docker-compose exec airflow-webserver airflow dags list
```

### Erro: "FAILED to get DAG 'weather_etl_dag'"

**Causa**: Syntax error no arquivo Python

**Solução**:

Verifique sintaxe:
```bash
python -m py_compile dags/weather_etl_dag.py
```

Se houver erro, ele mostra linha. Corrija e reinicie:
```bash
docker-compose restart airflow-scheduler
```

### Pipeline roda mas não carrega dados em BigQuery

**Causa**: Pode ser vários motivos

**Debug passo a passo**:

1. Verifique logs:
```bash
docker-compose logs airflow-webserver | grep load_to_bigquery
```

2. Teste transform localmente:
```python
from pipeline.extractors.open_meteo import OpenMeteoClient
from pipeline.transformers.weather_transformer import WeatherTransformer

client = OpenMeteoClient()
data = client.get_last_30_days(-23.5505, -46.6333)
df, metrics = WeatherTransformer.clean_weather_data(data, "Test", "TS")
print(f"Rows: {len(df)}, Quality: {metrics}")
```

3. Teste load:
```python
from pipeline.loaders.bigquery_loader import BigQueryLoader
loader = BigQueryLoader()
loader.load_to_bronze(df, "weather_raw", "append")
```

4. Verifique dados em BigQuery:
```bash
bq query "SELECT COUNT(*) as total FROM \`seu-projeto.weather_bronze.weather_raw\`"
```

### Performance: Pipeline está muito lenta

**Possíveis causas**:

1. **API lenta**: Open-Meteo pode estar congestionada
   - Solução: rodar em horário de menor carga

2. **BigQuery lento**: Carga está processando muitos dados
   - Solução: reduzir para 7 dias em vez de 30 (se possível)

3. **Transformer lento**: Processamento de dados está pesado
   - Solução: usar `df.sample()` para debug, depois rodar em batch

4. **Airflow lento**: Container sem recursos suficientes
   - Solução: aumentar CPU/RAM em `docker-compose.yml`

## Checklist de Saúde Diária

Antes de confiar na pipeline:

```bash
# 1. Verificar se Airflow e Postgres estão rodando
docker-compose ps

# 2. Verifique última execução
docker-compose logs airflow-scheduler | tail -20

# 3. Verifique dados carregados ontem
bq query --use_legacy_sql=false "
  SELECT DATE(load_timestamp) as load_date, COUNT(*) as rows
  FROM \`seu-projeto.weather_bronze.weather_raw\`
  GROUP BY DATE(load_timestamp)
  ORDER BY load_date DESC
  LIMIT 5
"

# 4. Verifique quality_score (se houver dados em Silver)
bq query --use_legacy_sql=false "
  SELECT AVG(data_quality_score) as avg_quality
  FROM \`seu-projeto.weather_silver.weather_cleaned\`
  WHERE DATE(aggregation_timestamp) = CURRENT_DATE()
"

# 5. Verifique se há alertas de erro
docker-compose exec airflow-webserver airflow dags list --report
```

Se tudo está verde, a pipeline está saudável! ✅
