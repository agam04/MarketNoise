from django.contrib import admin
from .models import UserAPIKey


@admin.register(UserAPIKey)
class UserAPIKeyAdmin(admin.ModelAdmin):
    list_display = ('user', 'service', 'masked_key', 'updated_at')
    list_filter = ('service',)
    readonly_fields = ('encrypted_key', 'created_at', 'updated_at')
