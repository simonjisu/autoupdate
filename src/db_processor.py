from collections import defaultdict
from tqdm import tqdm
import sys
import sqlite3
from pathlib import Path

class DatabaseProcessor(object):
    def __init__(self, base_path, **kwargs):
        """
        params
         - base_path
         - info_columns
         - data_columns
        """
        self.info_columns = kwargs["info_columns"]
        self.data_columns = kwargs["data_columns"]
        self.update_person_columns = kwargs["update_person_columns"]
        db_path = Path(base_path) / "database"
        if not db_path.exists():
            db_path.mkdir()
        self.lec_db_path = db_path / "lecture.db"
        self.check_is_table = lambda d: len(set(list(map(lambda x: len(x), d.values())))) <= 1
        self.update_src_dict_cols = ('lasttable_id', 'lec_ids', 'pages', 'lastupdate', 'ids')
        
    def create_connection(self):
        try:
            conn = sqlite3.connect(str(self.lec_db_path))
            return conn
        except:
            print("Unexpected error:", sys.exc_info()[0])
            raise
    
    def create_table(self):
        """
        table columns:
         - lecinfo: ('id', 'page', 'name', 'date', 'prof', 'partner', 'imglink', 'access')
         - lecdata: ('id', 'lec_id', 'person', 'daynum', 'daylast', 'dayenroll')
        """
        lec_table = """CREATE TABLE lecinfo (
            {} integer PRIMARY KEY,
            {} text,
            {} text,
            {} text,
            {} text,
            {} text,
            {} text,
            {} integer
            ); """.format(*self.info_columns)

        data_table = """CREATE TABLE lecdata (
            {} integer PRIMARY KEY,
            {} integer,
            {} text,
            {} integer,
            {} text,
            {} text,
            FOREIGN KEY(lec_id) REFERENCES lecinfo(id)
            ); """.format(*self.data_columns)
        conn = self.create_connection()
        with conn:
            self._ct(conn, lec_table)
            self._ct(conn, data_table)
        print("created tables")
    
    def delete_table(self):
        conn = self.create_connection()
        with conn:
            self._dt(conn)
        print("deleted tables")
    
    def check_table_info(self, table_name):
        conn = self.create_connection()
        with conn:
            c = conn.cursor()
            res = c.execute(f"PRAGMA table_info({table_name});")
            desc = list(zip(*res.description))[0]
            print("\t".join(desc))
            for r in res.fetchall():
                print("\t".join(list(map(lambda x: str(x), r))))
    
    def get_update_src(self, opt, conn, lec_ids):
        """
        lec_ids: "all" or list of numbers
        
        update_src: 
         - lasttable_id
         - lec_ids
         - pages
         - lastupdate
         - ids
        """
        if lec_ids[0] == "all":
            lec_ids = lec_ids[0]
        elif lec_ids != []:
            lec_ids = list(map(lambda x: int(x), lec_ids))
        else:
            assert False, "must be a list that contain 'all' or lecture numbers" 
            
        with conn:
            c = conn.cursor()
            
            update_src = defaultdict()
            query = """SELECT MAX(id) FROM lecdata"""
            update_src["lasttable_id"] = c.execute(query).fetchone()[0]
            # process: lec_ids, pages, lastupdate
            select_lec = "" if lec_ids == "all" else "WHERE data.lec_id IN ("+",".join(["?"]*(len(lec_ids)))+")"
            query = """
                SELECT DISTINCT data.lec_id AS lec_id, info.page, MAX(data.dayenroll) AS last
                FROM lecdata AS data 
                INNER JOIN (
                    SELECT id, page, access
                    FROM lecinfo
                    WHERE access=1
                ) AS info ON data.lec_id=info.id 
                {}
                GROUP BY data.lec_id
                ORDER BY data.lec_id
                ;""".format(select_lec)
            res = c.execute(query).fetchall() if lec_ids == "all" else c.execute(query, lec_ids).fetchall()
            for x, col in zip(zip(*res), self.update_src_dict_cols[1:4]):
                update_src[col] = x
            
            # process: ids  
            select_tar = "=" if opt == "update_dayenroll" else "<="  # update_user select all datas
            select_lec = "" if lec_ids == "all" else "AND (d.lec_id IN ("+",".join(["?"]*(len(lec_ids)))+"))"
            
            query = """
                SELECT d.lec_id, d.id, d.person
                FROM lecdata AS d
                INNER JOIN (
                    SELECT DISTINCT data.lec_id AS lec_id, MAX(data.dayenroll) AS last
                    FROM lecdata AS data
                    INNER JOIN (
                        SELECT id, page, access
                        FROM lecinfo
                        WHERE access=1
                    ) AS info ON data.lec_id=info.id 
                    GROUP BY data.lec_id
                ) AS lu
                ON d.lec_id=lu.lec_id
                WHERE (d.dayenroll{}lu.last) {}
                ORDER BY d.lec_id
            """.format(select_tar,select_lec)

            res = c.execute(query).fetchall() if lec_ids == "all" else c.execute(query, lec_ids).fetchall()
            update_src["ids"] = []
            for lec_id in update_src["lec_ids"]:
                update_src["ids"].append([r[1:] for r in res if r[0] == lec_id])
        
        return update_src
    
        
    def process_values(self, opt, **kwargs):
        conn = self.create_connection()
        with conn:
            if opt == "new_init":
                self._insrt(conn, opt, data_dict=kwargs["lecinfo"], table_name="lecinfo")
                self._insrt(conn, opt, data_dict=kwargs["lecdata"], table_name="lecdata")
                
            elif opt == "update_dayenroll":
                self._insrt(conn, opt, data_dict=kwargs["insert"], table_name="lecdata", update=False)
                self._insrt(conn, opt, data_dict=kwargs["update"], table_name="lecdata", update=True)
                
            elif opt == "update_user":
                self._insrt(conn, opt, data_dict=kwargs["update"], table_name="lecdata", update=True)
                
    def _ct(self, conn, create_table_query):
        try:
            c = conn.cursor()
            c.execute(create_table_query)
        except:
            print("Unexpected error:", sys.exc_info()[0])
            raise
    
    def _dt(self, conn):
        c = conn.cursor()
        droptable = "DROP TABLE IF EXISTS lecinfo"
        c.execute(droptable)
        droptable = "DROP TABLE IF EXISTS lecdata"
        c.execute(droptable)
    
    def _insrt(self, conn, opt, data_dict, table_name, update=False):
        c = conn.cursor()
        if opt == "new_init":
            assert self.check_is_table(data_dict), f"{data_dict}: columns dosen't have same lengths"
            columns = ",".join(self.info_columns if table_name == "lecinfo" else self.data_columns)
            values = ",".join(["?"]*len(self.info_columns) if table_name == "lecinfo" else ["?"]*len(self.data_columns))
            query = """INSERT INTO {}({}) VALUES ({}); """.format(table_name, columns, values)
            for data in tqdm(self._row_iter(data_dict), 
                             desc=f"[process] table {table_name} inserting", 
                             total=len(data_dict["id"])):
                c.execute(query, data)
        else: 
            assert self.check_is_table(data_dict), f"{data_dict}: columns dosen't have same lengths"
            if opt == "update_dayenroll":
                columns = ",".join(self.data_columns[1:] if update else self.data_columns) 
                values = ",".join(["?"]*len(self.data_columns[1:] if update else self.data_columns))
                query = """UPDATE {} SET ({})=({}) WHERE id=?;""" if update else """INSERT INTO {}({}) VALUES ({});"""
                query = query.format(table_name, columns, values)
            elif opt == "update_user":
                columns = ",".join(self.update_person_columns[1:]) 
                values = ",".join(["?"]*len(self.update_person_columns[1:]))
                query = """UPDATE {} SET ({})=({}) WHERE id=?;"""
                query = query.format(table_name, columns, values)
            else:
                assert False, "insert opt"
            for data in tqdm(self._row_iter(data_dict),
                             desc=f"[process] table {table_name} {'update' if update else 'insert'}ing", 
                             total=len(data_dict["id"])):
                data = tuple(data[1:] + (data[0],)) if update else data
                c.execute(query, data)
            
    def _row_iter(self, x):    
        for values in zip(*list(x.values())):
            yield values
