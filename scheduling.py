import tabula
import fitz
import re

def check_metadata(inputmetadata):
    template_metadata = {'format': 'PDF 1.6', 'title': '', 'author': '', 'subject': '', 'keywords': '', 'creator': '', 'producer': 'Oracle BI Publisher 12.2.1.4.0', 'creationDate': '', 'modDate': '', 'trapped': '', 'encryption': 'Standard V4 R4 128-bit AES'}
    if inputmetadata['format'] != template_metadata['format'] or inputmetadata['creator'] != template_metadata['creator'] or inputmetadata['trapped'] != template_metadata['trapped'] or inputmetadata['encryption'] != template_metadata['encryption']:
        return False
    else: return True
    

def extract_data(filename):
    with fitz.open(filename) as pdfdata:
        if check_metadata(pdfdata.metadata) is False: 
            print(f"Bad pdf metadata: {pdfdata.metadata}")
            raise NotImplementedError
        pdftext = pdfdata[0].getText()
    lines = pdftext.split('\n')
    name = re.sub('Name:\s+', '', lines[0])
    studentid1 = re.sub('ID:\s+', '', lines[1])
    studentid = re.sub('\s+', '', studentid1)

    table = tabula.read_pdf(filename, pages = 1, output_format = "json")[0]
    #this will only read one table - if the schedule goes to 2 pages it wont read the second one
    i = 0
    class_and_section_dict = {}
    for lis in table['data']:
        if i > 0:
            filtered_courseID = re.sub('\r', ' ', lis[0]['text'])
            filtered_sectionID = re.sub('\r', ' ', lis[1]['text'])
            class_and_section_dict[filtered_courseID] = filtered_sectionID
        i += 1
    
    extracted = {'studentid': studentid, 'name': name, 'classes': class_and_section_dict}
    return extracted