# Generated for Medical Store System V1.0
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StoreProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('code', models.CharField(max_length=80, unique=True)),
                ('manufacturer', models.CharField(blank=True, max_length=150)),
                ('unit', models.CharField(choices=[('Piece', 'Piece'), ('Box', 'Box'), ('Pack', 'Pack'), ('Carton', 'Carton'), ('Roll', 'Roll'), ('Bottle', 'Bottle'), ('Tube', 'Tube'), ('Set', 'Set')], default='Piece', max_length=40)),
                ('shelf', models.CharField(blank=True, max_length=100)),
                ('minimum_stock', models.PositiveIntegerField(default=0)),
                ('category', models.CharField(blank=True, max_length=120)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Medical Store Product', 'verbose_name_plural': 'Medical Store Products', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='StoreRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_number', models.CharField(blank=True, max_length=30, unique=True)),
                ('department', models.CharField(blank=True, max_length=150)),
                ('reason', models.TextField()),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('PENDING_HOSPITAL_MANAGER', 'Pending Hospital Manager Approval'), ('REJECTED', 'Rejected'), ('APPROVED_WAITING_STORE', 'Approved - Waiting Store Issue'), ('ISSUED_WAITING_NURSE_CONFIRM', 'Issued - Waiting Nurse Confirmation'), ('CLOSED', 'Closed')], default='DRAFT', max_length=40)),
                ('hospital_manager_at', models.DateTimeField(blank=True, null=True)),
                ('hospital_manager_comment', models.TextField(blank=True)),
                ('store_issued_at', models.DateTimeField(blank=True, null=True)),
                ('store_comment', models.TextField(blank=True)),
                ('nurse_confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('nurse_comment', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('hospital_manager_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='store_approved_requests', to=settings.AUTH_USER_MODEL)),
                ('nurse_confirmed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='store_confirmed_receipts', to=settings.AUTH_USER_MODEL)),
                ('requested_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='medical_store_requests', to=settings.AUTH_USER_MODEL)),
                ('store_issued_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='store_issued_requests', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Medical Store Request', 'verbose_name_plural': 'Medical Store Requests', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='StoreBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('supplier_name', models.CharField(max_length=150)),
                ('batch_number', models.CharField(max_length=120)),
                ('received_date', models.DateField(default=django.utils.timezone.localdate)),
                ('manufacturing_date', models.DateField(blank=True, null=True)),
                ('expiry_date', models.DateField(blank=True, null=True)),
                ('received_quantity', models.PositiveIntegerField(default=0)),
                ('current_quantity', models.PositiveIntegerField(default=0)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='batches', to='medical_store.storeproduct')),
                ('received_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='store_received_batches', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Stock Batch', 'verbose_name_plural': 'Stock Batches', 'ordering': ['expiry_date', 'created_at'], 'indexes': [models.Index(fields=['product', 'expiry_date'], name='medical_stor_product_05a77d_idx')]},
        ),
        migrations.CreateModel(
            name='StoreRequestItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('requested_quantity', models.PositiveIntegerField(default=1)),
                ('issued_quantity', models.PositiveIntegerField(default=0)),
                ('issue_adjustment_reason', models.TextField(blank=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='request_items', to='medical_store.storeproduct')),
                ('store_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='medical_store.storerequest')),
            ],
            options={'verbose_name': 'Medical Store Request Item', 'verbose_name_plural': 'Medical Store Request Items'},
        ),
        migrations.CreateModel(
            name='StoreIssueAllocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='issue_allocations', to='medical_store.storebatch')),
                ('request_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='allocations', to='medical_store.storerequestitem')),
            ],
        ),
        migrations.CreateModel(
            name='StoreAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=120)),
                ('details', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='medical_store.storeproduct')),
                ('store_request', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to='medical_store.storerequest')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Medical Store Audit Log', 'verbose_name_plural': 'Medical Store Audit Logs', 'ordering': ['-created_at']},
        ),
    ]
