import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
User = get_user_model()
ONE_POST = 1
REDIRECT_STATUS = 302
img_folder = Post.image.field.upload_to


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormCreateEditTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(username='author')
        cls.user_not_author = User.objects.create(username='vanyathetester')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.test_image = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client_not_author = Client()
        self.authorized_client_not_author.force_login(self.user_not_author)
        self.author_client = Client()
        self.author_client.force_login(PostFormCreateEditTests.author)

    def test_post_create_authorized(self):
        """Новый пост создан и добавлен в БД."""
        posts_nbr_before_creation = Post.objects.count()
        # Не согласен на счет переноса картинки в setUpClass,
        # это просто не работает.
        # 1ый тест с картинкой работает, 2-ой нет из-за специфики чтения файла.
        # Решал этот вопрос в пачке с наставниками, они сказали сделать так.
        # Можно перенести ёё в setUp, но она нужна только для 2ух функции,
        # не нужды создовать её перед каждым тестом.
        uploaded = SimpleUploadedFile(
            name='test_image.gif',
            content=PostFormCreateEditTests.test_image,
            content_type='image/gif'
        )

        post_content = {
            'text': 'Новый пост',
            'group': PostFormCreateEditTests.group.pk,
            'image': uploaded
        }

        self.author_client.post(
            reverse('posts:post_create'),
            data=post_content,
        )

        posts_nbr_after_creation = Post.objects.count()
        post = Post.objects.all()[0]

        self.assertEqual(post_content['text'], post.text)
        self.assertEqual(post_content['group'], post.group.pk)
        self.assertEqual(f'posts/{uploaded.name}', post.image)
        self.assertEqual(PostFormCreateEditTests.author, post.author)
        self.assertEqual(
            posts_nbr_before_creation + ONE_POST,
            posts_nbr_after_creation
        )

    def test_post_create_authorized_without_group(self):
        """Новый пост создан без группы и добавлен в БД."""
        post_content = {
            'text': 'Пост без группы'
        }

        posts_nbr_before_creation = Post.objects.count()

        self.author_client.post(
            reverse('posts:post_create'),
            data=post_content,
        )

        posts_nbr_after_creation = Post.objects.count()
        post = Post.objects.select_related('group', 'author').get()

        self.assertEqual(post_content['text'], post.text)
        self.assertEqual(post.group, None)
        self.assertEqual(PostFormCreateEditTests.author, post.author)
        self.assertEqual(
            posts_nbr_before_creation + ONE_POST,
            posts_nbr_after_creation
        )

    def test_post_create_not_authorized(self):
        """Новый пост не создан неавторизованный пользователем."""
        post_content = {
            'text': 'Новый пост',
            'group': PostFormCreateEditTests.group.pk
        }

        posts_nbr_before_creation = Post.objects.count()

        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=post_content,
        )

        posts_nbr_after_creation = Post.objects.count()

        self.assertEqual(
            posts_nbr_before_creation,
            posts_nbr_after_creation
        )
        self.assertEqual(
            response.status_code,
            REDIRECT_STATUS
        )

    def test_post_edit_author(self):
        """Пост отредактирован автором."""
        uploaded = SimpleUploadedFile(
            name='test_image_1.gif',
            content=PostFormCreateEditTests.test_image,
            content_type='image/gif'
        )
        created_post = Post.objects.create(
            text='Новый пост',
            author=self.author,
            group=self.group
        )

        post_edit_content = {
            'text': 'Новый пост отредактирован',
            'group': self.group.pk,
            'image': uploaded
        }

        response = self.author_client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': created_post.id}
            ),
            data=post_edit_content,
            follow=True
        )
        edited_post = response.context['post']

        self.assertEqual(edited_post.pub_date, created_post.pub_date)
        self.assertEqual(edited_post.author, created_post.author)
        self.assertEqual(edited_post.text, post_edit_content['text'])
        self.assertEqual(edited_post.group.pk, post_edit_content['group'])
        self.assertEqual(f'posts/{uploaded.name}', edited_post.image)

    def test_post_edit_not_authorized(self):
        """Пост не отредактирован неавторизованным пользователем."""
        created_post = Post.objects.create(
            text='Новый пост',
            author=PostFormCreateEditTests.author,
            group=PostFormCreateEditTests.group
        )

        post_edited_content = {
            'text': 'Новый пост отредактирован',
            'group': PostFormCreateEditTests.group.pk
        }

        response = self.guest_client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': created_post.id}
            ),
            data=post_edited_content
        )

        edited_post = Post.objects.select_related('group', 'author').get()

        self.assertEqual(edited_post.pub_date, created_post.pub_date)
        self.assertEqual(edited_post.author, created_post.author)
        self.assertEqual(edited_post.text, created_post.text)
        self.assertEqual(edited_post.group.pk, created_post.group.pk)
        self.assertEqual(
            response.status_code,
            REDIRECT_STATUS
        )

    def test_post_edit_authorized_not_author(self):
        """Пост не отредактирован не автором."""
        created_post = Post.objects.create(
            text='Новый пост',
            author=PostFormCreateEditTests.author,
            group=PostFormCreateEditTests.group
        )

        post_edited_content = {
            'text': 'Новый пост отредактирован',
            'group': PostFormCreateEditTests.group.pk
        }

        response = self.authorized_client_not_author.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': created_post.id}
            ),
            data=post_edited_content,
        )

        edited_post = Post.objects.select_related('group', 'author').get()

        self.assertEqual(edited_post.pub_date, created_post.pub_date)
        self.assertEqual(edited_post.author, created_post.author)
        self.assertEqual(edited_post.text, created_post.text)
        self.assertEqual(edited_post.group.pk, created_post.group.pk)
        self.assertEqual(
            response.status_code,
            REDIRECT_STATUS
        )

    def test_comment_create_authorized(self):
        """Новый comment создан и добавлен в БД."""
        comments_nbr_before_creation = Comment.objects.count()
        created_post = Post.objects.create(
            text='Новый пост',
            author=PostFormCreateEditTests.author,
            group=PostFormCreateEditTests.group
        )

        comment_data = {'text': 'Текст комментария'}
        self.authorized_client_not_author.post(
            reverse('posts:add_comment', kwargs={'post_id': created_post.id}),
            data=comment_data,
        )

        comments_nbr_after_creation = Comment.objects.count()
        post = Post.objects.all()[0]
        comment_db = post.comments.all()[0]

        self.assertEqual(comment_db.post, post)
        self.assertEqual(comment_db.author, self.user_not_author)
        self.assertEqual(comment_db.text, comment_data['text'])
        self.assertEqual(
            comments_nbr_before_creation + 1,
            comments_nbr_after_creation
        )
