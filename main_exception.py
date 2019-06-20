# -*- coding: utf-8 -*-

from google.appengine.ext import deferred
import logging
import webapp2

class SafeRequestHandler(webapp2.RequestHandler):
    def handle_exception(self, exception, debug_mode):
        report_exception()

def deferredSafeHandleException(obj, *args, **kwargs):
    deferred.defer(safeHandleException, obj, *args, **kwargs)

def safeHandleException(obj, *args, **kwargs):
    try:
        obj(*args, **kwargs)
    except:  # catch *all* exceptions
        report_exception()
        # raise deferred.PermanentTaskFailure

def report_exception():
    from main import tell_admin
    import traceback
    msg = "❗ Detected Exception: " + traceback.format_exc()
    tell_admin(msg)
    logging.error(msg)


