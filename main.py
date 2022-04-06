import tables as tb
from PyPDF2 import PdfFileReader
import pandas
import sqlite3
from sqlite3 import Error
import os
from os import listdir
from os.path import isfile, join

def connect_to_database(path):
    conn = None
    try:
        conn = sqlite3.connect(path)
    except Error as e:
        print(e)
    return conn

def create_tables(cursor):
    paper_table = """ CREATE TABLE IF NOT EXISTS paper_table (
                      id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      paper_name VARCHAR(1024)                      
                  );"""
    cursor.execute(paper_table)

    rad_table = """ CREATE TABLE IF NOT EXISTS rad_table (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    part_number VARCHAR(255) NOT NULL, 
                    manufacturer VARCHAR(255) NOT NULL,
                    tester_id VARCHAR(255),
                    device_function VARCHAR(255) NOT NULL,
                    category VARCHAR(255),
                    technology VARCHAR(255),
                    principal_investigator VARCHAR(255),
                    results VARCHAR(1024) NOT NULL,
                    in_spec BOOL,
                    dose_rate VARCHAR(255),
                    proton_energy VARCHAR(255),
                    degradation_level VARCHAR(255),
                    proton_fluence VARCHAR(255),
                    misc_info VARCHAR(1024),
                    source_paper INTEGER NOT NULL
                    ); """

    cursor.execute(rad_table)

    # holds info on all abbreviations that are used in the documents 
    # type specifies whether the abbreviation is for a term or for a principal investigator
    abbreviation_table = """ CREATE TABLE IF NOT EXISTS abbreviation_table (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        abbreviation VARCHAR(255) NOT NULL,
                        expansion VARCHAR(255) NOT NULL,
                        type VARCHAR(255) NOT NULL,
                        source_papers VARCHAR(1024) NOT NULL
                        ); """
    cursor.execute(abbreviation_table)
    
    # categories = ["operational_amplifiers", "memory", "transistors", "voltage_references", "voltage_regulators", ""]

    # for cat in categories:







def is_table_empty(table):
    if table.df.apply(lambda x: x == '').any(axis=1).apply(lambda y: y== True).all(axis=0):
        return True
    return False


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


def find_table_type(title):
    title = title.lower()
    if "principal" in title or "investigator" in title:
        return "principal_investigator"
    elif "acronym" in title or "abbreviations" in title:
        return "abbreviation"
    elif "tid" in title or "see" in title or "dd" in title or "seu" in title or "let" in title:
        return "rad"
    return None

def get_pdf_title(path):
    return os.path.basename(path)

def get_all_files(path):
    return [f for f in listdir(path) if isfile(join(path,f))]
    
# def find_header(table):
#     for index, row in table.iterrows():
#         print(row)

# work flow: get document, run through priocessing -> convert to temporary csv
# -> check/correct csv (manually rn) 
# -> add to radiation database (split up based on category (TID, SEE, etc.), if two papers for given value, put both down and cite both)
# (each paper gets its own entry into database, even if part is repeated, unique ids are generated for each new part in database that is referenced by part databases) 
# -> get parameters from manufacturer (based on category, get relevant info) 
# -> add to part database and back reference the radiation (list unique ids)

pdf_name =  'docs/NEPP-CP-2015-Campola-Paper-DW-NSREC-TN24941.pdf'
print(get_all_files("docs/"))
pdf = PdfFileReader(open(pdf_name,'rb'))
num_pages = pdf.getNumPages()
# num_pages = 5
titles = []
tables = []

get_pdf_title(pdf_name)
for page in range(num_pages): 
    new_titles, new_tables = tb.get_tables_and_titles(pdf_name, page)
    for ti, ta in zip(new_titles, new_tables):
        if not is_table_empty(ta):
            if ti == '':
                tmp = tables[len(tables)-1].df
                if (ta.df[ta.df != ""].count().to_numpy().sum()/ ta.df[ta.df == ""].count().to_numpy().sum() >= 0.5):
                    tmp = pandas.concat([tmp, ta.df.drop([0])])
                    tables[len(tables)-1].df = tmp
            else:
                titles.append(ti)
                tables.append(ta)
abbreviations_table = []                
for ti, ta in zip(titles, tables):
    ta.to_csv(f'{ti}.csv')

input("verify that csvs were properly generated, press enter to continue...")

print("reloading csv information, deleting csvs...")
for index, ti in enumerate(titles):
    if os.path.exists(f"{ti}.csv"):
        tables[index] = pandas.read_csv(f"{ti}.csv")
        os.remove(f"{ti}.csv")

# for ti, ta in zip(titles, tables):
#     ta.to_csv(f'{ti}.csv')

print(titles)

input("tmp")





if __name__ == '__main__':
    path = "main.db"
    conn = connect_to_database(path)
    cursor = conn.cursor()
    create_tables(cursor)
    conn.close()
