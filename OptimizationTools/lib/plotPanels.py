"""Plotting Panels

Contains all the panels on the RHS of the gui that do
the plotting etc.
"""
import wx
from wx.lib.pubsub import Publisher as pub
import numpy

import matplotlib
matplotlib.interactive( True )
matplotlib.use( 'WXAgg' )
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas

class MyPanel(wx.Panel):
    """Small wrapper around a wx.Panel that includes a model"""
    #this is cludgey and should be fixed
    grey_col = numpy.array([247, 247, 247, 247])
    face_col = numpy.array([.9647, .9647, .9647])

    sz_num_field = (40, 20)

    def __init__(self, *args, **kwargs):
        assert "sesModel" in kwargs
        self.model = kwargs.pop("sesModel")
        wx.Panel.__init__(self, *args, **kwargs)        

    def labelBars(self, rects, s_labels, ax):
        """label each of the rectangles above.  s_labels should be strings."""
        for rect, label in zip(rects, s_labels):
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width()/2., 
                    height + 2 , label,
                    ha='center', va='bottom')

class CourseSummarySubPanel(MyPanel):
    def __init__(self, *args, **kwargs):
        MyPanel.__init__(self, *args, **kwargs)        

        sum_box = wx.StaticBox(self, label="Course Breakdown")
        box_sizer = wx.StaticBoxSizer(sum_box, wx.VERTICAL)
        fgs = wx.FlexGridSizer(rows=3, cols=3)
        box_sizer.Add(fgs, proportion=1, flag=wx.EXPAND)

        fgs.Add(wx.StaticText(self, label="All"), flag=wx.TE_LEFT)
        self.TotalCourses = (
                wx.StaticText(self, size=self.sz_num_field, style=wx.TE_RIGHT), 
                wx.StaticText(self, size=self.sz_num_field, style=wx.TE_RIGHT))
        fgs.AddMany(self.TotalCourses)

        fgs.Add(wx.StaticText(self, label="Lectures"), flag=wx.TE_LEFT)
        self.NoLecturesFields = (
                wx.StaticText(self, size=self.sz_num_field, style=wx.TE_RIGHT), 
                wx.StaticText(self, size=self.sz_num_field, style=wx.TE_RIGHT))
        fgs.Add(self.NoLecturesFields[0], flag=wx.TE_RIGHT)
        fgs.Add(self.NoLecturesFields[1], flag=wx.TE_RIGHT)

        fgs.Add(wx.StaticText(self, label="Other"), flag=wx.TE_LEFT)
        self.NoOtherCourses = (
                wx.StaticText(self, size=self.sz_num_field, style=wx.TE_RIGHT), 
                wx.StaticText(self, size=self.sz_num_field, style=wx.TE_RIGHT))
        fgs.AddMany(self.NoOtherCourses)

        fgs.Add(wx.StaticText(self, label="Fixed Rooms   "), flag=wx.TE_LEFT)
        self.FixedRooms = (
                wx.StaticText(self, size=self.sz_num_field, style=wx.TE_RIGHT), 
                wx.StaticText(self, size=self.sz_num_field, style=wx.TE_RIGHT))
        fgs.AddMany(self.FixedRooms)

        fgs.Add(wx.StaticText(self, label="Fixed Times"), flag=wx.TE_LEFT)
        self.FixedTimes = (
                wx.StaticText(self, size=self.sz_num_field, style=wx.TE_RIGHT), 
                wx.StaticText(self, size=self.sz_num_field, style=wx.TE_RIGHT))
        fgs.AddMany(self.FixedTimes)

        self.SetSizerAndFit(box_sizer)
        pub.subscribe(self.updateCourseRequests, "data_loaded")


    def updateCourseRequests(self, message):
        """Listener for data_loaded Event"""
        try:        
            #ideally this info would be passsed by a controller
            #instead of solicited
            no_lecs, no_other, no_tot, no_fixedRooms, no_fixedTimes = self.model.countCourseTypes()
            
            self.NoLecturesFields[0].SetLabel("%d" % no_lecs[0])
            self.NoLecturesFields[1].SetLabel("%.0f%%" % (100 * no_lecs[1]))
            self.NoOtherCourses[0].SetLabel("%d" % no_other[0])
            self.NoOtherCourses[1].SetLabel("%.0f%%" % (100 * no_other[1]))
            self.TotalCourses[0].SetLabel("%d" % no_tot[0])
            self.TotalCourses[1].SetLabel("%.0f%%" % (100 * no_tot[1]))
            self.FixedRooms[0].SetLabel("%d" % no_fixedRooms[0])
            self.FixedRooms[1].SetLabel("%.0f%%" % (100 * no_fixedRooms[1]))
            self.FixedTimes[0].SetLabel("%d" % no_fixedTimes[0])
            self.FixedTimes[1].SetLabel("%.0f%%" % (100 * no_fixedTimes[1]))
        except Exception as e:
            pub.sendMessage("status_bar.error", str(e))


class PreferencesSubPanel(MyPanel):
    def __init__(self, *args, **kwargs):
        MyPanel.__init__(self, *args, **kwargs)        

        sum_box = wx.StaticBox(self, label="Preferences")
        box_sizer = wx.StaticBoxSizer(sum_box, wx.VERTICAL)
        fgs = wx.FlexGridSizer(rows=3, cols=5)
        box_sizer.Add(fgs, proportion=1, flag=wx.EXPAND)

        fgs.AddMany([(wx.StaticText(self, style=wx.ALIGN_LEFT), 0, wx.EXPAND), 
                    (wx.StaticText(self, label="1st", style=wx.ALIGN_LEFT), 0, wx.EXPAND), 
                    (wx.StaticText(self, label="2nd", style=wx.ALIGN_LEFT), 0, wx.EXPAND),  
                    (wx.StaticText(self, label="3rd", style=wx.ALIGN_LEFT), 0, wx.EXPAND), 
                    (wx.StaticText(self, label="Other", style=wx.ALIGN_LEFT), 0, wx.EXPAND) ])

        self.RoomPrefFields = [wx.StaticText(self, size=self.sz_num_field, style=wx.ALIGN_LEFT), 
                wx.StaticText(self, size=self.sz_num_field, style=wx.ALIGN_LEFT), 
                wx.StaticText(self, size=self.sz_num_field, style=wx.ALIGN_LEFT), 
                wx.StaticText(self, size=self.sz_num_field, style=wx.ALIGN_LEFT)] 
        fgs.Add(wx.StaticText(self, label="Rooms   ", style=wx.TE_LEFT), flag = wx.EXPAND)
        for field in self.RoomPrefFields:
            fgs.Add(field, flag=wx.EXPAND)

        self.TimePrefFields = [wx.StaticText(self, size=self.sz_num_field, style=wx.ALIGN_LEFT), 
                wx.StaticText(self, size=self.sz_num_field, style=wx.ALIGN_LEFT), 
                wx.StaticText(self, size=self.sz_num_field, style=wx.ALIGN_LEFT), 
                wx.StaticText(self, size=self.sz_num_field, style=wx.ALIGN_LEFT)]
        fgs.Add(wx.StaticText(self, label="Times   ", style=wx.TE_LEFT), flag = wx.EXPAND)
        for field in self.TimePrefFields:
            fgs.Add(field, flag=wx.EXPAND)

        self.SetSizerAndFit(box_sizer)
        pub.subscribe(self.updatePrefs, "assignments_calced")


    def updatePrefs(self, messsage):
        """Listener for the assignments_calced event"""
        try:
            room_prefs, time_prefs = self.model.prefsStats()
    
            assert len(room_prefs) == len(self.RoomPrefFields)
            assert len(time_prefs) == len(self.TimePrefFields)
            
            for ix in range(len(room_prefs)):
                 self.RoomPrefFields[ix-1].SetLabel("%d" % room_prefs[ix])
    
            for ix in range(len(time_prefs)):
                self.TimePrefFields[ix-1].SetLabel("%d" % time_prefs[ix])
        except Exception as e:
            pub.sendMessage("status_bar.error", str(e))


class EfficiencySubPanel(MyPanel):
    def __init__(self, *args, **kwargs):
        MyPanel.__init__(self, *args, **kwargs)        
        #self.SetBackgroundColour(self.grey_col)

        sum_box = wx.StaticBox(self, label="Efficiency")
        box_sizer = wx.StaticBoxSizer(sum_box, wx.VERTICAL)
        fgs = wx.FlexGridSizer(rows=2, cols=2)
        box_sizer.Add(fgs, proportion=1, flag=wx.EXPAND)

        fgs.Add(wx.StaticText(self, label="Excess Capacity   ", style=wx.TE_LEFT), flag=wx.EXPAND)
        self.eCapField = wx.StaticText(self, 
                size = self.sz_num_field, style=wx.TE_RIGHT)
        fgs.Add(self.eCapField, flag=wx.EXPAND)

        fgs.Add(wx.StaticText(self, label="Congestion", 
                style=wx.TE_LEFT), flag=wx.EXPAND)
        self.CongField = wx.StaticText(self, 
                size = self.sz_num_field, style=wx.TE_RIGHT)
        fgs.Add(self.CongField, flag=wx.EXPAND)

        self.SetSizerAndFit(box_sizer)
        pub.subscribe(self.update, "assignments_calced")


    def update(self, messsage):
        """Listener for the assignments_calced event"""
        try:
            e_cap = self.model.summarizeExcessCap()
            cong = self.model.maxCongestion()
    
            self.eCapField.SetLabel("%.0f%%" % e_cap)         
            self.CongField.SetLabel("%d" % cong) 
        except Exception as e:
            pub.sendMessage("status_bar.error", str(e))

class FairnessSubPanel(MyPanel):
    def __init__(self, *args, **kwargs):
        MyPanel.__init__(self, *args, **kwargs)        
        sum_box = wx.StaticBox(self, label="Fairness")
        box_sizer = wx.StaticBoxSizer(sum_box, wx.VERTICAL)
        fgs = wx.FlexGridSizer(rows=2, cols=4, hgap = 10)
        box_sizer.Add(fgs, proportion=1, flag=wx.EXPAND)

        fgs.Add(wx.StaticText(self, style=wx.ALIGN_RIGHT), flag = wx.EXPAND)
        fgs.Add(wx.StaticText(self, label="Dept", style=wx.ALIGN_RIGHT), flag=wx.EXPAND) 
        fgs.Add(wx.StaticText(self, label="Room", style=wx.ALIGN_RIGHT), flag=wx.EXPAND)
        fgs.Add(wx.StaticText(self, label="Time", style=wx.ALIGN_RIGHT), flag=wx.EXPAND)

        self.minDeptFields = [wx.StaticText(self, size=self.sz_num_field, style=wx.ALIGN_RIGHT), 
                wx.StaticText(self, style=wx.ALIGN_RIGHT), 
                wx.StaticText(self, size=self.sz_num_field, style=wx.ALIGN_RIGHT)] 
        fgs.Add(wx.StaticText(self, label="Min", style=wx.ALIGN_RIGHT), flag = wx.EXPAND)
        for field in self.minDeptFields:
            fgs.Add(field, flag=wx.EXPAND)

        self.maxDeptFields = [wx.StaticText(self, size=self.sz_num_field, style=wx.ALIGN_RIGHT), 
                wx.StaticText(self, style=wx.ALIGN_RIGHT), 
                wx.StaticText(self, size=self.sz_num_field, style=wx.ALIGN_RIGHT)]
        fgs.Add(wx.StaticText(self, label="Max", style=wx.ALIGN_RIGHT), flag = wx.EXPAND)
        for field in self.maxDeptFields:
            fgs.Add(field, flag=wx.EXPAND)

        self.SetSizerAndFit(box_sizer)
        self.sizer = box_sizer
        pub.subscribe(self.update, "assignments_calced")


    def update(self, messsage):
        """Listener for the assignments_calced event"""
        try:
            results = self.model.getAllDeptPrefScores()
            sorted_keys = sorted(results.keys(), key=lambda k: results[k][0] + results[k][1])
            min_dept = sorted_keys[0]
            max_dept = sorted_keys[-1]

        except Exception as e:
            pub.sendMessage("status_bar.error", e.__str__())
        else:
            self.minDeptFields[0].SetLabel(min_dept[:4])
            self.minDeptFields[1].SetLabel("%.0f%%" % (100 * results[min_dept][0]))
            self.minDeptFields[2].SetLabel("%.0f%%" % (100 * results[min_dept][1]))
    
            self.maxDeptFields[0].SetLabel(max_dept[:4])
            self.maxDeptFields[1].SetLabel("%.0f%%" % (100 * results[max_dept][0]))
            self.maxDeptFields[2].SetLabel("%.0f%%" % (100 * results[max_dept][1]))


class OverviewPanel(MyPanel):
    def __init__(self, *args, **kwargs):
        MyPanel.__init__(self, *args, **kwargs)        
        self.SetBackgroundColour(wx.WHITE)
        fgs = wx.FlexGridSizer(rows=2, cols=2, vgap = 20, hgap = 20)
        fgs.Add(CourseSummarySubPanel(self, sesModel=self.model))
        fgs.Add(FairnessSubPanel(self, sesModel=self.model))
        fgs.Add(EfficiencySubPanel(self, sesModel=self.model))
        fgs.Add(PreferencesSubPanel(self, sesModel=self.model))
        self.SetSizerAndFit(fgs)
     

class PreferencesPanel(MyPanel):
    def __init__(self, *args, **kwargs):
        MyPanel.__init__(self, *args, **kwargs)
        self.SetBackgroundColour(self.grey_col)
        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.fig = Figure(facecolor=self.face_col)
        self.ax = self.fig.add_subplot(111)

        self.canvas = FigureCanvas(self, -1, self.fig)
        self.vbox.Add(self.canvas, flag = wx.EXPAND | wx.ALL)
        self.SetSizerAndFit(self.vbox)

        pub.subscribe(self.redraw, "assignments_calced")
    
    def redraw(self, message):
        """Does all the work to generate the two bar plots
        Listener for the assignments_calced message"""
        try:
            rooms_dict, times_dict = self.model.prefsStats()
    
            #relabel the dictionaries
            #probably a smarter way to do this
            labels = ["1st", "2nd", "3rd", "Other"]
            room_prefs = [rooms_dict[1], rooms_dict[2], rooms_dict[3], rooms_dict[0]]
            time_prefs = [times_dict[1], times_dict[2], times_dict[3], times_dict[0]]
    
    
            width = .35
            x_ticks = numpy.arange(max(len(rooms_dict), len(times_dict)))
            self.ax.clear()
    
            #1 plot, two sets of data
            rects_rooms = self.ax.bar(x_ticks, room_prefs, linewidth=0, color="cornflowerblue", width=width)
            rects_times = self.ax.bar(x_ticks + width, time_prefs, linewidth=0, color="orange", width=width)
            self.ax.set_xticks(x_ticks + width)
            
            #label axes etc.
            self.ax.set_xticklabels(labels)        
            self.fig.autofmt_xdate()
            self.ax.set_xlabel("Choice")
            self.ax.set_title("Preference Breakdown")
            self.ax.set_ylabel("No. of Courses")        
            self.ax.legend( (rects_rooms[0], rects_times[0]), ('Rooms', 'Times') )
    
            #label bars
            room_tot = sum(room_prefs)
            room_prefs_perc = [ 100 * r / room_tot for r in room_prefs ]
            room_prefs_perc = [ "%.0f%%" % r for r in room_prefs_perc]
            self.labelBars(rects_rooms, room_prefs_perc, self.ax)
    
            time_tot = sum(time_prefs)
            time_prefs_perc = [ 100 * t / time_tot for t in time_prefs ]
            time_prefs_perc = [ "%.0f%%" % t for t in time_prefs_perc]
            self.labelBars(rects_times, time_prefs_perc, self.ax)
    
            self.canvas.draw()
        except Exception as e:
            pub.sendMessage("status_bar.error", str(e))


class CapacityPanel(MyPanel):
    def __init__(self, *args, **kwargs):
        MyPanel.__init__(self, *args, **kwargs)        
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        fig = Figure(facecolor=self.face_col)
        
        self.ax = fig.add_subplot(111)

        self.canvas = FigureCanvas(self, -1, fig)
        self.vbox.Add(self.canvas, flag = wx.EXPAND | wx.ALL)
        self.SetSizerAndFit(self.vbox)

        pub.subscribe(self.redraw, "assignments_calced")

    def redraw(self, message):
        """Create a histogram"""
        e_caps = self.model.excessCap()
        e_caps = [x * 100 for x in e_caps]

        self.ax.clear()
        n, bins, patches = self.ax.hist(e_caps, normed=False, bins=10, color="cornflowerblue", 
                    rwidth=.8, linewidth=0)
        self.ax.set_xlabel("Excess Capacity (%)")
        self.ax.set_ylabel("No. of Courses")
        self.ax.set_title("Distribution of Excess Capacity")
        
        num_courses = float(len(e_caps))
        s_labels = [ 100 * p.get_height()/num_courses for p in patches]
        s_labels = [ "%.0f%%" % p for p in s_labels]
        
        self.labelBars(patches, s_labels, self.ax)
        self.canvas.draw()
        

class FairnessPanel(MyPanel):
    def __init__(self, *args, **kwargs):
        MyPanel.__init__(self, *args, **kwargs)        
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.fig = Figure(facecolor=self.face_col)
        
        self.ax = self.fig.add_subplot(111)

        self.canvas = FigureCanvas(self, -1, self.fig)
        self.vbox.Add(self.canvas, flag = wx.EXPAND | wx.ALL)
        self.SetSizerAndFit(self.vbox)

        pub.subscribe(self.redraw, "assignments_calced")

    def redraw(self, message):
        """Create a barplot.  Listner for the assignments_calced event"""
        results = self.model.getAllDeptPrefScores()
        sorted_keys = sorted(results.keys())
        room_vals = [results[k][0] * 100 for k in sorted_keys ]
        time_vals = [results[k][1] * 100 for k in sorted_keys ]

        width = .35
        x_ticks = numpy.arange(len(results))
        
        self.ax.clear()
        rects_rooms = self.ax.bar(x_ticks, room_vals, linewidth=0, color="cornflowerblue", width=width)
        self.ax.set_xticks(x_ticks + width)
                
        rects_times = self.ax.bar(x_ticks + width, time_vals, linewidth=0, color="orange", width=width)

        self.ax.set_xticklabels(sorted_keys)        
        self.fig.autofmt_xdate()
        self.ax.set_title("Preference Scores by Dept")
        self.ax.set_ylabel("Score (%)")        
        self.ax.legend( (rects_rooms[0], rects_times[0]), ('Rooms', 'Times'), 
                ncol=1, loc="lower right")

        self.canvas.draw()


class HeatMapPanel(MyPanel):
    def __init__(self, *args, **kwargs):
        MyPanel.__init__(self, *args, **kwargs)        
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.fig = Figure(facecolor=self.face_col)
        
        self.ax1 = self.fig.add_subplot(211)
        self.ax2 = self.fig.add_subplot(212)
        self.cbar = None

        self.canvas = FigureCanvas(self, -1, self.fig)
        self.vbox.Add(self.canvas)

        self.SetSizerAndFit(self.vbox)

        pub.subscribe(self.redraw, "assignments_calced")

    def redraw(self, message):
        """Create both heatmaps and colorbar.  Listner for the assignments_calced event"""
        cax1 = self.createHeatMap(self.ax1, "H1")
        cax2 = self.createHeatMap(self.ax2, "H2")
 
        if self.cbar is None:
            self.cbar = self.fig.colorbar(cax2, orientation="horizontal")

        self.canvas.draw()

    def createHeatMap(self, ax, half):
        resultsH1, xlabels, ylabels = self.model.genHeatMap(half)
        ax.clear()
        cax = ax.imshow(resultsH1, 
                interpolation="none", 
                picker=True, 
                vmin=0, 
                vmax=20)

        ax.set_title(half)
        ax.set_yticklabels([""] + ylabels)        

        ax.set_xticks(range(0, len(xlabels), 3))
        ax.set_xticklabels(xlabels[::3])
        
        return cax


class LogPanel(MyPanel):
    def __init__(self, *args, **kwargs):
        MyPanel.__init__(self, *args, **kwargs)        

        #Create a Sizer and place a single display in it
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.TextLog = wx.TextCtrl(self, style = wx.TE_MULTILINE | wx.TE_READONLY)
        vbox.Add(self.TextLog, proportion=1, flag=wx.EXPAND)

        self.SetSizerAndFit(vbox)
        pub.subscribe(self.logErrors, "warning")
        pub.subscribe(self.logErrors, "status_bar")

    def logErrors(self, message):
        """Listenener for errors/warnings"""
        if "warning" in message.topic:
            self.TextLog.WriteText("Warning: ") 
        elif "error" in message.topic:
            self.TextLog.WriteText("Error: ")
        
        self.TextLog.WriteText(message.data + "\n")



# ------------ For debugging purposes only
## Import platform specific model
from platform import system
import courseCalculator as cc 

class TestFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, None, *args, **kwargs)

        model = cc.SESModel()

        #add the panel to be tested
        testPanel = FairnessPanel(self, sesModel=model)

        model.setData("./F10_DataFiles/courseRequests.csv", 
                      "./F10_DataFiles/roomInventory.csv", 
                      "./F10_DataFiles/noConflict.csv")
        model.addAssignments("./F10_DataFiles/Assignments.csv")


#        testPanel.redraw(None)


if __name__ == '__main__':
    app = wx.App(False)      
    frame = TestFrame(size=(800,600))
    frame.Show()
    
    app.MainLoop()



