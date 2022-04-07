
import tables as tb
from tables import Tables

from PyPDF2 import PdfFileReader
import pandas
import sqlite3
from sqlite3 import Error
import os
from os import listdir
from os.path import isfile, join

from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
import re
import nltk
# from nltk.tag.stanford import NERTagger

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
                    source_paper INTEGER NOT NULL,
                    source_paper_year INTEGER NOT NULL
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


def get_pdf_title(path):
    fp = open(path, 'rb')
    try:
        parser = PDFParser(fp)
        doc = PDFDocument(parser)
        doc_info = doc.info[0]
        return re.sub(r"b'",'',f"{(doc_info['Title'])}{doc_info['ModDate']}") 
    except:
        print(f"could not find pdf metadata for {path}, ignoring...")
        return None

def get_all_files(path):
    return [f for f in listdir(path) if isfile(join(path,f))]

# def find_header(table):
#     for index, row in table.iterrows():
#         print(row)

# work flow: get document, run through priocessing -> convert to temporary csv
# -> check/correct/remove csv (manually rn) 
# -> populate part information, manually insert result information + degradation info
# -> add to radiation database (split up based on category (TID, SEE, etc.), if two papers for given value, put both down and cite both)
# (each paper gets its own entry into database, even if part is repeated, unique ids are generated for each new part in database that is referenced by part databases) 
# -> get parameters from manufacturer (based on category, get relevant info) 
# -> add to part database and back reference the radiation (list unique ids)

pdf_name =  'docs/2015-nasa-compendium.pdf'
get_pdf_title(pdf_name)
# pdf = PdfFileReader(open(pdf_name,'rb'))
# num_pages = pdf.getNumPages()
num_pages = 9
tables_arr = []

# get_pdf_title(pdf_name)
for page in range(num_pages): 
    new_titles, new_tables = tb.get_tables_and_titles(pdf_name, page)
    for ti, ta in zip(new_titles, new_tables):
        tmp_table = Tables(table=ta.df, title=ti)

        if tmp_table.get_table_density() > 0.25: # arbitrary cutoff for what counts as an empty table vs not
            if ti == '':
                last_table = tables_arr[len(tables_arr)-1].table
                last_table = pandas.concat([last_table, ta.df.drop([0])])
                tables_arr[len(tables_arr)-1].table = last_table.reindex()
            else:
                tables_arr.append(tmp_table)
abbreviations_table = []                



# generate csvs for user to check if data parsed properly
for ti in tables_arr:
    ti.table.to_csv(f'tmp_csvs/{ti.title}.csv')

input("verify that csvs were properly generated, press enter to continue...")

print("reloading csv information, deleting csvs...")

tmp_arr = tables_arr.copy()
for ti in tables_arr:
    if os.path.exists(f"tmp_csvs/{ti.title}.csv"):
        ti.table = pandas.read_csv(f"tmp_csvs/{ti.title}.csv")
        os.remove(f"tmp_csvs/{ti.title}.csv")
    else:
        tmp_arr.remove(ti)
tables_arr = tmp_arr.copy()


tmp_arr = tables_arr.copy()
for ti in tables_arr:
    t_type = ti.find_table_type(ti.title)
    if t_type != None:
        ti.type= t_type
    else:
        print(f"could not find type for table: {ti.title}, dropping")
        tmp_arr.remove(ti)
tables_arr = tmp_arr.copy()
input("press enter to continue...")


for ti in tables_arr:
    if "TABLE IV" in ti.title:
        print(ti.get_header()) 
        print(ti.get_row_density(3))
        ti.header_mapping()
        # for index, row in ti.table.iterrows():
        #     print(row)



# for ti in tables_arr:
#     print(ti.title, ti.type)





if __name__ == '__main__':
    path = "main.db"
    conn = connect_to_database(path)
    cursor = conn.cursor()
    create_tables(cursor)
    conn.close()
