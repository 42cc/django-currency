# -*- coding: utf-8 -*-

# system:
from decimal import Decimal
import datetime

# django:
from django.core.cache import cache
from django.test import TestCase

# thirdparty
from mock import patch

# local
from ..models import Currency, ExchangeRate, Money


class TestMoneyExchanging(TestCase):

    def test_exchangerate(self):
        # test default currency
        default_currency = Currency.get_default_currency()
        self.assertEqual(default_currency.code, 'USD')
        self.assertEqual(default_currency.format(5), '$5')

        hrn = Currency.objects.create(code='UAH', short_name='hrn')
        hrn = Currency.objects.get(code='UAH')  # get stored value
        rub = Currency.objects.create(code='RUB', short_name='rub')
        rub = Currency.objects.get(code='RUB')  # get stored value

        # test indirect currency converting
        rate1 = ExchangeRate.objects.create(
            base_currency=default_currency, foreign_currency=hrn,
            rate='0.125')
        # get stored value:
        rate1 = ExchangeRate.objects.get(
            base_currency=default_currency, foreign_currency=hrn)

        rate2 = ExchangeRate.objects.create(
            base_currency=default_currency, foreign_currency=rub,
            rate='0.03125')
        # get stored value:
        rate2 = ExchangeRate.objects.get(
            base_currency=default_currency, foreign_currency=rub)

        self.assertEqual(hrn.get_rate(rub), rate1.rate / rate2.rate)

        # test direct currency converting

        # NOTE: rate for hrn-> rub conversion have already been created from
        # usd->rub, usd->uah rates. so we are redefining it
        rate = ExchangeRate.objects.filter(
            base_currency=hrn, foreign_currency=rub).latest()
        rate.rate = '4.1'
        rate.save()
        rate = ExchangeRate.objects.get(pk=rate.pk)  # get stored value
        self.assertAlmostEqual(hrn.get_rate(rub), rate.rate)
        self.assertAlmostEqual(rub.get_rate(hrn), Decimal('1') / rate.rate)

        # check dates conflict:
        rate.date = rate.date - datetime.timedelta(days=1)
        rate.save()
        with self.assertRaises(ValueError):
            hrn.get_rate(rub)

        # testing Money helper class
        test_value = Decimal('1245.22')
        test_rate = Decimal('1.3')
        eur = Currency.objects.create(code='EUR', short_name=u'€')
        eur = Currency.objects.get(code='EUR')  # get stored value
        usd_pack = Money(test_value, 'USD')
        rate = ExchangeRate.objects.create(
            base_currency=eur, foreign_currency=default_currency,
            rate=test_rate)
        # get stored value:
        rate = ExchangeRate.objects.get(
            base_currency=eur, foreign_currency=default_currency)
        eur_pack = usd_pack.convert_to('EUR')
        self.assertEqual(eur_pack.value, (test_value / test_rate).quantize(Decimal('.00001')))

        # testing cache and memoization
        with patch.object(cache, 'get') as cache_get:
            with patch.object(cache, 'set') as cache_set:
                # get_rate is memoized:
                eur_pack = usd_pack.convert_to('EUR')
                self.assertEqual(cache_get.call_count, 0)
                self.assertEqual(cache_set.call_count, 0)

                # reset memoization and test cached value
                usd_pack = Money(test_value, 'USD')
                cache_get.return_value = Decimal('1.3')
                eur_pack = usd_pack.convert_to('EUR')
                self.assertEqual(cache_get.call_count, 1)
                self.assertEqual(cache_set.call_count, 0)

                # reset memoization and test cache setting:
                usd_pack = Money(test_value, 'USD')
                cache_get.return_value = None
                eur_pack = usd_pack.convert_to('EUR')
                self.assertEqual(cache_get.call_count, 2)
                self.assertEqual(cache_set.call_count, 1)

        # test that caching do not result in outdated values:
        usd_pack = Money(test_value, 'USD')
        eur_pack = usd_pack.convert_to('EUR')
        self.assertEqual(eur_pack.value, (test_value / rate.rate).quantize(Decimal('.00001')))

        new_rate = Decimal('1.33')
        rate.rate = new_rate
        rate.save()

        # memoization will not occure frequntly but it ignores changes
        # so I'm getting new instance here
        usd_pack = Money(test_value, 'USD')
        eur_pack = usd_pack.convert_to('EUR')
        self.assertEqual(eur_pack.value, (test_value / new_rate).quantize(Decimal('.00001')))

        # testing money operations
        usd_money = Money(0, 'USD')
        self.assertEqual((usd_money * 5).value, Decimal('0'))
        self.assertEqual((usd_money.new('12') * Decimal('5.1')).value, Decimal('61.2'))
        self.assertEqual((usd_money.new('2') / Decimal('3')).value, Decimal('0.66667'))
        self.assertEqual((usd_money.new('2.55387') + usd_money.new('1.33')).value, Decimal('3.88387'))
        self.assertEqual((usd_money.new('2.55387') - usd_money.new('1.33')).value, Decimal('1.22387'))
