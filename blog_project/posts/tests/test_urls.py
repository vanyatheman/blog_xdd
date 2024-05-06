from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Comment, Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованый клиент
        self.author_client = Client()
        self.author_client.force_login(PostURLTests.author)
        cache.clear()

    # Проверяем общедоступные страницы

    def test_pages_exist_at_desired_locations(self):
        """Страницы доступны по указанным адресам."""
        group_test = PostURLTests.group
        post_test = PostURLTests.post
        template_page_names = [
            reverse('posts:index'),
            reverse('posts:group_posts', kwargs={'slug': group_test.slug}),
            reverse('posts:profile', kwargs={'username': post_test.author}),
            reverse('posts:post_detail', kwargs={'post_id': post_test.id}),
            reverse('posts:post_create'),
            reverse('posts:post_edit', kwargs={'post_id': post_test.id})
        ]

        for address in template_page_names:
            if (address == reverse('posts:post_create')
                    or reverse(
                        'posts:post_edit',
                        kwargs={'post_id': post_test.id})):
                with self.subTest(address=address):
                    response = self.author_client.get(address)
                    self.assertEqual(response.status_code, HTTPStatus.OK)
            else:
                with self.subTest(address=address):
                    response = self.guest_client.get(address)
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    # redirects
    def test_create_url_redirect_anonymous_on_login(self):
        """Страница /create/ перенаправит анонимного пользователя
        на страницу логина.
        """
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(
            response, '/auth/login/?next=/create/')

    def test_edit_url_redirect_users_on_post(self):
        """Страница /posts/<post_id>/edit перенаправит не автора поста
        на страницу поста.
        """
        post = PostURLTests.post
        response = self.guest_client.get(
            f'/posts/{post.id}/edit/', follow=True
        )
        self.assertRedirects(
            response, f'/posts/{post.id}/')

    def test_comment_url_redirect_anonymous_on_login(self):
        """Страница /comment/ перенаправит анонимного пользователя
        на страницу логина.
        """
        comments_nbr_before_creation = Comment.objects.count()
        post_test = PostURLTests.post
        comment_data = {'text': 'Текст комментария'}
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': post_test.id}),
            data=comment_data,
        )
        response = self.guest_client.get(
            reverse('posts:add_comment', kwargs={'post_id': post_test.id})
        )
        comments_nbr_after_creation = Comment.objects.count()

        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{post_test.id}/comment/'
        )
        self.assertEqual(
            comments_nbr_before_creation,
            comments_nbr_after_creation
        )

    def test_pages_use_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        group_test = PostURLTests.group
        post_test = PostURLTests.post
        template_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_posts', kwargs={'slug': group_test.slug}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': post_test.author}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': post_test.id}):
                'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': post_test.id}):
                'posts/create_post.html',
            # reverse():'core/404.html'
        }

        for address, template in template_page_names.items():
            with self.subTest(address=address):
                response = self.author_client.get(address)
                self.assertTemplateUsed(response, template)
