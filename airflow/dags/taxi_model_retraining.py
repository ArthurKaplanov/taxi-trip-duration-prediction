
from datetime import datetime, timedelta

from airflow import DAG
from airflow.decorators import task
from airflow.providers.cncf.kubernetes.operators.pod import (
    KubernetesPodOperator,
)
from kubernetes.client import models as k8s


TRAINING_IMAGE = (
    "cr.yandex/REGISTRY_ID/taxi-training:VERSION"
)

with DAG(
    dag_id="taxi_model_retraining",
    description="Scheduled retraining of taxi duration model",
    start_date=datetime(2026, 11, 3),
    schedule=None,  # Manual MVP; schedule later
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "mlops",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["taxi", "mlops", "retraining"],
) as dag:

    train_candidate = KubernetesPodOperator(
        task_id="train_candidate",
        name="taxi-training",
        namespace="taxi-training",

        image=TRAINING_IMAGE,
        image_pull_policy="IfNotPresent",

        # Configure the remote Kubernetes connection
        # in Airflow before enabling this task.
        kubernetes_conn_id="taxi_kubernetes",
        in_cluster=False,

        cmds=["/bin/sh", "-ec"],
        arguments=[
            """
            dvc pull

            python -m taxi_trip_duration.training_pipeline \
              --result-path /airflow/xcom/return.json
            """
        ],

        env_vars={
            "AWS_ENDPOINT_URL":
                "https://storage.yandexcloud.net",
            "AWS_DEFAULT_REGION": "ru-central1",
        },

        env_from=[
            k8s.V1EnvFromSource(
                secret_ref=k8s.V1SecretEnvSource(
                    name="taxi-training-secrets"
                )
            )
        ],

        container_resources=k8s.V1ResourceRequirements(
            requests={
                "cpu": "500m",
                "memory": "2Gi",
            },
            limits={
                "cpu": "1500m",
                "memory": "4Gi",
            },
        ),

        do_xcom_push=True,
        get_logs=True,
        on_finish_action="delete_pod",
        startup_timeout_seconds=300,
    )

    @task
    def inspect_result(result: dict):
        if not isinstance(result, dict):
            raise ValueError("Training returned no result")

        decision = result["decision"]
        version = result["candidate_version"]

        print(f"Candidate version: {version}")
        print(f"Decision: {decision}")

        if decision == "rejected":
            print("Champion remains unchanged")

        elif decision in ("approved", "initial_candidate"):
            print("Candidate is eligible for Model Release")

        else:
            raise ValueError(
                f"Unknown training decision: {decision}"
            )

    inspect_result(train_candidate.output)
