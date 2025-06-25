from django.urls import path,include
from .views import *
from . import views



urlpatterns = [
    path('home/',views.home,name='home'),
    path('chatbot-api/', chatbot_api, name='chatbot_api'),
    path('chatbot2/', chatbotAPI,name='chatbot'),
    # path('signup/',views.signup,name='signup'),
    # path('',views.login_view,name="login"),
    path('new/',views.new,name='new'),
    path('response/',views.response,name="response"),
]