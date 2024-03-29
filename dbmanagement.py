from pymongo import MongoClient


class MongoManage:
    def __init__(self):
        self.client = MongoClient()
        db = self.client.scheduledb
        self.schedules = db.schedules
        self.test = db.tempschedule

    def checkExisting(self, newdata):
        index = "discord_id"

        id_to_find = newdata[index]
        query_result = self.schedules.find_one({index: id_to_find})
        if query_result != None:
            self.schedules.replace_one({index: id_to_find}, newdata)
            print(f"New data was updated: {newdata}")
            return True
        return False

    def insertNew(self, newdata):
        self.schedules.insert_one(newdata)
        print(f"New data was inserted: {newdata}")

    def findSimilarSection(self, lookup_index, lookup_type):
        current_data = self.schedules.find_one({lookup_type: lookup_index})
        # check to see if user exists, if not raise random exception
        # should i make my own exception? yes. will i? no.
        if current_data == None:
            raise FileNotFoundError
        canonical_name = current_data["name"]

        class_section_dicts = current_data["classes"]
        full_output_dict = {}
        for class_dict in class_section_dicts:
            found_names = self.schedules.find(
                {
                    "classes": {
                        "course": class_dict["course"],
                        "section": class_dict["section"],
                        "instructor": class_dict["instructor"],
                    }
                },
                {"name": 1, "username": 1, "saved_nickname": 1},
            )
            names_list = []
            for student in found_names:
                if student["name"] == canonical_name or student == None:
                    pass
                else:
                    names_list.append(
                        student["name"]
                        + "   //   "
                        + student["saved_nickname"]
                        + "   (@"
                        + student["username"]
                        + ")"
                    )
            class_section_string = f"{class_dict['course']} : {class_dict['section']}"
            full_output_dict[class_section_string] = names_list
        # dictionary returned is formatted as:  {classID : sectionID}:[{name} // discordNickname @{discord name}, {name} // discordNickname @{discord name}...]
        return full_output_dict

    def queryProfs(self, course):
        professorList = []
        # should find all professors who teach a certain course
        for element in self.schedules.find({"classes.course": course}, {"classes": 1}):
            for class_dict in element["classes"]:
                if class_dict["course"] == course:
                    try:
                        if class_dict["instructor"] not in professorList:
                            professorList.append(class_dict["instructor"])
                    except KeyError:
                        print("No instructor listed for this class")
                        pass
        return professorList

    def findStudentswithProfessor(self, prof):
        # should find all students who are taking a class taught by a certain professor
        found_names = self.schedules.find(
            {"classes.instructor": prof},
            {"name": 1, "username": 1, "saved_nickname": 1},
        )
        names_list = []
        output_dict = {}
        # loop over every student found, add them to the list for output
        for student in found_names:
            if student == None:
                pass
            else:
                names_list.append(
                    student["name"]
                    + " // "
                    + student["saved_nickname"]
                    + " (@"
                    + student["username"]
                    + ")"
                )
        # dictionary is formatted as {professor}:[{name} // @{discord name}, {name} // @{discord name}...]
        output_dict[prof] = names_list
        return output_dict

    def amountOfDocs(self, search_value):
        if search_value is None:
            amount_of_docs = self.schedules.find(
                {"studentid": {"$exists": 1}}, {"name": 1}
            ).count()
        else:
            amount_of_docs = self.schedules.find(
                {"campus": search_value}, {"name": 1}
            ).count()
        return amount_of_docs

    def findStudentsWithClass(self, classid):
        found_names = self.schedules.find(
            {"classes.course": classid}, {"name": 1, "username": 1, "saved_nickname": 1}
        )
        full_output_dict = {}
        names_list = []
        check_exists = 0
        for student in found_names:
            names_list.append(
                student["name"]
                + " // "
                + student["saved_nickname"]
                + " (@"
                + student["username"]
                + ")"
            )
            check_exists = 1
        if check_exists == 0:
            raise SyntaxError

        full_output_dict[classid] = names_list
        # dictionary returned is formatted as:  {classID}:[{name} // @{discord name}, {name} // @{discord name}...]
        return full_output_dict

    def getName(self, lookup_index, lookup_type):
        student_name = self.schedules.find_one({lookup_type: lookup_index}, {"name": 1})
        return student_name["name"]

    def reassociate(self, newdata, lookup_type, lookup_index):
        s = self.schedules.find_one({lookup_type: lookup_index})
        if s == None:
            raise FileNotFoundError
        self.schedules.update_one({lookup_type: lookup_index}, {"$set": newdata})
        return

    def closeConnection(self):
        self.client.close()
