from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from avatar.models import Avatar
from avatar.providers import DefaultAvatarProvider

# django imports
from django.contrib.auth import login
from django.views.decorators.csrf import csrf_exempt
from django.contrib.sites.shortcuts import get_current_site

# rest_framework imports
from rest_framework import generics, authentication, permissions
from rest_framework.settings import api_settings
from rest_framework.authtoken.serializers import AuthTokenSerializer

# knox imports
from knox.views import LoginView as KnoxLoginView
from knox.auth import TokenAuthentication

from rest_framework.authentication import SessionAuthentication


from api.serializers import UserSerializer, GroupSerializer,\
        HelplineUserSerializer, HelplineCaseSerializer,\
        SipServerConfigSerializer, HelplineContactSerializer,\
	AuthSerializer, FetchApiKeySerializer

from helpline.models import HelplineUser, Case, SipServerConfig,\
        Contact

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

class HelplineUserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows helpline users to be viewed or edited.
    """
    queryset = HelplineUser.objects.all()
    serializer_class = HelplineUserSerializer

class HelplineCaseViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows helpline cases to be viewed or edited.
    """
    queryset = Case.objects.all()
    serializer_class = HelplineCaseSerializer

class SipServerConfigViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows asterisk configs to be viewed or edited.
    """
    queryset = SipServerConfig.objects.all()
    serializer_class = SipServerConfigSerializer

class ContactViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows helpline contacts to be viewed or edited.
    """
    queryset = Contact.objects.all()
    serializer_class = HelplineContactSerializer


class CreateUserView(generics.CreateAPIView):
    # Create user API view
    serializer_class = UserSerializer


class LoginView(KnoxLoginView):
    # login view extending KnoxLoginView
    serializer_class = AuthSerializer
    permission_classes = (permissions.AllowAny,)

    @csrf_exempt
    def post(self, request, format=None):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return super(LoginView, self).post(request, format=None)


class FetchApiKeyView(KnoxLoginView):
    # login view extending KnoxLoginView
    serializer_class = FetchApiKeySerializer
    permission_classes = (permissions.AllowAny,)

    @csrf_exempt
    def post(self, request, format=None):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return super(FetchApiKeyView, self).post(request, format=None)




class ManageUserView(generics.RetrieveUpdateAPIView):
    """Manage the authenticated user"""
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        """Retrieve and return authenticated user"""
        user = self.request.user
        avatar_url = DefaultAvatarProvider.get_avatar_url(user, 128)
        current_site = get_current_site(self.request)
        avatar_uri = f"https://{current_site}{avatar_url}"
        data = {
            "username": user.username,
            "email": user.email,
            "id":user.pk,
            "created_timestamp": str(user.date_joined),
            "last_login": str(user.last_login.strftime('%s')),
            "full_name": user.get_full_name(),
            "avatar_url": avatar_uri,
            "cover_image": "https://zerxis.com/assets/img/logo.png",
        }
        return data
