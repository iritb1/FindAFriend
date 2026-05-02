class Singleton:
    """Decorator class that ensures only one instance per unique arguments."""

    def __init__(self, cls):
        self._cls = cls
        self._instances = {}

    def __call__(self, *args, **kwargs):
        key = args + tuple(sorted(kwargs.items()))
        if key not in self._instances:
            self._instances[key] = self._cls(*args, **kwargs)
        return self._instances[key]
