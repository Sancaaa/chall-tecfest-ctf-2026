#!/usr/bin/env python3
"""
test_challenger_round2.py: Challenger Iteration 2 Adversarial Verification Harness.
Performs empirical stress-testing of:
1. Dual verification routes (/complete/<seq_id> and /api/verify_solution) across JSON, Form, and Query formats.
2. Defenses against type confusion, nulls, integers, oversized tokens, and non-dict JSON roots.
3. S3 LFI traversal containment, directory traversal escape attempts, null-byte injection, and boundary checks.
4. Deleted routes (/s1/*, /s2/*, /s4/*, /s5/*) across all HTTP methods (GET, POST, PUT, DELETE, OPTIONS).
5. S8 SQLite connection pool resilience under rapid error stress.
6. Reference solver determinism under repeated execution.
7. Workspace anti-slop and em dash hygiene.
"""

import os
import sys
import json
import base64
import unittest
import threading
import time
from unittest.mock import patch

src_dir = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_dir)

import app
import utils
import models


class AdversarialRound2Tests(unittest.TestCase):
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

    # =========================================================================
    # SECTION 1: Dual Verification Routes & Interface Contract Compliance
    # =========================================================================

    def test_01_dual_routes_json_and_form_full_progression(self):
        """Verify full progression S9->S8->S7->S6->S3->S0 strictly via /api/verify_solution."""
        # S9 via JSON with 'token'
        r9 = self.client.post('/api/verify_solution', json={'sequence': 'S9', 'token': 'seer_sees_all'})
        self.assertEqual(r9.status_code, 200)
        d9 = r9.get_json()
        self.assertTrue(d9['success'])
        self.assertEqual(d9['next_sequence'], 'S8')
        self.assertEqual(d9['completed_count'], 1)
        self.assertEqual(d9['redirect'], '/s8/clown')

        # S8 via Form Data with 'solution'
        r8 = self.client.post('/api/verify_solution', data={'sequence': 'S8', 'solution': 'laughing_error_s8'})
        self.assertEqual(r8.status_code, 200)
        d8 = r8.get_json()
        self.assertTrue(d8['success'])
        self.assertEqual(d8['next_sequence'], 'S7')
        self.assertEqual(d8['completed_count'], 2)
        self.assertEqual(d8['redirect'], '/s7/magician')

        # S7 via JSON with 'answer' and 'seq_id' alias
        r7 = self.client.post('/api/verify_solution', json={'seq_id': 'S7', 'answer': 'unauthorized_spell'})
        self.assertEqual(r7.status_code, 200)
        d7 = r7.get_json()
        self.assertTrue(d7['success'])
        self.assertEqual(d7['next_sequence'], 'S6')
        self.assertEqual(d7['completed_count'], 3)
        self.assertEqual(d7['redirect'], '/s6/faceless')

        # S6 via Form Data with 'code' and 'seq' alias
        r6 = self.client.post('/api/verify_solution', data={'seq': 'S6', 'code': 'forged_identity'})
        self.assertEqual(r6.status_code, 200)
        d6 = r6.get_json()
        self.assertTrue(d6['success'])
        self.assertEqual(d6['next_sequence'], 'S3')
        self.assertEqual(d6['completed_count'], 4)
        self.assertEqual(d6['redirect'], '/s3/scholar')

        # S3 via JSON with 'solution'
        r3 = self.client.post('/api/verify_solution', json={'sequence': 'S3', 'solution': 'scholar_reading_deep'})
        self.assertEqual(r3.status_code, 200)
        d3 = r3.get_json()
        self.assertTrue(d3['success'])
        self.assertEqual(d3['next_sequence'], 'S0')
        self.assertEqual(d3['completed_count'], 5)
        self.assertEqual(d3['redirect'], '/s0/fool')

        # S0 finale access granted
        r0 = self.client.get('/s0/fool')
        self.assertEqual(r0.status_code, 200)
        self.assertIn('TecFest26{h34rtb34t_h34rtbr34k_4ll_0v3r_g4l4u_p4r4h_b4ng3t}', r0.data.decode())

    def test_02_interleaved_routes_progression(self):
        """Verify seamless interoperability between /complete/<seq_id> and /api/verify_solution."""
        # S9 via /complete/S9
        r9 = self.client.post('/complete/S9', json={'answer': 'seer_sees_all'})
        self.assertTrue(r9.get_json()['success'])

        # S8 via /api/verify_solution
        r8 = self.client.post('/api/verify_solution', json={'sequence': 'S8', 'token': 'laughing_error_s8'})
        self.assertTrue(r8.get_json()['success'])

        # S7 via /complete/S7
        r7 = self.client.post('/complete/S7', json={'token': 'unauthorized_spell'})
        self.assertTrue(r7.get_json()['success'])

        # S6 via /api/verify_solution (Form)
        r6 = self.client.post('/api/verify_solution', data={'sequence': 'S6', 'solution': 'forged_identity'})
        self.assertTrue(r6.get_json()['success'])

        # S3 via /complete/S3
        r3 = self.client.post('/complete/S3', json={'code': 'scholar_reading_deep'})
        self.assertTrue(r3.get_json()['success'])

        # Finale verification
        r0 = self.client.get('/s0/fool')
        self.assertEqual(r0.status_code, 200)
        self.assertIn('TecFest26{h34rtb34t_h34rtbr34k_4ll_0v3r_g4l4u_p4r4h_b4ng3t}', r0.data.decode())

    def test_03_verification_api_defensive_rejections(self):
        """Stress-test edge cases and adversarial inputs against /api/verify_solution."""
        # 1. Missing sequence identifier
        r = self.client.post('/api/verify_solution', json={'token': 'seer_sees_all'})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.get_json()['success'])
        self.assertIn('Missing sequence identifier', r.get_json()['message'])

        # 2. Integer sequence identifier
        r = self.client.post('/api/verify_solution', json={'sequence': 9, 'token': 'seer_sees_all'})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.get_json()['success'])

        # 3. None sequence identifier
        r = self.client.post('/api/verify_solution', json={'sequence': None, 'token': 'seer_sees_all'})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.get_json()['success'])

        # 4. Out of sequence submission
        r = self.client.post('/api/verify_solution', json={'sequence': 'S8', 'token': 'laughing_error_s8'})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.get_json()['success'])
        self.assertIn('prior Sequences first', r.get_json()['message'])

        # 5. Invalid / deleted sequences
        for invalid_seq in ['S1', 'S2', 'S4', 'S5', 'S0', 'S10', 'FLAG']:
            r = self.client.post('/api/verify_solution', json={'sequence': invalid_seq, 'token': 'anything'})
            self.assertEqual(r.status_code, 200)
            self.assertFalse(r.get_json()['success'])
            self.assertIn('Invalid sequence identifier', r.get_json()['message'])

        # 6. Oversized token DoS prevention (> 256 chars)
        r = self.client.post('/api/verify_solution', json={'sequence': 'S9', 'token': 'A' * 10000})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.get_json()['success'])

        # 7. Non-dict root payloads (scalar, list)
        for non_dict in [[1, 2, 3], 'raw_string', 12345, True]:
            r = self.client.post('/api/verify_solution', json=non_dict)
            self.assertEqual(r.status_code, 200)
            self.assertFalse(r.get_json()['success'])

        # 8. HTTP Method guards
        for method in ['get', 'put', 'delete', 'patch']:
            r = getattr(self.client, method)('/api/verify_solution')
            self.assertEqual(r.status_code, 405)
            r2 = getattr(self.client, method)('/complete/S9')
            self.assertEqual(r2.status_code, 405)

    # =========================================================================
    # SECTION 2: S3 Scholar LFI Containment and Directory Traversal Attacks
    # =========================================================================

    def test_04_lfi_containment_adversarial_traversal(self):
        """Adversarial stress testing of path traversal containment at /s3/scholar/view."""
        # Advance session to S3
        self.client.post('/complete/S9', json={'answer': 'seer_sees_all'})
        self.client.post('/complete/S8', json={'answer': 'laughing_error_s8'})
        self.client.post('/complete/S7', json={'answer': 'unauthorized_spell'})
        self.client.post('/complete/S6', json={'answer': 'forged_identity'})

        # Legitimate traversal to Beyonder secret
        r_valid = self.client.get('/s3/scholar/view', query_string={'scroll': '../secrets/lfi_token.txt'})
        self.assertEqual(r_valid.status_code, 200)
        self.assertIn('scholar_reading_deep', r_valid.get_json().get('content', ''))

        # Traversal escapes: paths that escape the /opt/ctf/ container boundary
        forbidden_escapes = [
            '../../../../etc/passwd',
            '../../../../etc/shadow',
            '../../../../proc/self/environ',
            '../../../../proc/1/cmdline',
            '../../../../Windows/System32/drivers/etc/hosts',
            '../../../../Windows/win.ini',
            '../../app.py',
            '../../requirements.txt',
            '..',
            '../',
            '../../',
            '../../../',
            '../secrets/../../etc/passwd',
            'C:\\Windows\\win.ini',
            'C:/Windows/win.ini',
            '..\\..\\app.py',
        ]
        for escape in forbidden_escapes:
            r = self.client.get('/s3/scholar/view', query_string={'scroll': escape})
            d = r.get_json()
            self.assertEqual(d.get('error'), 'Access denied', f"Path '{escape}' must be strictly denied")

        # Paths that stay inside /opt/ctf/ but do not exist (e.g. non-traversal names or literal url-encoded names in test_client)
        non_existent_inside = [
            '/etc/passwd',  # evaluates to /opt/ctf/sequence_data/etc/passwd
            'nonexistent.txt',
            '../secrets/missing.txt',
            '..%2f..%2fapp.py',
            '..%252f..%252fapp.py',
        ]
        for path in non_existent_inside:
            r = self.client.get('/s3/scholar/view', query_string={'scroll': path})
            d = r.get_json()
            self.assertIn('Scroll not found', d.get('error', ''), f"Missing path '{path}' should return 'Scroll not found'")

        # Null-byte injection attempt: /s3/scholar/view?scroll=../secrets/lfi_token.txt%00.txt
        r_null = self.client.get('/s3/scholar/view', query_string={'scroll': '../secrets/lfi_token.txt\x00.txt'})
        d_null = r_null.get_json()
        self.assertTrue('error' in d_null, "Null-byte string must return an error and not leak content")
        self.assertNotIn('scholar_reading_deep', str(d_null))

        # Directory read attempt: /s3/scholar/view?scroll=../secrets
        r_dir = self.client.get('/s3/scholar/view', query_string={'scroll': '../secrets'})
        d_dir = r_dir.get_json()
        self.assertTrue('error' in d_dir, "Reading a directory path must handle exception cleanly")

        # Non-existent file inside container: /s3/scholar/view?scroll=../secrets/missing.txt
        r_missing = self.client.get('/s3/scholar/view', query_string={'scroll': '../secrets/missing.txt'})
        d_missing = r_missing.get_json()
        self.assertIn('Scroll not found', d_missing.get('error', ''))

    def test_05_unauthenticated_s3_rejection(self):
        """Verify unauthenticated access to /s3/scholar/view without completing S6 redirects to '/'."""
        # Fresh unauthenticated client
        r = self.client.get('/s3/scholar/view', query_string={'scroll': '../secrets/lfi_token.txt'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers.get('Location'), '/')

    # =========================================================================
    # SECTION 3: Deleted Routes Strict 404 Verification Across HTTP Methods
    # =========================================================================

    def test_06_deleted_routes_all_methods_return_404(self):
        """Verify deleted sequences S1, S2, S4, S5 return HTTP 404 for all standard HTTP methods."""
        deleted_routes = [
            # S5 Marionettist
            '/s5/marionettist',
            '/s5/marionettist/fetch',
            '/s5/marionettist/control',
            # S4 Sorcerer
            '/s4/sorcerer',
            '/s4/sorcerer/graphql',
            '/s4/sorcerer/api',
            # S2 Miracle
            '/s2/miracle',
            '/s2/miracle/init',
            '/s2/miracle/api/shop',
            '/s2/miracle/api/buy',
            # S1 Attendant
            '/s1/attendant',
            '/s1/attendant/notice',
            '/s1/attendant/oracle',
            '/s1/attendant/verify_mac',
            '/s1/attendant/get_flag',
        ]
        http_methods = ['get', 'post', 'put', 'delete', 'options']

        for route in deleted_routes:
            for method in http_methods:
                client_fn = getattr(self.client, method)
                resp = client_fn(route)
                self.assertEqual(resp.status_code, 404,
                                 f"{method.upper()} {route} returned status {resp.status_code}, expected 404")

    # =========================================================================
    # SECTION 4: Database Connection Pool Robustness Under SQLi Error Stress
    # =========================================================================

    def test_07_s8_connection_cleanup_under_intense_error_fuzzing(self):
        """Stress-test /s8/clown/joke with 50 malformed SQL inputs to guarantee no connection leaks."""
        self.client.post('/complete/S9', json={'answer': 'seer_sees_all'})

        fuzz_payloads = [
            "'", "''", "'''", "\"", "\\", ";", "--", "/*",
            "' OR 1=1; --", "' UNION SELECT 1, 2, 3, 4, 5 --",
            "admin'--", "1' AND (SELECT 1 FROM non_existent_table) --",
            "'; DROP TABLE jokes; --", "x' UNION SELECT 1 --"
        ] * 4  # 56 requests

        for payload in fuzz_payloads:
            r = self.client.post('/s8/clown/joke', json={'joke': payload})
            # Either 500 (schema disclosure on syntax error) or 200 (executed query)
            self.assertIn(r.status_code, [200, 500])

        with app.app.app_context():
            checked_out = app.db.engine.pool.checkedout()
            self.assertEqual(checked_out, 0, f"Expected 0 checked-out connections in pool, found {checked_out}")

    # =========================================================================
    # SECTION 5: Reference Solver Determinism (Multiple Consecutive Runs)
    # =========================================================================

    def test_08_solver_determinism_consecutive_runs(self):
        """Run reference solver multiple times against live server instance to ensure 100% determinism."""
        from werkzeug.serving import make_server
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'solver'))
        import solve as solver

        port = 5066
        srv = make_server('127.0.0.1', port, app.app)
        t = threading.Thread(target=srv.serve_forever)
        t.daemon = True
        t.start()
        time.sleep(1)

        expected_flag = 'TecFest26{h34rtb34t_h34rtbr34k_4ll_0v3r_g4l4u_p4r4h_b4ng3t}'

        try:
            for iteration in range(1, 11):
                flag = solver.solve(f'http://127.0.0.1:{port}')
                self.assertEqual(flag, expected_flag, f"Iteration {iteration} solver returned unexpected flag: {flag}")

            # Also test solver with trailing slash in URL
            flag_slash = solver.solve(f'http://127.0.0.1:{port}/')
            self.assertEqual(flag_slash, expected_flag)
        finally:
            srv.shutdown()

    # =========================================================================
    # SECTION 6: Antislop & Workspace Hygiene (0 Em Dashes)
    # =========================================================================

    def test_09_workspace_em_dash_hygiene(self):
        """Verify zero em dashes exist across Web Exploit/mr-fool implementation files."""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
        em_dash_char = chr(8212)
        violations = []
        for root, dirs, files in os.walk(base_dir):
            for f in files:
                if f.startswith('test_challenger_round2'):
                    continue
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as fh:
                        content = fh.read()
                        if em_dash_char in content:
                            violations.append(filepath)
                except Exception:
                    pass

        self.assertEqual(len(violations), 0, f"Found em dash violations in: {violations}")


if __name__ == '__main__':
    unittest.main()
