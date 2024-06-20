"""MongoIR URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
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
from django.contrib import admin
from django.urls import path
from MongoIRApp import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.search_documents, name='search_documents'),  # URL for the search page
    path('upload/', views.upload_document, name='upload_document'),  # URL for uploading documents
    path('multiple_term_search/', views.multiple_term_search, name='multiple_term_search'),
    path('search-results/', views.search_results, name='search_results'),
    path('document/<int:doc_id>/', views.view_document, name='view_document'),
]

from django.conf import settings
from django.conf.urls.static import static

# ... your other url patterns ...
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


