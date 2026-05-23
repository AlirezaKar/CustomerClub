"""
Django 5.0 + Python 3.14: ``BaseContext.__copy__`` uses ``copy(super())``, which raises.

This module replaces ``__copy__`` with Django’s newer pattern (fresh ``BaseContext``,
then copy ``__dict__`` and ``dicts``). No-op on Python < 3.14.
"""
import sys


def apply_patch():
    if sys.version_info < (3, 14):
        return
    from copy import copy
    from django.template.context import BaseContext

    def __copy__(self):
        duplicate = BaseContext()
        duplicate.__class__ = self.__class__
        duplicate.__dict__ = copy(self.__dict__)
        duplicate.dicts = self.dicts[:]
        return duplicate

    BaseContext.__copy__ = __copy__
