from pathlib import Path
import hashlib
import sqlite3
import logging
import os

logging.basicConfig(format="%(message)s", level='DEBUG')
logger = logging.getLogger(__name__)

IMAGES_BY_HASH = """
SELECT images.id, albums.relativePath, images.name, images.album
FROM images JOIN albums ON images.album=albums.id
WHERE uniqueHash='{hash}'
ORDER BY LENGTH(name) ASC, NAME ASC
"""

def digikam_unique_hash_v2(path:Path):
    """
    Replicate Digikams DImgLoader::uniqueHashV2
    https://github.com/KDE/digikam/blob/master/core/libs/dimg/loaders/dimgloader.cpp#L333
    """
    md5 = hashlib.md5()
    with open(str(path),'rb') as file:
        spec_size = 100 * 1024
        file_size = os.fstat(file.fileno()).st_size
        size = min(spec_size, file_size)
        chunk = file.read(size)
        if len(chunk) > 0:
            md5.update(chunk)
        file.seek(file_size - size)
        chunk = file.read(size)
        if len(chunk) > 0:
            md5.update(chunk)
    return md5.hexdigest()

def md5_hash(path:Path):
    md5 = hashlib.md5()
    with open(str(path),'rb') as file:
        while chunk := file.read(8192):
            md5.update(chunk)
    return md5.hexdigest()

def iterate_files_in_directory(dir:Path, album_path:Path, cursor:sqlite3.Cursor):
    pathlist = dir.glob('**/*.*')
    for path in pathlist:
        if path.is_dir():
            continue

        unique_hash = digikam_unique_hash_v2(path)
        result = cursor.execute(IMAGES_BY_HASH.format(hash=unique_hash))
        images = result.fetchall()
        if len(images) == 0:
            logger.error(f'{str(path)} not found in Digikam database.')            
        elif len(images) > 1:
            logger.warn(f'{str(path)} found {len(images)} times Digikam database. Consider running move_duplicates first.')
        else:
            img = images[0]
            album_rel_path = '.' + img[1]
            name = img[2]
            db_file_path = Path(album_path, album_rel_path, name)
            db_file_md5 = md5_hash(db_file_path)
            duplicate_md5 = md5_hash(path)
            if db_file_md5 != duplicate_md5:
                logger.error(f'MD5 sums of {str(path)} and {str(db_file_path)} do not match. possible file corruption.')
            else:
                logger.info(f'{str(path)} found in Digikam DB as {str(db_file_path)} file MD5 sum matches. Deleting ...')
                # TODO: Protect behind dry-run/force flag
                #path.unlink()

if __name__ == '__main__':
    #TODO: Proper CLI
    duplicates_path = Path('X:\\Nino\\Duplicates')
    album_path = Path('X:\\Nino\\Pictures\\')
    db_path = Path(album_path, "digikam4.db")
    logger.info("Opening database file {}".format(str(db_path)))
    with sqlite3.connect(str(db_path)) as connection:
        iterate_files_in_directory(duplicates_path, album_path, connection.cursor())
