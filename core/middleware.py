import traceback
import sys

class ExceptionLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            print(f"[MIDDLEWARE] Processing request: {request.path}", file=sys.stderr)
            response = self.get_response(request)
            print(f"[MIDDLEWARE] Response status: {response.status_code}", file=sys.stderr)
            return response
        except Exception as e:
            print("=" * 50, file=sys.stderr)
            print(f"EXCEPTION in __call__ on {request.path}:", file=sys.stderr)
            print(f"Exception type: {type(e).__name__}", file=sys.stderr)
            print(f"Exception message: {str(e)}", file=sys.stderr)
            print("Traceback:", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            print("=" * 50, file=sys.stderr)
            raise

    def process_exception(self, request, exception):
        print("=" * 50, file=sys.stderr)
        print(f"EXCEPTION on {request.path}:", file=sys.stderr)
        print(f"Exception type: {type(exception).__name__}", file=sys.stderr)
        print(f"Exception message: {str(exception)}", file=sys.stderr)
        print("Traceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print("=" * 50, file=sys.stderr)
        return None
