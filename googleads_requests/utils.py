# -*- coding: utf-8 -*-
import requests
try:
    from xml.etree import cElementTree as ET
except ImportError:
    from xml.etree import ElementTree as ET

from googleads.adwords import (ReportDownloaderBase, _SERVICE_MAP, _DEFAULT_ENDPOINT, _REPORT_HEADER_KWARGS,
                               BatchJobHelperBase)
from googleads.common import GenerateLibSig
from googleads.dfp import DataDownloaderBase
from googleads.errors import GoogleAdsValueError, AdWordsReportBadRequestError, AdWordsReportError


LIB_SIGNATURE = GenerateLibSig('AwApi-Python')
BATCHJOB_HELPER_HEADERS = {'Content-Type', 'application/xml'}
DOWNLOADER_CONTENT_TYPE = 'application/x-www-form-urlencoded'


def get_report_headers(kwargs):
    try:
        return {
            _REPORT_HEADER_KWARGS[kw]: kwargs[kw]
            for kw in kwargs
        }
    except KeyError as e:
        raise GoogleAdsValueError("Invalid keyword '{0}'. Valid keywords are: {1}'", e.args[0],
                                  _REPORT_HEADER_KWARGS.keys())


def extract_report_error(response):
    content = response.text
    try:
        tree = ET.fromstring(content)
    except ET.ParseError:
        pass
    else:
        if tree.tag == 'reportDownloadError':
            api_error = tree.find('ApiError')
            if api_error:
                return AdWordsReportBadRequestError(api_error.findtext('type'), api_error.findtext('trigger'),
                                                    api_error.findtext('fieldPath'), response.status_code, response,
                                                    content)
    return AdWordsReportError(response.status_code, response, content)


class AdwordsBatchJobHelper(BatchJobHelperBase):
    def UploadBatchJobOperations(self, upload_url, *operations):
        operations_xml = ''.join([
            self._GenerateOperationsXML(operations_list)
            for operations_list in operations])

        request_body = self._UPLOAD_REQUEST_BODY_TEMPLATE % (self._adwords_endpoint, operations_xml)
        response = requests.post(upload_url, data=request_body, headers=BATCHJOB_HELPER_HEADERS)
        response.raise_for_status()


class AdwordsReportDownloader(ReportDownloaderBase):
    chunk_size = 8192

    def __init__(self, adwords_client, version=sorted(_SERVICE_MAP.keys())[-1], server=_DEFAULT_ENDPOINT):
        super(AdwordsReportDownloader, self).__init__(adwords_client, version=version, server=server)
        self._session = requests.Session()
        if self._adwords_client.https_proxy:
            self._session.proxies = {'https': self._adwords_client.https_proxy}
        self._session.headers = {
            'Content-type': DOWNLOADER_CONTENT_TYPE,
            'developerToken': self._adwords_client.developer_token,
            'clientCustomerId': self._adwords_client.client_customer_id,
            'User-Agent': '{0}_{1},gzip'.format(self._adwords_client.user_agent, LIB_SIGNATURE),
        }

    def _post(self, post_body, kwargs, stream=False):
        headers = self._adwords_client.oauth2_client.CreateHttpHeader()
        headers.update(get_report_headers(kwargs))
        response = self._session.post(self._end_point, data=post_body, headers=headers, stream=stream)
        if response.status_code >= 400 < 500:
            e = extract_report_error(response)
            response.close()
            raise e
        response.raise_for_status()
        return response

    def _DownloadReport(self, post_body, output, kwargs):
        response = self._post(post_body, kwargs, stream=True)
        try:
            for buf in response.iter_content(self.chunk_size):
                output.write(buf)
            output.flush()
        finally:
            response.close()

    def _DownloadReportAsString(self, post_body, kwargs):
        return self._post(post_body, kwargs).text

    def _DownloadReportAsStream(self, post_body, kwargs):
        return self._post(post_body, kwargs, stream=True)


class DfpDataDownloader(DataDownloaderBase):
    chunk_size = 8192

    def DownloadReportToFile(self, report_job_id, export_format, outfile):
        service = self._GetReportService()
        report_url = service.getReportDownloadURL(report_job_id, export_format)
        response = requests.get(report_url, stream=True)
        try:
            response.raise_for_status()
            for buf in response.iter_content(self.chunk_size):
                outfile.write(buf)
            outfile.flush()
        finally:
            response.close()
