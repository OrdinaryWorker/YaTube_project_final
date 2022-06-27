from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..forms import CommentForm, PostForm
from ..models import Comment, Group, Post

User = get_user_model()


class PostCreateFormTest(TestCase):
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
            text=f'Post by {cls.user.username}',
            author=cls.user,
            group=cls.group
        )
        cls.form = PostForm()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostCreateFormTest.user)

    def test_create_post_form(self):
        """Тест для проверки валидности формы поста при создании поста."""
        posts_count = Post.objects.count()
        form_data = {
            'text': self.post.text,
            'group': self.post.group.pk
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.post.author})
        )

        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group']
            ).exists()
        )

    def test_edit_post_form(self):
        """Тест для проверки валидности формы
         поста при редактировании поста."""
        self.new_group = Group.objects.create(
            title='Test group 2',
            slug='test-slug_new',
            description='Test description'
        )
        self.post.group = self.new_group
        form_data = {
            'text': 'modified text',
            'group': self.post.group.pk
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group']
            ).exists()
        )


class CommentCreateFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='leo')
        cls.group = Group.objects.create(
            title='Test group',
            slug='test-slug',
            description='Test description'
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(CommentCreateFormTest.user)
        self.post = Post.objects.create(
            text=f'Post by {self.user.username}',
            author=self.user,
            group=self.group
        )
        self.form = CommentForm()

    def test_authorized_client_create_comment_form(self):
        """Тест для проверки валидности формы поста при создании поста."""
        comments_init_count = Comment.objects.filter(post=self.post).count()
        form_data = {
            'text': 'Тестовый комментарий'
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        comments_update_count = Comment.objects.filter(post=self.post).count()
        self.assertEqual(comments_update_count, comments_init_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                text=form_data['text']
            ).exists()
        )

    def test_guest_client_create_comment_form(self):
        """Тест для проверки валидности формы поста при создании поста."""
        comments_init_count = Comment.objects.filter(post=self.post).count()
        form_data = {
            'text': 'Тестовый комментарий 2'
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            '/auth/login/?next=%2Fposts%2F1%2Fcomment%2F'
        )
        comments_update_count = Comment.objects.filter(post=self.post).count()
        self.assertNotEqual(comments_update_count, comments_init_count + 1)
        self.assertFalse(
            Comment.objects.filter(
                text=form_data['text']
            ).exists()
        )
