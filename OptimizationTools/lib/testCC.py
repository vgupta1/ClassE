""" Unit Tests for the Course Calculator

All unit tests for the course calculator.  Excludes tests of the GUI

"""
import unittest
import courseCalculator as cc
import readData
from wx.lib.pubsub import Publisher as pub
from sesClasses import SESError
from sesClasses import TimeSlot


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


class TestReadData(unittest.TestCase):
    """Series of tests that test the readData Funcitonality"""
    def setUp(self):
        global _hasMsg 
        _hasMsg = False

    def test_rec_partner(self):
        """Ensures we throw if recitation missing a parnter lecture"""
        roomInventory = readData.importRoomInventory("./TestFiles/roominventory1.csv")
        self.assertRaises(SESError, readData.importCourses, 
                "./TestFiles/rec_no_partner1.csv", roomInventory)

    def test_room_twice_in_inventory(self):
        """Ensure we throw if room listed twice in inventory"""
        self.assertRaises(SESError, readData.importRoomInventory, 
            "./TestFiles/two_rooms.csv")

    def test_duplicate_course(self):
        """Throw an error if try to add the same course twice."""
        roomInventory = readData.importRoomInventory("./TestFiles/roominventory1.csv")
        self.assertRaises(SESError, readData.importCourses, 
                "./TestFiles/course_twice1.csv", roomInventory)

    def test_breakout_partner(self):
        """Ensures we throw if recitation missing a parnter lecture"""
        roomInventory = readData.importRoomInventory("./TestFiles/roominventory1.csv")
        self.assertRaises(SESError, readData.importCourses, 
                "./TestFiles/breakout_no_partner1.csv", roomInventory)

    def test_unknown_b2b(self):
        """Specifying b2b constraints for a course that is not scheduled should
        yield a warning, and then constraint ignored."""
        pass


class TestCC(unittest.TestCase):    
    def setUp(self):
        global _hasMsg 
        _hasMsg = False
    
    def test_no_inventory_room_pref(self):
        """
        Specifying a room not in inventory as a preference 
        If respect room, should get it, no warning.
        If not, raise a warning and preference is dropped.
        """
        ######First try with a respectRoom Flag
        #should issue no warnings and execute normally
        self.assertFalse(hasMsg())
        model = cc.SESModel(quiet=True)
        model.setData("./TestFiles/room_not_in_inv_respect1.csv", 
                "./TestFiles/roominventory1.csv", 
                "./TestFiles/NoConflict1.csv", 
                "./TestFiles/blank_b2b.csv")

        model.setWeights(scoreWeights=[1, 0, 0], 
                        prefWeight=1, 
                        eCapWeight = 1, 
                        congWeight = 1, 
                        deptFairness = 1, 
                        b2bWeight = 0)

        model.optimize()
        
        #assert that course got its room        
        c = filter(lambda c: c.isSame("15.012", "A", "LEC"), model.courses)
        self.assertEqual(len(c), 1)
        self.assertEqual(str(c[0].assignedRoom), "E25-111")
        self.assertFalse(hasMsg())
        
        ########Now try without respectRoom Flag
        #should issue a warning and assign to some other room
        model.setData("./TestFiles/room_not_in_inv1.csv", 
                "./TestFiles/roominventory1.csv", 
                "./TestFiles/NoConflict1.csv", 
                "")
        model.setWeights(scoreWeights=[1, 0, 0], 
                        prefWeight=1, 
                        eCapWeight = 1, 
                        congWeight = 1, 
                        deptFairness = 1, 
                        b2bWeight = 0)
        model.optimize()
        self.assertTrue(hasMsg())
        c = filter(lambda c: c.isSame("15.012", "A", "LEC"), model.courses)
        self.assertEqual(len(c), 1)
        self.assertNotEqual(str(c[0].assignedRoom), "E25-111")

    def test_invalid_room_pref(self):
        """Specifying an invalid room should ALWAYS yield a warning.  
        If respect room, should get it.  
        If not, preference is dropped."""
        ### Without a respect Room Flg
        self.assertFalse(hasMsg())
        model = cc.SESModel(quiet=True)
        model.setData("./TestFiles/invalid_room1.csv", 
                "./TestFiles/roominventory1.csv", 
                "./TestFiles/NoConflict1.csv", 
                "")
        self.assertTrue(hasMsg())

        model.setWeights(scoreWeights=[1, 0, 0], 
                        prefWeight=1, 
                        eCapWeight = 1, 
                        congWeight = 1, 
                        deptFairness = 1, 
                        b2bWeight = 0)

        model.optimize()
        self.assertTrue(hasMsg())
        
        c = filter(lambda c: c.isSame("15.012", "A", "LEC"), model.courses)
        self.assertEqual(len(c), 1)
        self.assertNotEqual(str(c[0].assignedRoom), "E51-061")

        #### Now with a respect Room Flag
        model.setData("./TestFiles/invalid_room_respect1.csv", 
                "./TestFiles/roominventory1.csv", 
                "./TestFiles/NoConflict1.csv", 
                "")
        self.assertTrue(hasMsg())

        model.setWeights(scoreWeights=[1, 0, 0], 
                        prefWeight=1, 
                        eCapWeight = 1, 
                        congWeight = 1, 
                        deptFairness = 1, 
                        b2bWeight = 0)
        model.optimize()
        self.assertTrue(hasMsg())
        
        c = filter(lambda c: c.isSame("15.012", "A", "LEC"), model.courses)
        self.assertEqual(len(c), 1)
        self.assertEqual(str(c[0].assignedRoom), "E51-061")

    def test_invalid_time_pref(self):
        """Specifying an invalid time should ALWAYS yield a warning.
        Preference should ALWAYS be included as if valid."""
        #second preference is invalid compared to first
        #first is not feasible bc another course has a respect time
        #should get second (invalid) pref.
        self.assertFalse(hasMsg())
        model = cc.SESModel(quiet=True)
        model.setData("./TestFiles/invalid_time_pref1.csv", 
                "./TestFiles/roominventory1.csv", 
                "./TestFiles/NoConflict1.csv", 
                "")
        self.assertTrue(hasMsg())

        model.setWeights(scoreWeights=[2, 1, 0], 
                        prefWeight=1, 
                        eCapWeight = 0, 
                        congWeight = 0, 
                        deptFairness = 0, 
                        b2bWeight = 0)

        model.optimize()
        self.assertTrue(hasMsg())
        
        #Check that the course gets its second preference
        c = filter(lambda c: c.isSame("15.012", "A", "LEC"), model.courses)
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0].assignedTime, TimeSlot("H1", "T", "8:30 AM", "10:00 AM"))

        c = filter(lambda c: c.isSame("15.012", "B", "LEC"), model.courses)
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0].assignedTime, TimeSlot("H1", "M W F", "8:30 AM", "10:00 AM"))
        
    def test_breakout(self):
        """Ensure that breakouts are on same floor/time as lecture"""
        self.assertFalse(hasMsg())
        model = cc.SESModel(quiet=True)
        model.setData("./TestFiles/breakout1.csv", 
                "./TestFiles/roominventory1.csv", 
                "./TestFiles/NoConflict1.csv", 
                "./TestFiles/blank_b2b.csv")
        self.assertTrue(hasMsg())

        model.setWeights(scoreWeights=[2, 1, 0], 
                        prefWeight=1, 
                        eCapWeight = 0, 
                        congWeight = 0, 
                        deptFairness = 0, 
                        b2bWeight = 0)

        model.optimize()
        self.assertTrue(hasMsg())
        
        #Check that the Lecture
        c = filter(lambda c: c.isSame("15.S03", "", ""), model.courses)
        self.assertEqual(len(c), 1)
        c = c[0]
        self.assertEqual(c.assignedTime, TimeSlot("", "T", "4:00 PM", "7:00 PM"))
        r = c.assignedRoom
        self.assertEqual(str(r), "E62-233")

        c = filter(lambda c: c.isSame("15.S03", "", "Breakout"), model.courses)
        self.assertEqual(len(c), 1)
        c = c[0]
        self.assertTrue(r.sameFloor(c.assignedRoom))
        self.assertEqual(c.assignedTime, TimeSlot("", "T", "4:00 PM", "7:00 PM"))

    def test_same_day(self):
        """Soft constraints that we maintain same requested day for things if possible"""
        pass
        
    def test_back2back_teaching(self):  
        """Should prefer to schedule back-2-back if possible"""
        #This schedule is set up that in the absence of back-2-back constraints
        #courses would be scheduled in different rooms
        #test that with and without are both identical
        model = cc.SESModel(quiet=True)

        #first solve with no b2b
        model.setData("./TestFiles/b2b_courses.csv", 
                "./TestFiles/roominventory1.csv", 
                "./TestFiles/NoConflict1.csv", 
                "")

        model.setWeights(scoreWeights=[1, 1, 0], 
                        prefWeight=10, 
                        eCapWeight = 0, 
                        congWeight = 0, 
                        deptFairness = 0, 
                        b2bWeight = 10)

        model.optimize()
        c1 = filter(lambda c: c.isSame("15.218", "A", "LEC"), model.courses)[0]
        c2 = filter(lambda c: c.isSame("15.218", "B", "LEC"), model.courses)[0]
        c3 = filter(lambda c: c.isSame("15.058", "", "LEC"), model.courses)[0]

#         print "No B2B"
#         for c in model.courses:
#             print c, c.assignedRoom, c.assignedTime

        self.assertEqual(str(c1.assignedRoom), "E51-057")
        self.assertEqual(str(c2.assignedRoom), "E51-145")
        self.assertEqual(str(c3.assignedRoom), "E51-145")

        #observe c1 and c2 assigned to different rooms without b2b
        self.assertNotEqual(c1.assignedRoom, c2.assignedRoom)

        #now with b2b
        model.setData("./TestFiles/b2b_courses.csv", 
                "./TestFiles/roominventory1.csv", 
                "./TestFiles/NoConflict1.csv", 
                "./TestFiles/back2back1.csv")
                
        model.optimize()
        c1 = filter(lambda c: c.isSame("15.218", "A", "LEC"), model.courses)[0]
        c2 = filter(lambda c: c.isSame("15.218", "B", "LEC"), model.courses)[0]
        c3 = filter(lambda c: c.isSame("15.058", "", "LEC"), model.courses)[0]

#         print "With B2B"
#         for c in model.courses:
#             print c, c.assignedRoom, c.assignedTime

        #observe c1 and c2 assigned to same room with b2b
        self.assertEqual(c1.assignedRoom, c2.assignedRoom)

        self.assertEqual(str(c1.assignedRoom), "E51-145")
        self.assertEqual(str(c2.assignedRoom), "E51-145")
        self.assertNotEqual(str(c3.assignedRoom), "E51-145")

    
    def test_back2back_teaching2(self):  
        """Should prefer to schedule back-2-back if possible"""
        #This schedule is set up that in the absence of back-2-back constraints
        #courses would be scheduled in different at different times
        #test that with and without are both identical
        model = cc.SESModel(quiet=True)

        model.setData("./TestFiles/b2b_courses2.csv", 
                "./TestFiles/roominventory1.csv", 
                "./TestFiles/NoConflict1.csv", 
                "./TestFiles/back2back1.csv")

        #first solve with no b2b
        model.setWeights(scoreWeights=[1, 1, 0], 
                        prefWeight=10, 
                        eCapWeight = 0, 
                        congWeight = 0, 
                        deptFairness = 0, 
                        b2bWeight = 0.)

        model.optimize()
        c1 = filter(lambda c: c.isSame("15.218", "A", "LEC"), model.courses)[0]
        c2 = filter(lambda c: c.isSame("15.218", "B", "LEC"), model.courses)[0]
        c3 = filter(lambda c: c.isSame("15.058", "", "LEC"), model.courses)[0]

        self.assertEqual(str(c1.assignedRoom), "E51-057")
        self.assertEqual(str(c2.assignedRoom), "E51-145")
        self.assertEqual(str(c3.assignedRoom), "E51-145")

        #observe c1 and c2 assigned to different rooms, non-adjacent times without b2b
        self.assertEqual(c1.assignedTime, TimeSlot("F", "T Th", "2:00 PM", "3:30 PM"))
        self.assertEqual(c2.assignedTime, TimeSlot("F", "T Th", "10:00 AM", "11:30 AM"))
        self.assertEqual(c3.assignedTime, TimeSlot("F", "T Th", "8:30 AM", "10:00 AM"))

        #Now with b2b
        model.setWeights(scoreWeights=[1, 1, 0], 
                        prefWeight=10, 
                        eCapWeight = 0, 
                        congWeight = 0, 
                        deptFairness = 0, 
                        b2bWeight = 100)

        model.optimize()
        c1 = filter(lambda c: c.isSame("15.218", "A", "LEC"), model.courses)[0]
        c2 = filter(lambda c: c.isSame("15.218", "B", "LEC"), model.courses)[0]
        c3 = filter(lambda c: c.isSame("15.058", "", "LEC"), model.courses)[0]

        self.assertEqual(str(c1.assignedRoom), "E51-145")
        self.assertEqual(str(c2.assignedRoom), "E51-145")
        self.assertEqual(str(c3.assignedRoom), "E51-145")

        #observe c1 and c2 same room, adjacent (including lunch) with b2b
        self.assertEqual(c1.assignedTime, TimeSlot("F", "T Th", "1:00 PM", "2:30 PM"))
        self.assertEqual(c2.assignedTime, TimeSlot("F", "T Th", "10:00 AM", "11:30 AM"))
        self.assertEqual(c3.assignedTime, TimeSlot("F", "T Th", "8:30 AM", "10:00 AM"))

    def test_friday_afternoon(self):
        """Classes should not be too late on Fridays"""
        pass

    def test_no_conflict(self):
        """Specifying a non-conflict for a course that doesn't exist 
            should yield a waring, and ignore the constraint
            Otherwise use it."""
        pass

class TestOutput(unittest.TestCase):
    def setUp(self):
        global _hasMsg 
        _hasMsg = False

    def test_grid(self):
        """confirm that grid funcitonality works
        Especially confirm the listing of which choice people got when they specify
        less than 3 choices"""
        pass

    def test_mark_same_day(self):
        """confirm that when same-day not respected, we get a mark"""
        pass

    def test_listing(self):
        """confirm thatlisting functionality works"""
        pass    