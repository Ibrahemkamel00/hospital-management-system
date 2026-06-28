from django.db import migrations, models


def migrate_existing_products(apps, schema_editor):
    StoreProduct = apps.get_model('medical_store', 'StoreProduct')
    for product in StoreProduct.objects.all():
        if not product.allowed_units:
            product.allowed_units = [product.unit or 'Piece']
        if not product.unit_pieces:
            product.unit_pieces = {'Pack': 1, 'Carton': 1, 'Set': 1}
        if product.shelf is None:
            product.shelf = ''
        product.save(update_fields=['allowed_units', 'unit_pieces', 'shelf'])


def migrate_existing_batches(apps, schema_editor):
    StoreBatch = apps.get_model('medical_store', 'StoreBatch')
    for batch in StoreBatch.objects.select_related('product'):
        if not batch.received_unit:
            batch.received_unit = batch.product.unit or 'Piece'
        if not batch.received_unit_pieces:
            batch.received_unit_pieces = 1
        if not batch.received_total_quantity:
            batch.received_total_quantity = batch.received_quantity
        batch.save(update_fields=['received_unit', 'received_unit_pieces', 'received_total_quantity'])


def migrate_existing_items(apps, schema_editor):
    StoreRequestItem = apps.get_model('medical_store', 'StoreRequestItem')
    for item in StoreRequestItem.objects.select_related('product'):
        if not item.requested_unit:
            item.requested_unit = item.product.unit or 'Piece'
        if not item.requested_unit_pieces:
            item.requested_unit_pieces = 1
        if not item.requested_total_quantity:
            item.requested_total_quantity = item.requested_quantity
        if not item.issued_unit:
            item.issued_unit = item.requested_unit
        if not item.issued_unit_pieces:
            item.issued_unit_pieces = 1
        if not item.issued_total_quantity:
            item.issued_total_quantity = item.issued_quantity
        item.save(update_fields=['requested_unit','requested_unit_pieces','requested_total_quantity','issued_unit','issued_unit_pieces','issued_total_quantity'])


class Migration(migrations.Migration):
    dependencies = [
        ('medical_store', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='storeproduct',
            name='allowed_units',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='storeproduct',
            name='unit_pieces',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name='storeproduct',
            name='shelf',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='storebatch',
            name='batch_number',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='storebatch',
            name='received_unit',
            field=models.CharField(blank=True, default='', max_length=40),
        ),
        migrations.AddField(
            model_name='storebatch',
            name='received_unit_pieces',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='storebatch',
            name='received_total_quantity',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='storerequestitem',
            name='requested_unit',
            field=models.CharField(default='Piece', max_length=40),
        ),
        migrations.AddField(
            model_name='storerequestitem',
            name='requested_unit_pieces',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='storerequestitem',
            name='requested_total_quantity',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='storerequestitem',
            name='issued_unit',
            field=models.CharField(blank=True, default='', max_length=40),
        ),
        migrations.AddField(
            model_name='storerequestitem',
            name='issued_unit_pieces',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='storerequestitem',
            name='issued_total_quantity',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(migrate_existing_products, migrations.RunPython.noop),
        migrations.RunPython(migrate_existing_batches, migrations.RunPython.noop),
        migrations.RunPython(migrate_existing_items, migrations.RunPython.noop),
    ]
