import os
import requests
import datetime
import uuid
import json
import logging


def download_image_bytes(url):
    """Download image and return as bytes"""
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Failed to download image: {response.status_code}")


def generate_blob_path(task_id):
    
    base_path = ""
    
    current_datetime = datetime.datetime.now()
    date_str = current_datetime.strftime('%Y-%m-%d')
    unique_id = str(uuid.uuid4())
    text_path = f"{base_path}/{task_id}/{date_str}/{unique_id}"
    bc_path = f"{base_path}/{task_id}/{date_str}/{unique_id}"
    return text_path, bc_path


def translate_text(text):
    try:
        if not text:  # handles None, "", etc.
            logging.info("No text provided for translation, returning empty string.")
            return ""
        
        endpoint = "https://api.cognitive.microsofttranslator.com/"

        path = '/translate'
        constructed_url = endpoint + path

        params = {
            'api-version': '3.0',
            'from': 'en',
            'to': ['zh-Hans']
        }

        headers = {
            'Ocp-Apim-Subscription-Key': os.environ.get('TranslationAPIKey'),

            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4())
        }

        body = [{
            'text': text
        }]

        request = requests.post(constructed_url, params=params, headers=headers, json=body)
        response = request.json()

        print(json.dumps(response, sort_keys=True, ensure_ascii=False, indent=4, separators=(',', ': ')))
        return response[0]['translations'][0]['text']
    except Exception as e:
        logging.warning(f"Translation failed, using original text: {e}")
        return text  # fall back to original text



def parse_quill_delta(value_richtext, translate_fn=None):
    """
    Parse ClickUp Quill Delta richtext into a list of ReportLab Paragraphs.
    
    Quill Delta structure:
    - Text content comes in {"insert": "text"} ops
    - Formatting comes in {"insert": "\n", "attributes": {"list": {"list": "bullet"}}} ops
    - A \n op with list attribute means the PRECEDING text was a bullet item
    """
    if not value_richtext:
        return []
    
    try:
        delta = json.loads(value_richtext)
        ops = delta.get("ops", [])
    except (json.JSONDecodeError, AttributeError):
        return []
    
    # Walk ops: accumulate text, and when we hit a \n op check for list attribute
    segments = []
    current_text = ""
    
    for op in ops:
        insert = op.get("insert", "")
        attributes = op.get("attributes", {})
        
        if insert == "\n":
            # This \n terminates the current segment
            list_attr = attributes.get("list", {})
            list_type = list_attr.get("list") if isinstance(list_attr, dict) else None
            
            segments.append({
                "text": current_text.strip(),
                "type": list_type  # "bullet", "ordered", or None
            })
            current_text = ""
        else:
            current_text += insert
    
    # Any trailing text without a terminating \n
    if current_text.strip():
        segments.append({"text": current_text.strip(), "type": None})
    
    # Drop empty segments
    segments = [s for s in segments if s["text"]]
    
    return segments