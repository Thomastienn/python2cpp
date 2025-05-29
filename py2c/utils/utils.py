import sys, io
class Utils:
    # List of names of template used. Must be the name of the enum
    template_uses: set[str] = set()
    def get_file_no_ext(filename):
        if "." in filename:
            return filename.split(".")[0]
        else:
            return filename
    def capture_output(func, *args, **kwargs):
        original = sys.stdout
        sys.stdout = io.StringIO()
        ret = func(*args)
        output = sys.stdout.getvalue()
        sys.stdout = original
        if "include_return" in kwargs and kwargs["include_return"]:
            return output, ret
        return output




