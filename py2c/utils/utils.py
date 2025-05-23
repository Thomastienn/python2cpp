def get_file_no_ext(filename):
    if "." in filename:
        return filename.split(".")[0]
    else:
        return filename

