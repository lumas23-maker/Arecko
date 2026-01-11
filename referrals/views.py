import os
import json
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Story, Comment, ReferralRequest, Profile, APIKey, Reaction, REACTION_TYPES
import csv
import re
import io

# Debug endpoint to check Cloudinary config
def debug_config(request):
    from django.conf import settings
    return JsonResponse({
        'cloudinary_cloud_name': os.environ.get('CLOUDINARY_CLOUD_NAME', 'NOT SET'),
        'default_file_storage': getattr(settings, 'DEFAULT_FILE_STORAGE', 'NOT SET'),
        'cloudinary_storage': getattr(settings, 'CLOUDINARY_STORAGE', {}),
    })

# 1. Main Feed: Displays all video stories/Reckos with pagination
def home(request):
    from django.core.paginator import Paginator

    stories_list = Story.objects.select_related('user').prefetch_related('user__profile').order_by('-created_at')
    paginator = Paginator(stories_list, 10)  # 10 posts per page

    page_number = request.GET.get('page', 1)
    stories = paginator.get_page(page_number)

    return render(request, 'referrals/home.html', {'stories': stories, 'paginator': paginator})

# 2. Detailed View: Individual Recko page
def recko_detail(request, pk):
    story = get_object_or_404(Story, pk=pk)
    page_url = request.build_absolute_uri()
    media_url = request.build_absolute_uri(story.media.url) if story.media else None
    return render(request, 'referrals/recko_detail.html', {
        'story': story,
        'page_url': page_url,
        'media_url': media_url
    })

# 3. Post a Story: Handles uploading new video recommendations (no login required)
def post_story(request):
    # Business accounts cannot post Reckos - they can only ask for them
    if request.user.is_authenticated and request.user.is_staff:
        messages.error(request, "Business accounts cannot post Reckos. Use 'Ask for Recko' to request referrals from customers.")
        return redirect('ask_referral')

    if request.method == 'POST':
        business_name = request.POST.get('business_name')
        industry = request.POST.get('industry', 'other')
        contact_info = request.POST.get('contact_info', '').strip() or None
        story_text = request.POST.get('story')
        media = request.FILES.get('media')
        guest_name = request.POST.get('guest_name', '').strip() or None

        if business_name and story_text:
            # Create story with user if logged in, otherwise use guest_name
            if request.user.is_authenticated:
                story = Story.objects.create(
                    user=request.user,
                    business_name=business_name,
                    industry=industry,
                    contact_info=contact_info,
                    story=story_text,
                    media=media
                )
            else:
                story = Story.objects.create(
                    guest_name=guest_name or "Anonymous",
                    business_name=business_name,
                    industry=industry,
                    contact_info=contact_info,
                    story=story_text,
                    media=media
                )
            # Notify businesses about new referral (find staff users with matching business name)
            notify_business_of_referral(story)
            return redirect('share_success', pk=story.pk)
    return render(request, 'referrals/post_story.html', {'user_is_authenticated': request.user.is_authenticated})

# 3b. Share Success: Shows social share buttons after posting (no login required)
def share_success(request, pk):
    story = get_object_or_404(Story, pk=pk)
    share_url = request.build_absolute_uri(f'/recko/{story.pk}/')
    return render(request, 'referrals/share_success.html', {
        'story': story,
        'share_url': share_url
    })

# 4. Ask for Referral: Sends automated emails to customers
@login_required
def ask_referral(request):
    # Get or create API key for this user
    api_key_obj, _ = APIKey.objects.get_or_create(
        user=request.user,
        defaults={'key': APIKey.generate_key()}
    )

    if request.method == 'POST':
        mode = request.POST.get('mode', 'single')

        # Generate new API key
        if mode == 'generate_api_key':
            api_key_obj.key = APIKey.generate_key()
            api_key_obj.save()
            messages.success(request, "New API key generated!")
            return redirect('ask_referral')

        # Single email mode
        elif mode == 'single':
            email_addr = request.POST.get('customer_email')
            personal_message = request.POST.get('personal_message', '').strip()
            if email_addr:
                send_referral_email(request.user, email_addr, personal_message)
                messages.success(request, f"Arecko-mendation request sent to {email_addr}!")
                return redirect('ask_referral')

        # Bulk email mode
        elif mode == 'bulk':
            emails = []
            personal_message = request.POST.get('bulk_message', '').strip()

            # Parse pasted emails
            bulk_emails = request.POST.get('bulk_emails', '')
            if bulk_emails:
                # Split by commas, newlines, spaces, or semicolons
                email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                emails.extend(re.findall(email_pattern, bulk_emails))

            # Parse CSV file
            csv_file = request.FILES.get('csv_file')
            if csv_file:
                try:
                    decoded = csv_file.read().decode('utf-8')
                    reader = csv.DictReader(io.StringIO(decoded))
                    for row in reader:
                        # Look for email column (case-insensitive)
                        for key in row:
                            if 'email' in key.lower():
                                email = row[key].strip()
                                if re.match(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', email):
                                    emails.append(email)
                                break
                except Exception as e:
                    messages.error(request, f"Error reading CSV: {str(e)}")

            # Remove duplicates and send
            emails = list(set(emails))
            if emails:
                sent_count = 0
                for email in emails:
                    try:
                        send_referral_email(request.user, email, personal_message)
                        sent_count += 1
                    except Exception as e:
                        print(f"Failed to send to {email}: {e}")
                messages.success(request, f"Sent {sent_count} Arecko-mendation requests!")
            else:
                messages.error(request, "No valid emails found.")
            return redirect('ask_referral')

    referral_requests = ReferralRequest.objects.filter(business_user=request.user).order_by('-created_at')
    return render(request, 'referrals/ask_referral.html', {
        'referral_requests': referral_requests,
        'api_key': api_key_obj.key
    })


def send_referral_email(business_user, email_addr, personal_message=''):
    """Helper function to send a single referral request email"""
    # Save request record
    ReferralRequest.objects.create(business_user=business_user, customer_email=email_addr)

    business_name = business_user.first_name or business_user.username

    # Prepare Email Content
    subject = f"Thank you from {business_name} - We'd love your Arecko-mendation!"
    text_content = f"{business_name} would like to thank you for doing business with us. Please leave us an Arecko-mendation at: https://www.arecko.com/post/"
    html_content = render_to_string('referrals/newsletter_email.html', {
        'business_name': business_name,
        'referral_url': "https://www.arecko.com/post/",
        'personal_message': personal_message
    })

    # Use DEFAULT_FROM_EMAIL for "from" address, with Reply-To set to business user's email
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)
    reply_to = [business_user.email] if business_user.email else []

    # Send the automated email
    msg = EmailMultiAlternatives(subject, text_content, from_email, [email_addr], reply_to=reply_to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()

# 5. Interaction Logic: Emoji reactions
@login_required
def toggle_reaction(request, story_id):
    story = get_object_or_404(Story, id=story_id)
    reaction_type = request.GET.get('type', 'like')

    # Validate reaction type
    valid_types = [r[0] for r in REACTION_TYPES]
    if reaction_type not in valid_types:
        reaction_type = 'like'

    # Check if user already reacted
    existing = Reaction.objects.filter(story=story, user=request.user).first()

    if existing:
        if existing.reaction_type == reaction_type:
            # Same reaction - remove it
            existing.delete()
        else:
            # Different reaction - update it
            existing.reaction_type = reaction_type
            existing.save()
    else:
        # New reaction
        Reaction.objects.create(story=story, user=request.user, reaction_type=reaction_type)

    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        reactions = story.reactions.all()
        reaction_counts = {}
        for r in reactions:
            emoji = Reaction.get_emoji(r.reaction_type)
            reaction_counts[emoji] = reaction_counts.get(emoji, 0) + 1

        user_reaction = Reaction.objects.filter(story=story, user=request.user).first()

        return JsonResponse({
            'success': True,
            'total': reactions.count(),
            'counts': reaction_counts,
            'user_reaction': user_reaction.reaction_type if user_reaction else None
        })

    return redirect('home')


# Legacy like support (redirects to reaction)
@login_required
def toggle_like(request, story_id):
    return toggle_reaction(request, story_id)

@login_required
def delete_story(request, story_id):
    story = get_object_or_404(Story, id=story_id)
    business_name = request.user.first_name or request.user.username

    # Allow deletion if: user owns the story, is superuser, or is a business whose name matches
    can_delete = (
        request.user == story.user or
        request.user.is_superuser or
        (request.user.is_staff and business_name.lower() in story.business_name.lower())
    )

    if can_delete:
        story.delete()
        messages.success(request, "Recko deleted successfully.")
    else:
        messages.error(request, "You don't have permission to delete this Recko.")

    # Redirect back to appropriate page
    next_url = request.GET.get('next', 'home')
    if next_url == 'dashboard':
        return redirect('business_dashboard')
    return redirect('home')

@login_required
def add_comment(request, story_id):
    story = get_object_or_404(Story, id=story_id)
    if request.method == 'POST':
        text = request.POST.get('text')
        if text:
            Comment.objects.create(story=story, user=request.user, text=text)
    return redirect('home')

# 5b. Account Settings
@login_required
def account_settings(request):
    return render(request, 'referrals/account_settings.html')

# 5c. Delete Account
@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        # Delete all user's stories first
        Story.objects.filter(user=user).delete()
        # Delete the user account
        user.delete()
        messages.success(request, "Your account has been deleted. We're sorry to see you go!")
        return redirect('home')
    return redirect('account_settings')

# 6. User Signup (Regular Users)
def signup(request):
    if request.method == 'POST':
        display_name = request.POST.get('display_name', '').strip()
        username = request.POST.get('username', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        # Validation
        if not all([display_name, username, password1, password2]):
            messages.error(request, "All fields are required.")
            return render(request, 'registration/signup.html')

        if password1 != password2:
            messages.error(request, "Passwords don't match.")
            return render(request, 'registration/signup.html')

        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, 'registration/signup.html')

        from django.contrib.auth.models import User
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return render(request, 'registration/signup.html')

        # Create user
        user = User.objects.create_user(username=username, password=password1)
        user.first_name = display_name
        user.save()

        messages.success(request, "Account created! You can now log in.")
        return redirect('login')

    return render(request, 'registration/signup.html')

# 6b. Business Signup (Business Accounts)
def business_signup(request):
    if request.method == 'POST':
        business_name = request.POST.get('business_name', '').strip()
        username = request.POST.get('username', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        # Validation
        if not all([business_name, username, password1, password2]):
            messages.error(request, "All fields are required.")
            return render(request, 'registration/business_signup.html')

        if password1 != password2:
            messages.error(request, "Passwords don't match.")
            return render(request, 'registration/business_signup.html')

        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, 'registration/business_signup.html')

        from django.contrib.auth.models import User
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return render(request, 'registration/business_signup.html')

        # Create business user
        user = User.objects.create_user(username=username, password=password1)
        user.first_name = business_name
        user.is_staff = True  # Business account
        user.save()

        messages.success(request, "Business account created! You can now log in.")
        return redirect('login')

    return render(request, 'registration/business_signup.html')

# 7. Newsletter: Create and send customized newsletters
@login_required
def create_newsletter(request):
    if request.method == 'POST':
        content = request.POST.get('content')
        recipients = request.POST.get('recipients', '')

        if content and recipients:
            # Parse recipient emails
            email_list = [email.strip() for email in recipients.split(',') if email.strip()]

            if email_list:
                # Prepare newsletter email
                subject = f"Newsletter from {request.user.username}"
                text_content = content
                html_content = render_to_string('referrals/newsletter_template.html', {
                    'business_name': request.user.username,
                    'content': content
                })

                # Send to all recipients with Reply-To set to sender's email
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)
                reply_to = [request.user.email] if request.user.email else []

                for email_addr in email_list:
                    try:
                        msg = EmailMultiAlternatives(subject, text_content, from_email, [email_addr], reply_to=reply_to)
                        msg.attach_alternative(html_content, "text/html")
                        msg.send()
                    except Exception as e:
                        print(f"Failed to send to {email_addr}: {e}")

                messages.success(request, f"Newsletter sent to {len(email_list)} recipient(s)!")
                return redirect('create_newsletter')

    return render(request, 'referrals/create_newsletter.html')

# 8. AI Newsletter Generator (using Hugging Face free API)
@login_required
def generate_newsletter_ai(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            topic = data.get('topic', '')
            key_points = data.get('key_points', '')
            tone = data.get('tone', 'professional')
            business_name = data.get('business_name', 'Our Business')

            # Build the prompt
            tone_descriptions = {
                'professional': 'professional and polished',
                'friendly': 'friendly, warm, and casual',
                'excited': 'excited, energetic, and enthusiastic',
                'grateful': 'grateful, appreciative, and heartfelt'
            }
            tone_desc = tone_descriptions.get(tone, 'professional')

            prompt = f"""Write a {tone_desc} business newsletter for {business_name} about: {topic}."""
            if key_points:
                prompt += f" Include these key points: {key_points}."
            prompt += " Keep it concise (3-4 paragraphs). Do not include subject line or headers, just the body content."

            # Try Hugging Face free inference API
            try:
                response = requests.post(
                    "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2",
                    headers={"Content-Type": "application/json"},
                    json={
                        "inputs": f"<s>[INST] {prompt} [/INST]",
                        "parameters": {"max_new_tokens": 500, "temperature": 0.7}
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        generated = result[0].get('generated_text', '')
                        # Extract just the response after [/INST]
                        if '[/INST]' in generated:
                            generated = generated.split('[/INST]')[-1].strip()
                        return JsonResponse({'content': generated})
            except Exception as api_error:
                print(f"Hugging Face API error: {api_error}")

            # Fallback: Generate a simple template-based newsletter
            fallback_content = generate_fallback_newsletter(business_name, topic, key_points, tone)
            return JsonResponse({'content': fallback_content})

        except Exception as e:
            print(f"Error generating newsletter: {e}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)

def generate_fallback_newsletter(business_name, topic, key_points, tone):
    """Generate a simple template-based newsletter as fallback"""
    greetings = {
        'professional': 'Dear Valued Customer,',
        'friendly': 'Hey there! 👋',
        'excited': 'Great news! 🎉',
        'grateful': 'We are so thankful for you! 🙏'
    }
    closings = {
        'professional': 'Best regards,',
        'friendly': 'Cheers,',
        'excited': "Can't wait to see you!",
        'grateful': 'With sincere gratitude,'
    }

    greeting = greetings.get(tone, greetings['professional'])
    closing = closings.get(tone, closings['professional'])

    content = f"""{greeting}

We're excited to share some news with you about {topic}!

At {business_name}, we're always working to bring you the best experience possible. {f"Here's what you need to know: {key_points}" if key_points else "We have some exciting updates we'd love to share with you."}

Thank you for being part of our community. We truly appreciate your continued support and trust in us.

{closing}
{business_name}"""

    return content


# 9. Notify Business of New Referral
def notify_business_of_referral(story):
    """Send email notification to business accounts when a new referral is made for their business"""
    from django.contrib.auth.models import User

    # Find business accounts (staff users) whose name matches the business
    business_users = User.objects.filter(
        is_staff=True,
        first_name__icontains=story.business_name
    ) | User.objects.filter(
        is_staff=True,
        username__icontains=story.business_name
    )

    for business_user in business_users:
        if business_user.email:
            try:
                referrer_name = story.get_poster_name()
                subject = f"New Arecko-mendation for {story.business_name}!"
                text_content = f"A new referral has been posted for your business by {referrer_name}. Log in to verify it!"
                html_content = render_to_string('referrals/referral_notification.html', {
                    'business_name': story.business_name,
                    'referrer_name': referrer_name,
                    'story': story,
                    'verify_url': 'https://www.arecko.com/business/dashboard/'
                })

                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)
                msg = EmailMultiAlternatives(subject, text_content, from_email, [business_user.email])
                msg.attach_alternative(html_content, "text/html")
                msg.send()
            except Exception as e:
                print(f"Failed to notify {business_user.email}: {e}")


# 10. Business Dashboard: View and verify referrals
@login_required
def business_dashboard(request):
    """Dashboard for businesses to view and verify referrals"""
    if not request.user.is_staff:
        messages.error(request, "Access denied. Business accounts only.")
        return redirect('home')

    business_name = request.user.first_name or request.user.username

    # Get pending (unverified) referrals for this business
    pending_referrals = Story.objects.filter(
        business_name__icontains=business_name,
        is_verified=False
    ).order_by('-created_at')

    # Get verified referrals
    verified_referrals = Story.objects.filter(
        business_name__icontains=business_name,
        is_verified=True
    ).order_by('-verified_at')

    return render(request, 'referrals/business_dashboard.html', {
        'pending_referrals': pending_referrals,
        'verified_referrals': verified_referrals,
        'business_name': business_name
    })


# 11. Verify Referral: Mark a referral as verified
@login_required
def verify_referral(request, story_id):
    """Verify a referral (business accounts only)"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Access denied'}, status=403)

    from django.utils import timezone

    story = get_object_or_404(Story, id=story_id)
    story.is_verified = True
    story.verified_by = request.user
    story.verified_at = timezone.now()
    story.save()

    # Check if user earned a new status
    user_status, count = Story.get_user_status(story.user, business_name=story.business_name)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'user_status': user_status,
            'verified_count': count
        })

    messages.success(request, f"Referral verified! {story.user.first_name or story.user.username} now has {count} verified referrals.")
    return redirect('business_dashboard')


# 12. User Profile with Status Badges
def user_profile(request, username):
    """View user profile with their referral status badges"""
    from django.contrib.auth.models import User

    profile_user = get_object_or_404(User, username=username)

    # Get or create profile
    profile, created = Profile.objects.get_or_create(user=profile_user)

    # Get all verified referrals for this user
    verified_stories = Story.objects.filter(user=profile_user, is_verified=True)

    # Calculate status for each business they've referred
    business_statuses = {}
    businesses = verified_stories.values_list('business_name', flat=True).distinct()
    for business in businesses:
        status, count = Story.get_user_status(profile_user, business_name=business)
        if status:
            business_statuses[business] = {'status': status, 'count': count}

    # Calculate status for each industry
    industry_statuses = {}
    industries = verified_stories.values_list('industry', flat=True).distinct()
    for industry in industries:
        status, count = Story.get_user_status(profile_user, industry=industry)
        if status:
            industry_statuses[industry] = {'status': status, 'count': count}

    # Overall status
    overall_status, overall_count = Story.get_user_status(profile_user)

    # Get recent posts
    recent_stories = Story.objects.filter(user=profile_user).order_by('-created_at')[:10]

    return render(request, 'referrals/user_profile.html', {
        'profile_user': profile_user,
        'profile': profile,
        'business_statuses': business_statuses,
        'industry_statuses': industry_statuses,
        'overall_status': overall_status,
        'overall_count': overall_count,
        'recent_stories': recent_stories
    })


# 13. Edit Profile: Allow users to update their profile
@login_required
def edit_profile(request):
    # Get or create profile for user
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # Update user fields
        display_name = request.POST.get('display_name', '').strip()
        email = request.POST.get('email', '').strip()
        bio = request.POST.get('bio', '').strip()
        location = request.POST.get('location', '').strip()
        website = request.POST.get('website', '').strip()

        # Update User model
        if display_name:
            request.user.first_name = display_name
        if email:
            request.user.email = email
        request.user.save()

        # Update Profile model
        profile.bio = bio
        profile.location = location
        profile.website = website

        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']

        profile.save()

        messages.success(request, "Profile updated successfully!")
        return redirect('user_profile', username=request.user.username)

    return render(request, 'referrals/edit_profile.html', {
        'profile': profile
    })


# 14. Legal Pages
def privacy_policy(request):
    return render(request, 'referrals/privacy_policy.html')

def terms_of_service(request):
    return render(request, 'referrals/terms.html')


# 15. API Endpoint for CRM Integration
@csrf_exempt
def api_referral_request(request):
    """API endpoint for sending referral requests from CRM systems"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # Validate API key
    api_key = data.get('api_key')
    if not api_key:
        return JsonResponse({'error': 'API key required'}, status=401)

    try:
        api_key_obj = APIKey.objects.get(key=api_key)
        business_user = api_key_obj.user
    except APIKey.DoesNotExist:
        return JsonResponse({'error': 'Invalid API key'}, status=401)

    # Check rate limit (500 requests per day)
    allowed, remaining = api_key_obj.check_rate_limit(max_requests=500)
    if not allowed:
        return JsonResponse({
            'error': 'Rate limit exceeded. Maximum 500 requests per day.',
            'retry_after': 'tomorrow'
        }, status=429)

    # Get emails
    emails = data.get('emails', [])
    if isinstance(emails, str):
        emails = [emails]

    if not emails:
        return JsonResponse({'error': 'No emails provided'}, status=400)

    # Validate and send
    personal_message = data.get('message', '')
    sent_count = 0
    failed = []

    for email in emails:
        # Basic email validation
        if not re.match(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', email):
            failed.append({'email': email, 'reason': 'Invalid email format'})
            continue

        try:
            send_referral_email(business_user, email, personal_message)
            sent_count += 1
        except Exception as e:
            failed.append({'email': email, 'reason': str(e)})

    return JsonResponse({
        'success': True,
        'sent': sent_count,
        'failed': failed,
        'total': len(emails),
        'rate_limit_remaining': remaining
    })