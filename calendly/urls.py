# urls.py

from django.urls import path
from . import views as calendly_views

app_name = 'calendly'
urlpatterns = [
    # Other URL patterns...
#    path('calendly/', calendly_views.calendly_auth, name='calendly_auth'),
    path('callback', calendly_views.calendly_callback, name='calendly_callback'),
    path('events', calendly_views.get_user_events, name='get_user_events'),
    path('error', calendly_views.error_view, name='error_view'),
    path('success', calendly_views.error_view, name='success_view'),

]
