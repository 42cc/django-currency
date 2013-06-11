# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Currency'
        db.create_table('currency_currency', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=3)),
            ('short_name', self.gf('django.db.models.fields.CharField')(default='', max_length=8, blank=True)),
            ('full_name', self.gf('django.db.models.fields.CharField')(default='', max_length=64, blank=True)),
            ('money_format', self.gf('django.db.models.fields.CharField')(default='%(currency)s%(value)s', max_length=64, blank=True)),
        ))
        db.send_create_signal('currency', ['Currency'])

        # Adding model 'ExchangeRate'
        db.create_table('currency_exchangerate', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('base_currency', self.gf('django.db.models.fields.related.ForeignKey')(related_name='rates', to=orm['currency.Currency'])),
            ('foreign_currency', self.gf('django.db.models.fields.related.ForeignKey')(related_name='reverse_rates', to=orm['currency.Currency'])),
            ('rate', self.gf('django.db.models.fields.DecimalField')(default='1', max_digits=9, decimal_places=5)),
            ('date', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
        ))
        db.send_create_signal('currency', ['ExchangeRate'])

        # Adding unique constraint on 'ExchangeRate', fields ['base_currency', 'foreign_currency', 'date']
        db.create_unique('currency_exchangerate', ['base_currency_id', 'foreign_currency_id', 'date'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'ExchangeRate', fields ['base_currency', 'foreign_currency', 'date']
        db.delete_unique('currency_exchangerate', ['base_currency_id', 'foreign_currency_id', 'date'])

        # Deleting model 'Currency'
        db.delete_table('currency_currency')

        # Deleting model 'ExchangeRate'
        db.delete_table('currency_exchangerate')


    models = {
        'currency.currency': {
            'Meta': {'ordering': "('code',)", 'object_name': 'Currency'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '3'}),
            'full_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '64', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'money_format': ('django.db.models.fields.CharField', [], {'default': "'%(currency)s%(value)s'", 'max_length': '64', 'blank': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '8', 'blank': 'True'})
        },
        'currency.exchangerate': {
            'Meta': {'ordering': "('-date', 'base_currency', 'foreign_currency')", 'unique_together': "(('base_currency', 'foreign_currency', 'date'),)", 'object_name': 'ExchangeRate'},
            'base_currency': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'rates'", 'to': "orm['currency.Currency']"}),
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'foreign_currency': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reverse_rates'", 'to': "orm['currency.Currency']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rate': ('django.db.models.fields.DecimalField', [], {'default': "'1'", 'max_digits': '9', 'decimal_places': '5'})
        }
    }

    complete_apps = ['currency']
