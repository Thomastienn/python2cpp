import sys, io
class Utils:
    # List of names of template used
    template_uses: set[str] = set()
    def get_file_no_ext(filename):
        if "." in filename:
            return filename.split(".")[0]
        else:
            return filename
    def capture_output(func, *args):
        original = sys.stdout
        sys.stdout = io.StringIO()
        func(*args)
        output = sys.stdout.getvalue()
        sys.stdout = original
        return output




