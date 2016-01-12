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
import tempfile
from six.moves import http_client


class FakeGoogleObjectInsertExecute(object):

    def execute(self, *args, **kwargs):
        return {u'md5Hash': u'Z2NzY2luZGVybWQ1'}

class FakeGoogleObjectListExecute(object):

    def execute(self, *args, **kwargs):
        return {'items': [{'name': 'backup_001'},
                          {'name': 'backup_002'},
                          {'name': 'backup_003'}]}
            
class FakeGoogleBucketListExecute(object):

    def execute(self, *args, **kwargs):
        return {u'items': [{u'name': u'gcscinderbucket'}, {u'name': u'gcsbucket'}]} 

class FakeGoogleBucketInsertExecute(object):
    def execute(self, *args, **kwargs):
        pass

class FakeMediaObject(object):
    def __init__(self, bucket_name, object_name):
        self.bucket_name = bucket_name
        self.object_name = object_name

class FakeGoogleObject(object):
   
    def insert(self, *args, **kwargs):
        return FakeGoogleObjectInsertExecute()

    def get_media(self, *args, **kwargs):
        return FakeMediaObject(kwargs['bucket'], kwargs['object'])

    def list(self, *args, **kwargs):
        return FakeGoogleObjectListExecute()
        


class FakeGoogleBucket(object):

    def list(self, *args, **kwargs):
        return FakeGoogleBucketListExecute()

    def insert(self, *args, **kwargs):
        return FakeGoogleBucketInsertExecute()    

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

class FakeGoogleMediaIoBaseDownload(object):
    def __init__(self, fh, req, chunksize=None):
        print "nikesh in FakeGoogleMediaIoBaseDownload"
        print req.bucket_name
        if 'metadata' in req.object_name:
            print "nikesh in if of FakeGoogleMediaIoBaseDownload"
            metadata = {}
            metadata['version'] = '1.0.0'
            metadata['backup_id'] = 123
            metadata['volume_id'] = 123
            metadata['backup_name'] = 'fake backup'
            metadata['backup_description'] = 'fake backup description'
            metadata['created_at'] = '2016-01-09 11:20:54,805'
            metadata['objects'] = [{
                'backup_001': {'compression': 'zlib', 'length': 10,
                               'offset': 0},
                'backup_002': {'compression': 'zlib', 'length': 10,
                               'offset': 10},
                'backup_003': {'compression': 'zlib', 'length': 10,
                               'offset': 20}
            }]
            metadata_json = json.dumps(metadata, sort_keys=True, indent=2)
            print "nikesh metadata_json", metadata_json
            if six.PY3:
                metadata_json = metadata_json.encode('utf-8')
            fh.write(metadata_json)
        else:
            print "nikesh in else of FakeGoogleMediaIoBaseDownload"
            fh.write(zlib.compress(os.urandom(1024 * 1024)))

    def next_chunk(self, **kwargs):
        return (100, True)
