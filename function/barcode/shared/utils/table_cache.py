import os
import json
import logging
from datetime import datetime, timezone
from azure.data.tables import TableServiceClient, TableClient, UpdateMode
from azure.identity import ManagedIdentityCredential

TABLE_NAME = "TaskCache"
PARTITION_KEY = "task"
CACHE_TTL_SECONDS = 3600


def _get_table_client(table_name: str = TABLE_NAME) -> TableClient:
    if os.environ.get("AZURE_FUNCTIONS_ENVIRONMENT") == "Development":
        conn_str = os.environ.get("AzureWebJobsStorage", "UseDevelopmentStorage=true")
        service = TableServiceClient.from_connection_string(conn_str)
    else:
        credential = ManagedIdentityCredential(
            client_id=os.environ.get("AzureWebJobsStorage__clientId")
        )
        service = TableServiceClient(
            endpoint="https://faclickupbarcodeautomati.table.core.windows.net",
            credential=credential
        )
    service.create_table_if_not_exists(table_name)
    return service.get_table_client(table_name)


def write_task_snapshot(task_id: str, task_data: dict, pdf_blob_url: str) -> None:
    """
    Upsert a task snapshot entity into Table Storage.
    Uses MERGE mode so existing tech fields (arrival_date_iso, etc.) are preserved
    if the PDF is regenerated for the same task.
    """
    addr = ""
    desc = ""
    action_items_raw = ""
    start_buffer_hours = 0
    translate_flag = False
    contractor_notes_field_id = None

    for cf in task_data.get("custom_fields", []):
        name = cf.get("name", "")
        if name == "Property Address":
            addr = cf.get("value") or ""
        elif name == "Task Issue Description":
            desc = cf.get("value") or ""
        elif name == "Task Start Buffer":
            start_buffer_hours = int(float(cf.get("value", 0) or 0))
        elif name == "Task Action Items":
            val = cf.get("value_richtext")
            action_items_raw = val if isinstance(val, str) else (json.dumps(val) if val else "")
        elif name == "Translate":
            translate_flag = cf.get("value", "false").lower() == "true"
        elif name.lower() == "contractor notes":
            contractor_notes_field_id = cf.get("id")

    status_obj = task_data.get("status", {})
    task_status = status_obj.get("status", "") if isinstance(status_obj, dict) else ""

    entity = {
        "PartitionKey": PARTITION_KEY,
        "RowKey": task_id,
        "property_address": addr,
        "issue_description": desc,
        "action_items_raw": action_items_raw,
        "start_date_ms": str(task_data.get("start_date") or ""),
        "start_buffer_hours": start_buffer_hours,
        "task_name": task_data.get("name", ""),
        "task_status": task_status,
        "translate_flag": translate_flag,
        "pdf_blob_url": pdf_blob_url,
        "snapshot_written_at": datetime.now(timezone.utc).isoformat(),
    }
    if contractor_notes_field_id:
        entity["contractor_notes_field_id"] = contractor_notes_field_id

    client = _get_table_client()
    client.upsert_entity(entity=entity, mode=UpdateMode.MERGE)
    logging.info(f"Task snapshot written to Table Storage for task {task_id}")


def read_task_snapshot(task_id: str) -> dict | None:
    """Return the entity dict if found, None if not found."""
    try:
        client = _get_table_client()
        entity = client.get_entity(partition_key=PARTITION_KEY, row_key=task_id)
        return dict(entity)
    except Exception:
        return None


def is_snapshot_fresh(entity: dict, ttl_seconds: int = CACHE_TTL_SECONDS) -> bool:
    """Return True if snapshot_written_at is within ttl_seconds of now."""
    written_at_str = entity.get("snapshot_written_at")
    if not written_at_str:
        return False
    try:
        written_at = datetime.fromisoformat(written_at_str)
        if written_at.tzinfo is None:
            written_at = written_at.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - written_at).total_seconds()
        return age < ttl_seconds
    except Exception:
        return False


def update_tech_fields(task_id: str, updates: dict) -> None:
    """
    Merge only technician-writable fields into the entity.
    Does not overwrite snapshot fields from ClickUp.
    """
    allowed = {"arrival_date_iso", "completion_status", "tech_notes"}
    entity = {
        "PartitionKey": PARTITION_KEY,
        "RowKey": task_id,
        "last_ui_update_at": datetime.now(timezone.utc).isoformat(),
    }
    for key in allowed:
        if key in updates:
            entity[key] = updates[key]

    client = _get_table_client()
    client.upsert_entity(entity=entity, mode=UpdateMode.MERGE)
    logging.info(f"Tech fields updated in Table Storage for task {task_id}")
