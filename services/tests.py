from django.test import TestCase
from rest_framework.test import APIRequestFactory
from .models import Packages
from .views import GetSlotView


class PackageSlotTests(TestCase):
	def setUp(self):
		self.factory = APIRequestFactory()

	def get_package_slots(self, package, **query_params):
		request = self.factory.get('/services/slots/', {
			'type': 'package',
			'package_id': package.id,
			'date': '2099-01-15',
			**query_params,
		})
		return GetSlotView.as_view()(request)

	def test_package_slots_only_include_configured_services(self):
		package = Packages.objects.create(
			title='Sauna and Lunch',
			description='VIP sauna and lunchroom',
			packages=['private_sauna', 'lunchroom'],
		)

		response = self.get_package_slots(package)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(set(response.data['data']), {'private_sauna', 'lunchroom'})

	def test_package_subtype_not_included_returns_message(self):
		package = Packages.objects.create(
			title='Sauna and Lunch',
			description='VIP sauna and lunchroom',
			packages=['private_sauna', 'lunchroom'],
		)

		response = self.get_package_slots(package, sub_type='saltroom')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['data'], {})
		self.assertIn('not included', response.data['message'])

	def test_empty_package_returns_clear_message(self):
		package = Packages.objects.create(
			title='Empty package',
			description='No services',
			packages=[],
		)

		response = self.get_package_slots(package)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['data'], {})
		self.assertIn('No supported booking services', response.data['message'])

	def test_package_slots_require_package_id_or_subtype(self):
		request = self.factory.get('/services/slots/', {
			'type': 'package',
			'date': '2099-01-15',
		})

		response = GetSlotView.as_view()(request)

		self.assertEqual(response.status_code, 400)
		self.assertEqual(response.data['data'], {})
		self.assertIn('package_id', response.data['message'])
