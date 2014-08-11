"""Harness for SES Optimization

File can be used as a command line harness for the SES Optimization
Should only be used for debugging, not main development
"""
import sesClasses as ses
import courseCalculator as cc
import optimizer as opt
from readData import importCourses, importRoomInventory, importNoConflictGroups, importB2BPairs
import config
import helpers
from numpy import average
import sys

# def getDeptScores(courses, optimizer, prefWeights):
#         all_depts = optimizer.getDepts()
#         results = {}
#         for dept in all_depts:
#             courses_by_dept = filter(lambda c: c.isDept(dept), courses)            
#             room_scores, time_scores = cc.getPrefScore(courses_by_dept, prefWeights)
#             results[dept] = average(room_scores), average(time_scores)
#  
#         return results


def main():
    if len(sys.argv) <> 5:
        print "Inputs -roompath -courses_path - noConflict_path - back2back_path"
        sys.exit()

    #VG Change this to command line arguments
    room_path, courses_path, groups_path, b2b_path = tuple(sys.argv[1:])

    #Building objects
    rooms = importRoomInventory(room_path)
    courses = importCourses(courses_path, rooms)
    config_details = config.Options()
    no_conflicts = importNoConflictGroups(groups_path)
    back_to_back = importB2BPairs(b2b_path, courses)

    #building optimization
    optimizer = opt.Optimizer(courses, rooms, config_details, no_conflicts, quiet=True, 
    b2b_pairs = back_to_back)
    optimizer.build()

    #some optimization details
    print "Rooms \t %d" % len(rooms)
    print "Courses \t %d" % len(courses)
    print "Time Slots \t %d" % len(optimizer.allTimeSlots)

    #solve
    print "------ Solution 1 -------"
    optimizer.updateObjFcnAndSolve([10, 0, 0], 
            pref_weight=1, 
            e_cap_weight=0, 
            congestion_weight=0, 
            dept_fairness=0.0, 
            b2b_weight = 1.0)


    #Debugging
    #optimizer.writeLP("debug_lp.lp")

    print "\n \n Max Cong:\t%d" % optimizer.getMaxCong()
    courses = optimizer.retrieveAssignment()

    courses_with_break = set([c.number + c.section for c in courses if c.isBreakout()] )

    for sCourse in courses_with_break:
        filt = lambda c : c.number + c.section == sCourse
        courses_filt = filter(filt, courses)
        
        for c in courses_filt:
            if c.number + c.section == "15.665A":
                print "%s \t %s \t %s" % (c, c.assignedTime, c.assignedRoom)

    #solve
    print "------ Solution 2 -------"
    optimizer.updateObjFcnAndSolve([10, 5, 1], 
            pref_weight=10, 
            e_cap_weight=1, 
            congestion_weight=1, 
            dept_fairness=5, 
            b2b_weight = 1.0)


#     
#     print "Excess Cap: \t", 
#     f_ecap = lambda c: helpers.e_cap(c, c.assignedRoom)
#     e_caps = map(f_ecap, courses)
#     print 100 * sum(e_caps)/len(e_caps)
# 
#     print "Prefs: \n"
#     print cc.countTypes(courses, lambda c: c.gotRoomPref() )
#     print cc.countTypes(courses, lambda c: c.gotTimePref() )
# 
#     print "Fairness: \n"
#     results = getDeptScores(courses, optimizer, [10, 0, 0])
#     for k in results.keys():
#         print k, sum(results[k])

#    for course in courses:
#        print "%s \t %s \t %s" % (course, course.assignedTime, course.assignedRoom)

#     course_times = [c.assignedTime for c in courses]
#     results = cc.createHeatMap(course_times, time_grid, "H1")
#     cc.outputHeatMap(results, time_grid)
    
    print "\n \n"

#     results = cc.createHeatMap(course_times, time_grid, "H2")
#     cc.outputHeatMap(results, time_grid)

#     courses_no_times = filter(lambda c: not c.gotTimePref(), courses)
#     c0 = courses_no_times[0]
#     
#     print c0
#     ts = c0.timePrefs[0]
#     print "Time Pref %s" % ts
#     for c in courses:
#         if c.timePrefs[0] == ts:
#             print c
# 
#     print "all bad courses"
#     for c in courses_no_times:
#         print c
    

if __name__ == '__main__':
    main()
