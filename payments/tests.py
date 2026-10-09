from django.test import TestCase
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from rest_framework import status
from bookings.models import SaunaBooking
from payments.models import Payments


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
