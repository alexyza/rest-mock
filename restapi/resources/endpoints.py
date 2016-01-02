#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" How to create endpoints into REST service """

from .. import get_logger
from ..meta import Meta
from confs.config import ALL_API_URL

logger = get_logger(__name__)


class Endpoints(object):
    """ Handling endpoints creation"""

    rest_api = None

    def __init__(self, api):
        super(Endpoints, self).__init__()
        self.rest_api = api

    def create_single(self, resource, endpoint, endkey):
        """ Adding a single restpoint from a Resource Class """

        address = ALL_API_URL + '/' + endpoint
        logger.info("Adding '%s' resource to REST address: *%s*",
                    resource.__name__, address)
        # Normal endpoint, e.g. /api/foo
        urls = [address]
        # Special endpoint, e.g. /api/foo/:endkey
        if endkey is not None:
            urls.append(address + '/<' + endkey + '>')
        # Create restful resource with it
        self.rest_api.add_resource(resource, *urls)

    def many_from_module(self, module):
        """ Automatic creation of endpoint from specified resources """

        resources = Meta().get_new_classes_from_module(module)
        # Init restful plugin
        if len(resources) > 0:
            # For each RESTful resource i receive
            for resource in resources:
                endpoint, endkey = resource().get_endpoint()
                self.create_single(resource, endpoint, endkey)

    def services_startup(self, myresources):
        """
        A special case for RethinkDB and other main services?

        This is where you tell the app what to do with requests.
        Note: For this resources make sure you create the table!
        """
        for name, content in myresources.items():
            (rclass, rname) = content
            # print rname, rclass.__dict__

            # Add resource from ORM class
            self.rest_api.add_resource(
                rclass,
                '/' + rname,
                '/' + rname + '/<string:data_key>')
            # Warning: due to restful plugin system,
            # methods get and get(value) require 2 different resources.
            # This is why we provide two times the same resource

            logger.info("Resource '" + rname + "' [" + name + "]: loaded")

#resources_init(jresources.json_autoresources)
