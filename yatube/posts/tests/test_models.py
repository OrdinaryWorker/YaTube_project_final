from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
        )

    def test_models_have_correct_object_names(self):
        """Тест для проверки наличия у формы указанного метода __str__."""
        post = PostModelTest.post
        group = PostModelTest.group
        self.assertEqual(post.text[:15], str(post),
                         'Тест метода str для post не пройден')
        self.assertEqual(group.title, str(group),
                         'Тест метода str для group не пройден')
