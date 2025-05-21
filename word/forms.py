from django import forms
from .models import Post

class BlogForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'category']
from django import forms
from .models import Post  # Make sure to import your model correctly

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'type']  # Include the fields required for the post

