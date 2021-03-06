import logging

import requests  # noqa: F401
from jsonpath_rw import parse
from typing import Any  # noqa: F401

from databuilder.rest_api.rest_api_query import RestApiQuery

#  How many records considers as full and indicating there might be next page? In list reports on space API, it's 30.
DEFAULT_MAX_RECORD_SIZE = 30
PAGE_SUFFIX_TEMPLATE = '?page={}'

LOGGER = logging.getLogger(__name__)


class ModePaginatedRestApiQuery(RestApiQuery):
    """
    Certain API such as get list of reports on a space is paginated with query term page.
    https://mode.com/developer/api-cookbook/management/get-all-reports/

    This subclass makes sure to detect if there's more page and update URL to get next page.
    """

    def __init__(self,
                 pagination_json_path,  # type: str
                 max_record_size=DEFAULT_MAX_RECORD_SIZE,  # type: int
                 **kwargs  # type: Any
                 ):
        # type (...) -> None
        super(ModePaginatedRestApiQuery, self).__init__(**kwargs)

        self._original_url = self._url
        self._max_record_size = max_record_size
        self._current_page = 1
        self._pagination_jsonpath_expr = parse(pagination_json_path)

    def _preprocess_url(self,
                        record,  # type: Dict[str, Any]
                        ):
        # type: (...) -> str
        """
        Updates URL with page information
        :param record:
        :return: a URL that is ready to be called.
        """
        page_suffix = PAGE_SUFFIX_TEMPLATE.format(self._current_page)  # example: ?page=2

        # example: http://foo.bar/resources?page=2
        self._url = self._original_url + '{page_suffix}'.format(original_url=self._original_url,
                                                                page_suffix=page_suffix)
        return self._url.format(**record)

    def _post_process(self,
                      response,  # type: requests.Response
                      ):
        # type: (...) -> None
        """
        Updates trigger to pagination (self._more_pages) as well as current_page (self._current_page)
        Mode does not have explicit indicator that it just the number of records need to be certain number that
        implying that there could be more records on next page.
        :return:
        """

        result_list = [match.value for match in self._pagination_jsonpath_expr.find(response.json())]

        if result_list and len(result_list) >= self._max_record_size:
            self._more_pages = True
            self._current_page = self._current_page + 1
            return

        self._more_pages = False
        self._current_page = 1
