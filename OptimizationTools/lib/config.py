"""Config file for the SES Optimization

Contains constants particular to the SES
"""
from sesClasses import TimeSlot

#Heat Maps for requests
__time_grid__ = ["8:30 AM", "9:00 AM", "9:30 AM", "10:00 AM", "10:30 AM", 
            "11:00 AM", "11:30 AM", "12:00 PM","12:30 PM", "1:00 PM", 
            "1:30 PM", "2:00 PM", "2:30 PM", "3:00 PM", "3:30 PM", 
            "4:00 PM", "4:30 PM", "5:00 PM", "5:30 PM", "6:00 PM", 
            "6:30 PM", "7:00 PM", "7:30 PM", "8:00 PM"]

class Options:
    def __init__(self, file_path=None):
        """Initialize the config details"""
        if file_path is not None:
            raise NotImplementedError("Not yet supported.")
    
        self.FIRST_CLASS = "8:30 AM"
        self.LAST_CLASS = "8:00 PM"
        self.FIRST_SEMINAR = "4:00 PM"
    
        self.SLOAN_BLOCKS = (("8:30 AM", "10:00 AM"), ("10:00 AM", "11:30 AM"), 
                    ("11:30 AM", "1:00 PM"), ("1:00 PM", "2:30 PM"), 
                    ("2:30 PM", "4:00 PM"), ("4:00 PM", "5:30 PM"))
    
        self.FREE_TIME = TimeSlot("F", "M T W Th", "11:30 AM", "1:00 PM")

        #Pref Score Weight enforced to be >= this quantitiy
        self.EPS_SAFETY_OVERRIDE = 1e-3

        #Penalty for violating soft-constraint
        self.SOFT_CNST_PENALTY = 1e3
         
        #solver parameters
        self.REL_GAP = 1e-2
