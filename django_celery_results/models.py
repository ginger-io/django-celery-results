"""Database models."""
from __future__ import absolute_import, unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from celery import states
from celery.five import python_2_unicode_compatible

from . import managers

import io
import gzip
import logging
from .utils import disable_logging

ALL_STATES = sorted(states.ALL_STATES)
TASK_STATE_CHOICES = sorted(zip(ALL_STATES, ALL_STATES))


@python_2_unicode_compatible
class TaskResult(models.Model):
    """Task result/status."""

    task_id = models.CharField(
        _('task id'),
        max_length=255, unique=True,
    )
    status = models.CharField(
        _('state'),
        max_length=50, default=states.PENDING,
        choices=TASK_STATE_CHOICES,
    )
    content_type = models.CharField(
        _('content type'), max_length=128,
    )
    content_encoding = models.CharField(
        _('content encoding'), max_length=64,
    )

    # Warning: access the result via the `inflated` getter/setter which handles gzipping/unzipping,
    #          do not acccess result data directly.
    result = models.BinaryField(null=True, default=None, editable=False)
    date_done = models.DateTimeField(_('done at'), auto_now=True)
    traceback = models.TextField(_('traceback'), blank=True, null=True)
    hidden = models.BooleanField(editable=False, default=False, db_index=True)
    meta = models.TextField(null=True, default=None, editable=False)

    objects = managers.TaskResultManager()

    class Meta:
        """Table information."""

        verbose_name = _('task result')
        verbose_name_plural = _('task results')

    def as_dict(self):
        return {
            'task_id': self.task_id,
            'status': self.status,
            'result': self.inflated,
            'date_done': self.date_done,
            'traceback': self.traceback,
            'meta': self.meta,
        }

    @property
    def inflated(self):
        """
        Unzipped result.
        :return:
        """
        if self.result is None:
            return None

        in_ = io.BytesIO()
        in_.write(self.result)
        in_.seek(0)
        with gzip.GzipFile(fileobj=in_, mode='rb') as fo:
            gunzipped_bytes_obj = fo.read()

        return gunzipped_bytes_obj.decode('utf-8')

    @inflated.setter
    def inflated(self, uncompressed):
        """
        Gzips the provided uncompressed value into the result field.
        :param uncompressed: serialized input data
        :return:
        """
        if uncompressed is None:
            self.result = None
            return

        # Gzip it for storage.
        out = io.BytesIO()
        with gzip.GzipFile(fileobj=out, mode='w') as fo:
            fo.write(uncompressed.encode('utf-8'))
        self.result = out.getvalue()

    def save(self, *args, **kwargs):
        """
        MySQL django backend issues warnings when BinaryField is sent
        non text encoded bytes.

        This suppresses these superflous warnings.
        :param args:
        :param kwargs:
        :return:
        """
        with disable_logging(logging.WARNING):
            super(TaskResult, self).save(*args, **kwargs)


    def __str__(self):
        return '<Task: {0.task_id} ({0.status})>'.format(self)
