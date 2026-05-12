import base64
import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError


s3 = boto3.client("s3")
sqs = boto3.client("sqs")
dynamodb = boto3.resource("dynamodb")

# This file expects the following Lambda environment variables
JOBS_TABLE_NAME = os.environ["JOBS_TABLE_NAME"]
RAW_BUCKET_NAME = os.environ["RAW_BUCKET_NAME"]
QUEUE_URL = os.environ["QUEUE_URL"]

jobs_table = dynamodb.Table(JOBS_TABLE_NAME)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)

    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_json_safe(v) for v in value]

    return value


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(_json_safe(body)),
    }


def _parse_body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body") or "{}"

    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")

    return json.loads(body)


def _extract_method(event: dict[str, Any]) -> str:
    if "httpMethod" in event:
        return event["httpMethod"]
    return event.get("requestContext", {}).get("http", {}).get("method", "")


def _extract_path_param(event: dict[str, Any], name: str) -> str | None:
    return (event.get("pathParameters") or {}).get(name)


def _create_job(event: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = _parse_body(event)
    except json.JSONDecodeError:
        return _response(400, {"message": "Request body must be valid JSON"})

    title = payload.get("title")
    content = payload.get("content")

    if not isinstance(title, str) or not title.strip():
        return _response(400, {"message": "Field 'title' must be a non-empty string"})
    if not isinstance(content, str) or not content.strip():
        return _response(400, {"message": "Field 'content' must be a non-empty string"})

    job_id = str(uuid.uuid4())
    created_at = _now_iso()
    s3_key = f"raw/{job_id}.json"

    raw_document = {
        "job_id": job_id,
        "title": title,
        "content": content,
        "created_at": created_at,
    }

    try:
        s3.put_object(
            Bucket=RAW_BUCKET_NAME,
            Key=s3_key,
            Body=json.dumps(raw_document).encode("utf-8"),
            ContentType="application/json",
        )

        jobs_table.put_item(
            Item={
                "job_id": job_id,
                "title": title,
                "status": "PENDING",
                "created_at": created_at,
                "s3_key": s3_key,
            }
        )

        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(
                {
                    "job_id": job_id,
                    "s3_key": s3_key,
                }
            ),
        )

    except ClientError as exc:
        return _response(
            500,
            {
                "message": "Failed to create job",
                "error": str(exc),
            },
        )

    return _response(
        202,
        {
            "job_id": job_id,
            "status": "PENDING",
        },
    )


def _get_job(event: dict[str, Any]) -> dict[str, Any]:
    job_id = _extract_path_param(event, "job_id")
    if not job_id:
        return _response(400, {"message": "Missing path parameter 'job_id'"})

    try:
        item_resp = jobs_table.get_item(Key={"job_id": job_id})
    except ClientError as exc:
        return _response(500, {"message": "Failed to read DynamoDB", "error": str(exc)})

    item = item_resp.get("Item")
    if not item:
        return _response(404, {"message": "Job not found"})

    body = {
        "job_id": item["job_id"],
        "status": item["status"],
        "title": item["title"],
        "created_at": item["created_at"],
    }

    if item["status"] == "COMPLETED":
        body["result"] = {
            "title_upper": item.get("result_title_upper"),
            "content_length": item.get("result_content_length"),
            "word_count": item.get("result_word_count"),
            "processed_at": item.get("processed_at"),
        }

    if item["status"] == "FAILED" and "error_message" in item:
        body["error_message"] = item["error_message"]

    return _response(200, body)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    method = _extract_method(event)

    if method == "POST":
        return _create_job(event)

    if method == "GET":
        return _get_job(event)

    return _response(405, {"message": "Method not allowed"})