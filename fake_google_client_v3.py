# Copyright (C) 2012 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json
import os
import socket
import zlib

import six
from six.moves import http_client

from swiftclient import client as swift


class FakeGoogleObjectExecute():

    def execute(self, *args, **kwargs):
        return {u'md5Hash': u'Z2NzY2luZGVybWQ1'}

            
class FakeGoogleBucketExecute():

    def execute(self, *args, **kwargs):
        return {u'items': [{u'name': u'gcscinderbucket'}, {u'name': u'gcsbucket'}]} 


class FakeGoogleObject(object):
   
    def insert(self, *args, **kwargs):
        return FakeGoogleObjectExecute()

class FakeGoogleBucket(object):

    def list(self, *args, **kwargs):
        return FakeGoogleBucketExecute()    

class FakeGoogleDiscovery(object):
    """Logs calls instead of executing."""
    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def Build(self, *args, **kargs):
        return FakeDiscoveryBuild()


class FakeDiscoveryBuild(object):
    """Logging calls instead of executing."""
    def __init__(self, *args, **kwargs):
        pass

    def objects(self):
        return FakeGoogleObject() 

    def buckets(self):
        return FakeGoogleBucket()

class FakeGoogleCredentials(object):
    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def from_stream(self, *args, **kwargs):
        pass
