'''Noddy history file wrapper
Created on 24/03/2014

@author: Florian Wellmann
'''

import time # for header in model generation
import numpy as np
# import numpy as np
# import matplotlib.pyplot as plt

import events


class NoddyHistory():
    """Class container for Noddy history files"""
    
    def __init__(self, history=None):
        """Methods to analyse and change Noddy history files
        
        **Arguments**:
            - *history* = string : Name of Noddy history file
        
        """
        if history is None:
            # generate a new history
            pass
        else:
            # load existing history
            self.load_history(history)
            self.determine_events()
        
    def info(self):
        """Print out model information"""
        # First: check if all information available
        if not hasattr(self, 'extent_x'): self.get_extent()
        if not hasattr(self, 'origin_x'): self.get_origin()
        if not hasattr(self, 'cube_size'): self.get_cube_size()
        if not hasattr(self, 'filename'): self.get_filename()
        if not hasattr(self, 'date_saved'): self.get_date_saved()
        print(60 * "*" + "\n\t\t\tModel Information\n" + 60 * "*")
        print("\n")
        if self.n_events == 0:
            print("The model does not yet contain any events\n")
        else:
            print("This model consists of %d events:" % self.n_events)
            for k,ev in self.events.items():
                print("\t(%d) - %s" % (k,ev.event_type))
                
        print("The model extent is:")
        print("\tx - %.1f m" % self.extent_x)
        print("\ty - %.1f m" % self.extent_y)
        print("\tz - %.1f m" % self.extent_z)
        
        print("The model origin is located at: \n\t(%.1f, %.1f, %.1f)" % (self.origin_x,
                                                                      self.origin_y,
                                                                      self.origin_z))
        
        print("The cubesize for model export is: \n\t%d m" % self.cube_size)
        # and now some metadata
        print("\n")
        print(60 * "*" + "\n\t\t\tMeta Data\n" + 60 * "*")
        print("\n")
        print("The filename of the model is:\n\t%s" % self.filename)
        print("It was last saved (if origin was a history file!) at:\n\t%s\n" % self.date_saved)
        
    def get_origin(self):
        """Get coordinates of model origin and return and store in local variables
        
        **Returns**: (origin_x, origin_y, origin_z)
        """
        for i,line in enumerate(self.history_lines):
            if "Origin X" in line:
                self.origin_x = float(self.history_lines[i].split("=")[1])
                self.origin_y = float(self.history_lines[i+1].split("=")[1])
                self.origin_z = float(self.history_lines[i+2].split("=")[1])
                break
                
        return(self.origin_x, self.origin_y, self.origin_z)
    
    def get_extent(self):
        """Get model extent and return and store in local variables
        
        **Returns**: (extent_x, extent_y, extent_z)
        """
        for i,line in enumerate(self.history_lines):
            if "Length X" in line:
                self.extent_x = float(self.history_lines[i].split("=")[1])
                self.extent_y = float(self.history_lines[i+1].split("=")[1])
                self.extent_z = float(self.history_lines[i+2].split("=")[1])
                break
                
        return(self.extent_x, self.extent_y, self.extent_z)
        
    
    def load_history(self, history):
        """Load Noddy history
        
        **Arguments**:
            - *history* = string : Name of Noddy history file
        """
        self.history_lines = open(history, 'r').readlines()
    
    def determine_events(self):
        """Determine events and save line numbers
        
        .. note:: Parsing of the history file is based on a fixed Noddy output order. 
                  If this is, for some reason (e.g. in a changed version of Noddy) not the case, then
                  this parsing might fail!
        
        """
        self._raw_events = []
        for i,line in enumerate(self.history_lines):
            if "No of Events" in line:
                self.n_events = int(line.split("=")[1])
            elif "Event #" in line:
                event = {}
                event['type'] = line.split('=')[1].rstrip()
                event['num'] = int(line[7:9])
                event['line_start'] = i
                self._raw_events.append(event)       
            # finally: if the definition for BlockOptions starts, the event definition is over
            elif "BlockOptions" in line:
                last_event_stop = i-2
        # now: find the line ends for the single event blocks
        for i,event in enumerate(self._raw_events[1:]):
            self._raw_events[i]['line_end'] = event['line_start']-1
        # now adjust for last event
        self._raw_events[-1]['line_end'] = last_event_stop
        
        
        self.events = {} # idea: create events as dictionary so that it is easier
        # to swap order later!
        # now create proper event objects for these events
        for e in self._raw_events:
            event_lines = self.history_lines[e['line_start']:e['line_end']+1]
            print e['type']
            if 'FAULT' in e['type']:
                ev = events.Fault(lines = event_lines)
                # set specific aspects first
            elif 'FOLD' in e['type']:
                ev = events.Fold(lines = event_lines)
            elif 'UNCONFORMITY' in e['type']:
                ev = events.Unconformity(lines = event_lines)
                
            elif 'STRATIGRAPHY' in e['type']:
                ev = events.Stratigraphy(lines = event_lines)
            else: continue
                
            # now set shared attributes (those defined in superclass Event)
            order = e['num']
            self.events[order] = ev
        
        # determine overall begin and end of the history events
        self.all_events_begin = self._raw_events[0]['line_start']
        self.all_events_end = self._raw_events[-1]['line_end']
       
    def get_cube_size(self):
        """Determine cube size for model export"""
        for line in self.history_lines:
            if 'Geophysics Cube Size' in line: 
                self.cube_size = float(line.split('=')[1].rstrip())
         
    def get_filename(self):
        """Determine model filename from history file/ header"""
        self.filename = self.history_lines[0].split('=')[1].rstrip()
        
    def get_date_saved(self):
        """Determine the last savepoint of the file"""
        self.date_saved = self.history_lines[1].split('=')[1].rstrip()    
    
    def change_cube_size(self, cube_size):
        """Change the model cube size (isotropic)
        
        **Arguments**:
            - *cube_size* = float : new model cube size
        """
        # create local copy of history
        lines_new = self.history_lines[:]
        for i,line in enumerate(self.history_lines):
            if 'Geophysics Cube Size' in line: 
                l = line.split('=')
                l_new = '%7.2f\r\n' % cube_size
                line_new = l[0] + "=" + l_new
                lines_new[i] = line_new
        # assign changed lines back to object
        self.history_lines = lines_new[:]        
        
                
    def write_history(self, filename):
        """Write history to new file
        
        **Arguments**:
            - *filename* = string : filename of new history file
            
        .. hint:: Just love it how easy it is to 'write history' with Noddy ;-)
        
        """
        # before saving: update all event properties (in case changes were made)
        self.update_all_event_properties()
        
        # First step: update history lines with events
        all_event_lines = []
        for event_id in sorted(self.events.keys()):
            for line in self.events[event_id].event_lines:
                all_event_lines.append(line)
        # now substitute old with new lines:
        self.history_lines[self.all_events_begin:self.all_events_end+1] = all_event_lines
        
        
        f = open(filename, 'w')
        for line in self.history_lines:
            f.write(line)
        f.close()
        
        
    def swap_events(self, event_num_1, event_num_2):
        """Swap two geological events in the timeline
        
        **Arguments**:
            - *event_num_1/2* = int : number of events to be swapped ("order")
        """
        # events have to be copied, otherwise only a reference is passed!
        event_tmp = self.events[event_num_1]
        self.events[event_num_1] = self.events[event_num_2]
        self.events[event_num_2] = event_tmp
        self.update_event_numbers()
        
    def reorder_events(self, reorder_dict):
        """Reorder events accoring to assignment in reorder_dict
        
        **Arguments**:
            - *reorder_dict* = dict : for example {1 : 2, 2 : 3, 3 : 1}
        """
        tmp_events = self.events.copy()
        for key, value in reorder_dict.items():
            tmp_events[value] = self.events[key]
        self.events = tmp_events.copy()
        self.update_event_numbers()
        
    def update_event_numbers(self):
        """Update event numbers in 'Event #' line in noddy history file"""
        for key, event in self.events.items():
            event.set_event_number(key)
        
    def update_all_event_properties(self):
        """Update properties of all events - in case changes were made"""
        for event in self.events.values():
            event.update_properties()
        

class NewHistory():
    """Methods to create a Noddy model"""
    
    def __init__(self):
        """Methods to create a Noddy model
        
        """
        # set event counter
        self.event_counter = 0
        self.all_events_begin = 7 # default after header
        self.all_events_end = 7
        # initialise history lines
        self.history_lines = []
        self.events = {}
        
    def get_ev_counter(self):
        """Event counter for implicit and continuous definition of events"""
        self.event_counter += 1
        return self.event_counter
        
    
    def add_event(self, event_type, event_options, **kwds):
        """Add an event type to history
        
        **Arguments**:
            - *event_type* = string : type of event, legal options to date are:
            'stratigraphy', 'fault', 'fold', 'unconformity'
            - *event_options* = list : required options to create event (event dependent)
        **Optional keywords**:
            - *event_num* = int : event number (default: implicitly defined with increasing counter)
        """
        
        event_num = kwds.get("event_num", self.get_ev_counter())
        
        
        if event_type == 'stratigraphy':
            ev = self._create_stratigraphy(event_options)
            ev.event_type = 'STRATIGRAPHY'

        elif event_type == 'fault':
            ev = self._create_fault(event_options)
            ev.event_type = 'FAULT'
        
        else:
            raise NameError('Event type %s not (yet) implemented' % event_type)
        
        ev.set_event_number(event_num)
        self.events[event_num] = ev
            
        # update beginning and ending of events in history
        self.all_events_end = self.all_events_end + len(ev.event_lines)
            
    def _create_header(self):
        """Create model header, include actual date"""
        t = time.localtime() # get current time
        time_string = "%d/%d/%d %d:%d:%d" % (t.tm_mday, 
                                             t.tm_mon, 
                                             t.tm_year,
                                             t.tm_hour,
                                             t.tm_min,
                                             t.tm_sec)
        self.header_lines = """#Filename = """ + self.filename + """ 
#Date Saved = """ + time_string + """
FileType = 111
Version = 7.11

"""
    
    def _create_stratigraphy(self, event_options):
        """Create a stratigraphy event
        
        **Arguments**:
            - *event_options* = list : list of required and optional settings for event
            Options are:
            'num_layers' = int : number of layers (required)
            'layer_names' = list of strings : names for layers (default names otherwise)
            'layer_thickness' = list of floats : thicknesses for all layers
        """
        ev = events.Stratigraphy()
        tmp_lines = [""]
        tmp_lines.append("\tNum Layers\t= %d" % event_options['num_layers'])
        for i in range(event_options['num_layers']):
            """Add stratigraphy layers"""
            layer_name = event_options['layer_names'][i]
            cum_thickness = np.cumsum(event_options['layer_thickness'])
            layer_lines = _Templates().strati_layer
            # now replace required variables
            layer_lines = layer_lines.replace("$NAME$", layer_name)
            layer_lines = layer_lines.replace("$HEIGHT$", "%.1f" % cum_thickness[i])
            layer_lines = layer_lines.replace("    ", "\t")
            # split lines and add to event lines list:
            for layer_line in layer_lines.split("\n"):
                tmp_lines.append(layer_line)
        
        # append event name
        tmp_lines.append("""\tName\t= Strat
""")
        
        # event lines are defined in list:
        tmp_lines_list = []
        for line in tmp_lines:
            tmp_lines_list.append(line + "\n")
        ev.set_event_lines(tmp_lines_list)
        ev.num_layers = event_options['num_layers']
        return ev
    
    def _create_fault(self, event_options):
        """Create a fault event
        
        **Arguments**:
            - *event_options* = list : list of required and optional settings for event;
            Options are:
            'name' = string : name of fault event
            'pos' = (x,y,z) : position of reference point (floats)
                .. note::     for convenience, it is possible to assign 'top' to z
                              for position at "surface"
            'dip_dir' = [0,360] : dip direction of fault
            'dip' = [0,90] : dip angle of fault
            'slip' = float : slip along fault
        """
        ev = events.Fault()
        tmp_lines = [""]
        fault_lines = _Templates.fault
        # substitute text with according values
        fault_lines = fault_lines.replace("$NAME$", event_options['name'])
        fault_lines = fault_lines.replace("$POS_X$", "%.1f" % event_options['pos'][0])
        fault_lines = fault_lines.replace("$POS_Y$", "%.1f" % event_options['pos'][1])
        if event_options['pos'] == 'top':
            # recalculate z-value to be at top of model
            z = self.zmax
            fault_lines = fault_lines.replace("$POS_Z$", "%.1f" % z)
        else:
            fault_lines = fault_lines.replace("$POS_Z$", "%.1f" % event_options['pos'][2])
        fault_lines = fault_lines.replace("$DIP_DIR$", "%.1f" % event_options['dip_dir'])
        fault_lines = fault_lines.replace("$DIP$", "%.1f" % event_options['dip'])
        fault_lines = fault_lines.replace("$SLIP$", "%.1f" % event_options['slip'])
        
        # now split lines and add as list entries to event lines
        # event lines are defined in list:

        # split lines and add to event lines list:
        for layer_line in fault_lines.split("\n"):
            tmp_lines.append(layer_line)

        tmp_lines_list = []
        for line in tmp_lines:
            tmp_lines_list.append(line + "\n")
        ev.set_event_lines(tmp_lines_list)
        return ev
         
        
        
    
    def write_history(self, filename):
        """Write history to new file
        
        **Arguments**:
            - *filename* = string : filename of new history file
            
        .. hint:: Just love it how easy it is to 'write history' with Noddy ;-)
        
        """
        # first: create header
        self.filename = filename
        self._create_header()
        
        # initialise history lines
        history_lines = []
        
        # add header
        for line in self.header_lines.split("\n"):
            history_lines.append(line + "\n")
            
        # add number of events
        history_lines.append("No of Events\t= %d\n" % len(self.events))
        # add events
        for event_id in sorted(self.events.keys()):
            for line in self.events[event_id].event_lines:
                history_lines.append(line)
        
        # add footer
        for line in _Templates().footer.split("\n"):
            line = line.replace("    ", "\t")
            history_lines.append(line + "\n")    
        
        f = open(filename, 'w')
        for line in history_lines:
            f.write(line)
        f.close()
#        print history_lines

        
#        
#        # First step: update history lines with events
#        all_event_lines = []
#        for event_id in sorted(self.events.keys()):
#            for line in self.events[event_id].event_lines:
#                all_event_lines.append(line)
#        # now substitute old with new lines:
#        self.history_lines[self.all_events_begin:self.all_events_end+1] = all_event_lines
#        
#        
#        f = open(filename, 'w')
#        for line in self.history_lines:
#            f.write(line)
#        f.close()
#        
 


#===============================================================================
# Templates for Noddy history file
#===============================================================================

class _Templates():
    
    header = """#Filename = simple_two_faults.his
#Date Saved = 24/3/2014 14:21:0
FileType = 111
Version = 7.11"""

    strati_layer = """    Unit Name    = $NAME$
    Height    = $HEIGHT$
    Apply Alterations    = ON
    Density    = 4.00e+000
    Anisotropic Field    = 0
    MagSusX    = 1.60e-003
    MagSusY    = 1.60e-003
    MagSusZ    = 1.60e-003
    MagSus Dip    = 9.00e+001
    MagSus DipDir    = 9.00e+001
    MagSus Pitch    = 0.00e+000
    Remanent Magnetization    = 0
    Inclination    =  30.00
    Angle with the Magn. North    =  30.00
    Strength    = 1.60e-003
    Color Name    = Color 92
    Red    = 0
    Green    = 153
    Blue    = 48 """
    
    fault = """    Geometry    = Translation
    Movement    = Hanging Wall
    X    = $POS_X$
    Y    = $POS_Y$
    Z    =   $POS_Z$
    Dip Direction    =  $DIP_DIR$
    Dip    =  $DIP$
    Pitch    =  90.00
    Slip    = $SLIP$
    Rotation    =  30.00
    Amplitude    = 2000.00
    Radius    = 1000.00
    XAxis    = 2000.00
    YAxis    = 2000.00
    ZAxis    = 2000.00
    Cyl Index    =   0.00
    Profile Pitch    =  90.00
    Color Name    = Custom Colour 8
    Red    = 0
    Green    = 0
    Blue    = 254
    Fourier Series
        Term A 0    =   0.00
        Term B 0    =   0.00
        Term A 1    =   0.00
        Term B 1    =   1.00
        Term A 2    =   0.00
        Term B 2    =   0.00
        Term A 3    =   0.00
        Term B 3    =   0.00
        Term A 4    =   0.00
        Term B 4    =   0.00
        Term A 5    =   0.00
        Term B 5    =   0.00
        Term A 6    =   0.00
        Term B 6    =   0.00
        Term A 7    =   0.00
        Term B 7    =   0.00
        Term A 8    =   0.00
        Term B 8    =   0.00
        Term A 9    =   0.00
        Term B 9    =   0.00
        Term A 10    =   0.00
        Term B 10    =   0.00
    Name    = Fault Plane
    Type    = 1
    Join Type     = LINES
    Graph Length    = 200.000000
    Min X    = 0.000000
    Max X    = 6.280000
    Min Y Scale    = -1.000000
    Max Y Scale    = 1.000000
    Scale Origin    = 0.000000
    Min Y Replace    = -1.000000
    Max Y Replace    = 1.000000
    Num Points    = 21
        Point X    = 0
        Point Y    = 0
        Point X    = 31
        Point Y    = 30
        Point X    = 62
        Point Y    = 58
        Point X    = 94
        Point Y    = 80
        Point X    = 125
        Point Y    = 94
        Point X    = 157
        Point Y    = 99
        Point X    = 188
        Point Y    = 95
        Point X    = 219
        Point Y    = 81
        Point X    = 251
        Point Y    = 58
        Point X    = 282
        Point Y    = 31
        Point X    = 314
        Point Y    = 0
        Point X    = 345
        Point Y    = -31
        Point X    = 376
        Point Y    = -59
        Point X    = 408
        Point Y    = -81
        Point X    = 439
        Point Y    = -95
        Point X    = 471
        Point Y    = -100
        Point X    = 502
        Point Y    = -96
        Point X    = 533
        Point Y    = -82
        Point X    = 565
        Point Y    = -59
        Point X    = 596
        Point Y    = -32
        Point X    = 628
        Point Y    = -1
    Alteration Type     = NONE
    Num Profiles    = 12
    Name    = Density
    Type    = 2
    Join Type     = LINES
    Graph Length    = 200.000000
    Min X    = 0.000000
    Max X    = 0.000000
    Min Y Scale    = 0.000000
    Max Y Scale    = 4.000000
    Scale Origin    = 1.000000
    Min Y Replace    = 0.000000
    Max Y Replace    = 10.000000
    Num Points    = 2
        Point X    = 0
        Point Y    = -50
        Point X    = 628
        Point Y    = -50
    Name    = Anisotropy
    Type    = 3
    Join Type     = LINES
    Graph Length    = 200.000000
    Min X    = 0.000000
    Max X    = 0.000000
    Min Y Scale    = -10.000000
    Max Y Scale    = 10.000000
    Scale Origin    = 0.000000
    Min Y Replace    = -10.000000
    Max Y Replace    = 10.000000
    Num Points    = 2
        Point X    = 0
        Point Y    = 0
        Point X    = 628
        Point Y    = 0
    Name    = - X Axis (Sus)
    Type    = 4
    Join Type     = LINES
    Graph Length    = 200.000000
    Min X    = 0.000000
    Max X    = 0.000000
    Min Y Scale    = -5.000000
    Max Y Scale    = 5.000000
    Scale Origin    = 0.000000
    Min Y Replace    = 2.000000
    Max Y Replace    = 8.000000
    Num Points    = 2
        Point X    = 0
        Point Y    = 0
        Point X    = 628
        Point Y    = 0
    Name    = - Y Axis (Sus)
    Type    = 5
    Join Type     = LINES
    Graph Length    = 200.000000
    Min X    = 0.000000
    Max X    = 0.000000
    Min Y Scale    = -5.000000
    Max Y Scale    = 5.000000
    Scale Origin    = 0.000000
    Min Y Replace    = 2.000000
    Max Y Replace    = 8.000000
    Num Points    = 2
        Point X    = 0
        Point Y    = 0
        Point X    = 628
        Point Y    = 0
    Name    = - Z Axis (Sus)
    Type    = 6
    Join Type     = LINES
    Graph Length    = 200.000000
    Min X    = 0.000000
    Max X    = 0.000000
    Min Y Scale    = -5.000000
    Max Y Scale    = 5.000000
    Scale Origin    = 0.000000
    Min Y Replace    = 2.000000
    Max Y Replace    = 8.000000
    Num Points    = 2
        Point X    = 0
        Point Y    = 0
        Point X    = 628
        Point Y    = 0
    Name    = - Dip (Sus)
    Type    = 7
    Join Type     = LINES
    Graph Length    = 200.000000
    Min X    = 0.000000
    Max X    = 0.000000
    Min Y Scale    = -180.000000
    Max Y Scale    = 180.000000
    Scale Origin    = 1.000000
    Min Y Replace    = -180.000000
    Max Y Replace    = 180.000000
    Num Points    = 2
        Point X    = 0
        Point Y    = 1
        Point X    = 628
        Point Y    = 1
    Name    = - Dip Dir (Sus)
    Type    = 8
    Join Type     = LINES
    Graph Length    = 200.000000
    Min X    = 0.000000
    Max X    = 0.000000
    Min Y Scale    = -360.000000
    Max Y Scale    = 360.000000
    Scale Origin    = 1.000000
    Min Y Replace    = -360.000000
    Max Y Replace    = 360.000000
    Num Points    = 2
        Point X    = 0
        Point Y    = 0
        Point X    = 628
        Point Y    = 0
    Name    = - Pitch (Sus)
    Type    = 9
    Join Type     = LINES
    Graph Length    = 200.000000
    Min X    = 0.000000
    Max X    = 0.000000
    Min Y Scale    = -360.000000
    Max Y Scale    = 360.000000
    Scale Origin    = 1.000000
    Min Y Replace    = -360.000000
    Max Y Replace    = 360.000000
    Num Points    = 2
        Point X    = 0
        Point Y    = 0
        Point X    = 628
        Point Y    = 0
    Name    = Remanence
    Type    = 10
    Join Type     = LINES
    Graph Length    = 200.000000
    Min X    = 0.000000
    Max X    = 0.000000
    Min Y Scale    = -10.000000
    Max Y Scale    = 10.000000
    Scale Origin    = 0.000000
    Min Y Replace    = -10.000000
    Max Y Replace    = 10.000000
    Num Points    = 2
        Point X    = 0
        Point Y    = 0
        Point X    = 628
        Point Y    = 0
    Name    = - Declination (Rem)
    Type    = 11
    Join Type     = LINES
    Graph Length    = 200.000000
    Min X    = 0.000000
    Max X    = 0.000000
    Min Y Scale    = -360.000000
    Max Y Scale    = 360.000000
    Scale Origin    = 1.000000
    Min Y Replace    = -360.000000
    Max Y Replace    = 360.000000
    Num Points    = 2
        Point X    = 0
        Point Y    = 0
        Point X    = 628
        Point Y    = 0
    Name    = - Inclination (Rem)
    Type    = 12
    Join Type     = LINES
    Graph Length    = 200.000000
    Min X    = 0.000000
    Max X    = 0.000000
    Min Y Scale    = -360.000000
    Max Y Scale    = 360.000000
    Scale Origin    = 1.000000
    Min Y Replace    = -360.000000
    Max Y Replace    = 360.000000
    Num Points    = 2
        Point X    = 0
        Point Y    = 0
        Point X    = 628
        Point Y    = 0
    Name    = - Intensity (Rem)
    Type    = 13
    Join Type     = LINES
    Graph Length    = 200.000000
    Min X    = 0.000000
    Max X    = 0.000000
    Min Y Scale    = -5.000000
    Max Y Scale    = 5.000000
    Scale Origin    = 0.000000
    Min Y Replace    = -5.000000
    Max Y Replace    = 5.000000
    Num Points    = 2
        Point X    = 0
        Point Y    = 0
        Point X    = 628
        Point Y    = 0
    Surface Type    = FLAT_SURFACE
    Surface Filename    =      
    Surface Directory    = \\psf\Home
    Surface XDim    = 0.000000
    Surface YDim    = 0.000000
    Surface ZDim    = 0.000000
    Name    = $NAME$"""
    
    # everything below events
    footer = """#BlockOptions
    Number of Views    = 1
    Current View    = 0
    NAME    = Default
    Origin X    =   0.00
    Origin Y    =   0.00
    Origin Z    = 5000.00
    Length X    = 10000.00
    Length Y    = 7000.00
    Length Z    = 5000.00
    Geology Cube Size    =  50.00
    Geophysics Cube Size    = 100.00

#GeologyOptions
    Scale    =  10.00
    SectionDec    =  90.00
    WellDepth    = 5000.00
    WellAngleZ    =   0.00
    BoreholeX    =   0.00
    BoreholeX    =   0.00
    BoreholeX    = 5000.00
    BoreholeDecl    =  90.00
    BoreholeDip    =   0.00
    BoreholeLength    = 5000.00
    SectionX    =   0.00
    SectionY    =   0.00
    SectionZ    = 5000.00
    SectionDecl    =  90.00
    SectionLength    = 10000.00
    SectionHeight    = 5000.00
    topofile    = FALSE
    Topo Filename    =    
    Topo Directory    = .
    Topo Scale    =   1.00
    Topo Offset    =   0.00
    Topo First Contour    = 100.00
    Topo Contour Interval    = 100.00
    Chair Diagram    = FALSE
    Chair_X    = 5000.00
    Chair_Y    = 3500.00
    Chair_Z    = 2500.00

#GeophysicsOptions
    GPSRange     = 0
    Declination    =   0.00
    Inclination    = -67.00
    Intensity    = 63000.00
    Field Type    = FIXED
    Field xPos    =   0.00
    Field yPos    =   0.00
    Field zPos    = 5000.00
    Inclination Ori    =   0.00
    Inclination Change    =   0.00
    Intensity Ori    =  90.00
    Intensity Change    =   0.00
    Declination Ori    =   0.00
    Declination Change    =   0.00
    Altitude    =  80.00
    Airborne=     FALSE
    Calculation Method    = SPATIAL
    Spectral Padding Type    = RECLECTION_PADDING
    Spectral Fence    = 100
    Spectral Percent    = 100
    Constant Boxing Depth    =   0.00
    Clever Boxing Ratio    =   1.00
    Deformable Remanence=     FALSE
    Deformable Anisotropy=     TRUE
    Vector Components=     FALSE
    Project Vectors=     TRUE
    Pad With Real Geology=     FALSE
    Draped Survey=     FALSE

#3DOptions
    Declination    = 150.000000
    Elevation    = 30.000000
    Scale    = 1.000000
    Offset X    = 1.000000
    Offset Y    = 1.000000
    Offset Z    = 1.000000
    Fill Type    = 2

#ProjectOptions
    Susceptibility Units    = CGS
    Geophysical Calculation    = 2
    Calculation Type    = LOCAL_JOB
    Length Scale    = 0
    Printing Scale    = 1.000000
    Image Scale    = 10.000000
    New Windows    = FALSE
    Background Red Component    = 254
    Background Green Component    = 254
    Background Blue Component    = 254
    Internet Address    = 255.255.255.255
    Account Name    =       
    Noddy Path    = ./noddy
    Help Path    = iexplore %h
    Movie Frames Per Event    = 3
    Movie Play Speed    =  10.00
    Movie Type    = 0
    Gravity Clipping Type    = RELATIVE_CLIPPING
    Gravity Image Display Clip Min    = 0.000000
    Gravity Image Display Clip Max    = 100.000000
    Gravity Image Display Type    = GREY
    Gravity Image Display Num Contour    = 25
    Magnetics Clipping Type    = RELATIVE_CLIPPING
    Magnetics Image Display Clip Min    = 0.000000
    Magnetics Image Display Clip Max    = 100.000000
    Magnetics Image Display Type    = GREY
    Magnetics Image Display Num Contour    = 25
    False Easting    = 0.000000
    False Northing    = 0.000000

#Window Positions
    Num Windows    = 16
    Name    = Block Diagram
    X    = 60
    Y    = 60
    Width    = 500
    Height    = 300
    Name    = Movie
    X    = 60
    Y    = 60
    Width    = -1
    Height    = -1
    Name    = Well Log
    X    = 60
    Y    = 60
    Width    = 400
    Height    = 430
    Name    = Section
    X    = 14
    Y    = 16
    Width    = 490
    Height    = -1
    Name    = Topography Map
    X    = 60
    Y    = 60
    Width    = 490
    Height    = 375
    Name    = 3D Topography Map
    X    = 60
    Y    = 60
    Width    = 490
    Height    = 375
    Name    = 3D Stratigraphy
    X    = 60
    Y    = 60
    Width    = 490
    Height    = 375
    Name    = Line Map
    X    = 60
    Y    = 60
    Width    = 490
    Height    = -1
    Name    = Profile - From Image
    X    = 60
    Y    = 60
    Width    = 490
    Height    = 600
    Name    = Sterographic Projections
    X    = 60
    Y    = 60
    Width    = 430
    Height    = 430
    Name    = Stratigraphic Column
    X    = 60
    Y    = 60
    Width    = 230
    Height    = 400
    Name    = Image
    X    = 30
    Y    = 30
    Width    = -1
    Height    = -1
    Name    = Contour
    X    = 30
    Y    = 30
    Width    = -1
    Height    = -1
    Name    = Toolbar
    X    = 10
    Y    = 0
    Width    = -1
    Height    = -1
    Name    = History
    X    = 229
    Y    = 160
    Width    = 762
    Height    = 898
    Name    = History
    X    = 229
    Y    = 160
    Width    = 762
    Height    = 898

#Icon Positions
    Num Icons    = 3
    Row    = 1
    Column    = 1
    X Position    = 1
    Y Position    = 1
    Row    = 1
    Column    = 2
    X Position    = 4
    Y Position    = 1
    Row    = 1
    Column    = 3
    X Position    = 7
    Y Position    = 1
    Floating Menu Rows    = 1
    Floating Menu Cols    = 24
End of Status Report"""


        
if __name__ == '__main__':
    # some testing and debugging:
    import os
    os.chdir(r'/Users/Florian/git/pynoddy/sandbox')
    H1 = NoddyHistory("../examples/simple_two_faults.his")
    H1.swap_events(2, 3)
    H1.write_history("test")
    H2 = NoddyHistory("test")
    H2.events[2].properties['Dip'] = 12
    H2.write_history("test2")
        
        
        
        
        
        
        
        
        
        
        
        
        
