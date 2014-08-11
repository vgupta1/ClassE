""" Contains the Unit tests for the basic objects of SES Scheduler"""

import unittest
from sesClasses import *
import datetime
import helpers, config
from wx.lib.pubsub import Publisher as pub

#simple couple lines for checking when warnings are thrown
global _hasMsg
_hasMsg = False

def updateMsg(msg ):
    global _hasMsg
    _hasMsg = True

def hasMsg():
    global _hasMsg
    if _hasMsg:
        _hasMsg = False
        return True
    else:
        return False

#set up pubsub subscriber to test warnings
pub.subscribe(updateMsg, "warning")


class TestRoom(unittest.TestCase):
    def setUp(self):
        global _hasMsg 
        _hasMsg = False

        self.room = Room("E52-135", 50, ["projector"])
        self.room2 = Room("E52-135", 50, ["projector", " documentCamera "])

    def test_names(self):
        #invalid room names representation
        #Do these in the weird way bc can't figure out how to pass optional
        with self.assertRaises(SESError):
            Room("Foo", 50)

        with self.assertRaises(SESError):
            Room("E52--135", 50)

    def test_capacity(self):
        with self.assertRaises(SESError):
            Room("Foo", -1,)

        with self.assertRaises(SESError):
            Room("E52-135", -1,)
            
    def test_stripping(self):
        #Room specified with a space in rooming
        room1 = Room(" e52 - 136 ", 50) 
        self.assertEqual(room1.__str__(), "E52-136")
        
    def test_equality(self):
        room1 = Room("E52-135", 100, ["projector"]);
        room1b = Room("E52-135", 100, ["projector"]);
        room2 = Room("E51 - 136", 100); 
        
        self.assertTrue(room1 == room1b)
        self.assertTrue(room1 <> room2)
        self.assertFalse(room1 == room2)
        self.assertFalse(room1 <> room1b)
    
    def test_bldg(self):
        self.assertTrue(self.room.isInBldg(" E52 "))
        self.assertFalse(self.room.isInBldg("E62"))

    def test_AV(self):
        av_reqs = "projector"
        self.assertTrue(self.room.hasAV(av_reqs))
        self.assertFalse(self.room.hasAV("documentCamera"))

        av_reqs = ["projector", "documentcamera"]
        self.assertTrue(self.room2.hasAV(av_reqs))
        self.assertTrue(self.room2.hasAV("documentcamera"))
        self.assertTrue(self.room.hasAV([]))

class TestTimeSlots(unittest.TestCase):
    def test_init(self):
        self.assertRaises(SESError, TimeSlot, "H 1", "M W F", 
                          "10:00 AM", "11:30 AM")
        self.assertRaises(SESError, TimeSlot, "Full", "M W F", 
                          "10:00 AM", "11:30 AM")
        self.assertRaises(SESError, TimeSlot, "H1", "MW F", 
                          "10:00 AM", "11:30 AM")
        self.assertRaises(SESError, TimeSlot, "H1", "L W F", 
                          "10:00 AM", "11:30 AM")
        self.assertRaises(SESError, TimeSlot, "H1", "M", 
                          "12:00 PM", "11:30 AM")
        self.assertRaises(SESError, TimeSlot, "H1", "M", 
                          "11:30 AM", "11:30 AM")
        self.assertRaises(SESError, TimeSlot, "F", "m W F", 
                          "10:30 AM", "12:00 PM")
    
    def setUp(self):
        self.time1 = TimeSlot("F", "M W F", "10:30 AM", "12:00 PM")
        self.time2 = TimeSlot("H1", "M", "10:30 AM", "11:00 AM")
        self.time3 = TimeSlot("H2", "M", "10:30 AM", "11:00 AM")
        self.time4 = TimeSlot("H2", "M", "11:00 AM", "12:00 PM")
        self.time5 = TimeSlot("H2", "T", "10:30 AM", "11:00 AM")
        self.time6 = TimeSlot("H2", "M", "2:00 PM", "3:00 pm")


    def test_overlap(self):
        self.assertTrue(self.time1.overlap(self.time2))
        self.assertTrue(self.time1.overlap(self.time3))
        self.assertFalse(self.time2.overlap(self.time3))
        self.assertFalse(self.time3.overlap(self.time4))
        self.assertFalse(self.time4.overlap(self.time5))
        self.assertFalse(self.time4.overlap(self.time6))
        
        
    def test_during(self):
        self.assertTrue(self.time1.meetsDuring("11:00 AM"))
        self.assertFalse(self.time1.meetsDuring("12:00 PM"))
        self.assertFalse(self.time1.meetsDuring("12:01 PM"))

    def test_equality(self):
        time1_copy = TimeSlot("F", "M W F", "10:30 AM", "12:00 PM")
        self.assertTrue(self.time1 == time1_copy)
        self.assertFalse(self.time2 == time1_copy)
        self.assertFalse(self.time1 <> time1_copy)
        self.assertTrue(self.time2 <> time1_copy)

    def test_meetingsPerWk(self):
        self.assertEqual(3, self.time1.meetingsPerWk())
        self.assertEqual(1, self.time2.meetingsPerWk())

    def test_sessionLength(self):
        one_half_hours = datetime.timedelta(hours=1, minutes=30)
        self.assertEqual(one_half_hours, self.time1.sessionLength())        
        self.assertFalse(one_half_hours == self.time2.sessionLength())
        self.assertTrue(self.time2.sessionLength() == 
                        datetime.timedelta(minutes=30))
                        
    def testb2b(self):
        ts1 = TimeSlot("F", "M W F", "10:30 AM", "12:00 PM")
        self.assertTrue(ts1.isB2B(TimeSlot("F", "M W F", "9:00 AM", "10:30 AM")))
        self.assertTrue(ts1.isB2B(TimeSlot("H1", "M W F", "9:00 AM", "10:30 AM")))
        self.assertTrue(ts1.isB2B(TimeSlot("H1", "M", "9:00 AM", "10:30 AM")))
        self.assertTrue(ts1.isB2B(TimeSlot("H1", "M", "12:00 PM", "1:00 PM")))

        #This should pass because of lunch rules
        self.assertTrue(ts1.isB2B(TimeSlot("H1", "M", "1:00 PM", "2:00 PM")))

        self.assertFalse(ts1.isB2B(TimeSlot("F", "M W F", "8:00 AM", "9:30 AM")))
        self.assertFalse(ts1.isB2B(TimeSlot("F", "M W F", "1:30 PM", "2:30 PM")))
        self.assertFalse(ts1.isB2B(TimeSlot("F", "T", "9:00 AM", "10:30 AM")))
        self.assertFalse(ts1.isB2B(TimeSlot("F", "M W F", "8:00 AM", "12:00 PM")))
        self.assertFalse(ts1.isB2B(TimeSlot("F", "M W F", "10:30 AM", "2:00 PM")))

class TestInstructors(unittest.TestCase):
    def test_init(self):
        prof1 = Instructor("A. Barnett")
        prof2 = Instructor("a. barnett")
        prof3 = Instructor("d. bertsimas")
        prof4 = Instructor("")
        prof5 = Instructor("")
        
        self.assertTrue(prof1 == prof2)
        self.assertFalse(prof1 == prof3)
        self.assertFalse(prof1 <> prof2)
        self.assertTrue(prof1 <> prof3)
        self.assertFalse(prof4 == prof5)
        self.assertTrue(prof4 == prof4)

class TestCourse(unittest.TestCase):
    def setUp(self):
        global _hasMsg 
        _hasMsg = False

        #instructors
        self.arnie = Instructor("A. Barnett")
        self.dimitris = Instructor("D. Bertsimas")

        #TimeSlots
        self.time1 = TimeSlot("F", "M W F", "10:30 AM", "12:00 PM")
        self.time2 = TimeSlot("H1", "M", "10:30 AM", "11:00 AM")


        self.course1 = Course("15.051 J ", "Economics", 30, self.arnie, 
                              self.time1, av_requirements=["projector "])

        self.course2 = Course("15.051 J ", "DMD", 30, self.dimitris, 
                              self.time2, av_requirements=["camera "], 
                              section = "A", classtype="Rec", respectTime=True)
    def test_hardCap(self):
        self.assertTrue(self.course1.hasHardCap())
        self.assertFalse(self.course2.hasHardCap())
        
    def test_init(self):
        #zero enrollment
        with self.assertRaises(SESError):
            Course("15.051", "Economics", 0, self.arnie, self.time1)
        
        #tests stripping of certan data
        self.assertTrue(self.course1.dept == "ECONOMICS")
        self.assertTrue(self.course1.number == "15.051 J")
        self.assertTrue(self.course1.av_requirements[0] == "PROJECTOR")
        
    def test_timePrefs(self):
        #Each of these should yield a warning.  
        #Times that mismatches on one field
        self.assertFalse(hasMsg())
        self.course1.addTimePrefs([TimeSlot("H1", "M W F", "10:30 AM", "12:00 PM")])
        self.assertTrue(hasMsg())

        self.assertFalse(hasMsg())
        self.course1.addTimePrefs([TimeSlot("F", "M F", "10:30 AM", "12:00 PM")])
        self.assertTrue(hasMsg())

        self.assertFalse(hasMsg())
        self.course1.addTimePrefs([TimeSlot("F", "M W F", "10:00 AM", "12:00 PM")])
        self.assertTrue(hasMsg())

        #Add timePrefs to a respect time should yield a warming
        self.assertFalse(hasMsg())
        self.course2.addTimePrefs([TimeSlot("H2", "M", "10:30 AM", "11:00 AM")])
        self.assertTrue(hasMsg())

        #Should execute normally
        self.course1.addTimePrefs([TimeSlot("F", "M W F", "12:00 PM", "1:30 PM")])
        self.assertFalse(hasMsg())

    def test_preferred_days(self):
        self.course1.addTimePrefs([TimeSlot("F", "M W F", "12:00 PM", "1:30 PM")])
        self.assertTrue(self.course1.isPreferredDays(TimeSlot("F", "M W F", "8:00 AM", "10:00 AM")))
        self.assertFalse(self.course1.isPreferredDays(TimeSlot("F", "M", "8:00 AM", "10:00 AM")))
        self.assertFalse(self.course1.isPreferredDays(TimeSlot("F", "T Th", "8:00 AM", "10:00 AM")))

        self.course1.addTimePrefs([TimeSlot("F", "T Th", "12:00 PM", "1:30 PM")])
        self.assertTrue(self.course1.isPreferredDays(TimeSlot("F", "M W F", "8:00 AM", "10:00 AM")))
        self.assertTrue(self.course1.isPreferredDays(TimeSlot("F", "T Th", "8:00 AM", "10:00 AM")))      
        
    def test_RoomPrefs(self):
        room1 = Room("E52-135", 100, ["projector"]);
        room1b = Room("E52-136", 20, ["projector"]);
        room2 = Room("E51 - 137", 28, [" camera "]); 
        
        #Can't respect empty list
        self.assertRaises(SESError, self.course1.addRoomPrefs, 
                          [], True)

        #These should all raise warnings
        #Room too small
        self.assertFalse(hasMsg())
        self.course1.addRoomPrefs([room1b], False)
        self.assertTrue(hasMsg())

        #Room doesnt have gear
        self.assertFalse(hasMsg())
        self.course1.addRoomPrefs([room1, room2], False)
        self.assertTrue(hasMsg())

        #should fail hard capacity, and pass soft
        self.assertFalse(hasMsg())
        self.course1.addRoomPrefs([room2], False)
        self.assertTrue(hasMsg())

        self.course2.addRoomPrefs([room2], False)

        #should execute normally
        self.course1.addRoomPrefs([room1], False)
        self.assertFalse(hasMsg())
        self.assertTrue(str(self.course1.roomPrefs[0]) == "E52-135")

    def test_Assignment(self):
        room1 = Room("E52-135", 100, ["projector"]);
        room2 = Room("E51 - 136", 100); 
        time1 = TimeSlot("", "M W F", "10:30 AM", "12:00 PM")
        time2 = TimeSlot("H1", "M", "10:30 AM", "11:00 AM")

        #course 1 requires a projector, but room2 does not have one
        #should raise a warning
        self.assertFalse(hasMsg())
        self.course1.addAssignment(room2, time1, False)
        self.assertTrue(hasMsg())
        
        #a bad time should raise a warning
        self.assertFalse(hasMsg())
        self.course1.addAssignment(room1, time2, False)
        self.assertTrue(hasMsg())

        #should execute normally
        self.course1.addAssignment(room1, time1, False)
        self.assertFalse(hasMsg())
        self.assertTrue(str(self.course1.assignedRoom) == "E52-135")
        self.assertTrue(self.course1.assignedTime == time1)       
        
    def test_instructors(self):
        self.course1.addExtraInstructors([self.dimitris])
        t = self.course1.getInstructors()
        self.assertEqual(t[0], self.arnie)
        self.assertEqual(t[1], self.dimitris)
        
    def test_labels(self):
        #test that LEC, REC, BREAKOUT are only valid labels
        self.assertRaises(SESError, Course, 
            "15.051 J ", "Economics", 30, self.arnie, self.time1, 
            classtype = "Foo")

        self.assertRaises(SESError, Course, 
            "15.051 J ", "Economics", 30, self.arnie, self.time1, 
            classtype = "")

        #should all execute normally
        Course("15.051 J ", "Economics", 30, self.arnie, self.time1, 
            classtype = "rEc1")

        Course("15.051 J ", "Economics", 30, self.arnie, self.time1, 
            classtype = "Breakout23")

        Course("15.051 J ", "Economics", 30, self.arnie, self.time1, 
            classtype = "Lec1")    
        

class TestHelpers(unittest.TestCase):
    def setUp(self):
        global _hasMsg 
        _hasMsg = False

        self.room1 = Room("E52-135", 60, ["projector"])
        self.room2 = Room("E52-136", 55)
        self.room3 = Room("E52-137", 50, ["camera"])
        self.roomInventory = [ self.room1, self.room2, self.room3]
        
        self.course1 = Course("15.051", "Economics", 52, Instructor("Arnie"), 
                TimeSlot("", "M W", "10:00 AM", "11:30 AM"))

        self.course2 = Course("15.052", "Economics", 50, Instructor("Arnie"), 
                TimeSlot("H1", "F", "4:00 PM", "7:00 PM"), 
                av_requirements = ["camera"])

        self.course3 = Course("15.052", "Economics", 51, Instructor("Arnie"), 
                TimeSlot("F", "F", "3:00 PM", "4:00 PM"), 
                av_requirements = ["camera"], classtype="REC")
                
        self.config = config.Options()
                
    def test_allowedRooms(self):
        #only rooms 1 and 2 can fit course1
        viable_rooms = helpers.allowedRooms(self.course1, self.roomInventory)
        self.assertEqual(viable_rooms[0], self.room1)
        self.assertEqual(viable_rooms[1], self.room2)
        self.assertEqual(len(viable_rooms), 2)

        #Respecting equipment
        viable_rooms = helpers.allowedRooms(self.course2, self.roomInventory)
        self.assertEqual(viable_rooms[0], self.room3)
        self.assertEqual(len(viable_rooms), 1)

        #Respecting a roomFlag
        self.course1.addRoomPrefs([self.room1], True)
        viable_rooms = helpers.allowedRooms(self.course1, self.roomInventory)
        self.assertEqual(len(viable_rooms), 1)

        #Respecting soft_capacity
        viable_rooms = helpers.allowedRooms(self.course3, self.roomInventory)
        self.assertEqual(viable_rooms[0], self.room3)
        self.assertEqual(len(viable_rooms), 1)

        #respect roomflag even if inviable
        self.assertFalse(hasMsg())
        self.course2.addRoomPrefs([self.room2], True)
        self.assertTrue(hasMsg())
        viable_rooms = helpers.allowedRooms(self.course2, self.roomInventory)
        self.assertEqual(len(viable_rooms), 1)

        #requesting an inviable room does not add it to the list
        #note previous test checks if warning is thrown
        self.assertFalse(hasMsg())
        self.course2.addRoomPrefs([self.room1, self.room2], False)
        self.assertTrue(hasMsg())
            
    #Course 1 is a standard lecture
    def test_times_lecture(self):
        viable_times = helpers.allowedTimes(self.course1, self.config)
        self.assertEqual(len(viable_times), 12)
        self.assertTrue(self.course1.timePrefs[0] in viable_times)
        for t in viable_times:
            self.assertEqual(t.half, Half("F"))
            self.assertEqual(t.meetingsPerWk(), 2)
            self.assertEqual(t.sessionLength(), 
                        datetime.timedelta(hours=1, minutes=30))

    #Course 2 is a seminar
    def test_times_seminar(self): 
        viable_times = helpers.allowedTimes(self.course2, self.config)
        self.assertTrue(len(viable_times), 15)
        self.assertTrue(self.course2.timePrefs[0] in viable_times)
        for t in viable_times:
            self.assertEqual(t.half, Half("H1"))
            self.assertEqual(t.meetingsPerWk(), 1)
            self.assertEqual(t.sessionLength(), datetime.timedelta(hours=3))
            self.assertTrue(t.startTime >= 
                    datetime.datetime.strptime(self.config.FIRST_SEMINAR, "%I:%M %p"))
            
    #Course 3 is a recitation
    def test_times_rec(self):
        viable_times = helpers.allowedTimes(self.course3, self.config, self.config.FREE_TIME)
        self.assertEqual(len(viable_times), 32)
        self.assertTrue(self.course3.timePrefs[0] in viable_times)
        for t in viable_times:
            self.assertEqual(t.half, Half("F"))
            self.assertEqual(t.meetingsPerWk(), 1)
            self.assertEqual(t.sessionLength(), datetime.timedelta(hours=1))
            self.assertTrue( t.days[0] in ("W", "Th", "F"))


    def test_invalid_time(self):
        #setting an invalid time (should be H1), respecting room
        #shoudl yield a warning, but still allow room
        ts = TimeSlot("H2", "F", "4:00 PM", "7:00 PM")
        self.assertFalse(hasMsg())
        self.course2.addTimePrefs([ts])
        self.assertTrue(hasMsg())
        
        self.assertFalse(hasMsg())
        viable_times = helpers.allowedTimes(self.course2, self.config)
        self.assertTrue(hasMsg())        
        self.assertEqual(len(viable_times), 16)

        self.assertTrue(ts in viable_times)

    def test_e_cap(self):
        self.assertEqual(helpers.e_cap(self.course3, self.room3), 0)
        self.assertEqual(helpers.e_cap(self.course3, self.room1), 0.15)




if __name__ == '__main__':
    unittest.main()