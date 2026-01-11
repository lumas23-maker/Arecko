# Generated manually for video thumbnail support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('referrals', '0015_allow_anonymous_posting'),
    ]

    operations = [
        migrations.AddField(
            model_name='story',
            name='thumbnail',
            field=models.ImageField(blank=True, null=True, upload_to='thumbnails/'),
        ),
    ]
