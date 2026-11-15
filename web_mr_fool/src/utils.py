"""
utils.py: Token generation and progression helpers for Mr. Fool CTF.
"""

import secrets
import os

# Local/dev fallback only. Real deploys must set FLAG via environment variable.
FLAG = os.environ.get('FLAG', 'TecFest26{h34rtb34t_h34rtbr34k_4ll_0v3r_g4l4u_p4r4h_b4ng3t}')

SEQUENCES = [
    ('S9', 'Seer', '👁️'),
    ('S8', 'Clown', '🎭'),
    ('S7', 'Magician', '🪄'),
    ('S6', 'Faceless', '🎭'),
    ('S3', 'Scholar of Yore', '📜'),
]

ACTING_PRINCIPLES = {
    'S9': 'Observe what others overlook.',
    'S8': 'Make the system laugh at its own mistakes.',
    'S7': 'Make something appear that should not exist.',
    'S6': 'Become someone you are not.',
    'S3': 'Read what was written before the world began.',
    'S0': 'Only when all masks are worn can the true face be seen.',
}

SEQUENCE_URLS = {
    'S9': '/s9/seer',
    'S8': '/s8/clown',
    'S7': '/s7/magician',
    'S6': '/s6/faceless',
    'S3': '/s3/scholar',
}

SEQUENCE_NEXT = {
    'S9': 'S8',
    'S8': 'S7',
    'S7': 'S6',
    'S6': 'S3',
    'S3': 'S0',
}


def generate_token():
    return secrets.token_hex(16)


def generate_solution(phase, sequence_id):
    """Generate unique solution string per player session."""
    seed = secrets.token_hex(8)
    return f"{phase}_{sequence_id}_{seed}"


# Per-instance session secret key.
SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(16)


def get_current_sequence(completed):
    """Determine which sequence the player should tackle next."""
    for seq, _, _ in SEQUENCES:
        if seq not in completed:
            return seq
    if len(completed) >= 5:
        return 'S0'
    return None

