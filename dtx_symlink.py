from pathlib import Path
import os
import logging
import logging.config
from typing import Iterator, Tuple, Optional
import pickle
import logging_hack

def setup_logging():
    import sys

    log_config = {
        'version': 1,
        'disable_existing_loggers': False,
        "formatters": {
            "simple": {
                "format": u'[{asctime}] [{levelname:<8}] {name}: {message}',
                'datefmt': '%Y-%m-%dT%H:%M:%S%z',
                'style': '{',
            }
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'stream': sys.stdout,
                'formatter': 'simple',
            },
            'file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': 'log.txt',
                'formatter': 'simple',
            },
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['console', 'file'],
        },
    }
    logging.config.dictConfig(log_config)


try:
    from japanese import convert_to_kana, is_japanese, kana_group
    JAPANESE_SUPPORTED = True
except ImportError:
    JAPANESE_SUPPORTED = False

    def is_japanese(text: str) -> bool:
        return False

from DTXFile import DTXFile

def group_by_difficulty(dtx: DTXFile) -> Tuple[str, Optional[str]]:
    """Compute difficulty sorting group. Returns tuple of (difficulty sorting group, difficulty)"""
    def group_name(level: int):
        # levels can be either "90" -> 9.0, or "975" -> 9.75
        # so divide until the level is less than 100
        while level > 100:
            level = level/10
        
        if level < 0 or level > 100:
            logging_hack.warning(f"Illegal difficulty found - {level}")
            return "Error", None
        
        # group into intervals of 0.5
        # the intervals follow [0.0, 0.5), [0.5, 1), ... except the last group, which is [9.5, 10]
        if level >= 95:
            group_start = 95
            group_end = 100
        else:
            group_start = int(level/5) * 5
            group_end = group_start + 5
        return f"{group_start/10:.2f}-{group_end/10:.2f}", f"{level/10:.2f}"
    return group_name(dtx.level)

def group_alpha(title: str) -> str:
    """Compute alphabetical sorting group"""
    first_letter = title.strip()[0]
    if first_letter.isdigit():
        return '0-9'
    elif first_letter.isascii() and first_letter.isalpha():
        first_letter = first_letter.upper()
        if first_letter < 'A' or first_letter > 'Z':
            logging_hack.warning(f"Alphabetical character falls outside of [A,Z]?? {title} -> {first_letter}")
            return "Error"

        # choose the letter group it falls into
        groups = 'EIMOTW'
        for i,group_letter in enumerate(groups):
            if first_letter < group_letter:
                break
        else:
            i = len(groups)
        group = i

        first = groups[group-1] if group-1 >= 0 else "A"
        last = chr(ord(groups[group])-1) if group < len(groups) else "Z"
        return f'{first}-{last}'
    elif is_japanese(first_letter):
        kana = convert_to_kana(title)
        try:
            return kana_group(kana[0])
        except:
            logging_hack.warning(f"Unknown kana found: {kana}, {kana[0]}")
            return 'Error'
    else:
        return 'Other'
    
def group_alpha_using_folder_name(path: Path) -> str:
    """Group alphabetically using the folder name of the dtx file"""
    assert path.is_dir()
    return group_alpha(path.name)
    
def group_alpha_using_title(dtx: DTXFile) -> str:
    """Group alphabetically using the song title"""
    return group_alpha(dtx.title)

def symlink(src: Path, link_path: Path):
    link_path.parent.mkdir(exist_ok=True, parents=True)
    if link_path.exists():
        assert link_path.is_symlink()
        return
    os.symlink(src, link_path)


def iter_dtx_files(path: Path):
    yield from path.rglob("**/*.dtx")

class DTXDatabase:
    def __init__(self, song_folder):
        self.song_folder = song_folder
        self.dtx_files = {}
    
    def key_and_folder(self, path: Path):
        if path.is_absolute():
            key = path.relative_to(self.song_folder)
        else:
            key = path
        
        folder = key.parent
        return key,folder

    def path_folder(self, path: Path):
        return self.key_and_folder(path)[1]

    def set(self, dtx_path: Path, dtx_file: DTXFile):
        key, folder = self.key_and_folder(dtx_path)
        self.dtx_files[key] = dtx_file
    
    @classmethod
    def load(cls, path):
        with open(path, 'rb') as fp:
            obj = pickle.load(fp)
        return obj
    
    def save(self, path):
        with open(path, 'wb') as fp:
            pickle.dump(self, fp)


def load_dtx_files(input_path, from_db, cache_to_db, db_path) -> Iterator[Tuple[Path, DTXFile]]:
    """Iterate over every dtx file found in a folder. Searches recursively through subdirectories."""
    if from_db:
        db = DTXDatabase.load(db_path)
        for relative_path, dtx in db.dtx_files.items():
            yield (db.song_folder / relative_path, dtx)
    else:
        db = DTXDatabase(input_path)
        try:
            for dtx_path in iter_dtx_files(input_path):
                dtx = DTXFile.load(dtx_path)
                yield (dtx_path, dtx)
                if cache_to_db:
                    db.set(dtx_path, dtx)
        finally:
            if cache_to_db:
                db.save(db_path)

def delete_folder_contents(folder: Path):
    assert folder.exists() and folder.is_dir()
    for item in folder.iterdir():
        if item.is_symlink():
            # If it's a symlink, remove the symlink
            item.unlink()
        elif item.is_dir():
            delete_folder_contents(item)
            item.rmdir()  # Remove the empty subdirectory
        else:
            # Delete individual files
            item.unlink()

def confirm(prompt, choices):
    while True:
        answer = input(prompt)
        answer = answer.lower().strip()
        if answer in choices:
            return choices[answer]

class AlphaGroupingMethods:
    """Possible algorithms to use for alphabetical sorting"""
    SONG = 's'
    FOLDER = 'f'

class ProgressBar:
    def __init__(self):
        self.prev_line_length = 0
    
    def print(self, message):
        # when printing a longer message then a shorter message, 
        # the difference needs to be filled with spaces
        # to clear out the characters from the longer message
        print(f'\r{message:<{self.prev_line_length}}', end='\r')
        self.prev_line_length = len(message)

if __name__ == "__main__":
    import argparse
    import inspect

    setup_logging()
    if not JAPANESE_SUPPORTED:
        print("NOTE: Sorting by japanese is not installed, please see readme if you need this.")

    parser = argparse.ArgumentParser(
        prog='drummania-sorter',
        description=inspect.cleandoc(
        '''
            Create copies of a DTXMania song folder sorted in different ways. Supports alphabetically and by difficulty.
        '''
        ),
    )

    parser.add_argument('input_path', help="Input folder containing drummania files to sort")
    parser.add_argument('output_path', help="Output folder where all sorted file structures will be written")
    parser.add_argument('--alpha-method', choices=[AlphaGroupingMethods.SONG, AlphaGroupingMethods.FOLDER], help="Alphabetical sort method to use. 's' to sort by song title, 'f' to sort by folder name. (see readme)")

    args = parser.parse_args()
    INPUT_PATH = Path(args.input_path)
    OUTPUT_PATH = Path(args.output_path)
    assert INPUT_PATH.is_dir()
    assert not OUTPUT_PATH.exists() or OUTPUT_PATH.is_dir()

    # this database functionality is just for my own testing
    DB_PATH = OUTPUT_PATH / '..' / "gitadora.pkl"
    FROM_DB = False
    CACHE_TO_DB = False
    # result = confirm(f"Cache contents to a database at {DB_PATH}?")

    alpha_method = args.alpha_method
    if alpha_method is None:
        alpha_method = confirm(f"Use song titles ('s') or folder names ('f') for alphabetical sort: ", {'s': AlphaGroupingMethods.SONG, 'f': AlphaGroupingMethods.FOLDER})
        print(f"You can specify this from command line later by using `--alpha-method {alpha_method}`.")

    SORT_DIFF_FOLDER = OUTPUT_PATH / "DTXFiles.Difficulty"
    SORT_ALPHA_FOLDER = OUTPUT_PATH / "DTXFiles.Alphabetical"

    if OUTPUT_PATH.exists():
        delete_folder_contents(OUTPUT_PATH)

    visited_folders = set()

    # Manually looping over the iterator because
    # for i in iterator:
    #   ...
    # doesn't catch any errors thrown in the iterator, so I want to include it this time (so I can print when it failed)
    iterator = load_dtx_files(INPUT_PATH, FROM_DB, CACHE_TO_DB, DB_PATH)
    i = 1
    pbar = ProgressBar()
    while True:
        try:
            dtx_path,dtx = next(iterator)
            dtx_folder = dtx_path.parent
            pbar.print(f'{i} | {dtx_path.relative_to(INPUT_PATH)}')
            i += 1

            logging_hack.set_song(dtx_path.relative_to(INPUT_PATH))

            # sort by difficulty
            # first sort into difficulty groups (0.00-0.50, 0.50-1.00, ...)
            # then order within each difficulty group, by putting files into subfolders
            group, diff = group_by_difficulty(dtx)
            save_folder = SORT_DIFF_FOLDER / f"DTXFiles.{group}"
            if diff is not None:
                save_folder = save_folder / diff
            symlink(dtx_folder, save_folder / dtx_folder.name)
            
            # sort alphabetically
            if not dtx_folder in visited_folders:
                if alpha_method == AlphaGroupingMethods.SONG:
                    name_group = group_alpha_using_title(dtx)
                else:
                    name_group = group_alpha_using_folder_name(dtx_folder)
                symlink(dtx_folder, SORT_ALPHA_FOLDER / f"DTXFiles.{name_group}" / dtx_folder.name)
                visited_folders.add(dtx_folder)
            
        except StopIteration:
            break
        except:
            print("Error parsing", dtx_path)
            raise
