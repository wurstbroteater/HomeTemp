from core.core_configuration import load_config
from core.core_log import setup_logging, get_logger
from core.util import FileManager

load_config()
setup_logging()
log = get_logger(__name__)
if __name__ == "__main__":
    fm = FileManager("./testFolderStructure")

    fm.create_structure(["logs/la", "data", "configs"])
    # default: overwrite existing file
    fm.create_file("data/foo/bar/sample.txt", "Hello, World!asdasdasdsad")
    # This won't change the content
    fm.create_file("data/foo/bar/sample.txt", "Should not overwrite", exist_behavior="skip") 
    print(fm.read_file("data/foo/bar/sample.txt"))
    print(fm.list_files("data"))
    #fm.delete_file("data/foo/bar/sample.txt")
