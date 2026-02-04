from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'role', 'is_approved')
    list_filter = ('role', 'is_approved')
    search_fields = ('full_name', 'email')
