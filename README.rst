===============
Django currency
===============

Overview
========

Simple django app that handles basic currency handling, formatting and
**manual** addition of exchange rates that can be used
to easy convert from one currency to another


Example usage
=============


.. code-block:: python
    
   from currency.models import Currency, ExchangeRate, Money

   usd = Currency.objects.create(code='USD', short_name='$')
   eur = Currency.objects.create(code='EUR', short_name='€')

   ExchangeRate.objects.create(base_currency=usd, foreign_currency=eur, rate=1/1.3)

   print(usd.get_rate(eur))  # Decimal('0.76923')
   print(eur.get_rate(usd))  # Decimal('1.30000')

   my_money = Money(1531, 'USD')
   print(my_money)  # 1531.00000USD
   my_money += Money(23, 'USD')
   print(my_money)  # 1554.00000USD
   print(my_money.convert_to('EUR'))  # 1195.38342EUR

   # be careful with conversions. Errors accumulate with each conversion. Example:
   print(my_money.convert_to('EUR').convert_to('USD'))  # 1553.99845USD