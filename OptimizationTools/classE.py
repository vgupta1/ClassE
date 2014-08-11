""""The Class-e Gui"""
import wx, wx.lib.intctrl
from os.path import join #for concatenating path variables
from wx.lib.pubsub import Publisher as pub

from lib.plotPanels import* #used for the various notebook tabs
from lib import courseCalculator as cc

#GUI Version
__version__ = 3

#Needs spreadsheets of this version
__xl_version__ = 5

#Optimzier stores its own versioning info


class ClassE(wx.Frame):
    """ Gui for the SES project.
        """
    def __init__(self, *args, **kwargs):
        assert "title" not in kwargs
        kwargs["title"] ="class-E   version %s.%s.%s" % (
                __version__, cc.__version__, __xl_version__) 
        if "size" not in kwargs:
            kwargs["size"] = 1000, 600
        wx.Frame.__init__(self, None, *args, **kwargs)
        self.model = cc.SESModel()

        #give it a picture frame
        mainPanel_out =  wx.Panel(self)
        mainPanel_out.SetBackgroundColour(wx.WHITE)
        frame_box = wx.BoxSizer(wx.HORIZONTAL)

        mainPanel_in = wx.Panel(mainPanel_out)
        frame_box.Add( mainPanel_in,
                        proportion=1,
                        flag=wx.EXPAND | wx.ALL, 
                        border=20)

        self.topLayout(mainPanel_in)

        #add menubars
        self.addMenuBar()
        self.sb = self.CreateStatusBar()
        pub.subscribe(self.updateStatusBar, "status_bar")
        pub.subscribe(self.updateStatusBar, "warning")

        #Display everything
        mainPanel_out.SetSizerAndFit(frame_box)
        self.Show(True)

    def topLayout(self, parent):
        """Create the top level layout panels"""
        #Top level panel divided in to left/right
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        #the left handside panels do not need to size
        left_vbox = wx.BoxSizer(wx.VERTICAL)
        hbox.Add(left_vbox, border = 10)    
                 
        left_vbox.Add(LoadingPanel(parent, sesModel=self.model), 
                flag = wx.EXPAND)
        left_vbox.Add(OptimizationPanel(parent, sesModel=self.model), 
                flag = wx.TOP, 
                 border = 20)
                 
        #the Notebook area
        self.notebookPanel = wx.Panel(parent, 
                style = wx.RAISED_BORDER)

        hbox.Add(self.notebookPanel, 
                 proportion=1, 
                 border=10, 
                 flag = wx.EXPAND | wx.LEFT)
        self.populateNotebook()

        parent.SetSizerAndFit(hbox)

    def populateNotebook(self):
        nb = wx.Notebook(self.notebookPanel)
        self.heatMapTab = HeatMapPanel(nb, sesModel=self.model)
        self.prefTab = PreferencesPanel(nb, sesModel=self.model)
        self.capTab = CapacityPanel(nb, sesModel=self.model)
        self.overviewTab = OverviewPanel(nb, sesModel=self.model)
        self.logTab = LogPanel(nb, sesModel=self.model)
        self.fairnessTab = FairnessPanel(nb, sesModel=self.model)

        nb.AddPage(self.overviewTab, "Dashboard")
        nb.AddPage(self.capTab, "Excess Capacity")
        nb.AddPage(self.prefTab, "Preferences")
        nb.AddPage(self.fairnessTab, "Fairness")
        nb.AddPage(self.heatMapTab, "Heat Maps")
        nb.AddPage(self.logTab, "Logger")
        
        nb_sizer = wx.BoxSizer(wx.VERTICAL)
        nb_sizer.Add(nb, proportion=1, flag=wx.EXPAND)
        self.notebookPanel.SetSizerAndFit(nb_sizer)

    def addMenuBar(self):
        menubar = wx.MenuBar()

        #everything belongs under "File" menu
        file = wx.Menu()
        about = file.Append(wx.ID_ANY, '&About')
        self.Bind(wx.EVT_MENU, self.onAbout, about)
        export = file.Append(wx.ID_SAVEAS, '&Save', 'Export Assignments to a text file')
        self.Bind(wx.EVT_MENU, self.onExport, export)
        togrid = file.Append(wx.ID_ANY, 'Export &Grid', 'Export Assignments to a Grid')
        self.Bind(wx.EVT_MENU, self.onGrid, togrid)

        menubar.Append(file, '&File')
        self.SetMenuBar(menubar)

    def updateStatusBar(self, message):
        """Listener for status bar changes"""
        #check current status.  Precedence is reset > error < warning
        if "reset" in message.topic:
            self.sb.SetBackgroundColour((255, 255, 255, 255))
            self.SetStatusText("")
        elif "warning" in message.topic:
            self.sb.SetBackgroundColour('yellow')
            self.SetStatusText("Warnings generated. Check Log")
        elif "error" in message.topic:
            self.sb.SetBackgroundColour('Red')
            self.SetStatusText("Error encountered. Check Log")
            print message.data
        else:
            self.sb.SetBackgroundColour((255, 255, 255, 255))
            self.SetStatusText(message.data)

    def onAbout(self, event):
            msg_dlg = wx.MessageDialog(self, "classE was created by V. Gupta", 
                    style=wx.OK)
            msg_dlg.ShowModal()
            msg_dlg.Destroy()

    def onExport(self, event):
        """Export solution to a csv file"""
        dlg = wx.FileDialog(self, wildcard="*.csv", style=wx.SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.model.exportAssignments(path)
        dlg.Destroy()

    def onGrid(self, event):
        """Export solution to a csv file"""
        dlg = wx.FileDialog(self, wildcard="*.csv", style=wx.SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.model.exportToGrid(path)
        dlg.Destroy()

class LoadingPanel(MyPanel):
    def __init__(self, *args, **kwargs):
        MyPanel.__init__(self, *args, **kwargs)
        self.addLoadPaths()

        pub.subscribe(self.assignmentsCalced, "assignments_calced")

    def addLoadPaths(self):
        """Adds widgets to load the data from .txt files"""
        #create a static boxsizer
        load_box = wx.StaticBox(self, label="Step 1: Input Data")
        box_sizer = wx.StaticBoxSizer(load_box, wx.VERTICAL)
        fgs = wx.FlexGridSizer(rows=2, cols=2, vgap=10, hgap=10)
        box_sizer.Add(fgs, proportion=1, flag=wx.EXPAND)

        #actual data handled by a FGS
        self.data_btn = wx.Button(self, label="Load Data")
        self.data_btn.Bind(wx.EVT_BUTTON, self.onLoadData)

        self.assign_btn = wx.Button(self, label="Add Assignments")
        self.assign_btn.Bind(wx.EVT_BUTTON, self.onAddAssignment)
        self.assign_btn.Disable()

        pub.subscribe(self.dataLoaded, "data_loaded")
        
        fgs.Add(self.data_btn, proportion=1, flag = wx.EXPAND)
        fgs.Add(wx.StaticText(self), proportion=1, flag = wx.EXPAND)

        fgs.Add(self.assign_btn)
        btn_label = wx.StaticText(self, label="(optional)")
        new_font = btn_label.GetFont()
        new_font.SetStyle(wx.FONTSTYLE_ITALIC)
        btn_label.SetFont(new_font)
        fgs.Add(btn_label)
        
        
        fgs.Add(wx.StaticText(self), proportion=1, flag = wx.EXPAND)

        self.SetSizerAndFit(box_sizer)

    def onLoadData(self, event):
        """Bring up a directory to load data from a file"""
        pub.sendMessage("status_bar", "")
        dlg = wx.DirDialog(self, "Choose directory containing data:")
        if dlg.ShowModal() == wx.ID_OK:
            rooms_path = join(dlg.GetPath(), 
                    "roomInventory.csv")
            courses_path = join(dlg.GetPath(), 
                    "courseRequests.csv")  
            no_conflicts_path = join(dlg.GetPath(), 
                    "NoConflict.csv")
            b2b_path = join(dlg.GetPath(), 
                    "back2back.csv")
            dlg.Destroy()
            self.model.setData(courses_path, rooms_path, 
                        no_conflicts_path, b2b_path)

    def dataLoaded(self, message):
        """Listener for when data loads"""
        self.assign_btn.Enable()
        self.data_btn.Disable()

    def onAddAssignment(self, event):
        """Add the assignments to all the courses"""
        pub.sendMessage("status_bar", "")
        dlg = wx.FileDialog(self, wildcard="*.csv")
        if dlg.ShowModal() == wx.ID_OK:
            #pubsub errors/warnings
            self.model.addAssignments(dlg.GetPath())
        dlg.Destroy()
 
    def assignmentsCalced(self, message):
        """Listener for the assignments calced event"""
        self.assign_btn.Disable()

class OptimizationPanel(MyPanel):
    def __init__(self, *args, **kwargs):
        MyPanel.__init__(self, *args, **kwargs)
        self.addInputs()

    def addInputs(self):
        """Add the textboxes for the optimization inputs"""
        #create a static boxsizer
        static_box = wx.StaticBox(self, label="Step 2: Optimize")
        box_sizer = wx.StaticBoxSizer(static_box, wx.VERTICAL)
        fgs = wx.FlexGridSizer(rows=4, cols=4, vgap=10, hgap=10)
        box_sizer.Add(fgs, proportion=1, flag=wx.EXPAND)

        fgs.Add(wx.StaticText(self, label="Score Weights"))
        self.prefWghts1 = wx.lib.intctrl.IntCtrl(self, value=10, 
                min=0, max=100, size=(34,22))
        self.prefWghts2 = wx.lib.intctrl.IntCtrl(self, value=10, 
                min=0, max=100, size=(34,22))
        self.prefWghts3 = wx.lib.intctrl.IntCtrl(self, value=10, 
                min=0, max=100, size=(34,22))

        fgs.AddMany([(self.prefWghts1), 
                (self.prefWghts2), 
                (self.prefWghts3)]) 

        fgs.Add(wx.StaticText(self, label="Preferences"))
        self.Prefs = wx.lib.intctrl.IntCtrl(self, value=10, 
                min=0, max=100, size=(34,22))
        fgs.AddMany([ (self.Prefs),
                (wx.StaticText(self)), 
                (wx.StaticText(self)) ])

        fgs.Add(wx.StaticText(self, label="Excess Capacity"))
        self.ExcessCap = wx.lib.intctrl.IntCtrl(self, value=10, 
                min=0, max=100, size=(34,22))
        fgs.AddMany([ (self.ExcessCap),
                (wx.StaticText(self)), 
                (wx.StaticText(self)) ])

        fgs.Add(wx.StaticText(self, label="Congestion"))
        self.CongPenalty = wx.lib.intctrl.IntCtrl(self, value=10, 
                min=0, max=100, size=(34,22))
        fgs.AddMany([ (self.CongPenalty),
                (wx.StaticText(self)), 
                (wx.StaticText(self)) ])

        fgs.Add(wx.StaticText(self, label="Dept. Fairness"))
        self.DeptFairness = wx.lib.intctrl.IntCtrl(self, value=10, 
                min=0, max=100, size=(34,22))
        fgs.AddMany([ (self.DeptFairness),
                (wx.StaticText(self)), 
                (wx.StaticText(self)) ])

        fgs.Add(wx.StaticText(self, label="Back to Back"))
        self.Back2Back = wx.lib.intctrl.IntCtrl(self, value=10, 
                min=0, max=100, size=(34,22))
        fgs.AddMany([ (self.Back2Back),
                (wx.StaticText(self)), 
                (wx.StaticText(self)) ])

        self.optimize_btn = wx.Button(self, label="Optimize")
        self.optimize_btn.Bind(wx.EVT_BUTTON, self.onOptimize)
        fgs.Add(self.optimize_btn)
        
        self.SetSizerAndFit(box_sizer)
        self.Disable()
        
        pub.subscribe(self.enable, "data_loaded")
        pub.subscribe(self.updateWeights, "update_weights")
        
    def enable(self, message):
        """Listener for the Data-Loaded Message"""
        self.Enable()

    def updateWeights(self, message):
        """Listener for the update weights message"""
        prefWeights = [self.prefWghts1.GetValue(), 
                        self.prefWghts2.GetValue(), 
                        self.prefWghts3.GetValue()]

        self.model.setWeights(prefWeights, 
                self.Prefs.GetValue(), 
                self.ExcessCap.GetValue(), 
                self.CongPenalty.GetValue(), 
                self.DeptFairness.GetValue(), 
                self.Back2Back.GetValue())

    def onOptimize(self, event):
        pub.sendMessage("status_bar", "")
        self.model.optimize()



if __name__ == '__main__':
    app = wx.App(False)      
    frame = ClassE()
    
    app.MainLoop()
    
