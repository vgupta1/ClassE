""" 
    Basic analysis of SES room requests data.
    Assumes data comes from the excel prototype format
"""

import readData
import courseCalculator as cc
from sesClasses import TimeSlot as TS
from time import strptime

import numpy as np
import matplotlib.pyplot as plt

#VG Change this to take command line arguments
def main():
    """Analyze requests and output to tab-delimited txt file."""
    rooms = readData.importRoomInventory("./F10_DataFiles/roomInventory.csv")
    courses = readData.importCourses("./F10_DataFiles/courseRequests.csv", rooms)    
    courses = readData.addAssignments(courses, rooms, "./F10_DataFiles/Assignments.csv")

    #preferences types
    

    #Dept
    results = cc.countTypes(courses, lambda c: c.dept)
    plotTypeCount(results)


def outputTypeCount(f_out, results):
    for k,v in results.items():
        f_out.write("%s: \t %d \n" % (k,v) )
    f_out.write("\n")

def plotTypeCount(results):
    ind = np.arange(len(results))  # the x locations for the groups
    
    width = 0.1       # the width of the bars
    
    rects1 = plt.bar(ind, results.values(), width,
                    color='blue')

    plt.ylabel('No. of Courses')
    plt.title('Boo Yah')
    plt.xticks(ind + width * 0.5, results.keys() )
    plt.show()
    print results.keys()
    
            
def overviewStats(courses, rooms, f_out):
    """Compute overview stats and write to file"""
    f_out.write("Num Courses: \t %d \n \n" % len(courses))

    #Core
    results = cc.countTypes(courses, lambda c: c.isCore)
    f_out.write("In Core:\n")
    outputTypeCount(f_out, results)
    
#    plotTypeCount(results)

    #Dept
    results = cc.countTypes(courses, lambda c: c.dept)
    f_out.write("Depts: \n")
    outputTypeCount(f_out, results)

    #No. Meetings per Week
    results = cc.countTypes(courses, lambda x: len(x.timePrefs[0].days))
    f_out.write("Meetings Per Week: \n")
    outputTypeCount(f_out, results)
    
    #Team Teaching
    results = cc.countTypes(courses, lambda c: c.instructor.name.count(","))
    f_out.write("Team Teaching: \n")
    outputTypeCount(f_out, results)
    
    #Bldg Breakdown
    courses_with_rooms = dict(filter(lambda (s, c): len(c.roomPrefs), courses.items()))
    results = cc.countTypes(courses_with_rooms, lambda c: c.roomPrefs[0].bldg)
    f_out.write("Bldg Breakdown: \n")
    outputTypeCount(f_out, results)

    #Room Distribution for E62
    courses_e62 = filter(lambda (k,v): "E62" == v.roomPrefs[0].bldg, courses_with_rooms.items())
    courses_e62 = dict(courses_e62)
    results = cc.countTypes(courses_e62, lambda c: c.roomPrefs[0].roomNum)
    f_out.write("E62 Breakdown: \n")
    outputTypeCount(f_out, results)

    #Room Distribution for E51
    courses_e51 = filter(lambda (k,v): "E51" == v.roomPrefs[0].bldg, courses_with_rooms.items())
    courses_e51 = dict(courses_e51)
    results = cc.countTypes(courses_e51, lambda c: c.roomPrefs[0].roomNum)
    f_out.write("E51 Breakdown: \n")
    outputTypeCount(f_out, results)

    #Heat Maps for requests
    time_grid = ["8:30 AM", "9:00 AM", "9:30 AM", "10:00 AM", "10:30 AM", 
                "11:00 AM", "11:30 AM", "12:00 PM","12:30 pm", "1:00 pm", 
                "1:30 pm", "2:00 PM", "2:30 PM", "3:00 PM", "3:30 PM", 
                "4:00 PM", "4:30 PM", "5:00 PM", "5:30 PM", "6:00 PM", 
                "6:30 PM", "7:00 PM", "7:30 PM", "8:00 PM"]

    #Overall
    course_times = [course.timePrefs[0] for (s, course) in courses.items() 
                                            if course.timePrefs[0]]
    f_out.write("Overall Heat Map \n")
    results = cc.createHeatMap(course_times, time_grid)
    outputHeatMap(f_out, results, time_grid)

    #E62
    course_times = [course.timePrefs[0] for (s, course) in courses_e62.items() 
                                            if course.timePrefs[0]]
    f_out.write("E62 Heat Map \n")
    results = cc.createHeatMap(course_times, time_grid)
    outputHeatMap(f_out, results, time_grid)
    
    #E51
    course_times = [course.timePrefs[0] for (s, course) in courses_e51.items() 
                                            if course.timePrefs[0]]
    f_out.write("E51 Heat Map \n")
    results = cc.createHeatMap(course_times, time_grid)
    outputHeatMap(f_out, results, time_grid)

    #Heat Maps for assignment
    #Overall
    course_times = [course.assignedTime for (s, course) in courses.items() 
                                            if course.assignedTime]
    f_out.write("Overall Heat Map \n")
    results = cc.createHeatMap(course_times, time_grid)
    outputHeatMap(f_out, results, time_grid)
    
    #E62
    course_times = [course.assignedTime for (s, course) in courses_e62.items() 
                                            if course.assignedTime]
    f_out.write("E62 Heat Map \n")
    results = cc.createHeatMap(course_times, time_grid)
    outputHeatMap(f_out, results, time_grid)

    #E51
    course_times = [course.assignedTime for (s, course) in courses_e51.items() 
                                            if course.assignedTime]
    f_out.write("E51 Heat Map \n")
    results = cc.createHeatMap(course_times, time_grid)
    outputHeatMap(f_out, results, time_grid)

    #Excess capacity
    e_caps = []
    for (sName, course) in courses.items():
        if course.assignedRoom:
            e = course.assignedRoom.capacity - course.enrollment
            e /= float(course.assignedRoom.capacity)
            e_caps.append((sName, course, e))
    
#     f_out.write("Excess Capacity: \n")
#     f_out.write("Avg: \t %f \n" % (sum([e for (s,c,e) in e_caps])/len(e_caps) ))
#     f_out.write("Num Overbooked: \t %d \n" % sum([1 for (s,c,e) in e_caps 
#                                                         if e <= 0]))
#     
#     #Number First Choices
#     courses_with_rooms_assignments = filter(
#             lambda (s,c): (c.assignedRoom is not None) & bool(c.roomPrefs), 
#             courses.items() )
#     courses_with_rooms_assignments = dict(courses_with_rooms_assignments)
#     num_first_rooms = sum([ 1 for course in courses_with_rooms_assignments.values()
#             if course.assignedRoom == course.roomPrefs[0] ]) 
#     
#     courses_with_time_assignments = filter(
#             lambda (s,c): (c.assignedTime is not None) & bool(c.timePrefs), 
#             courses.items() )
#     courses_with_time_assignments = dict(courses_with_time_assignments)
#     num_first_times = sum([1 for course in courses_with_time_assignments.values()
#             if course.assignedTime == course.timePrefs[0] ] ) 
#         
#     f_out.write("\nFirst Choices: \n")
#     f_out.write("Rooms: \t %d \t %d \n" %  (num_first_rooms, 
#                                             len(courses_with_rooms_assignments)))
#     f_out.write("Times: \t %d \t %d \n" %  (num_first_times, 
#                                             len(courses_with_time_assignments)))
# 
#     #How many rooms are "off-cycle?"
#     start_cycle = ("8:30 AM", "10:20 AM", "11:30 AM", "1:00 PM", "2:30 PM")
#     start_cycle = map(lambda s: strptime(s, "%I:%M %p"), start_cycle)
#     num, tot = 0, 0
#     for course in courses_with_time_assignments.values():
#         if (course.assignedRoom.isInBldg("E62") and not "REC" in course.section):
#             tot += 1
#             if course.assignedTime.startTime in start_cycle:
#                 num += 1
#             else:
#                 pass
#                 #print course.title, course.section, course.assignedTime
#                 
#     print "Num Start Cycle %d \t %d" % (num, 
#                                         tot)
# 
# 
#     #How many courses are overbooked, non recitation
#     tot = 0
#     for course in courses_with_rooms_assignments.values():
#         if ("REC" not in course.section and 
#                 course.enrollment > course.assignedRoom.capacity ):
#             ecap = (course.assignedRoom.capacity - course.enrollment)/float(
#                             course.assignedRoom.capacity)
#             print course.title, ecap
#             tot += 1
#     print tot


if __name__ == '__main__':
  main()
