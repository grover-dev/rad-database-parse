# from pdfminer.high_level import extract_text


# text = extract_text("NEPP-CP-2015-Campola-Paper-DW-NSREC-TN24941.pdf")

# buf = ""
# for line in text:
#     buf += line
#     if line == "\n" and len(buf) > 1:
#         print(buf)
#         buf = "" 

# import webbrowser
# import tabula
# import tabulate

# df = tabula.read_pdf('NEPP-CP-2015-Campola-Paper-DW-NSREC-TN24941.pdf',pages="3")
# print(tabulate(df))
import sqlite3
from sqlite3 import Error
from turtle import title

def connect_to_database(path):
    conn = None
    try:
        conn = sqlite3.connect(path)
    except Error as e:
        print(e)
    finally:
        if conn:
            conn.close()


import camelot
from camelot.handlers import PDFHandler
import os 
import webbrowser
import math
from PyPDF2 import PdfFileReader
import pandas


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
            # print(best_guess)
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
    tables = camelot.read_pdf(pdf_filename, pages=f'{page}', line_scale=40, flavor = 'lattice')
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


def is_table_empty(table):
    if table.df.apply(lambda x: x == '').any(axis=1).apply(lambda y: y== True).all(axis=0):
        return True
    return False





pdf_name =  'NEPP-CP-2015-Campola-Paper-DW-NSREC-TN24941.pdf'
pdf = PdfFileReader(open(pdf_name,'rb'))
num_pages = pdf.getNumPages()
# num_pages = 1
titles = []
tables = []

for page in range(num_pages): 
    new_titles, new_tables = get_tables_and_titles(pdf_name, page)
    for ti, ta in zip(new_titles, new_tables):
        if not is_table_empty(ta):
            if ti == '':
                print(titles[len(titles)-1])
                tables[len(tables)-1].df =  pandas.concat([tables[len(tables)-1].df, ta.df.drop([0])])
                # .append(ta.df) #(ta.df)
                # print(ta.df)
            else:
                titles.append(ti)
                tables.append(ta)

for ti, ta in zip(titles, tables):
    ta.to_csv(f'{ti}.csv')

print(titles)

# tables[5].to_csv('foo.csv')
# camelot.plot(abc[0],kind='text').show()
# input("Press Enter to continue...")
# abc[0].to_csv('foo.csv')
# # print(abc[0])


if __name__ == '__main__':
    path = "main.db"
    connect_to_database(path)

