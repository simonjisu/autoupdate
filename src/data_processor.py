
import re
import time
import pickle
import hashlib

from datetime import datetime as dt, timedelta
from selenium import webdriver

from bs4 import BeautifulSoup
from collections import defaultdict
from tqdm import tqdm
from pathlib import Path

class DataProcessor(object):
    def __init__(self, **kwargs):
        self.edwith_site = "https://www.edwith.org"
        self.driver_path = kwargs["driver_path"]
        self.info_columns = kwargs["info_columns"]
        self.data_columns = kwargs["data_columns"]
        self.update_person_columns = kwargs["update_person_columns"]
                
    def main(self, opt, **kwargs):
        """
        params needed
             > login_info: login module(contains, email & password)
            
        params needed by opt:
         - opt: new_init
             > max_show: crawling page max show number, defualt 1000
             > save: boolean for save data into .pickle file
         - opt: update_dayenroll
             > update_src: pages to update
             > max_show: crawling page max show number, defualt 500
         - opt: update_user:
             > update_src: pages to update
             > max_show: crawling page max show number, defualt 500
        """
        if opt is not None:
            driver = self.launch_driver(kwargs["login_info"])
        else:
            assert False, "Insert 'opt': (new_init, update_dayenroll, update_user)"
            
        if opt == "new_init":
            self.scroll_leclist(driver)
            lecinfo = self.get_lecinfo(driver, type_="info")
            lecdata = self.get_lecdata(driver, lecinfo, type_="data", max_show=kwargs["max_show"])
            if kwargs["save"]:
                with open('lecinfo.pickle', 'wb') as handle:
                    pickle.dump(lecinfo, handle, protocol=pickle.HIGHEST_PROTOCOL)
                with open('lecdata.pickle', 'wb') as handle:
                    pickle.dump(lecdata, handle, protocol=pickle.HIGHEST_PROTOCOL)
            
            return driver, lecinfo, lecdata        
        elif (opt == "update_dayenroll") or (opt == "update_user"):
            update_dict = self.get_update_lecdata(opt, driver, kwargs["update_src"], type_="data", max_show=kwargs["max_show"])
            driver.quit()
            return driver, update_dict

    def launch_driver(self, login_info):
        
        driver = webdriver.Chrome(str(Path(self.driver_path)/"chromedriver.exe"), port=4444)
        driver.implicitly_wait(3)
        driver.get(self.edwith_site + "/neoid/emailLogin")
        driver.find_element_by_name('email').send_keys(login_info.email)
        driver.find_element_by_name('password').send_keys(login_info.password)
        driver.find_element_by_xpath('//*[@id="submit"]').click()
        driver.implicitly_wait(5)
        if driver.current_url == (self.edwith_site + "/neoid/emailLogin"):
            assert False, "Error in when launching driver"
        return driver
    
    def scroll_leclist(self, driver):
        """강좌 url 모두 따오기"""
        find_progress_text = lambda x: re.sub("[\(\)]", "", re.findall(r"\(.*\)", x)[0])
        url = self.edwith_site + "/search/index"
        soup = self.driver_process(driver, url)
        progress_text = find_progress_text(soup.select("#_more_area > button")[0].text)
        now, total_lec = map(lambda x: int(x), progress_text.split("/"))
        start_scroll=True
        while start_scroll:
            driver.find_element_by_xpath('//*[@id="_more_area"]/button').click()
            driver.implicitly_wait(3)
            time.sleep(1.5)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            progress_text = find_progress_text(soup.select("#_more_area > button")[0].text)
            now, total_lec = map(lambda x: int(x), progress_text.split("/"))
            print(f"{now/total_lec*100:.2f}% scrolling", flush=True)
            if driver.find_element_by_xpath('//*[@id="_more_area"]').get_attribute("style") != "":
                driver.implicitly_wait(3)
                time.sleep(1.5)
                start_scroll=False
        print(f"{100}% scrolled")
    
    def get_lecinfo(self, driver, type_="info"):
        lecinfo = defaultdict(list)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        all_lectures =  soup.select_one("#course").find_all("li")

        for i, x in tqdm(enumerate(all_lectures, 1), desc="[process] lecture list", total=len(all_lectures)):
            data = self.find_data(x, i, type_)
            self.add_data(lecinfo, data, self.info_columns)

        # check urls can access manage page
        for i, page in tqdm(enumerate(lecinfo['page']), desc="[process] lecture accessable", total=len(all_lectures)):
            try:
                driver.get(self.edwith_site + page)
                driver.implicitly_wait(3)
                time.sleep(0.5)
                if driver.find_element_by_id("__USER_ROLE").get_property("value") == "ROLE_PROFESSOR":
                    lecinfo['access'][i] = 1
            except:
                continue

        return lecinfo
    
    def get_lecdata(self, driver, lecinfo, type_="data", max_show=1000):
        lecdata = defaultdict(list)
        available_urls = []
        available_ids = []
        for acc, page, lec_id in zip(lecinfo["access"], lecinfo["page"], lecinfo["id"]):
            if acc == 1:
                available_urls.append(self.edwith_site + page + "/manage/studentManage/list")
                available_ids.append(lec_id)
        i = 1  # table idx
        for url, lec_id in tqdm(zip(available_urls, available_ids), desc="[process] lecture data", total=len(available_urls)):
            soup = self.driver_process(driver, url)
            css_select = "#content > section > div.group_lr.mab10 > div.group_r > p > em"
            total_student = int(soup.select_one(css_select).text.replace(",", ""))
            total_pages = total_student // max_show + 1

            for k in range(total_pages):
                table_url = url + f"?offset={k*max_show}&max={max_show}"
                soup = self.driver_process(driver, table_url)
                table = soup.find("tbody")
                rows = table.find_all("tr")
                for r in rows:
                    data = self.find_data(r, i, type_, lec_id=lec_id)
                    if data is not None:
                        self.add_data(lecdata, data, self.data_columns)
                        i += 1
        return lecdata
    
    def get_update_lecdata(self, opt, driver, update_src, type_="data", max_show=500):
        """
        update_src: 
         - lasttable_id
         - lec_ids
         - pages
         - lastupdate
         - ids
        """
        update_dict = {"insert": defaultdict(list), "update": defaultdict(list)}
        day_fmt = "%Y.%m.%d"
        i = update_src["lasttable_id"] + 1
        for lec_id, page, date, idxs in tqdm(zip(update_src["lec_ids"], 
                                                 update_src["pages"], 
                                                 update_src["lastupdate"], 
                                                 update_src["ids"]),
                                             desc="[process] getting update data",
                                             total=len(update_src["lec_ids"])
                                            ):
            person_id_dict = dict(map(lambda x: tuple(reversed(x)), idxs))
            src = (lec_id, page, date)
            if opt == "update_dayenroll":
                update_datas = self.find_update_dayenroll(driver, src, type_, max_show, day_fmt)
                for x in update_datas:
                    if (x[-1] == date) and (person_id_dict.get(x[2]) is not None):
                        x[0] = person_id_dict.get(x[2])  # change to matched person table id
                        self.add_data(update_dict["update"], x, self.data_columns)
                    else:
                        x[0] = i # change to table id
                        self.add_data(update_dict["insert"], x, self.data_columns)
                        i += 1
            elif opt == "update_user":
                update_datas = self.find_update_user(driver, src, type_, max_show, day_fmt)
                update_datas = [[person_id_dict.get(x[1])]+x[-2:] for x in update_datas]
                # id, lec_id, person, daynum, daylast

                for x in update_datas:
                    self.add_data(update_dict["update"], x, self.update_person_columns)
        return update_dict

    
    def find_update_dayenroll(self, driver, src, type_, max_show, day_fmt):
        lec_id, page, date = src
        date_to_find = dt.strptime(date, day_fmt) - timedelta(days=1)
        try_num = 0
        while try_num <= 3:
            table_url = data_processor.edwith_site + page + "/manage/studentManage/list" + f"?offset={try_num*max_show}&max={max_show}"
            soup = data_processor.driver_process(driver, table_url)
            table = soup.find("tbody")
            rows = table.find_all("tr")

            update_datas = []
            cnt = 0
            for r in rows:
                data = data_processor.find_data(r, 0, type_, lec_id=lec_id)
                if data is not None:
                    if dt.strptime(data[-1], day_fmt) <= date_to_find:
                        try_num = 999
                        break
                    else:
                        update_datas.append(data)
                        cnt += 1
            if cnt == len(rows):
                try_num += 1

        if try_num == 3:
            assert False, "Can't find date {} set 'max_show' larger".format(date_to_find)

        return update_datas
    

    def find_update_user(self, driver, src, type_, max_show, day_fmt):
        lec_id, page, date = src
        
        url = self.edwith_site + page + "/manage/studentManage/list"
        soup = self.driver_process(driver, url)
        css_select = "#content > section > div.group_lr.mab10 > div.group_r > p > em"
        total_student = int(soup.select_one(css_select).text.replace(",", ""))
        total_pages = total_student // max_show + 1

        for k in range(total_pages):
            table_url = url + f"?offset={k*max_show}&max={max_show}"
            soup = self.driver_process(driver, table_url)
            table = soup.find("tbody")
            rows = table.find_all("tr")

            update_datas = []
            for r in rows:
                data = self.find_data(r, 0, type_, lec_id=lec_id)
                if data is not None:
                    if dt.strptime(data[-1], day_fmt) <= dt.strptime(date, day_fmt):
                        update_datas.append(data[1:5])

        return update_datas
    
    
    def driver_process(self, driver, url):
        """utils: """
        driver.get(url)
        driver.implicitly_wait(3)
        time.sleep(0.5)
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        return soup
    
    def find_data(self, x, i, type_, **kwargs):
        """utils: """
        if type_=="info":
            res = [
                i,
                x.find(class_="lnk_lecture").get("href"),
                x.find("dt").text.strip(),
                x.find(class_="date").text.strip(),
                x.find(class_="txt_prof").text.strip(),
                x.find(class_="txt_partner").text.strip(),
                x.find("img").get("src"),
                0
            ]
        elif type_=="data":
            if x.find_all("td")[1].text == "수강생":
                string = re.findall(r".*\)", x.find("div", class_="profile_el2").text)[0].strip().encode()
                hash_email = hashlib.sha256(string).hexdigest()
                res = [
                    i,
                    kwargs['lec_id'],
                    hash_email,  # hashed id for email
                    *[int(tag.text) if i == 0 else str(tag.text) for i, tag in enumerate(x.find_all("td")[2:])]
                ]
            else:
                res = None
        return res

    def add_data(self, data_dict, data, columns):
        """utils: """
        for i, c in enumerate(columns):
            data_dict[c].append(data[i])