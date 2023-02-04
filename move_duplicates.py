#! python3

# python move_duplicates.py --album X:\\Nino\\Pictures --target-folder X:\\Nino\\Duplicates -f

import os
import sqlite3
import argparse
from pathlib import Path
import logging
import shutil
import datetime

# TODO: Make log file a command line option.
# logging.basicConfig(format="%(message)s", filename='duplicates.log')
logging.basicConfig(format="%(message)s")
logger = logging.getLogger(__name__)

DUPLICATE_HASHES = """
WITH hashes as (SELECT uniqueHash, COUNT(*) as count FROM Images WHERE Images.album NOT NULL GROUP BY 1)
SELECT uniqueHash, count FROM hashes WHERE count > 1 ORDER BY 2 DESC
"""

# SELECT id, relativePath || '/' || name FROM
IMAGES_BY_HASH = """
SELECT images.id, albums.relativePath, images.name, images.album
FROM images JOIN albums ON images.album=albums.id
WHERE uniqueHash='{hash}'
ORDER BY LENGTH(name) ASC, NAME ASC
"""

DELETE_BY_ID = """
DELETE FROM images WHERE id = ?
"""

class DuplicateRemover:

    def __init__(self):
        self.moved_file_ids = []

    def move_file(self, id:int, src:Path, dst:Path):
        if self.dry_run:
            logger.info(f"Would move {src} to {dst}")
            self.moved_file_ids.append(str(id))
        elif self.force:
            try:
                logger.info(f"Moving {src} to {dst}")
                dst.parent.absolute().mkdir(0o777, True, True)
                src.rename(dst)
                self.moved_file_ids.append(str(id))
            except Exception:
                logger.warning(f"Could not move {src} to {dst}.")
                
    def remove_moved_files_from_db(self):
        if self.dry_run:
            logger.info(f"Would remove from images table: {self.moved_file_ids}")
        elif self.force:
            logger.info(f"Removing ids from images table: {self.moved_file_ids}")
            cursor = self.connection.cursor()
            cursor.executemany(DELETE_BY_ID, zip(self.moved_file_ids))
        self.moved_file_ids.clear()

    def remove_duplicates(self):
        db_path = Path(self.album, "digikam4.db")
        logger.info("Opening database file {}".format(str(db_path)))
        with sqlite3.connect(str(db_path)) as self.connection:
            cursor = self.connection.cursor()
            result = cursor.execute(DUPLICATE_HASHES)
            duplicate_hashes = result.fetchall()
            for duplicate_hash in duplicate_hashes:
                logger.info("Found {count} images with hash {hash}".format(hash=duplicate_hash[0], count=duplicate_hash[1]))
                result = cursor.execute(IMAGES_BY_HASH.format(hash=duplicate_hash[0]))
                images = result.fetchall()
                for img in images:
                    id = img[0]
                    album_rel_path = img[1]
                    album_path = str(self.album) + album_rel_path
                    target_path = str(self.target_folder)  + album_rel_path
                    name = img[2]
                    album_id = img[3]
                    src_path = Path(album_path, name)
                    dst_path = Path(target_path, name)
                    if img == images[0]:
                        logger.info(f"Keeping {src_path}")
                    else:
                        self.move_file(id, src_path, dst_path)
                        if len(self.moved_file_ids) > 100:
                            self.remove_moved_files_from_db()
            self.remove_moved_files_from_db()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Duplicate image remover')
    parser.add_argument('-n', '--dry-run', action='store_true', default=False, help='neither move files nor delete database entries')
    parser.add_argument('-f', '--force', action='store_true', default=False, help='actually apply the changes')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='be chatty')
    parser.add_argument('-a', '--album', default=Path(Path.home(), Path('Pictures')), help='path of the album')
    parser.add_argument('-t', '--target-folder', default=Path(Path.home(), Path('Duplicates')), help='folder where duplicate files will be moved to')

    duplicate_remover = DuplicateRemover()
    parser.parse_args(namespace=duplicate_remover)
    if not duplicate_remover.dry_run and not duplicate_remover.force:
        logger.error('Either --dry-run or --force have to be specified.')
        parser.print_help()
        exit(-1)
    if duplicate_remover.dry_run and duplicate_remover.force:
        logger.error('--dry-run and --force cannot be enabled at the same time.')
        parser.print_help()
        exit(-1)
    

    if duplicate_remover.verbose:
        logger.setLevel('DEBUG')
    else:
        logger.setLevel('INFO')

    duplicate_remover.remove_duplicates()