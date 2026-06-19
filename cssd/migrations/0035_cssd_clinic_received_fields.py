
# Generated manually for CSSD clinic confirmation fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cssd', '0034_inquirymessage_requestattachment'),
    ]

    operations = [
        migrations.AddField(
            model_name='cssdrequestitem',
            name='quantity_received_by_clinic',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='cssdrequestitem',
            name='clinic_comment',
            field=models.TextField(blank=True),
        ),
    ]
