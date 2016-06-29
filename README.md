# Googleads-Requests

Python `Requests` for Google Ads API client and utilities.

# Overview

The [Google Ads API client for Python](https://github.com/googleads/googleads-python-lib) is based on
[Suds](https://fedorahosted.org/suds/) for communicating with the SOAP endpoint. By default, Suds uses Python's built-in
`urllib2` as a transport and that is also wired into utilities of the API client library. Issues have been reported
related to `urllib2` (e.g. [#88](https://github.com/googleads/googleads-python-lib/issues/88)), especially when using
special characters in AdWords content.

Using the popular [Requests library](http://docs.python-requests.org) has several advantages. Its use is straightforward
and it has well-tested practices for dealing with content encoding and decoding. Besides that, it has built-in
connection pooling through `urllib3`.

`Googleads-Requests` provides lightweight wrappers for using the Requests library as a transport instead of `urllib2`
for accessing reports and services on the Google AdWords and DFP API. On the service client, this is accomplished
through Suds' support for custom transports, implemented by [suds_requests](https://github.com/armooo/suds_requests).
For utilities such as the `ReportDownloader`, derived implementations are provided.

Please note that this library is not supported or endorsed by Google. It uses private variables and overrides private
methods in `googleads` for avoiding redundancy, but might be broken on any update.

# Installation

This implementation uses `suds_requests`, but installation is needed without further dependencies. Since it declares
`suds` as a dependent package, it would break an existing installation of `suds-jurko`. `suds-requests` is therefore
not included in the setup directly:

```bash
pip install --no-deps suds_requests
```

`Googleads-Requests` can be installed from the repository by using the latest release tag, e.g.

```bash
pip install git+https://github.com/Precis/googleads-requests.git@1.2.0#egg=googleads-requests
```

# Getting started

Where applicable, `Googleads-Requests` uses the same function names and arguments as `googleads` (even following its
strange naming conventions) for providing compatibility.

## Client

When instantiating a service client, a proxy configuration has to be created. That can be passed to the client
constructor:

```python
from googleads.adwords import AdWordsClient
from googleads_requests.common import RequestsProxyConfig

...
proxy_config = RequestsProxyConfig()
client = AdWordsClient(developer_token, oauth2_client, user_agent, proxy_config=proxy_config)
```

Although it is optional, you can pass the same arguments to `RequestsProxyConfig` as for
`googleads.common.ProxyConfig`, e.g. for actual http/https proxy configuration.

## Utilities

Instead of using `GetBatchJobHelper` and `GetReportDownloader`, instantiate alternative implementations of
`ReportDownloader` or `BatchJobHeler` directly using the client instance as created above:

```python
from googleads_requests.utils import AdwordsReportDownloader

report_downloader = AdwordsReportDownloader(client)
```

or 

```python
from googleads_requests.utils import get_batch_job_helper

batch_job_helper = get_batch_job_helper(client)
```
