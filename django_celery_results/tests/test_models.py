from __future__ import absolute_import, unicode_literals

from datetime import datetime, timedelta

from celery import states, uuid
from celery.five import text_t
from celery.tests.case import AppCase

from django_celery_results.models import TaskResult, GroupResult
from django_celery_results.utils import now


class test_Models(AppCase):

    def setup(self):
        self.app.conf.result_serializer = 'pickle'
        self.app.conf.result_backend = (
            'django_celery_results.backends:DatabaseBackend')
        self.app.set_current()
        self.app.set_default()

    def createTaskResult(self):
        id = uuid()
        taskmeta, created = TaskResult.objects.get_or_create(task_id=id)
        return taskmeta

    def createGroupResult(self):
        id = uuid()
        gr, created = GroupResult.objects.get_or_create(group_id=id)
        return gr

    def test_taskmeta(self):
        m1 = self.createTaskResult()
        m2 = self.createTaskResult()
        m3 = self.createTaskResult()
        self.assertTrue(text_t(m1).startswith('<Task:'))
        self.assertTrue(m1.task_id)
        self.assertIsInstance(m1.date_done, datetime)

        self.assertEqual(
            TaskResult.objects.get_task(m1.task_id).task_id,
            m1.task_id,
        )
        self.assertNotEqual(TaskResult.objects.get_task(m1.task_id).status,
                            states.SUCCESS)
        TaskResult.objects.store_result(
            m1.task_id, True, status=states.SUCCESS)
        TaskResult.objects.store_result(
            m2.task_id, True, status=states.SUCCESS)
        self.assertEqual(TaskResult.objects.get_task(m1.task_id).status,
                         states.SUCCESS)
        self.assertEqual(TaskResult.objects.get_task(m2.task_id).status,
                         states.SUCCESS)

        # Have to avoid save() because it applies the auto_now=True.
        TaskResult.objects.filter(
            task_id=m1.task_id
        ).update(date_done=now() - timedelta(days=10))

        expired = TaskResult.objects.get_all_expired(
            self.app.conf.result_expires,
        )
        self.assertIn(m1, expired)
        self.assertNotIn(m2, expired)
        self.assertNotIn(m3, expired)

        TaskResult.objects.delete_expired(
            self.app.conf.result_expires,
        )
        self.assertNotIn(m1, TaskResult.objects.all())

    def test_group_result(self):
        m1 = self.createGroupResult()
        m2 = self.createGroupResult()
        m3 = self.createGroupResult()
        self.assertTrue(text_t(m1).startswith('<Group: '))
        self.assertTrue(m1.group_id)
        self.assertIsInstance(m1.date_done, datetime)

        self.assertEqual(
            GroupResult.objects.restore_group(m1.group_id).group_id,
            m1.group_id,
        )

        # Have to avoid save() because it applies the auto_now=True.
        GroupResult.objects.filter(
            group_id=m1.group_id,
        ).update(date_done=now() - timedelta(days=10))

        expired = GroupResult.objects.get_all_expired(
            self.app.conf.result_expires,
        )
        self.assertIn(m1, expired)
        self.assertNotIn(m2, expired)
        self.assertNotIn(m3, expired)

        GroupResult.objects.delete_expired(
            self.app.conf.result_expires,
        )
        self.assertNotIn(m1, GroupResult.objects.all())

        m4 = self.createGroupResult()
        self.assertEqual(
            GroupResult.objects.restore_group(m4.group_id).group_id,
            m4.group_id,
        )

        GroupResult.objects.delete_group(m4.group_id)
        self.assertIsNone(GroupResult.objects.restore_group(m4.group_id))