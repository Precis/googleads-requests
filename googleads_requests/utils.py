# -*- coding: utf-8 -*-
from requests import Request
import suds
import xmltodict

try:
    from xml.etree import cElementTree as ET
except ImportError:
    from xml.etree import ElementTree as ET

from googleads.adwords import (ReportDownloader, _SERVICE_MAP, _DEFAULT_ENDPOINT, _REPORT_HEADER_KWARGS,
                               BatchJobHelper)
from googleads.common import GenerateLibSig
from googleads.dfp import DataDownloader
from googleads.errors import (GoogleAdsValueError, AdWordsReportBadRequestError, AdWordsReportError,
                              AdWordsBatchJobServiceInvalidOperationError)

LIB_SIGNATURE = GenerateLibSig('AwApi-Python')
DOWNLOADER_CONTENT_TYPE = 'application/x-www-form-urlencoded'
UPLOAD_URL_INIT_HEADERS = {
    'Content-Type': 'application/xml',
    'Content-Length': 0,
    'x-goog-resumable': 'start'
}
LATEST_VERSION = sorted(_SERVICE_MAP.keys())[-1]


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


def get_batch_job_helper(client, version=LATEST_VERSION, server=_DEFAULT_ENDPOINT):
    request_builder = AdwordsBatchJobHelper.GetRequestBuilder(client=client, version=version, server=server)
    response_parser = AdwordsBatchJobHelper.GetResponseParser()
    return AdwordsBatchJobHelper(request_builder, response_parser, version=version)


class SudsRequestBuilder(BatchJobHelper._SudsUploadRequestBuilder):
    def BuildUploadRequest(self, upload_url, operations, current_content_length=0, is_last=None, **kwargs):
        """
        Builds the BatchJob upload request.

        :param upload_url: a string url that the given operations will be uploaded to.
        :param operations: a list where each element is a list containing operations
            for a single AdWords Service.
        :param current_content_length: an integer indicating the current total content
          length of an incremental upload request. If this keyword argument is
          provided, this request will be handled as an incremental upload.
        :param is_last: a boolean indicating whether this is the final request in an
          incremental upload.
        :param kwargs: Optional keyword arguments.
        :return: Request instance.
        :rtype: requests.models.PreparedRequest
        """
        # Generate an unpadded request body
        request_body = self._BuildUploadRequestBody(
            operations,
            has_prefix=current_content_length == 0,
            has_suffix=is_last)
        # Determine length of this message and the required padding.
        new_content_length = current_content_length
        request_data = request_body.encode('utf-8')
        request_length = len(request_data)
        padding_length = self._GetPaddingLength(request_length)
        padded_request_length = request_length + padding_length
        new_content_length += padded_request_length
        request_data += ' ' * padding_length
        content_range = 'bytes {0}-{1}/{2}'.format(
            current_content_length,
            new_content_length - 1,
            new_content_length if is_last else '*'
        )
        headers = {
            'Content-Type': 'application/xml',
            'Content-Length': padded_request_length,
            'Content-Range': content_range,
        }
        request = Request('PUT', upload_url, headers=headers, data=request_data)
        return request.prepare()


class XMLResultParser(BatchJobHelper.AbstractResponseParser):
    def ParseResponse(self, batch_job_response):
        return xmltodict.parse(batch_job_response, force_list=('rval', ))


class IncrementalUploadHelper(object):
    """
    A utility for uploading operations for a BatchJob incrementally.

    :param request_builder: a SudsRequestBuilder instance.
    :param upload_url: a string url provided by the BatchJobService.
    :param current_content_length: an integer identifying the current content length
        of data uploaded to the Batch Job.
    :param is_last: a boolean indicating whether this is the final increment.
    :param version: A string identifying the AdWords version to connect to. This
        defaults to what is currently the latest version. This will be updated
        in future releases to point to what is then the latest version.
    :raises GoogleAdsValueError: if the content length is lower than 0.
    """
    def __init__(self, request_builder, upload_url, current_content_length=0,
                 is_last=False, version=LATEST_VERSION):
        self._version = version
        self._request_builder = request_builder
        if current_content_length < 0:
            raise GoogleAdsValueError(
                "Current content length %s is < 0." % current_content_length)
        self._current_content_length = current_content_length
        self._session = session = request_builder.client.proxy_config.session
        if current_content_length != 0:
            self._upload_url = upload_url
        else:
            response = session.post(upload_url, headers=UPLOAD_URL_INIT_HEADERS)
            self._upload_url = response.headers['location']
        self._is_last = is_last

    def UploadOperations(self, operations, is_last=False):
        if self._is_last:
            raise AdWordsBatchJobServiceInvalidOperationError(
                "Can't add new operations to a completed incremental upload.")
        # Build the request
        request = self._request_builder.BuildUploadRequest(
            self._upload_url, operations, current_content_length=self._current_content_length, is_last=is_last
        )
        response = self._session.send(request)
        response.raise_for_status()
        # Update upload status.
        self._current_content_length += len(request.body)
        self._is_last = is_last


class AdwordsBatchJobHelper(BatchJobHelper):
    def GetIncrementalUploadHelper(self, upload_url, current_content_length=0):
        return IncrementalUploadHelper(self._request_builder, upload_url, current_content_length,
                                       version=self._version)

    @classmethod
    def GetRequestBuilder(cls, **kwargs):
        return SudsRequestBuilder(**kwargs)

    @classmethod
    def GetResponseParser(cls, **kwargs):
        return XMLResultParser(**kwargs)

    def UploadOperations(self, upload_url, *operations):
        uploader = IncrementalUploadHelper(self._request_builder, upload_url,
                                           version=self._version)
        uploader.UploadOperations(operations, is_last=True)


class AdwordsReportDownloader(ReportDownloader):
    chunk_size = 8192

    def _post(self, post_body, kwargs, stream=False):
        client = self._adwords_client
        session = client.proxy_config.session
        headers = client.oauth2_client.CreateHttpHeader()
        headers.update({
            'Content-type': DOWNLOADER_CONTENT_TYPE,
            'developerToken': client.developer_token,
            'User-Agent': '{0}{1},gzip'.format(client.user_agent, LIB_SIGNATURE),
        })
        report_kwargs = client.report_download_headers.copy()
        report_kwargs.update(kwargs)
        report_kwargs.setdefault('client_customer_id', client.client_customer_id)
        headers.update(get_report_headers(report_kwargs))
        response = session.post(self._end_point, data=post_body, headers=headers, stream=stream)
        if response.status_code >= 400 < 500:
            e = extract_report_error(response)
            response.close()
            raise e
        response.raise_for_status()
        return response

    def DownloadReportAsString(self, report_definition, **kwargs):
        return self._post(self._SerializeReportDefinition(report_definition), kwargs).text

    def DownloadReportAsStringWithAwql(self, query, file_format, **kwargs):
        return self._post(self._SerializeAwql(query, file_format), kwargs).text

    def _DownloadReport(self, post_body, output, **kwargs):
        response = self._post(post_body, kwargs, stream=True)
        try:
            for buf in response.iter_content(self.chunk_size):
                output.write(buf)
            output.flush()
        finally:
            response.close()

    def _DownloadReportAsStream(self, post_body, **kwargs):
        return self._post(post_body, kwargs, stream=True)

    def _SerializeAwql(self, query, file_format):
        return {'__fmt': file_format, '__rdquery': query}

    def _SerializeReportDefinition(self, report_definition):
        content = suds.mx.Content(
            tag=self._REPORT_DEFINITION_NAME, value=report_definition,
            name=self._REPORT_DEFINITION_NAME, type=self._report_definition_type)
        return {'__rdxml': self._marshaller.process(content).plain()}


class DfpDataDownloader(DataDownloader):
    chunk_size = 8192

    def DownloadReportToFile(self, report_job_id, export_format, outfile,
                             include_report_properties=False,
                             include_totals_row=None, use_gzip_compression=True):
        service = self._GetReportService()
        if include_totals_row is None:  # True unless CSV export if not specified
            include_totals_row = True if export_format != 'CSV_DUMP' else False
        opts = {
            'exportFormat': export_format,
            'includeReportProperties': include_report_properties,
            'includeTotalsRow': include_totals_row,
            'useGzipCompression': use_gzip_compression
        }
        report_url = service.getReportDownloadUrlWithOptions(report_job_id, opts)
        session = self.proxy_config.session
        response = session.get(report_url, stream=True)
        try:
            response.raise_for_status()
            for buf in response.iter_content(self.chunk_size):
                outfile.write(buf)
            outfile.flush()
        finally:
            response.close()
