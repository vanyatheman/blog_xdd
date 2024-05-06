from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import (get_object_or_404, redirect, render)
from django.views.decorators.cache import cache_page

from yatube.settings import POSTS_PER_PAGE, TITLE_SYMBOLS

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post

User = get_user_model()


def paginator(request, posts):
    paginator = Paginator(posts, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


@cache_page(20, key_prefix='index_page')
def index(request):
    posts = Post.objects.select_related('group', 'author').all()
    page_obj = paginator(request, posts)
    template = 'posts/index.html'
    title = 'Последние обновления на сайте'
    context = {
        'title': title,
        'posts': posts,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related('author').all()
    page_obj = paginator(request, posts)
    template = 'posts/group_list.html'
    context = {
        'group': group,
        'posts': posts,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    following = False
    author = get_object_or_404(User, username=username)
    posts = author.posts.select_related('group').all()
    page_obj = paginator(request, posts)
    template = 'posts/profile.html'
    follower = request.user

    if (
        request.user.is_authenticated
        and Follow.objects.filter(user=follower, author=author)
    ):
        following = True
    else:
        following = False

    context = {
        'author': author,
        'username': author,
        'posts': posts,
        'page_obj': page_obj,
        'following': following
    }
    return render(request, template, context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    author_posts = post.author.posts.count()
    title = post.text[:TITLE_SYMBOLS]
    template = 'posts/post_detail.html'
    comments = post.comments.all()
    form = CommentForm()
    context = {
        'title': title,
        'post': post,
        'author_posts': author_posts,
        'comments': comments,
        'form': form
    }
    return render(request, template, context)


@login_required
def post_create(request):
    is_edit = False
    template = 'posts/create_post.html'
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', request.user.username)
    context = {'form': form, 'is_edit': is_edit}
    return render(request, template, context)


def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    is_edit = True
    if post.author != request.user:
        return redirect('posts:post_detail', post_id)
    template = 'posts/create_post.html'
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        post = form.save()
        return redirect('posts:post_detail', post_id)
    context = {'form': form, 'is_edit': is_edit, 'post': post}
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    template = 'posts/follow.html'
    posts = Post.objects.filter(author__following__user=request.user)
    page_obj = paginator(request, posts)
    context = {
        'posts': posts,
        'page_obj': page_obj,
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    author_followed = get_object_or_404(User, username=username)
    follow_instance = Follow.objects.filter(
        user=request.user,
        author=author_followed
    )
    if request.user != author_followed and not follow_instance.exists():
        Follow.objects.create(user=request.user, author=author_followed)
    return redirect('posts:follow_index')


@login_required
def profile_unfollow(request, username):
    author_followed = get_object_or_404(User, username=username)
    follow_instance = Follow.objects.filter(
        user=request.user,
        author=author_followed
    )
    if follow_instance.exists():
        follow_instance.delete()
    return redirect('posts:follow_index')
