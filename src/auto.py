from db_processor import DatabaseProcessor
from data_processor import DataProcessor

class Autoupdate(object):
    """
        [params]
         - base_path: base file path
         - driver_path: chrome driver path
         
        [program process]
        
        if opt == "new_init":
            # data_processor: open webdriver and login(launch_driver)
            # data_processor: scroll all lectures(scroll_leclist)
            # data_processor: get lecture list data(get_lecinfo)
            # data_processor: get all datas(get_lecdata)
            # db_processor: create & save to database
        elif opt == "update_dayenroll":
            # db_processor: load & find last updated date from database
            # data_processor: get datas to update (data_columns): 
            # db_processor: last date - udate, new dates - insert
        elif opt == "update_user":
            # db_processor: load all lecture list from database
            # data_processor: get datas to update (only "daynum", "daylast")
            # db_processor: update datas
    """
    def __init__(self, base_path, driver_path):
        
        # init processor
        info_columns = ("id", "page", "name", "date", "prof", "partner", "imglink", "access")
        data_columns = ("id", "lec_id", "person", "daynum", "daylast", "dayenroll")
        update_person_columns = ("id", "daynum", "daylast")
        
        self.data_processor = DataProcessor(driver_path=driver_path,
                                            info_columns=info_columns, 
                                            data_columns=data_columns,
                                            update_person_columns=update_person_columns)
        self.db_processor = DatabaseProcessor(base_path=base_path, 
                                              info_columns=info_columns, 
                                              data_columns=data_columns,
                                              update_person_columns=update_person_columns)
    
    def init_program(self, **kwargs):
        """
        first install: 
        [params]
         - login
         - max_show
         - save
        """
        if kwargs["load"]:
            from pathlib import Path
            import pickle
            with (Path(kwargs["load_path"]) / 'lecinfo.pickle').open(mode='rb') as handle:
                    lecinfo = pickle.load(handle)
            with (Path(kwargs["load_path"]) / 'lecdata.pickle').open(mode='rb') as handle:
                lecdata = pickle.load(handle)
            self.db_processor.process_values(opt="new_init", 
                lecinfo=kawrgs["lecinfo"], 
                lecdata=kwargs["lecdata"])
        else:
            driver, lecinfo, lecdata = self.data_processor.main(
                opt="new_init", 
                login_info=kwargs["login"], 
                max_show=kwargs["max_show"], 
                save=kwargs["save"])
            driver.quit()
            self.db_processor.delete_table()
            self.db_processor.create_table()

            self.db_processor.process_values(opt="new_init", lecinfo=lecinfo, lecdata=lecdata)
            print("All DB install is Done!")
    
    def update(self, **kwargs):
        """
        update values: 
        [params]
         - login
         - opt: 'update_dayenroll' or 'update_user'
         - max_show
         - lec_ids: 'all'(string) or list of lecture number
        
        """
        conn = self.db_processor.create_connection()
        with conn:
            update_src = self.db_processor.get_update_src(
                opt=kwargs["opt"], 
                conn=conn, 
                lec_ids=kwargs["lec_ids"])
            driver, update_dict = self.data_processor.main(
                opt=kwargs["opt"], 
                login_info=kwargs["login"], 
                max_show=kwargs["max_show"], 
                update_src=update_src)
            driver.quit()
            self.db_processor.process_values(
                opt=kwargs["opt"], 
                insert=update_dict["insert"], 
                update=update_dict["update"])
            
    def show_lec_available(self):
        """
        show access available lectures
        lec_id, name, last updated
        """
        conn = self.db_processor.create_connection()
        query = """
            SELECT DISTINCT data.lec_id AS lec_id, 
                            info.name AS name, 
                            MAX(data.dayenroll) AS last
            FROM lecdata AS data 
            INNER JOIN (
                SELECT id, name, access
                FROM lecinfo
                WHERE access=1
            ) AS info ON data.lec_id=info.id 
            GROUP BY data.lec_id
            ORDER BY data.lec_id"""
        with conn:
            c = conn.cursor()
            res = c.execute(query).fetchall()
            return res
                
    def __version__(self):
        print("0.1")