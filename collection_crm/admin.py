from django.contrib import admin
from collection_crm.models import CollectionUser

class CollectionUserAdmin(admin.ModelAdmin):
    """Administer users in the collection_crm app"""
    list_display = (
        'user', 'level', 'extension_number', 'account_status',
        'daily_target', 'monthly_target'
    )
    search_fields = [
        'user__username', 'user__email', 'extension_number', 'account_status'
    ]

    def view_user_email(self, obj):
        """Show email address from user model"""
        return obj.user.email

    view_user_email.empty_value_display = '???'


admin.site.register(CollectionUser, CollectionUserAdmin)
