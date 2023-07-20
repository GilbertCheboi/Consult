"""Zerxis Social Media URLS"""
from django.conf.urls import include
from django.urls import re_path, path

from zerxis import views

urlpatterns = [
    re_path(r'^$', views.social_dashboard, name='social_dashboard'),

    # TWITTER
    re_path(r'^twitter/(?P<uid>\w+)/$', views.twitter_home, name='twitter_home'),
    re_path(r'^post_tweet/(?P<uid>\w+)/$', views.post_tweet, name='post_tweet'),
    re_path(r'^like_tweet/(?P<uid>\w+)/$',
            views.like_tweet, name='like_tweet'),
    re_path(r'^twitter/home_timeline/(?P<uid>\w+)/$', views.twitter_home_timeline,
            name='twitter_home_timeline'),
    re_path(r'^twitter/user_timeline/(?P<uid>\w+)/$', views.twitter_user_timeline,
            name='twitter_user_timeline'),
    re_path(r'^twitter/mentions_timeline/(?P<uid>\w+)/$', views.twitter_mentions_timeline,
            name='twitter_mentions_timeline'),
    re_path(r'^twitter/user/(?P<user_name>\w+)/(?P<uid>\w+)/$',
            views.twitter_user_stream, name='twitter_user_stream'),
    re_path(r'^twitter/user/(?P<user_name>\w+)/(?P<uid>\w+)/following/$',
            views.twitter_user_friends, name='twitter_user_friends'),
    re_path(r'^twitter/user/(?P<user_name>\w+)/(?P<uid>\w+)/followers/$',
            views.twitter_user_followers, name='twitter_user_followers'),
    re_path(r'^login/$', views.login, name='zerxis_login'),
    re_path(r'^twitter/search/(?P<uid>\w+)/$', views.search, name='twitter_search'),
    re_path(r'^twitter/mentions/(?P<uid>\w+)/$',
            views.user_mentions, name='twitter_user_mentions'),
    re_path(r'^twitter/directs/(?P<uid>\w+)/$',
            views.user_directs, name='twitter_direct_message'),

    # FACEBOOK

    re_path(r'^facebook/$', views.facebook_home, name='facebook_home'),
    re_path(r'^facebook/home_timeline/(?P<uid>\w+)/$', views.twitter_home_timeline,
            name='facebook_home_timeline'),
    re_path(r'^facebook/user_timeline/(?P<uid>\w+)/$', views.twitter_user_timeline,
            name='facebook_user_timeline'),
    re_path(r'^facebook/mentions_timeline/(?P<uid>\w+)/$', views.twitter_mentions_timeline,
            name='facebook_mentions_timeline'),
    re_path(r'^facebook/user/(?P<user_name>\w+)/$',
            views.twitter_user_stream, name='facebook_user_stream'),
]
