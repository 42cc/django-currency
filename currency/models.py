# -*- coding: utf-8 -*-
import datetime
from decimal import Decimal, Context, localcontext

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .utils import memoize_for_object, simple_cache


RATES_CACHE_KEY = '{0}_{1}_rate'


class Currency(models.Model):

    """
    Currenncy info
    """

    code = models.CharField('ISO 4217 code', max_length=3, unique=True)

    short_name = models.CharField(
        _(u'Symbol or short name'), max_length=8, blank=True, default='',
        help_text=_(u'e.g. $, руб.'))

    full_name = models.CharField(
        _(u'Full name'), max_length=64, blank=True, default='',
        help_text=_(u'e.g. holland dollar, ukrainian hryvnya'))

    money_format = models.CharField(
        _(u'money format string'), max_length=64, blank=True,
        default='%(short_name)s%(value)s',
        help_text=_(ur'e.g. %(value)s%(short_name)s'))

    class Meta:
        ordering = ('code',)
        verbose_name = _('currency')
        verbose_name_plural = _('currencies')

    def __unicode__(self):
        return self.code

    def format(self, value):
        """
        Return string for numeric `value` formatted according to self.money_format

        """
        result = self.money_format % {
            'code': self.code, 'short_name': self.short_name,
            'full_name': self.full_name, 'value': value,
        }
        return result

    @classmethod
    def get_default_currency(cls):
        currency, _ = cls.objects.get_or_create(
            code='USD',
            defaults={'short_name': '$', 'money_format': '%(short_name)s%(value)s'}
        )
        return currency

    def get_rate_object(self, other_currency, ignore_conflict=False):
        """
        Return ExchangeRate instance that can be used to convert current
        Currency to `other_currency`.
        New rate (indirect) can be created if there are rates for current and
        `other_currency` with base_currency==Currency.get_default_currency()

        if both direct rate ind indirect rate exist and indirect rate is newer
        then ValueError is raise. This can be overriden with
        ignore_conflict=True, then newer rate is returned

        Return value: (exchangerate_instance, is_reverse_boolean)

        """
        # direct exchange rate
        with localcontext(Context(prec=ExchangeRate.PRECISION + 10)):
            try:
                direct_rate = (
                    self.rates.filter(foreign_currency=other_currency).latest()
                )
            except ExchangeRate.DoesNotExist:
                direct_rate = None

            try:
                reverse_rate = (
                    other_currency.rates.filter(foreign_currency=self).latest()
                )
            except ExchangeRate.DoesNotExist:
                reverse_rate = None

            # indirect exchange rate
            indirect_rate = False
            try:
                default_currency = Currency.get_default_currency()
                if default_currency.code != self.code:
                    rate_to_self = (
                        default_currency.rates
                                        .filter(foreign_currency=self)
                                        .latest()
                    )
                    rate_to_other = (
                        default_currency.rates
                                        .filter(foreign_currency=other_currency)
                                        .latest()
                    )
                    new_rate = rate_to_self.rate / rate_to_other.rate
                    new_date = max(rate_to_self.date, rate_to_other.date)
                    indirect_rate = ExchangeRate(
                        base_currency=self,
                        foreign_currency=other_currency,
                        rate=new_rate,
                        date=new_date,
                    )
            except ExchangeRate.DoesNotExist:
                pass

            is_reverse = False
            rate = None
            if not indirect_rate:
                if direct_rate:
                    rate = direct_rate
                elif reverse_rate:
                    rate = reverse_rate
                    is_reverse = True
            else:
                if not (direct_rate or reverse_rate):
                    rate = indirect_rate
                else:  # we have both indirect and (reverse or direct) rates
                    if direct_rate:
                        rate = direct_rate
                    else:
                        rate = reverse_rate
                        is_reverse = True

                    if rate.date < indirect_rate.date:
                        if not ignore_conflict:
                            raise ValueError(
                                'direct rate `%s` is older then indirect rate `%s`. '
                                'Please investigate' % (direct_rate, indirect_rate))
                        else:
                            rate = indirect_rate
            if rate is None:
                raise Currency.DoesNotExist
            if rate == indirect_rate:
                rate.save()
            return (rate, is_reverse)

    def get_rate(self, *args, **kwargs):
        """
        Get ExchangeRate instance from get_rate_object() and return
        `instance.rate`
        """
        with localcontext(Context(prec=ExchangeRate.PRECISION + 10)):
            rate_object, reverse = self.get_rate_object(*args, **kwargs)
            rate = rate_object.rate
            if reverse:
                rate = Decimal('1') / rate
            return rate


def validate_positive(value):
    if value <= 0:
        raise ValidationError('%s is not positive' % value)


class ExchangeRate(models.Model):
    PRECISION = 5

    base_currency = models.ForeignKey(Currency, related_name='rates')

    foreign_currency = models.ForeignKey(Currency, related_name='reverse_rates')

    rate = models.DecimalField(
        _(u'Exchange rate'), max_digits=9, decimal_places=PRECISION,
        default='1',
        validators=[validate_positive])

    date = models.DateField(_(u'Settlement date'), default=datetime.date.today)

    class Meta:
        ordering = ('-date', 'base_currency', 'foreign_currency')
        get_latest_by = 'date'
        verbose_name = _('Exchange rate')
        verbose_name_plural = _('Exchange rates')
        unique_together = (
            ('base_currency', 'foreign_currency', 'date'),
        )

    def __unicode__(self):
        return "%s to %s for %s: %s" % (self.base_currency, self.foreign_currency, self.date, self.rate)

    def save(self, *args, **kwargs):
        super(ExchangeRate, self).save(*args, **kwargs)
        key = RATES_CACHE_KEY.format(self.base_currency.code, self.foreign_currency.code)
        cache.delete(key)
        key = RATES_CACHE_KEY.format(self.foreign_currency.code, self.base_currency.code)
        cache.delete(key)

    def clean(self):
        # only called from admin and modelforms. If you create "bad" model with
        # plain Model.objects.create(...) then this validation will not take it's
        # place
        try:
            reverse_rate = (
                ExchangeRate.objects
                .get(
                    base_currency=self.foreign_currency,
                    foreign_currency=self.base_currency,
                    date=self.date)
            )
        except ExchangeRate.DoesNotExist:
            reverse_rate = None

        if reverse_rate:
            raise ValidationError(
                'Reverse rate with pk=%s for same date already exists.' % reverse_rate.pk)

        if self.date > datetime.date.today():
            raise ValidationError("Can't create rate for future")
        return


def get_currency(currency):
    """
    If currency is of type Currency then just return it. If it's string then
    returns Currency by code

    """
    if isinstance(currency, Currency):
        currency = currency
    elif isinstance(currency, basestring):
        currency = Currency.objects.get(code=currency)
    else:
        raise TypeError(
            'currency argument should be of type string or Currency. Got `%s` instead' % currency)
    return currency


@simple_cache(RATES_CACHE_KEY, 86400)
def cached_get_rate(base_currency, foreign_currency):
    """Return exchange rate between two currencies. Results are cached for 1 day.

    :type base_currency: string or unicode
    :type foreign_currency: string or unicode
    """

    return get_currency(base_currency).get_rate(get_currency(foreign_currency))


class Money(object):

    """Helper class to handle money operations with Currency. Example:
    >>> from currency.models import *
    >>> my_money = Money(1531, 'USD')
    >>> my_money *= 100
    >>> my_money
    <Money: 153100USD>
    >>> my_money += Money(23, 'USD')
    >>> my_money
    <Money: 153123USD>
    >>> my_money.convert_to('EUR')
    ...
    DoesNotExist
    >>> usd = Currency.objects.get(code='USD')
    >>> eur = Currency.objects.get(code='EUR')
    >>> ExchangeRate.objects.create(base_currency=usd, foreign_currency=eur, rate=1/1.3)
    <ExchangeRate: USD to EUR for 2013-06-13: 0.769230769231>
    >>> ExchangeRate.objects.get(base_currency=usd, foreign_currency=eur)
    <ExchangeRate: USD to EUR for 2013-06-13: 0.76923>
    >>> # Be careful wheny you usd exchange rate right after creation!
    >>> my_money.convert_to('EUR')
    <Money: 117786.80529EUR>
    >>> my_money.convert_to('EUR').convert_to('USD') - my_money
    <Money: -3USD>
    >>> # Ooops!

    """
    def __init__(self, value, currency='USD', max_digits=15):
        self.precision = max_digits
        places = ExchangeRate.PRECISION
        if not (isinstance(currency, basestring) and len(currency) == 3):
            raise TypeError("currency argument should be a string with lenght 3")
        self.currency = currency.upper()
        self.context = Context(prec=self.precision)
        with localcontext(self.context):
            if isinstance(value, Decimal):
                self.value = value
            else:
                self.value = Decimal(str(value))
            self.quantizator = Decimal(10) ** (-places)
            self.value = self.quantize(self.value)
        return

    def quantize(self, value):
        return value.quantize(self.quantizator)

    def __unicode__(self):
        return "%s%s" % (self.value, self.currency)

    def __str__(self):
        return self.__unicode__()

    def __repr__(self):
        return "<Money: %s>" % self.__str__()

    @staticmethod
    def same_currencies(one, other):
        if one.currency != other.currency:
            raise ValueError(
                'Currencies of %s and %s differ. Please convert them '
                'to same currencies' % (one, other)
            )
        return True

    @memoize_for_object
    def get_rate(self, other_currency):
        """Just calls get_rate but memoizes result so even cache is not hit

        """
        return cached_get_rate(self.currency, other_currency)

    def convert_to(self, other_currency):
        """Return current Money converted to other_currency as new instance of
        Money

        """
        with localcontext(self.context):
            rate = self.get_rate(other_currency)
            result = Money(self.value * rate, other_currency)
            return result

    def new(self, value):
        """Return new Money instance with same currency but different value

        """
        with localcontext(self.context):
            return Money(value, self.currency)

    def __add__(self, other):
        with localcontext(self.context):
            self.same_currencies(self, other)
            return self.new(self.value + other.value)

    def __sub__(self, other):
        with localcontext(self.context):
            self.same_currencies(self, other)
            return self.new(self.value - other.value)

    def __mul__(self, other):
        with localcontext(self.context):
            other = Decimal(str(other))
            return self.new(self.value * other)

    def __div__(self, other):
        with localcontext(self.context):
            other = Decimal(str(other))
            return self.new(self.value / other)

    def __divmod__(self, other):
        with localcontext(self.context):
            other = Decimal(str(other))
            return self.new(divmod(self.value, other))
