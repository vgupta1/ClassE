""" 
Main Calculator for ClassE
"""
import sesClasses as ses
import config
import readData
from helpers import e_cap
import csv
from numpy import average, array
from sys import __stdout__ #default logging location  
import optimizer as opt

#for the message pasing
#must use old style for now because old version of wxpython?
from wx.lib.pubsub import Publisher as pub

__version__ = 4

def countTypes(alist, f):
    """ Iterate through alist and apply f.  Create a dictionary
        indexed by output values of f with tallies of how many found."""
    results = {}
    for item in alist:
        k = f(item)
        if k in results:
            results[k] +=1
        else:
            results[k] = 1
            
    return results

def getPrefScore(courses, weights):
    """Get the list of scores for rooms and times"""
    room_scores, time_scores = [], []
    for c in courses:
        room_pref, time_pref = c.gotRoomPref(), c.gotTimePref()
        if room_pref:
            room_scores.append( weights[room_pref - 1])
        else:
            room_scores.append(0)
    
        if time_pref:
            time_scores.append(weights[time_pref - 1 ])
        else:
            time_scores.append(0)

    #rescale these so they are on a scale of unity
    max_weight = float(max(weights))
    if max_weight == 0:
        max_weight = 1.
        
    room_scores = [r / max_weight for r in room_scores]
    time_scores = [t / max_weight for t in time_scores]

    return room_scores, time_scores
            
def createHeatMap(course_times, time_grid, half):
    """Compute the number of classes occuring simultaneously
    args
    course_times - list of timeslot objects
    time_grid - List of Strings "10:20 am"

    output
    key - dayofWeek
    val = list of NumClasses.  same length as time_grid 
    """
    results = {}
    for day in ses.TimeSlot.daysOfWeek:
        num_at_time = []
        for sTime in time_grid:
            f = lambda c_time: c_time.meetsDuring2(half, day, sTime)
            num_at_time.append(len(filter(f, course_times)))            
        results[day] = num_at_time

    return results        

def outputHeatMap(results, time_grid, f_out = __stdout__):
    f_out.write("\t")
    for t in time_grid:
        f_out.write("%s \t" % t)
    f_out.write("\n")

    for day in ses.TimeSlot.daysOfWeek:
        f_out.write("%s \t" % day)
        for num in results[day]:
            f_out.write(" %d \t" % num)
        f_out.write("\n")
    f_out.write("\n")



class SESModel:
    """Wrapper for the optimization and analysis routines.
    Focus is on publishing messages via pubsub for GUI hookins
    Warnings are published under topic "warning"
    Errors are thrown as SESErrors
    """
    def __init__(self, quiet=False):
        """Create a new instance."""
        self.optimizer, self.isBuilt = None, False
        self.courses_filt, self.courses, self.roomInventory = None, None, None
        self.prefWeights = [1, 1, 1]
        self.eCapWeight, self.congWeight = 1, 1
        self.quiet = quiet

    #-------------Creating Assignments
    def setData(self, courses_path, rooms_path, no_conflicts_path, b2b_path):
        """Populate the optimizer"""
        self.isBuilt = False
        try:
            self.rooms = readData.importRoomInventory(rooms_path)
            no_conflicts = readData.importNoConflictGroups(no_conflicts_path)
            self.courses = readData.importCourses(courses_path, self.rooms)
            b2b_pairs = readData.importB2BPairs(b2b_path, self.courses)

            self.optimizer = opt.Optimizer(self.courses, 
                    self.rooms, 
                    config.Options(), 
                    no_conflicts, 
                    quiet=self.quiet, 
                    b2b_pairs = b2b_pairs)

        except ses.SESError as e:
            print e
            pub.sendMessage("status_bar.error", str(e))
        except Exception as e:
            print e
            pub.sendMessage("status_bar.error", str(e))

        else:        
            self.resetCourses()
            pub.sendMessage("data_loaded")

    def setWeights(self, scoreWeights, prefWeight, 
                    eCapWeight, congWeight, deptFairness, b2bWeight):
        self.scoreWeights = scoreWeights
        self.eCapWeight, self.congWeight, self.deptFairness = eCapWeight, congWeight, deptFairness
        self.prefWeight = prefWeight
        self.b2bWeight = b2bWeight

    def getScoreWeights(self):
        return self.scoreWeights

    def addAssignments(self, path):
        """Add assignments to the courses"""
        try:
            readData.addAssignments(self.optimizer.getCourses(), 
                                    self.optimizer.getRoomInventory(), 
                                    path)

            pub.sendMessage("update_weights")
    
            #throw an error if not all asignments present.
            for c in self.optimizer.getCourses():
                if c.assignedRoom is None or c.assignedTime is None:
                    #raise an error
                    raise ses.SESError("Course %s does not have an assignment." % c)
        except ses.SESError as e:
            print e
            pub.sendMessage("status_bar.error", str(e))

        pub.sendMessage("assignments_calced")

    def optimize(self):
        """Compute Assignments by Optimization"""
        pub.sendMessage("update_weights")
        try:
            if not self.isBuilt:
                pub.sendMessage("status_bar", "Building optimization...")
                self.optimizer.build()
                self.isBuilt = True
        
            pub.sendMessage("status_bar", "Running optimization...")
            self.optimizer.updateObjFcnAndSolve(self.scoreWeights, self.prefWeight,
                    self.eCapWeight, self.congWeight, self.deptFairness, self.b2bWeight)
        except ses.SESError as e:
            pub.sendMessage("status_bar.error", str(e))
        except Exception as e:
            pub.sendMessage("status_bar.error", str(e))
        else:
            pub.sendMessage("status_bar", "Optimization completed")
            self.courses = self.optimizer.retrieveAssignment()
            pub.sendMessage("assignments_calced")


    def exportAssignments(self, path):
        out = csv.writer(open(path, 'wb'), quoting=csv.QUOTE_MINIMAL)
        out.writerow(["Course", "Section", "classtype", "Title", 
                "Half", "Days", "StartTime", "EndTime", "Room", "IsFixedTime", "IsFixedRoom", 
                "Time Pref", "Room Pref"])
        for c in self.courses:
            t = c.assignedTime
            r = c.assignedRoom
            out.writerow([c.number, c.section, c.classtype, c.title, t.half, " ".join(t.days), 
                    t.time2str(t.startTime), t.time2str(t.endTime), r, 
                    c.isFixedTime(), c.isFixedRoom(), c.gotTimePref(), c.gotRoomPref()])

    def exportToGrid(self, path):
        out = csv.writer(open(path, 'wb'), quoting=csv.QUOTE_MINIMAL)
        
        #compute day of week_grid, time_grid and room_grid        
        half_day_grid = [(h, d) for h in ses.Half.halfSemesters for d in ses.TimeSlot.daysOfWeek]       
        time_grid = config.__time_grid__
        room_col_indx_map = dict(zip(self.rooms, range(len(self.rooms))))

        for h, d in half_day_grid:
            out.writerow([])
            out.writerow([h + " " + d]) 
            out.writerow([""] + self.rooms)
            for t in time_grid:
                line = [""] * len(self.rooms)
                for c in self.courses:
                    if c.assignedTime.meetsDuring2(h, d, t) and c.assignedRoom in self.rooms:
                            col_indx = room_col_indx_map[c.assignedRoom]
                            assert line[col_indx] == ""
                            line[col_indx] = c.__str__()
                        
                out.writerow([t] + line)
            
        
    #-------------Filtering courses lists
    def resetCourses(self):
        self.courses_filt = self.optimizer.getCourses()

    def filterByDept(self, dept):
        self.courses_filt = filter(lambda c: c.isDept(dept), 
                self.courses_filt)
    
    def filterByAssignedBldg(self, bldg):
        f = lambda c: c.assignedRoom.isInBldg(bldg)
        self.courses_filt = filter(f, self.courses_filt)
    
    def filterByIsLec(self, isLec):
        if isLec:
            f = lambda c: c.isLec()
        else:
            f = lambda c: not c.isLec()
            
        self.courses_filt = filter(lambda c: c.isLec(), 
                self.courses_filt)

    #-------------Analyzing courses lists
    def countCourseTypes(self):
        """Count the number/percentage of each of lectures
        other and total types of courses"""
        assert(len(self.courses_filt))
        num_lec = len([1 for c in self.courses_filt if c.isLec() ])
        tot = len(self.courses)
        num_fixedRooms = len([1 for c in self.courses_filt if c.isFixedRoom() ])
        num_fixedTimes = len([1 for c in self.courses_filt if c.isFixedTime() ])

        return [ (num_lec, num_lec/float(tot)), 
                 (tot - num_lec, 1- num_lec/float(tot) ), 
                 (tot, 1.), 
                 (num_fixedRooms, num_fixedRooms / float(tot) ), 
                 (num_fixedTimes, num_fixedTimes / float(tot) )]

    def summarizeExcessCap(self):
        """Compute Avg Excess capacity"""
        f = lambda c: e_cap(c, c.assignedRoom)
        return 100 * sum(map(f, self.courses_filt))/len(self.courses_filt)

    def excessCap(self):
        """Compute excess capacity for every course"""
        f = lambda c: e_cap(c, c.assignedRoom)
        return map(f, self.courses_filt)

    def maxCongestion(self):
        if self.isBuilt:
            return self.optimizer.getMaxCong()
        else:
            #this implementation somewhat slow/problematic
            #but unlikely to be called often
            course_times = [c.assignedTime for c in self.courses_filt]
            resultsH1 = createHeatMap(course_times, config.__time_grid__, ses.Half("H1"))
            maxh1 = max([max(num_class_list) for num_class_list in resultsH1.values()])
                
            resultsH2 = createHeatMap(course_times, config.__time_grid__, ses.Half("H2"))
            maxh2 = max([max(num_class_list) for num_class_list in resultsH2.values()])
            
            return max(maxh1, maxh2)
         
    def prefsStats(self):
        """compute how many courses were assigned choice 1, 2, 3 
        or other"""
        room_dict = countTypes(self.courses_filt, lambda c: c.gotRoomPref() )
        time_dict = countTypes(self.courses_filt, lambda c: c.gotTimePref() )

        #make sure 1, 2, 3, 0 are all in there
        for i in range(4):
            if i not in room_dict:
                room_dict[i] = 0
            if i not in time_dict:
                time_dict[i] = 0

        return room_dict, time_dict

    def getAllDeptPrefScores(self):
        """Return a dictionary {dept:(avg_room_score, avg_time_score)}"""
        all_depts = self.getDepts()
        results = {}
        for dept in all_depts:
            courses_by_dept = filter(lambda c: c.isDept(dept), self.courses_filt)            
            room_scores, time_scores = getPrefScore(courses_by_dept, self.prefWeights)
            results[dept] = average(room_scores), average(time_scores)
 
        return results
 
    def getDepts(self):
        """Return a list of all the departments 
        ordered alphabetically"""
        return self.optimizer.getDepts()

    def getTopBldgs(self, k=-1):
        """Return k most popularly ASSIGNED buildings."""
        f = lambda c: c.assignedRoom.getBldg()
        bldg_dict = countTypes(self.optimizer.getCourses(), f)
        getCount = lambda bldg, count: count
        bldgs = sorted(bldg_dict.items(), key=getCount)
        bldgs = [b for (b,c) in bldgs]

        if k==-1:
            return bldgs
        else:
            return bldgs[:k]

    def genHeatMap(self, half):
        """Generate a heat map numpy array"""
        course_times = [c.assignedTime for c in self.courses_filt]
        results = createHeatMap(course_times, config.__time_grid__, half)

        results_list = [results[k] for k in ses.TimeSlot.daysOfWeek]
        results_np = array(results_list, dtype=float)

#        outputHeatMap(results, config.__time_grid__)        
        
        return results_np, config.__time_grid__, ses.TimeSlot.daysOfWeek 


if __name__ == '__main__':
    room_path = "./F10_DataFiles/roomInventory.csv"
    courses_path = "./F10_DataFiles/courseRequests.csv"
    groups_path = "./F10_DataFiles/NoConflict.csv"

    #Building objects
    sesModel = SESModel()
    sesModel.setData(courses_path, room_path, groups_path)
    sesModel.setWeights([10, 0, 0], 100, 1, 50, 50, 50)
    sesModel.optimize()
    
    sesModel.exportToGrid("temp.csv")
    