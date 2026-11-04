from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace
from django.test import TestCase
from django.test import override_settings
from django.core import mail
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from rest_framework import status
from bookings.models import SaunaBooking
from payments.models import Payments
from payments.helper import send_booking_confirmation_email


class PaymentsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.booking = SaunaBooking.objects.create(
            sauna_type='private',
            booking_date='2026-10-15',
            booking_time='10:00:00',
            time_slot='3_hours',
            capacity=2,
            name='John Doe',
            email='john@example.com',
            phone='+1234567890',
            total_price=150.00
        )

    @patch('djstripe.models.PaymentIntent._api_create')
    @patch('djstripe.models.PaymentIntent.sync_from_stripe_data')
    def test_create_payment_intent_success(self, mock_sync, mock_api_create):
        mock_intent = MagicMock()
        mock_intent.id = 'pi_test_12345'
        mock_intent.client_secret = 'pi_test_12345_secret_abc'
        mock_api_create.return_value = mock_intent
        mock_sync.return_value = mock_intent

        url = '/api/payments/create-intent/'
        data = {'booking_id': self.booking.booking_id, 'currency': 'eur'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['client_secret'], 'pi_test_12345_secret_abc')
        self.assertEqual(response.data['payment_intent_id'], 'pi_test_12345')

        # Check DB Payment record
        payment = Payments.objects.get(booking_id=self.booking.booking_id)
        self.assertEqual(payment.stripe_payment_intent_id, 'pi_test_12345')
        self.assertEqual(payment.payment_status, 'pending')

    def test_webhook_payment_succeeded(self):
        # Create payment record
        payment = Payments.objects.create(
            booking_id=self.booking.booking_id,
            booking_type='sauna',
            amount=150.00,
            currency='eur',
            payment_status='pending',
            stripe_payment_intent_id='pi_test_12345'
        )

        url = '/api/payments/webhook/'
        payload = {
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'pi_test_12345',
                    'metadata': {
                        'booking_id': self.booking.booking_id
                    }
                }
            }
        }

        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(payment.payment_status, 'paid')
        self.assertEqual(self.booking.payment_status, 'paid')
        self.assertEqual(self.booking.status, 'confirmed')


class ActivityConfirmationEmailTests(TestCase):
    def test_activity_confirmation_email_uses_recipient_language(self):
        localized_content = {
            'nl': {
                'subject': 'Wat leuk dat je erbij bent!',
                'activity': 'Yoga NL',
                'booking_number': 'Reserveringsnummer:',
                'total_paid': 'Totaal betaald:',
                'plain_total_paid': 'Totaal betaald: € 45.00',
            },
            'en': {
                'subject': 'How wonderful to have you joining us!',
                'activity': 'Yoga EN',
                'booking_number': 'Booking number:',
                'total_paid': 'Total paid:',
                'plain_total_paid': 'Total paid: € 45.00',
            },
            'de': {
                'subject': 'Wie schön, dass du dabei bist!',
                'activity': 'Yoga DE',
                'booking_number': 'Reservierungsnummer:',
                'total_paid': 'Gesamtbetrag bezahlt:',
                'plain_total_paid': 'Gesamtbetrag bezahlt: € 45.00',
            },
        }

        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            with patch('notifications.views.notify_user'), patch('notifications.views.notify_admins'):
                for lang, expected in localized_content.items():
                    booking = SimpleNamespace(
                        booking_id='ACT-0001',
                        email=f'{lang}@example.com',
                        name='Alex Example',
                        user=SimpleNamespace(language=lang),
                        activity=SimpleNamespace(
                            title='Yoga',
                            title_nl='Yoga NL',
                            title_en='Yoga EN',
                            title_de='Yoga DE',
                            date=date(2026, 11, 4),
                            open_time=time(10, 0),
                            close_time=time(11, 0),
                        ),
                        capacity=2,
                        total_price=Decimal('45.00'),
                        payment_status='paid',
                        status='confirmed',
                    )

                    result = send_booking_confirmation_email(booking)

                    self.assertTrue(result['status'])
                    sent_email = mail.outbox[-1]
                    html_message = sent_email.alternatives[0][0]
                    self.assertIn(expected['subject'], sent_email.subject)
                    self.assertIn(expected['activity'], html_message)
                    self.assertIn(expected['booking_number'], html_message)
                    self.assertIn(expected['total_paid'], html_message)
                    self.assertIn('€ 45.00', html_message)
                    self.assertIn(expected['plain_total_paid'], sent_email.body)
