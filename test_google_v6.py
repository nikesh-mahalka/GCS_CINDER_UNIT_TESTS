# Copyright (C) 2012 Hewlett-Packard Development Company, L.P.
# Copyright (C) 2015 Biarca
# Copyright (C) 2015 Google
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
"""
Tests for Google Backup code.

"""

import bz2
import ddt
import filecmp
import hashlib
import os
import shutil
import tempfile
import zlib

import mock
from oslo_config import cfg

from cinder import db
from cinder import context
from cinder import exception
from cinder.i18n import _
from cinder import objects
from cinder import test
from cinder.backup.drivers import google as google_dr
from cinder.tests.unit.backup import fake_google_client


def fake_md5(arg):
    class result(object):
        def digest(self):
            return 'gcscindermd5'

        def hexdigest(self):
            return 'gcscindermd5'

    ret = result()
    return ret


@ddt.ddt
class GoogleBackupDriverTestCase(test.TestCase):
    """Test Case for Google"""

    _DEFAULT_VOLUME_ID = 'c7eb81f4-bec6-4730-a60f-8888885874df'

    def _create_volume_db_entry(self, volume_id=_DEFAULT_VOLUME_ID):
        vol = {'id': volume_id,
               'size': 1,
               'status': 'available'}
        return db.volume_create(self.ctxt, vol)['id']

    def _create_backup_db_entry(self,
                                volume_id=_DEFAULT_VOLUME_ID,
                                container=google_dr.CONF.backup_gcs_bucket,
                                backup_id=123, parent_id=None,
                                service_metadata=None):

        try:
            db.volume_get(self.ctxt, volume_id)
        except exception.NotFound:
            self._create_volume_db_entry(volume_id=volume_id)

        backup = {'id': backup_id,
                  'size': 1,
                  'container': container,
                  'volume_id': volume_id,
                  'parent_id': parent_id,
                  'user_id': 'user-id',
                  'project_id': 'project-id',
                  'service_metadata': service_metadata,
                  }
        return db.backup_create(self.ctxt, backup)['id']

    def setUp(self):
        self.flags(backup_gcs_bucket='gcscinderbucket')
        self.flags(backup_gcs_credential_file=None)
        super(GoogleBackupDriverTestCase, self).setUp()
        self.ctxt = context.get_admin_context()
        self.stubs.Set(hashlib, 'md5', fake_md5)
        self.stubs.Set(google_dr.discovery, 'build', fake_google_client.FakeGoogleDiscovery.Build)
        self.stubs.Set(google_dr.client, 'GoogleCredentials', fake_google_client.FakeGoogleCredentials) 
        self.volume_file = tempfile.NamedTemporaryFile()
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(self.volume_file.close)
        # Remove tempdir.
        self.addCleanup(shutil.rmtree, self.temp_dir)
        for _i in range(0, 64):
            self.volume_file.write(os.urandom(1024))                      
       
        notify_patcher = mock.patch(
            'cinder.volume.utils.notify_about_backup_usage')
        notify_patcher.start()
        self.addCleanup(notify_patcher.stop)


    def test_backup(self):
        volume_id = 'b09b1ad4-5f0e-4d3f-8b9e-0000004f5ec2'
        container_name = 'test-bucket'
        self._create_backup_db_entry(volume_id=volume_id,
                                     container=container_name)
        service = google_dr.GoogleBackupDriver(self.ctxt)
        self.volume_file.seek(0)
        backup = objects.Backup.get_by_id(self.ctxt, 123)
        result = service.backup(backup, self.volume_file)
        self.assertEqual(None, result)

    def test_backup_uncompressed(self):
        volume_id = '2b9f10a3-42b4-4fdf-b316-000000ceb039'
        self._create_backup_db_entry(volume_id=volume_id)
        self.flags(backup_compression_algorithm='none')
        service = google_dr.GoogleBackupDriver(self.ctxt)
        self.volume_file.seek(0)
        backup = objects.Backup.get_by_id(self.ctxt, 123)
        service.backup(backup, self.volume_file)

    def test_backup_bz2(self):
        volume_id = 'dc0fee35-b44e-4f13-80d6-000000e1b50c'
        self._create_backup_db_entry(volume_id=volume_id)
        self.flags(backup_compression_algorithm='bz2')
        service = google_dr.GoogleBackupDriver(self.ctxt)
        self.volume_file.seek(0)
        backup = objects.Backup.get_by_id(self.ctxt, 123)
        service.backup(backup, self.volume_file)
