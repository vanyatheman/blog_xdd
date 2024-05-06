import shutil
import tempfile
from http import HTTPStatus

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Follow, Group, Post
from blog_project.settings import POSTS_PER_PAGE

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
User = get_user_model()
NUMBER_OF_POSTS_TEST = 13
TWO_MORE_TEST_POSTS = 2
NUMBER_OF_FOLLOWED_AUTHORS = 2


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.author1 = User.objects.create_user(username='author1')
        cls.user = User.objects.create_user(username='vanyathetester')
        cls.test_image = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='test_image.gif',
            content=cls.test_image,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.special_post = Post.objects.create(
            author=cls.author,
            text='Специальный пост для тестов',
            group=cls.group,
            image=cls.uploaded
        )
        cls.posts = Post.objects.bulk_create([
            Post(
                author=cls.author,
                group=cls.group,
                text=f'Тестовый пост_{i+1}',
            ) for i in range(NUMBER_OF_POSTS_TEST)
        ])

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.author_client_1 = Client()
        self.author_client_1.force_login(self.author1)
        cache.clear()

    def test_pages_use_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        group_test = self.group
        post_test = self.special_post
        author_client_test = self.author_client
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
                'posts/create_post.html'
        }

        for address, template in template_page_names.items():
            if address == f'/posts/{post_test.id}/edit/':
                with self.subTest(address=address):
                    response = author_client_test.get(address)
                    self.assertTemplateUsed(response, template)
            else:
                with self.subTest(address=address):
                    response = self.authorized_client.get(address)
                    self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Главная страница с правильным конекстом"""
        response = self.authorized_client.get(reverse('posts:index'))
        posts = Post.objects.select_related(
            'author').all()[:POSTS_PER_PAGE]

        self.assertIn('page_obj', response.context)

        page_obj = response.context['page_obj']

        for (post, post_db) in zip(page_obj, posts):
            self.assertEqual(post, post_db)

    def test_group_posts_page_show_correct_context(self):
        """Шаблон group_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:group_posts',
                kwargs={'slug': self.group.slug}
                # Наставники сказали обращаться к объектам, созданным в
                # методе класса, как PostURLTests.group,
                # а не через self.
            )
        )
        posts = Post.objects.select_related(
            'author',
            'group'
        ).filter(group=self.group)[:POSTS_PER_PAGE]

        self.assertIn('page_obj', response.context)
        self.assertIn('group', response.context)

        page_obj = response.context['page_obj']

        for (post, post_db) in zip(page_obj, posts):
            self.assertEqual(post, post_db)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': self.author}
            )
        )
        posts = Post.objects.select_related(
            'author',
            'group'
        ).filter(author=self.user)[:POSTS_PER_PAGE]

        self.assertIn('page_obj', response.context)
        self.assertIn('author', response.context)

        page_obj = response.context['page_obj']

        for (post, post_db) in zip(page_obj, posts):
            self.assertEqual(post, post_db)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.special_post.id}
            )
        )
        post = response.context['post']

        self.assertEqual(post, self.special_post)

    def test_post_create_page_show_correct_context(self):
        """Шаблон create сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_create')
        )

        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        is_edit_object = response.context['is_edit']

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

        self.assertEqual(is_edit_object, False)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.author_client.get(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.special_post.id}
            )
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        is_edit_object = response.context['is_edit']
        post_object = response.context['post']

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

        self.assertEqual(is_edit_object, True)
        self.assertEqual(post_object.id, self.special_post.id)

    def test_first_page_contains_ten_records(self):
        list_of_pages = [
            reverse('posts:index'),
            reverse(
                'posts:group_posts',
                kwargs={'slug': self.group.slug}
            ),
            reverse(
                'posts:profile',
                kwargs={'username': self.author}
            ),
        ]
        for _ in list_of_pages:
            response = self.authorized_client.get(_)
            page_obj_object = response.context['page_obj']
            with self.subTest(_=_):
                self.assertEqual(len(page_obj_object), POSTS_PER_PAGE)

    def test_second_page_contains_four_records(self):
        list_of_pages = [
            reverse('posts:index') + '?page=2',
            reverse(
                'posts:group_posts',
                kwargs={'slug': self.group.slug}
            ) + '?page=2',
            reverse(
                'posts:profile',
                kwargs={'username': self.author}
            ) + '?page=2',
        ]
        for _ in list_of_pages:
            response = self.authorized_client.get(_)
            page_obj_object = response.context['page_obj']
            with self.subTest(_=_):
                self.assertEqual(
                    len(page_obj_object),
                    NUMBER_OF_POSTS_TEST - POSTS_PER_PAGE + 1
                )

    def test_pages_show_correct_context_image(self):
        """Index page with correct context."""
        group_test = PostURLTests.group
        post_test = PostURLTests.special_post
        page_names = [
            reverse('posts:index'),
            reverse('posts:group_posts', kwargs={'slug': group_test.slug}),
            reverse('posts:profile', kwargs={'username': post_test.author}),
            reverse('posts:post_detail', kwargs={'post_id': post_test.id})
        ]
        for address in page_names:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                if address == page_names[len(page_names) - 1]:
                    post_from_server = response.context['post']
                else:
                    post_from_server = response.context['posts'].filter(
                        text='Специальный пост для тестов'
                    )[0]

                    self.assertEqual(post_test.image, post_from_server.image)

    def test_cache_index(self):
        '''пост в кеше'''
        post_test = Post.objects.create(
            author=PostURLTests.author,
            text='Специальный пост для тестов',
        )
        response_1 = self.guest_client.get(reverse('posts:index'))
        post_test.delete()
        response_2 = self.guest_client.get(reverse('posts:index'))

        self.assertEqual(response_1.content, response_2.content)

    def test_following(self):
        '''
        Авторизованный пользователь может подписываться на
        других пользователей и удалять их из подписок.
        '''
        response = self.authorized_client.get(reverse(
            'posts:profile_follow', kwargs={'username': PostURLTests.author}
        ))
        response_1 = self.authorized_client.get(reverse(
            'posts:profile_follow', kwargs={'username': PostURLTests.author1}
        ))
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response_1.status_code, HTTPStatus.FOUND)
        self.assertEqual(Follow.objects.count(), NUMBER_OF_FOLLOWED_AUTHORS)

        # отписаться от второго автора
        response_1 = self.authorized_client.get(reverse(
            'posts:profile_unfollow', kwargs={'username': PostURLTests.author1}
        ))
        self.assertEqual(
            Follow.objects.count(),
            NUMBER_OF_FOLLOWED_AUTHORS - 1
        )
        follow_instance = Follow.objects.first()
        self.assertEqual(follow_instance.author, PostURLTests.author)

    def test_follow_posts(self):
        author_followed = PostURLTests.author
        self.authorized_client.get(reverse(
            'posts:profile_follow', kwargs={'username': author_followed}
        ))
        response = self.authorized_client.get(reverse('posts:follow_index'))
        response_1 = self.author_client_1.get(reverse('posts:follow_index'))
        posts_nbr_before_post_follower = len(response.context['posts'])
        posts_nbr_before_post_not_follower = len(response_1.context['posts'])
        post_test_follow = Post.objects.create(
            author=author_followed,
            text='test_follow_posts'
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        posts_nbr_after_post_follower = len(response.context['posts'])
        posts_nbr_after_post_not_follower = len(response_1.context['posts'])
        self.assertEqual(
            posts_nbr_after_post_follower,
            posts_nbr_before_post_follower + 1
        )
        self.assertEqual(response.context['posts'][0], post_test_follow)
        self.assertEqual(
            posts_nbr_after_post_not_follower,
            posts_nbr_before_post_not_follower
        )
        self.assertNotIn(post_test_follow, response_1.context['posts'])
