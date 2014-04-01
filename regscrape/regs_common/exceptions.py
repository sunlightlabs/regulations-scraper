class ExtractionFailed(Exception):
    pass

class DoesNotExist(Exception):
    pass

class ChildTimeout(Exception):
    pass

class RateLimitException(Exception):
    pass