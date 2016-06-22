# -*- coding: utf-8 -*-
from googleads.common import ProxyConfig
from requests import Session
from suds_requests import RequestsTransport


class RequestsProxyConfig(ProxyConfig):
    """
    A utility for configuring the usage of requests.
    """
    def __init__(self, http_proxy=None, https_proxy=None, cafile=None,
                 disable_certificate_validation=False):
        self._session = Session()
        proxies = self._session.proxies
        if http_proxy:
            proxies['http'] = str(http_proxy)
        if https_proxy:
            proxies['https'] = str(https_proxy)
        if cafile:
            self._session.verify = cafile
        elif disable_certificate_validation:
            self._session.verify = False

    def GetHandlers(self):
        """
        Dummy.

        Returns:
          A list of urllib2.BaseHandler subclasses to be used when making calls
          with proxy.
        """
        return []

    def GetSudsProxyTransport(self):
        """
        Retrieve a suds.transport.http.HttpTransport to be used with suds.

        Returns:
          A RequestsTransport instance used to make requests with suds using the
          requests transport.
        """
        return RequestsTransport(self._session)

    @property
    def session(self):
        return self._session
