#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Mock Resources as Example """

# In case you do not know how API endpoints usually looks,
# see some examples here to take inspiration
# https://parse.com/docs/rest/guide

from .. import get_logger
logger = get_logger(__name__)

from .base import ExtendedApiResource
import mylibs.resources.decorators as decorate

#####################################
## FIRST simple EXAMPLE

## Works with request(s) to:
# GET /api/foo

class FooOne(ExtendedApiResource):
    """ Empty example for mock service with no :myid """

    @decorate.apimethod
    def get(self):
        return self.response('Hello world!')

#####################################
## SECOND and more complex EXAMPLE

## Works with requests to:
# GET /api/another/path
# GET /api/another/path/:identifier
# POST /api/another/path (respond with null)

@decorate.enable_endpoint_identifier('identifier')
class FooTwo(ExtendedApiResource):
    """ Example with use of myid """

    # Specify a different endpoint
    endpoint = 'another/path'

    @decorate.apimethod
    def get(self, identifier=None):
        logger.debug("Using different endpoint")
        key = 'hello'

        # I want to check if /api/another/path/identifier is empty
        if identifier is not None:
            key += ' ' + identifier
            logger.info("Using data key '%s'" % identifier)
            #return self.response("error")

        obj = {key: 'new endpoint'}
        return self.response(obj)

    @decorate.apimethod
    def post(self, identifier=None):
        """ I do nothing """
        pass

#####################################
## THIRD EXAMPLE with parameters

## Works with requests to:
# GET /api/another/path?myarg=a
# POST /api/another/path?arg2=3&arg3=test

class FooThree(ExtendedApiResource):
    """
    Example with parameters.
    Add as many parameter in a decorator stack on top of the method.

    BEWARE: the decorator 'apimethod' has to be the innermost in the stack
    OTHERWISE NO PARAMETERS WILL BE SEEN
    """

    # Adding parameter with decorator
    @decorate.add_endpoint_parameter('myarg')
    @decorate.apimethod
    def get(self):
        logger.debug("Received args %s" % self._args)
# Test an exception
        #return pippo
        return self.response(self._args)

    # Adding parameters with decorator in different ways
    @decorate.add_endpoint_parameter('arg1', str)
    @decorate.add_endpoint_parameter('arg2', ptype=int)
    @decorate.add_endpoint_parameter(name='arg3', ptype=str)
    @decorate.apimethod
    def post(self):
        logger.debug("Received args %s" % self._args)
        return self.response(self._args, fail=True)
