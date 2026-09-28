from rest_framework.pagination import PageNumberPagination


class StandardResultsPagination(PageNumberPagination):
    """
    Our default paging. Same page size as the global setting, but this one lets
    a client ask for a bigger page with ?page_size= (capped so nobody asks for
    10,000 rows at once).
    """

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
