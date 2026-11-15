"""
app.py: Main Flask application for Mr. Fool CTF.
Session-based progression across 5 Sequences and S0 finale.
"""

import json
import hmac
import hashlib
import secrets
import re
from functools import wraps
from flask import (
    Flask, render_template, request, jsonify,
    session, redirect, url_for, make_response, g
)
from models import db, Player, PotionToken, Spell, Joke, PotionSecret
from utils import (
    SEQUENCES, ACTING_PRINCIPLES, SEQUENCE_URLS,
    SEQUENCE_NEXT, SECRET_KEY, FLAG,
    get_current_sequence, generate_token
)
import urllib.parse
import os

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/mr_fool.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()
    if not Joke.query.first():
        db.session.add_all([
            Joke(content='Why did the Beyonder cross the road? To become someone else on the other side.', author='attendant'),
            Joke(content='I told a joke about UNION SELECT but nobody joined in.', author='clown'),
        ])
    if not PotionSecret.query.first():
        db.session.add(PotionSecret(name='clown_potion', secret_code='laughing_error_s8'))
    db.session.commit()



def get_completed():
    return session.get('completed', [])


def set_completed(seq_id):
    completed = get_completed()
    if seq_id not in completed:
        completed.append(seq_id)
        session['completed'] = completed


def require_sequence(seq_id):
    """Decorator: ensures player has completed the previous sequence."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            completed = get_completed()
            idx = None
            for i, (s, _, _) in enumerate(SEQUENCES):
                if s == seq_id:
                    idx = i
                    break

            if idx is None:
                return redirect('/')

            if idx == 0:
                return f(*args, **kwargs)

            prev = SEQUENCES[idx - 1][0]
            if prev not in completed:
                return redirect('/')
            return f(*args, **kwargs)
        return wrapped
    return decorator


@app.context_processor
def inject_globals():
    completed = get_completed()
    current = get_current_sequence(completed)
    if current and current != 'S0':
        current_name = next((n for s, n, _ in SEQUENCES if s == current), '')
    else:
        current_name = ''
    return dict(
        completed_seq=completed,
        current_seq=current,
        current_name=current_name,
        completion_count=len(completed),
        all_completed=len(completed) >= 5,
        seq_urls=SEQUENCE_URLS,
        seq_emblems={
            'S9': 'seer',
            'S8': 'clown',
            'S7': 'magician',
            'S6': 'faceless',
            'S3': 'scholar',
            'S0': 'fool'
        }
    )


@app.route('/')
def index():
    completed = get_completed()
    current = get_current_sequence(completed)
    current_name = ''
    acting_principle = ''
    if current and current != 'S0':
        for s, n, _ in SEQUENCES:
            if s == current:
                current_name = n
                break
        acting_principle = ACTING_PRINCIPLES.get(current, '')
    return render_template('index.html',
                         sequences=SEQUENCES,
                         current_seq=current,
                         current_name=current_name,
                         acting_principle=acting_principle)


@app.route('/reset')
def reset():
    session.clear()
    return redirect('/')


@app.route('/progress')
def progress():
    return jsonify({'completed': get_completed()})


def extract_request_payload():
    """Extract dict payload from JSON body or form submission."""
    data = request.get_json(silent=True)
    if data is not None and isinstance(data, dict):
        return data
    if request.form:
        return request.form.to_dict()
    if request.values:
        return request.values.to_dict()
    return {}


def extract_token_from_payload(data):
    """Extract token or solution string from payload dictionary."""
    if not isinstance(data, dict):
        return ''
    for key in ('token', 'solution', 'answer', 'code'):
        if key in data and data[key] is not None:
            return data[key]
    for key in ('token', 'solution', 'answer', 'code'):
        if key in data:
            return data[key]
    return ''


def verify_solution(seq_id, answer):
    """Defensively verify token hash against sequence answer key."""
    if not isinstance(answer, str) or not isinstance(seq_id, str):
        return False
    if len(answer) > 256:
        return False
    # Exactly one valid token per sequence, hashed to prevent answer key disclosure.
    answer_hashes = {
        'S9': ['bf9a3f02a1410692b9c1e685071857a855de09895ce7c1c4240a71ba4b7f9411'],
        'S8': ['f00257a8e21478388a89d4cf7a3e34cb11c3606c05aa16ead75520e26e2c0058'],
        'S7': ['e8c354edf7e1273e9fc7c10dcc2f49187af43ce9261a42a645d775a0d19adeb9'],
        'S6': ['94d68f0a1aee982be54c91d9f973fd4f8c64096e05c0e4eea1b54d14c1d43e62'],
        'S3': ['c3eecf4635f9cdd350a29e3cd7513e0624c639ad5d3e9f021a1ada29ba168486'],
    }
    valid = answer_hashes.get(seq_id, [])
    submitted = hashlib.sha256(answer.strip().encode()).hexdigest()
    return any(hmac.compare_digest(submitted, h) for h in valid)


def process_sequence_verification(seq_id, answer):
    """Core verification and progression state handler."""
    valid_sequences = [s[0] for s in SEQUENCES]
    if seq_id not in valid_sequences:
        return {'success': False, 'message': 'Invalid sequence identifier.'}

    completed = get_completed()
    if seq_id in completed:
        return {'success': False, 'message': 'This Sequence has already been digested.'}

    current = get_current_sequence(completed)
    if current != seq_id:
        return {'success': False, 'message': 'You must complete prior Sequences first.'}

    if verify_solution(seq_id, answer):
        set_completed(seq_id)
        next_seq = SEQUENCE_NEXT.get(seq_id)
        next_url = '/'
        if next_seq == 'S0':
            next_url = '/s0/fool'
        elif next_seq:
            next_url = SEQUENCE_URLS.get(next_seq, '/')

        return {
            'success': True,
            'next_sequence': next_seq,
            'completed_count': len(get_completed()),
            'redirect': next_url,
            'message': f'The {seq_id} potion has been digested.'
        }

    return {
        'success': False,
        'message': 'The potion recoils. Your understanding is incomplete.'
    }


@app.route('/complete/<seq_id>', methods=['POST'])
def complete_sequence(seq_id):
    """Legacy UI route: sequence ID in path parameter."""
    data = extract_request_payload()
    answer = extract_token_from_payload(data)
    result = process_sequence_verification(seq_id, answer)
    return jsonify(result)


@app.route('/api/verify_solution', methods=['POST'])
def api_verify_solution():
    """PROJECT.md interface contract route: sequence ID in request body."""
    data = extract_request_payload()
    seq_id = data.get('sequence') or data.get('seq_id') or data.get('seq')
    if isinstance(seq_id, str):
        seq_id = seq_id.strip()
    if not seq_id:
        return jsonify({'success': False, 'message': 'Missing sequence identifier.'})

    answer = extract_token_from_payload(data)
    result = process_sequence_verification(seq_id, answer)
    return jsonify(result)


# ========================================
# S9 Seer (Recon / Info Disclosure)
# ========================================

@app.route('/s9/seer')
def s9_seer():
    resp = make_response(render_template('s9_seer.html'))
    resp.headers['X-Hint'] = 'Seek the prophecy parameter.'
    return resp


@app.route('/s9/seer/robots.txt')
def s9_robots():
    return """User-agent: *
Disallow: /s9/seer/hidden
Allow: /s9/seer/

# Those who observe deeply will find the prophecy parameter.""", 200, {'Content-Type': 'text/plain'}


@app.route('/s9/seer/hidden')
def s9_hidden():
    return """<html><body>
<!-- The Seer observes the truth. -->
<!-- Potion Token: seer_sees_all -->
<p>The prophecy is fulfilled. Digest the token: <code>seer_sees_all</code></p>
</body></html>"""


# S8 Clown (Verbose Errors)

@app.route('/s8/clown')
@require_sequence('S8')
def s8_clown():
    return render_template('s8_clown.html')


@app.route('/s8/clown/joke', methods=['POST'])
@require_sequence('S8')
def s8_joke():
    data = request.get_json(silent=True) or {}
    joke = data.get('joke', '')
    conn = None
    try:
        conn = db.engine.raw_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM jokes WHERE content = '{joke}'")
        result = cursor.fetchall()
        return jsonify({'success': True, 'response': str(result)})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'schema': {
                'target_table': 'potion_secrets',
                'columns': ['id', 'name', 'secret_code']
            },
            'hint': 'The clown makes the system laugh at its own mistakes. Backstage schema is visible at /s8/clown/schema.'
        }), 500
    finally:
        if conn is not None:
            conn.close()


@app.route('/s8/clown/schema', methods=['GET'])
@require_sequence('S8')
def s8_schema():
    return jsonify({
        'tables': ['jokes', 'potion_secrets'],
        'columns': {
            'jokes': ['id', 'content', 'author'],
            'potion_secrets': ['id', 'name', 'secret_code']
        }
    })


# S7 Magician (Mass Assignment)

@app.route('/s7/magician')
@require_sequence('S7')
def s7_magician():
    return render_template('s7_magician.html')


@app.route('/s7/magician/api/spells/create', methods=['POST'])
@require_sequence('S7')
def s7_create_spell():
    data = request.get_json(silent=True) or {}
    player_id = session.get('player_id', 'anon')
    spell = Spell(
        player_id=player_id,
        name=data.get('name', 'unnamed'),
        spell_type=data.get('type', data.get('spell_type', 'cantrip')),
        approved=data.get('approved', False),
        secret_code=data.get('secret_code', '')
    )
    db.session.add(spell)
    db.session.commit()
    return jsonify({
        'success': True,
        'spell': {
            'id': spell.id,
            'name': spell.name,
            'type': spell.spell_type,
            'approved': spell.approved,
            'secret_code': spell.secret_code
        },
        'message': 'ANCIENT SPELL APPROVED. The potion token is: unauthorized_spell' if spell.approved else 'Spell created (approved: false). The Magician only grants power to spells with "approved": true in the JSON payload.'
    })


@app.route('/s7/magician/api/spells', methods=['GET'])
@require_sequence('S7')
def s7_list_spells():
    player_id = session.get('player_id', 'anon')
    spells = Spell.query.filter_by(player_id=player_id).all()
    return jsonify([{
        'id': s.id, 'name': s.name, 'type': s.spell_type,
        'approved': s.approved, 'secret_code': s.secret_code
    } for s in spells])


# S6 Faceless (Auth Bypass / JWT)

@app.route('/s6/faceless')
@require_sequence('S6')
def s6_faceless():
    return render_template('s6_faceless.html')


@app.route('/s6/faceless/login', methods=['POST'])
@require_sequence('S6')
def s6_login():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '')
    password = data.get('password', '')

    if username == 'guest' and password == 'guest':
        token_data = json.dumps({
            'username': 'guest',
            'role': 'user',
            'exp': 9999999999
        })
        token = base64_encode(token_data) + '.' + base64_encode('fakesig')
        return jsonify({'success': True, 'token': token, 'user': 'guest', 'role': 'user'})

    return jsonify({'success': False, 'message': 'Invalid credentials. Guest login: guest/guest'})


@app.route('/s6/faceless/admin', methods=['GET'])
@require_sequence('S6')
def s6_admin():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'success': False, 'message': 'No token provided'})

    token = auth[7:]
    try:
        parts = token.split('.')
        if len(parts) != 2:
            return jsonify({'success': False, 'message': 'Invalid JWT format.'})

        raw_data = base64_decode(parts[0])
        data = json.loads(raw_data)

        if data.get('username') == 'admin' or data.get('role') == 'admin':
            return jsonify({
                'success': True,
                'message': 'Welcome, High-Sequence Beyonder.',
                'secret': 'The Faceless potion awaits those who become someone they are not. Token: forged_identity'
            })
        else:
            return jsonify({
                'success': False,
                'message': f"Admin access required. Expected payload attributes: username='admin' or role='admin'. Received: username='{data.get('username')}', role='{data.get('role')}'. Note: Tokens follow base64(payload).base64(signature)."
            })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error parsing token: {str(e)}'})


def base64_encode(s):
    import base64
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip('=')


def base64_decode(s):
    import base64
    s += '=' * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s).decode()


# S3 Scholar of Yore (LFI / Path Traversal)

@app.route('/s3/scholar')
@require_sequence('S3')
def s3_scholar():
    return render_template('s3_scholar.html')


@app.route('/s3/scholar/view')
@require_sequence('S3')
def s3_view_scroll():
    scroll = request.args.get('scroll', 'scroll_of_truth.txt')

    SCROLLS_DIR = os.environ.get('SCROLLS_DIR', '/opt/ctf/sequence_data/')

    # Containment check: traversal allows accessing /opt/ctf/secrets/lfi_token.txt
    # but strictly prevents escaping /opt/ctf/.
    ARCHIVE_ROOT = os.path.realpath('/opt/ctf') + os.sep
    filepath = SCROLLS_DIR + scroll
    real_filepath = os.path.realpath(filepath)
    if not real_filepath.startswith(ARCHIVE_ROOT):
        return jsonify({'error': 'Access denied'})
    filepath = real_filepath

    try:
        with open(filepath, 'r') as f:
            content = f.read(2000)
        if 'BEYONDER' in content or 'lfi_token' in content:
            return jsonify({'content': content, 'hint': 'You found the hidden token!'})
        return jsonify({'content': content})
    except FileNotFoundError:
        return jsonify({'error': 'Scroll not found. Have you examined ../secrets/lfi_token.txt?'})
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'})


# S0 The Fool (Finale)

@app.route('/s0/fool')
def s0_fool():
    completed = get_completed()
    if len(completed) < 5:
        return redirect('/')
    return render_template('s0_fool.html', flag=FLAG, sequences=SEQUENCES)


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
