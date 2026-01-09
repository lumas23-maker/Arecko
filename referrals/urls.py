from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('post/', views.post_story, name='post_story'),
    path('share/<int:pk>/', views.share_success, name='share_success'),
    path('request-recko/', views.ask_referral, name='ask_referral'),
    path('recko/<int:pk>/', views.recko_detail, name='recko_detail'),
    path('signup/', views.signup, name='signup'),
    path('signup/business/', views.business_signup, name='business_signup'),
    path('like/<int:story_id>/', views.toggle_like, name='toggle_like'),
    path('react/<int:story_id>/', views.toggle_reaction, name='toggle_reaction'),
    path('comment/<int:story_id>/', views.add_comment, name='add_comment'),
    path('delete/<int:story_id>/', views.delete_story, name='delete_story'),
    path('account/', views.account_settings, name='account_settings'),
    path('account/delete/', views.delete_account, name='delete_account'),
    path('newsletter/', views.create_newsletter, name='create_newsletter'),
    path('newsletter/generate/', views.generate_newsletter_ai, name='generate_newsletter_ai'),
    path('business/dashboard/', views.business_dashboard, name='business_dashboard'),
    path('business/verify/<int:story_id>/', views.verify_referral, name='verify_referral'),
    path('user/<str:username>/', views.user_profile, name='user_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('api/referral-request/', views.api_referral_request, name='api_referral_request'),
    path('privacy/', views.privacy_policy, name='privacy_policy'),
    path('terms/', views.terms_of_service, name='terms_of_service'),
    path('debug-config/', views.debug_config, name='debug_config'),
]