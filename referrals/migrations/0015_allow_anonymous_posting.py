# Generated manually for anonymous posting support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('referrals', '0014_apikey_last_request_date_apikey_requests_today'),
    ]

    operations = [
        migrations.AlterField(
            model_name='story',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.CASCADE, to='auth.user'),
        ),
        migrations.AddField(
            model_name='story',
            name='guest_name',
            field=models.CharField(blank=True, help_text='Name for anonymous posters', max_length=100, null=True),
        ),
    ]
