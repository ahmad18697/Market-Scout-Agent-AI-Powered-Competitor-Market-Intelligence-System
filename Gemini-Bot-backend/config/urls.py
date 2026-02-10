from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("text_bot.urls")),
    path("", include("image_bot.urls")),
    path("", include("pdf_chat.urls")),
]

