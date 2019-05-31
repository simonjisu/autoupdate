from auto import Autoupdate
import argparse
import sys
import sqlite3
from pathlib import Path

class LOGIN(object):
    def __init__(self, path):
        txts = Path(path).read_text().split()
        self.email = txts[0].split("=")[1].strip("'")
        self.password = txts[1].split("=")[1].strip("'")

def main(args):
    auto = Autoupdate(base_path=args.base_path, driver_path=args.driver_path)
    if args.opt == "show":
        try:
            res = auto.show_lec_available()
            for r in res:
                print("\t".join([str(x) for x in r]))
        except sqlite3.OperationalError as e:
            print(e)
        print("Install the program first")
    elif args.opt == "debug":
        pass
    elif args.opt == "del_program":
        assert args.delopt is not None, "must insert delete option: -del [0-secure, 1-database, 2-all]"
        secure_path = Path(args.login_path)
        database_path = Path(args.base_path) / "database" / "lecture.db"
        del_list = [secure_path, database_path]
        if args.delopt == 2:
            for x in del_list:
                x.unlink()
                x.parent.rmdir()
        else:
            del_list[args.delopt].unlink()
            del_list[args.delopt].parent.rmdir()
        
        database_path.unlink()
        database_path.parent.rmdir()
        print(f"removed {args.login_path}")
    elif args.opt in ["new_init", "update_dayenroll", "update_user"]:
        if args.opt == "new_init":
            secure_path = Path(args.login_path)
            print(f"mode: {args.opt}")
            if not secure_path.parent.exists():
                secure_path.parent.mkdir()
            if not secure_path.exists():
                email = input("등록할 이메일을 입력: ")
                password = input("등록할 비밀번호 입력: ")
                with secure_path.open(mode="w") as handle:
                    print(f"email='{email}'", file=handle)
                    print(f"password='{password}'", file=handle)
            login = LOGIN(args.login_path)
            auto.init_program(
                login=login, 
                max_show=args.max_show, 
                save=args.save)
        elif args.opt in ["update_dayenroll", "update_user"]:
            if args.lec_ids is None:
                lec_ids = ["all"]
            else:
                lec_ids = args.lec_ids
            print(f"mode: {args.opt} lec_ids: {lec_ids}")
            login = LOGIN(args.login_path)
            auto.update(login=login,
                        opt=args.opt,
                        max_show=args.max_show, 
                        lec_ids=lec_ids)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="\tpython main.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""\
    insert options below to run this program: 
    options('-op'/'--opt'): 
        * new_init: first install program
        * update_dayenroll: update daily user enrollment
        * update_user: update number of day that user comeback and last day visit
        * show: show all avaiable lectures
        * del_program: remove all secure, database files"""
    )
    parser.add_argument("-op", "--opt", required=True,
        help="new_init, update_dayenroll, update_user, show")
    parser.add_argument("-bp", "--base_path", type=str, default=".",
        help="basic path of this program, default is current path '.' ")
    parser.add_argument("-dp", "--driver_path", type=str, default="./src",
        help="chrome driver path of this program, default is './src' ")
    parser.add_argument("-lgp", "--login_path", type=str, default=".secure/LOGIN.py",
        help="login information in dir '.secure/LOGIN.py'")
    parser.add_argument("-ms", "--max_show", type=int, default=1000,
        help="max offset when visit student list table url")
    parser.add_argument("-l","--lec_ids", nargs="+",
        help="lecture ids to update 'all' or list of number, default is ['all']")
    parser.add_argument("-del","--delopt", type=int,
        help="delete option [1-all, 2-secure, 3-database]")
    parser.add_argument("-sv","--save", action="store_true",
        help="save install data to pickle file")
    args = parser.parse_args()
    main(args)