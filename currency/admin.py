# -*- coding: utf-8 -*-

from django.contrib import admin

from .models import Currency, ExchangeRate


class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('code', 'full_name', 'short_name',)


class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('date', 'base_currency', 'foreign_currency', 'rate')
    list_filter = ('date', 'base_currency',)


admin.site.register(Currency, CurrencyAdmin)
admin.site.register(ExchangeRate, ExchangeRateAdmin)
