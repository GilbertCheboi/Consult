from django.contrib.auth.models import User, Group
from rest_framework import serializers
import urllib.parse

from helpline.models import HelplineUser, Case, SipServerConfig,\
        Contact


from django.contrib.auth.models import User
from django.contrib.auth import  authenticate

import requests
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    '''serializer for the user object'''
    avatar_url = serializers.CharField()
    full_name = serializers.CharField()
    cover_image = serializers.CharField()
    class Meta:
        model = User
        fields = (
            'username',
            'password',
            'date_joined',
            'email',
            'avatar_url',
            'full_name',
            'last_login',
            'cover_image',
        )
        extra_kwargs = {'password': {'write_only': True, 'min_length': 5}}

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class AuthSerializer(serializers.Serializer):
    '''serializer for the user authentication object'''
    username = serializers.CharField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False
    )
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        user = authenticate(
            request=self.context.get('request'),
            username=username,
            password=password
        )

        if not user:
            msg = ('Unable to authenticate with provided credentials')
            raise serializers.ValidationError(msg, code='authentication')

        attrs['user'] = user
        return


class FetchApiKeySerializer(serializers.Serializer):
    '''serializer for the user authentication object'''
    username = serializers.CharField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False
    )
    def validate(self, attrs):

        body = attrs.get('body')
        queryStr = body.get('params')
        params = urllib.parse.parse_qs(queryStr)
        username = "mary" # params.get('username')
        password = "nitronitro" # params.get('password')

        user = authenticate(
            request=self.context.get('request'),
            username=username,
            password=password
        )

        if not user:
            msg = ('Unable to authenticate with provided credentials')
            raise serializers.ValidationError(msg, code='authentication')

        attrs['user'] = user
        return


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')

class HelplineUserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = HelplineUser
        fields = ('url', 'user', 'hl_auth', 'hl_exten', 'case', 'hl_status')

class HelplineCaseSerializer(serializers.HyperlinkedModelSerializer):
    contact = serializers.HyperlinkedIdentityField(view_name='contact.hl_contact')
    user = serializers.HyperlinkedIdentityField(view_name='user.username')
    class Meta:
        model = Case
        fields = (
            'url', 'hl_case', 'contact', 'hl_unique', 'hl_disposition',
            'user', 'hl_data', 'hl_time', 'instance', 'status'
        )

class SipServerConfigSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = SipServerConfig
        fields = ('name', 'sip_host', 'sip_domain', 'sip_port')


class HelplineContactSerializer(serializers.HyperlinkedModelSerializer):
    """Contact serializer"""
    class Meta:
        model = Contact
        fields = ('url', 'hl_contact', 'phone', 'created_on', 'created_by', 'hl_status', 'is_active')
