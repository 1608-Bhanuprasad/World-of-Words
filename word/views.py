from cProfile import Profile
from datetime import timezone
from email.headerregistry import Group
from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
import json
from .models import CommunityUpdate, DiscussionPost, DiscussionReply, GroupMembership, Notification, Outline, ProjectAsset, Storyboard  # Ensure this import is correct
from .serializers import NotificationSerializer, AuthorSuggestionSerializer
from requests import Response

from word.models import AuthorSuggestion, Post, Comment, Suggestion, Notification, Profile
from word.forms import BlogForm, PostForm

import logging

from word import models  # Add logging for debugging

# Set up logging
logger = logging.getLogger(__name__)

def index(request):
    return render(request, 'word/index.html')

def intermediate_view(request):
    return render(request, 'word/intermediate.html')

from django.core.mail import send_mail

from django.core.mail import send_mail
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.models import User

def register_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, 'word/register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return render(request, 'word/register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return render(request, 'word/register.html')

        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()

        # ✅ SMTP Email sending
        subject = 'Welcome to World of Words!'
        message = f"Hi {username},\n\nThanks for registering at World of Words!\nWe're excited to have you with us.\n\nHappy writing!"
        from_email = 'worldofwords81@gmail.com'
        recipient_list = [email]

        try:
            send_mail(subject, message, from_email, recipient_list)
            messages.success(request, "Registration successful! A welcome email has been sent.")
        except Exception as e:
            messages.warning(request, f"Registered, but failed to send email: {e}")

        return redirect("login")

    return render(request, 'word/register.html')


def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Login successful!")
            return redirect("mainuser")
        else:
            messages.error(request, "Invalid username or password")
    return render(request, 'word/login.html')

def author_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_staff:
                login(request, user)
                return JsonResponse({'success': True, 'redirect': '/author_dashboard/'})
            else:
                return JsonResponse({'success': False, 'message': 'Not authorized as an author'})
        return JsonResponse({'success': False, 'message': 'Invalid credentials'})
    return render(request, 'word/author_login.html')

def password_reset(request):
    return render(request, 'word/password_reset.html')

@login_required
def author_dashboard(request):
    posts = Post.objects.filter(user=request.user, is_published=True)
    notifications = Notification.objects.filter(user=request.user).count()
    writings_count = posts.count()
    reviews = []
    latest_fan_message = None

    context = {
        'user': request.user,
        'posts': posts,
        'writings_count': writings_count,
        'notifications_count': notifications,
        'reviews': reviews,
        'latest_fan_message': latest_fan_message,
        
    }
    return render(request, 'word/author_dashboard.html', context)

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('index')

@login_required
def mainuser(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category', 'all')
    
    posts = Post.objects.filter(user=request.user)  # Fetch user's posts
    suggestions = Suggestion.objects.filter(post__in=posts)  # Fetch suggestions for user's posts

    if query:
        posts = posts.filter(title__icontains=query) | posts.filter(content__icontains=query)
    if category != 'all':
        posts = posts.filter(category=category)

    trending_posts = posts.order_by('-created_at')[:3]

    context = {
        'user': request.user,
        'query': query,
        'category': category,
        'posts': posts[:6],
        'trending_posts': trending_posts,
        'suggestions': suggestions,  # Add suggestions to context
    }
    return render(request, 'word/mainuser.html', context)

@login_required
def editor_view(request):
    type = request.GET.get('type', 'content')
    return render(request, 'word/editor.html', {'type': type})

from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json

@csrf_exempt
@login_required
def publish_post(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            title = data.get("title")
            content = data.get("content")
            type = data.get("type", "blog")

            if not title or not content:
                return JsonResponse({"success": False, "error": "Missing title or content"}, status=400)

            # 🌐 AI Content Check
            ai_score = check_ai_generated(content)
            if ai_score is None:
                return JsonResponse({"success": False, "error": "Plagiarism check failed. Please try again later."}, status=500)
            elif ai_score >= 0.5:
                return JsonResponse({
                    "success": False,
                    "error": "This post appears to be AI-generated. Please revise it before publishing."
                }, status=400)

            # ✅ Save Post if Passed AI Check
            new_post = Post.objects.create(
                user=request.user,
                type=type,
                title=title,
                content=content,
                is_published=True
            )

            suggestion = f"Consider adding more details to enhance engagement for '{title}'."
            authors = User.objects.filter(is_staff=True)
            for author in authors:
                Notification.objects.create(
                    user=author,
                    post=new_post,
                    message=f"New {type} posted: {title}. Suggested Review: {suggestion}"
                )

            return JsonResponse({"success": True, "post_id": new_post.id, "suggestion": suggestion})

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)


def generate_suggestions(blog_id):
    blog = get_object_or_404(Post, id=blog_id)
    author = blog.user

    # Example suggestion message (you can replace this with AI-generated text)
    suggestion_message = f"Suggested Review: Consider adding more details to '{blog.title}' to enhance engagement."

    # Create a notification for the author
    Notification.objects.create(
        user=author,
        message=f"New blog posted: {blog.title}. {suggestion_message}",
        post=blog
    )

    # Notify the user (who should receive suggestions)
    try:
        user_to_notify = User.objects.get(username="sai123")  # Adjust logic if needed
        Notification.objects.create(
            user=user_to_notify,
            message=f"New blog posted: {blog.title}. {suggestion_message}",
            post=blog
        )
    except User.DoesNotExist:
        print("User 'sai123' not found. No notification created.")

@login_required
def blog_detail(request, post_id):
    try:
        post = Post.objects.get(id=post_id)
        comments = Comment.objects.filter(post=post)
        context = {'post': post, 'comments': comments}
        return render(request, 'word/blog_detail.html', context)
    except Post.DoesNotExist:
        return HttpResponse("Post not found", status=404)

@login_required
def notifications(request):
    return render(request, "word/notifications.html")

@login_required
def suggestions(request):
    type = request.GET.get('type', 'following')
    suggestions = Suggestion.objects.all()
    context = {'type': type, 'suggestions': suggestions}
    return render(request, 'word/suggestions.html', context)

@login_required
def shop(request):
    return render(request, 'word/shop.html')

def about(request):
    return render(request, 'word/about.html', {'user': request.user})

@login_required
def user_profile(request):
    user_profile, created = Profile.objects.get_or_create(user=request.user)
    user_posts = Post.objects.filter(user=request.user)  # Fetch user's posts
    return render(request, 'word/profile.html', {'profile': user_profile, 'posts': user_posts})

@login_required
def author_notifications(request):
    return render(request, 'author_notifications.html', {})

def community(request):
    return render(request, 'word/community.html')

def writing_goals(request):
    return render(request, 'word/')

@login_required
def create_blog(request):
    """Allows an author to create a new blog"""
    if request.method == 'POST':
        form = BlogForm(request.POST)
        if form.is_valid():
            blog = form.save(commit=False)
            blog.user = request.user
            blog.save()
            messages.success(request, "Blog post created successfully!")
            return redirect('author_dashboard')
    else:
        form = BlogForm()
    return render(request, 'word/create_blog.html', {'form': form})

@login_required
def edit_blog(request, blog_id):
    """Allows an author to edit a blog"""
    blog = get_object_or_404(Post, id=blog_id, user=request.user)
    if request.method == 'POST':
        form = BlogForm(request.POST, instance=blog)
        if form.is_valid():
            form.save()
            messages.success(request, "Blog post updated successfully!")
            return redirect('author_dashboard')
    else:
        form = BlogForm(instance=blog)
    return render(request, 'word/edit_blog.html', {'form': form, 'blog': blog})

@login_required
def delete_blog(request, blog_id):
    """Allows an author to delete a blog"""
    blog = get_object_or_404(Post, id=blog_id, user=request.user)
    if request.method == 'POST':
        blog.delete()
        messages.success(request, "Blog post deleted successfully!")
        return redirect('author_dashboard')
    return render(request, 'word/confirm_delete.html', {'blog': blog})

@login_required
def settings(request):
    """Author settings page"""
    return render(request, 'word/settings.html')

from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Notification, AuthorSuggestion

@api_view(["GET"])
def get_notifications(request):
    user = request.user
    logger.debug(f"Fetching notifications for user: {user.username}")
    notifications = Notification.objects.filter(user=user).order_by("-created_at")
    logger.debug(f"Found {notifications.count()} notifications")
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)

@api_view(["GET"])
def get_suggestions(request):
    user = request.user
    logger.debug(f"Fetching suggestions for user: {user.username}")
    
    # Generate suggestions for each notification if they don't exist
    notifications = Notification.objects.filter(user=user)
    logger.debug(f"Found {notifications.count()} notifications for suggestion generation")
    
    admin_user = User.objects.filter(is_superuser=True).first()  # Use admin as the suggestion author
    if not admin_user:
        admin_user = user  # Fallback to the current user if no admin exists
        logger.debug("No admin user found, using current user as suggestion author")

    for notification in notifications:
        if notification.post and not AuthorSuggestion.objects.filter(user=user, suggestion_text__contains=notification.post.title).exists():
            logger.debug(f"Generating suggestion for post: {notification.post.title}")
            # Check if the user is the author of the post
            if notification.post.user == user:
                suggestion_text = f"Consider adding more details to your post '{notification.post.title}' to enhance engagement."
            else:
                suggestion_text = f"You might enjoy reading '{notification.post.title}' in more detail—check it out!"
            AuthorSuggestion.objects.create(
                user=user,
                author=admin_user,
                suggestion_text=suggestion_text
            )
            logger.debug(f"Created suggestion: {suggestion_text}")

    suggestions = AuthorSuggestion.objects.filter(user=user).order_by("-created_at")
    logger.debug(f"Found {suggestions.count()} suggestions for user")
    serializer = AuthorSuggestionSerializer(suggestions, many=True)
    return Response(serializer.data)

@login_required
@csrf_exempt
def submit_author_suggestion(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            post_id = data.get('post_id')
            suggestion_text = data.get('suggestion_text')

            if not post_id or not suggestion_text:
                return JsonResponse({'success': False, 'error': 'Missing post_id or suggestion_text'}, status=400)

            post = get_object_or_404(Post, id=post_id)
            author = request.user  # The author submitting the suggestion
            user = post.user  # The user who posted the content

            logger.debug(f"Submitting suggestion for post {post_id} by user {user.username}")
            logger.debug(f"Suggestion text: {suggestion_text}, submitted by author: {author.username}")

            # Create an AuthorSuggestion for the user
            author_suggestion = AuthorSuggestion.objects.create(
                user=user,
                author=author,
                suggestion_text=suggestion_text
            )
            logger.debug(f"Created AuthorSuggestion: {author_suggestion.id} for user {user.username}")

            # Create a Notification for the user
            notification = Notification.objects.create(
                user=user,
                post=post,
                message=f"New suggestion from {author.username}: {suggestion_text}"
            )
            logger.debug(f"Created Notification: {notification.id} for user {user.username}")

            return JsonResponse({'success': True, 'message': 'Suggestion submitted successfully!'})
        except Exception as e:
            logger.error(f"Error in submit_author_suggestion: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
def add_suggestion(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        post_id = data.get('post_id')
        text = data.get('text')

        post = get_object_or_404(Post, id=post_id)
        suggestion = Suggestion.objects.create(user=request.user, post=post, text=text)

        # Notify the post owner
        Notification.objects.create(
            user=post.user,
            post=post,
            message=f"You have a new suggestion on '{post.title}'."
        )

        return JsonResponse({'message': 'Suggestion added successfully!'})
    return JsonResponse({'error': 'Invalid request'}, status=400)
@login_required
def author_editor(request):
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")

        if not title or not content:
            messages.error(request, "Title and content are required.")
            return redirect("author_editor")

        ai_score = check_ai_generated(content)
        if ai_score is None:
            messages.error(request, "Plagiarism check failed. Please try again later.")
            return redirect("author_editor")
        elif ai_score >= 0.5:
            messages.error(request, "Your post appears to be AI-generated. Please revise before publishing.")
            return redirect("author_editor")

        # Save only if passed
        post = Post.objects.create(
            title=title,
            content=content,
            user=request.user,
            is_published=True
        )
        messages.success(request, "Post published successfully!")
        return redirect("author_profile")

    return render(request, "word/author_editor.html")


@login_required
def collaboration(request):
    return render(request, 'word/collaboration.html')

@login_required
def editor(request):
    type = request.GET.get('type', 'content')
    return render(request, 'word/editor.html', {'type': type})

@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, author=request.user)
    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Post updated successfully'})
        else:
            return JsonResponse({'success': False, 'error': form.errors}, status=400)
    else:
        form = PostForm(instance=post)
    return render(request, 'word/author_editor.html', {'form': form, 'post': post})

@login_required
@csrf_exempt
def save_draft(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            title = data.get('title')
            content = data.get('content')
            type = data.get('type', 'blog')
            if not title or not content:
                return JsonResponse({'success': False, 'error': 'Title and content are required'}, status=400)
            post, created = Post.objects.get_or_create(
                author=request.user,
                title=title,
                type=type,
                defaults={'content': content}
            )
            if not created:
                post.content = content
                post.save()
            return JsonResponse({'success': True, 'post_id': post.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
@csrf_exempt
def add_collaborator(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            if not username:
                return JsonResponse({'success': False, 'error': 'Username is required'}, status=400)
            try:
                collaborator = User.objects.get(username=username)
                return JsonResponse({'success': True, 'username': username})
            except User.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
def discussions(request):
    discussions = DiscussionPost.objects.all().order_by('-created_at')[:20]
    context = {
        'discussions': discussions,
    }
    return render(request, 'word/discussions.html', context)

@login_required
def community_feed(request):
    if request.method == 'GET':
        updates = CommunityUpdate.objects.all().order_by('-created_at')[:20]
        updates_data = [
            {
                'id': update.id,
                'author': update.user.username,
                'message': update.message,
                'created_at': update.created_at.isoformat(),
            } for update in updates
        ]
        return JsonResponse({'updates': updates_data})
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
@csrf_exempt
def community_discussion(request):
    if request.method == 'POST':
        try:
            logger.debug('Received POST data: %s', request.body)
            data = json.loads(request.body)
            content = data.get('content')
            if not content:
                return JsonResponse({'success': False, 'error': 'Content is required'}, status=400)
            discussion = DiscussionPost.objects.create(
                user=request.user,
                content=content
            )
            logger.debug('Created discussion with id: %d', discussion.id)
            return JsonResponse({'success': True, 'id': discussion.id})
        except Exception as e:
            logger.error('Error in community_discussion: %s', str(e))
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
@csrf_exempt
def community_reply(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            post_id = data.get('post_id')
            reply_content = data.get('reply')
            if not post_id or not reply_content:
                return JsonResponse({'success': False, 'error': 'Post ID and reply content are required'}, status=400)
            discussion = get_object_or_404(DiscussionPost, id=post_id)
            reply = DiscussionReply.objects.create(
                user=request.user,
                discussion_post=discussion,
                content=reply_content
            )
            return JsonResponse({'success': True, 'id': reply.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)


@login_required
def community_groups(request):
   return render(request,'word\community.html')

@login_required
@csrf_exempt
def community_join(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            group_id = data.get('group_id')
            if not group_id:
                return JsonResponse({'success': False, 'error': 'Group ID is required'}, status=400)
            group = get_object_or_404(Group, id=group_id)
            if GroupMembership.objects.filter(user=request.user, group=group).exists():
                return JsonResponse({'success': False, 'error': 'You are already a member of this group'}, status=400)
            GroupMembership.objects.create(
                user=request.user,
                group=group
            )
            return JsonResponse({'success': True, 'message': 'Joined group successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)



@login_required
@csrf_exempt
def create_group(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name')
            description = data.get('description')
            if not name or not description:
                return JsonResponse({'success': False, 'error': 'Name and description are required'}, status=400)
            group = Group.objects.create(
                name=name,
                description=description,
                creator=request.user,
                
            )
            return JsonResponse({'success': True, 'id': group.id, 'message': 'Group created successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)


@login_required
@csrf_exempt
def add_storyboard(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            title = data.get('title')
            content = data.get('content', '')
            collaborator_usernames = data.get('collaborators', [])

            if not title:
                return JsonResponse({'success': False, 'error': 'Title is required'}, status=400)

            storyboard = Storyboard.objects.create(
                title=title,
                content=content,
                creator=request.user
            )

            for username in collaborator_usernames:
                try:
                    collaborator = User.objects.get(username=username)
                    storyboard.collaborators.add(collaborator)
                    Notification.objects.create(
                        user=collaborator,
                        message=f"You've been added as a collaborator to storyboard '{title}' by {request.user.username}.",
                    )
                except User.DoesNotExist:
                    logger.warning(f"User {username} not found for storyboard collaboration.")

            return JsonResponse({'success': True, 'id': storyboard.id, 'message': 'Storyboard created successfully'})
        except Exception as e:
            logger.error(f"Error in add_storyboard: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
@csrf_exempt
def edit_storyboard(request, storyboard_id):
    if request.method == 'POST':
        try:
            storyboard = get_object_or_404(Storyboard, id=storyboard_id)
            if request.user != storyboard.creator and request.user not in storyboard.collaborators.all():
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

            data = json.loads(request.body)
            title = data.get('title')
            content = data.get('content')
            collaborator_usernames = data.get('collaborators', [])

            if title:
                storyboard.title = title
            if content:
                storyboard.content = content

            storyboard.collaborators.clear()
            for username in collaborator_usernames:
                try:
                    collaborator = User.objects.get(username=username)
                    storyboard.collaborators.add(collaborator)
                except User.DoesNotExist:
                    logger.warning(f"User {username} not found for storyboard collaboration.")

            storyboard.save()
            return JsonResponse({'success': True, 'message': 'Storyboard updated successfully'})
        except Exception as e:
            logger.error(f"Error in edit_storyboard: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
def view_storyboard(request, storyboard_id):
    if request.method == 'GET':
        try:
            storyboard = get_object_or_404(Storyboard, id=storyboard_id)
            if request.user != storyboard.creator and request.user not in storyboard.collaborators.all():
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

            data = {
                'id': storyboard.id,
                'title': storyboard.title,
                'content': storyboard.content,
                'creator': storyboard.creator.username,
                'collaborators': [user.username for user in storyboard.collaborators.all()],
                'created_at': storyboard.created_at.isoformat(),
                'updated_at': storyboard.updated_at.isoformat(),
            }
            return JsonResponse({'success': True, 'storyboard': data})
        except Exception as e:
            logger.error(f"Error in view_storyboard: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)


@login_required
@csrf_exempt
def add_outline(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            title = data.get('title')
            content = data.get('content', '')
            collaborator_usernames = data.get('collaborators', [])

            if not title:
                return JsonResponse({'success': False, 'error': 'Title is required'}, status=400)

            outline = Outline.objects.create(
                title=title,
                content=content,
                creator=request.user
            )

            for username in collaborator_usernames:
                try:
                    collaborator = User.objects.get(username=username)
                    outline.collaborators.add(collaborator)
                    Notification.objects.create(
                        user=collaborator,
                        message=f"You've been added as a collaborator to outline '{title}' by {request.user.username}.",
                    )
                except User.DoesNotExist:
                    logger.warning(f"User {username} not found for outline collaboration.")

            return JsonResponse({'success': True, 'id': outline.id, 'message': 'Outline created successfully'})
        except Exception as e:
            logger.error(f"Error in add_outline: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)


@login_required
@csrf_exempt
def edit_outline(request, outline_id):
    if request.method == 'POST':
        try:
            outline = get_object_or_404(Outline, id=outline_id)
            if request.user != outline.creator and request.user not in outline.collaborators.all():
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

            data = json.loads(request.body)
            title = data.get('title')
            content = data.get('content')
            collaborator_usernames = data.get('collaborators', [])

            if title:
                outline.title = title
            if content:
                outline.content = content

            outline.collaborators.clear()
            for username in collaborator_usernames:
                try:
                    collaborator = User.objects.get(username=username)
                    outline.collaborators.add(collaborator)
                except User.DoesNotExist:
                    logger.warning(f"User {username} not found for outline collaboration.")

            outline.save()
            return JsonResponse({'success': True, 'message': 'Outline updated successfully'})
        except Exception as e:
            logger.error(f"Error in edit_outline: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
def view_outline(request, outline_id):
    if request.method == 'GET':
        try:
            outline = get_object_or_404(Outline, id=outline_id)
            if request.user != outline.creator and request.user not in outline.collaborators.all():
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

            data = {
                'id': outline.id,
                'title': outline.title,
                'content': outline.content,
                'creator': outline.creator.username,
                'collaborators': [user.username for user in outline.collaborators.all()],
                'created_at': outline.created_at.isoformat(),
                'updated_at': outline.updated_at.isoformat(),
            }
            return JsonResponse({'success': True, 'outline': data})
        except Exception as e:
            logger.error(f"Error in view_outline: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)


@login_required
@csrf_exempt
def upload_asset(request):
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            asset_type = request.POST.get('asset_type')
            file = request.FILES.get('file')
            url = request.POST.get('url')

            if not name or not asset_type:
                return JsonResponse({'success': False, 'error': 'Name and asset type are required'}, status=400)

            if asset_type in ['pdf', 'image', 'video'] and not file:
                return JsonResponse({'success': False, 'error': 'File is required for this asset type'}, status=400)
            if asset_type == 'url' and not url:
                return JsonResponse({'success': False, 'error': 'URL is required for this asset type'}, status=400)

            asset = ProjectAsset.objects.create(
                name=name,
                asset_type=asset_type,
                file=file if file else None,
                url=url if url else None,
                creator=request.user
            )
            return JsonResponse({'success': True, 'id': asset.id, 'message': 'Asset uploaded successfully'})
        except Exception as e:
            logger.error(f"Error in upload_asset: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
def view_asset(request, asset_id):
    if request.method == 'GET':
        try:
            asset = get_object_or_404(ProjectAsset, id=asset_id)
            if request.user != asset.creator:
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

            data = {
                'id': asset.id,
                'name': asset.name,
                'asset_type': asset.asset_type,
                'file_url': asset.file.url if asset.file else None,
                'url': asset.url,
                'creator': asset.creator.username,
                'created_at': asset.created_at.isoformat(),
            }
            return JsonResponse({'success': True, 'asset': data})
        except Exception as e:
            logger.error(f"Error in view_asset: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, user=request.user)
    if request.method == "POST" or request.method == "GET":
        post.delete()
        messages.success(request, "Post deleted successfully!")
        return redirect('author_profile')
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)

def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    return render(request, 'word\post_detail.html', {'post': post})

@login_required
def author_profile(request):
    if not request.user.is_staff:
        posts = Post.objects.filter(user=request.user, is_published=True)
    else:
        posts = Post.objects.filter(user=request.user)

    writings_count = posts.count()
    reviews = []  # Replace with actual review logic if needed
    latest_fan_message = None  # Replace with actual fan message logic if needed

    # Get or create the user's profile
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'writings_count': writings_count,
            'posts': [
                {
                    'id': post.id,
                    'title': post.title,
                    'type_display': post.get_type_display(),
                    'created_at': post.created_at.isoformat()
                } for post in posts
            ]
        })

    context = {
        'user': request.user,
        'profile': profile,  # Add profile to context
        'posts': posts,
        'writings_count': writings_count,
        'reviews': reviews,
        'latest_fan_message': latest_fan_message,
    }
    return render(request, 'word/author_profile.html', context)

@login_required
def author_editor(request):
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        post_type = request.POST.get("type")
        
        print(f"Received post type: {post_type}")

        if not title or not content:
            return render(request, "word/author_editor.html", {
                "error": "Title and content are required.",
                "title": title,
                "content": content,
                "post_type": post_type,
            })

        valid_types = ['blog', 'novel', 'story', 'gossip']
        if post_type not in valid_types:
            return render(request, "word/author_editor.html", {
                "error": "Invalid post type selected.",
                "title": title,
                "content": content,
                "post_type": post_type,
            })

        ai_score = check_ai_generated(content)
        print(f"AI score for content: {ai_score}")
        if ai_score is None:
            return render(request, "word/author_editor.html", {
                "plagiarism_error": "Plagiarism check failed. Please try again later.",
                "title": title,
                "content": content,
                "post_type": post_type,
            })
        elif ai_score >= 0.5:
            return render(request, "word/author_editor.html", {
                "plagiarism_error": f"Your content appears to be AI-generated or plagiarized (score: {ai_score:.2f}). Please revise and try again.",
                "title": title,
                "content": content,
                "post_type": post_type,
            })

        post = Post.objects.create(
            title=title,
            content=content,
            user=request.user,
            is_published=True,
            type=post_type
        )
        messages.success(request, "Post published successfully!")
        return redirect("author_profile")

    return render(request, "word/author_editor.html", {
        "title": "",
        "content": "",
        "post_type": "blog",  # Default to blog
    })

import requests  # Add this if not already present

# Sapling AI Detection Function
def check_ai_generated(text):
    API_KEY = "sapling_api_key"
    url = "https://api.sapling.ai/api/v1/aidetect"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "key": API_KEY,
        "text": text
    }
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        score = result.get("ai_probability") or result.get("score") or result.get("ai")
        return score
    else:
        return None

import google.generativeai as genai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

# Configure Gemini API (replace with your API key)
genai.configure(api_key="AIzaSyAFEn4l3CSh7E3R1dorODCbh1KhObJIoSM")
model = genai.GenerativeModel("gemini-1.5-flash")

@csrf_exempt
def gemini_bot(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get("message", "").lower()
            conversation_history = data.get("conversation_history", [])

            # Initialize chat with Gemini
            chat = model.start_chat()

            # Prepare the prompt with conversation history for context
            history_prompt = ""
            for entry in conversation_history:
                role = entry["role"]
                message = entry["message"]
                history_prompt += f"{role.capitalize()}: {message}\n"
            full_prompt = f"Conversation history:\n{history_prompt}\nUser: {user_message}\nBot:"

            # Check if user wants to know about website features
            if any(keyword in user_message for keyword in ["features", "what can i do", "what does this website offer"]):
                if request.user.is_authenticated:
                    username = request.user.username
                    features_response = (
                        f"### Welcome to World of Words, {username}!\n"
                        "Here are the features you can enjoy:\n"
                        "- **Write and Publish**: Create blogs, novels, short stories, and gossip using our editor.\n"
                        "- **Explore Content**: Check out the Latest Blogs and Trending Now sections with categories like Tech, Romance, and more.\n"
                        "- **Plagiarism Check**: Use me to verify if your content is original before publishing.\n"
                        "- **User Profile**: View your username and email in the Profile section.\n"
                        "- **Notifications & Suggestions**: Stay updated with notifications and get writing ideas.\n"
                        "- **Dark Mode**: Toggle between light and dark themes for a better experience.\n"
                        "- **Search & Filter**: Use the search bar to find content by category or keyword.\n"
                        "\nWhat would you like to do next?"
                    )
                else:
                    features_response = (
                        "### Welcome to World of Words!\n"
                        "Please log in to access all features:\n"
                        "- Write blogs, novels, short stories, and gossip.\n"
                        "- Explore Latest Blogs and Trending Now sections.\n"
                        "- Check for plagiarism.\n"
                        "- View your profile, notifications, and toggle dark mode.\n"
                        "\nLog in to get started!"
                    )
                bot_response = features_response
                plagiarism_result = None

            # Check if user wants to write content
            elif any(keyword in user_message for keyword in ["write", "blog", "story", "gossip"]):
                prompt = f"{full_prompt} Generate a short {user_message} (100-150 words) and format the response in Markdown with a title and paragraphs."
                response = chat.send_message(prompt)
                bot_response = response.text
                plagiarism_result = None

            # Check for plagiarism
            elif "check plagiarism" in user_message or "can you check for plagiarism" in user_message or len(user_message.split()) > 50:
                prompt = f"{full_prompt} Check if the following content is original or potentially plagiarized by comparing it to common web sources: '{user_message}'. Format the response in Markdown with a heading 'Plagiarism Check Result' and a detailed explanation."
                response = chat.send_message(prompt)
                bot_response = "Plagiarism check completed."
                plagiarism_result = response.text

            # Check for latest blogs
            elif "latest blogs" in user_message:
                bot_response = (
                    "### Latest Blogs on World of Words\n"
                    "Here are some of the latest blogs you can explore:\n"
                    "- **Weekly Horoscope: April 6 to 12, 2025** - Insights into astrological events.\n"
                    "- **Astros Crawfish Boil: April 1, 2025** - Updates on Houston Astros.\n"
                    "- **Gen Z & Tumblr: A New Wave** - Tumblr's resurgence among Gen Z.\n"
                    "- **Here Are the 15 Books You Should Read in April** - Curated book list.\n"
                    "\nCheck out the 'Latest Blogs' section for more!"
                )
                plagiarism_result = None

            # Check for dark mode toggle instructions
            elif "dark mode" in user_message:
                bot_response = (
                    "### How to Toggle Dark Mode\n"
                    "To switch between light and dark themes:\n"
                    "- Look for the **moon icon** in the top-right corner of the page.\n"
                    "- Click the icon to toggle between light and dark modes.\n"
                    "\nEnjoy a comfortable reading experience!"
                )
                plagiarism_result = None

            # Check for writing tips
            elif "writing tips" in user_message:
                bot_response = (
                    "### Writing Tips for Beginners\n"
                    "Here are some tips to improve your writing:\n"
                    "- **Start with a Strong Hook**: Grab your reader's attention with an interesting opening.\n"
                    "- **Keep it Simple**: Use clear and concise language to convey your ideas.\n"
                    "- **Show, Don’t Tell**: Use descriptive language to paint a picture instead of just stating facts.\n"
                    "- **Edit Ruthlessly**: Revise your work to remove unnecessary words and improve clarity.\n"
                    "- **Read Aloud**: This helps you catch awkward phrasing and improve the flow.\n"
                    "\nWould you like to start writing now?"
                )
                plagiarism_result = None

            else:
                # General query handling with conversation context
                prompt = f"{full_prompt} Respond to the user's query in a conversational tone, referencing the conversation history if relevant. Format the response in Markdown with appropriate headings and bullet points if needed."
                response = chat.send_message(prompt)
                bot_response = response.text
                plagiarism_result = None

            return JsonResponse({
                "response": bot_response,
                "plagiarism_result": plagiarism_result
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=400)




def contact(request):
    return render(request, 'word/about.html', {})

from django.db.models import Q
from .models import Post, Notification, Profile, Message

@login_required
def discussions(request):
    # Get the logged-in user
    current_user = request.user

    # Get only superusers (authors), excluding the current user
    all_authors = User.objects.filter(is_superuser=True).exclude(id=current_user.id)

    # Determine the "first author" (e.g., Bhanu, or the author with the lowest ID)
    first_author = None
    bhanu = all_authors.filter(username='Bhanu').first()
    if bhanu and bhanu != current_user:
        first_author = bhanu
    else:
        # Fallback to the author with the lowest ID if Bhanu doesn't exist or is the current user
        first_author = all_authors.order_by('id').first()

    # Initialize chat_messages to None
    chat_messages = None
    recipient = None

    # Handle AJAX POST request for sending messages and file uploads
    if request.method == "POST" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        recipient_id = request.POST.get('recipient')
        content = request.POST.get('content', '')  # Allow empty content if there's a file
        file_attachment = request.FILES.get('file_attachment')

        if not recipient_id:
            return JsonResponse({'success': False, 'error': 'Recipient is required.'}, status=400)

        try:
            recipient = User.objects.get(id=recipient_id)
            # Ensure the recipient is a superuser (author)
            if not recipient.is_superuser:
                return JsonResponse({'success': False, 'error': 'Recipient is not an author.'}, status=400)

            # Validate file type and size (optional)
            if file_attachment:
                allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
                max_size = 5 * 1024 * 1024  # 5MB
                if file_attachment.content_type not in allowed_types:
                    return JsonResponse({'success': False, 'error': 'Unsupported file type. Only JPEG, PNG, and PDF are allowed.'}, status=400)
                if file_attachment.size > max_size:
                    return JsonResponse({'success': False, 'error': 'File size exceeds 5MB limit.'}, status=400)

            # Create the new message
            new_message = Message.objects.create(
                sender=current_user,
                recipient=recipient,
                content=content,
                file_attachment=file_attachment if file_attachment else None
            )
            # Return the new message details for the frontend to append
            response_data = {
                'success': True,
                'message': {
                    'content': new_message.content,
                    'timestamp': new_message.timestamp.strftime('%H:%M, %b %d, %Y'),
                    'is_sent': True,  # Since this is the sender's view
                }
            }
            if new_message.file_attachment:
                response_data['message']['file_url'] = new_message.file_attachment.url
                response_data['message']['file_type'] = new_message.file_attachment.url.split('.')[-1].lower()
            return JsonResponse(response_data)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Recipient does not exist.'}, status=400)

    # Handle regular GET/POST requests
    # Get the selected recipient (if any) from the query parameter
    recipient_id = request.GET.get('recipient')
    if recipient_id:
        try:
            recipient = User.objects.get(id=recipient_id)
            # Ensure the recipient is a superuser (author)
            if not recipient.is_superuser:
                messages.error(request, "Selected user is not an author.")
                recipient = None
        except User.DoesNotExist:
            messages.error(request, "Selected user does not exist.")
    elif first_author and first_author != current_user:
        # If no recipient is specified and the current user is not the first author,
        # automatically select the first author as the recipient
        recipient = first_author
    elif all_authors.exists():
        # If the current user is the first author, select the next available author
        recipient = all_authors.exclude(id=first_author.id).order_by('id').first()

    # Handle regular POST request for sending messages (fallback for non-AJAX)
    if request.method == "POST" and not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        recipient_id = request.POST.get('recipient')
        content = request.POST.get('content', '')
        file_attachment = request.FILES.get('file_attachment')

        if not recipient_id:
            messages.error(request, "Recipient is required.")
        else:
            try:
                recipient = User.objects.get(id=recipient_id)
                # Ensure the recipient is a superuser (author)
                if not recipient.is_superuser:
                    messages.error(request, "Recipient is not an author.")
                else:
                    Message.objects.create(
                        sender=current_user,
                        recipient=recipient,
                        content=content,
                        file_attachment=file_attachment if file_attachment else None
                    )
                    messages.success(request, "Message sent successfully!")
                    # Redirect to the same page with the recipient selected
                    return redirect(f"{request.path}?recipient={recipient_id}")
            except User.DoesNotExist:
                messages.error(request, "Recipient does not exist.")

    # Get the conversation between the current user and the selected recipient
    if recipient:
        chat_messages = Message.objects.filter(
            (Q(sender=current_user) & Q(recipient=recipient)) |
            (Q(sender=recipient) & Q(recipient=current_user))
        )
        # If no messages exist, send a predefined "Hi" message from the first author
        if not chat_messages.exists():
            # Determine who the first author is between the two users
            if current_user == first_author or (first_author and recipient != first_author):
                # If the current user is the first author, they send the "Hi"
                sender = current_user
                receiver = recipient
            else:
                # Otherwise, the first author (e.g., Bhanu) sends the "Hi" to the current user
                sender = first_author
                receiver = current_user
            Message.objects.create(
                sender=sender,
                recipient=receiver,
                content="Hi"
            )
            # Refresh the messages queryset after adding the predefined message
            chat_messages = Message.objects.filter(
                (Q(sender=current_user) & Q(recipient=recipient)) |
                (Q(sender=recipient) & Q(recipient=current_user))
            )

    context = {
        'current_user': current_user,
        'all_authors': all_authors,
        'recipient': recipient,
        'chat_messages': chat_messages,
        'first_author': first_author,
    }
    return render(request, 'word/discussions.html', context)