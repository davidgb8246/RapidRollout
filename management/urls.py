"""
URL configuration for prueba project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, re_path

from management import views


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.create_user, name='create_user'),
    path('users/delete/<uuid:user_id>/', views.delete_user, name='delete_user'),
    
    path('projects/', views.project_list, name='project_list'),
    path('projects/create/', views.create_project, name='create_project'),
    path('projects/<uuid:project_id>/delete/', views.delete_project, name='delete_project'),
    path('projects/<uuid:project_id>/edit/', views.edit_project, name='edit_project'),
    path('projects/<uuid:project_id>/reset_secret/', views.reset_project_secret, name='reset_project_secret'),
    path('projects/<uuid:project_id>/delete_secret/', views.delete_project_secret, name='delete_project_secret'),
]
