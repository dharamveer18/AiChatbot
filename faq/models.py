from django.db import models
from django.contrib.auth.models import AbstractUser


# Create your models here.
class User(AbstractUser):
    name = models.CharField(null=True,blank=True)
    email = models.EmailField(unique=True)
    
    def __str__(self):
        return self.name if self.name else "name"