""" Builds and Solves the SES Optimization Model"""

import datetime as dt
from time import time
import sesClasses as ses
import helpers
import gurobipy as grb

class Optimizer:
    """Builds and solves scheduling optimization.
    
    Attributes:
        vars - list of tuples (course, room, time, var)
        m - gurobi Model
        maxCongVar - variable indicating the maximum congestion
        course_list
        roomInventory
    """

    def __init__(self, course_list, roomInventory, configDetails, 
                 noConflictGroups=None, enforceFreeTime=True, quiet = False, 
                 b2b_pairs = []):
        """NoConflictGroups is a dict {cnst_name: list[ (number, section, classtype)]"""
        self.course_list, self.roomInventory = course_list, roomInventory
        self.config = configDetails
        self.m = grb.Model("SesModel")
        self.enforceFreeTime = bool(enforceFreeTime)
        self.noConflictGroups = noConflictGroups
        self.b2b_pairs = b2b_pairs
        
        if quiet:
            self.m.params.outputflag = False

        #List of tuples (course, room, time, var)
        self.vars = []

        #List of all fairness constraints
        self.FairnessConstraints = []
        
        #Speed efficiency
        self.vars_by_time = []
        self.iTs = None
        self.m.params.presolve = 1
        self.m.params.mipgap = configDetails.REL_GAP
        self.b2b_vars = []

        #gen time slots excluding free time for safety
        self.allTimeSlots = helpers.genAllTimeSlots(configDetails, False)

    def genBinaries(self, forbiddenTimes):
        """Create and store the z(s,r,c) and assignment constraint 
           'Every course has 1 room-time'"""
        #add a binary variable for each course, room, time triplet
        ##Begin Optimized Code
        vars_by_course = []
        for course in self.course_list:
            course_vars = []
            for r, ts in helpers.allowedRoomTimes(course, self.config, self.roomInventory, 
                                                  forbiddenTimes):
                var = self.m.addVar(vtype=grb.GRB.BINARY, 
                                    name= "c%s %s %s" % (course, r, ts))
                self.vars.append((course, r, ts, var))
                course_vars.append(var)
            vars_by_course.append(course_vars)

        self.m.update()
        for indx, course in enumerate(self.course_list):
            self.m.addConstr(grb.quicksum(vars_by_course[indx]) ==1, "One Room-Time %s" % course )

        ##End optimized code

    #needs to be tuned.
    def addBack2Back(self, course_pairs):
        """Add variables and constraints for back2back teaching
        Each pair in course_pairs will be encouraged by to be back-2-back"""
        for c1_tuple, c2_tuple in course_pairs:
            #identify all the variables for course1, course2
            c1_vars = filter(lambda (c, r, ts, var): c.isSame(*c1_tuple), self.vars)
            c2_vars = filter(lambda (c, r, ts, var): c.isSame(*c2_tuple), self.vars)

            for c1, r1, ts1, var1 in c1_vars:
                #find the course 2 variables that are neighboring and same room
                c2_neighbors = filter(lambda (c2, r2, ts2, var2) : r1 == r2 and ts1.isB2B(ts2), 
                                        c2_vars)
                c2_vars_filt = [var for (c, r, t, var) in c2_neighbors]

                #add a binary if c1 is back 2 back to c2 and c1 is at t1 in r1
                b2b_var = self.m.addVar(vtype = grb.GRB.BINARY, 
                                        name = "Back2Back_%s_%s_%s" % (c1, " ".join(c2_tuple), ts1))
                self.b2b_vars.append(b2b_var)
                self.m.update()
                
                #Add constraints: z_b2b <= c1_var
                self.m.addConstr(b2b_var <= var1, "B2B_typeA %s %s %s" % (c1, ts1, r1)) 
                    
                #add Constraints z_b2b <= sum( neighboring c2_vars )
                self.m.addConstr(b2b_var <= grb.quicksum(c2_vars_filt), 
                                "B2B_typeB %s %s %s %s" % (c1, ts1, r1, " ".join(c2_tuple)))

    def _updateVarsByTime(self, time_slot):
        """Find all variables that overlap given timeslot"""
        #lazy calculation only
        if self.iTs is not None and self.iTs == time_slot:
            return

        #filter out those variables that overlap
        self.iTs = time_slot
        f_overlap = time_slot.overlap
        self.vars_by_time = [(c, r, ts, v) for (c, r, ts, v) in self.vars if f_overlap(ts)]

    #With some cleverness, might add fewer constraints here...
    def atMostOneCourseConstraints(self, time_instant):
        """Add constraint: At Given time_instant, a room has at most one course"""
        self._updateVarsByTime(time_instant)
        room_dict = {}
        for (c, r, ts, v) in self.vars_by_time:
            room_dict.setdefault(r, []).append(v)

#         if not len(room_dict):
#             raise RuntimeError("No Variables overlap with time %s" % time_instant)

        for r in room_dict.keys():
            if len(room_dict[r]) > 1:
                self.m.addConstr(grb.quicksum(room_dict[r]) <= 1, 
                                 "Time %s: At most 1 course in room %s" %
                                 (time_instant, r))
        
    def instructorConstraints(self, time_instant):
        """At given time, at most 1 course per instructor"""
        self._updateVarsByTime(time_instant)
        dict_profs = {}
        for c, r, ts, v in self.vars_by_time:
            profs = c.getInstructors()
            for prof in profs: 
                dict_profs.setdefault(prof, []).append(v)
                
        for prof in dict_profs.keys():
            if len(dict_profs[prof]) > 1:
                self.m.addConstr(grb.quicksum(dict_profs[prof]) <= 1, 
                                 "Prof %s %s" % (prof, time_instant) )

    def lectureRecitationConstraints(self, time_instant):
        """Courses with same number and section cannot conflict"""
        self._updateVarsByTime(time_instant)
        dict_vars_by_course = {}
        courses_with_rec = set()
        for c, r, ts, v in self.vars_by_time:
            sCourse = c.number + c.section
            dict_vars_by_course.setdefault(sCourse, []).append(v)
            if c.isRec():
                courses_with_rec.add(sCourse)

        for sCourse in courses_with_rec:
            self.m.addConstr(grb.quicksum(dict_vars_by_course[sCourse]) <= 1, 
                             "Time: %s Lec-Rec %s" % (time_instant, sCourse))
 
    def writeLP(self, file_name):
        """Writes underlying LP to a file"""
        if not file_name.endswith(".lp"):
            file_name += ".lp"
        self.m.write(file_name)


    #coding relies on fact that not too many breakouts
    def breakOutConstraints(self, time_instant):
        """Breakouts meet simultaneously to Lectures, same floor"""
        self._updateVarsByTime(time_instant)

        #Divide the variables by course name
        #each dict of form {sCourse : (c, r, ts, v)}
        breakouts, lecs = {}, {}
        for c, r, ts, v in self.vars_by_time:
            if c.isRec():
                continue
            
            sCourse = c.number + c.section
            if c.isBreakout():
                breakouts.setdefault(sCourse, []).append((c, r, ts, v))
            else:
                lecs.setdefault(sCourse, []).append((c, r, ts, v))

        for sCourse in breakouts.keys():
            for c_b, r_b, ts_b, v_b in breakouts[sCourse]:
                #find all lectures with same time-block and floor
                if sCourse not in lecs:
                    #if the lecture has a fixed time, it may not occur in this time_instant
                    #checks for whether all breakouts have partners occur earlier
                    lec_vars_filt = []
                else:
                    same_ts_floor = lambda x : (x[2] == ts_b) and (r_b.sameFloor(x[1]))
                    lec_vars_filt = filter(same_ts_floor, lecs[sCourse])
                    lec_vars_filt = [v for (c, r, ts, v) in lec_vars_filt]

                #Constraint: if choose this breakout, must choose one lecture
                self.m.addConstr(v_b <= grb.quicksum(lec_vars_filt), 
                                "Lec-Breakout %s TimeSlot %s Room %s" % (c_b, ts_b, r_b))

    def maxCongestionConstraint(self, time_instant):
        """Add a variable and constraint for maxCongestion"""
        self._updateVarsByTime(time_instant)
        vars_only = [v for (c, r, t, v) in self.vars_by_time]
        self.m.addConstr(grb.quicksum(vars_only) <= self.maxCongVar, 
                         "MaxCong %s" % time_instant)        

    def addAllNoConflictGroups(self, time_instant):
        """Add constraints for each group of classes that cannot conflict."""
        if self.noConflictGroups is None:
            return

        self._updateVarsByTime(time_instant)
        for cnst_name, course_nums in self.noConflictGroups.items():
            #Make list of course names
            names = [" ".join([num, sec, type]) for num, sec, type in course_nums]
            vars_only = [v for (c, r, ts, v) in self.vars_by_time if c.__str__() in names]

            if len(vars_only) > 1:
                self.m.addConstr(grb.quicksum(vars_only) <= 1, 
                                ("Time: %s" + cnst_name) % time_instant)


    def build(self):
        """Build the optimization model"""
        if self.enforceFreeTime:
            self.genBinaries(self.config.FREE_TIME)
        else:
            self.genBinaries()

        self.addBack2Back(self.b2b_pairs)

        self.maxCongVar = self.m.addVar(name="MaxCong")
        self.minDept = self.m.addVar(name="minDep")
        self.m.update()

        for its in self.allTimeSlots:
            self.atMostOneCourseConstraints(its)
            self.instructorConstraints(its)
            self.lectureRecitationConstraints(its)
            self.breakOutConstraints(its)
            self.maxCongestionConstraint(its)
            self.addAllNoConflictGroups(its)
        
        self.m.update()

        #don't bother adding fairness constraints yet
        #will add right before optimization

    def retrieveAssignment(self):
        """Return a course list with the correct assignments"""
        if self.m.status <> grb.GRB.OPTIMAL:
            raise ses.SESError("Optimizer has not been solved yet. Status: %s" % self.m.status)

        #leverage the fact that everything is a pointer
        for (c, r, t, v) in self.vars:
            if v.x > 1 - 1e-3:
                c.addAssignment(r, t, testViable=False)

        return self.course_list

    def getMaxCong(self):
        if self.m.status <> grb.GRB.status.OPTIMAL:
            raise SESError("Optimizer has not been solved yet. Status: %s" 
                    % self.m.status)
        return self.maxCongVar.x      

    #these allow handles on internal data
    def getCourses(self):
        return self.course_list

    #these allow handles on internal data
    def getRoomInventory(self):
        return self.roomInventory

    def getDepts(self):
        """Return a list of all the departments 
        ordered alphabetically"""
        all_depts = [c.dept for c in self.course_list]
        all_depts = list(set(all_depts))
        return sorted(all_depts)

    def addDeptFairnessConstraints(self, choice_weights):
        """maximize the avg_score of the minimal dept"""
        #num courses for each dept
        norm_factors = {}
        for c in self.course_list:
            dept = c.getDept()
            if dept in norm_factors:
                norm_factors[dept] += 1
            else:
                norm_factors[dept] = 1

        #group the variables by department        
        #values in dictionaries are tupes: (var_indx_list, coeffs)
        const_by_dept = {}
        for c, r, t, v in self.vars:
            dept = c.getDept()
            if dept not in const_by_dept:
                const_by_dept[dept] = ([], [])
            
            #preference business
            coef = 0.0
            for ix in range(len(c.roomPrefs)):
                if c.roomPrefs[ix] == r:
                    coef += choice_weights[ix]
            for ix in range(len(c.timePrefs)):
                if c.timePrefs[ix] == t:
                    coef += choice_weights[ix]
        
            coef /= float(norm_factors[dept])

            #VG Change this to a list of tuples, instead of two lists.
            const_by_dept[dept][0].append(v)
            const_by_dept[dept][1].append(coef) 
            
        for dept in self.getDepts():
            t = self.m.addConstr(
                    grb.quicksum([c * v for c, v in zip(const_by_dept[dept][0],
                                                        const_by_dept[dept][1]) ])
                    >= self.minDept,
                    name="DeptFairness_%s" % dept)
            self.FairnessConstraints.append(t)

    def updateObjFcnAndSolve(self, score_weights, pref_weight, e_cap_weight, 
            congestion_weight, dept_fairness, b2b_weight):
        """choiceweights should be in order [1st choice, 2nd choice, etc]"""
        pref_weight = max(pref_weight, self.config.EPS_SAFETY_OVERRIDE)

        #normalize the score weights
        max_weight = float(max(score_weights))
        if max_weight == 0:
            max_weight = 1.
        score_weights = [w/max_weight for w in score_weights]

        #check to see if fairness constraints are already there
        if self.FairnessConstraints:
            [self.m.remove(const) for const in self.FairnessConstraints]

        self.FairnessConstraints = []
        self.addDeptFairnessConstraints(score_weights)

        #Normalize weights to make order unity
        e_cap_weight /= float(-len(self.course_list))
        pref_weight /= float(len(self.course_list))

        obj = grb.LinExpr()
        for c, r, t, var in self.vars:
            obj += helpers.e_cap(c, r) * e_cap_weight * var
        
        #add the preference weights
        for c, r, t, var in self.vars:
            for ix in range(len(c.roomPrefs)):
                if c.roomPrefs[ix] == r:
                    obj += score_weights[ix] * pref_weight * var
            for ix in range(len(c.timePrefs)):
                if c.timePrefs[ix] == t:
                    obj += score_weights[ix] * pref_weight * var
        
            #add large penalty if day string doesn't match prefferred
            if not c.isPreferredDays(t):
                obj -= self.config.SOFT_CNST_PENALTY * var

        #add the maxCong, minDeptFairness
        obj += -congestion_weight * self.maxCongVar
        obj += dept_fairness * self.minDept
        
        #add the bonuses for b2b teaching
        obj += grb.quicksum(b2b_weight * v for v in self.b2b_vars)        


        self.m.setObjective(obj, grb.GRB.MAXIMIZE)
        self.m.optimize()
        
        if self.m.status == grb.GRB.status.INF_OR_UNBD:
            self.m.params.presolve = 0
            self.m.optimize()
    
        if self.m.status == grb.GRB.status.INFEASIBLE:
            self.m.computeIIS()
            self.m.write("infeasible_conflict.ilp")
            raise ses.SESError("Optimization Infeasible.  Check file infeasible_conflict.ilp")
        elif self.m.status <> grb.GRB.status.OPTIMAL:
            self.m.write("ses.lp")
            raise SESError("Optimizer did not solve. Check ses.lp Status: %d" % self.m.status) 

  
#VG Move this to test suite
import config
import sys

def main():
    course1 = ses.Course("15.051", "Economics", 70, ses.Instructor("Arnie"), 
                     ses.TimeSlot("", "M W", "10:00 AM", "11:30 AM"))
    course2 = ses.Course("15.052", "Economics", 50, ses.Instructor("Arnie"), 
                     ses.TimeSlot("H1", "F", "4:00 PM", "7:00 PM"), 
                     av_requirements = ["camera"])
    course3 = ses.Course("15.052", "Economics", 52, ses.Instructor("Dimitris"), 
                     ses.TimeSlot("F", "W", "10:00 AM", "11:00 AM"), 
                     av_requirements = ["camera"], classtype="REC")
    courses = [course1, course2, course3]

    room1 = ses.Room("E52-135", 100, ["projector"])
    room2 = ses.Room("E52-140", 50, ["projector", " camera "])
    rooms = [room1, room2]    


    config_options = config.Options()

    optimizer = Optimizer_(courses, rooms, config_options)
    optimizer.build()
    optimizer.m.update()

    print "Object Details"
    print "numVariables \t", len(optimizer.vars)

    optimizer.m.printStats()    
    optimizer.updateObjFcnAndSolve([10], 0, 0)

    print "Max Congestion \t %f" % optimizer.maxCongVar.x
    courses = optimizer.retrieveAssignment()
    for c in courses:
        print c, c.assignedRoom, c.assignedTime


if __name__ == '__main__':
    main()
