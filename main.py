import tables as tb
from tables import Tables
# import database as db
from database import Database

import os
from os import listdir
from os.path import isfile, join






def generate_abbreviations_list(table):
    abbrev_to_text_list = []
    for index, row in table.iterrows():
        for col in row:
            abbrev = ""
            full_text = ""
            equals_flag = False
            parantheses_lock = False
            for char in col:
                if char == "(":
                    parantheses_lock = True
                elif char == ")":
                    parantheses_lock = False
                if char == "\n" and not parantheses_lock:
                    abbrev_to_text_list.append([abbrev, " ".join(full_text.split())])
                    abbrev = ""
                    full_text = ""
                    equals_flag = False
                elif char != "=" and not equals_flag:
                    abbrev += char
                elif char != "=" and equals_flag:
                    abbrev = " ".join(abbrev.split())
                    full_text += char
                elif char == "=":
                    equals_flag = True
    return abbrev_to_text_list

def abbreviation_expansion(abbrev_list, table):
    for index, row in table.iterrows():
        for col in row:
            for abbrev in abbrev_list:
                col = col.replace(abbrev[0],abbrev[1])
    return table



def get_all_files(path):
    return [f for f in listdir(path) if isfile(join(path,f))]


# work flow: get document, run through priocessing -> convert to temporary csv
# -> check/correct/remove csv (manually rn) 
# -> populate part information, manually insert result information + degradation info
# -> add to radiation database (split up based on category (TID, SEE, etc.), if two papers for given value, put both down and cite both)
# (each paper gets its own entry into database, even if part is repeated, unique ids are generated for each new part in database that is referenced by part databases) 
# -> get parameters from manufacturer (based on category, get relevant info) 
# -> add to part database and back reference the radiation (list unique ids)




""" feature list:
    - parametric search for radiation tolerance/behavior?
    - parametric search for parts, 
    - be able to link parts that have no formal radiation testing but have been used on missions 
        - include mission state (failure/success)
    - have process for adding new parts by users (also solicit support from others)


"""



pdf_name =  'docs/2015-nasa-compendium.pdf'

if __name__ == "__main__":
    path = "main.db"
    db = Database(path)
    db.create_tables()

    for file in os.listdir("docs/"):
        filename = os.fsdecode(file)
        state = db.check_if_exists("rad_table", "source_paper", tb.get_pdf_title(f'docs/{str(filename)}'))
        # if "2015" in filename:
        if filename.endswith(".pdf") and not state:
            print(filename)
            tables = tb.get_all_tables(f'docs/{str(filename)}')
            if tables != None:
                tables = tb.csv_check(tables)
                tables = tb.type_check(tables)
                
                for ta in tables:
                    ta.map_header()
                    if ta.mapped_header != None:
                        for row in range(1, ta.get_num_rows()):
                            if ta.get_mapped_row_type(row) == "valid":
                                keys, values = ta.map_row(row)
                                db.add_entry_to_table("rad_table",keys,values)
                            # print(ta.get_row(row))
    db.close_conn()
    # for ta in tables:
        