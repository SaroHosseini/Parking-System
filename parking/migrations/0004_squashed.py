from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('parking', '0003_alter_parkinglot_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='session',
            field=models.ForeignKey(
                to='parking.parkingsession',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='payments',
                verbose_name='سشن پارک',
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='receipt',
            name='receipt_number',
            field=models.CharField(
                'شماره رسید',
                max_length=50,
                unique=True,
                editable=False,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name='receipt',
            name='session',
            field=models.OneToOneField(
                to='parking.parkingsession',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='receipt',
                verbose_name='سشن پارک',
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='receipt',
            name='payment',
            field=models.OneToOneField(
                to='parking.payment',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='receipt',
                verbose_name='پرداخت',
                null=True,
                blank=True,
            ),
        ),
        
        migrations.AlterModelOptions(
            name='parkingsession',
            options={'ordering': ['-entry_time'], 'verbose_name': 'سشن پارک', 'verbose_name_plural': 'سشن\u200cهای پارک'},
        ),
        migrations.AlterModelOptions(
            name='vehicle',
            options={'ordering': ['owner_name', 'plate_number'], 'verbose_name': 'وسیله نقلیه', 'verbose_name_plural': 'وسایل نقلیه'},
        ),
        migrations.AlterField(
            model_name='parkingsession',
            name='calculated_fee',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='پس از ثبت خروج خودکار محاسبه می\u200cشود', max_digits=10, null=True, verbose_name='هزینه محاسبه\u200cشده'),
        ),
        migrations.AlterField(
            model_name='parkingsession',
            name='status',
            field=models.CharField(choices=[('open', 'باز (در حال پارک)'), ('closed', 'بسته (خارج شده)'), ('cancelled', 'لغو شده')], default='open', max_length=20, verbose_name='وضعیت'),
        ),
        migrations.AlterField(
            model_name='payment',
            name='payment_method',
            field=models.CharField(blank=True, choices=[('pos', 'پرداخت با کارتخوان'), ('cash', 'پرداخت نقدی'), ('card_to_card_transfer', 'پرداخت با کارت به کارت'), ('online_gateway', 'پرداخت با درگاه آنلاین')], max_length=50, null=True, verbose_name='نحوه پرداخت'),
        ),
    ]
