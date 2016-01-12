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
from cinder.tests.unit.backup import fake_google_client2

def fake_md5(arg):
    class result(object):
        def digest(self):
            return 'gcscindermd5'

        def hexdigest(self):
            return 'gcscindermd5'

    ret = result()
    return ret


class FakeObjectName(object):
    @classmethod
    def _fake_generate_object_name_prefix(self, backup):
        az = 'az_fake'
        backup_name = '%s_backup_%s' % (az, backup['id'])
        volume = 'volume_%s' % (backup['volume_id'])
        prefix = volume + '_' + backup_name
        return prefix


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
        self.stubs.Set(google_dr,
                       'GoogleMediaIoBaseDownload',
                       fake_google_client.FakeGoogleMediaIoBaseDownload)
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

    def test_backup_default_container(self):
        volume_id = '9552017f-c8b9-4e4e-a876-00000053349c'
        self._create_backup_db_entry(volume_id=volume_id,
                                     container=None)
        service = google_dr.GoogleBackupDriver(self.ctxt)
        self.volume_file.seek(0)
        backup = objects.Backup.get_by_id(self.ctxt, 123)
        service.backup(backup, self.volume_file)
        backup = objects.Backup.get_by_id(self.ctxt, 123)
        self.assertEqual('gcscinderbucket', backup['container'])

    @mock.patch('cinder.backup.drivers.google.GoogleBackupDriver.'
                '_send_progress_end')
    @mock.patch('cinder.backup.drivers.google.GoogleBackupDriver.'
                '_send_progress_notification')
    def test_backup_default_container_notify(self, _send_progress,
                                             _send_progress_end):
        volume_id = '87dd0eed-2598-4ebd-8ebb-000000ac578a'
        self._create_backup_db_entry(volume_id=volume_id,
                                     container=None)
        # If the backup_object_number_per_notification is set to 1,
        # the _send_progress method will be called for sure.
        google_dr.CONF.set_override("backup_object_number_per_notification", 1)
        google_dr.CONF.set_override("backup_gcs_enable_progress_timer", False)
        service = google_dr.GoogleBackupDriver(self.ctxt)
        self.volume_file.seek(0)
        backup = objects.Backup.get_by_id(self.ctxt, 123)
        service.backup(backup, self.volume_file)
        self.assertTrue(_send_progress.called)
        self.assertTrue(_send_progress_end.called)

        # If the backup_object_number_per_notification is increased to
        # another value, the _send_progress method will not be called.
        _send_progress.reset_mock()
        _send_progress_end.reset_mock()
        google_dr.CONF.set_override("backup_object_number_per_notification", 10)
        service = google_dr.GoogleBackupDriver(self.ctxt)
        self.volume_file.seek(0)
        backup = objects.Backup.get_by_id(self.ctxt, 123)
        service.backup(backup, self.volume_file)
        self.assertFalse(_send_progress.called)
        self.assertTrue(_send_progress_end.called)

        # If the timer is enabled, the _send_progress will be called,
        # since the timer can trigger the progress notification.
        _send_progress.reset_mock()
        _send_progress_end.reset_mock()
        google_dr.CONF.set_override("backup_object_number_per_notification", 10)
        google_dr.CONF.set_override("backup_gcs_enable_progress_timer", True)
        service = google_dr.GoogleBackupDriver(self.ctxt)
        self.volume_file.seek(0)
        backup = objects.Backup.get_by_id(self.ctxt, 123)
        service.backup(backup, self.volume_file)
        self.assertTrue(_send_progress.called)
        self.assertTrue(_send_progress_end.called)

    def test_backup_custom_container(self):
        volume_id = '1da9859e-77e5-4731-bd58-000000ca119e'
        container_name = 'fake99'
        self._create_backup_db_entry(volume_id=volume_id,
                                     container=container_name)
        service = google_dr.GoogleBackupDriver(self.ctxt)
        self.volume_file.seek(0)
        backup = objects.Backup.get_by_id(self.ctxt, 123)
        service.backup(backup, self.volume_file)
        backup = objects.Backup.get_by_id(self.ctxt, 123)
        self.assertEqual(container_name, backup['container'])

    def test_backup_shafile(self):
        volume_id = '6465dad4-22af-48f7-8a1a-000000218907'

        # Raise a pseudo exception.BackupDriverException.
        self.stubs.Set(google_dr.GoogleBackupDriver,
                       '_generate_object_name_prefix',
                       FakeObjectName._fake_generate_object_name_prefix)
        container_name = self.temp_dir.replace(tempfile.gettempdir() + '/',
                                               '', 1)
        self._create_backup_db_entry(volume_id=volume_id,
                                     container=container_name)
        self.stubs.Set(google_dr.discovery, 'build', fake_google_client2.FakeGoogleDiscovery.Build)
        self.stubs.Set(google_dr, 'GoogleMediaIoBaseDownload', fake_google_client2.FakeGoogleMediaIoBaseDownload)
        service = google_dr.GoogleBackupDriver(self.ctxt)
        self.volume_file.seek(0)
        backup = objects.Backup.get_by_id(self.ctxt, 123)
        service.backup(backup, self.volume_file)
        backup = objects.Backup.get_by_id(self.ctxt, 123)
        self.assertEqual(container_name, backup['container'])

        # Verify sha contents
        content1 = service._read_sha256file(backup)
        self.assertEqual(64 * 1024 / content1['chunk_size'],
                         len(content1['sha256s']))

    def test_backup_cmp_shafiles(self):
        volume_id = '1a99ac67-c534-4fe3-b472-0000001785e2'

        # Raise a pseudo exception.BackupDriverException.
        self.stubs.Set(google_dr.GoogleBackupDriver,
                       '_generate_object_name_prefix',
                       FakeObjectName._fake_generate_object_name_prefix)

        container_name = self.temp_dir.replace(tempfile.gettempdir() + '/',
                                               '', 1)
        self._create_backup_db_entry(volume_id=volume_id,
                                     container=container_name,
                                     backup_id=123)
        self.stubs.Set(google_dr.discovery, 'build', fake_google_client2.FakeGoogleDiscovery.Build)
        self.stubs.Set(google_dr, 'GoogleMediaIoBaseDownload', fake_google_client2.FakeGoogleMediaIoBaseDownload)
        service = google_dr.GoogleBackupDriver(self.ctxt)
        self.volume_file.seek(0)
        backup = objects.Backup.get_by_id(self.ctxt, 123)
        service.backup(backup, self.volume_file)
        backup = objects.Backup.get_by_id(self.ctxt, 123)
        self.assertEqual(container_name, backup['container'])

        # Create incremental backup with no change to contents
        self._create_backup_db_entry(volume_id=volume_id,
                                     container=container_name,
                                     backup_id=124,
                                     parent_id=123)
        self.stubs.Set(google_dr.discovery,
                       'build',
                       fake_google_client2.FakeGoogleDiscovery.Build)
        self.stubs.Set(google_dr,
                       'GoogleMediaIoBaseDownload',
                       fake_google_client2.FakeGoogleMediaIoBaseDownload)        
        service = google_dr.GoogleBackupDriver(self.ctxt)
        self.volume_file.seek(0)
        deltabackup = objects.Backup.get_by_id(self.ctxt, 124)
        service.backup(deltabackup, self.volume_file)
        deltabackup = objects.Backup.get_by_id(self.ctxt, 124)
        self.assertEqual(container_name, deltabackup['container'])

        # Compare shas from both files
        content1 = service._read_sha256file(backup)
        content2 = service._read_sha256file(deltabackup)

        self.assertEqual(len(content1['sha256s']), len(content2['sha256s']))
        self.assertEqual(set(content1['sha256s']), set(content2['sha256s']))

    def test_backup_delta_two_objects_change(self):
        volume_id = '30dab288-265a-4583-9abe-000000d42c67'

        # Raise a pseudo exception.BackupDriverException.
        self.stubs.Set(google_dr.GoogleBackupDriver,
                       '_generate_object_name_prefix',
                       FakeObjectName._fake_generate_object_name_prefix)
        self.flags(backup_gcs_object_size=8 * 1024)
        self.flags(backup_gcs_block_size=1024)

        container_name = self.temp_dir.replace(tempfile.gettempdir() + '/',
                                               '', 1)
        self._create_backup_db_entry(volume_id=volume_id,
                                     container=container_name,
                                     backup_id=123)
        self.stubs.Set(google_dr.discovery,
                       'build',
                       fake_google_client2.FakeGoogleDiscovery.Build)
        self.stubs.Set(google_dr,
                       'GoogleMediaIoBaseDownload',
                       fake_google_client2.FakeGoogleMediaIoBaseDownload)
        service = google_dr.GoogleBackupDriver(self.ctxt)
        self.volume_file.seek(0)
        backup = objects.Backup.get_by_id(self.ctxt, 123)
        service.backup(backup, self.volume_file)
        backup = objects.Backup.get_by_id(self.ctxt, 123)
        self.assertEqual(container_name, backup['container'])

        # Create incremental backup with no change to contents
        self.volume_file.seek(2 * 8 * 1024)
        self.volume_file.write(os.urandom(1024))
        self.volume_file.seek(4 * 8 * 1024)
        self.volume_file.write(os.urandom(1024))

        self._create_backup_db_entry(volume_id=volume_id,
                                     container=container_name,
                                     backup_id=124,
                                     parent_id=123)
        self.stubs.Set(google_dr.discovery,
                       'build',
                       fake_google_client2.FakeGoogleDiscovery.Build)
        self.stubs.Set(google_dr,
                       'GoogleMediaIoBaseDownload',
                       fake_google_client2.FakeGoogleMediaIoBaseDownload)

        service = google_dr.GoogleBackupDriver(self.ctxt)
        self.volume_file.seek(0)
        deltabackup = objects.Backup.get_by_id(self.ctxt, 124)
        service.backup(deltabackup, self.volume_file)
        deltabackup = objects.Backup.get_by_id(self.ctxt, 124)
        self.assertEqual(container_name, deltabackup['container'])

        content1 = service._read_sha256file(backup)
        content2 = service._read_sha256file(deltabackup)

        # Verify that two shas are changed at index 16 and 32
        self.assertNotEqual(content1['sha256s'][16], content2['sha256s'][16])
        self.assertNotEqual(content1['sha256s'][32], content2['sha256s'][32])

    def test_backup_backup_metadata_fail(self):
        """Test of when an exception occurs in backup().
        In backup(), after an exception occurs in
        self._backup_metadata(), we want to check the process of an
        exception handler.
        """
        volume_id = '020d9142-339c-4876-a445-000000f1520c'

        self._create_backup_db_entry(volume_id=volume_id)
        self.flags(backup_compression_algorithm='none')
        service = google_dr.GoogleBackupDriver(self.ctxt)
        self.volume_file.seek(0)
        backup = objects.Backup.get_by_id(self.ctxt, 123)

        def fake_backup_metadata(self, backup, object_meta):
            raise exception.BackupDriverException(message=_('fake'))

        # Raise a pseudo exception.BackupDriverException.
        self.stubs.Set(google_dr.GoogleBackupDriver, '_backup_metadata',
                       fake_backup_metadata)

        # We expect that an exception be notified directly.
        self.assertRaises(exception.BackupDriverException,
                          service.backup,
                          backup, self.volume_file)

    def test_backup_backup_metadata_fail2(self):
        """Test of when an exception occurs in an exception handler.
        In backup(), after an exception occurs in
        self._backup_metadata(), we want to check the process when the
        second exception occurs in self.delete().
        """
        volume_id = '2164421d-f181-4db7-b9bd-000000eeb628'

        self._create_backup_db_entry(volume_id=volume_id)
        self.flags(backup_compression_algorithm='none')
        service = google_dr.GoogleBackupDriver(self.ctxt)
        self.volume_file.seek(0)
        backup = objects.Backup.get_by_id(self.ctxt, 123)

        def fake_backup_metadata(self, backup, object_meta):
            raise exception.BackupDriverException(message=_('fake'))

        # Raise a pseudo exception.BackupDriverException.
        self.stubs.Set(google_dr.GoogleBackupDriver, '_backup_metadata',
                       fake_backup_metadata)

        def fake_delete(self, backup):
            raise exception.BackupOperationError()

        # Raise a pseudo exception.BackupOperationError.
        self.stubs.Set(google_dr.GoogleBackupDriver, 'delete', fake_delete)

        # We expect that the second exception is notified.
        self.assertRaises(exception.BackupOperationError,
                          service.backup,
                          backup, self.volume_file)

    def test_restore(self):
        volume_id = 'c2a81f09-f480-4325-8424-00000071685b'
        self._create_backup_db_entry(volume_id=volume_id)
        service = google_dr.GoogleBackupDriver(self.ctxt)

        with tempfile.NamedTemporaryFile() as volume_file:
            backup = objects.Backup.get_by_id(self.ctxt, 123)
            service.restore(backup, volume_id, volume_file)
