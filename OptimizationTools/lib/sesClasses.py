""" 
Contains the basic objects for the SES Scheduler.
Room
TimeSlot
Instructor
Course
Course Listing
"""
import datetime
from uuid import uuid4 as uid
from sys import __stdout__

from wx.lib.pubsub import Publisher as pub

class SESError(Exception):
    """A custom exception class.  These exceptions are deemed
    uncorecoverable, and must be addressed by the user."""
    def __init(*args, **kwargs):
        Exception.__init__(*args, **kwargs)

def uniquify(items):
    """removes duplicates, preserves order"""
    seen, out = {}, []
    for i in items:
        if str(i) not in seen:
            seen[str(i)] = 0.
            out.append(i)
    return out        
        
class Room:
    """A room in a bldg.
    Attributes:
        bldg
        roomNum
        capacity
        AV - list of av facilities
    """
    MAX_SIZE = 200

    @staticmethod
    def isValidRoomName(sName):
        """Check Valid room String"""
        if (sName.count("-") <> 1 or
                len(sName.strip().split("-")) <> 2):
            return False
        else:
            return True

    def __init__(self, sName, capacity, AV_equipment = []):
        if not(Room.isValidRoomName(sName)):
            raise SESError("Room %s not recognized." % sName)

        sName = sName.strip().split("-")
        sName = map(lambda s: s.strip().upper(), sName)
        self.bldg, self.roomNum = sName 

        if int(capacity) <= 0:
            raise SESError("Room %s has nonpositive capcity" % self)
        self.capacity = int(capacity) 

        try:
            self.AV = map( lambda s: s.strip().upper(), AV_equipment)
        except Exception:
            raise SESError("AV List for Room %s must be \
                             specified as list of strings" % self )         

    def __eq__(self, other):
        return self.__str__() == other.__str__()
    
    def __ne__(self, other):
        return self.__str__() <> other.__str__()

    def __str__(self):
        """Provide room string in 'E51-31' format"""
        return self.bldg + "-" + self.roomNum

    def __hash__(self):
        return hash(self.__str__())

    def isInBldg(self, bldg2):
        """Test if room is in given building."""
        return self.bldg == bldg2.strip().upper()
        
    def getBldg(self):
        return self.bldg
    
    def hasAV(self, items):
        """Tests if room has this AV item."""
        if not isinstance(items, list):
            items = [items]
        items = [item.strip().upper() for item in items]
        return set(items).issubset(set(self.AV))

    def sameFloor(self, rm2):
        """Tests if rm2 is on same floor.  Assumes labels in form E52-35."""
        if self.isInBldg(rm2.getBldg()):
            return self.roomNum[0] == rm2.roomNum[0]
        else:
            return False

#---------------------------------------------

class Half:
    """Simple Enum Type to capture the types of semesters"""
    halfSemesters = ["H1", "H2"]
    fullSemesters = ["F", ""]
    def __init__(self, s):
        s = s.strip().upper()
        if s in Half.halfSemesters:
            self.half = s
        elif s in Half.fullSemesters:
            self.half = "F"
        else:
            msg = ("Unrecognized half-semester type %s."  % s +
                    "Must be one of 'H1', 'H2', or 'F' ") 
            raise SESError(msg)

    def isFull(self):
#        return self.half in self.fullSemesters
        return self.half in ["F", ""]

    def __str__(self):
        return self.half

    def __eq__(self, other):
        return self.half == other.half
    
    def __hash__(self):
        return hash(self.half)

    def overlap(self, other):
        if self.isFull() or other.isFull():
            return True
        else:
            return self.half == other.half

#---------------------------------------------

class TimeSlot:
    """Primitive TimeSlot Object
    Class Attributes
    daysOfWeek list of "M", "T", etc.
    
    Attributes
    half as instance of Half
    days - list of 
    startTime - stored as datetime.datetime object
    endTime - stored as a datetime.datetime object

    When times specified as strings, should be as '10:30 AM'
    """    
    daysOfWeek = ["M", "T", "W", "Th", "F"]
    
    @staticmethod
    def str2time(s):
        """returns a datetime objct from a 10:30 AM string"""
        return datetime.datetime.strptime(s.strip(), "%I:%M %p")

    @staticmethod
    def time2str(dt):
        """returns a 10:30 am string from a datetime object"""
        return dt.strftime("%I:%M %p")

    def __init__(self, half, dayString, startTime, endTime):
        """Create a time slot.  
        dayString whitespace separated like 'M W F'.
        startTime and endTime strings '10:30 AM' or datetime.time
        """
        if isinstance(half, str):
            half = Half(half)
        self.half = half
        
        self.days = dayString.split()
        if not self.days:
            raise SESError("No days specified for Timeslot.")
            
        for d in self.days:
            if not(d in TimeSlot.daysOfWeek):
                msg = ("Unrecognized day type %s. Must be one of " % d + 
                      ", ".join(TimeSlot.daysOfWeek))
                raise SESError(msg)
            
        if isinstance(startTime, str):
            self.startTime = self.str2time(startTime)
        else:
            self.startTime = startTime
        if isinstance(endTime, str):
            self.endTime = self.str2time(endTime)
        else:
            self.endTime = endTime

        assert(isinstance(self.startTime, datetime.datetime))
        assert(isinstance(self.endTime, datetime.datetime))
        if self.startTime >= self.endTime:
            raise SESError("Start Time after End Time: %s %s" % (startTime, endTime) )

    def overlap(self, timeSlot2):
        """Test if two time slots overlap.
            Logic presumes that classes run from [startTime, endTime) """
        if (self.endTime <= timeSlot2.startTime or
           timeSlot2.endTime <= self.startTime):
           return False
        elif not(set(self.days) & set(timeSlot2.days)): #check days
            return False
        elif not self.half.overlap(timeSlot2.half):
            return False
        else:
            return True
            
    #Try to deprecate this
    def meetsDuring(self, sTime):
        """Test if class meets during given time specified 
        as datetime.datetime or string '10:20 AM'"""
        if isinstance(sTime, str):
            sTime = self.str2time(sTime)
        return self.startTime <= sTime < self.endTime
        
    def meetsDuring2(self, half, day, sTime):
        """Test if time slot overlaps given instant"""
        t = self.str2time(sTime)
        five_min = datetime.timedelta(minutes=5)
        t_p = t + five_min
        return self.overlap(TimeSlot(half, day, sTime, t_p))

    def meetingsPerWk(self):
        """Returns the number of meetings per week"""
        return len(self.days)
    
    def sessionLength(self):
        """Return length of session as a timedelta"""
        return self.endTime - self.startTime

    def isB2B(self, ts):
        """Is ts a back2back slot?  Ignores semester info"""
        if not set(self.days).issubset(ts.days) and not set(self.days).issuperset(ts.days):
            return False

        five_min = datetime.timedelta(minutes=5)
        
        #self starts just after ts
        if self.startTime >= ts.endTime and (self.startTime - ts.endTime) <= five_min:
            return True
        
        #ts starts just after self
        if ts.startTime >= self.endTime and (ts.startTime - self.endTime) <= five_min:
            return True
        
        #Have to do an oddity to account for lunch
        if ((self.str2time("11:30 AM") <= self.endTime <= self.str2time("1:00 PM")) and
            (self.endTime <= ts.startTime <= self.str2time("1:00 PM")) ):
            return True

        if ((self.str2time("11:30 AM") <= ts.endTime <= self.str2time("1:00 PM")) and
            (ts.endTime <= self.startTime <= self.str2time("1:00 PM")) ):
            return True
            
        return False        

    def __str__(self):
        sDays = " ".join(self.days)
        return "%s %s %s %s " % (self.half, sDays, 
                                 self.time2str(self.startTime), 
                                 self.time2str(self.endTime))
                                
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
        
    def __hash__(self):
        return hash(self.__str__())
                
#---------------------------------------------

class Instructor:
    """Encapsulates Prof Info.  
    Teams should be entered under a specific instructor.
    We assume no "blanks" on the outside.
    
    Attributes:
    name - stored as upper case, used as identifier
    """
    def __init__(self, instructorName):
        assert isinstance(instructorName, str)
        if instructorName == "":
            #use a uuid
            instructorName = str(uid())
            
        self.name = instructorName.strip().upper()
    
    def __str__(self):
        return str(self.name)

    def __eq__(self, other):
        return self.name == other.name
    
    def __ne__(self, other):
        return self.name <> other.name

    #Assumes unique names for instructors
    def __hash__(self):
        return hash(self.name)

#---------------------------------------------

class Course:
    """ Single course.  
    Contains a fair amount of logic and functionality.  
    Assumes that the triplet "number, section, classtype" is unique.

    Attributes:
        number
        dept
        enrollment
        instructor  - instance
        section - an ocean letter (A, B, C)        
        classtype - e.g. recitation, lecture, lab
        title
        av_requirements 
        respectTime - boolean
        respectRoom - boolean
        roomPrefs -  
        timePrefs - 
        assignedRoom - room Instance or None if not yet known
        assignedTime - timeSlot Instance or None if not yet known
        extraInstructors - 
    """
    #Move this to a config file.  
    SOFT_CAPACITY= .1
    MAX_ECAP = .5

    def __init__(self, courseNumber, dept, enrollment, instructor,
                    firstTimePref, respectTime = False, 
                    section="", classtype = "LEC", title ="", 
                    av_requirements = []):
        """ Create a Course
        Assumes that 
            courseNumber + section + classtype 
        is a unique identifier.
        
        args
            courseNumber - e.g. 15.051
            dept - e.g. Economics
            enrollment - e.g. 65 (must be positive)
            instructor - an Instructor instance
            firstTimePref - preferred TimeSlot.  Determines admissible times
            
        keywords args:
            section - e.g. "A, B, C" or "A, A"
            classtype = "rec", "lab", etc.
            title = "DATA, MODELS AND DECISIONS"
            av_requirements - ["OVERHEAD", "COMPUTER", "RECORDING"]
            respectTime - boolean
        """
        assert(isinstance(enrollment, int))
        assert(isinstance(respectTime, bool))
        assert(isinstance(instructor, Instructor))
        assert(isinstance(firstTimePref, TimeSlot))

        if enrollment <= 0:
            raise SESError("Enrollment for course %s must be positive" 
                % courseNumber)

        self.number, self.dept, self.enrollment = (str(courseNumber).strip(), 
                dept.strip().upper(), enrollment)
        self.section, self.title, self.respectRoom, self.respectTime = ( 
                section.strip().upper(), title.strip(), False, respectTime )
        self.classtype = classtype.strip().upper()

        is_valid_type = False
        for type in ("LEC", "REC", "BREAKOUT"):
            if type in self.classtype:
                is_valid_type = True

        if not is_valid_type:
            raise SESError(
                "Classtype for course %s must be one of 'LEC', 'REC', 'BREAKOUT'" % 
                self )
        
        self.instructor, self.extraInstructors = instructor, []
        self.roomPrefs, self.timePrefs = [], [firstTimePref]
        self.assignedRoom, self.assignedTime = None, None
        self.av_requirements = map(lambda s : s.strip().upper(), 
                                    av_requirements)

        self.pref_days = [firstTimePref.days]

    def __str__(self):
        """Return the course number + section + section"""
        return " ".join([self.number, self.section, self.classtype])

    def __eq__(self, other):
        return str(self) == str(other)
    
    def __ne__(self, other):
        return str(self) <> str(other)

    def addExtraInstructors(self, instructors):
        """Add additional instructors to the course.  For team teaching"""
        self.extraInstructors = uniquify([self.instructor] + instructors)
        self.extraInstructors = self.extraInstructors[1:]

        #check for blanks
        if reduce(lambda has_blank, prof: has_blank or not bool(prof), 
                  self.extraInstructors, False):
            raise SESError("An additional instructor for course %s has no name" % self)

    def isSame(self, num, sec, classtype):
        """Test equality"""
        if not classtype.strip():
            classtype = "LEC"
        return (self.number == num.strip().upper() and 
                self.section == sec.strip().upper() and
                self.classtype == classtype.strip().upper())

    def getInstructors(self):
        return [self.instructor] + self.extraInstructors

    def isViableTime(self, ts):
        """Check if TimeSlot is viable"""
        time1 = self.timePrefs[0]
        assert(isinstance(ts, TimeSlot))
        return (ts.half == time1.half and
                ts.meetingsPerWk() == time1.meetingsPerWk() and
                ts.sessionLength() == time1.sessionLength() )
        
    def addTimePrefs(self, timePrefs):
        """timePrefs is an interable collection of timeSlots.  
        Order determines pref.  Appends to first pref.
        Must be consistent to first in terms of half, No. Meetings/Wk, Hour length"""
        #only want unique elements, excluding the one already set
        timePrefs = uniquify([self.timePrefs[0]] + timePrefs)
        timePrefs, self.timePrefs = timePrefs[1:], self.timePrefs[:1]
        self.pref_days = self.pref_days[:1]

        if self.respectTime and timePrefs:
            pub.sendMessage("warning", 
                    "Attempt to addTimePrefs to %s after specifying respectTime" % self)

        for ts in timePrefs:
            assert(isinstance(ts, TimeSlot))
            if not self.isViableTime(ts):
                pub.sendMessage("warning", 
                        "Time Slot %s is not viable for course %s" % (ts, self) )

            self.timePrefs.append(ts)
            self.pref_days.append(ts.days)

        self.pref_days = uniquify(self.pref_days)

    def isViableRoom(self, room):
        """Check if room is viable for course"""
        if not room.hasAV(self.av_requirements):
            return False
        
        if self.hasHardCap():
            return room.capacity >= self.enrollment
        else:
            return self.enrollment <= (1 + self.SOFT_CAPACITY) * room.capacity
            
    def hasHardCap(self):
        """Determines if needs hard capcaity constraints.
            section_type is one of "REC", "LEC" etc.
        """
        return not self.isRec()

    def isRec(self):
        """True if we should not conflict with some partnering lecture"""
        return "REC" in self.classtype

    def isBreakout(self):
        """True if we must be simultaneous to some partnering lecture"""
        return "BREAKOUT" in self.classtype

    def isLec(self):
        return "LEC" in self.classtype

    def addRoomPrefs(self, roomPrefs, respectRoom):
        """roomPrefs is an iterable collection of rooms. 
        Clears current prefs before adding.  
        Order determines preferences.
        Issues warning for inviable preferences"""
        if respectRoom and not roomPrefs:
            raise SESError("Course %s specified respectRoom but not given prefs"
                            % self )
                            
        self.respectRoom, self.roomPrefs = respectRoom, []
        roomPrefs = uniquify(roomPrefs)

        for r in roomPrefs:
            assert(isinstance(r, Room))
            #allow them to specify inviable rooms, but issue warning
            self.roomPrefs.append(r)
            if not self.isViableRoom(r):
                pub.sendMessage("warning", 
                                "Room preference %s is inviable for course %s" % (r, self))

    def addAssignment(self, r, ts, testViable=True):
        """add the asigned room and time for this course."""
        assert(isinstance(r, Room))
        assert(isinstance(ts, TimeSlot))
        assert(not testViable)

        if not self.isViableRoom(r):
            pub.sendMessage("warning", "Room %s is inviable for course %s" % (r, self))
        
        if not self.isViableTime(ts):
            pub.sendMessage("warning", "Assigned Time %s is inviable for course %s" % (ts, self))

        self.assignedRoom, self.assignedTime = r, ts
        return self.isViableRoom(r) and self.isViableTime(ts)
        
    def isDept(self, dept):
        """Test if in this dept"""
        return self.dept == dept.strip().upper()

    def getDept(self):
        return self.dept
        
    def gotRoomPref(self):
        """Return which preference (first second) was assigned. 0 means did not get pref"""
        idx = [ix + 1 for (ix, r) in enumerate(self.roomPrefs) 
                if r == self.assignedRoom]
        if len(idx) == 1:
            return idx[0]
        elif len(idx) == 0:
            return 0
        else:
            #suggests two preferences are identical for a room
            raise SESError("Unreachable.  Course %s has duplicate \
            room preferences preferences" % self)

    def gotTimePref(self):
        """Return which preference (first second) was assigned. 0 means did not get pref"""
        idx = [ix + 1 for (ix, ts) in enumerate(self.timePrefs)
                if self.assignedTime == ts]
        if len(idx) == 1:
            return idx[0]
        elif len(idx) == 0:
            return 0
        else:
            #suggests two preferences are identical for a room
            raise SESError("Unreachable.  Course %s has duplicate \
            time preferences preferences" % self)

    def isFixedRoom(self):
        return self.respectRoom
    
    def isFixedTime(self):
        return self.respectTime

    def isPreferredDays(self, ts):
        """Does the timeslot use preferred times only"""
        return ts.days in self.pref_days

