__author__ = 'thunder'
__version__ = '0.3'

from flask import request
from thunderargs.endpoint import Endpoint
from thunderargs.helpers import wraps


class ThunderargsProxy(object):

    def __init__(self, app):
        self.app = app
        app.register_endpoint = self.register_endpoint
        app.froute = app.route
        app.route = self.route
        app._arg_taker = self._arg_taker

    def route(self, rule, **options):

        if options.get('dont_wrap'):
            del options['dont_wrap']
            return self.app.froute(rule, **options)

        def registrator(func):
            wrapped = self.register_endpoint(rule, func, **options)
            return wrapped

        return registrator


    def register_endpoint(self, rule, func, endpoint_name=None, **options):

        if 'methods' in options:
            method = options['methods'][0]
        elif 'method' in options:
            method = options['method']
        else:
            method = 'GET'
        endpoint_name = endpoint_name or "{}.{}".format(func.__name__, method)
        default_source = 'args' if method=='GET' else 'form'

        if not isinstance(func, Endpoint):
            func = Endpoint(func, default_source=default_source)

        wrapped = self._arg_taker(func)
        self.app.add_url_rule(rule, endpoint_name, wrapped,
                              methods=[method],
                              defaults=options.get('defaults', None))
        return func


    def _arg_taker(self, func):

        """
        Эта функция будет забирать аргументы из формы. Такие дела.
        """

        @wraps(func)
        def wrapper(*args, **kwargs):
            for key_name, arg_object in func.__annotations__.items():
                source = None
                if arg_object.source in ['form',
                                         'json',
                                         'headers',
                                         'args',
                                         'cookies']:
                    source = getattr(request, arg_object.source, {})
                else:
                    raise AttributeError("Unknown source: {}".format(arg_object.source))

                if arg_object.multiple and arg_object.source is not 'json':
                    kwargs[key_name] = source.getlist(key_name)
                else:
                    kwargs[key_name] = source.get(key_name)
            return func(*args, **kwargs)
        return wrapper