"""Helper Functions for the Scheduling Optimization"""
import sesClasses as ses
import datetime as dt
import config, itertools
from wx.lib.pubsub import Publisher as pub


#these are mostly for readability
str2time = ses.TimeSlot.str2time
time2str = ses.TimeSlot.time2str 

#these are needed for the function main()
import readData

def allowedRooms(course, roomInventory):
    """Return a list of permissible rooms for this course.
    If asked to respect room, will always return that room.
    Othewise, only return viable rooms.  
    """
    if course.respectRoom:
        return [course.roomPrefs[0]]

    viable_rooms = filter(lambda r: course.isViableRoom(r), roomInventory)
    for r in course.roomPrefs:
        if r not in viable_rooms:
            pub.sendMessage("warning", 
                    "Room Pref %s not used for course %s because inviable or not in inventory" % 
                    (r, course) )
    
    return viable_rooms
    
#VG: change this to look for forbiddentimeSlots inside config_details
def allowedTimes(course, config_details, forbiddenTimeSlot = None):
    """Return a list of allowed TimeSlots for this course.
        Args:
        course - course instance
        forbiddenTimeSlot - No TimeSlot meets OVERLAP with this 1 time slot

        If asked ot respect time, always return that time.
        Otherwise, will add preferred times even if deemed inviable (with warning)
    """
    if course.respectTime:
        return [course.timePrefs[0]]
    
    #Figure out how many times it meets
    ts = course.timePrefs[0]
    no_meetings_wk = ts.meetingsPerWk()        
    days = []
    if no_meetings_wk == 3:
        days = ("M W F",)
    elif no_meetings_wk == 2:
        days = ("M W", "T Th")
    elif no_meetings_wk == 1:
        #if its a recitation requesting last half week, honor it
        if course.isRec() and ts.days[0] in ("W", "Th", "F"):
            days = ("W", "Th", "F")
        else:
            days = ses.TimeSlot.daysOfWeek
    else: #no_meetings_wk >= 4:
        raise ses.SESError("Course %s meets more than 3X/wk" % course )

    #figure out for how long it meets
    session_length = ts.sessionLength()
    half_hour = dt.timedelta(minutes=30)
    if session_length < half_hour:
        raise ValueError(
        "Course %s meets for less than 30 min per session" % course)

    starts = []
    if session_length == dt.timedelta(hours=1, minutes=30):
        #Sloan blocks only
        starts = [str2time(s) for s,e in config_details.SLOAN_BLOCKS]
    elif session_length == dt.timedelta(hours=1):
        #Sloan Blocks and half hour offsets    
        starts = [str2time(s) for s,e in config_details.SLOAN_BLOCKS]
        starts += [start + half_hour for start in starts]
    else:
        #If it specifically requested a time before 4pm, let it have it
        #otherwise, must be after 4pm
        #This rule should be revisited by the SES team
        if ts.startTime < str2time(config_details.FIRST_SEMINAR):
            earliest_time = str2time(config_details.SLOAN_BLOCKS[0][0])
        else:
            earliest_time = str2time(config_details.FIRST_SEMINAR)

        latest_time = str2time(config_details.LAST_CLASS) - session_length
        while earliest_time <= latest_time:
            starts.append(earliest_time)
            earliest_time += half_hour
    
    #put everything together
    ts_from_start = lambda s, d: ses.TimeSlot(ts.half, d, s, 
                    s + session_length) 
    viable_ts = [ts_from_start(s, d) for (s,d) in itertools.product(starts, days)]
            
    #exclude the foribidden time slots.
    if forbiddenTimeSlot is not None:
        assert isinstance(forbiddenTimeSlot, ses.TimeSlot)
        viable_ts = filter(lambda t: not t.overlap(forbiddenTimeSlot), viable_ts)    

    #add the preferences back just incase they aren't in there
    #potentially violates forbidden times
    #ideally throw a warning here instead of adding back directly
    for ts in course.timePrefs:
        if ts not in viable_ts:
            pub.sendMessage(
                    "warning", "Time Pref %s was added, but not deemed viable for %s" % (ts, course))
            viable_ts.append(ts)
    
    return viable_ts

def allowedRoomTimes(course, config_details, roomInventory, forbiddenTimeSlots):
    """Returns a list of allowed (room, Timeslots) for this course."""
    rooms = allowedRooms(course, roomInventory)
    times = allowedTimes(course, config_details, forbiddenTimeSlots)

    if not rooms or not times:
        raise ses.SESError("No viable rooms or times for course %s" % course.__str__())
        
    return [(r, ts) for r in rooms for ts in times]

def e_cap(course, room):
    """Compute excess capacity in room"""
    return max((room.capacity - course.enrollment)/float(room.capacity), 0)

def genAllTimeSlots(config_options, excludeFreeTime=True):
    """List all half-hour time slots"""
    halfhour = dt.timedelta(minutes=30)
    times = []
    for half in (ses.Half("H1"), ses.Half("H2")):
        for d in ses.TimeSlot.daysOfWeek:
            startTime = str2time(config_options.FIRST_CLASS)
            while startTime < str2time(config_options.LAST_CLASS):
                ts = ses.TimeSlot(half, d, startTime, startTime + halfhour)
                if not excludeFreeTime or not config_options.FREE_TIME.overlap(ts):
                    times.append(ts)
                startTime += halfhour
    return times
    

def main():
    room_inventory = readData.importRoomInventory("DataFiles/roomInventory.csv")

    ts1 = ses.TimeSlot("F", "W", "4:00 PM", "7:00 PM")
    course1 = ses.Course("15.051", "Economics", 58, ses.Instructor("Arnie"), 
                ts1)

    rooms = allowedRooms(course1, room_inventory)
    print len(rooms), len(room_inventory)
    print min([r.capacity for r in rooms])

    course1.addRoomPrefs((ses.Room("E62-223", 100),), True)
    rooms = allowedRooms(course1, room_inventory)
    print len(rooms), len(room_inventory)
    print rooms[0]

    viable_times = allowedTimes(course1, [])
    print len(viable_times)

    #some sanity checks
    assert(ts1 in viable_times)
    for ts in viable_times:
        assert(course1.isViableTime(ts))
        print ts

    #all times
    all_times = genAllTimeSlots()
    for t in all_times:
        print t
        
    
if __name__ == '__main__':
    main()