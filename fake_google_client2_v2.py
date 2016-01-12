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

import tempfile

class FakeGoogleObjectExecute():

    def execute(self, *args, **kwargs):
        return {u'md5Hash': u'Z2NzY2luZGVybWQ1'}

            
class FakeGoogleBucketListExecute():

    def execute(self, *args, **kwargs):
        return {u'items': [{u'name': u'gcscinderbucket'}, {u'name': u'gcsbucket'}]} 

class FakeGoogleBucketInsertExecute():
    def execute(self, *args, **kwargs):
        pass

class FakeMediaObject(object):
    def __init__(self, bucket_name, object_name):
        self.bucket_name = bucket_name
        self.object_name = object_name

class FakeGoogleObject(object):
   
    def insert(self, *args, **kwargs):
        object_path = tempfile.gettempdir() + '/' + kwargs['bucket'] + '/' + kwargs['name']
        kwargs['media_body']._fd.getvalue()
        with open(object_path, 'wb') as object_file: 
            kwargs['media_body']._fd.seek(0)
            object_file.write(kwargs['media_body']._fd.read())
                
        return FakeGoogleObjectExecute()

    def get_media(self, *args, **kwargs):
        return FakeMediaObject(kwargs['bucket'], kwargs['object'])  


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
        object_path = tempfile.gettempdir() + '/' + req.bucket_name + '/' + req.object_name
        with open(object_path, 'rb') as object_file:
            fh.write(object_file.read())

    def next_chunk(self, **kwargs):
        return (100, True)
