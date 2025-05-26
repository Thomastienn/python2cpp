class Utils:
    # List of names of template used
    template_uses: set[str] = set()
    def get_file_no_ext(filename):
        if "." in filename:
            return filename.split(".")[0]
        else:
            return filename


