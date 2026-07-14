"""S3 as the load-bearing extraction cache + audit trail (locked #2, ADR-0002).

boto3 pointed at LocalStack (endpoint from env); the *same* calls hit real S3 by dropping the endpoint.
Holds two things:
  * ``extractions/{note_id}.json`` — one schema-shaped record per note (cache + per-record audit trail).
  * ``_budget/{YYYY-MM-DD}.json``  — the daily call ledger; survives restart → enforces the 50/day cap.

Restart-safety falls out of this: a re-run finds every note already cached → zero LLM calls.
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from .config import get_settings

_EXTRACT_PREFIX = "extractions/"
_BUDGET_PREFIX = "_budget/"


class S3Store:
    def __init__(self) -> None:
        s = get_settings()
        self._bucket = s.s3_bucket
        self._s3 = boto3.client(
            "s3",
            endpoint_url=s.aws_endpoint_url,
            aws_access_key_id=s.aws_access_key_id,
            aws_secret_access_key=s.aws_secret_access_key,
            region_name=s.aws_region,
            # path-style addressing is required for LocalStack; harmless on real S3.
            config=Config(retries={"max_attempts": 3}, s3={"addressing_style": "path"}),
        )

    def ensure_bucket(self) -> None:
        """Idempotent bucket bootstrap — called at startup so a clean clone just works."""
        try:
            self._s3.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._s3.create_bucket(Bucket=self._bucket)

    # --- extraction records -------------------------------------------------
    def _key(self, note_id: str) -> str:
        return f"{_EXTRACT_PREFIX}{note_id}.json"

    def get_extraction(self, note_id: str) -> Optional[dict[str, Any]]:
        try:
            obj = self._s3.get_object(Bucket=self._bucket, Key=self._key(note_id))
        except ClientError:
            return None
        return json.loads(obj["Body"].read())

    def put_extraction(self, note_id: str, record: dict[str, Any]) -> None:
        self._s3.put_object(
            Bucket=self._bucket,
            Key=self._key(note_id),
            Body=json.dumps(record, ensure_ascii=False, indent=2).encode("utf-8"),
            ContentType="application/json",
        )

    def list_extractions(self) -> list[dict[str, Any]]:
        """Read every cached record — the source the DuckDB view is materialized from (Decision E)."""
        records: list[dict[str, Any]] = []
        paginator = self._s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=_EXTRACT_PREFIX):
            for item in page.get("Contents", []):
                obj = self._s3.get_object(Bucket=self._bucket, Key=item["Key"])
                records.append(json.loads(obj["Body"].read()))
        return records

    # --- daily budget ledger (locked #4) ------------------------------------
    def _budget_key(self, day: Optional[str] = None) -> str:
        return f"{_BUDGET_PREFIX}{day or date.today().isoformat()}.json"

    def get_budget_used(self, day: Optional[str] = None) -> int:
        try:
            obj = self._s3.get_object(Bucket=self._bucket, Key=self._budget_key(day))
        except ClientError:
            return 0
        return int(json.loads(obj["Body"].read()).get("calls", 0))

    def incr_budget(self, n: int = 1, day: Optional[str] = None) -> int:
        """Read-modify-write; fine for the single-writer prototype (DynamoDB atomic counter at scale)."""
        used = self.get_budget_used(day) + n
        self._s3.put_object(
            Bucket=self._bucket,
            Key=self._budget_key(day),
            Body=json.dumps({"calls": used}).encode("utf-8"),
            ContentType="application/json",
        )
        return used
