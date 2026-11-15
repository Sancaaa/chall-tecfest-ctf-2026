#!/usr/bin/env python3
"""
test_challenger_stress.py: Adversarial stress test harness for Mr. Fool CTF.
Tests sequence state transitions, bypass attempts, token fuzzing,
softened exploit mechanisms, boundary containment, and contract compliance.
"""

import os
import sys
import json
import base64
import unittest

src_dir = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_dir)

import app
import utils
import models


class AdversarialMrFoolTests(unittest.TestCase):
    def setUp(self):
        app.app.config['TESTING'] = True
        app.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with app.app.app_context():
            app.db.create_all()
            if not models.Joke.query.first():
                app.db.session.add_all([
                    models.Joke(content='Why did the Beyonder cross the road? To become someone else on the other side.', author='attendant'),
                    models.Joke(content='I told a joke about UNION SELECT but nobody joined in.', author='clown'),
                ])
            if not models.PotionSecret.query.first():
                app.db.session.add(models.PotionSecret(name='clown_potion', secret_code='laughing_error_s8'))
            app.db.session.commit()
        self.client = app.app.test_client()

    # ---------------------------------------------------------
    # 1. State Machine & Sequence Skipping Attacks
    # ---------------------------------------------------------
    def test_01_direct_access_unauthorized_sequences(self):
        """Attacker tries to bypass progression by accessing later stages directly."""
        unauthorized = ['/s8/clown', '/s7/magician', '/s6/faceless', '/s3/scholar', '/s0/fool']
        for path in unauthorized:
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 302, f"Direct access to {path} must redirect (302), got {resp.status_code}")
            self.assertEqual(resp.headers.get('Location'), '/')

    def test_02_out_of_order_completion_submission(self):
        """Attacker tries to solve S8, S7, S6, or S3 before solving S9."""
        attacks = [
            ('S8', 'laughing_error_s8'),
            ('S7', 'unauthorized_spell'),
            ('S6', 'forged_identity'),
            ('S3', 'scholar_reading_deep'),
        ]
        for seq, tok in attacks:
            resp = self.client.post(f'/complete/{seq}', json={'answer': tok})
            data = resp.get_json()
            self.assertFalse(data.get('success'), f"Submission to {seq} without prerequisites must fail")
            self.assertIn("You must complete prior Sequences first", data.get('message', ''))

    def test_03_invalid_and_phantom_sequence_submissions(self):
        """Attacker tries to complete S0 or non-existent sequences directly."""
        resp = self.client.post('/complete/S0', json={'answer': 'anything'})
        data = resp.get_json()
        self.assertFalse(data.get('success'))

        resp = self.client.post('/complete/S99', json={'answer': 'anything'})
        data = resp.get_json()
        self.assertFalse(data.get('success'))

        resp = self.client.post('/complete/admin', json={'answer': 'anything'})
        data = resp.get_json()
        self.assertFalse(data.get('success'))

    def test_04_replay_already_completed_sequence(self):
        """Attacker tries to submit the same completed sequence again."""
        # Complete S9
        resp = self.client.post('/complete/S9', json={'answer': 'seer_sees_all'})
        self.assertTrue(resp.get_json().get('success'))

        # Re-submit S9
        resp2 = self.client.post('/complete/S9', json={'answer': 'seer_sees_all'})
        data2 = resp2.get_json()
        self.assertFalse(data2.get('success'))
        self.assertIn("already been digested", data2.get('message', ''))

    def test_05_session_reset_revocation(self):
        """Verify /reset flushes completed sequences and revokes access to subsequent stages."""
        # Complete S9
        self.client.post('/complete/S9', json={'answer': 'seer_sees_all'})
        resp = self.client.get('/s8/clown')
        self.assertEqual(resp.status_code, 200)

        # Reset session
        reset_resp = self.client.get('/reset')
        self.assertEqual(reset_resp.status_code, 302)

        # Verify S8 is now inaccessible again
        resp_after = self.client.get('/s8/clown')
        self.assertEqual(resp_after.status_code, 302)

        # Verify progress is empty
        prog = self.client.get('/progress').get_json()
        self.assertEqual(prog.get('completed'), [])

    # ---------------------------------------------------------
    # 2. Token Verification & Fuzzing
    # ---------------------------------------------------------
    def test_06_token_fuzzing_and_type_confusion(self):
        """Test complete/<seq> with malformed bodies, wrong types, and fuzzing payloads."""
        # Missing payload / empty JSON
        resp = self.client.post('/complete/S9', json={})
        self.assertFalse(resp.get_json().get('success'))

        # None / null token: safely rejected without unhandled crash
        resp_none = self.client.post('/complete/S9', json={'answer': None})
        self.assertEqual(resp_none.status_code, 200)
        self.assertFalse(resp_none.get_json().get('success'))

        # Integer token: safely rejected without unhandled crash
        resp_int = self.client.post('/complete/S9', json={'answer': 12345})
        self.assertEqual(resp_int.status_code, 200)
        self.assertFalse(resp_int.get_json().get('success'))

        # Non-dict JSON root: safely rejected without unhandled crash
        resp_list = self.client.post('/complete/S9', json=[1, 2, 3])
        self.assertEqual(resp_list.status_code, 200)
        self.assertFalse(resp_list.get_json().get('success'))

        # Wrong token / Cross-sequence token (S8 token submitted for S9)
        resp_cross = self.client.post('/complete/S9', json={'answer': 'laughing_error_s8'})
        self.assertFalse(resp_cross.get_json().get('success'))

        # Whitespace handling: trailing and leading whitespace
        resp_ws = self.client.post('/complete/S9', json={'answer': '  seer_sees_all  \n'})
        self.assertTrue(resp_ws.get_json().get('success'), "strip() handles leading/trailing whitespace")

    def test_07_alternate_field_names(self):
        """Test whether 'token' or 'code' field names work as alternatives to 'answer'."""
        # Test alternative parameter name 'token'
        resp = self.client.post('/complete/S9', json={'token': 'seer_sees_all'})
        self.assertTrue(resp.get_json().get('success'))

        # Next is S8, test alternative parameter name 'code'
        resp2 = self.client.post('/complete/S8', json={'code': 'laughing_error_s8'})
        self.assertTrue(resp2.get_json().get('success'))

    # ---------------------------------------------------------
    # 3. Contract Compliance: /api/verify_solution Check
    # ---------------------------------------------------------
    def test_08_project_md_verify_solution_endpoint(self):
        """
        Check if POST /api/verify_solution as specified in PROJECT.md exists
        and verifies solutions with JSON or form data.
        Contract in PROJECT.md specifies:
        POST /api/verify_solution with JSON {"sequence": "S9", "token": "..."}
        or form data sequence=S9&solution=...
        """
        # 1. JSON submission
        resp_json = self.client.post('/api/verify_solution', json={'sequence': 'S9', 'token': 'seer_sees_all'})
        self.assertEqual(resp_json.status_code, 200)
        data_json = resp_json.get_json()
        self.assertTrue(data_json.get('success'))
        self.assertEqual(data_json.get('next_sequence'), 'S8')
        self.assertEqual(data_json.get('completed_count'), 1)
        self.assertEqual(data_json.get('redirect'), '/s8/clown')

        # 2. Form data submission
        resp_form = self.client.post('/api/verify_solution', data={'sequence': 'S8', 'solution': 'laughing_error_s8'})
        self.assertEqual(resp_form.status_code, 200)
        data_form = resp_form.get_json()
        self.assertTrue(data_form.get('success'))
        self.assertEqual(data_form.get('next_sequence'), 'S7')
        self.assertEqual(data_form.get('completed_count'), 2)
        self.assertEqual(data_form.get('redirect'), '/s7/magician')

    # ---------------------------------------------------------
    # 4. Softened Exploits Stress Testing
    # ---------------------------------------------------------
    def test_09_s9_seer_reconnaissance(self):
        """Test S9 Seer endpoints."""
        r_page = self.client.get('/s9/seer')
        self.assertEqual(r_page.status_code, 200)
        self.assertEqual(r_page.headers.get('X-Hint'), 'Seek the prophecy parameter.')

        r_robots = self.client.get('/s9/seer/robots.txt')
        self.assertEqual(r_robots.status_code, 200)
        self.assertIn('Disallow: /s9/seer/hidden', r_robots.data.decode())

        r_hidden = self.client.get('/s9/seer/hidden')
        self.assertEqual(r_hidden.status_code, 200)
        self.assertIn('seer_sees_all', r_hidden.data.decode())

    def test_10_s8_clown_sqli_and_error_leak(self):
        """Test S8 Clown SQLi, error leakage, and schema endpoint."""
        self.client.post('/complete/S9', json={'answer': 'seer_sees_all'})

        # Schema route
        r_schema = self.client.get('/s8/clown/schema')
        self.assertEqual(r_schema.status_code, 200)
        d_schema = r_schema.get_json()
        self.assertIn('potion_secrets', d_schema.get('tables', []))
        self.assertIn('secret_code', d_schema.get('columns', {}).get('potion_secrets', []))

        # Error disclosure
        r_err = self.client.post('/s8/clown/joke', json={'joke': "'"})
        self.assertEqual(r_err.status_code, 500)
        d_err = r_err.get_json()
        self.assertIn('schema', d_err)
        self.assertIn('target_table', d_err['schema'])
        self.assertEqual(d_err['schema']['target_table'], 'potion_secrets')

        # UNION injection
        payload = "x' UNION SELECT id, secret_code, name FROM potion_secrets--"
        r_inj = self.client.post('/s8/clown/joke', json={'joke': payload})
        self.assertEqual(r_inj.status_code, 200)
        self.assertIn('laughing_error_s8', r_inj.get_json().get('response', ''))

    def test_11_s7_magician_mass_assignment(self):
        """Test S7 Magician mass assignment and rejection hint."""
        self.client.post('/complete/S9', json={'answer': 'seer_sees_all'})
        self.client.post('/complete/S8', json={'answer': 'laughing_error_s8'})

        # Rejection message
        r_unapproved = self.client.post('/s7/magician/api/spells/create', json={'name': 'Spark', 'type': 'cantrip'})
        self.assertEqual(r_unapproved.status_code, 200)
        self.assertIn('"approved": true', r_unapproved.get_json().get('message', ''))
        self.assertFalse(r_unapproved.get_json().get('spell', {}).get('approved'))

        # Mass assignment with approved=True
        r_approved = self.client.post('/s7/magician/api/spells/create', json={'name': 'Inferno', 'type': 'sorcery', 'approved': True})
        self.assertEqual(r_approved.status_code, 200)
        d_app = r_approved.get_json()
        self.assertTrue(d_app.get('spell', {}).get('approved'))
        self.assertIn('unauthorized_spell', d_app.get('message', ''))

    def test_12_s6_faceless_jwt_spoofing(self):
        """Test S6 Faceless login, rejection hint, and admin spoofing variations."""
        self.client.post('/complete/S9', json={'answer': 'seer_sees_all'})
        self.client.post('/complete/S8', json={'answer': 'laughing_error_s8'})
        self.client.post('/complete/S7', json={'answer': 'unauthorized_spell'})

        def b64url(s):
            return base64.urlsafe_b64encode(s.encode()).decode().rstrip('=')

        # Invalid token header
        r_no_auth = self.client.get('/s6/faceless/admin')
        self.assertFalse(r_no_auth.get_json().get('success'))

        # Token with role=user
        user_jwt = f"{b64url(json.dumps({'username': 'guest', 'role': 'user'}))}.{b64url('sig')}"
        r_user = self.client.get('/s6/faceless/admin', headers={'Authorization': f'Bearer {user_jwt}'})
        self.assertFalse(r_user.get_json().get('success'))
        self.assertIn("username='admin' or role='admin'", r_user.get_json().get('message', ''))

        # Token variation 1: role='admin'
        admin_jwt_1 = f"{b64url(json.dumps({'username': 'anon', 'role': 'admin'}))}.{b64url('fake')}"
        r_admin_1 = self.client.get('/s6/faceless/admin', headers={'Authorization': f'Bearer {admin_jwt_1}'})
        self.assertTrue(r_admin_1.get_json().get('success'))
        self.assertIn('forged_identity', r_admin_1.get_json().get('secret', ''))

        # Token variation 2: username='admin'
        admin_jwt_2 = f"{b64url(json.dumps({'username': 'admin', 'role': 'viewer'}))}.{b64url('fake')}"
        r_admin_2 = self.client.get('/s6/faceless/admin', headers={'Authorization': f'Bearer {admin_jwt_2}'})
        self.assertTrue(r_admin_2.get_json().get('success'))
        self.assertIn('forged_identity', r_admin_2.get_json().get('secret', ''))

    def test_13_s3_scholar_lfi_and_containment(self):
        """Test S3 Scholar path traversal and archive containment boundary."""
        self.client.post('/complete/S9', json={'answer': 'seer_sees_all'})
        self.client.post('/complete/S8', json={'answer': 'laughing_error_s8'})
        self.client.post('/complete/S7', json={'answer': 'unauthorized_spell'})
        self.client.post('/complete/S6', json={'answer': 'forged_identity'})

        # Valid traversal to ../secrets/lfi_token.txt
        r_lfi = self.client.get('/s3/scholar/view', query_string={'scroll': '../secrets/lfi_token.txt'})
        d_lfi = r_lfi.get_json()
        self.assertIn('scholar_reading_deep', d_lfi.get('content', ''))

        # Traversal escape attempts escaping /opt/ctf/ boundary
        escapes = [
            '../../../../etc/passwd',
            '../../../etc/shadow',
            '../../../../windows/win.ini',
            '../../app/app.py',
        ]
        for escape in escapes:
            r_esc = self.client.get('/s3/scholar/view', query_string={'scroll': escape})
            d_esc = r_esc.get_json()
            self.assertEqual(d_esc.get('error'), 'Access denied', f"Path {escape} must be denied")

    # ---------------------------------------------------------
    # 5. Full End-to-End Progression and Flag Capture
    # ---------------------------------------------------------
    def test_14_end_to_end_flag_recovery(self):
        """Complete all 5 stages in order and verify flag at /s0/fool."""
        # 1. S9
        self.client.post('/complete/S9', json={'answer': 'seer_sees_all'})
        # 2. S8
        self.client.post('/complete/S8', json={'answer': 'laughing_error_s8'})
        # 3. S7
        self.client.post('/complete/S7', json={'answer': 'unauthorized_spell'})
        # 4. S6
        self.client.post('/complete/S6', json={'answer': 'forged_identity'})
        # 5. S3
        self.client.post('/complete/S3', json={'answer': 'scholar_reading_deep'})

        # S0 access
        r_s0 = self.client.get('/s0/fool')
        self.assertEqual(r_s0.status_code, 200)
        html = r_s0.data.decode()
        self.assertIn('TecFest26{h34rtb34t_h34rtbr34k_4ll_0v3r_g4l4u_p4r4h_b4ng3t}', html)
        self.assertIn('all five potions', html)

    def test_15_s8_connection_resource_cleanup_stress(self):
        """Verify SQLite connections are safely closed in finally block and not leaked on errors."""
        from unittest.mock import patch
        self.client.post('/complete/S9', json={'answer': 'seer_sees_all'})

        with app.app.app_context():
            engine = app.db.engine
            orig_raw = engine.raw_connection
            closed_calls = []

            def mocked_raw():
                conn = orig_raw()
                orig_close = conn.close
                def spy_close():
                    closed_calls.append(True)
                    return orig_close()
                conn.close = spy_close
                return conn

            with patch.object(engine, 'raw_connection', side_effect=mocked_raw):
                # Error request (intended schema disclosure)
                resp_err = self.client.post('/s8/clown/joke', json={'joke': "'"})
                self.assertEqual(resp_err.status_code, 500)
                self.assertEqual(len(closed_calls), 1, "conn.close() must be called on SQL error")

                # Success request
                resp_ok = self.client.post('/s8/clown/joke', json={'joke': 'normal'})
                self.assertEqual(resp_ok.status_code, 200)
                self.assertEqual(len(closed_calls), 2, "conn.close() must be called on query success")

        # Test pool health under 30 consecutive error queries
        for _ in range(30):
            r = self.client.post('/s8/clown/joke', json={'joke': "'"})
            self.assertEqual(r.status_code, 500)
        with app.app.app_context():
            self.assertEqual(app.db.engine.pool.checkedout(), 0)


if __name__ == '__main__':
    unittest.main()
