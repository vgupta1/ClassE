""" Builds and Solves the SES Optimization Model
    This uses the cplex api"""

import datetime as dt
from time import time
import cplex 

import sesClasses as ses
import helpers

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
                 noConflictGroups=None, enforceFreeTime=True, quiet=False, 
                 b2b_pairs = []):
        """NoConflictGroups is a dict {cnst_name: list[ (number, section, classtype)]"""
        self.course_list, self.roomInventory = course_list, roomInventory
        self.config = configDetails
        self.m = cplex.Cplex()
        self.enforceFreeTime = bool(enforceFreeTime)
        self.noConflictGroups = noConflictGroups
        self.b2b_pairs = b2b_pairs

        if quiet:
            self.m.set_results_stream(None)

        #non-hashable sequence, store as list of tuples (course, room, time, var_indx)
        self.vars = []
        
        #Speed efficiency
        self.vars_by_time = []
        self.iTs = None
        self.hasDeptFairness = False
        self.b2b_vars = []
        self.m.parameters.mip.tolerances.mipgap.set(configDetails.REL_GAP)

        #gen time slots excluding free time for safety
        self.allTimeSlots = helpers.genAllTimeSlots(configDetails, False)

    def genBinaries(self, forbiddenTimes):
        """Create and store the z(s,r,c) and assignment constraint 
           'Every course has 1 room-time'"""
        #add a binary variable for each course, room, time triplet
        vars_by_course = []
        for course in self.course_list:
            course_vars = []
            for r, ts in helpers.allowedRoomTimes(course, self.config, self.roomInventory, 
                                                  forbiddenTimes):
                var = self.m.variables.add(types="B", names=["%s %s %s" % (course, r, ts)])
                var_indx = len(self.vars)
                self.vars.append((course, r, ts, var_indx))
                course_vars.append(var_indx)
            vars_by_course.append(course_vars)

        #this separation is primarily for the gurobi implementation.
        for ix, course in enumerate(self.course_list):
            num_poss = len(vars_by_course[ix])
            self.m.linear_constraints.add(
                    lin_expr = [[vars_by_course[ix], [1.0] * num_poss]], 
                    names = ["1 Room-Time %s" % course], 
                    senses = "E", 
                    rhs = [1.0])
            
    #needs to be tuned.
    def addBack2Back(self, course_pairs):
        """Add variables and constraints for back2back teaching
        Each pair in course_pairs will be encouraged by to be back-2-back"""
        for c1_tuple, c2_tuple in course_pairs:
            #identify all the variables for course1, course2
            c1_vars = filter(lambda (c, r, ts, indx): c.isSame(*c1_tuple), self.vars)
            c2_vars = filter(lambda (c, r, ts, indx): c.isSame(*c2_tuple), self.vars)

            for c1, r1, ts1, indx1 in c1_vars:
                #find the course 2 variables that are neighboring and same room
                c2_neighbors = filter(lambda (c2, r2, ts2, indx2) : r1 == r2 and ts1.isB2B(ts2), 
                                        c2_vars)
                c2_indices = [indx for (c, r, t, indx) in c2_neighbors]

                #add a binary if c1 is back 2 back to c2 and c1 is at t1 in r1
                b2b_indx = self.m.variables.get_num()        
                self.m.variables.add(types="B", names=["Back2Back_%s_%s_%s" % (c1, 
                                                        " ".join(c2_tuple), ts1)])
                self.b2b_vars.append(b2b_indx)

                #Add constraints: z_b2b <= c1_var
                self.m.linear_constraints.add(
                            lin_expr = [cplex.SparsePair([indx1, b2b_indx], [-1., 1.])], 
                            names = ["B2B_typeA %s %s %s" % (c1, ts1, r1)], 
                            senses = "L", 
                            rhs = [0.])
    
                #add Constraints z_b2b <= sum( neighboring c2_vars )
                self.m.linear_constraints.add(
                        lin_expr = [cplex.SparsePair([b2b_indx] + c2_indices, 
                                                    [1.] + [-1.] * len(c2_indices))], 
                        names = ["B2B_typeB %s %s %s %s" % (c1, ts1, r1, " ".join(c2_tuple))], 
                        senses = "L", 
                        rhs = [0.])

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

        for r in room_dict.keys():
            if len(room_dict[r]) > 1:
                self.m.linear_constraints.add(
                        lin_expr = [[room_dict[r], [1.0] * len(room_dict[r])]], 
                        names = ["Time %s: At most 1 course in room %s" % (time_instant, r)], 
                        senses = "L", 
                        rhs = [1.0])
        
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
                self.m.linear_constraints.add(
                        lin_expr = [[dict_profs[prof], [1.0] * len(dict_profs[prof])]], 
                        names = ["Prof %s %s" % (prof, time_instant)], 
                        senses = "L", 
                        rhs = [1.0])

    def lectureRecitationConstraints(self, time_instant):
        """Recitations cannot conflict with each other, or with their lectures"""
        self._updateVarsByTime(time_instant)
        dict_vars_by_course = {}
        courses_with_rec = set()
        for c, r, ts, v in self.vars_by_time:
            sCourse = c.number + c.section
            dict_vars_by_course.setdefault(sCourse, []).append(v)
            
            #Don't add breakout rooms. 
            #These will be constrained to be at same time as lectures anyway, 
            #so will not conflict.  If we add them here though, constraint invalid
            #Since only a few, for efficiency we pop them instead
            if c.isBreakout():
                dict_vars_by_course[sCourse].pop()
            
            if c.isRec():
                courses_with_rec.add(sCourse)

        for sCourse in courses_with_rec:
            num_courses = len(dict_vars_by_course[sCourse])
            self.m.linear_constraints.add(
                lin_expr = [[dict_vars_by_course[sCourse], [1.0] * num_courses]], 
                senses = "L", 
                rhs = [1.0], 
                names = ["Time: %s Lec-Rec %s" % (time_instant, sCourse)] )
                
    def writeLP(self, file_name):
        """Writes underlying LP to a file"""
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
                self.m.linear_constraints.add(
                        lin_expr=[
                            (lec_vars_filt + [v_b], 
                            [1.0] * len(lec_vars_filt) + [-1.0] ) ], 
                        senses = "G", 
                        rhs = [0.0], 
                        names = ["Lec-Breakout %s TimeSlot %s Room %s" % (c_b, ts_b, r_b)]
                        )
 
    def maxCongestionConstraint(self, time_instant):
        """Add a variable and constraint for maxCongestion"""
        self._updateVarsByTime(time_instant)
        vars_only = [v for (c, r, t, v) in self.vars_by_time]
        self.m.linear_constraints.add(
                lin_expr = [[vars_only + [self.maxCongVar], [1.0] * len(vars_only) + [-1.0] ]], 
                senses = "L", 
                rhs = [0.0], 
                names = ["MaxCong %s" % time_instant] )


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
                self.m.linear_constraints.add(
                        lin_expr = [[ vars_only, [1.0] * len(vars_only) ]], 
                        senses = "L", 
                        rhs = [1.0], 
                        names = [("Time: %s" + cnst_name) % time_instant])


    def build(self):
        """Build the optimization model"""
        if self.enforceFreeTime:
            self.genBinaries(self.config.FREE_TIME)
        else:
            self.genBinaries()

        self.addBack2Back(self.b2b_pairs) 

        self.m.variables.add(names=["MaxCong"])
        self.maxCongVar = "MaxCong"

        self.m.variables.add(names=["minDept"])
        self.minDept = "minDept"


        for its in self.allTimeSlots:
            self.atMostOneCourseConstraints(its)
            self.instructorConstraints(its)
            self.lectureRecitationConstraints(its)
            self.breakOutConstraints(its)
            self.maxCongestionConstraint(its)
            self.addAllNoConflictGroups(its)
        
        #don't bother adding fairness constraints yet
        #will add right before optimization
    
    def getMaxCong(self):
        if self.m.solution.get_status() not in  (101, 102):  #fix this
            raise SESError("Optimizer has not been solved yet. Status: %s" 
                    % self.m.solution.get_status())
        return self.m.solution.get_values(self.maxCongVar)      

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
        for c, r, t, indx in self.vars:
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
            const_by_dept[dept][0].append(indx)
            const_by_dept[dept][1].append(coef) 
            
        for dept in self.getDepts():
            vars = const_by_dept[dept][0] + [self.minDept]
            coefs = const_by_dept[dept][1] + [-1.]
            self.m.linear_constraints.add(
                    lin_expr = [[vars, coefs]], 
                    senses = "G", 
                    rhs = [0.0],
                    names = ["DeptFairness_%s" % dept]
                    )

        self.hasDeptFairness = True

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
        if self.hasDeptFairness:
            const_names = ["DeptFairness_%s" % dept for dept in self.getDepts()]
            self.m.linear_constraints.delete(const_names)                        

        self.addDeptFairnessConstraints(score_weights)

        #normalize weights to make comparable
        e_cap_weight /= float(-len(self.course_list))
        pref_weight /= float(len(self.course_list))
        
        #VG better performance if we don't normalize here...
        #b2b_weight /= float(len(self.b2b_vars) + 1 ) #add 1 for safety

        obj_coefs = []
        for c, r, t, var in self.vars:
            #ecap weight
            coef_ecap = helpers.e_cap(c, r) * e_cap_weight

            #preference business
            coef_pref = 0
            for ix in range(len(c.roomPrefs)):
                if c.roomPrefs[ix] == r:
                    coef_pref += score_weights[ix]
            for ix in range(len(c.timePrefs)):
                if c.timePrefs[ix] == t:
                    coef_pref += score_weights[ix]

            #add large penalty if day string doesn't match prefferred
            coef_pref_day = 0.
            if not c.isPreferredDays(t):
                coef_pref_day = -self.config.SOFT_CNST_PENALTY

            obj_coefs.append(coef_pref * pref_weight + coef_ecap + coef_pref_day)
            
        self.m.objective.set_sense(self.m.objective.sense.maximize)

        #add the maxCong
        vars_only = [v for c, r, t, v in self.vars]
        vars_only += [self.maxCongVar]
        obj_coefs += [-congestion_weight]

        #add minDeptFairness
        vars_only += [self.minDept]
        obj_coefs += [dept_fairness]

        #add the bonuses for b2b teaching
        vars_only += self.b2b_vars        
        obj_coefs += [b2b_weight] * len(self.b2b_vars)

        self.m.objective.set_linear(zip(vars_only, obj_coefs))
        self.m.solve()
        
        solution = self.m.solution
        
        #Debug
        #print solution.get_status(), solution.status[solution.get_status()], 

        if solution.get_status() not in  (101, 102):  #fix this
            sol_status = solution.get_status()

            #probably infeasible
            self.m.conflict.refine(self.m.conflict.all_constraints())
            self.m.conflict.write("infeasible_conflict")

            self.m.write("ses.lp")
            print "VG Sol_status", sol_status
            print "VG solution string", solution.status[sol_status]
            raise ses.SESError("Optimizer did not solve. Check ses.lp Status and infeasible_conflict: %s %s" % 
                    (solution.status[sol_status], sol_status) ) 

    def retrieveAssignment(self):
        """Return a course list with the correct assignments"""
        solution = self.m.solution
        if solution.get_status() not in  (101, 102):  #fix this
            raise ses.SESError("Optimizer has not been solved yet. Status: %s" % 
                    solution.get_status())

        for (c, r, t, v) in self.vars:
            if solution.get_values(v) > 1 - 1e-3:
                c.addAssignment(r, t, testViable=False)

        return self.course_list


  
#VG Move this to test suite
import config, sys

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

    optimizer = Optimizer(courses, rooms, config_options)
    optimizer.build()

    print "Object Details"
    print "numVariables \t", len(optimizer.vars)

    optimizer.updateObjFcnAndSolve([10], 1, 1, 1)

#    print "Max Congestion \t %f" % optimizer.maxCongVar.x
    courses = optimizer.retrieveAssignment()
    for c in courses:
        print c, c.assignedRoom, c.assignedTime


if __name__ == '__main__':
    main()
