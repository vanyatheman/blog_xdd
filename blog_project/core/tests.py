from http import HTTPStatus

from django.test import Client, TestCase


class PostURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_unexisting_page(self):
        """Проверка 404."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_pages_use_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        response = self.guest_client.get('/unexisting_page/')
        template = 'core/404.html'
        self.assertTemplateUsed(response, template)
