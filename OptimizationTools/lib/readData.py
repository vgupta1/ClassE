""" Create a list of courses from .csv files
    Structure of files is assumed from excel prototype"""

import csv
import sesClasses as ses
from sys import __stdout__ #default logging location  
from wx.lib.pubsub import Publisher as pub


def importNoConflictGroups(csv_filename):
    """Import the list of groups which cannot conflict."""
    f = csv.reader(open(csv_filename, 'rU'))
    #throw away headers
    f.next()
    no_conflict_dict = {}
    for line in f:
        if line[0] <> "":
            no_conflict_dict[line[0]] = []
            last_key = line[0]

        if line[3] == "":
            line[3] = "LEC"

        no_conflict_dict[last_key].append((line[1].strip().upper(), 
                                           line[2].strip().upper(), 
                                           line[3].strip().upper()))

    return no_conflict_dict

def importRoomInventory(csv_filename):
    """Import room inventory to a list roomInstance"""
    f = csv.reader(open(csv_filename, 'rU'))
    headers = f.next()

    rooms = []
    for roomInfo in f:
        #Treat the seating style separately
        assert(headers[2] == "Seating Style")
        av_equip = []
        if roomInfo[2]:
            av_equip = [roomInfo[2]]
       
        #Treat remaining equipment, if non-blank
        paired_info = zip(headers[3:], roomInfo[3:]) #exclude the name and size
        #only add to list if nonblank
        av_equip += [h for h,r in paired_info if r ] 
     
        sName = roomInfo[0]
        if sName in rooms:
            raise ses.SESError("Room %s appears twice in inventory." % sName)
        else:
            r = ses.Room(sName, roomInfo[1], av_equip)
            rooms.append(r)     
    
    return rooms

def importCourses(csv_filename, roomInventory):
    ''' Imports to list of courses.  
    roomInventory is dict of rooms
    '''
    #assumes we know the headers and structure of Excel Sheet
    #Changing them BREAKS this code.
    f = csv.reader(open(csv_filename, 'rU'))

    #correct the misnamed headers
    headers = f.next()    
    old_names = ("Course", "Section", "Title", "Dept", "Half", 
                     "Anticipated Enrollment")
    new_names = ("courseNumber", "section", "title", "dept", "half", 
                     "enrollment")

    headers_dict = dict(zip(old_names, new_names))
    for indx, h in enumerate(headers):
        if h in old_names:
            headers[indx] = headers_dict[h]

    courses = []
    for vals in f:
        d = dict(zip(headers, vals))

        #Arguments must become objects
        d["enrollment"] = int(d["enrollment"])

        if d["AV Requirements"]:
            d["av_requirements"] = d["AV Requirements"].split(", ")
        del d["AV Requirements"]

        #delete if its blank
        if not d["classtype"]:
            del d["classtype"]

        #pop off the first one
        #VG check for a " "
        instructors = d["Instructors"].split(", ")
        instructors = [ses.Instructor(i) for i in instructors]

        d["instructor"] = instructors[0]
        del d["Instructors"]
            
        respectRoom = convertYesNoToBool(d["Respect Room"], False)
        del d["Respect Room"]
        
        if d["Respect Time"]:
            d["respectTime"] = convertYesNoToBool(d["Respect Time"], False)
        del d["Respect Time"]

        timePrefs = _createTimeSlots(d)
        d["firstTimePref"] = timePrefs[0]
        del d["half"]

        roomPrefs, in_inv = _createRooms(d, roomInventory, respectRoom)
        
        c = ses.Course(**d)
        c.addExtraInstructors(instructors[1:])
        c.addTimePrefs(timePrefs[1:])
        c.addRoomPrefs(roomPrefs, respectRoom)

        if c in courses:
            raise ses.SESError("Attempted to add Course %s twice" % c)

        courses.append(c)

    #Every recitation/breakout has a partner lecture
    for c in courses:
        if c.isRec() or c.isBreakout():
            partner_courses = filter(lambda x: x.isSame(c.number, c.section, "LEC"), 
                                     courses)
            #exit early for efficiency
            if len(partner_courses) == 1:
                continue
            elif not partner_courses:
                raise ses.SESError("Course %s has no partner lecture" % c)
            else:
                raise ses.SESError("Course %s has %d possible partner lectures" % 
                            (c, len(partner_courses)))

        
    return courses

def _createRooms(d, roomInventory, respectRoom, num_prefs = 3):
    """return a prefernece ordered, list of rooms.  
    d is a dictionary of room_prefs {"Room 1":"E51-135", "Room 2":"E62-133"}
    blank requests are ignored.
    Rooms not in inventory will be created if respectRoom = True.
    If room not inventory, and not "respect", will log error."""
    out, all_in_inv = [], True
    for ix_pref in range(1, num_prefs + 1):
        roomName = d.get("Room " + str(ix_pref), "").strip()
        del d["Room " + str(ix_pref)]

        if not roomName:
            continue
        
        #search for it in the list.  
        room_list = filter(lambda x: str(x) == roomName, roomInventory)
        
        if room_list:
            assert len(room_list) == 1
            out.append(room_list[0])
#         elif respectRoom:
#             out.append(ses.Room(roomName, ses.Room.MAX_SIZE))
        else:
            out.append(ses.Room(roomName, ses.Room.MAX_SIZE))
            all_in_inv = False

            #only issue warning if not respect room
            if not respectRoom:
                pub.sendMessage("warning", "Room %s not in inventory" % roomName)


    return out, all_in_inv


def _createTimeSlots(d, numPrefs=3):
    """returns a list of the time slot preferences in order
    d is again a dictionary.  see the below workhorse for details of elements"""
    ts_out = []
    for ix in range(1, numPrefs + 1):
        ts = _createTimeSlot(d, ix)
        if ts is not None:
            ts_out.append(ts)      
            
    return ts_out

def _createTimeSlot(d, ix):
    """do this one at a time"""
    if d["Days " + str(ix)]:
        days = d["Days " + str(ix)].split(", ")
        days = " ".join(days)
        ts = ses.TimeSlot(d["half"], days, d["Start Time " + str(ix)], 
                            d["End Time " + str(ix)])
    else:
        ts = None

    del d["Days " + str(ix)], d["Start Time "+ str(ix)]
    del d["End Time " + str(ix)]
    
    return ts

def addAssignments(courses, roomInventory, csv_filename):
    """Add assignments to courselist  
    """
    f = csv.reader(open(csv_filename, 'rU'))
    headers = f.next()
    all_viable = []

    for courseInfo in f:
        d = dict(zip(headers, courseInfo))
        #make sure course exists        
        find_course = lambda c : c.isSame(d["Course"], d["Section"], d["classtype"])
        course = filter(find_course, courses) 
        if not course:
            raise ses.SESError("Course %s-%s-%s not in list" % 
                    (d["Course"], d["Section"], d["classtype"]))
        else:
            assert(len(course) == 1)
            course = course[0]

        #we only add details for courses that are properly assigned
        if not (d["Room"] and d["StartTime"] and d["EndTime"] and d["Days"]):
            pub.sendMessage("warning", "Course %s-%s-%s not properly assigned\n" % (
                    d["Course"], d["Section"], d["classtype"]) )
            continue
            
        #create the room
        #this is an annoyance because of roomnames
        find_room = lambda r: str(r) == d["Room"].strip().upper()
        room = filter(find_room, roomInventory)
        if room:
            assert len(room == 0)
            room = room[0]
        else:
            #fail silently
            pub.sendMessage("warning", "Room %s not in inventory\n" % d["Room"])
            room = ses.Room(d["Room"], ses.Room.MAX_SIZE)

        #create the timeslot
        sdays = d["Days"].split(", ")
        sdays = " ".join(sdays)
        ts = ses.TimeSlot(d["Half"], sdays, d["StartTime"], d["EndTime"])

        course.addAssignment(room, ts, False)

    return courses

def importB2BPairs(b2b_path, courses):
    """Should yield an empty list if nothing at path"""
    #assumes we know the headers and structure of Excel Sheet
    #Changing them BREAKS this code.

    #Try opening hte back-2-back, if not there warn and ignore
    try:
        f = csv.reader(open(b2b_path, 'rU'))
    except IOError:
        pub.sendMessage("warning", "B2B File not found.  No B2B constraints will be used.")
        return []

    #drop the headers
    f.next()    
    out = []
    for line in f:
        c1 = tuple(line[:3])
        c2 = tuple(line[3:])
        
        courses_1 = filter(lambda c: c.isSame(*c1), courses)
        if not courses_1:
            pub.sendMessage("warning", 
                    "Course %s %s %s from B2B file not found.  Constraint Skipped." % c1)
            continue
        elif len(courses_1) > 1:
            raise ses.SESError("Multiple courses match B2B listing %s %s %s" % c1)

        courses_2 = filter(lambda c: c.isSame(*c2), courses)
        if not courses_2:
            pub.sendMessage("warning", 
                    "Course %s %s %s from B2B file not found.  Constraint Skipped." % c2)
            continue
        elif len(courses_2) > 1:
            raise ses.SESError("Multiple courses match B2B listing %s %s %s" % c2)

        out.append((c1, c2))
    return out

def convertYesNoToBool(yes_no, default_blank):
    "Convert 'Y'/'N'/'' to true/false/default_blank resp"
    if yes_no.strip().upper() == "Y":
        return True
    elif yes_no.strip().upper() == "N":
        return False
    elif yes_no.strip().upper() == "":
        return default_blank
    else:
        raise ses.SESError("%s must be one of 'Y', 'N', '' " % yes_no )
    
def main():
    #VG Change this to take in system args
    rooms = importRoomInventory("./DataFiles/roomInventory.csv")
    print len(rooms)
    
    courses = importCourses("./DataFiles/courseRequests.csv", rooms)
    print len(courses)
    
    no_conflicts = importNoConflictGroups("./DataFiles/NoConflict.csv")
    
    courses = addAssignments(courses, rooms, "./DataFiles/aug3.csv")
    print len(courses)
    
if __name__ == '__main__':
  main()
