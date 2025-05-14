from django.db import models
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.utils import timezone

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    location = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"
PLAGIARISM_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('passed', 'Passed'),
    ('rejected', 'Rejected'),
]

plagiarism_status = models.CharField(
    max_length=10,
    choices=PLAGIARISM_STATUS_CHOICES,
    default='pending'
)
class Post(models.Model):
    POST_TYPES = (
        ('blog', 'Blog'),
        ('novel', 'Novel'),
        ('short-story', 'Short Story'),
        ('gossip', 'Gossip'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    type = models.CharField(max_length=20, choices=POST_TYPES, default='blog')
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image_url = models.URLField(blank=True, null=True)
    is_published = models.BooleanField(default=False)
    category = models.CharField(max_length=100,blank=True,null=True)
    plagiarism_status = models.CharField(
        max_length=10,
        choices=PLAGIARISM_STATUS_CHOICES, 
        default='pending')
    def __str__(self):
        return self.title

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.post.title}"

class Suggestion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='suggestions', null=True, blank=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Suggestion by {self.user.username} on {self.post.title}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message}"

class AuthorSuggestion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='author_suggestions')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_suggestions')
    suggestion_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Suggestion for {self.user.username} by {self.author.username}"
    
class CommunityUpdate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_updates')
    message = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Update by {self.user.username}: {self.message[:50]}"

class DiscussionPost(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discussion_posts')
    content = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Discussion by {self.user.username}: {self.content[:50]}"

class DiscussionReply(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discussion_replies')
    discussion_post = models.ForeignKey(DiscussionPost, on_delete=models.CASCADE, related_name='replies')
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply by {self.user.username} on Discussion {self.discussion_post.id}"

class Group(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')

    def __str__(self):
        return self.name

class GroupMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_memberships')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='members')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'group')

    def __str__(self):
        return f"{self.user.username} in {self.group.name}"

class Storyboard(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='storyboards')
    collaborators = models.ManyToManyField(User, related_name='collaborated_storyboards', blank=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='storyboards', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Storyboard: {self.title} by {self.creator.username}"

class Outline(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='outlines')
    collaborators = models.ManyToManyField(User, related_name='collaborated_outlines', blank=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='outlines', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Outline: {self.title} by {self.creator.username}"

class ProjectAsset(models.Model):
    ASSET_TYPES = (
        ('pdf', 'PDF'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('url', 'URL'),
    )

    name = models.CharField(max_length=200)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES)
    file = models.FileField(upload_to='project_assets/', blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_assets')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='project_assets', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Asset: {self.name} by {self.creator.username}"

    def clean(self):
        if self.asset_type in ['pdf', 'image', 'video'] and not self.file:
            raise ValidationError("File is required for PDF, Image, or Video asset types.")
        if self.asset_type == 'url' and not self.url:
            raise ValidationError("URL is required for URL asset type.")
        
        
        from django.db import models

class Asset(models.Model):
    name = models.CharField(max_length=255)
    asset_type = models.CharField(max_length=10, choices=[('pdf', 'PDF'), ('image', 'Image')])
    file = models.FileField(upload_to='assets/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Message(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    content = models.TextField(blank=True)  # Allow blank since messages can be file-only
    file_attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True)  # New field for file attachments
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Message from {self.sender} to {self.recipient} at {self.timestamp}"