from django.urls import path
from .views import ExcelUploadView, QueryTableView


urlpatterns = [
    path('file/', ExcelUploadView.as_view(), name='file'),
    path('query/', QueryTableView.as_view(), name='query'),
]