from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from import_export import resources
from import_export.admin import ImportExportModelAdmin

from helpline.models import Report, HelplineUser,\
        Schedule,\
        Service, Hotdesk, Category, Clock,\
        Dialect, Partner, SipServerConfig, Contact,\
        Address, Disposition, ServiceExternalURL,\
        BackendServerManagerConfig, Break,\
        DID, Scheme, IpAddress, TurnServerConfig,\
        RecordPlay, Case


class DialectAdmin(admin.ModelAdmin):
    list_display = ('id', 'hl_dialect')
    exclude = ('id', 'hl_category', 'hl_status')


class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'extension', 'queue', 'backend_manager_config')
    exclude = ('id',)


class SchemeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ['name']

class ServiceExternalURLAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'urltemplate', 'description', 'opentype')


def disable_hotdesk(modeladmin, request, queryset):
    """Disable a hot desk"""
    queryset.update(status="Unavailable")


disable_hotdesk.short_description = "Disable selected hotdesk"


def enable_hotdesk(modeladmin, request, queryset):
    """Enable a hot desk"""
    queryset.update(status="Available")


enable_hotdesk.short_description = "Enable selected hotdesk"


class HotdeskAdmin(admin.ModelAdmin):
    """Admin list for Hotdesk model"""
    search_fields = [
        'user__username',
        'extension',
        'sip_server__name',
        'backend_manager_config__host',
        'backend_manager_config__name',
    ]
    list_display = (
        'extension',
        'extension_type',
        'status',
        'user',
        'sip_server',
        'backend_manager_config',
        'primary',
    )
    actions = [disable_hotdesk, enable_hotdesk]


def change_service(modeladmin, request, queryset):
    """Change service to hard coded value for now"""
    s = Service.objects.get(id=16)
    queryset.update(service=s)


change_service.short_description = "Change service for selected schedule"


class ScheduleAdmin(admin.ModelAdmin):
    """Schedule list for Schedule model in admin"""
    list_display = ('id', 'user', 'service', 'hl_status', 'view_user_email')
    actions = [change_service]
    search_fields = ['user__username', 'service__name', 'user__email']

    def view_user_email(self, obj):
        return obj.user.email

    view_user_email.empty_value_display = '???'


class BackendServerManagerConfigAdmin(admin.ModelAdmin):
    """Manage backend servers, either Asterisk through AMI
    Or FreeSwitch through it's API"""
    search_fields = ['name', 'host', 'mysql_host']
    list_display = ('id', 'name', 'username', 'host', 'port', 'server_type',
                    'pbxapi_url', 'mysql_host')


class SipServerConfigAdmin(admin.ModelAdmin):
    """Manage SIP Server configs"""
    search_fields = ['name', 'sip_host', 'sip_domain', 'webrtc_gateway_url']
    list_display = ('name', 'sip_host', 'sip_domain', 'webrtc_gateway_url')

class TurnServerConfigAdmin(admin.ModelAdmin):
    """Manage TURN Server configs"""
    search_fields = ['name', 'turn_uri', 'turn_username', 'turn_password']
    list_display = ('name', 'turn_uri', 'turn_username')


class AddressAdmin(admin.ModelAdmin):
    """Manage Helpline Address Objects"""
    list_display = ('hl_names', 'hl_email')


class ContactAdmin(admin.ModelAdmin):
    """Manage Helpline Contact Objects"""
    list_display = ('hl_contact', 'address')


class DispositionAdmin(admin.ModelAdmin):
    """Manage Helpline Disposition Objects"""
    list_display = ('value', 'description')


class CaseAdmin(admin.ModelAdmin):
    """Manage Helpline Disposition Objects"""
    list_display = ('hl_case', 'hl_disposition')
    search_fields = ['hl_case']


class IpAddressAdmin(admin.ModelAdmin):
    """Manage IP Addresses Objects"""
    list_display = ('ip_address', 'user', 'pub_date', 'banned')
    search_fields = ['ip_address', 'user__username', 'user__email', 'pub_date']


class BreakAdmin(admin.ModelAdmin):
    """Manage Helpline Break Reason Objects"""
    list_display = ('name', 'description', 'status')


class RecordPlayAdmin(admin.ModelAdmin):
    """Manage Helpline RecordPlay Objects"""
    list_display = ('user', 'name', 'created_on')


class PartnerResource(resources.ModelResource):
    """Manage partner list"""
    class Meta:
        model = Partner


class PartnerAdmin(ImportExportModelAdmin):
    """Manage Helpline Partner Objects"""
    list_display = ('id', 'code', 'name')
    resource_class = PartnerResource


class HelplineUserAdmin(admin.ModelAdmin):
    """Administer users in the helpline app"""
    list_display = ('user', 'hl_exten', 'hl_status', 'view_user_email')
    search_fields = ['user__username', 'user__email', 'hl_exten', 'hl_status']

    def view_user_email(self, obj):
        return obj.user.email

    view_user_email.empty_value_display = '???'


class DIDAdmin(admin.ModelAdmin):
    """Administer DIDs in the helpline app"""
    list_display = (
        'id', 'view_hotdesk_extension', 'number', 'comment', 'prefix'
    )
    search_fields = [
        'hotdesk__extension',
        'number',
        'comment'
    ]

    def view_hotdesk_extension(self, obj):
        return [
            extension for extension in obj.hotdesk.values_list(
                'extension', flat=True
            )
        ]

    view_hotdesk_extension.empty_value_display = '???'


class ClockAdmin(admin.ModelAdmin):
    """Administer users in the helpline app"""
    list_display = (
        'user', 'hl_clock', 'service', 'hl_time',
        'break_reason', 'break_reason', 'view_user_email',
        'ip_address'
    )
    search_fields = [
        'user__username', 'user__email', 'hl_clock', 'service__name', 'service__extension',
        'service__slug', 'ip_address__ip_address',
    ]

    def view_user_email(self, obj):
        return obj.user.email

    view_user_email.empty_value_display = '???'


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'hl_category', 'hl_subcategory',
                    'hl_subsubcat', 'backend_manager_config')
    search_fields = ['hl_category', 'hl_subcategory', 'hl_subsubcat']


class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'service', 'hl_time',
                    'case', 'telephone')
    search_fields = ['telephone', 'id', 'case_id']

admin.site.register(Schedule, ScheduleAdmin)
admin.site.register(DID, DIDAdmin)
admin.site.register(HelplineUser, HelplineUserAdmin)
admin.site.register(Service, ServiceAdmin)
admin.site.register(ServiceExternalURL, ServiceExternalURLAdmin)
admin.site.register(Hotdesk, HotdeskAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(Clock, ClockAdmin)
admin.site.register(Scheme, SchemeAdmin)
admin.site.register(Break, BreakAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Partner, PartnerAdmin)
admin.site.register(Dialect, DialectAdmin)
admin.site.register(SipServerConfig, SipServerConfigAdmin)
admin.site.register(TurnServerConfig, TurnServerConfigAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Contact, ContactAdmin)
admin.site.register(RecordPlay, RecordPlayAdmin)
admin.site.register(IpAddress, IpAddressAdmin)
admin.site.register(Disposition, DispositionAdmin)
admin.site.register(Case, CaseAdmin)
admin.site.register(
    BackendServerManagerConfig,
    BackendServerManagerConfigAdmin
)
