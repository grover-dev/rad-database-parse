import camelot
from camelot.handlers import PDFHandler
import os 
import math


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