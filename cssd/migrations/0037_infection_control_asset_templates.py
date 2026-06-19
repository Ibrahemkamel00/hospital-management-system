from django.db import migrations, models
import django.db.models.deletion
import django.db.models


DEFAULT_ITEMS = [
    ('surface_cleaning', 'تنظيف وتطهير الأسطح'),
    ('chair_cleaning', 'تنظيف وتطهير كرسي الأسنان'),
    ('spittoon_cleaning', 'تنظيف وتطهير مصفاة المبصقة'),
    ('suction_filter_cleaning', 'تنظيف وتطهير فلاتر وحدات الشفط'),
    ('handwash_basin_cleaning', 'تنظيف وتطهير حوض غسل اليدين'),
    ('ppe_drawers_refill', 'تعبئة الأدراج بأدوات الحماية الشخصية'),
    ('soap_refill', 'تعبئة حاويات الصابون'),
    ('sanitizer_refill', 'تعبئة حاويات مطهر اليدين'),
]


def create_default_template(apps, schema_editor):
    Template = apps.get_model('cssd', 'InfectionProcedureTemplate')
    Item = apps.get_model('cssd', 'InfectionProcedureTemplateItem')
    template, _ = Template.objects.get_or_create(
        name='Dental Unit Cleaning Procedure',
        defaults={'is_active': True}
    )
    for index, (field_name, label) in enumerate(DEFAULT_ITEMS, start=1):
        Item.objects.get_or_create(
            template=template,
            field_name=field_name,
            defaults={
                'label': label,
                'sort_order': index,
                'is_active': True,
            }
        )


class Migration(migrations.Migration):

    dependencies = [
        ('cssd', '0036_infectioncleaningassignment_infectioncleaningtask'),
    ]

    operations = [
        migrations.CreateModel(
            name='InfectionProcedureTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='Dental Unit Cleaning Procedure', max_length=200)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='InfectionProcedureTemplateItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_name', models.CharField(choices=[('surface_cleaning', 'تنظيف وتطهير الأسطح'), ('chair_cleaning', 'تنظيف وتطهير كرسي الأسنان'), ('spittoon_cleaning', 'تنظيف وتطهير مصفاة المبصقة'), ('suction_filter_cleaning', 'تنظيف وتطهير فلاتر وحدات الشفط'), ('handwash_basin_cleaning', 'تنظيف وتطهير حوض غسل اليدين'), ('ppe_drawers_refill', 'تعبئة الأدراج بأدوات الحماية الشخصية'), ('soap_refill', 'تعبئة حاويات الصابون'), ('sanitizer_refill', 'تعبئة حاويات مطهر اليدين')], max_length=80)),
                ('label', models.CharField(max_length=255)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='cssd.infectionproceduretemplate')),
            ],
            options={
                'ordering': ['sort_order', 'id'],
                'unique_together': {('template', 'field_name')},
            },
        ),
        migrations.AddField(
            model_name='infectioncleaningassignment',
            name='asset',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='infection_cleaning_assignments', to='cssd.asset'),
        ),
        migrations.AlterField(
            model_name='infectioncleaningassignment',
            name='clinic',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='infection_cleaning_assignments', to='cssd.location'),
        ),
        migrations.AddField(
            model_name='infectioncleaningtask',
            name='asset',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='infection_cleaning_tasks', to='cssd.asset'),
        ),
        migrations.AlterField(
            model_name='infectioncleaningtask',
            name='clinic',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='infection_cleaning_tasks', to='cssd.location'),
        ),
        migrations.AlterUniqueTogether(
            name='infectioncleaningassignment',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='infectioncleaningtask',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='infectioncleaningassignment',
            constraint=models.UniqueConstraint(condition=models.Q(('is_active', True), ('asset__isnull', False)), fields=('asset',), name='unique_active_infection_asset_assignment'),
        ),
        migrations.AddConstraint(
            model_name='infectioncleaningtask',
            constraint=models.UniqueConstraint(condition=models.Q(('assignment__isnull', False)), fields=('assignment', 'due_date'), name='unique_infection_assignment_due_date'),
        ),
        migrations.RunPython(create_default_template, migrations.RunPython.noop),
    ]
