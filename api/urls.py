from django.conf.urls import url, include
from rest_framework import routers
from api import views
from django.urls import re_path, path
from helpline import views as helpline_views
from knox import views as knox_views

from api.views import CreateUserView, LoginView,\
        ManageUserView, FetchApiKeyView

router = routers.DefaultRouter()

urlpatterns = [
    path('create/', CreateUserView.as_view(), name="create"),
    path('profile/', ManageUserView.as_view(), name='profile'),
    path('login/', LoginView.as_view(), name='knox_login'),
    path('fetch_api_key', FetchApiKeyView.as_view(), name='fetch_api_key'),
    path('logout/', knox_views.LogoutView.as_view(), name='knox_logout'),
    path('logoutall/', knox_views.LogoutAllView.as_view(), name='knox_logoutall'),
    re_path('^server_settings/$', helpline_views.server_settings),
    re_path('^users/me/presence', helpline_views.update_active_status_backend),
    re_path('^users/me/presence', helpline_views.update_active_status_backend),
    re_path('^register', helpline_views.do_events_register),
    re_path('^events', helpline_views.get_events),
    re_path('^messages', helpline_views.get_messages),
    url(r'^', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]
