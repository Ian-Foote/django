from datetime import datetime
from math import pi
from unittest import skipIf, skipUnless

from django.db import NotSupportedError, connection
from django.db.models import F, FloatField, Value
from django.db.models.functions import Coalesce, Pi
from django.test import TestCase

from .models import (
    Article, DBArticle, DBDefaults, DBDefaultsFK, DBDefaultsFunction,
    DBDefaultsPK,
)


class DefaultTests(TestCase):
    def test_field_defaults(self):
        a = Article()
        now = datetime.now()
        a.save()

        self.assertIsInstance(a.id, int)
        self.assertEqual(a.headline, "Default headline")
        self.assertLess((now - a.pub_date).seconds, 5)

    @skipUnless(connection.vendor == 'postgresql', 'Postgres test')
    def test_field_database_defaults_postgres(self):
        a = DBArticle()
        now = datetime.now()
        a.save()

        self.assertIsInstance(a.id, int)
        self.assertEqual(a.headline, "Default headline")
        self.assertLess((a.pub_date - now).seconds, 5)

    @skipUnless(connection.vendor == 'mysql', 'MySQL test')
    def test_field_database_defaults_mysql(self):
        a = DBArticle()
        now = datetime.utcnow()
        a.save()
        a.refresh_from_db()

        self.assertIsInstance(a.id, int)
        self.assertEqual(a.headline, "Default headline")
        self.assertLess((a.pub_date - now).seconds, 5)

    @skipUnless(connection.vendor == 'sqlite', 'Sqlite test')
    def test_field_database_defaults_sqlite(self):
        a = DBArticle()
        now = datetime.utcnow()
        a.save()
        a.refresh_from_db()

        self.assertIsInstance(a.id, int)
        self.assertEqual(a.headline, "Default headline")
        self.assertLess((now - a.pub_date).seconds, 5)

    def test_null_db_default(self):
        m = DBDefaults.objects.create()
        if not connection.features.can_return_columns_from_insert:
            m.refresh_from_db()
        self.assertEqual(m.null, 1.1)

        m2 = DBDefaults.objects.create(null=None)
        self.assertIsNone(m2.null)

    @skipUnless(connection.vendor == 'postgresql', 'Postgres test')
    def test_both_default_postgres(self):
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO field_defaults_dbdefaults DEFAULT VALUES')
        m = DBDefaults.objects.get()
        self.assertEqual(m.both, 2)

        m2 = DBDefaults.objects.create()
        self.assertEqual(m2.both, 1)

    @skipUnless(connection.vendor == 'mysql', 'MySQL test')
    def test_both_default_mysql(self):
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO field_defaults_dbdefaults () VALUES ()')
        m = DBDefaults.objects.get()
        self.assertEqual(m.both, 2)

        m2 = DBDefaults.objects.create()
        self.assertEqual(m2.both, 1)

    @skipUnless(connection.vendor == 'sqlite', 'Sqlite test')
    def test_both_default_sqlite(self):
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO field_defaults_dbdefaults ("null") VALUES (1)')
        m = DBDefaults.objects.get()
        self.assertEqual(m.both, 2)

        m2 = DBDefaults.objects.create()
        self.assertEqual(m2.both, 1)

    @skipUnless(
        connection.features.supports_functions_in_defaults,
        'MySQL before 8.0.13 does not support function defaults.',
    )
    def test_db_default_function(self):
        m = DBDefaultsFunction.objects.create()
        if not connection.features.can_return_columns_from_insert:
            m.refresh_from_db()
        self.assertAlmostEqual(m.number, pi)
        self.assertEqual(m.year, datetime.now().year)
        self.assertAlmostEqual(m.added, pi + 4.5)
        self.assertEqual(m.multiple_subfunctions, 4.5)

    @skipIf(
        connection.features.supports_functions_in_defaults,
        'MySQL before 8.0.13 does not support function defaults.',
    )
    def test_db_default_function_invalid(self):
        message = f'{connection.version} does not support functions in defaults.'
        with self.assertRaisesMessage(NotSupportedError, message):
            FloatField(db_default=Pi())

    def test_db_default_expression_invalid(self):
        expression = F('field_name')
        message = f'{expression} is not a valid database default.'
        with self.assertRaisesMessage(NotSupportedError, message):
            FloatField(db_default=expression)

    def test_db_default_combined_invalid(self):
        expression = Value(4.5) + F('field_name')
        message = f'{expression} is not a valid database default.'
        with self.assertRaisesMessage(NotSupportedError, message):
            FloatField(db_default=expression)

    def test_db_default_function_arguments_invalid(self):
        expression = Coalesce(Value(4.5), F('field_name'))
        message = f'{expression} is not a valid database default.'
        with self.assertRaisesMessage(NotSupportedError, message):
            FloatField(db_default=expression)

    @skipUnless(connection.vendor == 'postgresql', 'Postgres test')
    def test_pk_db_default(self):
        m = DBDefaultsPK.objects.create()
        self.assertEqual(m.pk, 'en')
        self.assertEqual(m.language_code, 'en')

        m2 = DBDefaultsPK.objects.create(language_code='de')
        self.assertEqual(m2.pk, 'de')
        self.assertEqual(m2.language_code, 'de')

    @skipUnless(connection.vendor == 'postgresql', 'Postgres test')
    def test_foreign_key_db_default(self):
        m = DBDefaultsPK.objects.create(language_code='fr')
        r = DBDefaultsFK.objects.create()
        self.assertEqual(r.language_code, m)

        m2 = DBDefaultsPK.objects.create()
        r2 = DBDefaultsFK.objects.create(language_code=m2)
        self.assertEqual(r2.language_code, m2)
