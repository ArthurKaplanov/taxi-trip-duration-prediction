# Taxi Trip Duration Prediction — End-to-End MLOps

Проект прогнозирования длительности поездок такси Нью-Йорка с онлайн-инференсом и облачной MLOps-инфраструктурой. Главный фокус — **воспроизводимый жизненный цикл ML-модели**: подготовка данных, обучение, регистрация, контейнеризация, развёртывание, масштабирование, наблюдаемость и контролируемое переобучение.

> **Статус на 3 ноября 2026 года:** online serving в Kubernetes, HPA, мониторинг HTTP-метрик в Prometheus и ручной запуск retraining из Yandex Managed Airflow проверены. Полностью автоматические promotion/CD, работа по расписанию и доставка алертов **пока не подтверждены**. Не следует считать систему полностью автономным production-сервисом.

## 1. ML-задача и ценность

**Задача:** регрессия — предсказать ожидаемую длительность поездки в секундах до её начала. Сервис может использоваться для расчёта ETA в приложении перевозчика и предварительной оценки времени поездки.

**Источник:** NYC TLC High Volume For-Hire Vehicle (HVFHV) trip data; справочник Taxi Zones. Для MVP использована партиция за май 2026 года и подготовленная sample-выборка для инфраструктурной проверки retraining.

**Входные признаки:** идентификаторы зон посадки/высадки, время запроса, лицензия перевозчика, флаги поездки и признаки, сформированные из этих полей и справочника зон. Недоступные в момент запроса сведения о фактически завершённой поездке не должны попадать в feature pipeline.

**Модель:** CatBoostRegressor. **Метрики:** MAE и RMSE в секундах. Разбиение train/validation/test — по времени.

### Зафиксированные результаты

| Показатель | Результат | Контекст |
|---|---:|---|
| Validation MAE | 249.38 с | Последний training run на sample |
| Validation RMSE | 372.57 с | Тот же run |
| Test MAE | 330.52 с | Тот же run |
| Test RMSE | 461.30 с | Тот же run |
| Model Registry | Champion v1, Challenger v3 rejected | MAE кандидата равен MAE Champion |
| Online load test | 50 RPS, p95 17.15 мс, 0 ошибок | k6, 2 мин., условия теста не равны предельной пропускной способности |

Результаты основаны на учебном датасете и не являются доказательством качества модели на всех сезонных и географических сегментах. p95 17.15 мс относится к измерению в конкретном нагрузочном тесте, не к SLA.

## 2. Архитектура

```mermaid
flowchart TD
  A[NYC TLC HVFHV / Taxi Zones] --> B[Data validation & preprocessing]
  B --> C[(Yandex Object Storage / DVC)]
  C --> D[Airflow: KubernetesPodOperator]
  D --> E[CatBoost training + feature engineering]
  E --> F[(MLflow Tracking / Registry)]
  F --> G{Quality Gate: Challenger vs Champion}
  G -->|Rejected| H[Keep current Champion]
  G -.->|Approved: CD integration pending.-> I[GitHub Actions Model Release]
  I --> J[Yandex Container Registry]
  J -.->|CD rollout pending verification.-> K[Kubernetes / FastAPI]
  K --> L[Prometheus / Grafana]
  K --> M[HPA]
```

**Разделение ответственности:** Airflow оркестрирует batch training, GitHub Actions проверяет код и собирает релизы, MLflow ведёт версии моделей и экспериментов, Kubernetes выполняет онлайн-инференс, Prometheus собирает операционные метрики.

## 3. Технологии

| Зона | Инструменты |
|---|---|
| ML / Feature Engineering | Python 3.12, pandas, CatBoost, scikit-learn |
| Data versioning / storage | DVC, S3-compatible Yandex Object Storage |
| Tracking / registry | MLflow |
| Model API | FastAPI, Docker |
| Orchestration | Yandex Managed Airflow, KubernetesPodOperator |
| CI / release | GitHub Actions, uv, pytest, Ruff, Yandex Container Registry |
| Serving / scaling | Yandex Managed Kubernetes, Deployment, Service, HPA |
| Monitoring | Prometheus, kube-prometheus-stack, Grafana |
| Infrastructure as Code | Terraform, Kubernetes manifests, Helm |
| Load testing | k6 |

## 4. Подготовка окружения

Требуются Python 3.12, `uv`, Docker, `kubectl`, DVC с S3-поддержкой и доступ к Yandex Cloud. Для облачных операций нужны собственные учётные данные и заранее развёрнутые сервисы.

```bash
uv sync --locked
uv run pytest
uv run ruff check .
```

Секреты не должны храниться в репозитории. Для AWS-compatible клиентов используются `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, endpoint `https://storage.yandexcloud.net`; для MLflow — `MLFLOW_TRACKING_URI` и при необходимости `MLFLOW_S3_ENDPOINT_URL`. Точные значения задаются через GitHub Secrets, Kubernetes Secrets или секретное хранилище.

## 5. Данные и обучение

Данные отслеживаются DVC и загружаются из Object Storage:

```bash
uv run dvc pull
```

Пример ручного запуска training pipeline:

```bash
uv run python -m taxi_trip_duration.training_pipeline \
  --processed-path data/processed/fhvhv_tripdata_2026-05_sample.parquet \
  --zone-lookup-path data/raw/taxi_zone_lookup.csv \
  --result-path /tmp/training_result.json
```

Training pipeline выполняет генерацию признаков, временное разбиение, обучение CatBoost, логирование MLflow run, регистрацию кандидата и сравнение с Champion по Validation MAE. Для promotion задан минимальный абсолютный выигрыш `5.0` секунды (не 5%).

**Quality Gate:** `approved`, `initial_candidate` либо `rejected`. Результат сохраняется вместе с `run_id`, `candidate_version`, `champion_version` и метриками. При отклонении действующий Champion не меняется. Вручную подтверждён сценарий `rejected` для версии 3.

Для честного сравнения модель-кандидат и Champion оцениваются на одном `X_val/y_val`. Перед production-автоматизацией необходимо закрепить политику валидационного окна и обновления данных.

## 6. Онлайн-сервис

Сервис на FastAPI предоставляет:

| Endpoint | Назначение |
|---|---|
| `GET /health` | Readiness / проверка загрузки модели |
| `POST /predict` | Прогноз длительности поездки |
| `GET /metrics` | HTTP-метрики для Prometheus |

Пример запроса:

```bash
curl -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{
    "PULocationID": 76,
    "DOLocationID": 161,
    "request_datetime": "2026-05-15T08:30:00",
    "hvfhs_license_num": "HV0003",
    "shared_request_flag": "N",
    "wav_request_flag": "N"
  }'
```

Проверка в Kubernetes через локальный port-forward:

```bash
kubectl -n taxi-ml port-forward svc/taxi-prediction 8000:80
curl http://localhost:8000/health
```

**Model Contract:** при загрузке сервиса проверяется совместимость feature-set version, перечня и порядка признаков, категориальных признаков и артефакта модели. Это снижает риск незаметно неправильного inference.

## 7. Docker, CI/CD и Kubernetes

- **App CI:** тесты и статические проверки кода.
- **Model Release:** явно заданная версия MLflow Registry → скачивание модели → восстановление справочника Taxi Zones с DVC → Docker build → локальные `/health` и `/predict` smoke tests → публикация в Yandex Container Registry.
- **Kubernetes:** inference Deployment, ClusterIP Service, health probes, лимиты ресурсов, HPA по CPU. HPA масштабировался в эксперименте от 1 до 5 Pod.
- **CD:** доступ GitHub Actions к Kubernetes проверялся через отдельный ServiceAccount; автоматический rollout, post-deploy smoke test, rollback и promotion Champion **ещё требуют end-to-end подтверждения**.

Для Kubernetes rollout предпочтительно закреплять Docker image digest, а не плавающий tag. Права deployment ServiceAccount должны быть ограничены namespace `taxi-ml`.

## 8. Airflow retraining

DAG `taxi_model_retraining` выполняет `training_pipeline.py` через `KubernetesPodOperator` в namespace `taxi-training`. Training image отдельно от serving image; DVC загружает данные из S3, а MLflow сохраняет метрики и кандидата. JSON-результат передаётся через `/airflow/xcom/return.json` в downstream task `quality_gate`.

**Проверено:** ручной запуск DAG успешно завершился. **Не проверено:** рабочее расписание, автоматическое обновление входного датасета и автоматический запуск CD после `approved`.

Переобучение на одном и том же фиксированном sample не заменяет полноценного обновления данных. Это ограничение специально зафиксировано для финальной демонстрации.

## 9. Мониторинг и масштабирование

Метрики `/metrics` собираются Prometheus через ServiceMonitor. Предусмотрены панели Grafana: RPS, latency p95, HTTP 5xx и число доступных реплик. PrometheusRule для ошибок и недоступности сервиса спроектирован; фактическое срабатывание/доставка уведомления требуют проверки.

Нагрузочные тесты проводились с k6. Успешный тест с постоянной интенсивностью `50 RPS` за 2 минуты: `6001` запроса, p95 `17.15 мс`, ошибок `0`, dropped iterations `0`. Это измерение в условиях имеющегося кластера, а не универсальная оценка максимального throughput.

## 10. Проверенные сценарии и оставшиеся ограничения

| Сценарий | Статус |
|---|---|
| DVC → S3 внутри Kubernetes Training Pod | Проверено |
| Обучение CatBoost в Kubernetes Job | Проверено |
| Регистрация MLflow Challenger и отказ в promotion | Проверено |
| Airflow → KubernetesPodOperator → XCom | Проверено |
| Serving FastAPI и Model Contract в Kubernetes | Проверено |
| HPA под нагрузкой и k6 benchmark | Проверено |
| Prometheus scraping HTTP-метрик | Проверено |
| Retraining по расписанию на обновляемых данных | Не подтверждено |
| Approved → Model Release → Kubernetes → Champion | Не подтверждено |
| Автоматический rollback при неудачном CD | Не подтверждено |
| Grafana alerts → внешние уведомления | Не подтверждено |

## 11. Безопасность и стоимость

- Не размещать в Git `.dvc/config.local`, kubeconfig, ServiceAccount token, S3 credentials или GitHub Actions Secrets.
- Разделять права `airflow-training` и `github-deployer` по namespace и операциям.
- Ограничить публичный Kubernetes API (в MVP он был временно открыт по TCP 443/6443) либо использовать deployment runner внутри VPC.
- Текущая учебная инфраструктура включает облачные сервисы, за которые может начисляться плата. После демонстрации выключать или удалять неиспользуемые ресурсы через Terraform/CLI.

## 12. Что осталось до полностью автоматического MLOps lifecycle

1. Включить обновление/версионирование тренировочных данных и контролируемое расписание Airflow.
2. Согласовать production evaluation window и критерии promotion.
3. Проверить `approved` → GitHub Model Release → Kubernetes rollout → smoke test → обновление Champion.
4. Протестировать rollback и согласованность MLflow alias с реально развёрнутым образом.
5. Подтвердить Grafana panels, PrometheusRule и доставку хотя бы одного алерта.

## 13. Как демонстрировать проект

1. Показать MLflow Registry: Champion v1 и отклонённые версии-кандидаты.
2. Открыть успешный `taxi_model_retraining` DAG и XCom с `decision`.
3. Показать Kubernetes Deployment и HPA.
4. Выполнить запрос к `/predict`, открыть `/metrics` и Prometheus.
5. Показать GitHub Actions Model Release и зафиксировать, какие CD-этапы действительно проверены.

---

**Итог:** реализован работающий MLOps MVP с online serving и облачным переобучением, запущенным из Airflow. Финальное звено автоматического production rollout находится в стадии интеграции; его нельзя считать завершённым до успешного end-to-end теста.
