from lib import create_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.serving import run_simple

main_flask_app = create_app()
application = DispatcherMiddleware(None, {
    '/deisi2006': main_flask_app
})

application = ProxyFix(application, x_for=1, x_proto=1)


if __name__ == "__main__":
    run_simple(hostname="0.0.0.0", port=9090, application=application)
