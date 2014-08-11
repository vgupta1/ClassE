"""Write Data to File"""

def writeData(courses, roomInventory, name, room_grid=None):
    """Create the Large Sloan-style grids of room-assignments.
    Saved as separate .csv files"""
    if room_grid is None:
        room_grid = filter(lambda r: r.isInBldg("E62"), roomInventory)

    if not room_grid:
        raise ValueError("RoomGrid is empty.")
        
    #This is a lazy data structure
    #each daytype dict {room:dict}
    mw_dict = {}
    tth_dict = {}
    f_dict = {}

    #each room dict = {Time, [course1, course1])}
    for room in room_grid:
        mw_dict[room] = {}
        tth_dict[room] = {}
        f_dict[room] = {}
        
           
    
    
    , populate the relevant times
    #can check if multiple assignments to a time-block in this way
    #Put in Half-courses with a -
    
    #amalgamate the dictionaries into a .csv files
    
    
import readData

def main():
    #read in sample set of courses and inventory
    rooms = readData.importRoomInventory("./DataFiles/roomInventory.csv")
    courses = readData.importCourses("./DataFiles/F10c.csv", rooms)    
    courses = readData.addAssignments(courses, rooms, "./DataFiles/F10_Final.csv")

    writeData(courses, roomInventory, "grid")
    
if __name__ == '__main__':
  main()

    
    
    