"""Module for the Images class."""
import os
import glob
import hashlib
import datetime as dt
import shutil
import pandas as pd
import datetime
from datetime import timedelta
from database import Database
import threading


class Loader:
    _index = 0
    _images = pd.DataFrame()

    def __init__(self, config):

        # Set up config and database
        self._config = config
        db_path = config.get("database/path", "image_tags.db")
        self._db = Database(db_path)
        self._initialize_database()
        self.current_data = None
        self.current_index = -1
        self.max_index = self.get_max_index()
        self.id_list = []
        return

    def get_max_index(self):
        max_index = self._db.query(" SELECT * FROM tags ORDER BY id DESC LIMIT 1 ")
        return dict(max_index.iloc[0])['id']

    def get_shown_images(self):
        datas = self._db.query("""
                    SELECT * FROM tags where SHOWN = 1
                    ;
                    """)
        return datas

    def get_remaining_and_count(self):
        count = len(self._db.query(" SELECT * FROM tags where tag = 'Prostate' "))
        remaining = len(self._db.query(" SELECT * FROM tags where tag = '0'"))
        return remaining, count

    def next_data(self):
        lock = threading.Lock()
        data = None
        lock.acquire()
        current_time = datetime.datetime.now()
        final_time = current_time - timedelta(minutes=1)
        if self.current_index < 0 or self.current_index >= self.max_index:
            result = self._db.query(" SELECT * FROM tags " +
                                    "where ( SHOWN = 0 or last_time < '" + str(final_time) + "' ) " +
                                    "and tag != 'Prostate' and tag != 'Not Prostate' LIMIT 1;"
                                    )
            if not result.empty:
                data = dict(result.iloc[0])
        else:
            result = self._db.query(" SELECT * FROM tags " +
                                    "where ( SHOWN = 0 or last_time < '" + str(final_time) + "' )" +
                                    " and tag != 'Prostate' " +
                                    "and tag != 'Not Prostate' and id > " + str(self.current_index) +
                                    " LIMIT 1 ;")
            if not result.empty:
                data = dict(result.iloc[0])
        if data is not None:
            data['SHOWN'] = 1
            self._db.query(
                "UPDATE tags " +
                "set SHOWN = 1 " +
                "where id = '" + str(data['id']) + "' ;"
            )
            self.current_data = data
            self.current_index = data['id']
            self.id_list.append(data)
            self.id_list = self.id_list[:100]
        lock.release()
        return data

    def get_by_id(self, id):
        data = self._db.query(
            "SELECT * FROM tags WHERE " + "id = '" + id + "' LIMIT 1"
        )
        return dict(data.iloc[0])

    def store(self, data):
        if data['tag'] is None:
            data['tag'] = '0'
        tag = data['tag']
        id = data['id']
        old_data = self.get_by_id(id)
        new_path = old_data['path']
        if tag == 'Not Prostate':
            file_name = old_data['path'].split("/")[2]
            shutil.move(old_data['path'], "not_prostate/")
            print("file moved!")
            new_path = "./not_prostate/" + file_name
        if tag == 'Prostate':
            file_name = old_data['path'].split("/")[2]
            shutil.move(old_data['path'], "prostate/")
            print("file moved!")
            new_path = "./prostate/" + file_name
        data['path'] = new_path
        data['hash'] = old_data['hash']
        data['id'] = id
        self._write_database(data)

    def _write_database(self, data):
        """
        Writes image tag data to the database.

        Parameters
        ----------
        data : dict
            Tagging data, should contain keys 'id', 'path', 'tags',
            'remark', 'updated'. All values should be provided as
            string values.
        """

        required = "path", "tag", "SHOWN", "hash"
        missing = set(required) - set(data)
        if missing:
            raise KeyError(
                "Missing the following keys from tag data: " + ", ".join(missing)
            )
        current_time = datetime.datetime.now()
        data['last_time'] = current_time
        if 'id' in data.keys():
            self._db.query(
                """
                INSERT INTO tags (id , hash, last_time, path , SHOWN , tag)
                    VALUES(:id, :hash , :last_time , :path, :SHOWN , :tag)
                ON CONFLICT (id) DO UPDATE SET
                    tag=excluded.tag , 
                    SHOWN=excluded.SHOWN , 
                    path=excluded.path , 
                    last_time=excluded.last_time
                ;
                """,
                data,
            )
        else:
            self._db.query(
                """
                INSERT INTO tags (hash, last_time , path , SHOWN , tag)
                    VALUES(:hash, :last_time , :path, :SHOWN , :tag)
                """,
                data,
            )

    def _initialize_database(self):
        """Creates the tag table if it does not exists."""
        self._db.query(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                hash TEXT ,
                last_time TIMESTAMP ,
                path TEXT NOT NULL,
                SHOWN INT ,
                tag TEXT 
            );
        """
        )
        current_files = os.listdir('./zip_files/')
        for file in current_files:
            data = dict()
            file_path = './zip_files/' + file
            hash = self._hash(file_path)
            result = self._db.query("SELECT * FROM tags  where hash = '" + hash + "'")
            if len(result) == 0:  # not added
                data['hash'] = hash
                data['path'] = file_path
                data['SHOWN'] = "0"
                data['tag'] = "0"
                self._write_database(data)
        return

    @staticmethod
    def _hash(filepath):
        """
        Creates an MD5 hash for a file path.
        Parameters
        ----------
        filepath : str
            File path as a string.
        Returns
        -------
        str
            MD5 hash as a string value.
        """

        m = hashlib.md5(filepath.encode("utf-8"))
        return m.hexdigest()
