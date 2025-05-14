# word/admin.py
from django.contrib import admin
from .models import Post, Comment, Suggestion

admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Suggestion)

from django.contrib import admin
from .models import Notification

admin.site.register(Notification)
