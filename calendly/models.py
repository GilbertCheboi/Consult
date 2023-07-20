from django.db import models
from django.contrib.auth.models import User

class AccessToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.CharField(max_length=1000)

    def __str__(self):
        return self.access_token

