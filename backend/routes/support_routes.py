"""
Support Chat Routes
Secure Groq proxy endpoint for frontend chat widget.
"""

import os
from flask import Blueprint, jsonify, request
import requests

support_bp = Blueprint('support', __name__, url_prefix='/api/support')

GROQ_ENDPOINT = 'https://api.groq.com/openai/v1/chat/completions'
DEFAULT_MODEL = 'llama-3.1-8b-instant'
FALLBACK_MODELS = ['llama-3.1-8b-instant', 'llama-3.3-70b-versatile']


def _get_groq_config():
    """Load Groq settings from environment at request time."""
    model = os.getenv('GROQ_MODEL', DEFAULT_MODEL).strip() or DEFAULT_MODEL
    max_tokens = int(os.getenv('GROQ_MAX_TOKENS', 300))
    temperature = float(os.getenv('GROQ_TEMPERATURE', 0.7))
    system_prompt = os.getenv(
        'GROQ_SYSTEM_PROMPT',
        'You are a helpful customer support AI assistant for a data integrity platform. Be concise, clear, and practical.'
    )
    return model, max_tokens, temperature, system_prompt


@support_bp.route('/chat', methods=['POST'])
def support_chat():
    """Proxy chat requests to Groq without exposing API key to browser."""
    groq_api_key = os.getenv('GROQ_API_KEY', '').strip()
    if not groq_api_key:
        return jsonify({'error': 'GROQ_API_KEY is not configured on server'}), 503

    body = request.get_json(silent=True) or {}
    raw_messages = body.get('messages', [])

    if not isinstance(raw_messages, list):
        return jsonify({'error': '"messages" must be an array'}), 400

    # Keep payload bounded and only allow expected roles.
    allowed_roles = {'user', 'assistant'}
    sanitized_messages = []
    for item in raw_messages[-20:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get('role', '')).strip()
        content = str(item.get('content', '')).strip()
        if role not in allowed_roles or not content:
            continue
        sanitized_messages.append({'role': role, 'content': content[:4000]})

    if not sanitized_messages:
        return jsonify({'error': 'At least one valid message is required'}), 400

    model, max_tokens, temperature, system_prompt = _get_groq_config()
    model_candidates = [model] + [m for m in FALLBACK_MODELS if m != model]

    payload = {
        'messages': [{'role': 'system', 'content': system_prompt}] + sanitized_messages,
        'max_tokens': max_tokens,
        'temperature': temperature,
    }

    resp = None
    data = None
    last_error = None

    for candidate_model in model_candidates:
        try:
            candidate_payload = dict(payload)
            candidate_payload['model'] = candidate_model

            resp = requests.post(
                GROQ_ENDPOINT,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {groq_api_key}',
                },
                json=candidate_payload,
                timeout=25,
            )
        except requests.RequestException as exc:
            return jsonify({'error': f'Groq request failed: {exc}'}), 502

        if resp.ok:
            data = resp.json()
            break

        body_text = resp.text[:1000]
        last_error = {'status': resp.status_code, 'body': body_text}

        # If model is decommissioned/unknown, try next fallback model.
        if 'model_decommissioned' in body_text or 'not_supported' in body_text or 'model_not_found' in body_text:
            continue

        return jsonify({'error': f'Groq API error {resp.status_code}', 'details': body_text}), 502

    if data is None:
        return jsonify({
            'error': f'Groq API error {last_error["status"] if last_error else 502}',
            'details': (last_error['body'] if last_error else 'Model selection failed')
        }), 502

    reply = (
        data.get('choices', [{}])[0]
        .get('message', {})
        .get('content', '')
    )
    reply = str(reply).strip()

    if not reply:
        return jsonify({'error': 'Empty response from Groq'}), 502

    return jsonify({'reply': reply}), 200
