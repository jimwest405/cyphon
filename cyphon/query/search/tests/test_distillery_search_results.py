# -*- coding: utf-8 -*-
# Copyright 2017 Dunbar Security Solutions, Inc.
#
# This file is part of Cyphon Engine.
#
# Cyphon Engine is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# Cyphon Engine is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Cyphon Engine. If not, see <http://www.gnu.org/licenses/>.
"""
Tests for the DistillerySearchResults Class.
"""

# standard library
from unittest.mock import patch

# third party
from django.test import TestCase
from django.test.client import RequestFactory

# local
from distilleries.models import Distillery
from query.search.distillery_search_results import (
    DistillerySearchResults,
    DistillerySearchResultsList,
)
from tests.test_fixture_manager import get_fixtures
from query.search.search_query import SearchQuery

MOCK_RESULTS_LIST = [{'id': 1, 'content': 'content'}]

MOCK_RESULTS = {
    'count': 1,
    'results': MOCK_RESULTS_LIST,
}

MOCK_FIND = patch(
    'distilleries.models.Distillery.find',
    return_value=MOCK_RESULTS,
)


class DistillerySearchResultsTestCase(TestCase):
    fixtures = get_fixtures(['distilleries'])

    @staticmethod
    def _get_instance(query, distillery):
        """

        Parameters
        ----------
        query : SearchQuery
        distillery : Distillery

        Returns
        -------
        DistillerySearchResults
        """
        with MOCK_FIND:
            return DistillerySearchResults(query, distillery)

    def test_distillery_attribute_set(self):
        """
        Makes sure that the distillery attribute is set to the passed in
        distillery parameter.
        """
        distillery = Distillery.objects.get(pk=1)
        search_query = SearchQuery('test')
        distillery_results = self._get_instance(search_query, distillery)

        self.assertEqual(distillery, distillery_results.distillery)

    def test_no_fieldsets(self):
        """
        Tests that no fieldsets are created for an instance with
        no keywords or parameters.
        """
        distillery = Distillery.objects.get(pk=1)
        search_query = SearchQuery('')
        distillery_results = self._get_instance(search_query, distillery)

        self.assertEqual(distillery_results.fieldsets, [])
        self.assertIsNone(distillery_results.engine_query)

    def test_field_fieldsets_if_related(self):
        """
        Tests that a list of QueryFieldsets are created when given a list of
        FieldSearchParameters if the parameter is related to the distillery.
        """
        distillery = Distillery.objects.get(pk=3)
        search_query = SearchQuery('ip_address=13.43')
        distillery_results = self._get_instance(search_query, distillery)

        self.assertEqual(len(distillery_results.fieldsets), 1)

        field_fieldset = distillery_results.fieldsets[0]

        self.assertEqual(field_fieldset.field_name, 'ip_address')
        self.assertEqual(field_fieldset.field_type, 'GenericIPAddressField')

    def test_field_fieldsets_if_not_related(self):
        """
        Tests that a list of QueryFieldsets are not created if the
        FieldSearchParameter is not related to the distillery
        """
        distillery = Distillery.objects.get(pk=1)
        search_query = SearchQuery('ip_address=13.43')
        distillery_results = self._get_instance(search_query, distillery)

        self.assertEqual(len(distillery_results.fieldsets), 0)

    def test_keyword_fieldsets(self):
        """
        Tests that a list of QueryFieldsets is created for each text field
        on a distillery.
        """
        distillery = Distillery.objects.get(pk=5)
        search_query = SearchQuery('test "more testing"')
        distillery_results = self._get_instance(search_query, distillery)

        self.assertEqual(len(distillery_results.fieldsets), 2)
        fieldset_1 = distillery_results.fieldsets[0]
        fieldset_2 = distillery_results.fieldsets[1]

        self.assertEqual(fieldset_1.field_name, 'host')
        self.assertEqual(fieldset_1.field_type, 'GenericIPAddressField')
        self.assertEqual(fieldset_1.operator, 'regex')
        self.assertEqual(fieldset_1.value, 'test|more testing')

        self.assertEqual(fieldset_2.field_name, 'message')
        self.assertEqual(fieldset_2.field_type, 'TextField')
        self.assertEqual(fieldset_2.operator, 'regex')
        self.assertEqual(fieldset_2.value, 'test|more testing')

    def test_results(self):
        """
        Tests that the results and result count from a distillery
        search get put onto the results and count attribute
        """
        distillery = Distillery.objects.get(pk=5)
        search_query = SearchQuery('test "more testing"')
        distillery_results = self._get_instance(search_query, distillery)

        self.assertEqual(distillery_results.count, 1)
        self.assertEqual(distillery_results.results, MOCK_RESULTS_LIST)

    def test_as_dict(self):
        """
        Tests that the correct dictionary shape is returned from the
        as_dict() function.
        """
        distillery = Distillery.objects.get(pk=1)
        search_query = SearchQuery('test "more testing"')
        distillery_results = self._get_instance(search_query, distillery)
        factory = RequestFactory()
        request = factory.get('/api/v1/search/')

        self.assertDictEqual(distillery_results.as_dict(request), {
            'count': 1,
            'results': MOCK_RESULTS_LIST,
            'next': None,
            'previous': None,
            'distillery': {
                'id': 1,
                'name': 'mongodb.test_database.test_posts',
                'url': 'http://testserver/api/v1/distilleries/1/',
            }
        })


class DistillerySearchResultsListTestCase(TestCase):
    fixtures = get_fixtures(['distilleries'])

    @staticmethod
    def _get_instance(query):
        """

        Parameters
        ----------
        query : SearchQuery

        Returns
        -------
        DistillerySearchResultsList
        """
        with MOCK_FIND:
            return DistillerySearchResultsList(query)

    def test_distillery_filter(self):
        """
        Tests that the distilleries from a distillery filter are used for
        getting distillery results.
        """
        search_query = SearchQuery('@source=test_database.test_posts test')
        distillery_results_list = self._get_instance(search_query)

        self.assertEqual(len(distillery_results_list.distilleries), 1)
        self.assertEqual(distillery_results_list.distilleries[0].pk, 1)
        self.assertEqual(len(distillery_results_list.results), 1)
        self.assertEqual(distillery_results_list.results[0].distillery.pk, 1)

    def test_result_count(self):
        """
        Tests that the result list returns a combined count of all
        DistillerySearchResults
        """
        search_query = SearchQuery('test')
        distillery_results_list = self._get_instance(search_query)

        self.assertEqual(distillery_results_list.count, 6)

    def test_result_length(self):
        """
        Tests that an accurate amount of DistillerySearchResults is created
        for the number of distilleries returned.
        """
        distillery_results_list = self._get_instance(SearchQuery('test'))

        self.assertEqual(len(distillery_results_list.results), 6)

    def test_as_dict(self):
        """
        Tests that the as_dict() function returns the correct
        dictionary shape.
        """
        search_query = SearchQuery('@source=test_database.test_posts test')
        distillery_results_list = self._get_instance(search_query)
        factory = RequestFactory()
        request = factory.get('/api/v1/search/')

        self.assertEqual(distillery_results_list.as_dict(request), {
            'count': 1,
            'results': [{
                'count': 1,
                'next': None,
                'previous': None,
                'results': MOCK_RESULTS_LIST,
                'distillery': {
                    'id': 1,
                    'name': 'mongodb.test_database.test_posts',
                    'url': 'http://testserver/api/v1/distilleries/1/',
                }
            }]
        })
