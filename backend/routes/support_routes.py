"""
Support Chat Routes
Secure Groq proxy endpoint for frontend chat widget.
"""

import os
from flask import Blueprint, jsonify, request
import requests

support_bp = Blueprint('support', __name__, url_prefix='/api/support')

GROQ_ENDPOINT = 'https://api.groq.com/openai/v1/chat/completions'
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama3-8b-8192')
MAX_TOKENS = int(os.getenv('GROQ_MAX_TOKENS', 300))
TEMPERATURE = float(os.getenv('GROQ_TEMPERATURE', 0.7))
SYSTEM_PROMPT = os.getenv(
    'GROQ_SYSTEM_PROMPT',
    'You are a helpful customer support AI assistant for a data integrity platform. Be concise, clear, and practical.'
)


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

    payload = {
        'model': GROQ_MODEL,
        'messages': [{'role': 'system', 'content': SYSTEM_PROMPT}] + sanitized_messages,
        'max_tokens': MAX_TOKENS,
        'temperature': TEMPERATURE,
    }

    try:
        resp = requests.post(
            GROQ_ENDPOINT,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {groq_api_key}',
            },
            json=payload,
            timeout=25,
        )
    except requests.RequestException as exc:
        return jsonify({'error': f'Groq request failed: {exc}'}), 502

    if not resp.ok:
        return jsonify({'error': f'Groq API error {resp.status_code}', 'details': resp.text[:600]}), 502

    data = resp.json()
    reply = (
        data.get('choices', [{}])[0]
        .get('message', {})
        .get('content', '')
    )
    reply = str(reply).strip()

    if not reply:
        return jsonify({'error': 'Empty response from Groq'}), 502

    return jsonify({'reply': reply}), 200
