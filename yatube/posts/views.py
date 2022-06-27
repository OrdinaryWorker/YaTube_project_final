from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User
from .utilites import use_paginator


@cache_page(20, key_prefix='index_page')
def index(request):
    post_list = Post.objects.all()
    page_obj = use_paginator(request, post_list)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    page_obj = use_paginator(request, post_list)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None,
                    files=request.FILES or None
                    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect("posts:profile", post.author)
    context = {
        "is_edit": False,
        "form": form
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post_id)
    form = PostForm(request.POST or None,
                    files=request.FILES or None,
                    instance=post
                    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id)
    context = {
        "is_edit": True,
        "form": form,
        "post": post
    }
    return render(request, 'posts/create_post.html', context)


def post_detail(request, post_id: int):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm()
    # comments = reversed(post.comments.all())
    comments = post.comments.all()
    context = {
        'post': post,
        'comments': comments,
        'form': form
    }
    return render(request, 'posts/post_detail.html', context)


@login_required()
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    print(form.errors)
    return redirect('posts:post_detail', post_id)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    post_list = author.posts.all()
    page_obj = use_paginator(request, post_list)
    following = False
    if request.user.is_authenticated:
        if Follow.objects.filter(user=request.user, author=author).exists():
            following = True
    context = {
        'posts': post_list,
        'page_obj': page_obj,
        'author': author,
        'following': following,
        'user': request.user
    }
    return render(request, 'posts/profile.html', context)


@login_required
def follow_index(request):
    user = get_object_or_404(User, username=request.user)
    post_list = Post.objects.filter(
        author__following__user=user
    ).select_related('author', 'group')
    page_obj = use_paginator(request, post_list)
    context = {
        'page_obj': page_obj,
        'user': user
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author and (not Follow.objects.filter(
            user=request.user,
            author=author).exists()):
        follower = request.user
        followed = User.objects.get(username=username)
        Follow.objects.create(user=follower, author=followed)
    return redirect('posts:profile', username=author)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    is_follower = Follow.objects.filter(user=request.user, author=author)
    if is_follower.exists():
        is_follower.delete()
    return redirect('posts:profile', username=author)
