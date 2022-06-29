from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='leo')
        cls.group = Group.objects.create(
            title='Test group',
            slug='test-slug',
            description='Test description'
        )
        cls.post = Post.objects.create(
            text='Test text',
            author=cls.user,
            group=cls.group
        )
        cls.url_names = {
            '': {
                'url_exception':
                    'URL Тест для главной страницы не пройден',
                'template_exception':
                    ' Тест проверки шаблона для главной страницы не пройден',
                'template_address': 'posts/index.html'
            },
            '/group/test-slug/': {
                'url_exception':
                    'URL Тест для страницы группы не пройден',
                'template_exception':
                    'Тест проверки шаблона для страницы группы не пройден',
                'template_address': 'posts/group_list.html'

            },
            '/profile/leo/': {
                'url_exception': 'URL Тест для страницы профиля не пройден',
                'template_exception':
                    'Тест проверки шаблона профиля не пройден',
                'template_address': 'posts/profile.html'
            },
            f'/posts/{cls.post.pk}/': {
                'url_exception': 'URL Тест для страницы поста не пройден',
                'template_exception':
                    'Тест проверки шаблона страницы поста не пройден',
                'template_address': 'posts/post_detail.html'
            },
            f'/posts/{cls.post.pk}/edit/': {
                'url_exception':
                    'URL Тест для страницы редактирования поста не пройден',
                'template_exception':
                    'Тест проверки шаблона для страницы редактирования поста '
                    'не пройден',
                'template_address': 'posts/create_post.html'
            },
            '/create/': {
                'url_exception':
                    'URL Тест для страницы создания поста не пройден',
                'template_exception':
                    'Тест проверки шаблона для страницы создания поста '
                    'не пройден',
                'template_address': 'posts/create_post.html'
            }
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostURLTests.user)
        cache.clear()

    def test_urls_exists_at_desired_location_for_authorized_client(self):
        """Тест URL страниц для авторизованного пользователя"""
        for address, test_case in self.url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code,
                                 HTTPStatus.OK,
                                 test_case['url_exception']
                                 )

    def test_urls_exists_at_desired_location_for_unauthorized_client(self):
        """Тест URL страниц для неавторизованного пользователя"""
        for address, test_case in self.url_names.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                if 'edit' in address:
                    self.assertEqual(self.user.username,
                                     self.post.author.username,
                                     'Тест на авторство поста не пройден'
                                     )
                    self.assertEqual(response.status_code,
                                     HTTPStatus.FOUND,
                                     test_case['url_exception'])
                elif 'create' in address:
                    self.assertEqual(response.status_code,
                                     HTTPStatus.FOUND,
                                     test_case['url_exception'])
                else:
                    self.assertEqual(response.status_code,
                                     HTTPStatus.OK,
                                     test_case['url_exception'])

    def test_urls_uses_correct_template(self):
        """Тест для проверки соотвествия URL-адресов шаблонам."""
        for address, item in self.url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response,
                                        item['template_address'],
                                        item['template_exception']
                                        )
