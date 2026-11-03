
from datetime import datetime

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import (
    KubernetesPodOperator,
)

with DAG(
    dag_id="test_kubernetes_connection",
    start_date=datetime(2026, 11, 1),
    schedule=None,
    catchup=False,
    tags=["taxi", "infrastructure"],
) as dag:

    test_connection = KubernetesPodOperator(
        task_id="test_connection",
        name="airflow-k8s-smoke-test",
        namespace="taxi-training",

        image="busybox:1.36",

        cmds=["sh", "-c"],
        arguments=[
            "echo 'Airflow successfully started a Kubernetes Pod'"
        ],

        kubernetes_conn_id="taxi_kubernetes",
        in_cluster=False,

        get_logs=True,
        on_finish_action="delete_pod",
    )
