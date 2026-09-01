"""Read-only DynamoDB access for the live probe.

The probe cross-checks what the SDK returns against the dev DynamoDB tables. It
shells out to the pre-configured AWS CLI (rather than adding boto3 as a
dependency) and only ever issues read operations (``get-item``, ``query``,
``list-tables``).

The Amplify Data tables are named ``SkGen<Model>-<apiId>-NONE``, where the
``apiId`` is per-deployment. Rather than hardcode it, the helper resolves the
suffix once by locating the SkGenTeamspace table that actually contains the
fixture teamspace row — so the probe keeps working across redeploys. Set
``SKETRICGEN_DDB_TABLE_SUFFIX`` to skip discovery.
"""

import json
import os
import subprocess
from typing import Any, Optional

from .fixtures import TEAMSPACE_ID

DEFAULT_REGION = "us-east-1"

# GSIs used to list teamspace-scoped resources / resolve a public id to a row.
_PROJECTS_BY_TEAMSPACE_INDEX = "skGenProjectsByTeamspace_idAndSlug"
_AGENTS_BY_TEAMSPACE_INDEX = "skGenAgentsByTeamspace_idAndLast_updated"
_AGENTS_BY_ID_INDEX = "skGenAgentsByAgent_id"
_KBS_BY_TEAMSPACE_INDEX = "skGenKnowledgeBasesByTeamspace_idAndLast_updated"


class DynamoUnavailable(RuntimeError):
    """Raised when the AWS CLI or the dev tables cannot be reached."""


def _unmarshal(value: dict[str, Any]) -> Any:
    """Turn a single DynamoDB attribute-value into a plain Python value."""
    ((tag, inner),) = value.items()
    if tag == "S":
        return inner
    if tag == "N":
        return int(inner) if inner.lstrip("-").isdigit() else float(inner)
    if tag == "BOOL":
        return inner
    if tag == "NULL":
        return None
    if tag == "M":
        return {k: _unmarshal(v) for k, v in inner.items()}
    if tag == "L":
        return [_unmarshal(v) for v in inner]
    if tag == "SS":
        return list(inner)
    if tag == "NS":
        return [int(n) if n.lstrip("-").isdigit() else float(n) for n in inner]
    return inner  # B, BS — returned as-is; the probe never inspects binary


def _unmarshal_item(item: dict[str, Any]) -> dict[str, Any]:
    return {k: _unmarshal(v) for k, v in item.items()}


class DynamoProbe:
    """Read-only accessor over the dev DynamoDB tables via the AWS CLI."""

    def __init__(self, region: Optional[str] = None) -> None:
        self.region = region or os.getenv("SKETRICGEN_DDB_REGION", DEFAULT_REGION)
        self._suffix: Optional[str] = os.getenv("SKETRICGEN_DDB_TABLE_SUFFIX")

    # -- CLI plumbing --------------------------------------------------

    def _aws(self, *args: str) -> dict[str, Any]:
        try:
            proc = subprocess.run(
                ["aws", *args, "--region", self.region, "--output", "json"],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except FileNotFoundError as e:
            raise DynamoUnavailable("aws CLI not found on PATH") from e
        except subprocess.TimeoutExpired as e:
            raise DynamoUnavailable("aws CLI call timed out") from e
        if proc.returncode != 0:
            raise DynamoUnavailable(
                f"aws {' '.join(args[:2])} failed: {proc.stderr.strip()}"
            )
        return json.loads(proc.stdout) if proc.stdout.strip() else {}

    def preflight(self) -> None:
        """Confirm credentials resolve and the dev tables are reachable."""
        self._aws("sts", "get-caller-identity")
        self.suffix()

    # -- table-name resolution ----------------------------------------

    def suffix(self) -> str:
        if self._suffix:
            return self._suffix
        tables = self._aws("dynamodb", "list-tables").get("TableNames", [])
        candidates = [
            t[len("SkGenTeamspace-") : -len("-NONE")]
            for t in tables
            if t.startswith("SkGenTeamspace-") and t.endswith("-NONE")
        ]
        for suffix in candidates:
            row = self._get_item(
                f"SkGenTeamspace-{suffix}-NONE",
                {"teamspace_id": {"S": TEAMSPACE_ID}},
            )
            if row is not None:
                self._suffix = suffix
                return suffix
        raise DynamoUnavailable(
            f"No SkGenTeamspace table holds the fixture teamspace {TEAMSPACE_ID}. "
            "Set SKETRICGEN_DDB_TABLE_SUFFIX to the correct dev suffix."
        )

    def _table(self, model: str) -> str:
        return f"SkGen{model}-{self.suffix()}-NONE"

    # -- read helpers --------------------------------------------------

    def _get_item(self, table: str, key: dict[str, Any]) -> Optional[dict[str, Any]]:
        data = self._aws(
            "dynamodb",
            "get-item",
            "--table-name",
            table,
            "--key",
            json.dumps(key),
        )
        item = data.get("Item")
        return _unmarshal_item(item) if item else None

    def _query_all(
        self, table: str, index: str, teamspace_id: str
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        start_key: Optional[str] = None
        while True:
            args = [
                "dynamodb",
                "query",
                "--table-name",
                table,
                "--index-name",
                index,
                "--key-condition-expression",
                "teamspace_id = :t",
                "--expression-attribute-values",
                json.dumps({":t": {"S": teamspace_id}}),
            ]
            if start_key:
                args += ["--exclusive-start-key", start_key]
            data = self._aws(*args)
            items.extend(_unmarshal_item(i) for i in data.get("Items", []))
            last = data.get("LastEvaluatedKey")
            if not last:
                break
            start_key = json.dumps(last)
        return items

    # -- entity accessors (mirror the Admin API surface) ---------------

    def teamspace(self) -> Optional[dict[str, Any]]:
        return self._get_item(
            self._table("Teamspace"), {"teamspace_id": {"S": TEAMSPACE_ID}}
        )

    def project_ids(self) -> list[str]:
        rows = self._query_all(
            self._table("Project"), _PROJECTS_BY_TEAMSPACE_INDEX, TEAMSPACE_ID
        )
        return [r["project_id"] for r in rows]

    def agent_by_id(self, agent_id: str) -> Optional[dict[str, Any]]:
        data = self._aws(
            "dynamodb",
            "query",
            "--table-name",
            self._table("Agent"),
            "--index-name",
            _AGENTS_BY_ID_INDEX,
            "--key-condition-expression",
            "agent_id = :a",
            "--expression-attribute-values",
            json.dumps({":a": {"S": agent_id}}),
        )
        items = data.get("Items", [])
        return _unmarshal_item(items[0]) if items else None

    def agent_ids(self) -> set[str]:
        rows = self._query_all(
            self._table("Agent"), _AGENTS_BY_TEAMSPACE_INDEX, TEAMSPACE_ID
        )
        return {r["agent_id"] for r in rows}

    def knowledge_base_ids(self) -> list[str]:
        rows = self._query_all(
            self._table("KnowledgeBase"), _KBS_BY_TEAMSPACE_INDEX, TEAMSPACE_ID
        )
        return [r["knowledge_base_id"] for r in rows]
