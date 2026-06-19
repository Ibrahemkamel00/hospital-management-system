from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cssd', '0038_alter_infectioncleaningassignment_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='infectioncleaningtask',
            name='surface_cleaning_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='infectioncleaningtask',
            name='chair_cleaning_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='infectioncleaningtask',
            name='spittoon_cleaning_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='infectioncleaningtask',
            name='suction_filter_cleaning_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='infectioncleaningtask',
            name='handwash_basin_cleaning_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='infectioncleaningtask',
            name='ppe_drawers_refill_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='infectioncleaningtask',
            name='soap_refill_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='infectioncleaningtask',
            name='sanitizer_refill_reason',
            field=models.TextField(blank=True),
        ),
    ]
