# -*- coding: utf-8 -*-
from requests import Session
from suds_requests import RequestsTransport


class RequestsProxyConfig(object):
    """
    A utility for configuring the usage of requests. Provides the same interface as
    :class:`googleads.common.ProxyConfig`.
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
        Dummy. The client prepares an urllib2 call, but we will not use it.

        :return: An empty list.
        :rtype: list
        """
        return []

    def GetSudsProxyTransport(self):
        """
        Retrieve a suds.transport.http.HttpTransport to be used with suds.

        :return: A RequestsTransport instance used to make requests with suds using the requests transport.
        :rtype: suds_requests.RequestsTransport
        """
        return RequestsTransport(self._session)

    @property
    def session(self):
        """
        Returns the session object.

        :return: Requests session to be used in suds.
        :rtype: requests.Session
        """
        return self._session
