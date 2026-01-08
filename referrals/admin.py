from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Story, Comment, ReferralRequest, Profile


# Inline Profile in User Admin
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'


# Custom User Admin with Profile
class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name')
    actions = ['make_business', 'make_regular_user', 'deactivate_users', 'activate_users']

    def make_business(self, request, queryset):
        queryset.update(is_staff=True)
        self.message_user(request, f"{queryset.count()} user(s) converted to business accounts.")
    make_business.short_description = "Convert to Business Account"

    def make_regular_user(self, request, queryset):
        queryset.update(is_staff=False)
        self.message_user(request, f"{queryset.count()} user(s) converted to regular accounts.")
    make_regular_user.short_description = "Convert to Regular User"

    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} user(s) deactivated.")
    deactivate_users.short_description = "Deactivate selected users"

    def activate_users(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} user(s) activated.")
    activate_users.short_description = "Activate selected users"


# Unregister default User admin and register custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# 1. Manage Business Recommendations (Reckos)
@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'user', 'industry', 'is_verified', 'created_at')
    search_fields = ('business_name', 'story', 'user__username', 'user__first_name')
    list_filter = ('is_verified', 'industry', 'created_at')
    readonly_fields = ('created_at', 'verified_at')
    actions = ['verify_referrals', 'unverify_referrals', 'delete_selected']

    fieldsets = (
        ('Content', {
            'fields': ('user', 'business_name', 'industry', 'story', 'media')
        }),
        ('Contact', {
            'fields': ('contact_info',),
            'classes': ('collapse',)
        }),
        ('Verification', {
            'fields': ('is_verified', 'verified_by', 'verified_at')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def verify_referrals(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_verified=True, verified_by=request.user, verified_at=timezone.now())
        self.message_user(request, f"{queryset.count()} referral(s) verified.")
    verify_referrals.short_description = "Mark as Verified"

    def unverify_referrals(self, request, queryset):
        queryset.update(is_verified=False, verified_by=None, verified_at=None)
        self.message_user(request, f"{queryset.count()} referral(s) unverified.")
    unverify_referrals.short_description = "Mark as Unverified"


# 2. Manage Customer Comments
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'story', 'text_preview', 'created_at')
    search_fields = ('text', 'user__username', 'story__business_name')
    list_filter = ('created_at',)

    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Comment'


# 3. Manage Referral Requests
@admin.register(ReferralRequest)
class ReferralRequestAdmin(admin.ModelAdmin):
    list_display = ('customer_email', 'business_user', 'created_at')
    search_fields = ('customer_email', 'business_user__username')
    list_filter = ('created_at',)


# 4. Manage User Profiles
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'has_picture')
    search_fields = ('user__username', 'user__email', 'location', 'bio')
    list_filter = ('location',)

    def has_picture(self, obj):
        return bool(obj.profile_picture)
    has_picture.boolean = True
    has_picture.short_description = 'Has Profile Picture'


# Customize admin site
admin.site.site_header = "Arecko Admin"
admin.site.site_title = "Arecko Admin Portal"
admin.site.index_title = "Welcome to Arecko Administration"
