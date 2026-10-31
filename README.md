# TAXI TRIP DURATION PREDICTION


ToDO:
- [X] TO INIT DVC, ADD  DATA TO LOCAL/S3 STORAGE
    SETUP: scripts/dvc_setup.sh
- [X] Проверить данные high volume taxi
- [X] Добавить data pipeline:
      ├── data_pipeline.py
      ├── preprocessing.py
      └── validation.py
- [X] добавить features_engineering.py
- [X] добавить train.py training_pipeline.py

**виртуальное окружение**:
```bash
# Запуск окружения
uv sync
# Переменные окружения см .env_example
source .env
```
**dvc**:
```bash
# опционально получить датасет
uv run dvc pull
 ```

**preprocessing (data quality)**:
```bash
make data
```
**training**:
```bash
make train
```

**mlflow**:
local server:
```bash
make mlflow-local
```

docker:
```bash
mlflow-docker
```
