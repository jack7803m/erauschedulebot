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
    name = re.sub(r'Name:\s+', '', lines[0])
    studentid1 = re.sub(r'ID:\s+', '', lines[1])
    studentid = re.sub(r'\s+', '', studentid1)

    table_list = tabula.read_pdf(filename, pages = 'all', output_format = "json", lattice=True)
    campus = 'none'
    
    #this should iterate over each table in the list of extracted tables
    #for each table in the list and for each row in each table, add appropriate data to main dict
    class_and_section_dict = {}
    for table in table_list:
        i = 0
        for lis in table['data']:
            if i > 0:
                filtered_courseID = re.sub('\r', ' ', lis[0]['text'])
                filtered_sectionID = re.sub('\r', ' ', lis[1]['text'])
                class_and_section_dict[filtered_courseID] = filtered_sectionID
                if campus == 'none':
                    if re.match(r'.*DB.*', filtered_sectionID) is not None: campus = 'daytona'
                    elif re.match(r'.*PC.*', filtered_sectionID) is not None: campus = 'prescott' 
            i += 1
    
    extracted = {'studentid': studentid, 'name': name, 'classes': class_and_section_dict, 'campus': campus}
    return extracted