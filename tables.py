from cmath import nan
from distutils.dir_util import copy_tree
import camelot
from camelot.handlers import PDFHandler
import os 
import math
import re
from numpy import NaN
import pandas
from PyPDF2 import PdfFileReader

from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
import re
from fuzzywuzzy import fuzz, process

# original pulled from https://stackoverflow.com/questions/58185404/python-pdf-parsing-with-camelot-and-extract-the-table-title
# code has been modified to better handle target documents
# Helper methods for _bbox
def top_mid(bbox):
    return ((bbox[0]+bbox[2])/2, bbox[3])

def bottom_mid(bbox):
    return ((bbox[0]+bbox[2])/2, bbox[1])

def distance(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

def get_closest_text(table, htext_objs):
    min_distance = 100  # Cause 9's are big :)
    best_guess = None
    table_flag = False
    table_mid = top_mid(table._bbox)  # Middle of the TOP of the table
    for obj in htext_objs:
        text_mid = bottom_mid(obj.bbox)  # Middle of the BOTTOM of the text
        d = distance(text_mid, table_mid)
        if d < min_distance and len(obj.get_text().strip()) < 50:
            if table_flag:
                best_guess += f" {obj.get_text().strip()}"
                return best_guess
            else:
                best_guess = obj.get_text().strip()

            if "table" in best_guess.lower():
                table_flag = True

            min_distance = d
    if not table_flag:
        return "" 
    return best_guess

def get_tables_and_titles(pdf_filename, page):
    """Here's my hacky code for grabbing tables and guessing at their titles"""
    my_handler = PDFHandler(pdf_filename)  # from camelot.handlers import PDFHandler
    tables = camelot.read_pdf(pdf_filename, pages=f'{page}', line_scale=40, flavor = 'lattice', copy_text=['v'])
    print('Extracting {:d} tables...'.format(tables.n))
    titles = []
    with camelot.utils.TemporaryDirectory() as tempdir:
        for table in tables:
            my_handler._save_page(pdf_filename, table.page, tempdir)
            tmp_file_path = os.path.join(tempdir, f'page-{table.page}.pdf')
            layout, dim = camelot.utils.get_page_layout(tmp_file_path)
            htext_objs = camelot.utils.get_text_objects(layout, ltype="horizontal_text")
            tmp = get_closest_text(table, htext_objs)
            titles.append(tmp)  # Might be None
    return titles, tables

def get_pdf_title(path):
    fp = open(path, 'rb')
    try:
        parser = PDFParser(fp)
        doc = PDFDocument(parser)
        doc_info = doc.info[0]
        return re.sub(r"b'",'',f"{(doc_info['Title'])}{doc_info['ModDate']}").replace("'","").replace("\"","")
    except:
        print(f"could not find pdf metadata for {path}, ignoring...")
        return None

def get_all_tables(pdf_filename):
    pdf = PdfFileReader(open(pdf_filename,'rb'))
    num_pages = pdf.getNumPages()
    
    tables_arr = []    
    for page in range(num_pages): 
        new_titles, new_tables = get_tables_and_titles(pdf_filename, page)
        for ti, ta in zip(new_titles, new_tables):
            tmp_table = Tables(table=ta.df, title=ti, source_paper = get_pdf_title(pdf_filename))

            if tmp_table.get_table_density() > 0.25: # arbitrary cutoff for what counts as an empty table vs not
                if ti == '':
                    last_table = tables_arr[len(tables_arr)-1].table
                    last_table = pandas.concat([last_table, ta.df.drop([0])])
                    tables_arr[len(tables_arr)-1].table = last_table.reindex()
                else:
                    tables_arr.append(tmp_table)

    return tables_arr

def csv_check(tables_arr):
    # generate csvs for user to check if data parsed properly
    for ti in tables_arr:
        ti.table.to_csv(f'tmp_csvs/{ti.title}.csv', index=False)

    input("verify that csvs were properly generated, press enter to continue...")

    print("reloading csv information, deleting csvs...")
    
    tmp_arr = tables_arr.copy()
    for ti in tables_arr:
        if os.path.exists(f"tmp_csvs/{ti.title}.csv"):
            ti.table = pandas.read_csv(f"tmp_csvs/{ti.title}.csv", index_col=False)
            os.remove(f"tmp_csvs/{ti.title}.csv")
        else:
            tmp_arr.remove(ti)
    return tmp_arr

def type_check(tables_arr):
    tmp_arr = tables_arr.copy()
    for ti in tables_arr:
        t_type = ti.find_table_type(ti.title)
        if t_type != None:
            ti.type= t_type
        else:
            print(f"could not find type for table: {ti.title}, dropping")
            tmp_arr.remove(ti)
    return tmp_arr

class Tables:
    def __init__(self, table, title, type=None, ta_header = None, mapped_header = None, source_paper = None):
        self.table = table
        self.title = title
        self.type = type
        self.header = ta_header
        self.mapped_header = mapped_header
        self.source_paper = source_paper
    
    # s_c_w - string contains word, checks if word (surrounded by spaces, punctuation or start/end of string)
    # is in the given string
    def s_c_w(self, s, w):
        return (re.compile(r'\b({0})\b'.format(w), flags=re.IGNORECASE).search(s) != None)

    # find the type of the table 
    # todo: switch to using fuzzy matching
    def find_table_type(self, title):
        title = title.lower()
        if self.s_c_w(title,"principal") or self.s_c_w(title,"investigator"):
            return "principal_investigator"
        elif self.s_c_w(title,"acronym") or self.s_c_w(title, "abbreviations"):
            return "abbreviation"
        elif self.s_c_w(title, "tid") or self.s_c_w(title, "see") or self.s_c_w(title, "dd") or self.s_c_w(title, "seu") or self.s_c_w(title, "let") or self.s_c_w(title, "ongoing") or self.s_c_w(title, "dose"):
            return "rad"
        return None

    # get the header
    def get_header(self):
        if self.header == None:
            row = self.table.values.tolist()[0]
            if row[0] == 0:
                row = row[1:]
            return row
        else:
            return self.header

    # map the header to column in database
    # todo: may need to rework to deal with tables from poorly made pdfs 
    def map_header(self):
        if self.header == None:
            self.header = self.get_header()
            #todo - modify check here
        if self.type == "rad":
            category = ["part number","manufacturer","device function", "technology", "results", "spec", "dose rate", "proton energy", "degradation level",  "proton fluence"]
            cols = len(self.header)
            rows = len(category)

            matrix = []        
            for elem in self.header:
                elem = str(elem).strip().replace("\n","")
                tmp = []
                for cat in category:
                    tmp_fuzz = fuzz.partial_ratio(cat, str(elem).lower())
                    tmp.append(tmp_fuzz)
                matrix.append(tmp)

            max_arr = {}
            for col in range(cols):
                max = 0
                max_index = 0
                for row in range(rows):
                    if matrix[row][col] > max:
                        max = matrix[row][col]
                        max_index = row
                    # elif matrix[row][col] == max:
                if max >= 75:
                    max_arr[category[col].replace(" ", "_")] = [max, max_index]
                else:
                    max_arr[category[col].replace(" ", "_")] = [max,None]
            self.mapped_header = max_arr
        # for cat in category:
        #     print(f"{cat}|", end = " ")
        # for row, elem in zip(matrix, self.header):
        #     elem = str(elem).strip().replace("\n","")
        #     print(f"\n{elem}{' '*(50-len(elem))}", end="")
        #     for col in row:
        #         print(f"{col}{' '*(3-len(str(col)))}", end = " ")
        # print(' ' * 50)
        # for elem in max_arr:
        #     print(f"{elem}{' '*(3-len(str(col)))}", end = " ")
        # print()
        # for elem in range(len(max_arr)):
        #     for elem_2 in range(elem, len(max_arr)):
        #         if max_arr[elem][2] == max_arr[elem_2][2] and elem != elem_2:
        #             print(max_arr[elem], max_arr[elem_2])

    def get_num_rows(self):
        return len(self.table.values.tolist())

    def get_row(self, index):
        return self.table.values.tolist()[index]

    def get_row_density(self, index):
        row = self.get_row(index)
        return (len(row) - (row.count("") + row.count(None)+row.count(NaN)+row.count(nan)))/ len(row) 


    def map_row(self, index):
        row = self.get_row(index)
        
        if self.mapped_header == None:
            self.map_header()
        keys = []
        values = []
        for col in self.mapped_header:
            column_mapping = self.mapped_header[col][1]
            if column_mapping != None:
                value =  row[column_mapping]
                try:
                    # if value != None and value != nan and value != NaN and not math.isnan(value):
                    # try:
                        keys.append(col)
                        if type(value) == str:
                            values.append(value.replace("\n"," "))
                        elif type(value) == int:
                            values.append(value)
                        else:
                            raise Exception("null val")
                except:
                    #  print(col, value, type(value))
                    raise Exception("null val")
                #     input("enter to continue")
        keys.append('source_paper')
        values.append(self.source_paper)
        
        return keys, values

    def get_table_density(self):
        '''returns table density(i.e. how many values are not empty'''
        density = 0
        for index, row in self.table.iterrows():
            density += self.get_row_density(index)        
        return density/(index+1)


    def get_mapped_row_type(self, index):
        try:
            mp_keys, mp_values = self.map_row(index)
            if self.mapped_header == None:
                self.map_header()
            density = (len(mp_values) - (mp_values.count("") + mp_values.count(None)+mp_values.count(NaN)+mp_values.count(nan))) / len (self.mapped_header)
            if density < 0.5:
                # print(mp_values)
                return "invalid"
            return "valid"
        except Exception as e:
            # print(e)
            # print(self.table.values.tolist())
            # print(self.get_row(index))
            # input("enter to continue")
            return "invalid"  



class Part:
    def __init__(self, keys, values):
        self.keys = keys
        self.values = values
    