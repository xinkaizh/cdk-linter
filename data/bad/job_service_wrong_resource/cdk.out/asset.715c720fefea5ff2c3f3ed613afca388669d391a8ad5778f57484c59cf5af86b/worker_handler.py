import json
import os
from datetime import datetime, timezone
from typing import Any

import boto3


s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

# This file expects the following Lambda environment variables
JOBS_TABLE_NAME = os.environ["JOBS_TABLE_NAME"]
RAW_BUCKET_NAME = os.environ["RAW_BUCKET_NAME"]

jobs_table = dynamodb.Table(JOBS_TABLE_NAME)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_raw_document(s3_key: str) -> dict[str, Any]:
    response = s3.get_object(Bucket=RAW_BUCKET_NAME, Key=s3_key)
    raw_bytes = response["Body"].read()
    return json.loads(raw_bytes.decode("utf-8"))


def _compute_result(document: dict[str, Any]) -> dict[str, Any]:
    title = document["title"]
    content = document["content"]

    return {
        "title_upper": title.upper(),
        "content_length": len(content),
        "word_count": len(content.split()),
        "processed_at": _now_iso(),
    }


def _mark_job_completed(job_id: str, result: dict[str, Any]) -> None:
    jobs_table.update_item(
        Key={"job_id": job_id},
        UpdateExpression=(
            "SET #s = :status, "
            "result_title_upper = :title_upper, "
            "result_content_length = :content_length, "
            "result_word_count = :word_count, "
            "processed_at = :processed_at"
        ),
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": "COMPLETED",
            ":title_upper": result["title_upper"],
            ":content_length": result["content_length"],
            ":word_count": result["word_count"],
            ":processed_at": result["processed_at"],
        },
    )


def _mark_job_failed(job_id: str, error_message: str) -> None:
    jobs_table.update_item(
        Key={"job_id": job_id},
        UpdateExpression="SET #s = :status, error_message = :error",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": "FAILED",
            ":error": error_message[:500],
        },
    )


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        job_id = body["job_id"]
        s3_key = body["s3_key"]

        try:
            document = _load_raw_document(s3_key)
            result = _compute_result(document)
            _mark_job_completed(job_id, result)
        except Exception as exc:
            _mark_job_failed(job_id, str(exc))
            raise

    return {"status": "ok"}