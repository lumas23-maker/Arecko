from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# User Profile for additional info
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(max_length=200, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


# Auto-create profile when user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


# Industry choices for categorization
INDUSTRY_CHOICES = [
    ('automotive', 'Automotive'),
    ('restaurant', 'Restaurant & Food'),
    ('retail', 'Retail & Shopping'),
    ('health', 'Health & Wellness'),
    ('beauty', 'Beauty & Spa'),
    ('home', 'Home Services'),
    ('professional', 'Professional Services'),
    ('fitness', 'Fitness & Sports'),
    ('entertainment', 'Entertainment'),
    ('travel', 'Travel & Hospitality'),
    ('technology', 'Technology'),
    ('education', 'Education'),
    ('other', 'Other'),
]

# Model for the business recommendations/posts
class Story(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    business_name = models.CharField(max_length=255)
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES, default='other')
    story = models.TextField()
    contact_info = models.CharField(max_length=255, blank=True, null=True, help_text="Optional: Your phone or email for the business to contact you")
    media = models.FileField(upload_to='stories/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name='liked_stories', blank=True)

    # Verification fields
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_referrals')
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.business_name} by {self.user.username}"

    # Helper to check if the uploaded media is a video
    def is_video(self):
        if self.media:
            return self.media.name.lower().endswith(('.mp4', '.mov', '.avi'))
        return False

    @staticmethod
    def get_user_status(user, business_name=None, industry=None):
        """Get user's referral status for a business or industry"""
        queryset = Story.objects.filter(user=user, is_verified=True)
        if business_name:
            queryset = queryset.filter(business_name__iexact=business_name)
        if industry:
            queryset = queryset.filter(industry=industry)

        count = queryset.count()
        if count >= 20:
            return 'platinum', count
        elif count >= 15:
            return 'gold', count
        elif count >= 10:
            return 'silver', count
        elif count >= 5:
            return 'bronze', count
        return None, count

# Model for comments on a specific story
class Comment(models.Model):
    story = models.ForeignKey(Story, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.story.business_name}"

# NEW: Model to track referral requests sent to customers
class ReferralRequest(models.Model):
    business_user = models.ForeignKey(User, on_delete=models.CASCADE)
    customer_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Request to {self.customer_email} from {self.business_user.username}"


# Reaction types
REACTION_TYPES = [
    ('like', '👍'),
    ('love', '❤️'),
    ('haha', '😂'),
    ('wow', '😮'),
    ('sad', '😢'),
    ('angry', '😡'),
]


# Reactions on posts
class Reaction(models.Model):
    story = models.ForeignKey('Story', related_name='reactions', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=10, choices=REACTION_TYPES, default='like')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['story', 'user']  # One reaction per user per story

    def __str__(self):
        return f"{self.user.username} reacted {self.reaction_type} to {self.story.business_name}"

    @staticmethod
    def get_emoji(reaction_type):
        emojis = dict(REACTION_TYPES)
        return emojis.get(reaction_type, '👍')


# API Key for CRM integration
class APIKey(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    key = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    requests_today = models.IntegerField(default=0)
    last_request_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"API Key for {self.user.username}"

    @staticmethod
    def generate_key():
        import secrets
        return secrets.token_hex(32)

    def check_rate_limit(self, max_requests=500):
        """Check if rate limit exceeded. Returns (allowed, remaining)"""
        from django.utils import timezone
        today = timezone.now().date()

        if self.last_request_date != today:
            # Reset counter for new day
            self.requests_today = 0
            self.last_request_date = today

        if self.requests_today >= max_requests:
            return False, 0

        self.requests_today += 1
        self.save()
        return True, max_requests - self.requests_today