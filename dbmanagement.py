from pymongo import MongoClient

class MongoManage:
    def __init__(self):
        self.client = MongoClient()
        db = self.client.scheduledb
        self.schedules = db.schedules
        

    def checkExisting(self, newdata):
        id_to_find = newdata['studentid']
        query_result = self.schedules.find_one({'studentid': id_to_find})
        if query_result != None:
            self.schedules.replace_one(
                {"studentid": id_to_find},
                newdata)
            print(f"New data was updated: {newdata}")
            return True
        return False
        

    def insertNew(self, newdata):
        self.schedules.insert_one(newdata)
        print(f"New data was inserted: {newdata}")
        
    #currently unused afaik  
    def findSimilarClass(self, studentid):
        current_data = self.schedules.find_one({'studentid': studentid})
        #check to see if user exists, if not raise random exception
        if current_data == None: 
            raise FileNotFoundError
        #get the user's actual name for later referencing
        canonical_name = current_data['name']

        classes_data = current_data['classes']
        full_output_dict = {}
        for classes_item in classes_data:
            found_names = self.schedules.find({f'classes.{classes_item}': {'$exists': 1}},{'name': 1, 'username': 1, 'saved_nickname': 1})
            names_list = []
            for student in found_names:
                if student['name'] == canonical_name or student == None:
                    pass
                else:
                    names_list.append(student['name'] + ' // ' + student['saved_nickname'] + ' (@' + student['username'] + ')')
            full_output_dict[classes_item] = names_list
        #dictionary returned is formatted as:  {classID}:[{name} // @{discord name}, {name} // @{discord name}...] 
        return full_output_dict
    

    def findSimilarSection(self, lookup_index, lookup_type):
        current_data = self.schedules.find_one({lookup_type: lookup_index})
        #check to see if user exists, if not raise random exception
        if current_data == None: 
            raise FileNotFoundError
        #get the user's actual name for later referencing
        canonical_name = current_data['name']

        class_section_correlation = current_data['classes']
        full_output_dict = {}
        for class_name in class_section_correlation.keys():
            found_names = self.schedules.find({f'classes.{class_name}': class_section_correlation[class_name]},{'name': 1, 'username': 1, 'saved_nickname': 1})
            names_list = []
            for student in found_names:
                if student['name'] == canonical_name or student == None:
                    pass
                else:
                    names_list.append(student['name'] + '   //   ' + student['saved_nickname'] + '   (@' + student['username'] + ')')
            #concat class and section name for clarity
            class_section_string = f'{class_name} : {class_section_correlation[class_name]}'
            full_output_dict[class_section_string] = names_list
        #dictionary returned is formatted as:  {classID : sectionID}:[{name} // discordNickname @{discord name}, {name} // discordNickname @{discord name}...]
        return full_output_dict
    

    def amountOfDocs(self):
        amount_of_docs = self.schedules.find({'studentid': {'$exists': 1}}).count()
        return amount_of_docs
        

    def findStudentsWithClass(self, classid):
        #check to see if the user even input a course code that exists in the system
        exists = self.schedules.find({f'classes.{classid}': {'$exists': 1}})
        if exists == {} or exists == None:
            raise SyntaxError
        #so this basically uhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh just read it
        found_names = self.schedules.find({f'classes.{classid}': {'$exists': 1}},{'name': 1, 'username': 1, 'saved_nickname': 1})
        full_output_dict = {}
        names_list = []
        for student in found_names:
            if student == None:
                pass
            else:
                names_list.append(student['name'] + ' // ' + student['saved_nickname'] + ' (@' + student['username'] + ')')
        full_output_dict[classid] = names_list
        #dictionary returned is formatted as:  {classID}:[{name} // @{discord name}, {name} // @{discord name}...] 
        return full_output_dict
    

    def getName(self, lookup_index, lookup_type):
        student_name = self.schedules.find_one({lookup_type: lookup_index}, {'name': 1})
        return student_name['name']


    def closeConnection(self):
        self.client.close()
        