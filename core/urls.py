from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 1. Django Admin Panel (using obscure path to avoid WAF blocks)
    path('arecko-dashboard/', admin.site.urls),

    # 2. Main Referral App URLs
    # This connects everything in referrals/urls.py to your main site
    path('', include('referrals.urls')),

    # 3. Built-in Authentication (Login/Logout)
    path('accounts/', include('django.contrib.auth.urls')),
]

# 4. Serving Media Files (Videos/Images) during development
# Note: In production with Cloudinary, media is served from Cloudinary CDN
# For local development without Cloudinary, serve from filesystem
if settings.DEBUG or settings.MEDIA_ROOT:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)