# Generated by Django 2.2.16 on 2023-03-22 13:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0009_remove_post_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='image',
            field=models.ImageField(blank=True, upload_to='posts/', verbose_name='Картинка'),
        ),
    ]
