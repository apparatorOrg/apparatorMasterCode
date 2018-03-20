# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.utils.encoding import python_2_unicode_compatible
from django.db import models

# Create your models here.


@python_2_unicode_compatible
class Review(models.Model):
    id = models.AutoField(primary_key=True)
    store_front = models.CharField(max_length=2)
    app_version = models.CharField(max_length=32)
    last_modified = models.DateTimeField('date published')
    nickname = models.CharField(max_length=128)
    rating = models.DecimalField(max_digits=3, decimal_places=2)
    title = models.CharField(max_length=255)
    review = models.TextField()
    edited = models.NullBooleanField()

    def __str__(self):
        return self.review
