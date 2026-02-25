import os
import json
import base64
import datetime
import logging
import requests
import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.identity import ManagedIdentityCredential
from azure.communication.email import EmailClient
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from shared.pdf.generator import MaintenancePDFGenerator
from shared.utils.helpers import download_image_bytes, translate_text, parse_quill_delta
from shared.utils.table_cache import write_task_snapshot, read_task_snapshot, update_tech_fields


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


def get_secret_value(secret_name):
    return os.environ.get(secret_name)


def _get_clickup_token():
    return get_secret_value("ClickUpSecret") or get_secret_value("ClickUpAPIToken")


def _get_blob_service_client():
    if os.environ.get("AZURE_FUNCTIONS_ENVIRONMENT") == "Development":
        return BlobServiceClient.from_connection_string(
            "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPfsNjYWjl2kh;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
        )
    credential = ManagedIdentityCredential(
        client_id=os.environ.get("AzureWebJobsStorage__clientId")
    )
    return BlobServiceClient(
        account_url="https://faclickupbarcodeautomati.blob.core.windows.net",
        credential=credential
    )


def _extract_task_fields(data: dict) -> dict:
    """Normalize a ClickUp task API response into a flat dict for the UI."""
    addr = ""
    desc = ""
    action_items_raw = ""
    start_buffer_hours = 0
    translate_flag = False

    for cf in data.get("custom_fields", []):
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

    status_obj = data.get("status", {})
    task_status = status_obj.get("status", "") if isinstance(status_obj, dict) else ""
    action_items = parse_quill_delta(action_items_raw) if action_items_raw else []

    attachments = [
        {
            "id": a.get("id"),
            "name": a.get("title", a.get("id", "")),
            "url": a.get("url"),
            "thumbnail": a.get("thumbnail_medium") or a.get("thumbnail_small"),
        }
        for a in data.get("attachments", [])
    ]

    return {
        "task_id": data.get("id"),
        "task_name": data.get("name", ""),
        "property_address": addr,
        "issue_description": desc,
        "action_items_raw": action_items_raw,
        "action_items": action_items,
        "start_date_ms": str(data.get("start_date") or ""),
        "start_buffer_hours": start_buffer_hours,
        "task_status": task_status,
        "translate_flag": translate_flag,
        "attachments": attachments,
    }


'''
ClickUp Task Info Retrieved
'''

#868hc1q7r

@app.route(route="http_trigger_task_parse")
def http_trigger_task_parse(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        raw = req.get_body()
        logging.info(f"Raw body: {raw}")

        body = req.get_json()
        id = body.get('task_id', None)
        event = body.get('event', None)

    except ValueError:
        return func.HttpResponse("Invalid JSON body: " + json.dumps(body, indent=2), status_code=400)

    try:

        updated_info = body.get('history_items', [])
        latest_date = 0
        latest_field = None
        update_id = None  # move outside the loop

        for i in updated_info:
            if int(i['date']) > latest_date:
                latest_date = int(i['date'])
                update_id = i['id']
                latest_field = i['field']

        if event == 'taskTagUpdated' and latest_field == "tag":
            # Find the most recent item directly
            latest_item = next((i for i in updated_info if i['id'] == update_id), None)

            if latest_item and latest_item['after'] and latest_item['after'][0]['name'] == "createpdf":
                logging.info("Triggering PDF generation for task " + id)
            else:
                logging.info("Most recent update was not createpdf tag addition, skipping")
                return func.HttpResponse("Most recent update was not createpdf, skipping", status_code=201)
        else:
            return func.HttpResponse("Event is not taskTagUpdated, skipping", status_code=201)

    except Exception as ex:
        logging.error(f"Error parsing request body: {type(ex).__name__} - {str(ex)}")
        return func.HttpResponse(f"Invalid request body: {str(ex)}", status_code=400)


    if id:

        try:
            token = get_secret_value("ClickUpSecret")
        except Exception as ex:
            logging.error(f"Error retrieving secret: {type(ex).__name__} - {str(ex)}")
            return func.HttpResponse(f"Error retrieving ClickUp API token: {str(ex)}", status_code=500)

        logging.info(id)

        try:

            headers = {'accept': 'application/json', 'content-type': 'application/json', 'Authorization': token}
            t_req = f'https://api.clickup.com/api/v2/task/{id}'

            response = requests.get(url=t_req, headers=headers)

            logging.info(response.status_code)
            logging.info(response.text)

            data = json.loads(response.text)

            print(data["attachments"])
            barcode_func_key = get_secret_value("BarcodeScanFuncKey")
            barcode_link = f'https://fa-clickup-barcode-automation.azurewebsites.net/api/http_trigger_barcodescan?code={barcode_func_key}&task_id={id}'

            image_bytes = []
            for i in data["attachments"]:
                image_bytes.append(download_image_bytes(i["thumbnail_medium"]))

            addr = ""
            desc = ""
            action_items = []
            arrival_buffer = 0
            start_date = data.get("start_date")  # top-level field
            translate_flag = False



            for cf in data["custom_fields"]:
                logging.info(cf["name"])
                logging.info(cf["type"])
                if cf["name"] == "Property Address":
                    addr = cf["value"]

                if cf["name"] == "Task Issue Description":
                    desc = cf["value"]

                if cf["name"] == "Task Start Buffer":
                    start_buffer = int(float(cf.get("value", 0) or 0))

                if cf["name"] == "Task Action Items":
                    action_items = cf["value_richtext"]

                if cf["name"] == "Translate":
                    translate_flag = cf.get("value", "false").lower() == "true"

        except Exception as ex:
            logging.error(f"Error retrieving task details: {type(ex).__name__} - {str(ex)}")
            return func.HttpResponse(f"Error retrieving task details: {str(ex)}", status_code=500)


        try:
            generator = MaintenancePDFGenerator(translate_flag)
            pdf_bytes = generator.generate(
                property_address=addr,
                unit_name='',
                start_date=start_date,
                start_buffer=start_buffer,
                issue_description=desc,
                action_items=action_items,
                completion_url=barcode_link,
                attachment_images=image_bytes
            )
        except Exception as ex:
            logging.error(f"Error generating PDF: {type(ex).__name__} - {str(ex)}")
            return func.HttpResponse(f"Error generating PDF: {str(ex)}", status_code=500)


        if response.status_code == 200:
            try:
                blob_service_client = _get_blob_service_client()
                blob_client = blob_service_client.get_blob_client(
                    container="content",
                    blob=f"{id}.pdf"
                )
                blob_client.upload_blob(pdf_bytes, overwrite=True)
                logging.info(f"Successfully wrote PDF to blob storage for task {id}")

                # Write task snapshot to Table Storage cache (non-fatal)
                try:
                    pdf_blob_url = f"https://faclickupbarcodeautomati.blob.core.windows.net/content/{id}.pdf"
                    write_task_snapshot(id, data, pdf_blob_url)
                except Exception as cache_err:
                    logging.warning(f"Table Storage snapshot failed (non-fatal): {cache_err}")

            except Exception as e:
                logging.error(f"Failed to write blob: {str(e)}")
                return func.HttpResponse(f"Blob write failed: {str(e)}", status_code=500)

            return func.HttpResponse(
                pdf_bytes,
                mimetype='application/pdf',
                headers={'Content-Disposition': 'inline; filename="maintenance_task.pdf"'},
                status_code=200
            )

        else:
            return func.HttpResponse(f"Failed to retrieve task details: {response.text}", status_code=response.status_code)

    else:
        return func.HttpResponse(f"Please include ClickUp task ID as parameter")



'''
Sent PDF to Fax E-mail and Attached PDF to Task
'''
@app.blob_trigger(
    arg_name="pdfBlob",
    path="content/{name}.pdf",
    source="EventGrid",
    connection="AzureWebJobsStorage"
)
def event_grid_blob_trigger_send_email(pdfBlob: func.InputStream):
    try:
        logging.info("=" * 50)
        logging.info("BLOB TRIGGER STARTED")
        logging.info(f"Name: {pdfBlob.name}")
        logging.info(f"Blob Size: {pdfBlob.length} bytes")

        # Read the blob content
        logging.info("Reading blob bytes...")
        pdf_bytes = pdfBlob.read()
        logging.info(f"Successfully read {len(pdf_bytes)} bytes")

        # Extract blob name/task_id from path
        blob_name = pdfBlob.name.split('/')[-1]
        task_id = blob_name.replace('.pdf', '')

        logging.info(f"Task ID: {task_id}")

        logging.info("Initializing email client...")
        connection_string = os.environ.get("AzureCommunicationServiceConnectionString")
        client = EmailClient.from_connection_string(connection_string)
        logging.info("Email client initialized")

        logging.info("Encoding PDF to base64...")
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        logging.info(f"Base64 encoding complete. Length: {len(pdf_base64)}")

        logging.info("Preparing email message...")
        message = {
            "senderAddress": "DoNotReply@mkz-management.com",
            "recipients": {
                "to": [{"address": os.environ.get("MaintenanceEmail")}]
            },
            "content": {
                "subject": f"Maintenance Task PDF - {task_id}",
                "plainText": f"Maintenance task PDF generated at {datetime.datetime.now()}"
                # , "html": f"""
                # <html>
                #     <body>
                #         <h2>Maintenance Task Report</h2>
                #         <p><strong>Task ID:</strong> {task_id}</p>
                #         <p>Generated at: {datetime.datetime.now()}</p>
                #         <p>Please see attached PDF.</p>
                #     </body>
                # </html>"""
            },
            "attachments": [
                {
                    "name": f"maintenance_task_{task_id}.pdf",
                    "contentType": "application/pdf",
                    "contentInBase64": pdf_base64
                }
            ]
        }

        logging.info("Sending email...")
        poller = client.begin_send(message)
        result = poller.result()
        logging.info(f"Email sent successfully!")
        logging.info(f"Result: {result}")
        logging.info("=" * 50)

    except Exception as ex:
        logging.error("=" * 50)
        logging.error(f"BLOB TRIGGER ERROR: {type(ex).__name__}")
        logging.error(f"Error message: {str(ex)}")
        logging.error("Full traceback:", exc_info=True)
        logging.error("=" * 50)
        raise


'''
Barcode Scanned — Redirect to Technician UI
'''
@app.route(route="http_trigger_barcodescan")
def http_trigger_barcodescan(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    id = req.params.get('task_id')

    if not id:
        return func.HttpResponse("Please include ClickUp task id as parameter", status_code=400)

    logging.info(f"QR scan received for task {id}")

    swa_url = os.environ.get("SWA_BASE_URL", "http://localhost:5173")
    redirect_url = f"{swa_url}/task/{id}"

    return func.HttpResponse(
        status_code=302,
        headers={"Location": redirect_url}
    )


'''
Technician UI — Task Data API (GET + PUT)
'''
@app.route(route="task/{task_id}", methods=["GET", "PUT"], auth_level=func.AuthLevel.ANONYMOUS)
def http_trigger_task(req: func.HttpRequest) -> func.HttpResponse:
    task_id = req.route_params.get("task_id")
    if not task_id:
        return func.HttpResponse("Missing task_id", status_code=400)

    if req.method == "GET":
        return _handle_task_get(req, task_id)
    elif req.method == "PUT":
        return _handle_task_put(req, task_id)
    else:
        return func.HttpResponse("Method not allowed", status_code=405)


def _handle_task_get(req: func.HttpRequest, task_id: str) -> func.HttpResponse:
    token = _get_clickup_token()
    cu_headers = {'accept': 'application/json', 'content-type': 'application/json', 'Authorization': token}

    clickup_data = None
    cache_stale = False

    # Always try ClickUp first for fresh data (includes attachments)
    try:
        resp = requests.get(f"https://api.clickup.com/api/v2/task/{task_id}", headers=cu_headers)
        if resp.status_code == 200:
            clickup_data = json.loads(resp.text)
        else:
            logging.warning(f"ClickUp returned {resp.status_code} for task {task_id}")
    except Exception as e:
        logging.warning(f"ClickUp fetch failed: {e}")

    # Read tech-specific fields from Table Storage
    entity = read_task_snapshot(task_id)

    if clickup_data:
        fields = _extract_task_fields(clickup_data)
        # Refresh Table Storage snapshot — MERGE preserves existing tech fields
        try:
            pdf_blob_url = f"https://faclickupbarcodeautomati.blob.core.windows.net/content/{task_id}.pdf"
            write_task_snapshot(task_id, clickup_data, pdf_blob_url)
        except Exception as e:
            logging.warning(f"Table Storage snapshot refresh failed (non-fatal): {e}")
    elif entity:
        # Fall back to cached snapshot if ClickUp is unreachable
        cache_stale = True
        fields = {
            "task_id": task_id,
            "task_name": entity.get("task_name", ""),
            "property_address": entity.get("property_address", ""),
            "issue_description": entity.get("issue_description", ""),
            "action_items": parse_quill_delta(entity.get("action_items_raw", "")),
            "start_date_ms": entity.get("start_date_ms", ""),
            "start_buffer_hours": entity.get("start_buffer_hours", 0),
            "task_status": entity.get("task_status", ""),
            "translate_flag": entity.get("translate_flag", False),
            "attachments": [],
        }
    else:
        return func.HttpResponse(
            json.dumps({"error": "Task not found"}),
            mimetype="application/json",
            status_code=404
        )

    # Merge tech fields from Table Storage
    if entity:
        tech_fields = {
            "arrival_date_iso": entity.get("arrival_date_iso") or "",
            "completion_status": entity.get("completion_status") or "pending",
            "tech_notes": entity.get("tech_notes") or "",
            "last_ui_update_at": entity.get("last_ui_update_at"),
            "snapshot_written_at": entity.get("snapshot_written_at"),
        }
    else:
        tech_fields = {
            "arrival_date_iso": "",
            "completion_status": "pending",
            "tech_notes": "",
            "last_ui_update_at": None,
            "snapshot_written_at": None,
        }

    response_data = {**fields, **tech_fields, "cache_stale": cache_stale}
    response_data.pop("action_items_raw", None)

    return func.HttpResponse(
        json.dumps(response_data),
        mimetype="application/json",
        status_code=200
    )


def _handle_task_put(req: func.HttpRequest, task_id: str) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body", status_code=400)

    token = _get_clickup_token()
    cu_headers = {'accept': 'application/json', 'content-type': 'application/json', 'Authorization': token}

    # Build ClickUp update payload from provided fields
    clickup_payload = {}
    if "clickup_status" in body:
        clickup_payload["status"] = body["clickup_status"]
    if body.get("arrival_date_iso"):
        try:
            dt = datetime.datetime.fromisoformat(body["arrival_date_iso"])
            clickup_payload["start_date"] = int(dt.timestamp() * 1000)
            clickup_payload["start_date_time"] = True
        except ValueError:
            pass

    if clickup_payload:
        try:
            resp = requests.put(
                f"https://api.clickup.com/api/v2/task/{task_id}",
                json=clickup_payload,
                headers=cu_headers
            )
            if resp.status_code not in (200, 201):
                logging.error(f"ClickUp update failed: {resp.status_code} {resp.text}")
        except Exception as e:
            logging.error(f"ClickUp update exception: {e}")

    # Write tech fields to Table Storage
    tech_updates = {k: body[k] for k in ("arrival_date_iso", "completion_status", "tech_notes") if k in body}
    try:
        update_tech_fields(task_id, tech_updates)
    except Exception as e:
        logging.error(f"Table Storage update failed: {e}")
        return func.HttpResponse(f"Failed to save changes: {e}", status_code=500)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return func.HttpResponse(
        json.dumps({"task_id": task_id, **tech_updates, "last_ui_update_at": now}),
        mimetype="application/json",
        status_code=200
    )


'''
Technician UI — Attachment Upload
'''
@app.route(route="task/{task_id}/attachment", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def http_trigger_task_attachment(req: func.HttpRequest) -> func.HttpResponse:
    task_id = req.route_params.get("task_id")

    try:
        body = req.get_json()
        filename = body.get("filename", "attachment")
        content_type = body.get("content_type", "application/octet-stream")
        file_data = base64.b64decode(body["data"])
    except Exception as e:
        return func.HttpResponse(f"Invalid request body: {e}", status_code=400)

    token = _get_clickup_token()
    # No Content-Type header — let requests set the correct multipart boundary
    cu_headers = {'Authorization': token}

    try:
        resp = requests.post(
            f"https://api.clickup.com/api/v2/task/{task_id}/attachment",
            headers=cu_headers,
            files={"attachment": (filename, file_data, content_type)}
        )
        if resp.status_code not in (200, 201):
            return func.HttpResponse(
                f"ClickUp attachment upload failed: {resp.text}",
                status_code=resp.status_code
            )
        result = json.loads(resp.text)
        return func.HttpResponse(
            json.dumps({
                "attachment_id": result.get("id"),
                "name": result.get("title", filename),
                "url": result.get("url"),
                "thumbnail": result.get("thumbnail_medium") or result.get("thumbnail_small"),
            }),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.error(f"Attachment upload failed for task {task_id}: {e}")
        return func.HttpResponse(f"Upload failed: {e}", status_code=500)


'''
Technician UI — PDF Download
'''
@app.route(route="task/{task_id}/pdf", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def http_trigger_task_pdf(req: func.HttpRequest) -> func.HttpResponse:
    task_id = req.route_params.get("task_id")

    try:
        blob_service_client = _get_blob_service_client()
        blob_client = blob_service_client.get_blob_client(container="content", blob=f"{task_id}.pdf")
        pdf_bytes = blob_client.download_blob().readall()
        return func.HttpResponse(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": f'inline; filename="task_{task_id}.pdf"'},
            status_code=200
        )
    except Exception as e:
        logging.error(f"PDF read failed for task {task_id}: {e}")
        return func.HttpResponse(
            json.dumps({"error": "PDF not found"}),
            mimetype="application/json",
            status_code=404
        )
