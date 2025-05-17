from django.urls import path
from . import views

urlpatterns = [
    path('nl/', views.nl_view, name='nl_view'),
    path('public-files/', views.public_files_view, name='public_files_view'),
    path('public-files/download/<str:filename>/', views.download_public_file_view, name='download_public_file'),
    path('<str:tool>/', views.tool_view, name='tool_view'),
] 