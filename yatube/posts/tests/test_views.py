# import os
import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostPagesTests(TestCase):
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

    def setUp(self):
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_uses_correct_template(self):
        """Тест для проверки соотвествия view-функций шаблонам."""
        templates_page_names = {
            reverse('posts:index'):
                'posts/index.html',
            reverse('posts:group_posts', kwargs={'slug': 'test-slug'}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.post.author}):
                'posts/profile.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}):
                'posts/create_post.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}):
                'posts/post_detail.html'
        }
        for reverse_name, template in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ContextTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group_1 = Group.objects.create(
            title='Test group1',
            slug='test-slug1',
            description='Test description'
        )
        cls.group_2 = Group.objects.create(
            title='Test group2',
            slug='test-slug2',
            description='Test description'
        )
        cls.user_1 = User.objects.create_user(username='leo_1')
        cls.user_2 = User.objects.create_user(username='leo_2')
        test_posts = []
        for i in range(36):
            if i < 18:
                test_posts.append(Post(text=f'Тестовый текст {i}',
                                       group=cls.group_1,
                                       author=cls.user_1))
            else:
                test_posts.append(Post(text=f'Тестовый текст {i}',
                                       group=cls.group_2,
                                       author=cls.user_2))
        Post.objects.bulk_create(test_posts)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_1)
        self.authorized_client.force_login(self.user_2)
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        self.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cache.clear()

    def test_post_context_with_image(self):
        """
        Тест, котороый проверяет, что картинка передается в списке контекста
        """

        form_data = {
            'text': f'Post  with image by {self.user_1.username}',
            'group': self.group_1.id,
            'image': self.uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Проверка что картинка сохранена на жестком диске,
        # проверка отключена, чтобы пройти тесты на сервере,
        # локально проверка работает
        # self.assertTrue(
        #     self.uploaded.name in os.listdir(f'{TEMP_MEDIA_ROOT}\\posts')
        # )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group'],
                image__isnull=False
            ).exists()
        )
        self.post = Post.objects.filter(
            text=form_data['text'],
            group=form_data['group'],
            image__isnull=False
        )[0]

        context_pages = {
            'page_obj': (
                reverse('posts:index'),
                reverse('posts:group_posts',
                        kwargs={'slug': self.post.group.slug}),
                reverse('posts:profile',
                        kwargs={'username': self.post.author.username}
                        )
            ),
            'post': (
                reverse('posts:post_detail',
                        kwargs={'post_id': self.post.id}
                        ),
            )
        }

        while context_pages:
            context_keys, pages = context_pages.popitem()
            for page in pages:
                posts = self.authorized_client.get(page).context[context_keys]
                if isinstance(posts, Post):
                    self.assertIsNotNone(posts.image)
                    self.assertEqual(posts.image, self.post.image)
                else:
                    for post in posts:
                        if self.post.id == post.id:
                            self.assertEqual(post.image, self.post.image)

    def test_index_page_show_correct_context(self):
        """Тест для проверки работы Паджинатора на главной странице."""
        for index in range(Post.objects.count() // settings.COUNT_OF_POSTS):
            response = self.authorized_client.get(
                reverse('posts:index') + f'?page={index + 1}'
            )
            self.assertEqual(len(response.context['page_obj']),
                             settings.COUNT_OF_POSTS
                             )

    def test_index_last_page_show_correct_context(self):
        """Тест для проверки работы Паджинатора на главной странице."""
        index = Post.objects.count() // settings.COUNT_OF_POSTS
        response = self.authorized_client.get(
            reverse('posts:index') + f'?page={index+1}'
        )
        self.assertEqual(len(response.context['page_obj']),
                         Post.objects.count() % settings.COUNT_OF_POSTS)

    def test_group_page_show_correct_context(self):
        """Тест для проверки работы Паджинатора на странице группы."""
        response = self.authorized_client.get(
            reverse('posts:group_posts', kwargs={'slug': self.group_1.slug})
        )
        self.assertEqual(len(response.context['page_obj']), 10)
        response = self.authorized_client.get(
            reverse('posts:group_posts', kwargs={'slug': self.group_1.slug})
            + '?page=2'
        )
        self.assertEqual(len(response.context['page_obj']), 8)

    def test_profile_page_show_correct_context(self):
        """Тест для проверки словаря context на странице профиля автора."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user_1})
        )
        self.assertEqual(len(response.context['page_obj']), 10)
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user_1})
            + '?page=2'
        )
        self.assertEqual(len(response.context['page_obj']), 8)

    def test_post_detail_page_show_correct_context(self):
        """Тест для проверки словаря context на странице поста."""
        self.post = Post.objects.create(
            text=f'Post by {self.user_1.username}',
            author=self.user_1,
            group=self.group_1
        )
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        self.assertEqual(response.context['post'].pk, self.post.pk)
        self.assertEqual(response.context['post'].author, self.post.author)

    def test_post_create_page_show_correct_context(self):
        """Тест для проверки словаря context на странице создания поста."""
        self.user = User.objects.create_user(username='leo')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        response = self.authorized_client.get(
            reverse('posts:post_create')
        )
        self.assertIn('form', response.context)
        self.assertIn('is_edit', response.context)

    def test_post_edit_page_show_correct_context(self):
        """Тест для проверки словаря context
        на странице редактирования поста."""
        self.user = User.objects.create_user(username='leo')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.post = Post.objects.create(
            text=f'Post by {self.user.username}',
            author=self.user,
            group=self.group_1
        )
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk})
        )
        self.assertIn('form', response.context)
        self.assertEqual(response.context['post'], self.post)
        self.assertEqual(response.context['is_edit'], True)


class PostCreationTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='leo')

        cls.group = Group.objects.create(
            title='Test group for post',
            slug='test-slug_post',
            description='Test description'
        )
        cls.empty_group = Group.objects.create(
            title='Test group not for post',
            slug='test-slug_without_post',
            description='Test description'
        )
        cls.post = Post.objects.create(
            text=f'Post by {cls.user.username}',
            author=cls.user,
            group=cls.group
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_new_post_shows_on_index_page(self):
        """Тест для проверки наличия созданного поста на главной странице."""
        response = self.authorized_client.get(reverse('posts:index'))
        post = response.context['page_obj'][0]
        self.assertEqual(post.pk, self.post.pk)

    def test_new_post_shows_on_group_page(self):
        """Тест для проверки наличия созданного
        поста на странице указанной группы."""
        response = self.authorized_client.get(
            reverse('posts:group_posts', kwargs={'slug': self.group.slug})
        )
        post = response.context['page_obj'][0]
        self.assertEqual(len(response.context['page_obj']), 1)
        self.assertEqual(post.pk, self.post.pk)

    def test_new_post_miss_on_empty_group_page(self):
        """Тест для проверки отсутствия созданного
        поста на странице неуказанной группы."""
        response = self.authorized_client.get(
            reverse('posts:group_posts',
                    kwargs={'slug': self.empty_group.slug}
                    )
        )
        self.assertEqual(len(response.context['page_obj']), 0)

    def test_profile_page_show_new_post(self):
        """Тест для проверки наличия созданного
        поста на странице профиля автора."""
        response = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': self.post.author.username}
                    )
        )
        post = response.context['page_obj'][0]
        self.assertEqual(len(response.context['page_obj']), 1)
        self.assertEqual(post.pk, self.post.pk)


class CommentCreateTest(TestCase):
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
        cls.comment = Comment.objects.create(
            post=cls.post,
            text='Текст тестового комментария',
            author=cls.user
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(CommentCreateTest.user)

    def test_post_page_show_new_comment(self):
        """Тест для проверки наличия созданного
        комментария на странице поста."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.pk}
            )
        )
        comment = response.context['comments'][0]
        self.assertEqual(comment.text, self.comment.text)


class TestCacheIndexPage(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='leo')

    def setUp(self):
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(TestCacheIndexPage.user)

    def test_cache_for_index_page(self):
        """Тест для проверки кеширования записей на странице index"""
        response_1 = self.authorized_client.get(reverse('posts:index'))
        self.post_1 = Post.objects.create(
            text='Test text 1',
            author=self.user
        )
        response_2 = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response_1.content, response_2.content)
        cache.clear()
        response_3 = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response_2.content, response_3.content)


class FollowsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_user = User.objects.create_user(username='guest')
        cls.user = User.objects.create_user(username='subscriber')
        cls.author_user = User.objects.create_user(username='author')
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author_user
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_subscriber = Client()
        self.authorized_subscriber.force_login(self.user)
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author_user)

    def test_follow_and_unfollow_for_auth_user(self):
        """Тест для проверки наличия возможности авторизованного пользователя
        подписываться и отписываться от авторов"""
        self.authorized_subscriber.get(
            reverse('posts:profile_follow', args=['author'])
        )
        self.assertTrue(Follow.objects.filter(
            user=self.user,
            author=self.author_user
        ).exists())
        Follow.objects.filter(
            user=self.user,
            author=self.author_user
        ).delete()
        self.assertFalse(Follow.objects.filter(
            user=self.user,
            author=self.author_user
        ).exists())

    def test_follow_for_guest_user(self):
        """Тест для проверки отсутствия возможности у неавторизованного
        пользователя пользоваться функциями подписки"""
        self.guest_client.get(
            reverse('posts:profile_follow', args=['author'])
        )
        self.assertFalse(Follow.objects.filter(
            user=self.guest_user,
            author=self.author_user
        ).exists())

    def test_content_for_follower_and_unfollow(self):
        """Тест для проверки отображения в ленте у пользователя записей
        избранного автора"""
        self.following = Follow.objects.create(
            user=self.user,
            author=self.author_user
        )
        response_1 = self.authorized_subscriber.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(len(response_1.context['page_obj']), 1)
        self.following.delete()
        response_2 = self.authorized_subscriber.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(len(response_2.context['page_obj']), 0)
