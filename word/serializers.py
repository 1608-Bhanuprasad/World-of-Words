# word/serializers.py
from rest_framework import serializers
from .models import Notification, AuthorSuggestion
from django.contrib.auth.models import User

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'created_at', 'post']

class AuthorSuggestionSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = AuthorSuggestion
        fields = ['id', 'suggestion_text', 'author_name', 'created_at']