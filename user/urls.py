from django.urls import path
from .views import register_view, login_view, logout_view,user_view,change_password_view,activate_view,delete_user_view

urlpatterns = [
    # AUTH
    path('register/', register_view, name='register'),
    path('activate/<uidb64>/<token>/', activate_view, name='activate'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    
     # USER (current user)
    path('me/', user_view, name='me'),
    path('me/password/', change_password_view, name='change_password'),
    path('me/delete/', delete_user_view, name='delete-user'),
  
   
]
