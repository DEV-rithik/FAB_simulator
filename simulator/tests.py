"""
Tests for critical application flows:
- Authentication (register, login, logout)
- Simulation run creation and history visibility
- Export endpoints (CSV and PDF)
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from .models import SimulationRun


class AuthTestCase(TestCase):
    """Test authentication flows."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', email='test@example.com', password='testpass123'
        )

    def test_register_new_user(self):
        response = self.client.post(reverse('auth:register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpass123',
            'password2': 'newpass123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_duplicate_username(self):
        response = self.client.post(reverse('auth:register'), {
            'username': 'testuser',
            'email': 'other@example.com',
            'password': 'pass123',
            'password2': 'pass123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Username already taken')

    def test_register_password_mismatch(self):
        response = self.client.post(reverse('auth:register'), {
            'username': 'anotheruser',
            'email': 'another@example.com',
            'password': 'pass123',
            'password2': 'different',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Passwords do not match')

    def test_login_valid(self):
        response = self.client.post(reverse('auth:login'), {
            'username': 'testuser',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)

    def test_login_invalid(self):
        response = self.client.post(reverse('auth:login'), {
            'username': 'testuser',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')

    def test_logout(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('auth:logout'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('simulator:dashboard'))
        self.assertRedirects(response, '/auth/login/?next=/dashboard/')


class SimulationRunTestCase(TestCase):
    """Test simulation run creation and per-user isolation."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='simuser', email='sim@example.com', password='simpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser', email='other@example.com', password='otherpass123'
        )
        self.client.login(username='simuser', password='simpass123')

    def _create_completed_run(self, user=None):
        """Helper to create a pre-completed run without running the full simulator."""
        if user is None:
            user = self.user
        run = SimulationRun.objects.create(
            user=user,
            status='completed',
            input_payload={
                'wafer_diameter_mm': 300,
                'die_size_mm': 5.0,
                'mc_runs': 100,
            },
            mean_yield=74.3,
            std_yield=1.2,
            best_yield=78.1,
            worst_yield=70.0,
            total_dies=2148,
            result_payload={
                'pareto': [
                    ['Threshold voltage (Vth0)', 5.2],
                    ['Gate oxide thickness (Tox)', 3.1],
                    ['Carrier mobility (u0)', 1.8],
                ],
                'yield_sample': [74.3, 75.1, 73.8],
            },
        )
        return run

    def test_history_shows_only_own_runs(self):
        self._create_completed_run(user=self.user)
        other_run = self._create_completed_run(user=self.other_user)

        response = self.client.get(reverse('simulator:history'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(f'#PX-{SimulationRun.objects.filter(user=self.user).first().pk}', content)
        # Other user's run should not appear
        self.assertNotIn(f'#PX-{other_run.pk}', content) if \
            SimulationRun.objects.filter(user=self.user).count() == 1 else None

    def test_results_page_requires_own_run(self):
        """Users cannot view other users' run results."""
        other_run = self._create_completed_run(user=self.other_user)
        response = self.client.get(reverse('simulator:results', kwargs={'pk': other_run.pk}))
        self.assertEqual(response.status_code, 404)

    def test_results_page_own_run(self):
        run = self._create_completed_run()
        response = self.client.get(reverse('simulator:results', kwargs={'pk': run.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '74.3')

    def test_dashboard_loads(self):
        response = self.client.get(reverse('simulator:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Yield Intelligence')

    def test_simulate_config_get(self):
        response = self.client.get(reverse('simulator:simulate'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Simulation Configuration')


class ExportTestCase(TestCase):
    """Test CSV and PDF export endpoints."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='exportuser', email='export@example.com', password='exportpass123'
        )
        self.client.login(username='exportuser', password='exportpass123')
        self.run = SimulationRun.objects.create(
            user=self.user,
            status='completed',
            input_payload={'wafer_diameter_mm': 300, 'die_size_mm': 5.0, 'mc_runs': 100},
            mean_yield=74.3,
            std_yield=1.2,
            best_yield=78.1,
            worst_yield=70.0,
            total_dies=2148,
            result_payload={
                'pareto': [['Threshold voltage (Vth0)', 5.2]],
                'yield_sample': [74.3, 75.1],
            },
        )

    def test_csv_export_success(self):
        response = self.client.get(reverse('simulator:export_csv', kwargs={'pk': self.run.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode()
        self.assertIn('74.30', content)
        self.assertIn('Mean Yield', content)

    def test_pdf_export_success(self):
        response = self.client.get(reverse('simulator:export_pdf', kwargs={'pk': self.run.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        # PDF starts with %PDF header
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_export_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('simulator:export_csv', kwargs={'pk': self.run.pk}))
        self.assertEqual(response.status_code, 302)

    def test_export_own_run_only(self):
        other_user = User.objects.create_user('eo', 'eo@test.com', 'pass')
        other_run = SimulationRun.objects.create(
            user=other_user, status='completed',
            input_payload={}, result_payload={},
        )
        response = self.client.get(reverse('simulator:export_csv', kwargs={'pk': other_run.pk}))
        self.assertEqual(response.status_code, 404)

