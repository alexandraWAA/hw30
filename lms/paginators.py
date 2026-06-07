from rest_framework.pagination import PageNumberPagination


class CoursePaginator(PageNumberPagination):
    """
    Пагинатор для курсов
    """
    page_size = 10  # Количество элементов на странице по умолчанию
    page_size_query_param = 'page_size'  # Параметр для изменения размера страницы
    max_page_size = 50  # Максимальный размер страницы


class LessonPaginator(PageNumberPagination):
    """
    Пагинатор для уроков
    """
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 50