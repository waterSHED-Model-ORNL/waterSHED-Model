# -*- coding: utf-8 -*-
"""
Last updated on April 25 2022

@author: Colin Sasthav
"""

#%%## Tips for syntax 
#The user interface relies on the Tkinter package.
#Each TopLevel and Frame object will have a section where the input objects are created and a section where the objects are packed (i.e., placed in the parent frame)
#Whenever an object requires a set of inputs from the GUI, a dict is used to parameterize the input
#The dict has the following structure: key=Attribute Name: [[entry type], unit, cast, support_tool, is_optional boolean]

#%%## IMPORT PACKAGES
import tkinter as tk
from tkinter import ttk 
import webbrowser
import pandas as pd
import queue
import threading
import module_classes as mc
import dynamic_modules as dm
import aux_functions as af
import case_study_functions as csf
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tksheet as tksheet
import numpy as np
import waterSHED_styles as styles
import os
from openpyxl import load_workbook
import time
import math
#%%## Styles
#Colors
TITLE_BG_COLOR = styles.TITLE_BG_COLOR
SUBTITLE_BG_COLOR = styles.SUBTITLE_BG_COLOR
LINK_FG_COLOR =  styles.LINK_FG_COLOR
SIDEBAR_BG_COLOR =  styles.SIDEBAR_BG_COLOR 
FRAME_BG_COLOR =  styles.FRAME_BG_COLOR
LABEL_BG_COLOR =  styles.LABEL_BG_COLOR
DYNAMIC_MODULE_BG_COLOR =  styles.DYNAMIC_MODULE_BG_COLOR
CHECK_BG_COLOR =  styles.CHECK_BG_COLOR
DIRECTIONS_BG_COLOR =  styles.DIRECTIONS_BG_COLOR
MODULE_COLORS =  styles.MODULE_COLORS
DYNAMIC_BOX_COLOR = styles.DYNAMIC_BOX_COLOR
# Fonts
PG_TITLE_FONT = styles.PG_TITLE_FONT
TEXT_FONT = styles.TEXT_FONT
TEXT_BOLD_FONT = styles.TEXT_BOLD_FONT
SUBTITLE_FONT = styles.SUBTITLE_FONT
LINK_FONT = styles.LINK_FONT
TEXT_ITALIC_FONT = styles.TEXT_ITALICS_FONT

plt.rcParams.update({'figure.max_open_warning': 0})
#%%## MAIN TKINTER APP
class tkinterApp(): 
    def __init__(self, master):  
        self.master = master
        self.page_name = 'Master'
        
        #waterSHED class instances - these instances will be created via the GUI
        self.mod_lib = mc.Module_library()
        self.costs = None
        self.site = None
        self.preferences = None
        self.proj = None
        self.opt_facs = [] #List of optimal facilities
        self.enum_res = [] #List of enumeration results, including [fac, sim_res, results_df]
        self.species_list = [] #List of Species objects
        self.saved_sim_results = [] #List of saved SimResults objects
        
        #Dimension parameters used to change scale of the window
        self.canvas_width = 870
        self.canvas_height = 800
        self.wrap_length = 850
        self.check_width = 8
    
        #Tkinter creating main window
        self.master.title('waterSHED 2.0 - Water Allocation Tool Enabling Rapid Small Hydropower Environmental Design')
        self.container = tk.Frame(master, bg = FRAME_BG_COLOR)   
        self.container.pack(fill = "both", expand = True)  
        self.container.rowconfigure(0, weight = 1) 
        self.container.columnconfigure(0, weight = 1)
        self.menubar = MenuBar(master)
        self.master.config(menu=self.menubar)
        self.canvas = tk.Canvas(self.container, width=self.canvas_width,height=self.canvas_height, bg=FRAME_BG_COLOR)
        self.scrollbar = tk.Scrollbar(self.container, orient='vertical', command=self.canvas.yview)
        self.mainframe = tk.Frame(self.canvas, bg=FRAME_BG_COLOR)
        self.canvas_frame = self.canvas.create_window((0,0), anchor='nw', window=self.mainframe)
        self.canvas.grid_columnconfigure(1, weight=1)        
        self.mainframe.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.configure(scrollregion=self.canvas.bbox("all"), yscrollcommand=self.scrollbar.set)
        self.canvas.bind('<Configure>', self.FrameWidth)
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)

        #List of pages
        self.pages = (StartPage, SitePage, AddModulePage,AddDynamicModulePage, AddScreenPage, FishPage, CostsPage, PreferencesPage, EnumeratePage, OptimizePage)
            
        #Creates frames for each page
        self.frames = {}   
        for F in self.pages: 
            frame = F(self.mainframe, self) 
            self.frames[F] = frame  
            frame.grid(row = 0, column = 0, sticky ="nsew", padx=2.5, pady=5) 
            frame.grid_columnconfigure(0, weight=1)
        self.show_frame(StartPage) 
   
        #Packing main window objects
        self.sidebar = SideBar(self.container, self)     
        self.sidebar.pack(side='left', fill='y', expand=False)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scrollbar.pack(side='right', expand=False, fill='y')
        
        #Set the Icon - Source: https://www.clipartkey.com/view/bTJJh_transparent-wave-border-png-water-flow-icon/
        self.img = Image.open("Images\\Water_Icon.png")
        self.p1 = ImageTk.PhotoImage(self.img, master=self.master)
        self.master.iconphoto(False, self.p1)

    #Checks if inputs are correct and then creates a SMH_Project instance and runs the genetic algorithm optimization from the Project class
    def optimize_facility(self, enum_lists, objective, constraints, iterations, pop_size, best_num, mut_num, random_num, cross_num, show_anim):
        if self.check_complete:
            try:
                if len(self.species_list) > 0:
                    species = self.species_list
                else:
                    species = None
                self.proj = mc.SMH_project(self.site, self.costs, self.preferences, self.mod_lib, species_list=species)
                self.opt_facs = self.proj.optimize(objective, constraints, enum_lists, iterations=iterations, population_size=pop_size, best_count=best_num, mutate_count=mut_num, random_count=random_num, cross_num=cross_num, show_anim=show_anim)
                self.frames[OptimizePage].optimization_complete()
                tk.messagebox.showinfo("Success", "Successfully optimized the facility design")
            except:
                tk.messagebox.showerror('Error', 'Unknown error during optimization process.')

    #Checks if the inputs are correct and then runs the enumeration optimization through the Project class
    def enumerate_facility(self, objective, enum_lists, save_bools, show_anim):
        if self.check_complete:
            try:
                if len(self.species_list) > 0:
                    species = self.species_list
                else:
                    species = None
                self.proj = mc.SMH_project(self.site, self.costs, self.preferences, self.mod_lib, species_list=species)
                start_time = time.perf_counter()
                self.enum_res = self.proj.enumeration_optimization(objective, enum_lists, save_bools,show_anim=show_anim)
                end_time = time.perf_counter()
                self.enum_res 
                if self.enum_res is False:
                    tk.messagebox.showerror('Error', 'Unable to enumerate the facility, make sure the enumeration parameters for any dynamic modules are feasible.')
                    return False
                if len(self.saved_sim_results) <= 0:
                    self.saved_sim_results = self.enum_res[2]
                else:
                    self.saved_sim_results = pd.merge(self.saved_sim_results, self.enum_res[2], on='Metric', sort=False, how='outer')
                self.frames[EnumeratePage].enumeration_complete()
                tk.messagebox.showinfo("Success", "Successfully enumerated the facility design. Total time = {} seconds".format(round(end_time-start_time, 2)))
            except:
                tk.messagebox.showerror('Error', 'Unknown error during enumeration process.')
        else:
            tk.messagebox.showerror('Error', 'All required objects must be created before running sensitivity analysis.')
            return False
        
    #Checks if inputs are correct, then runs through each sensitivity case using the appropriate optimization function
    def sensitivity_analysis(self, obj, variable_name, iterations, dict_key=None, unit_type=None): 
        if self.check_complete:
            try:
                results_df = None
                enum_params = self.frames[EnumeratePage].get_enumeration_parameters()
                if enum_params is False:
                    tk.messagebox.showerror('Error', 'Please ensure proper inputs on the enumeration page.')
                    return False
                
                #Get species
                if len(self.species_list) > 0:
                    species = self.species_list
                else:
                    species = None
                #Determine variable iteration
                iters = list(np.arange(iterations['Min'], iterations['Max'], iterations['Step']))
                iters = np.append(iters, iterations['Max'])
                for i in iters:
                    #Set sensitivity variable
                    iter_name = variable_name + ' - ' + str(i)
                    if dict_key is not None:
                        getattr(obj, variable_name)[dict_key] = i
                    elif unit_type  == 'Discount Equation':
                        getattr(obj, variable_name).set_discount_factor(i)
                    else:    
                        setattr(obj, variable_name, i)
                    #Run enumeration
                    proj = mc.SMH_project(self.site, self.costs, self.preferences, self.mod_lib, species_list=species)
                    enum_res = proj.enumeration_optimization(*enum_params) #enum_res includes [best_fac, best_sim_res, results_df]
                    if enum_res is False: #If enumeration is unsuccessful, then output a placeholder results_dict
                        results_dict = {'Enumeration Objective': 'Unsucessful', variable_name: i}
                        temp_df = pd.DataFrame.from_dict(results_dict, orient='index', columns=[iter_name]).reset_index()
                        temp_df.rename(columns={'index':'Metric'},inplace=True)
                    else: #If enumeration is successful, then save results
                        best_sim_res = enum_res[1]
                        results_dict = best_sim_res.get_run_dict(*enum_params[3])
                        results_dict['Enumeration Objective'] = best_sim_res.obj_dict[enum_params[0]]
                        results_dict[variable_name] = i
                        temp_df = pd.DataFrame.from_dict(results_dict, orient='index', columns=[iter_name]).reset_index()
                        temp_df.rename(columns={'index':'Metric'},inplace=True)
                    if results_df is None:
                        results_df = temp_df
                    else:
                        results_df = pd.merge(results_df, temp_df, on='Metric', sort=False, how='outer')
                self.sens_results = results_df
                if len(self.saved_sim_results) <= 0:
                    self.saved_sim_results = self.sens_results
                else:
                    self.saved_sim_results = pd.merge(self.saved_sim_results, self.sens_results, on='Metric', sort=False, how='outer')
                self.frames[EnumeratePage].sensitivity_complete(variable_name)
                tk.messagebox.showinfo("Success", "Successfully conducted sensitivity analysis")
            except:
                tk.messagebox.showerror('Error', 'Unknown error during sensitivity analysis.')
        else:
            tk.messagebox.showerror('Error', 'All required objects must be created before running sensitivity analysis.')
            return False
    
    #Checks if all of the required objects have been created for the SMH Project object
    def check_complete(self):
        if type(self.costs) == list:
            tk.messagebox.showerror('Error', 'Please make sure to submit cost info')
        elif type(self.site) == list:
            tk.messagebox.showerror('Error', 'Please make sure to submit site info')
        elif type(self.preferences) == list:
            tk.messagebox.showerror('Error', 'Please make sure to submit preferences')
        elif self.mod_lib.check_complete() == False:
            tk.messagebox.showerror('Error', 'Please make sure to have at least a water passage, a non-overflow, and a foundation module present in the module library.')
        else:
            return True
        return False        
        
    #Runs the waterSHED workbook window, the input while call data_uploaded function
    def import_watershed_workbook(self, import_type):
        self.import_type = import_type
        self.csv_window = csvUploadWindow(self, self, ['xlsx', 'Workbooks/waterSHED_Workbook', 'Preferences'], just_file_name=True)
        
    #When the waterSHED import filename is given, this function runs and cretes the imported objects
    def data_uploaded(self, file_name, import_type=None):
        if import_type is not None:
            self.import_type = import_type
        file_name = file_name + '.xlsx'
        imported_vals = import_from_workbook(file_name, self.import_type)
        if (type(imported_vals) == str):
            tk.messagebox.showerror('Error', imported_vals)
            return 
        try:
            if self.import_type == 'Preferences':
                self.preferences = imported_vals
                self.preferences_added()
            elif self.import_type == 'Costs':
                self.costs = imported_vals
                self.costs_added()
            elif self.import_type == 'Site':
                self.site = imported_vals
                self.site_added()
            elif self.import_type == 'Module Library':
                for mod in imported_vals:
                    if mod.name not in self.mod_lib.get_name_list():
                        self.mod_lib.add_static(mod)
                self.mods_added()
            elif self.import_type == 'All':
                for i in imported_vals:
                    if type(i) == str:
                        tk.messagebox.showerror('Error', i)
                        return
                self.site = imported_vals[0]
                self.costs = imported_vals[1]
                self.preferences = imported_vals[2]
                for mod in imported_vals[3]:
                    if mod.name not in self.mod_lib.get_name_list():
                        self.mod_lib.add_static(mod)
                for spec in imported_vals[4]:
                    self.species_list.append(spec)
                self.mods_added()
                self.site_added()
                self.costs_added()
                self.preferences_added()
                if len(self.species_list) > 0:
                    self.species_added()               
            tk.messagebox.showinfo('Success', 'Successfully imported all objects from the waterSHED Workbook!')
        except:
            tk.messagebox.showerror('Error', 'There was an error while importing the waterSHED Workbook. Please ensure that all inputs are formatted properly.')
                   
    #Gets the data used for the case studies
    def get_case_studies(self, case_name):
        if case_name in ['Deerfield', 'Housatonic', 'Schuylkill']:
            self.mod_lib.clear_static()
            self.mod_lib.clear_dynamic()
            self.data_uploaded('Workbooks/waterSHED_Workbook_'+case_name, import_type='All') #Import all defaults from workbook
            mods = csf.get_default_modules(case_name)
            for m in mods:
                self.mod_lib.add_dynamic(m)
            self.mods_added()
        
    #Helpful Tkinter functions
    def FrameWidth(self, event):
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_frame, width=canvas_width)
    def show_frame(self, cont): 
        frame = self.frames[cont] 
        frame.tkraise() 
        self.canvas.yview_moveto(0) #Resets view to top on frame switch
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    def busy(self, text):
        self.popup = busywindow(self, text)
        self.master.config(cursor="watch")
        self.master.update()
    def notbusy(self):
        self.popup.cleanup()
        self.master.config(cursor="")
        self.master.update() 
      
    #Update functions
    def mods_added(self):
        self.frames[AddModulePage].mod_lib_frame.update()
        self.frames[AddDynamicModulePage].mod_lib_frame.update()
        self.frames[EnumeratePage].update_mod_select_frame()
        self.frames[OptimizePage].update_mod_select_frame()
        self.frames[FishPage].update_fish_eff_frame()
        self.frames[AddScreenPage].update_cover_mod_frame()
        self.frames[OptimizePage].constraints_frame.pack_con_input_frame()
    def site_added(self):
        self.frames[SitePage].site_added()
    def costs_added(self):
        self.frames[CostsPage].costs_added()
    def species_added(self):
        self.frames[FishPage].species_updated()
    def preferences_added(self):
        self.frames[PreferencesPage].preferences_added()
    def screen_added(self):
        self.frames[EnumeratePage].update_mod_select_frame()
        self.frames[FishPage].update_fish_eff_frame()
        self.frames[AddScreenPage].update_cover_mod_frame()
        self.frames[AddScreenPage].screen_lib.update()        
        self.frames[OptimizePage].constraints_frame.pack_con_input_frame()
    def dynamic_updated(self):
        self.mod_lib.update()
        self.mods_added()
    def save_run(self, sim_res_dict, run_name):
        temp_df = pd.DataFrame.from_dict(sim_res_dict, orient='index', columns=[run_name]).reset_index()
        temp_df.rename(columns={'index':'Metric'},inplace=True)
        if len(self.saved_sim_results) <= 0:
            self.saved_sim_results = temp_df
        else:
            self.saved_sim_results = pd.merge(self.saved_sim_results, temp_df, on='Metric', sort=False, how='outer')
    def clear_runs(self):
        self.saved_sim_results = []
            

#%%## SURROUNDING TKINTER CLASSES
#Menu button that currently only has an exit function
class MenuBar(tk.Menu):
    def __init__(self, parent):
        tk.Menu.__init__(self, parent)
        self.parent = parent
        fileMenu = tk.Menu(self, tearoff=False)
        self.add_cascade(label="File",underline=0, menu=fileMenu)
        fileMenu.add_command(label="Exit", underline=1, command=self.onExit)

    def onExit(self):
        self.parent.destroy()
#Side bar (green) that has the buttons for each page
class SideBar(tk.Frame):
    def __init__(self, parent, controller):  
        tk.Frame.__init__(self, parent, bg=SIDEBAR_BG_COLOR)
        btn_pad_x = 5
        btn_pad_y = 5
        self.buttons = []
        i = 0
        for F in controller.frames:
            new_button = tk.Button(self, bg='white',width=15, text=controller.frames[F].page_name, command = lambda x=F:controller.show_frame(x))
            new_button.grid(row=i, column=0, padx=btn_pad_x, pady=btn_pad_y)
            self.buttons.append(new_button)
            i = i + 1

#%%## START PAGE - Presents the directions for using the tool       
class StartPage(tk.Frame): 
    def __init__(self, parent, controller):  
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR) 
        self.controller = controller
        self.page_name = 'Start'  
        
        self.welcome_txt = 'Welcome to the waterSHED Model! This tool will allow you to simulate and optimize a virtual Modular Hydropower Facility. To accomplish this you will need to input several things: site characteristics, modules, cost tables, facility parameters, and simulation parameters. Once those have been input, you can run the model, visualize your data, and plot the results. Please see the Technical Manual and User Guide for background information and instructions. Questions and comments can be directed to smh@ornl.gov.'
        self.instr_txt = 'Instructions\n\n1. Go through each tab and follow the provided directions.\n\n2. Through this process you will create and characterize several components that are used to create an SMH project, including a Site, a Module Library, Cost Tables, and Facility Preferences.\n\n3. Once these components have been successfully created you can use either the Customize tab to create a facility by hand or the Optimize tab which uses a genetic algorithm procedure create an optimal facility according to your inputs.\n\n4. Once the facility has been created and simulation, you can view the facility and simulated operation in the Results section on the respective pages.\n\n5.Finally, results and inputs can be exported as csv files. The inputs can be integrated (via copy and paste) into the waterSHED Workbook file that can be used to quickly upload information.\n\nTo upload all information from the waterSHED Workbook, please press the button below.'
        self.case_txt = 'To upload data from a previous case study, please select a case study below and press the upload button.'
        self.img = Image.open("Images\\waterSHED_Logo_transparent.png")
        self.img = self.img.resize((830, 250), Image.ANTIALIAS)
        self.ph_img = ImageTk.PhotoImage(self.img, master=self.controller.master)

        self.page_title = tk.Label(self, text = self.page_name, font = PG_TITLE_FONT, bg=TITLE_BG_COLOR) 
        self.welcome_lbl = tk.Label(self, text = self.welcome_txt, font = TEXT_FONT, wraplength=self.controller.wrap_length, justify="left", bg=LABEL_BG_COLOR)
        self.instr_lbl = tk.Label(self, text = self.instr_txt, font = TEXT_FONT, wraplength=self.controller.wrap_length, justify="left", bg=LABEL_BG_COLOR)
        self.image_lbl = tk.Label(self, image = self.ph_img, wraplength=self.controller.wrap_length, justify="center", bg=LABEL_BG_COLOR)
        self.case_instr = tk.Label(self, text = self.case_txt, font = TEXT_FONT, wraplength=self.controller.wrap_length, justify="left", bg=LABEL_BG_COLOR)
        self.wbook_btn = tk.Button(self, text='Import from waterSHED Workbook', font=TEXT_FONT, command=lambda:self.upload_all_workbook())

        self.case_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.case_lbl = tk.Label(self.case_frame, text='Select a case study', font=TEXT_FONT, bg=LABEL_BG_COLOR)
        self.menu_opts = ['Deerfield', 'Housatonic', 'Schuylkill']
        self.case_var = tk.StringVar()
        self.case_menu = tk.OptionMenu(self.case_frame, self.case_var, *self.menu_opts)
        self.case_var.set(self.menu_opts[0])
        self.case_btn = tk.Button(self.case_frame, text='Upload', font=TEXT_FONT, command=lambda:self.upload_case_study())
        self.case_lbl.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
        self.case_menu.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
        self.case_btn.grid(row=0, column=2, padx=5, pady=5, sticky='nsew')
        
        self.page_title.pack(fill='x') 
        self.welcome_lbl.pack(padx=5, pady=5)
        self.image_lbl.pack(padx=5, pady=5)
        self.instr_lbl.pack(padx=5)
        self.wbook_btn.pack(padx=5)
        self.case_instr.pack(padx=0)
        self.case_frame.pack(padx=5)
        
    def upload_all_workbook(self):
        self.controller.import_watershed_workbook('All')
    def upload_case_study(self):
        case_name = self.case_var.get()
        self.controller.get_case_studies(case_name)
        

#%%## SITE PAGE - Collects relevant site characteristics and flow-stage data
class SitePage(tk.Frame):       
    def __init__(self, parent, controller): 
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR) 
        self.page_name = 'Site Inputs'  
        self.controller = controller
        self.columnconfigure((0), weight=1)
        
        self.page_title = tk.Label(self, text =self.page_name, font = PG_TITLE_FONT, bg=TITLE_BG_COLOR) 
        self.directions_txt = 'Directions: This page allows you to input data describing your site. In addition to basic site characteristics like name and width, you must upload daily flow data, stage-discharge data, and peak flow data. These datasets can be uploaded via csv or automatically retrieved from USGS.'
        self.directions_lbl = tk.Label(self, text =self.directions_txt, font = TEXT_FONT, bg=DIRECTIONS_BG_COLOR, justify='left', anchor='w', wraplength=self.controller.wrap_length) 
        self.import_btn = tk.Button(self, text='Import from waterSHED Workbook', font=TEXT_FONT, command=lambda:self.controller.import_watershed_workbook('Site'))
        self.site_title = tk.Label(self, text ='Site Characteristics', font = SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR) 
        self.siteFrame = sitedataFrame(self, self.controller)
        self.inflow_title = tk.Label(self, text ='Daily Inflow Timeseries Data', font = SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR) 
        self.inflow_frame = inflowFrame(self, self.controller)
        self.peak_title = tk.Label(self, text ='*Historical Peak Flows', font = SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.peak_frame = peakFrame(self, self.controller)
        self.submit_btn = tk.Button(self, text='Submit Site Characteristics',font=TEXT_FONT, command=lambda:self.create_site())
        
        self.page_title.grid(row=0, column=0, padx=0, pady=0, sticky='nsew')
        self.directions_lbl.grid(row=1, column=0, padx=0, pady=5, sticky='nsew')
        self.import_btn.grid(row=2, column=0, padx=0, pady=5)
        self.site_title.grid(row=3, column=0, padx=0, pady=5, sticky='nsew')
        self.siteFrame.grid(row=4, column=0, padx=0, pady=5)
        self.inflow_title.grid(row=5, column=0, padx=0, pady=5, sticky='nsew')
        self.inflow_frame.grid(row=6, column=0, padx=0, pady=5, sticky='nsew')
        self.peak_title.grid(row=7, column=0, padx=0, pady=5, sticky='nsew')
        self.peak_frame.grid(row=8, column=0, padx=0, pady=5, sticky='nsew')
        self.submit_btn.grid(row=9, column=0, padx=0, pady=5, sticky='nsew')
        
    def site_added(self):
        self.siteFrame.site_added()
        self.inflow_frame.site_added()
        self.peak_frame.site_added()
        
    def create_site(self):
        site_dict = get_values(self.siteFrame)
        if site_dict is False:
            return 'Site data not uploaded properly'
        daily_inflow = self.inflow_frame.get_data()
        if daily_inflow is False:
            return 'Daily flow data not uploaded.'
        peak_flows = self.peak_frame.get_data()
        if peak_flows is False:
                peak_flows = None
        self.controller.site = mc.Site(site_dict['Site Name'], site_dict['Stream Width'], daily_inflow, \
             site_dict['Stage-Discharge Curve'],  site_dict['Stage-Storage Curve'], site_dict['Stream Slope'],site_dict['Trap Efficiency Parameter'], peak_flows=peak_flows, bed_elevation=site_dict['Dam Bed Elevation'])
        self.controller.site_added()
        tk.messagebox.showinfo('Successful', 'Successfully created the SMH project site!')
        return             


#%%## SITE DATA FRAME - Collects site data
class sitedataFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.controller = controller
        self.page_name = 'Site Data'
        self.entry_width = 20
        
        #key=Attribute Name: [entry type], unit, cast, support_tool, is_optional boolean
        self.input_dict = {'Site Name':[['text entry'], '', [str], [], False], \
                        'Stream Width': [['text entry'], 'ft', [float], ['Tool Tip - Use Google Earth'], False], \
                        'Dam Bed Elevation': [['text entry'], 'ft amsl', [float], [], True], \
                        'Stream Slope': [['text entry'], 'ft/ft', [float], ['Stream Slope Data'], True], \
                        'Trap Efficiency Parameter': [['text entry'], 'unitless', [float], ['Trap Efficiency Model'], True], \
                        'Stage-Discharge Curve': [['Equation', ['Inflow vs. Tailwater', 'Inflow (cfs)', 'Tailwater elevation (ft)', 'Stage']], '', [], ['Stage-Discharge Download'], False], \
                        'Stage-Storage Curve': [['Equation',['Headwater Level vs. Reservoir Volume','Headwater Level (ft)','Reservoir Volume (ft3)', '']], '', [], ['Geometric Reservoir Approach'], True]}
        
        self.att_labels, self.att_entries, self.att_units, self.att_tools, self.input_vars = create_inputs(self, self, self.input_dict, self.entry_width)
        pack_attributes(self, self, row_counter=0)
                
    def site_added(self):
        mysite = self.controller.site
        site_df = mysite.get_df().reset_index()
        for key in self.input_dict:
            if self.input_dict[key][0][0] == 'text entry':
                val = site_df[site_df['Attribute'] == key]['Value'].iloc[0]
                if val is not None:
                    clear_entries([self.att_entries[key]])
                    self.att_entries[key].insert(0, str(val))
        if mysite.reservoir_eq is not None:
            self.att_entries['Stage-Storage Curve'].update_equation(mysite.reservoir_eq)
        self.att_entries['Stage-Discharge Curve'].update_equation(mysite.stage_eq)
                  
    #Takes the values from the support tools and inputs it into the proper entry
    def import_from_tool(self, tool_name, out_var):
        if tool_name == 'Geometric Reservoir Approach':
            self.att_entries['Stage-Storage Curve'].update_equation(out_var)
        elif tool_name == 'Stage-Discharge Download':
            self.att_entries['Stage-Discharge Curve'].update_equation(out_var)

#%%## DAILY INFLOW FRAME - Gets Daily Flow information from USGS
class inflowFrame(tk.Frame):
    def __init__(self, parent, controller): 
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.button_width = 20
        self.page_name = 'Daily Results'
        self.controller = controller 
        self.flow_data = None
        self.columnconfigure((0,1,2), weight=1)
        plt.ioff()
        self.fig = plt.figure(figsize=(6,5))
        self.ax = self.fig.add_subplot(111)
        self.prob = 30

        self.option_lbl = tk.Label(self, text='Please select a data upload option', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.auto_btn = tk.Button(self, text='USGS Download', font=TEXT_FONT, command=lambda:self.auto_retrieval())
        self.csv_btn = tk.Button(self, text='Excel/CSV Upload', font=TEXT_FONT, command=lambda:self.csv_retrieval())
        
        self.option_lbl.grid(row=0, column=0,padx=5, pady=5, sticky='nsew')
        self.auto_btn.grid(row=0, column=1,padx=5, pady=5, sticky='nsew')
        self.csv_btn.grid(row=0, column=2,padx=5, pady=5, sticky='nsew')

    def site_added(self):
        self.flow_data = self.controller.site.daily_inflow
        self.update_results()
        
    #Updates the figure area when new data is added
    def update_results(self): 
        self.right_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.right_frame.columnconfigure((0), weight=1)
        self.fig_lbl = tk.Label(self.right_frame, text='View Options', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.fig_var = tk.StringVar()
        self.fig_options = ['Flow Duration','Daily', 'Monthly', 'Mean Annual','Total Annual']
        self.fig_var.trace('w', self.on_option_switch)
        self.fig_menu = tk.OptionMenu(self.right_frame, self.fig_var, *self.fig_options)
        self.table_btn = tk.Button(self.right_frame,text='View Table', font=TEXT_FONT, command=lambda:self.view_table())
        self.canvas_fig = FigureCanvasTkAgg(self.fig, master=self)
        self.pop_btn = tk.Button(self.right_frame, text='Pop-out Figure', font=TEXT_FONT, command=lambda:self.pop_figure())
        self.Qfind_frame = QFinderFrame(self, self.controller, self.flow_data)
        
        self.canvas_fig.get_tk_widget().grid(row=1,rowspan=2, column=0, columnspan=2, padx=0, pady=5, sticky='nsew')
        self.right_frame.grid(row=1, column=2, padx=5, pady=5, sticky='nsew')
        self.Qfind_frame.grid(row=2, column=2, padx=5, pady=5, sticky='nsew')
        
        self.fig_lbl.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
        self.fig_menu.grid(row=1, column=0, padx=5, pady=5, sticky='nsew')
        self.table_btn.grid(row=2, column=0, padx=5, pady=5, sticky='nsew')
        self.pop_btn.grid(row=3, column=0, padx=5, pady=5, sticky='nsew')
        
        self.fig_var.set(self.fig_options[0])
    
    #Changes the plot when the option menu changes 
    def on_option_switch(self, name=0, indx=0, op=0):
        if type(self.flow_data) != list:
            self.ax.clear()
            fig_type = self.fig_var.get()
            if fig_type == 'Daily':
                fig, self.ax = self.flow_data.get_flow_timeseries_plot(self.fig, self.ax)
            elif fig_type == 'Monthly':
                fig, self.ax = self.flow_data.get_average_month_plot(self.fig, self.ax)
            elif fig_type == 'Mean Annual':
                fig, self.ax = self.flow_data.get_mean_annual_plot(self.fig, self.ax)
            elif fig_type == 'Total Annual':
                fig, self.ax = self.flow_data.get_total_annual_plot(self.fig, self.ax)
            elif fig_type == 'Flow Duration':
                fig, self.ax = self.flow_data.get_flow_duration_plot(self.fig, self.ax, prob=self.prob)
            self.fig.canvas.draw()
            self.canvas_fig.draw()

        
    def view_table(self):
        if self.flow_data is not None:
            Tableviewer(self, self.controller, self.flow_data.get_df(), show_index=True, show_header=True)
        else:
            tk.messagebox.showerror('Error', 'Please upload flow data.')
           
    #Creates figure in separate window with matplotlib features
    def pop_figure(self):
        fig_type = self.fig_var.get()
        if fig_type == 'Daily':
            fig, ax = self.flow_data.get_flow_timeseries_plot(hide=False)
        elif fig_type == 'Monthly':
            fig, ax = self.flow_data.get_average_month_plot(hide=False)
        elif fig_type == 'Mean Annual':
            fig, ax = self.flow_data.get_mean_annual_plot(hide=False)
        elif fig_type == 'Total Annual':
            fig, ax = self.flow_data.get_total_annual_plot(hide=False)
        elif fig_type == 'Flow Duration':
            fig, ax = self.flow_data.get_flow_duration_plot(hide=False, prob=self.prob)
    
    #Get automated datra retrieval from the USGS NWIS API using the autodataFrame
    def auto_retrieval(self):
        autodataFrame(self, self.controller, 'Daily')
    
    #Get data from a csv from the csvUploadWindow
    def csv_retrieval(self):
        self.csv_window = csvUploadWindow(self, self.controller)

    #When csv or API data are added, update the flow data and figures
    def data_uploaded(self, df):
        if type(df['dateTime'][0]) == str:
            df['dateTime'] = pd.to_datetime(df.iloc[:,0])
            df['Discharge (cfs)'] = df.iloc[:,1]
        self.flow_data = mc.FlowData('Daily Inflows', df)
        self.update_results()
        return 'Successful'
    
    #Retuurn the flow data if it has been created
    def get_data(self):
        if type(self.flow_data) != list:
            return self.flow_data
        else:
            tk.messagebox.showerror('Error','Historical daily inflow data has not be properly uploaded.')
            return False
            
    #When the flow duration probability changes, the figures are updated
    def prob_changed(self, prob):
        self.prob = prob
        fig_type = self.fig_var.get()
        if fig_type == 'Flow Duration':
            self.ax.clear()
            fig, self.ax = self.flow_data.get_flow_duration_plot(self.fig, self.ax, prob=self.prob)
            self.fig.canvas.draw()
            self.canvas_fig.draw()
        
#Calculates the flow for a given exceedance probability and vice versa
class QFinderFrame(tk.Frame):
    def __init__(self, parent, controller, flow_data): 
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.page_name = 'Q Finder'
        self.parent = parent
        self.controller = controller
        self.entry_width = 5
        self.flow_data = flow_data
        
        self.title = tk.Label(self, text='Q Finder', font=TEXT_FONT, bg=SUBTITLE_BG_COLOR)
        self.prob_lbl = tk.Label(self, text='Q (%)', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.prob_entry = ttk.Entry(self, width=self.entry_width)
        self.prob_btn = tk.Button(self, text='v', font=TEXT_FONT, command=lambda:self.update_prob())
        self.flow_lbl = tk.Label(self, text='Flow (cfs)', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.flow_entry = ttk.Entry(self, width=self.entry_width)
        self.flow_btn = tk.Button(self, text='^', font=TEXT_FONT, command=lambda:self.update_flow())

        self.title.grid(row=0, column=0, columnspan=3, padx=5, pady=5,sticky='nsew')        
        self.prob_lbl.grid(row=1, column=0, columnspan=1, padx=5, pady=5,sticky='nsew')
        self.prob_entry.grid(row=1, column=1, columnspan=1, padx=5, pady=5,sticky='nsew')
        self.prob_btn.grid(row=1, column=2, columnspan=1, padx=5, pady=5,sticky='nsew')
        self.flow_lbl.grid(row=2, column=0, columnspan=1, padx=5, pady=5,sticky='nsew')
        self.flow_entry.grid(row=2, column=1, columnspan=1, padx=5, pady=5,sticky='nsew')
        self.flow_btn.grid(row=2, column=2, columnspan=1, padx=5, pady=5,sticky='nsew')
        
        self.set_default_prob()
        
    def set_default_prob(self):
        self.prob_entry.insert(0, str(self.parent.prob))
        self.update_prob()
        
    #Update the exceedance flow for a user-defined exceedance probability
    def update_prob(self):
        prob = check_entry(self.prob_entry.get(), [float])
        if prob == 'Error':
            tk.messagebox.showerror('Error', 'Please enter a flow exceedance percentage between 0 and 100 (exclusive).')
            return
        if (prob <= 0) or (prob >= 100):
            tk.messagebox.showerror('Error', 'Please enter a flow exceedance percentage between 0 and 100 (exclusive).')
            return
        new_flow = self.flow_data.get_flow_from_prob(prob)
        if new_flow is False:
            tk.messagebox.showerror('Error', 'Exceedance probability not between existing data points.')
            return
        clear_entries([self.flow_entry])
        self.flow_entry.insert(0, str(round(new_flow)))               
        self.prob = prob
        self.parent.prob_changed(self.prob)
        
    #Update the exceedance probability for a user-defined flow value
    def update_flow(self):
        flow = check_entry(self.flow_entry.get(), [float])
        if flow == 'Error':
            tk.messagebox.showerror('Error', 'Please enter a numeric value for flow in cfs.')
            return
        if flow <= 0:
            tk.messagebox.showerror('Error', 'Please enter a numeric value greater than zero for flow in cfs.')
            return
        new_prob = self.flow_data.get_prob_from_flow(flow)
        if new_prob is False:
            tk.messagebox.showerror('Error', 'Flow value is outside the range of provided flow data.')
            return
        clear_entries([self.prob_entry])
        self.prob_entry.insert(0, str(round(new_prob)))               
        self.prob = new_prob
        self.parent.prob_changed(self.prob)
        
# PEAK RESULTS FRAME - gets and displays peak inflow data
class peakFrame(tk.Frame):
    def __init__(self, parent, controller): 
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.button_width = 20
        self.page_name = 'Peak Results'
        self.controller = controller
        self.peak_data = []
        self.columnconfigure((0,1,2), weight=1)
        plt.ioff()
        self.fig = plt.figure(figsize=(6,5))
        self.ax = self.fig.add_subplot(111)
        
        self.option_lbl = tk.Label(self, text='Please select a data upload option', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.auto_btn = tk.Button(self, text='USGS Download', font=TEXT_FONT, command=lambda:self.auto_retrieval())
        self.csv_btn = tk.Button(self, text='Excel/CSV Upload', font=TEXT_FONT, command=lambda:self.csv_retrieval())
        
        self.option_lbl.grid(row=0, column=0,padx=5, pady=5, sticky='nsew')
        self.auto_btn.grid(row=0, column=1,padx=5, pady=5, sticky='nsew')
        self.csv_btn.grid(row=0, column=2,padx=5, pady=5, sticky='nsew')
        
        self.canvas_fig = []
        
    def site_added(self):
        self.peak_data = self.controller.site.peak_flows
        if self.peak_data is not None:
            self.update_results()
        
    #Update the flood frequency plot
    def update_results(self):
        self.fig, self.ax = self.peak_data.get_flood_analysis_plot(self.fig, self.ax)
        if type(self.fig) != str:
            self.right_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
            self.right_frame.columnconfigure((0), weight=1)
            self.export_btn = tk.Button(self.right_frame,text='View Table', font=TEXT_FONT, command=lambda:self.export_data())
            self.canvas_fig = FigureCanvasTkAgg(self.fig, master=self)
            self.pop_btn = tk.Button(self.right_frame, text='Pop-out Figure', font=TEXT_FONT, command=lambda:self.pop_figure())
            
            self.canvas_fig.get_tk_widget().grid(row=1, column=0, columnspan=2, padx=0, pady=5, sticky='nsew')
            self.right_frame.grid(row=1, column=2, padx=0, pady=5, sticky='nsew')
            
            self.export_btn.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
            self.pop_btn.grid(row=1, column=0, padx=5, pady=5, sticky='nsew')
        
    #Show a table view with peak flow data and let users export using the tableviewer
    def export_data(self):
        if type(self.peak_data) != list:
            Tableviewer(self, self.controller, self.peak_data.get_df(), show_index=True)
        else:
            tk.showerror('Error', 'Please upload data before exporting.')
            
    #Create figure pop-out with matplotlib features
    def pop_figure(self):
        fig, ax = self.peak_data.get_flood_analysis_plot(hide=False) 
    
    #Get peak flow data from API
    def auto_retrieval(self):
        autodataFrame(self, self.controller, 'Peak')
    
    #Get peak flow data from CSV
    def csv_retrieval(self):
        self.csv_window = csvUploadWindow(self, self.controller)

    #This is called when the csvUploadWindow or autodataFrame
    def data_uploaded(self, df):
        if type(df['dateTime'][0]) == str:
            df['dateTime'] = pd.to_datetime(df.iloc[:,0])
            df['Discharge (cfs)'] = df.iloc[:,1]
        self.peak_data = mc.FlowData('Peak Flows', df)
        self.update_results()
        return 'Successful'
        
    #Return saved peak flow data if available
    def get_data(self):
        if type(self.peak_data) != list:
            return self.peak_data
        else:
            return False

#%%## ADD MODULE PAGE - Adds modules to the library
class AddModulePage(tk.Frame):
    def __init__(self, parent, controller):  
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR) 
        self.page_name = 'Add Modules' 
        self.controller = controller
        self.columnconfigure((0,1,2,4), weight=1)
        self.parent = parent
        
        self.page_title = tk.Label(self, text = self.page_name, font = PG_TITLE_FONT, bg=TITLE_BG_COLOR) 
        self.direction_txt = 'Directions: This page allows you add static modules to the library. To do so, simply fill in the parameters within the corresponding module type and press the submit button.'
        self.directions_lbl = tk.Label(self, text =self.direction_txt, font = TEXT_FONT, bg=DIRECTIONS_BG_COLOR, justify='left', anchor='w', wraplength=self.controller.wrap_length) 
        self.add_mod_btn = tk.Button(self, text='Add Module',font=TEXT_FONT, command=lambda:self.open_add_module_pop())
        self.import_btn = tk.Button(self, text='Import Workbook', font=TEXT_FONT, command=lambda:self.controller.import_watershed_workbook('Module Library'))
        self.export_btn = tk.Button(self, text='Export All Modules', font=TEXT_FONT, command=lambda:self.export_mod_lib())
        self.clear_lib_btn = tk.Button(self, text='Clear Library', font=TEXT_FONT, command=lambda:self.clear_mod_lib())
        self.mod_lib_lbl = tk.Label(self, text='Module Library', font=SUBTITLE_FONT, bg = SUBTITLE_BG_COLOR)
        self.extra_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
       
        self.mod_lib_frame = ModuleLibraryFrame(self.extra_frame,self.controller)
        self.mod_lib_frame.pack(fill='x')
        
        self.page_title.grid(row=0, column=0, columnspan=4, sticky='ew')
        self.directions_lbl.grid(row=1, column=0, columnspan=4, pady=5, sticky='ew')
        self.add_mod_btn.grid(row=2, column=0, columnspan=1, pady=5, padx=5, sticky='nsew')
        self.import_btn.grid(row=2, column=1,columnspan=1, pady=5, padx=5, sticky='nsew')
        self.export_btn.grid(row=2, column=2,columnspan=1, pady=5, padx=5, sticky='nsew')
        self.clear_lib_btn.grid(row=2, column=3, columnspan=1, pady=5, padx=5, sticky='nsew')
        self.mod_lib_lbl.grid(row=3, column=0, columnspan=4, pady=5, sticky='ew')
        self.extra_frame.grid(row=4, column=0, columnspan=4, pady=5, sticky='nsew')
        
    #Exports the module library to a csv
    def export_mod_lib(self):
        out_df = self.controller.mod_lib.get_export_df()
        csvExportWindow(self, self.controller, out_df)

    #Clears the module library
    def clear_mod_lib(self):
        self.controller.mod_lib.clear_static()
        self.mod_lib_frame.update()
        self.controller.mods_added()
        
    #Creates a pop up window where users can create static modules
    def open_add_module_pop(self):
        self.add_mod_popup = OneFrameWindow(self, self.controller, scroll=True)
        self.add_mod_popup.addFrame(AddStaticModuleFrame(self.add_mod_popup.frame_parent, self.controller, self.add_mod_popup))

# MODULE LIBRARY FRAME - within the Add modules Page and displays a ModuleSummaryFrame for each module
class ModuleLibraryFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.page_name = 'Module Library Frame'
        self.controller = controller
        self.mod_frame_list = []
        self.update()
        self.grid_columnconfigure((0,1,2), weight=1)

    #Update the grid of modules based on the module library
    def update(self):
        if len(self.mod_frame_list) >0:
            for i in self.mod_frame_list:
                i.destroy()
            self.mod_frame_list = []
        self.grid_forget()
        for key in self.controller.mod_lib.static_mods:
            for mod in self.controller.mod_lib.static_mods[key]:    
                self.mod_frame_list.append(ModuleSummaryFrame(self, self.controller, mod))
        col_counter = 0
        row_counter = 0
        for i in range(0, len(self.mod_frame_list)):
            self.mod_frame_list[i].grid(row=row_counter, column=col_counter, pady=5, padx=5, sticky='nsew')
            if col_counter == 2:
                col_counter = 0
                row_counter += 1
                self.rowconfigure(i)
            else:
                col_counter +=1
                
# MODULE SUMMARY FRAME - Shows a small box for each module
class ModuleSummaryFrame(tk.Frame):
    def __init__(self, parent, controller, mod):
        tk.Frame.__init__(self, parent,bg=MODULE_COLORS[mod.module_class])
        self.controller = controller
        self.parent=parent
        self.mod = mod
        self.columnconfigure((0,1), weight=1)
        self.ICON_FONT = ("Verdana", 16, "bold")
        self.wrap_length = 250
        self.button_width = 7
        
        #Select the text to show based on the module class
        if self.mod.module_class == 'Gen':
            self.icon_text = 'G'
            self.label_text = styles.format_value(self.mod.nom_power, 'comma', 'kW')
        elif self.mod.module_class == 'Sed':
            self.icon_text = 'Sd'
            self.label_text = styles.format_value(self.mod.design_flow, 'comma', 'cfs')
        elif self.mod.module_class == 'Rec':
            self.icon_text = 'R'
            self.label_text = styles.format_value(self.mod.design_flow, 'comma', 'cfs')
        elif self.mod.module_class == 'Fou':
            self.icon_text = 'Fd'
            self.label_text = styles.format_value(self.mod.get_footprint(), 'comma', 'ft2')
        elif self.mod.module_class == 'Fish':
            self.icon_text = 'F'
            self.label_text = styles.format_value(self.mod.design_flow, 'comma', 'cfs')
        elif self.mod.module_class == 'Non':
            self.icon_text = 'N'
            self.label_text = styles.format_value(self.mod.length, 'comma', 'ft')
        elif self.mod.module_class == 'Wat':
            self.icon_text = 'W'
            self.label_text = styles.format_value(self.mod.design_flow, 'comma', 'cfs')
        elif self.mod.module_class == 'Spill':
            self.icon_text = 'Sp'
            self.label_text = styles.format_value(self.mod.design_flow, 'comma', 'cfs')
            
        self.icon_lbl = tk.Label(self, text=self.icon_text, font=self.ICON_FONT, bg = MODULE_COLORS[mod.module_class])
        self.name_lbl = tk.Label(self, text = self.mod.name, font=TEXT_FONT,wraplength=self.wrap_length, bg=MODULE_COLORS[mod.module_class])
        self.cost_lbl = tk.Label(self, text = styles.format_value(self.mod.cap_cost, 'dollar', ''),wraplength=self.wrap_length, font=TEXT_FONT, bg=MODULE_COLORS[mod.module_class])
        self.mod_lbl = tk.Label(self, text = self.label_text, font=TEXT_FONT,wraplength=self.wrap_length, bg= MODULE_COLORS[mod.module_class])
        self.delete_btn = tk.Button(self, text='Delete', width=self.button_width,font=TEXT_FONT, command=lambda:self.delete_module())
        self.view_btn = tk.Button(self, text='View', width=self.button_width, font=TEXT_FONT, command=lambda:self.view_module())
        
        self.name_lbl.grid(row=0, column=0,columnspan=2, sticky='nsew')
        self.view_btn.grid(row=1, column=0, pady=5, padx=5, sticky='nsw')
        self.delete_btn.grid(row=2, column=0, pady=5, padx=5, sticky='nsw')
        self.cost_lbl.grid(row=1, column=1, sticky='nse')
        self.mod_lbl.grid(row=2, column=1, sticky='nse')
        
    #View module characteristics in a tableviewer
    def view_module(self):
        Tableviewer(self, self.controller, self.mod.get_df(units=True), show_header=True, show_index=True)
        
    #Delete module from module library and update frame
    def delete_module(self):
        res = self.controller.mod_lib.remove_static(self.mod)
        if res == 'Successful':
            tk.messagebox.showinfo('Successful', 'Successfully removed module.')
            self.parent.update()
        else:
            tk.messagebox.showerror('Unsucessful', 'Unable to remove module.')
        self.controller.mods_added()
         
#Add Module Frame - used within a TopLevel to create a module
class AddStaticModuleFrame(tk.Frame):
    def __init__(self, parent, controller, window):  
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR) 
        self.parent = parent
        self.page_name = 'Add Static Modules Frame' 
        self.controller = controller
        self.window = window
        self.entry_width = 10
        self.module_opts = ['Generation','Fish Passage','Sediment Passage','Recreation','Water Passage','Non-overflow','Foundation']
        self.module_types_var = tk.StringVar()
        self.wrap_length= 780
        
        self.title_lbl = tk.Label(self, text='Add a Module', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.directions_lbl = tk.Label(self, text='Select a module class from the list below and input the values below.\nClick the support tools on the right for guidance.', font=TEXT_FONT, bg=DIRECTIONS_BG_COLOR, wraplength=self.wrap_length)
        self.mod_typ_menu = tk.OptionMenu(self, self.module_types_var, *self.module_opts)
        self.mod_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.module_types_var.trace('w', self.on_menu_switch)
        self.module_types_var.set(self.module_opts[0])
        self.add_btn = tk.Button(self, text='Add Module',font=TEXT_FONT, command=lambda:self.add_module())    
        
        self.title_lbl.pack(fill='x', expand=True, padx=5, pady=0)
        self.directions_lbl.pack(fill='x', expand=True, padx=5, pady=5)
        self.mod_typ_menu.pack(fill='x', expand=True, padx=100, pady=5)
        self.mod_frame.pack()
        self.add_btn.pack(fill='x', expand=True, padx=100, pady=5)
        
    #Changes the inputs depending on the selemodule class
    def on_menu_switch(self, name, indx, op):
        self.create_module_frame(self.module_types_var.get())
    
    #Grabs the required inputs from get_static_module_attributes based on the module class and packs them in the frame
    def create_module_frame(self, mod_type):
        for widget in self.mod_frame.winfo_children():
            widget.destroy()
        self.input_dict = get_static_module_attributes(self.module_types_var.get())
        self.att_labels, self.att_entries, self.att_units, self.att_tools, self.input_vars = create_inputs(self, self.mod_frame, self.input_dict, self.entry_width, self.module_types_var.get())
        pack_attributes(self, self.mod_frame, row_counter=1)
        self.set_defaults()
        
    #Set default values for checkbox and optionmenu inputs
    def set_defaults(self):
        for key in list(self.att_labels.keys()):
            if self.input_dict[key][0][0] == 'OptionMenu':
                self.input_vars[key].trace('w', self.on_option_switch)
                self.input_vars[key].set(self.input_dict[key][0][1][0])
            elif self.input_dict[key][0][0] == 'checkbox':
                self.input_vars[key].set(False)    
                    
    #Input values from the support tools into the corresponding entry
    def import_from_tool(self, tool_name, out_var):
        if tool_name == 'Turbine Head Efficiency':
            self.att_entries['Head Efficiency Curve'].update_equation(out_var)
        elif tool_name == 'Sluicing Operating Flow':
            clear_entries([self.att_entries['Operating Flow']])
            self.att_entries['Operating Flow'].insert(0, str(out_var))
                
    #Used for inputs that are only needed when other inputs are a certain value
    def on_option_switch(self, name='', indx='', op=''):
        mod_type = self.module_types_var.get()
        pack_attributes(self,self.mod_frame, row_counter=1)
        hide_keys = []
        if mod_type == 'Sediment Passage':
            if name == 'Operating Mode':
                mode = self.input_vars['Operating Mode'].get()
                if mode == 'Continuous':
                    hide_keys = ['Operating Flow', 'Flushing Duration', 'Operating Frequency']
                elif mode == 'Sluicing':
                    hide_keys = ['Flushing Duration', 'Operating Frequency']
                elif mode == 'Flushing':
                    hide_keys = ['Operating Flow']
        elif mod_type == 'Water Passage':
            if name == 'Operating Mode':
                mode = self.input_vars['Operating Mode'].get()
                if mode == 'Continuous':
                    hide_keys = ['Weir Coefficient', 'Crest Height']
                elif mode == 'Controlled Spillway':
                    hide_keys =['Weir Coefficient', 'Crest Height']
        for i in hide_keys:
            if self.input_dict[i][0][0] == 'text entry':
                clear_entries([self.att_entries[i]])
            self.att_labels[i].grid_forget()
            self.att_entries[i].grid_forget()
            self.att_units[i].grid_forget()
            self.att_tools[i].grid_forget()

    #Check if the attribute is a required input for a given module
    def check_required(self, key):
        if self.input_dict[key][4] == False: #If is_optional is False
            return True
        else:
            if key == 'Operating Flow':
                if self.input_vars['Operating Mode'].get() == 'Sluicing':
                    return True
            elif (key == 'Flushing Duration') or (key == 'Operating Frequency'):
                if self.input_vars['Operating Mode'].get() == 'Flushing':
                    return True
            elif (key == 'Weir Coefficient') or (key == 'Crest Height'):
                if self.input_vars['Operating Mode'].get() == 'Uncontrolled Spillway':
                    return True
        return False

    #Gets the inputs for a module class, error checks, then creates the module using create_mod_from_dict
    def add_module(self,msg_off=False):
        mod_type = self.module_types_var.get()       
        ad = get_values(self, self.check_required)
       
        if ad is False:
            return False
        #Checks for conflicting names
        if ad['Name'] in self.controller.mod_lib.get_name_list():
            tk.messagebox.showerror('Error', 'Module name already used in the Library')
            return False
        
        try:
            if mod_type == 'Generation':
                #If efficiency bounds are less than operating bounds, then raise an error
                if False in [ad['Flow Efficiency Curve'].check_bounds(ad['Maximum Operating Flow']/ad['Design Flow']),\
                             ad['Flow Efficiency Curve'].check_bounds(ad['Minimum Operating Flow']/ad['Design Flow'])]:
                    tk.messagebox.showerror('Error', 'Efficiency curves must span the operating range. Please make sure efficiencies are report as decimals (0.0 - 1.0).')
                    return False
                if ad['Head Efficiency Curve'] is not None:
                    if False in [ad['Head Efficiency Curve'].check_bounds(ad['Maximum Operating Head']/ad['Design Head']),\
                             ad['Head Efficiency Curve'].check_bounds(ad['Minimum Operating Head']/ad['Design Head'])]:
                        tk.messagebox.showerror('Error', 'Efficiency curves must span the operating range. Please make sure efficiencies are report as decimals (0.0 - 1.0).')
                        return False
                out_mod = create_mod_from_dict(mod_type, ad)
            else:
                out_mod = create_mod_from_dict(mod_type, ad) 
                
            if out_mod is not False:
                self.controller.mod_lib.add_static(out_mod)
                self.controller.mods_added()
                tk.messagebox.showinfo('Success!', 'Module has been sucessfully added to the Module Library.')
                self.window.cleanup()
            else:
                tk.messagebox.showerror('Error', 'Unable to create module. Please make sure all attributes are entered properly')
        except:
            tk.messagebox.showerror('Error', 'Unable to create module. Please make sure all attributes are entered properly')

#%%## ADD DYNAMIC MODULE PAGE - Adds dynamic modules to the library
class AddDynamicModulePage(tk.Frame):
    def __init__(self, parent, controller):  
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR) 
        self.page_name = 'Add Dynamic' 
        self.controller = controller
        self.columnconfigure((0,1,2,3), weight=1)
        self.parent = parent
        
        self.page_title = tk.Label(self, text = self.page_name, font = PG_TITLE_FONT, bg=TITLE_BG_COLOR) 
        self.direction_txt = 'Directions: This page allows you add dynamic modules to the library. Dynamic modules can be redesigned by assigning relationships to select control variables and then adjusting the control variables. Click the add dynamic module button to learn about the control variables and assigning relationships. Once the modules have been created, the modules can be viewed in the library below.'
        self.directions_lbl = tk.Label(self, text =self.direction_txt, font = TEXT_FONT, bg=DIRECTIONS_BG_COLOR, justify='left', anchor='w', wraplength=self.controller.wrap_length) 
        self.add_mod_btn = tk.Button(self, text='Add Dynamic Module',font=TEXT_FONT, command=lambda:self.open_add_module_pop())
        self.clear_lib_btn = tk.Button(self, text='Clear Dynamic Library', font=TEXT_FONT, command=lambda:self.clear_mod_lib())
        self.mod_lib_lbl = tk.Label(self, text='Dynamic Module Library', font=SUBTITLE_FONT, bg = SUBTITLE_BG_COLOR)
        self.extra_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.mod_lib_frame = DynamicModuleLibraryFrame(self.extra_frame,self.controller)
        
        self.mod_lib_frame.pack(fill='x')
        
        self.page_title.grid(row=0, column=0, columnspan=4, sticky='ew')
        self.directions_lbl.grid(row=1, column=0, columnspan=4, pady=5, sticky='ew')
        self.add_mod_btn.grid(row=2, column=0, columnspan=2, pady=5, padx=5, sticky='nsew')
        self.clear_lib_btn.grid(row=2, column=2, columnspan=2, pady=5, padx=5, sticky='nsew')
        self.mod_lib_lbl.grid(row=3, column=0, columnspan=4, pady=5, sticky='ew')
        self.extra_frame.grid(row=4, column=0, columnspan=4, pady=5, sticky='nsew')
        
    #Clear dynamic module library
    def clear_mod_lib(self):
        self.controller.mod_lib.clear_dynamic()
        self.mod_lib_frame.update()
        self.controller.mods_added()
        
    #Creates a toplevel that allows user to create a dynamic module
    def open_add_module_pop(self):
        self.add_mod_popup = OneFrameWindow(self, self.controller, scroll=True)
        self.add_mod_popup.addFrame(AddDynamicModuleFrame(self.add_mod_popup.frame_parent, self.controller, self.add_mod_popup))

# MODULE LIBRARY FRAME - within the Add modules Page and displays a ModuleSummaryFrame for each module
class DynamicModuleLibraryFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.page_name = 'Module Library Frame'
        self.controller = controller
        self.mod_frame_list = []
        self.update()

    #Update the grid of module summary frames based on the dynamic mods in the module library
    def update(self):
        if len(self.mod_frame_list) >0:
            for i in self.mod_frame_list:
                i.destroy()
            self.mod_frame_list = []
        self.grid_forget()
        for key in self.controller.mod_lib.dynamic_mods:
            for mod in self.controller.mod_lib.dynamic_mods[key]:  
                self.mod_frame_list.append(DynamicModuleSummaryFrame(self, self.controller, mod))
        col_counter = 0
        row_counter = 0
        for i in range(0, len(self.mod_frame_list)):
            self.mod_frame_list[i].grid(row=row_counter, column=col_counter, pady=5, padx=5, sticky='nsew')
            if col_counter == 1:
                col_counter = 0
                row_counter += 1
                self.rowconfigure(i)
            else:
                col_counter +=1
                
# MODULE SUMMARY FRAME - Shows a small box for each module with inputs used to redesign modules
class DynamicModuleSummaryFrame(tk.Frame):
    def __init__(self, parent, controller, mod):
        tk.Frame.__init__(self, parent,bg=MODULE_COLORS[mod.module_class])
        self.controller = controller
        self.parent=parent
        self.mod = mod
        self.bgc = MODULE_COLORS[self.mod.module_class]
        self.columnconfigure((0,1,2), weight=1)
        self.wrap_length = 250
        self.entry_width = 10
        self.button_width = 7
        self.ICON_FONT = ("Verdana", 16, "bold")
        self.name_var = tk.StringVar()


        self.input_frame = tk.Frame(self, bg=self.bgc)
        self.input_frame.columnconfigure((0,1), weight=1)
        
        #Sets the inputs based on the module class
        if self.mod.module_class == 'Gen':
            self.atts = ['Design Flow', 'Design Head']
            self.units = ['cfs', 'ft']
        elif self.mod.module_class == 'Sed':
            self.atts = ['Mean Daily Flow'] 
            self.units = ['cfs']
        elif self.mod.module_class == 'Rec':
            self.atts = ['Normal Operating Level', 'Mean Daily Flow']
            self.units = ['ft', 'cfs']
        elif self.mod.module_class == 'Fou':
            self.atts = ['Depth']
            self.units = ['ft']
        elif self.mod.module_class == 'Fish':
            self.atts = ['Normal Operating Level', 'Mean Daily Flow']
            self.units = ['ft', 'cfs']
        elif self.mod.module_class == 'Non':
            self.atts = ['Normal Operating Level']
            self.units = ['ft']
        elif (self.mod.module_class == 'Wat') or (self.mod.module_class == 'Spill'):
            self.atts = ['Normal Operating Level']            
            self.units = ['ft']
            
        #Creates labels and entries so that the dynamic modules can be redesigned based on these controlling variables
        self.att_labels = {}
        self.att_entries = {}
        for i in range(0, len(self.atts)):
            lbl_text = self.atts[i] + ' (' + self.units[i] + ')'
            self.att_labels[self.atts[i]] = tk.Label(self.input_frame, text=lbl_text, font=TEXT_FONT, bg=self.bgc)
            self.att_entries[self.atts[i]] = ttk.Entry(self.input_frame, width=self.entry_width)
            self.att_entries[self.atts[i]].insert(0, str(self.mod.control_vars_dict[self.atts[i]]))
            self.att_labels[self.atts[i]].grid(row=i, column=0, sticky='nse')
            self.att_entries[self.atts[i]].grid(row=i, column=1, sticky='nsew')
        self.name_lbl = tk.Label(self, textvariable = self.name_var, font=TEXT_FONT,wraplength=self.wrap_length, bg=self.bgc)
        self.redesign_btn = tk.Button(self, text='Redesign', width=self.button_width, font=TEXT_FONT, command=lambda:self.redesign_module())
        self.delete_btn = tk.Button(self, text='Delete', width=self.button_width,font=TEXT_FONT, command=lambda:self.delete_module())
        self.view_btn = tk.Button(self, text='View', width=self.button_width, font=TEXT_FONT, command=lambda:self.view_module())
        
        self.name_lbl.grid(row=0, column=0,columnspan=3, sticky='ns')
        self.input_frame.grid(row=1, column=0, columnspan=3, pady=5, padx=5, sticky='ns')
        self.redesign_btn.grid(row=2, column=0, pady=5, padx=5, sticky='ns')
        self.view_btn.grid(row=2, column=1, pady=5, padx=5, sticky='ns')
        self.delete_btn.grid(row=2, column=2, pady=5, padx=5, sticky='ns')
        self.update()
    
    #View dynamic module characteristics using a tableviewer, will update when redesigned
    def view_module(self):
        Tableviewer(self, self.controller, self.mod.get_df(units=True), show_header=True, show_index=True)
        
    #Delete module from module library and update grid
    def delete_module(self):
        res = self.controller.mod_lib.remove_dynamic(self.mod)
        if res == 'Successful':
            tk.messagebox.showinfo('Successful', 'Successfully removed module.')
            self.parent.update()
        else:
            tk.messagebox.showerror('Unsucessful', 'Unable to remove module.')
        self.controller.mods_added()
        
    #Recalculates the module paramerters based on the user-defined controlling variable 
    def redesign_module(self):
        vals = [check_entry(self.att_entries[i].get(), [float]) for i in self.att_entries.keys()]
        if ('Error' in vals) or ('' in vals):
            tk.messagebox.showerror('Error', 'Please input proper values.')
            return
        self.mod.redesign(*vals)
        if self.mod.valid:
            self.update()
        else:
            tk.messagebox.showerror('Error', 'Unable to redesign the module to these parameters due to an error during redesign. Double check the equation inputs are correct.')
        
    def update(self):
        self.name_var.set(self.mod.full_name)


# Add Module Frame - used within a TopLevel to create a dynamic module
class AddDynamicModuleFrame(tk.Frame):
    def __init__(self, parent, controller, window):  
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR) 
        self.parent = parent
        self.page_name = 'Add Dynamic Modules Frame' 
        self.controller = controller
        self.window = window
        self.entry_width = 10
        self.module_opts = ['Generation','Fish Passage','Sediment Passage','Recreation',
                                  'Water Passage','Non-overflow','Foundation']
        
        #Gets the dynamic module default attributes from the case_study_functions script
        self.def_mod_dict = {'Generation': {'Kaplan':csf.get_kaplan_dict()}, \
                              'Fish Passage': {'Vertical Slot':csf.get_verticalslot_dict()}, \
                              'Sediment Passage': {'Sluice Gate': csf.get_sluice_dict()}, \
                                  'Recreation': {'Boat Chute':csf.get_chute_dict()}, \
                                    'Water Passage': {'Obermeyer':csf.get_obermeyer_dict()},\
                                        'Non-overflow': {'Precast Concrete':csf.get_precastnon_dict()}, \
                                            'Foundation': {'Precast Concrete Foundation':csf.get_precastfou_dict()}}
        self.module_types_var = tk.StringVar()
        self.default_var = tk.StringVar()
        self.default_var.trace('w', self.on_default_menu_switch)
        self.wrap_length= 780
        
        self.title_lbl = tk.Label(self, text='Add a Module', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.directions_lbl = tk.Label(self, text='Select a module class from the list below and input the values below.\nClick the support tools on the right for guidance.', font=TEXT_FONT, bg=DIRECTIONS_BG_COLOR, wraplength=self.wrap_length)
        self.mod_typ_menu = tk.OptionMenu(self, self.module_types_var, *self.module_opts)
        self.module_types_var.trace('w', self.on_menu_switch)
        self.mod_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.add_btn = tk.Button(self, text='Add Module',font=TEXT_FONT, command=lambda:self.add_module())    
        
        self.title_lbl.pack(fill='x', expand=True, padx=5, pady=0)
        self.directions_lbl.pack(fill='x', expand=True, padx=5, pady=5)
        self.mod_typ_menu.pack(fill='x', expand=True, padx=100, pady=5)
        self.mod_frame.pack()
        self.add_btn.pack(fill='x', expand=True, padx=100, pady=5)
        
        self.module_types_var.set(self.module_opts[0])
        
    #Change the inputs based on the module class
    def on_menu_switch(self, name='', indx='', op=''):
        self.create_module_frame(self.module_types_var.get())
    
    #creates the frame wrapped around the module inputs
    def create_module_frame(self, mod_type):
        for widget in self.mod_frame.winfo_children():
            widget.destroy()
        
        self.default_lbl = tk.Label(self.mod_frame, text='Optional default*', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        menu_opts = list(self.def_mod_dict[self.module_types_var.get()].keys())
        self.default_menu = tk.OptionMenu(self.mod_frame,self.default_var, *menu_opts)
        self.default_var.set('')
        
        self.input_dict, self.my_cvars = get_dynamic_module_attributes(self.module_types_var.get())
        self.att_labels, self.att_entries, self.att_units, self.att_tools, self.input_vars = create_inputs(self, self.mod_frame, self.input_dict, self.entry_width, self.module_types_var.get(), self.my_cvars)
        
        self.pack_attributes()
        self.set_defaults()
   
    #Sets the inputs depending on the selected module class
    def on_default_menu_switch(self, name='', indx='', op=''):
        if self.default_var.get() != '':
            mod_dict = self.def_mod_dict[self.module_types_var.get()][self.default_var.get()]
        else:
            return 
        for key in list(self.att_labels.keys()):
            input_type = self.input_dict[key][0][0]
            if input_type == 'text entry':
                clear_entries([self.att_entries[key]])
                self.att_entries[key].insert(0, str(mod_dict[key]))
            elif input_type == 'OptionMenu':
                self.input_vars[key].set(mod_dict[key])     
            elif input_type == 'Equation':
                self.att_entries[key].update_equation(mod_dict[key])
            elif input_type == 'month box':
                self.att_entries[key].set_values(mod_dict[key])
            elif input_type == 'checkbox':
                if mod_dict[key] is True:
                    self.input_vars[key].set(True)
                else:
                    self.input_vars[key].set(False)
            elif input_type == 'Optional':
                self.att_entries[key].update(mod_dict[key])
        
    #Set default values for option menus and checkboxes
    def set_defaults(self):
        for key in list(self.att_labels.keys()):
            if self.input_dict[key][0][0] == 'OptionMenu':
                self.input_vars[key].trace('w', self.on_option_switch)
                self.input_vars[key].set(self.input_dict[key][0][1][0])
            elif self.input_dict[key][0][0] == 'checkbox':
                self.input_vars[key].set(False)    
                    
    #place menu option and place entries using the pack_attributes function
    def pack_attributes(self):
        for widget in self.mod_frame.winfo_children():
            widget.grid_forget()
        self.default_lbl.grid(row=0,column=0, columnspan=1, pady=5, sticky='nse')
        self.default_menu.grid(row=0,column=1, columnspan=1, pady=5, sticky='nsew')
        pack_attributes(self, self.mod_frame, 1)
        
    #Changes the visibility of inputs depending on the selected options
    def on_option_switch(self, name='', indx='', op=''):
        mod_type = self.module_types_var.get()
        self.pack_attributes()
        hide_keys = []
        if mod_type == 'Sediment Passage':
            if name == 'Operating Mode':
                mode = self.input_vars['Operating Mode'].get()
                if mode == 'Continuous':
                    hide_keys = ['Operating Flow', 'Flushing Duration', 'Operating Frequency']
                elif mode == 'Sluicing':
                    hide_keys = ['Flushing Duration', 'Operating Frequency']
                elif mode == 'Flushing':
                    hide_keys = ['Operating Flow']
        elif mod_type == 'Water Passage':
            if name == 'Operating Mode':
                mode = self.input_vars['Operating Mode'].get()
                if mode == 'Continuous':
                    hide_keys = ['Weir Coefficient', 'Crest Height']
                elif mode == 'Controlled Spillway':
                    hide_keys =['Weir Coefficient', 'Crest Height']
        for i in hide_keys:
            if self.input_dict[i][0][0] == 'text entry':
                clear_entries([self.att_entries[i]])
            self.att_labels[i].grid_forget()
            self.att_entries[i].grid_forget()
            self.att_units[i].grid_forget()
            self.att_tools[i].grid_forget()

    #Checks if an attribute is required to create the module
    def check_required(self, key):
        if self.input_dict[key][4] == False: #If is_optional is False
            return True
        else:
            if key == 'Operating Flow':
                if self.input_vars['Operating Mode'].get() == 'Sluicing':
                    return True
            elif (key == 'Flushing Duration') or (key == 'Operating Frequency'):
                if self.input_vars['Operating Mode'].get() == 'Flushing':
                    return True
            elif (key == 'Weir Coefficient') or (key == 'Crest Height'):
                if self.input_vars['Operating Mode'].get() == 'Uncontrolled Spillway':
                    return True
        return False

    #Collects the inputs, error checks, then creates a dynamic module 
    def add_module(self,msg_off=False):
        mod_type = self.module_types_var.get()
        ad = get_values(self,self.check_required)
        
        if ad is False:
            return False
        #Check for conflicting names
        if ad['Name'] in self.controller.mod_lib.get_name_list():
            tk.messagebox.showerror('Error', 'Module name already used in the Library')
            return False
        
        try: #Try to create the module from the ad dict
            if mod_type == 'Generation':
                out_mod = dm.Dynamic_Generation(ad['Name'],ad['Capital Cost'], ad['Annual Operating Cost'],\
                                            ad['Width'], ad['Length'], ad['Design Flow'], ad['Operating Months'], \
                                                ad['Minimum Operating Flow'],ad['Maximum Operating Flow'],ad['Minimum Operating Head'], \
                                                  ad['Design Head'], ad['Maximum Operating Head'],ad['Flow Efficiency Curve'], \
                                                      ad['Head Efficiency Curve'],ad['Max Power'], ad['Cost of Start-Stops'], ad['Instream or Diversion'])
            elif mod_type == 'Water Passage':
                out_mod = dm.Dynamic_Water(ad['Name'],ad['Capital Cost'], ad['Annual Operating Cost'],\
                                            ad['Width'], ad['Length'], ad['Design Flow'], ad['Operating Months'], \
                                            ad['Operating Mode'], ad['Weir Coefficient'], ad['Crest Height'], ad['Instream or Diversion'])
            elif mod_type == 'Fish Passage':
                out_mod = dm.Dynamic_Fish(ad['Name'],ad['Capital Cost'], ad['Annual Operating Cost'],\
                                            ad['Width'], ad['Length'], ad['Design Flow'], ad['Operating Months'], \
                                            ad['Number of Steps'], ad['Step Type'], ad['Maximum Headwater Drop'], ad['Maximum Headwater Rise'],\
                                                ad['Minimum Tailwater Level'], ad['Maximum Tailwater Level'], ad['Instream or Diversion'])
            elif mod_type == 'Recreation':
                out_mod = dm.Dynamic_Recreation(ad['Name'],ad['Capital Cost'], ad['Annual Operating Cost'],\
                                                    ad['Width'], ad['Length'], ad['Design Flow'], ad['Operating Months'], \
                                                    ad['Number of Steps'], ad['Step Type'], ad['Maximum Headwater Drop'], ad['Maximum Headwater Rise'],\
                                                        ad['Minimum Tailwater Level'], ad['Maximum Tailwater Level'], ad['Instream or Diversion'])
            elif mod_type == 'Non-overflow':
                out_mod = dm.Dynamic_Nonoverflow(ad['Name'],ad['Capital Cost'], ad['Annual Operating Cost'], ad['Width'], ad['Length'], ad['Height'])
            elif mod_type == 'Foundation':
                out_mod = dm.Dynamic_Foundation(ad['Name'],ad['Capital Cost'], ad['Annual Operating Cost'], ad['Width'], ad['Length'], ad['Depth'])
            elif mod_type == 'Sediment Passage':
                out_mod = dm.Dynamic_Sediment(ad['Name'], ad['Capital Cost'], ad['Annual Operating Cost'],\
                                              ad['Width'], ad['Length'], ad['Design Flow'], ad['Operating Months'],\
                                              ad['Operating Mode'], ad['Operating Flow'], ad['Flushing Duration'],\
                                              ad['Operating Frequency'], ad['Instream or Diversion'])
            #If the module is valid, then add it to the library
            if out_mod.validate() is not False:
                self.controller.mod_lib.add_dynamic(out_mod)
                self.controller.mods_added()
                tk.messagebox.showinfo('Success!', 'Module has been sucessfully added to the Module Library.')
                self.window.cleanup()
            else:
                tk.messagebox.showerror('Error', 'Unable to create module. Please make sure all attributes are entered properly')
        
        except:
            tk.messagebox.showerror('Error', 'Unable to create module. Please make sure all attributes are entered properly')

#Creates an input that can either be a constant or a function of set control variables
class OptionalFrame(tk.Frame):
    def __init__(self, parent, controller, mod_class, entry_name, entry_list, cvars):  
        tk.Frame.__init__(self, parent, bg='Black')
        self.parent = parent
        self.controller = controller
        self.mod_class = mod_class
        self.entry_name = entry_name
        self.entry_list = entry_list
        self.menu_var = tk.StringVar()
        self.columnconfigure((0), weight=1)
        
        #cvars are the controlling variables that are used to redesign the dynamic modules, which depend on the module class
        if type(cvars) == dict:
            self.cvars = cvars[self.entry_name]
        else:
            self.cvars = cvars
        self.opts = ['Constant']
        for i in self.cvars:
            self.opts.append('Function of {}'.format(i))
        
        self.opt_menu = tk.OptionMenu(self, self.menu_var, *self.opts)
        self.menu_var.trace('w', self.on_option_switch)
        self.menu_var.set(self.opts[0])
        
    #Place objects
    def pack_attributes(self):
        self.opt_menu.grid(row=0, column=0, padx=2, pady=(2,0), sticky='nsew')
        self.att_entry.grid(row=1, column=0, padx=2, pady=(0,2), sticky='nsew')
        
    #Update the entries based on the selected menu input 
    def update(self, att):
        if (type(att) == mc.Equation) or (type(att) == mc.PiecewiseEquation):
            self.menu_var.set(att.dynamic_type)
            self.att_entry.update_equation(att)
        else:
            clear_entries([self.att_entry])
            self.att_entry.insert(0, str(att))
        
    #Changes between constant and functions of the controlling variables
    def on_option_switch(self, name='', indx='', op=''):
        menu_select = self.menu_var.get()
        if menu_select == 'Constant':
            self.att_entry = ttk.Entry(self)
        else:
            eq_name = self.entry_name + ' as a '+ menu_select
            xz = menu_select[12:].split(' and ')
            xlabel = xz[0]
            if len(xz) == 2:
                zlabel = xz[1]
            else:
                zlabel = None
            self.att_entry = EquationAddFrame(self, self.controller, eq_name, xlabel, self.entry_name, zlabel=zlabel)
        self.pack_attributes()

    #Get the equation or the constant value depending on the selected menu
    def get_value(self):
        menu_select = self.menu_var.get()
        if menu_select == 'Constant':
            val = check_entry(self.att_entry.get(), self.entry_list[2])
            if (val == 'Error') or (val == ''):
                return False
        else:
            val = self.att_entry.get_equation()
            if val is None:
                return False
            val.set_dynamic_type(self.menu_var.get())
        return val            

#%%## Fish Page - used to input species and module fish passage characteristics
class FishPage(tk.Frame):
    def __init__(self, parent, controller):  
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.parent = parent
        self.controller = controller
        self.page_name = 'Species Passage'
        self.entry_width = 8
        self.species_var = tk.StringVar()
        self.first=True
        
        self.page_title = tk.Label(self, text = self.page_name, font = PG_TITLE_FONT, bg=TITLE_BG_COLOR) 
        self.directions_txt = 'Directions: This page provides inputs to the novel fish passage performance model. First, create a Species object by specifying a name, migratory months, and pressing the Add button. Then, you will be able to specify the four metrics required to parameterize the fish passage performance of each passage module in the Library. Click the Details buttons for more information on each input. These efficiencies must be completed for each Species object to simulate passage performance.'
        self.directions_lbl = tk.Label(self, text =self.directions_txt, font = TEXT_FONT, bg=DIRECTIONS_BG_COLOR, justify='left', anchor='w', wraplength=self.controller.wrap_length)
        self.add_species_subtitle = tk.Label(self, text='Add Species', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.add_species_frame = AddSpeciesFrame(self, self.controller)
        self.eff_species_subtitle = tk.Label(self, text='Input Module Attributes', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.fish_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.fish_frame.grid_columnconfigure((0,1,2,3,4), weight=1)        
        
        self.page_title.pack(fill='x', padx=0, pady=0)
        self.directions_lbl.pack(fill='x', padx=0, pady=5)
        self.add_species_subtitle.pack(fill='x', padx=0, pady=5)
        self.add_species_frame.pack(fill='x', padx=5, pady=5)
        self.eff_species_subtitle.pack(fill='x', padx=0, pady=5)
        self.fish_frame.pack(fill='x', padx=0, pady=5)
        
    #Check the entry values and add the passage metrics to each module. Screens can only take guidance and mortality metrics
    def submit_effs(self):
        species_name = self.species_var.get()
        if len(species_name) > 0:
            for mod_name in self.mod_entries.keys():
                guide = check_entry(self.mod_entries[mod_name][1].get(), [float])
                mort = check_entry(self.mod_entries[mod_name][2].get(), [float])
                if len(self.mod_entries[mod_name])>3:
                    entr = check_entry(self.mod_entries[mod_name][3].get(), [float])
                    pass_eff = check_entry(self.mod_entries[mod_name][4].get(), [float])
                    vals = [guide, mort, entr, pass_eff]
                else:
                    vals = [guide, mort]
                if ('Error' in vals) or ('' in vals):
                    tk.messagebox.showerror('Error', 'Please make sure that numbers have been input corrently into each efficiency entry.')
                    return
                else:
                    if len(vals) > 2:
                        self.controller.mod_lib.get_mod_by_name(mod_name).add_fish_effs(species_name, guide/100.0, mort/100.0, entr/100.0, pass_eff/100.0)
                    else:
                        self.controller.mod_lib.get_screen_by_name(mod_name).add_fish_effs(species_name, guide/100.0, mort/100.0)
            tk.messagebox.showinfo('Success', 'Successfully submitted fish model efficiencies')
        else:
            tk.messagebox.showerror('Error', 'Please select a species.')
    
    #When a species is added, update the corresponding option menu
    def species_updated(self):
        if self.first == True:
            self.select_species_lbl = tk.Label(self.fish_frame, text='Select a species to configure', font=TEXT_FONT, bg=FRAME_BG_COLOR)
            self.species_menu = tk.OptionMenu(self.fish_frame, self.species_var, *[x.name for x in self.controller.species_list])
            self.species_var.trace('w', self.update_fish_eff_frame)
            self.submit_btn = tk.Button(self.fish_frame, text='Submit Efficiencies', font=TEXT_FONT,command=lambda:self.submit_effs())
            self.entries_frame = tk.Frame(self.fish_frame, bg=FRAME_BG_COLOR)
            
            self.select_species_lbl.grid(row=0, column=0, columnspan=2, sticky='nsew', padx=5, pady=5)
            self.species_menu.grid(row=0, column=2, columnspan=1, sticky='nsew', padx=5, pady=5)
            self.entries_frame.grid(row=1, column=0, columnspan=3 )
            self.submit_btn.grid(row=2, column=0,columnspan=3, padx=5, pady=5, sticky='nsew')
        
            self.species_var.set(self.controller.species_list[0].name) #Triggers update_fish_eff_frame
            self.first=False
        else:
            self.species_menu.destroy()
            self.species_menu = tk.OptionMenu(self.fish_frame, self.species_var, *[x.name for x in self.controller.species_list])
            self.species_menu.grid(row=0, column=2, columnspan=1, sticky='nsew', padx=5, pady=5)


    #When a new species is added, update the frame that inputs the fish passage metrics for a selected species
    def update_fish_eff_frame(self, name=0, indx=0, op=0):
        species_name = self.species_var.get()
        if len(species_name) == 0: #If no species entered, then don't update
            return
        for widget in self.entries_frame.winfo_children():
            widget.destroy()
        self.mod_entries = {}
        lbl_list = ['Module Name', 'Downstream Guidance Efficiency', 'Downstream Mortality Rate', 'Upstream Entrance Efficiency', 'Upstream Passage Efficiency']
        self.header_lbls = []
        self.tool_btns = []
        self.wrap_length = 140

        for i in range(0, len(lbl_list)): #Headers
            self.header_lbls.append(tk.Label(self.entries_frame, text=lbl_list[i], font=TEXT_FONT, bg=FRAME_BG_COLOR, wraplength=self.wrap_length))
            self.header_lbls[i].grid(row=0, column=i, sticky='nsew', padx=5, pady=5)
    
        for i in range(1, len(lbl_list)): #Tool tip buttons
            self.tool_btns.append(tk.Button(self.entries_frame, text='Details', font=TEXT_FONT, command=lambda tool_text=lbl_list[i]:tool_click(self, tool_text)))
            self.tool_btns[i-1].grid(row=1, column=i, sticky='nsew', padx=5, pady=5)
    
        row_counter = 2
        self.pass_mods_list = self.controller.mod_lib.pass_mods_list
        for i in range(0, len(self.pass_mods_list)):
            mod_name = self.pass_mods_list[i].name
            self.mod_entries[mod_name] = []
            
            #Create entries and labels
            self.mod_entries[mod_name].append(tk.Label(self.entries_frame, text=mod_name, font=TEXT_FONT, bg=FRAME_BG_COLOR))
            for j in range(0, 4):
                self.mod_entries[mod_name].append(ttk.Entry(self.entries_frame, width=self.entry_width))

            #Place the entries and labels in the grid
            for j in range(0, len(self.mod_entries[mod_name])):
                self.mod_entries[mod_name][j].grid(row=row_counter, column=j, padx=5,pady=5, sticky='nsew')
            row_counter +=1
            #Add default inptus
            if type(self.pass_mods_list[i].guide_effs) == dict:
                if species_name in self.pass_mods_list[i].guide_effs.keys():
                    self.mod_entries[mod_name][1].insert(0, str(self.pass_mods_list[i].guide_effs[species_name]*100))
                    self.mod_entries[mod_name][2].insert(0, str(self.pass_mods_list[i].mort_rates[species_name]*100))
                    self.mod_entries[mod_name][3].insert(0, str(self.pass_mods_list[i].entr_effs[species_name]*100))
                    self.mod_entries[mod_name][4].insert(0, str(self.pass_mods_list[i].pass_effs[species_name]*100))
                elif self.pass_mods_list[i].module_class == 'Fish':
                    self.mod_entries[mod_name][1].insert(0, '0')
                    self.mod_entries[mod_name][2].insert(0, '0')
                    self.mod_entries[mod_name][3].insert(0, '100')
                    self.mod_entries[mod_name][4].insert(0, '100')
                else:
                    self.mod_entries[mod_name][1].insert(0, '0')
                    self.mod_entries[mod_name][2].insert(0, '100')
                    self.mod_entries[mod_name][3].insert(0, '0')
                    self.mod_entries[mod_name][4].insert(0, '0')
            elif self.pass_mods_list[i].module_class == 'Fish':
                self.mod_entries[mod_name][1].insert(0, '0')
                self.mod_entries[mod_name][2].insert(0, '0')
                self.mod_entries[mod_name][3].insert(0, '100')
                self.mod_entries[mod_name][4].insert(0, '100')
            else:
                self.mod_entries[mod_name][1].insert(0, '0')
                self.mod_entries[mod_name][2].insert(0, '100')
                self.mod_entries[mod_name][3].insert(0, '0')
                self.mod_entries[mod_name][4].insert(0, '0')
        
        self.screens_list = self.controller.mod_lib.screens_list
        for i in range(0, len(self.screens_list)):
            #Create entries and labels
            mod_name = self.screens_list[i].name
            self.mod_entries[mod_name] = []
            
            #Create entries and labels
            self.mod_entries[mod_name].append(tk.Label(self.entries_frame, text=mod_name, font=TEXT_FONT, bg=FRAME_BG_COLOR))
            for j in range(0, 2):
                self.mod_entries[mod_name].append(ttk.Entry(self.entries_frame, width=self.entry_width))

            #Place the entries and labels in the grid
            for j in range(0, len(self.mod_entries[mod_name])):
                self.mod_entries[mod_name][j].grid(row=row_counter, column=j, padx=5,pady=5, sticky='nsew')
            row_counter += 1
            
            #Default screen guidance efficiency and mortality
            if type(self.screens_list[i].guide_effs) == dict:
                if species_name in self.screens_list[i].guide_effs.keys():
                    self.mod_entries[mod_name][1].insert(0, str(self.screens_list[i].guide_effs[species_name]*100))
                    self.mod_entries[mod_name][2].insert(0, str(self.screens_list[i].mort_rates[species_name]*100))
                else:
                    self.mod_entries[mod_name][1].insert(0, '100')
                    self.mod_entries[mod_name][2].insert(0, '0')
            else:
                    self.mod_entries[mod_name][1].insert(0, '100')
                    self.mod_entries[mod_name][2].insert(0, '0')
                                                     
#Add Species Frame - Creates the inputs needed for 
class AddSpeciesFrame(tk.Frame):
    def __init__(self, parent, controller):  
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.parent = parent
        self.controller = controller
        self.page_name = 'Add Species'
        self.columnconfigure((0,1), weight =3)
        self.columnconfigure(2, weight=1)
        self.entry_width = 39
        
        #attribute name: [[input info], unit, data validate, [support tool names], is_optional boolean]
        self.input_dict = {'Species Name': [['text entry'], '', [str], [], False], \
                           'Relative Discharge Parameter (a)': [['text entry'], '', [float], ['Attraction Efficiency Model'], False], \
                           'Attraction Sensitivity Parameter (b)': [['text entry'], '', [float], ['Attraction Efficiency Model'], False], \
                           'Upstream Migratory Months': [['month box'], '', [], [], True], \
                           'Downstream Migratory Months': [['month box'], '', [], [], True]}
        
        self.att_labels, self.att_entries, self.att_units, self.att_tools, self.input_vars = create_inputs(self, self, self.input_dict, self.entry_width)
        self.add_btn = tk.Button(self, text='Add', font=TEXT_FONT,command=lambda:self.add())
        pack_attributes(self, self, 0)
        self.add_btn.grid(row=5,rowspan=1, column=1,columnspan=2, padx=5, pady=5)       
        self.set_defaults()
        
    #Set default species values
    def set_defaults(self):
        self.att_entries['Relative Discharge Parameter (a)'].insert(0, '0.8')
        self.att_entries['Attraction Sensitivity Parameter (b)'].insert(0, '0.05')
        self.att_entries['Upstream Migratory Months'].set_values([2,3,4,5,6])
        self.att_entries['Downstream Migratory Months'].set_values([9,10,11,12])
        
    #Check for input errors, create species, and add to species list
    def add(self):
        ad = get_values(self)
        if ad is False:
            return False
        species_name_list = [x.name for x in self.controller.species_list]
        if (ad['Species Name'] == 'Error') or (ad['Species Name'] in species_name_list) or ('Error' in [ad['Downstream Migratory Months'],ad['Attraction Sensitivity Parameter (b)']]):
            tk.messagebox.showerror('Error', 'Unable to add species. Please make sure that species name is unique and that at least one month is selected.')
        else:
            self.controller.species_list.append(mc.Species(ad['Species Name'], ad['Upstream Migratory Months'], ad['Downstream Migratory Months'], ad['Relative Discharge Parameter (a)'], ad['Attraction Sensitivity Parameter (b)']))
            self.controller.species_added()
            tk.messagebox.showinfo('Success', 'Species added successfully. Select the species in the drop down menu in the Input Module Attributes frame to configure the efficiencies.')

#%%## ADD SCREEN PAGE - add a screen object to the module library
class AddScreenPage(tk.Frame):
    def __init__(self, parent, controller):  
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.parent = parent
        self.controller = controller
        self.page_name = 'Add Screen'
        self.columnconfigure((0,1), weight=1)
        self.entry_width = 20
        self.directions_txt = 'Directions: Trash racks, fish screens, booms, and other screen like objects can be added using a Screen Object. This object is parameterized like a Dynamic module by setting equations for costs, head loss, and dimensions according to controlling variables. Prior to simulation, the screens will be designed according to the parameters of the modules that the screen is covering. Within the simulation, the screens can generate head losses for each covered module according to the provided equations.'
        
        self.title_lbl = tk.Label(self, text='Add a Screen', font=PG_TITLE_FONT, bg=TITLE_BG_COLOR)
        self.directions_lbl = tk.Label(self, text=self.directions_txt, font=TEXT_FONT, bg=DIRECTIONS_BG_COLOR,justify='left', anchor='w', wraplength=self.controller.wrap_length)
        self.att_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.cmod_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.create_btn = tk.Button(self, text='Create Screen', font=TEXT_FONT, command=lambda:self.create_screen())
        self.lib_title = tk.Label(self, text='Screen Library', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.screen_lib = ScreenLibraryFrame(self, self.controller)
        self.clean_btn = tk.Button(self, text='Clear All Screens', font=TEXT_FONT, command=lambda:self.clear_screens())
        self.att_title = tk.Label(self.att_frame, text='Select Attributes', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)

        self.title_lbl.grid(row=0, column=0, columnspan=2, pady=0, sticky='nsew')
        self.directions_lbl.grid(row=1, column=0, columnspan=2, pady=0, sticky='nsew')
        self.att_frame.grid(row=2, column=0, columnspan=2, pady=0, sticky='nsew')
        self.cmod_frame.grid(row=3, column=0, columnspan=2,pady=5, sticky='nsew')
        self.create_btn.grid(row=4, column=0, columnspan=2, padx=5, pady=5,sticky='nsew')
        self.lib_title.grid(row=5, column=0, columnspan=2, padx=5, pady=5,sticky='nsew')
        self.screen_lib.grid(row=6, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')
        self.clean_btn.grid(row=7, column=0, columnspan=2, padx=5, pady=5,sticky='nsew')
        
        self.def_screen_dict = {'0.75mm':csf.get_75in_screen_dict()}
        self.default_var = tk.StringVar()
        self.default_lbl = tk.Label(self.att_frame, text='Optional default*', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        menu_opts = list(self.def_screen_dict.keys())
        self.default_menu = tk.OptionMenu(self.att_frame,self.default_var, *menu_opts)
        self.default_var.trace('w', self.on_default_menu_switch)
        self.cmod_vars = {} #Covered modules variables
        
        #attribute name: [[input info], unit, data validate, [support tool names], is_optional boolean]       
        self.input_dict = {'Name':[['text entry'], '', [str], [], False],\
                       'Capital Cost':[['Optional'], '$', [float], [], False],\
                       'Annual Operating Cost':[['Optional'], '$', [float], [], False],\
                       'Head Loss':[['Optional'], 'ft', [float], ['Screen Head Loss Tool'], False],\
                       'Screen Width':[['Optional'], 'ft2', [float], ['Screen Width Angle Tool'], False], \
                       'Screen Height':[['Optional'], 'ft', [float], [], False], \
                       'Fractional Open Area': [['text entry'], '0-1', [float], [], True], \
                       'Vertical Angle': [['text entry'], 'deg', [float], [], True], \
                       'Bottom Elevation':[['text entry'], 'ft', [float], [], True]}
        #Controlling variables
        self.my_cvars = {'Capital Cost':['Total Area', 'Design Flow'], \
                         'Annual Operating Cost':['Total Area', 'Design Flow'], \
                         'Head Loss':['Active Area', 'Op. Flow', 'Active Area and Op. Flow'], \
                         'Screen Width':['Module Width', 'Stream Width'], \
                         'Screen Height': ['NOL']}
        
        self.att_labels, self.att_entries, self.att_units, self.att_tools, self.input_vars = create_inputs(self, self.att_frame, self.input_dict, self.entry_width, 'Screen', self.my_cvars)
        self.pack_attributes()
        self.update_cover_mod_frame()
        
    #Remove screens from module library and update
    def clear_screens(self):
        self.controller.mod_lib.clear_screens()
        self.screen_lib.update()
        
    #When the menu changes to a new default object, then update the default values
    def on_default_menu_switch(self, name='', indx='', op=''):
        if self.default_var.get() != '':
            screen_dict = self.def_screen_dict[self.default_var.get()]
            for key in list(self.att_labels.keys()):
                input_type = self.input_dict[key][0][0]
                if input_type == 'text entry':
                    clear_entries([self.att_entries[key]])
                    self.att_entries[key].insert(0, str(screen_dict[key]))
                elif input_type == 'OptionMenu':
                    self.input_vars[key].set(screen_dict[key]) #Make sure this works fine        
                elif input_type == 'Equation':
                    self.att_entries[key].update_equation(screen_dict[key])
                elif input_type == 'month box':
                    self.att_entries[key].set_values(screen_dict[key])
                elif input_type == 'checkbox':
                    if screen_dict[key] is True:
                        self.input_vars[key].set(True)
                    else:
                        self.input_vars[key].set(False)
                elif input_type == 'Optional':
                    self.att_entries[key].update(screen_dict[key])

    #Update the list of modules that can be covered
    def update_cover_mod_frame(self): 
        for widget in self.cmod_frame.winfo_children():
            widget.destroy()        
        self.cmod_vars = {} #stores the boolean vars
        self.mod_dict = {} #stores the checkbuttons
        mod_name_list = self.controller.mod_lib.get_name_list(passage_only=True)
        cmod_title = tk.Label(self.cmod_frame, text='Covered Modules', font=SUBTITLE_FONT, bg=LABEL_BG_COLOR)
        cmod_title.pack(fill='x')
        for i in range(0, len(mod_name_list)):
            self.cmod_vars[mod_name_list[i]] = tk.BooleanVar()
            self.mod_dict[mod_name_list[i]] = tk.Checkbutton(self.cmod_frame, text=mod_name_list[i], variable=self.cmod_vars[mod_name_list[i]], onvalue=True, offvalue=False, bg=FRAME_BG_COLOR, anchor='w')
            self.mod_dict[mod_name_list[i]].pack(fill='x', anchor='center')
            if self.controller.mod_lib.get_mod_by_name(mod_name_list[i]).module_class == 'Gen': #Defaults to turning on only generation modules
                self.cmod_vars[mod_name_list[i]].set(True)
        
    #Get the list of module names that are check in the cover mod frame
    def get_cover_mod_list(self):
        out_list = []
        for key in self.cmod_vars:
            if self.cmod_vars[key].get() == True:
                out_list.append(key)
        return out_list    
        
    #Check inputs, create screen, and add to module library
    def create_screen(self):
        ad = get_values(self)
        if ad is False:
            return False
        #Check for conflicting names
        if self.controller.mod_lib.check_name_in_screens(ad['Name']):
            tk.messagebox.showerror('Error', 'Screen name already used in the Library')
            return False
        try:
            out_screen = mc.Screen(ad['Name'],ad['Capital Cost'], ad['Annual Operating Cost'], ad['Head Loss'], ad['Screen Width'], ad['Screen Height'], self.get_cover_mod_list(),fractional_open_area=ad['Fractional Open Area'], vertical_angle=ad['Vertical Angle'], bottom_elevation=ad['Bottom Elevation'])
            self.controller.mod_lib.add_screen(out_screen)
            self.screen_lib.update()
            self.controller.screen_added()
            tk.messagebox.showinfo('Success', 'Successfully added a screen to the library.')
        except:
            tk.messagebox.showerror('Error', 'Unable to create screen. Please make sure all attributes are entered properly and the screen covers at least one type of module.')

    #Pack the default menu and then use the pack_attribute function to place all entries
    def pack_attributes(self):
        self.att_frame.columnconfigure((0,1,2,3), weight=1)
        self.att_title.grid(row=0, column=0, columnspan=4, pady=5, stick='nsew')
        self.default_lbl.grid(row=1,column=0, pady=5, sticky='nse')
        self.default_menu.grid(row=1,column=1, pady=5, sticky='nsew')
        pack_attributes(self, self, 2)
        
#On the screen page, keeps a list of the screens that have been created
class ScreenLibraryFrame(tk.Frame):
    def __init__(self, parent, controller):  
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.parent = parent
        self.controller = controller
        self.page_name = 'Screen Library'
        self.columnconfigure((0,1,2,3), weight=1)
        self.entry_width = 20     
        
        self.label_list = []
        self.view_btn_list = []
        self.clear_btn_list = []
        self.update()
        
    #Update the list of a screens when a new screen is added
    def update(self):
        self.label_list = []
        self.view_btn_list = []
        self.clear_btn_list = []
        for widget in self.winfo_children():
            widget.destroy() 
        for screen in self.controller.mod_lib.screens_list:
            self.label_list.append(tk.Label(self, text=screen.name, font=TEXT_FONT, bg=MODULE_COLORS['Screen']))
            self.view_btn_list.append(tk.Button(self, text='View', font=TEXT_FONT, command=lambda key=screen.name:self.view_screen(key)))
            self.clear_btn_list.append(tk.Button(self, text='Delete', font=TEXT_FONT, command=lambda key=screen.name:self.delete_screen(key)))
        self.pack_attributes()
        
    #Pack all screen labels and buttons
    def pack_attributes(self):
        for i in range(0, len(self.label_list)):
            self.label_list[i].grid(row=i, column=0,columnspan=2, sticky='nsew', padx=5, pady=5)
            self.view_btn_list[i].grid(row=i, column=2, sticky='nsew', padx=5, pady=5)
            self.clear_btn_list[i].grid(row=i, column=3, sticky='nsew', padx=5, pady=5)
            
    #View screen characteristics in tableviewer
    def view_screen(self, screen_name):
        df = self.controller.mod_lib.get_screen_by_name(screen_name).get_df(units=True)
        Tableviewer(self, self.controller, df,show_index=True)
    
    #Remove screen and update frame
    def delete_screen(self, screen_name):
        self.controller.mod_lib.clear_screens(screen_name)
        self.update()
        
    
#%%## COST PAGE - Retrieves cost data and creates cost object
class CostsPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.controller = controller
        self.page_name = 'Cost Tables'
        self.columnconfigure((0,1,2,3), weight=1)
        self.entry_width = 10
        self.direction_txt = 'Directions: Use this page to input your expected cost parameters, which will be used in the simulation for quantifying economic performance. Several inputs can be entered as either a lump sum or as a percent of ICC (initial capital costs), which is the sum of capital assets (e.g., turbines). The tool tips on the right can provide more information on each input. When not using an input, please set the value to 0.'
        
        self.page_title = tk.Label(self, text = self.page_name, font = PG_TITLE_FONT, bg=TITLE_BG_COLOR) 
        self.directions_lbl = tk.Label(self, text = self.direction_txt, font = TEXT_FONT, bg=DIRECTIONS_BG_COLOR, anchor='w', justify='left', wraplength=self.controller.wrap_length) 
        self.import_btn = tk.Button(self, text='Import from waterSHED Workbook', font=TEXT_FONT, command=lambda:self.controller.import_watershed_workbook('Costs'))
        self.submit_btn = tk.Button(self, text='Submit Costs',font=TEXT_FONT, command=lambda:self.create_costs())
        
        #attribute name: [[input info], unit, data validate, [support tool names], is_optional boolean]
        self.input_dict = {'Energy Price': [['text entry'], '$/MWh', [float], [], False], \
                          'Excavation Rate': [['text entry'], '$/ft2', [float], [], True], \
                          'Additional Capital Costs': [['text entry'], '$', [float], [], True], \
                          'Additional Non-Capital Costs': [['text entry'], '$', [float], [], True], \
                          'Overhead Cost': [['text entry'], ['($) Total Cost', '(%) Percent of ICC'], [float], [], True], \
                          'Engineering Cost': [['text entry'], ['($) Total Cost', '(%) Percent of ICC'], [float], [], True], \
                          'Contingency Allowance': [['text entry'], ['($) Total Cost', '(%) Percent of ICC'], [float], [], True], \
                          'Value of Recreation': [['text entry'], '$/hr', [float], [], True], \
                          'Annual O&M Cost': [['text entry'], ['($) Total Cost', '(%) Percent of ICC'], [float], [], True], \
                          'Flood Cost': [['text entry'], '$/cfs', [float], [], True], \
                          'Discount Rate': [['text entry'], '%', [float], [], False], \
                          'Project Life': [['text entry'], 'yr', [float], [], False]}
        
        self.att_labels, self.att_entries, self.att_units, self.att_tools, self.input_vars = create_inputs(self, self, self.input_dict, self.entry_width)
        self.pack_attributes()  
        
    #Pack surrounding objects and the inputs using the pack_attributes function
    def pack_attributes(self):
        self.page_title.grid(row=0, column=0, columnspan=4, sticky='nsew')
        self.directions_lbl.grid(row=1, column=0, columnspan=4, pady=5, sticky='nsew')
        self.import_btn.grid(row=2, column=0, columnspan=4, pady=5)
        pack_attributes(self, self, 3)
        for key in self.att_labels:
            if type(self.input_dict[key][1]) == list:
                self.att_units[key].config(width=14)
        self.submit_btn.grid(row=16, column=0, columnspan=4, pady=5,padx=5, sticky='nsew')   
        
    #Check inputs, create cost table, and add it to controller
    def create_costs(self):
        ad = get_values(self)
        if ad is False:
            return False
        for key in self.att_labels:            
            unit = self.input_dict[key][1]
            if type(unit) == list:
                ad[key] = [ad[key], self.input_vars[key].get()]
                
        self.controller.costs = mc.Cost_tables(ad['Energy Price'], excavation_cost=ad['Excavation Rate'],\
                        overhead_cost=ad['Overhead Cost'], engineering_cost=ad['Engineering Cost'],\
                            contingency_cost=ad['Contingency Allowance'], recreation_price=ad['Value of Recreation'],\
                                flood_price =ad['Flood Cost'],om_costs=ad['Annual O&M Cost'], discount_rate=ad['Discount Rate'], \
                                    project_life=ad['Project Life'], add_capital=ad['Additional Capital Costs'], add_noncapital=ad['Additional Non-Capital Costs'])
        
        tk.messagebox.showinfo('Success', 'Succesfully created the cost table!')
        self.controller.costs_added()
        
    #Update cost entries with existing cost table
    def costs_added(self):
        cost_table = self.controller.costs
        cost_df = cost_table.get_df().reset_index()
        clear_entries(list(self.att_entries.values()))
        for i in range(0, len(cost_df)):
            key = cost_df['Attribute'][i]
            self.att_entries[key].insert(0, cost_df['Value'][i])
            if type(self.input_dict[key][1]) == list:
                self.input_vars[key].set(cost_df['Units'][i])
        
        

#%%## PREFERENCES PAGE - Retrieves design preferences and creates Facilitiy_preferences object 
class PreferencesPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.controller = controller
        self.page_name = 'Preferences'
        self.columnconfigure((0,1,2,3), weight=1)
        self.entry_width = 12
        self.op_entry_width = 5
        self.direction_txt = 'Directions: In this page you can input your design, operation, and simulation preferences, which will be used in the design optimization process.'
        self.mod_list = ['Generation', 'Sediment Passage', 'Aquatic Species', 'Recreation', 'Water Passage']
        self.cl_list = ['Gen', 'Sed', 'Fish', 'Rec', 'Wat']
        
        self.page_title = tk.Label(self, text = self.page_name, font = PG_TITLE_FONT, bg=TITLE_BG_COLOR) 
        self.directions_lbl = tk.Label(self, text = self.direction_txt, font = TEXT_FONT, bg=DIRECTIONS_BG_COLOR, anchor='w', justify='left', wraplength=self.controller.wrap_length)
        self.import_btn = tk.Button(self, text='Import from waterSHED Workbook', font=TEXT_FONT, command=lambda:self.controller.import_watershed_workbook('Preferences'))
        
        #attribute name: [[input info], unit, data validate, [support tool names], is_optional boolean]
        self.input_dict = {'Normal Operating Level': [['text entry'], 'ft', [float], [], False], \
                          'Test Data Start Date': [['text entry'], '(YYYY-MM-DD)', [str], [], False], \
                          'Test Data End Date': [['text entry'], '(YYYY-MM-DD)', [str], [], False], \
                          'Generation Dispatch Mode': [['OptionMenu', ['Design Ramping', 'Peak Ramping', 'Simple Greedy', 'Advanced Greedy']], '', [], [], False], \
                          'Allow Turbine Over-run': [['checkbox', 'Y/N'],'', [], [], False], \
                          'Spillway Notch Flow': [['text entry'], 'cfs', [float], [], True], \
                          'Spillway Minimum Flow': [['text entry'], ['cfs (Constant)', '% (Percent of inflow)'], [float], [], True]}
        
        self.att_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.att_labels, self.att_entries, self.att_units, self.att_tools, self.input_vars = create_inputs(self, self.att_frame, self.input_dict, self.entry_width)
        self.att_units['Spillway Minimum Flow'].config(width=15)
        self.att_entries['Generation Dispatch Mode'].config(width=self.entry_width)
        self.rank_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.rank_directions_lbl = tk.Label(self.rank_frame, text = 'Rank the module classes in terms of operational priority\n (1-first to turn on, 5-last to turn on)', font=TEXT_FONT, bg=SUBTITLE_BG_COLOR)
        
        #Create the module class priority ranking
        self.rank_lbls = {}
        self.rank_entries = {}
        self.rank_frame.columnconfigure((0,1), weight=1)
        self.rank_directions_lbl.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')
        row=1
        for i in self.mod_list:
            self.rank_lbls[i] = tk.Label(self.rank_frame, text=i, font=TEXT_FONT, bg=FRAME_BG_COLOR)
            self.rank_entries[i] = ttk.Entry(self.rank_frame, width=self.op_entry_width)
            self.rank_entries[i].insert(0, str(row))
            self.rank_entries[i].grid(row=row, column=1, padx=5, pady=5, sticky='nsw')
            self.rank_lbls[i].grid(row=row, column=0, sticky='nse')
            row += 1
        self.submit_btn = tk.Button(self, text='Submit Preferences',font=TEXT_FONT, command=lambda:self.create_preferences())

        self.page_title.pack(fill='x')
        self.directions_lbl.pack(fill='x', pady=5)
        self.import_btn.pack(pady=5)
        self.att_frame.pack(fill='x')
        self.rank_frame.pack(fill='x')
        self.submit_btn.pack(pady=5)

        self.att_frame.columnconfigure((0,1,2,3), weight=1)
        pack_attributes(self, self.att_frame, 1)
                
    #Get the list of module class opreation priorities
    def get_op_priority(self):
        op_rank = []
        out_list = []
        for key in self.rank_entries.keys():
            op_rank.append(check_entry(self.rank_entries[key].get(), [int]))
        for i in range(1, 6):
            if type(op_rank[i-1]) != int:
                tk.messagebox.showerror('Error', 'Incorrect operation priority input, please put an integer')
                return False
            else:
                for j in range(0, len(op_rank)):
                    if op_rank[j] == i:
                        out_list.append(self.cl_list[j])
                        break
        if len(out_list) != 5:
            tk.messagebox.showerror('Error', 'Incorrect operation priority input, the numbers 1-5 are input properly')
            return False
        return out_list
                        
    #Check inputs, create preferences object, add it to controller class
    def create_preferences(self):
        ad = get_values(self)
        if ad is False:
            return False
        
        op_ranks = self.get_op_priority()
        if op_ranks is False:
            return
        try:
            ad['Test Data Start Date'] = pd.to_datetime(ad['Test Data Start Date'])
            ad['Test Data End Date'] = pd.to_datetime(ad['Test Data End Date'])
        except:
            tk.messagebox.showerror('Error', 'Unable to interpret start and end dates.')
            return
        
        self.controller.preferences = mc.Facility_preferences(op_ranks, ad['Normal Operating Level'], \
                                                              ad['Test Data Start Date'], ad['Test Data End Date'], \
                                                                  ad['Allow Turbine Over-run'], ad['Spillway Minimum Flow'], self.input_vars['Spillway Minimum Flow'].get(), ad['Spillway Notch Flow'], ad['Generation Dispatch Mode'])
        tk.messagebox.showinfo('Success', 'Successfully added preferences.')
        self.controller.preferences_added()
        
    #Update entries when a preference object is added
    def preferences_added(self):
        prefs = self.controller.preferences
        pref_df = prefs.get_df()
        for key in self.input_dict:
            entry_type = self.input_dict[key][0][0]
            if entry_type == 'text entry':
                clear_entries([self.att_entries[key]])
                self.att_entries[key].insert(0, pref_df.loc[key]['Value'])
            elif entry_type == 'OptionMenu':
                self.input_vars[key].set(pref_df.loc[key]['Value'])
            elif entry_type == 'checkbox':
                if key == 'Allow Turbine Over-run':
                    if prefs.allow_overrun == True:
                        self.input_vars[key].set(1)
                    else:
                        self.input_vars[key].set(0)
        clear_entries(list(self.rank_entries.values()))
        for rank in range(0, 5):
            for cl in range(0, 5):
                if prefs.op_rules[rank] == self.cl_list[cl]:
                    self.rank_entries[self.mod_list[cl]].insert(0, str(rank+1))
                    
                    
#%%## Enumerate Page - allows the user to select the range of module counts and dynamic module attributes 
class EnumeratePage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.controller = controller
        self.page_name = 'Enumerate'
        self.columnconfigure((0,1), weight=1)
        self.entry_width = 8
        self.direction_txt = 'Directions: This page allows you to optimize facility designs by simply iterating through a small number of module combinations. You can select an objective function and set performance constaints in the sections below. For each module in the library, you must identify the module count or range of module counts. You must have at least one spillway and can only have one foundation and one non-overflow module. For dynamic modules, you can also specify the range and iterations of the control variables.'
        self.show_anim_var = tk.IntVar()
        self.default_bools = [True, False, False, False, False, False]
        
        self.page_title = tk.Label(self, text = self.page_name, font = PG_TITLE_FONT, bg=TITLE_BG_COLOR) 
        self.directions_lbl = tk.Label(self, text = self.direction_txt, font = TEXT_FONT, bg=DIRECTIONS_BG_COLOR, anchor='w', justify='left', wraplength=self.controller.wrap_length)     
        self.objectives_frame = ObjectiveSelectFrame(self, self.controller)
        self.save_bools_frame = SaveRunFrame(self, self.controller, self.default_bools)
        self.modselect_lbl = tk.Label(self, text ='Select Module Iterations', font = SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR) 
        self.modselect_frame = tk.Label(self,text='No modules have been created.', font=TEXT_FONT, bg=FRAME_BG_COLOR) #This modselect_frame starts as a label and is updated to a ModuleSelectFrame when modules are added              
        self.run_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.show_anim_chk = tk.Checkbutton(self.run_frame, text='Show Iterations', variable=self.show_anim_var,  onvalue=1, width=12, anchor='c', padx=3, bg=CHECK_BG_COLOR)
        self.submit_btn = tk.Button(self.run_frame, text='Run Enumeration',font=TEXT_FONT, command=lambda:self.run_enumeration())
        self.sensi_btn = tk.Button(self.run_frame, text='Run Sensitivity Analysis', font=TEXT_FONT, command=lambda:self.run_sensitivity())
        self.sim_results_lbl = tk.Label(self, text ='Simulation Results', font = SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR) 
        self.sim_results = tk.Label(self, text='Please create a facility by pressing the Run button to see results.', font = TEXT_FONT,bg=LABEL_BG_COLOR, wraplength=self.controller.wrap_length)
        self.best_fac_lbl = tk.Label(self, text='Optimal Facility Configuration', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.best_fac_frame = tk.Label(self, text='Please run the optimization algorithm to see results.', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.sens_results_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.pack_attributes()
        
    #Places objects in the frame
    def pack_attributes(self):
        self.page_title.grid(row=0, column=0, columnspan=2, padx=0, pady=0, sticky='nsew')
        self.directions_lbl.grid(row=1, column=0, columnspan=2, padx=0, pady=5, sticky='nsew')
        self.run_frame.grid(row=2, column=0, columnspan=2, sticky='nsew')
        self.objectives_frame.grid(row=3, column=0, columnspan=1, sticky='nsew', padx=5)
        self.save_bools_frame.grid(row=3, column=1, columnspan=1, sticky='nsew', padx=5)
        self.modselect_lbl.grid(row=4, column=0, columnspan=2, sticky='nsew')
        self.modselect_frame.grid(row=5, column=0, columnspan=2, sticky='nsew')
        self.best_fac_lbl.grid(row=7, column=0, columnspan=2, sticky='nsew')
        self.best_fac_frame.grid(row=8, column=0, columnspan=2, sticky='nsew')
        self.sim_results_lbl.grid(row=9, column=0, columnspan=2, sticky='nsew')
        self.sim_results.grid(row=10, column=0, columnspan=2, sticky='nsew')
        
        #In run_frame
        self.run_frame.columnconfigure((0,1,2), weight=1)
        self.show_anim_chk.grid(row=0, column=0, padx=5, pady=5, sticky='nse')
        self.submit_btn.grid(row=0, column=1, padx=5, pady=5, sticky='nsw')
        self.sensi_btn.grid(row=0, column=2, padx=5, pady=5, sticky='nsw')
        
    #Opens the sensitivity analaysis frame in a pop-up window
    def run_sensitivity(self):
        self.add_mod_popup = OneFrameWindow(self, self.controller, scroll=True)
        self.add_mod_popup.addFrame(SensitivityAnalysisFrame(self.add_mod_popup.frame_parent, self.controller, 'Enumerate', self.add_mod_popup))

    #When the sensitivity analysis is complete, update the sensitivity results frame
    def sensitivity_complete(self, variable_name):
        self.sens_results_frame.destroy()
        self.sens_results_frame = SensitivityResultsFrame(self,self.controller, variable_name)
        self.sens_results_frame.grid(row=11, column=0, columnspan=2, sticky='nsew')
        
    #Update the frame to select modules when a module is added
    def update_mod_select_frame(self):
        self.modselect_frame.destroy()
        self.modselect_frame = ModuleSelectFrame(self, self.controller, 'Enumerate')
        self.pack_attributes()
        
    #Gets the user selected parameter needed to run an enumeration
    def get_enumeration_parameters(self):
        #enum_lists = [required mods dict, list of passage mods, list of constant variables, list of iterated variables, dict of screen booleans]
        enum_lists = self.modselect_frame.get_enumerate_lists() 
        if enum_lists is False: #If there is an incorrect input
            return False
        objective = self.objectives_frame.get_obj()
        save_bools = self.save_bools_frame.get_bools()
        if self.show_anim_var.get() == 1:
            show_anim = True
        else:
            show_anim = False
        return objective, enum_lists, save_bools, show_anim
    
    #Runs the enumeration through the controller class
    def run_enumeration(self):
        enum_params = self.get_enumeration_parameters()
        if enum_params is False:
            return False
        else:
            self.controller.enumerate_facility(*enum_params)
 
    #When the enumeration is done, update the results and facility frame
    def enumeration_complete(self):
        self.best_fac = self.controller.enum_res[0]
        self.latest_res = self.controller.enum_res[1]
        self.update_results()

    #Update the results and facility frames
    def update_results(self):
        if self.latest_res is not False:
            self.sim_results.destroy()
            self.best_fac_frame.destroy()
            self.sim_results = SimResultsFrame(self, self.controller, self.latest_res)
            self.best_fac_frame = FacilityFrame(self, self.controller, self.best_fac)
            self.modselect_frame.update_modselect_frame(self.best_fac)
            self.pack_attributes()
        else:
            tk.messagebox.showerror('Error', 'Unable to gather results due to an error during simulation. Likely causes are due to tight head constraints or improper module inputs.')
    

#%%## MODULE SELECT SUBFRAME - Frame that allows user to select number in facility in customization page     
class ModParamSelectFrame(tk.Frame):
    def __init__(self, parent, controller, mod, counter, page_type):
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.controller = controller
        self.parent = parent
        self.mod = mod
        self.counter = counter
        self.bg_color = MODULE_COLORS[self.mod.module_class]
        self.wrap_length = 150
        self.entry_width = 15
        self.check_width = 12
        self.page_type = page_type
        self.att_type = 'checkbox'
        
        #Determines the inputs based on the module class, mods that can only have one will include checkboxes
        if self.mod.module_class == 'Non':
            self.att_obj = tk.Checkbutton(self,text='Non-overflow', var=self.parent.non_var, onvalue = self.counter, offvalue=-1, width=self.check_width)
        elif self.mod.module_class == 'Fou':
            self.att_obj = tk.Checkbutton(self, text='Foundation', var=self.parent.fou_var, onvalue = self.counter, offvalue=-1, width=self.check_width)
        elif self.mod.module_class == 'Sed':
            if self.mod.op_mode == 'Flushing':
                self.att_obj = tk.Checkbutton(self, text='Flushing', var=self.parent.flush_var, onvalue = self.counter, offvalue=-1, width=self.check_width)
            else:
                self.att_obj = EnumerateModParamsFrame(self, self.controller, mod, self.bg_color, self.page_type)
                self.att_type = 'frame'
        elif self.mod.module_class == 'Screen':
            self.on_var = tk.BooleanVar()
            self.att_obj = tk.Checkbutton(self, text='On/Off', var=self.on_var, onvalue = True, offvalue= False, width=self.check_width)
            self.on_var.set(True)
            self.att_type = 'on/off checkbutton'
        else:
            self.att_obj = EnumerateModParamsFrame(self, self.controller, mod, self.bg_color, self.page_type)
            self.att_type = 'frame'
        self.name_lbl = tk.Label(self, text = self.mod.name, font =TEXT_FONT, bg=self.bg_color, width=11, wraplength=self.wrap_length)
        self.view_btn = tk.Button(self, text ='View', font=TEXT_FONT, command=lambda:self.view_module())

        self.name_lbl.pack(side='left', fill='y')
        self.att_obj.pack(side='left', fill='both', expand=True, padx=5)
        self.view_btn.pack(side='right', fill='y')
    

    def update(self):
        self.parent.update()
       
    #View the module specifications in a table
    def view_module(self):
        Tableviewer(self, self.controller, self.mod.get_df(units=True), show_index=True)
        
    #Returns the module and a dict describing the attribute parameters
    def get_values(self):
        if self.att_type == 'on/off checkbutton':
            return self.on_var.get()
        elif self.att_type == 'frame':
            val_dict = self.att_obj.get_values()
            if val_dict is False:
                return False
            else:
                return  (self.mod, val_dict)
            
    #Set the value for the checkboxes for the required modules
    def set_value(self, value):
        if self.att_type == 'checkbox':
            if value == True:
                self.att_obj.toggle()    
    
#A frame used to get the enumeration attributes for each module that can be iterated or redesigned
class EnumerateModParamsFrame(tk.Frame):
    def __init__(self, parent, controller, mod, bg_color, page_type):
        tk.Frame.__init__(self, parent, bg=bg_color)
        self.parent = parent
        self.controller = controller
        self.mod = mod
        self.bg_color = bg_color
        self.page_type = page_type
        
        self.att_list = []
        self.att_list.append(ParamFrame(self, self.controller, self.mod, 'Module Count', self.bg_color, self.page_type))
        if self.mod.is_dynamic(): #Create a ParamFrame for each attribute that needs enumerated
            for key in self.mod.control_vars_dict: 
                if key not in ['Normal Operating Level', 'Mean Daily Flow', 'Number of Steps', 'Volume']: #These metrics are set during facility creation and are not iterable parameters
                    self.att_list.append(ParamFrame(self, self.controller, self.mod, key, self.bg_color, self.page_type))
                
        for i in range(0, len(self.att_list)):
            self.att_list[i].grid(row=i, column=0, padx=5,pady=5,sticky='nsw')
        
    #Get the attribute values or ranges from the ParamFrames
    def get_values(self):
        out_dict = {}
        for i in range(0, len(self.att_list)):
            val = self.att_list[i].get_values()
            if val is False:
                return False
            else:    
                out_dict.update({self.att_list[i].att_name: val})
        return out_dict
            
#For each attribute that can be enumerated, this is a frame that inputs the value as a constant or as a range of values with a min, max, and a step (enumeration only)
class ParamFrame(tk.Frame):
    def __init__(self, parent, controller, mod, att_name, bg_color, page_type):
        tk.Frame.__init__(self, parent, bg=bg_color)
        self.parent = parent
        self.controller = controller 
        self.mod = mod
        self.att_name = att_name
        self.bg_color = bg_color
        self.page_type = page_type
        self.entry_width = 5
        self.menu_var = tk.StringVar()
        
        self.att_lbl = tk.Label(self, text=self.att_name, font=TEXT_FONT, width=11, wraplength=140, bg=self.bg_color)
        
        if self.page_type == 'Optimize': #Optimization does not need a step input, so it is a range
            self.opts = ['Constant', 'Range']
        else:
            self.opts = ['Constant', 'Iterations'] #Enumeration has a min, max, and step so it is called iteration
        self.opt_menu = tk.OptionMenu(self, self.menu_var, *self.opts)
        self.opt_menu.configure(width=8)
        self.const_entry = ttk.Entry(self, width=self.entry_width)
        self.iter_frame = tk.Frame(self, bg=self.bg_color)        
        self.menu_var.trace('w', self.on_menu_switch)
        self.menu_var.set('Constant')

    #When the menu switches from constant to range/iteration, then need to change the entries and labels
    def on_menu_switch(self,name='', idx='', op=''):
        self.iter_frame.destroy()
        self.const_entry.destroy()
        self.att_lbl.grid(row=0, column=0)
        self.opt_menu.grid(row=0, column=1, sticky='nsw')
        if self.menu_var.get() == 'Constant':
            self.const_entry = ttk.Entry(self, width=self.entry_width)
            self.const_entry.grid(row=0, column=2,padx=5,pady=5, sticky='nsw')
            self.const_entry.insert(0, '1')
        else:
            if self.att_name == 'Module Count':
                defaults = [0, 10, 1] 
            elif self.att_name in list(self.mod.enum_limits.keys()):
                defaults = [self.mod.enum_limits[self.att_name][0], self.mod.enum_limits[self.att_name][1], round((self.mod.enum_limits[self.att_name][1]-self.mod.enum_limits[self.att_name][0])/10)]
            else:
                defaults = [0, 10, 1]
            if self.page_type == 'Optimize':
                self.iter_frame = RangeFrame(self, self.controller, self.bg_color, defaults)
            else:    
                self.iter_frame = IterFrame(self, self.controller, self.bg_color, defaults)
            self.iter_frame.grid(row=0, column=2, sticky='nsew')

    #Returns a tuple with (Constant or Range/Iteration, a dict with Min/Max/Step as the keys)
    def get_values(self):
        if self.menu_var.get() == 'Constant':
            if self.att_name == 'Module Count':    
                out_val = check_entry(self.const_entry.get(), [int])
            else:
                out_val = check_entry(self.const_entry.get(), [float])
            if (out_val == 'Error') or (out_val == ''):
                return False
            else:
                return ('Constant', out_val)
        else:
            iter_dict = self.iter_frame.get_values()
            if iter_dict is False:
                return False
            else:
                return (self.menu_var.get(), iter_dict)

#A frame that has the user input the min and maxfor an optimization range
class RangeFrame(tk.Frame):
    def __init__(self, parent, controller, bg_color, defaults=None, entry_width=5): #defaults = [min, max, step]
        tk.Frame.__init__(self, parent, bg=bg_color)
        self.controller = controller
        self.page_name = 'Range Frame'
        self.bg_color = bg_color
        self.defaults = defaults
        self.entry_width = entry_width
        self.columnconfigure((0,1,2,3), weight=1)
        self.rowconfigure((0),weight=1)
        self.min_lbl = tk.Label(self, text='Min', font=TEXT_FONT, bg=self.bg_color)
        self.max_lbl = tk.Label(self, text='Max', font=TEXT_FONT, bg=self.bg_color)
        self.min_entry = ttk.Entry(self, width=self.entry_width)
        self.max_entry = ttk.Entry(self, width=self.entry_width)
        self.min_lbl.grid(row=0, column=0, sticky='ns')
        self.min_entry.grid(row=0, column=1, sticky='ns')
        self.max_lbl.grid(row=0, column=2, sticky='ns')
        self.max_entry.grid(row=0, column=3, sticky='ns')
        
        if self.defaults is not None:
            self.set_entries(self.defaults)
        
    #Inputs given values into the entries
    def set_entries(self, inputs):
        clear_entries([self.min_entry, self.max_entry])
        self.min_entry.insert(0, str(inputs[0]))
        self.max_entry.insert(0, str(inputs[1]))
        
    #Returns a dict with Min and Max as the keys
    def get_values(self):
        out_min = check_entry(self.min_entry.get(), [float])
        out_max = check_entry(self.max_entry.get(), [float])
        if ('Error' in [out_min, out_max]) or ('' in [out_min, out_max]):
            return False
        else:
            return {'Min':out_min, 'Max':out_max}

#A frame that lets the user input a min, max, and step for an attribute enumeration
class IterFrame(tk.Frame):
    def __init__(self, parent, controller, bg_color, defaults=None, entry_width=5): #defaults = [min, max, step]
        tk.Frame.__init__(self, parent, bg=bg_color)
        self.controller = controller
        self.page_name = 'Iterations Frame'
        self.bg_color = bg_color
        self.defaults = defaults
        self.entry_width = entry_width
        self.columnconfigure((0,1,2,3,4,5), weight=1)
        self.rowconfigure((0),weight=1)
        self.min_lbl = tk.Label(self, text='Min', font=TEXT_FONT, bg=self.bg_color)
        self.max_lbl = tk.Label(self, text='Max', font=TEXT_FONT, bg=self.bg_color)
        self.step_lbl = tk.Label(self, text='Step', font=TEXT_FONT, bg=self.bg_color)
        self.min_entry = ttk.Entry(self, width=self.entry_width)
        self.max_entry = ttk.Entry(self, width=self.entry_width)
        self.step_entry = ttk.Entry(self, width=self.entry_width)
        self.min_lbl.grid(row=0, column=0, sticky='ns')
        self.min_entry.grid(row=0, column=1, sticky='ns')
        self.max_lbl.grid(row=0, column=2, sticky='ns')
        self.max_entry.grid(row=0, column=3, sticky='ns')
        self.step_lbl.grid(row=0, column=4, sticky='ns')
        self.step_entry.grid(row=0, column=5, sticky='ns')
        
        if self.defaults is not None:
            self.set_entries(self.defaults)
        
    #Enters given values into the entries
    def set_entries(self, inputs):
        clear_entries([self.min_entry, self.max_entry, self.step_entry])
        self.min_entry.insert(0, str(inputs[0]))
        self.max_entry.insert(0, str(inputs[1]))
        self.step_entry.insert(0, str(inputs[2]))
        
    #Returns a dict with the Min, Max, and Step as keys
    def get_values(self):
        out_min = check_entry(self.min_entry.get(), [float])
        out_max = check_entry(self.max_entry.get(), [float])
        out_step = check_entry(self.step_entry.get(), [float])
        if ('Error' in [out_min, out_max, out_step]) or ('' in [out_min, out_max, out_step]):
            return False
        else:
            return {'Min':out_min, 'Max':out_max, 'Step':out_step}
        
     
#%%## Sensitivity Results Frame - included within the Enumeration page, shows the results of the sensitivity analysis process
class SensitivityResultsFrame(tk.Frame):
    def __init__(self, parent, controller, variable_name):
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.parent = parent
        self.controller = controller
        self.page_name = 'Sensitivity Results Frame'
        self.var_name = variable_name
        self.columnconfigure((0,1,2), weight=1)
        self.orig_df = self.controller.sens_results
        self.results_df = self.controller.sens_results.copy()
        self.results_df.set_index('Metric', drop=True, inplace=True)
        self.results_df = self.results_df.apply(pd.to_numeric, errors='coerce')
        self.results_df.dropna(axis=0, how='all', inplace=True)
        self.y_opts = self.results_df.index.to_list()
        self.y_opts.remove(variable_name)
        plt.ioff()
        self.fig = plt.figure(figsize=(6,5))
        self.ax = self.fig.add_subplot(111)
        self.y_var = tk.StringVar()
        
        self.title_lbl = tk.Label(self, text='Sensitivity Results', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.fig_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.btn_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.menu_lbl = tk.Label(self.btn_frame, text='Select a Variable to Plot', font=TEXT_FONT, bg=FRAME_BG_COLOR, wraplength = 250)
        self.y_menu = tk.OptionMenu(self.btn_frame, self.y_var, *self.y_opts)
        self.figure_canvas = FigureCanvasTkAgg(self.fig, master=self.fig_frame)
        self.pop_out_btn = tk.Button(self.btn_frame, text='Pop-out Figure', font=TEXT_FONT, command=lambda: self.pop_figure())
        self.view_tbl_btn = tk.Button(self.btn_frame, text='View Table', font=TEXT_FONT, command=lambda: self.view_table())
        
        self.title_lbl.grid(row=0, column=0, columnspan=3, sticky='new', padx=5, pady=5)
        self.fig_frame.grid(row=1, column=0, columnspan=2, rowspan=3, sticky='nsew', padx=5, pady=5)
        self.btn_frame.grid(row=1, column=2, columnspan=1, sticky='nsew', padx=5, pady=5)
        
        self.menu_lbl.pack(fill='x', expand=True)
        self.y_menu.pack(fill='x', expand=True)
        self.pop_out_btn.pack(fill='x', expand=True)
        self.view_tbl_btn.pack(fill='x', expand=True)
        
        self.figure_canvas.get_tk_widget().pack(fill='x', expand=True)
        self.y_var.trace('w', self.on_menu_switch)
        self.y_var.set(self.y_opts[0])
    
    #View sensitivity analysis results in a tableviewer
    def view_table(self):
        Tableviewer(self, self.controller, self.orig_df)
    
    #Pop sensitivity results figure into another window with Matplotlib features
    def pop_figure(self):
        fig, ax = self.plot_sensitivity_figure(hide=False)
        
    #Creates a plot between the sensitivity variable (X) and the selected output metric
    def plot_sensitivity_figure(self, fig=None, ax=None, hide=True):
        if hide == False:
            plt.ion()
        else:
            plt.ioff()
            
        if fig is None:
            fig = plt.figure(constrained_layout=True)
        if ax is None:
            ax = fig.add_subplot(111)
        else:
            ax.clear()
            
        y_var = self.y_var.get()
        raw_x = list(self.results_df.loc[self.var_name])
        raw_y = list(self.results_df.loc[y_var])
        x = []
        y = []
        for i in range(0, len(raw_x)):
            if not (np.isnan(raw_x[i]) or np.isnan(raw_y[i])):
                x.append(float(raw_x[i]))
                y.append(float(raw_y[i]))

        if len(x) > 0:
            ax.clear()
            ax.scatter(x, y)
            ax.set_xlabel(self.var_name)
            ax.set_ylabel(y_var)
            
            if af.check_all_equal(y):
                out_text = 'No relationship'
            else:
                try:
                    eq_name = self.var_name + ' v. ' + y_var
                    out_eq = af.auto_regression(eq_name, self.results_df.transpose(), self.var_name, y_var)
                    if type(out_eq) == mc.Equation:
                        regr_ys = []
                        for i in x:
                            regr_ys.append(out_eq.get_y(i))
                        ax.plot(x, regr_ys)
                        out_text = eq_name + '\nEquation: ' + out_eq.get_text(digits=3) + '\nR2: ' + str(round(out_eq.regr_results['R2'], 3)) + '\nOutliers: ' +str(out_eq.regr_results['Outlier Count'])
                    elif type(out_eq) == str:
                        out_text = out_eq
                    else:
                        out_text = 'Unable to regress data'
                except:
                    out_text = 'Unable to regress data'
            ax.text(0.1, 0.1, out_text,transform=ax.transAxes)
            return fig, ax
        else:
            return False, False
        
    #Redraw the figure when the menu changes
    def on_menu_switch(self, name=None, idx=None, op=None):
        fig, ax = self.plot_sensitivity_figure(fig=self.fig, ax=self.ax, hide=True)
        if self.fig is not False:
            self.fig = fig
            self.ax = ax
            self.figure_canvas.draw()
            
      

#%%## Sensitivity Analysis Frame - within a OneFrameWindow - collects inputs and runs a sensitivity analysis. The results are reported in the EnumerationPage
class SensitivityAnalysisFrame(tk.Frame):
    def __init__(self, parent, controller, opt_type, window):
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.parent = parent
        self.controller = controller
        self.page_name = 'Sensitivity Analysis Frame'
        self.opt_type = opt_type
        self.window = window
        self.direction_txt = 'Directions: This tool will let you adjust certain site and module parameters over a set of iterations and then run the enumeration or optimization procedures with the changing parameter values to conduct sensitivity analysis. Please input any percentages as 0-100.'
        self.wrap_length = 790
        
        self.obj_var = tk.StringVar()
        self.obj_opts = self.get_object_list()
        if len(self.obj_opts)==0:
            tk.messagebox.showerror('Error', 'No objects have been created that can be varied during sensitivity analysis. Please make sure you have pressed the submit button on each page.')
            self.destroy()

        self.par_var = tk.StringVar()
        self.par_opts = ['']
        self.unit_var = tk.StringVar()
        self.unit_opts = ['']
        
        self.title_lbl = tk.Label(self, text='Sensitivity Analysis', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.directions_lbl = tk.Label(self, text = self.direction_txt, font = TEXT_FONT, bg=DIRECTIONS_BG_COLOR, anchor='w', justify='left', wraplength=self.wrap_length)     
        self.step1_lbl = tk.Label(self, text='Step 1. Select an object to iterate.', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.object_menu = tk.OptionMenu(self, self.obj_var, *self.obj_opts)
        self.step2_lbl = tk.Label(self, text='Step 2. Select an parameter to iterate.', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.par_menu = tk.OptionMenu(self, self.par_var, *self.par_opts)
        self.unit_menu = tk.OptionMenu(self, self.unit_var, *self.unit_opts)
        
        self.step3_lbl = tk.Label(self, text='Step 3. Set the iteration limits.', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.iter_frame = IterFrame(self, self.controller, FRAME_BG_COLOR, entry_width=20)
        self.step4_lbl = tk.Label(self, text='Step 4. Select iteration units.', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.unit_menu = tk.OptionMenu(self, self.unit_var, *self.unit_opts)
        self.run_btn = tk.Button(self, text='Run Analysis', font=TEXT_FONT, command=lambda:self.run_sensitivity())
        
        self.obj_var.trace('w', self.object_menu_switch)
        self.par_var.trace('w', self.param_menu_switch)
        self.unit_var.trace('w', self.unit_menu_switch)
        
        self.pack_attributes()
        self.obj_var.set(self.obj_opts[0])

    #Places the text and entries
    def pack_attributes(self):
        self.title_lbl.pack(fill='x', expand=True, padx=5, pady=5)
        self.directions_lbl.pack(fill='x', expand=True, padx=5, pady=5)
        self.step1_lbl.pack(fill='x', expand=True, padx=5, pady=5)
        self.object_menu.pack(fill='x', expand=True, padx=5, pady=5)
        self.step2_lbl.pack(fill='x', expand=True, padx=5, pady=5)
        self.par_menu.pack(fill='x', expand=True, padx=5, pady=5)
        self.step3_lbl.pack(fill='x', expand=True, padx=5, pady=5)
        self.iter_frame.pack(fill='x', expand=True, padx=5, pady=5)
        self.step4_lbl.pack(fill='x', expand=True, padx=5, pady=5)
        self.unit_menu.pack(fill='x', expand=True, padx=5, pady=5)
        self.run_btn.pack(fill='x', expand=True, padx=5, pady=5)
    
    #When the menu switches, update the parameter list
    def object_menu_switch(self, name=None, idx=None, op=None):
        par_opts = self.get_param_list()
        if par_opts is False:
            par_opts = ['']
        self.par_opts = par_opts
        self.par_menu.destroy()
        self.par_menu = tk.OptionMenu(self, self.par_var, *self.par_opts)
        self.par_var.set(self.par_opts[0])
        self.par_menu.pack(fill='x', expand=True, padx=5, pady=5, before=self.step3_lbl)

    #When the parameter option changes, update the units
    def param_menu_switch(self, name=None, idx=None, op=None):        
        unit_opts = self.get_unit_list()
        if unit_opts is False:
            unit_opts = ['']
        self.unit_opts = unit_opts
        self.unit_menu.destroy()
        self.unit_menu = tk.OptionMenu(self, self.unit_var, *self.unit_opts)
        self.unit_var.set(self.unit_opts[0])
        self.unit_menu.pack(fill='x', expand=True, padx=5, pady=5, before=self.run_btn)

    #When the units switch, enter the default values
    def unit_menu_switch(self, name=None, idx=None, op=None):
        defaults = self.get_default_iterations()
        if defaults is not False:
            self.iter_frame.set_entries(defaults)
    
    #Returns the default values for a certain unit/parameter
    def get_default_iterations(self): #Returns [min, max, step] depending on the unit
        unit = self.unit_var.get()
        if unit == '':
            return False
        elif unit == 'cfs':
            return [100, 1000, 100]
        elif unit == 'ft':
            return [1, 10, 1]
        elif unit == '$':
            return [10000, 100000, 10000]
        elif unit == '($) Total Cost':
            return [10000, 100000, 10000]
        elif unit == '(%) Percent of ICC':
            return [1, 10, 1]
        elif unit == 'cfs (Constant)':
            return [100, 1000, 100]
        elif unit == '% (Percent of inflow)':
            return [1, 10, 1]
        elif unit == 'ft^(1/2)/s':
            return [2, 4, 0.5]
        elif unit == '$/MWh':
            return [0.04, 0.30, 0.02]
        elif unit == 'unitless':
            return [0, 1, 0.001]
        elif unit == '$/ft2':
            return [0, 100, 1]
        elif unit == '$/hr':
            return [0, 100, 5]
        elif unit == 'yr':
            return [20, 50, 5]
        elif unit == '%':
            return [0, 100, 10]
        elif unit == '$/cfs':
            return [0, 100, 10]
        elif unit == '$/start-stop':
            return [0, 100, 10]
        elif unit == 'Days':
            return [0, 5, 1]
        elif unit == 'Flushes/year':
            return [0, 24, 1]
        elif unit == '% of original':
            return [10, 100, 10]
        elif unit == 'dimensionless':
            return [0.1, 1, 0.1]
        else:
            print('unknown unit - '+ unit)
            return False
        
    #Gets the objects that can be selected for sensitivity
    def get_object_list(self):
        obj_list = []
        if self.controller.site is not None:
            obj_list.append('Site')
        if self.controller.costs is not None:
            obj_list.append('Cost Table')
        if self.controller.preferences is not None:
            obj_list.append('Preferences')
        for sp in self.controller.species_list:
            obj_list.append(sp.name)
        for mod_list in self.controller.mod_lib.all_mods_dict.values():
            for mod in mod_list:
                obj_list.append(mod.name)
        for screen in self.controller.mod_lib.screens_list:
            obj_list.append(screen.name)
        return obj_list
         
    #For a given object, determines the parameters that can be changed in sensitivity. Differs for static and dynamic modules
    def get_param_list(self):
        obj = self.obj_var.get()
        if obj == '':
            return False
        elif obj == 'Site':
            param_list = ['Stream Width', 'Trap Efficiency Parameter']
        elif obj == 'Cost Table': 
            param_list = ['Energy Price','Additional Capital Costs', 'Additional Non-Capital Costs','Excavation Rate','Overhead Cost','Engineering Cost','Contingency Allowance',\
                              'Value of Recreation','Annual O&M Cost','Flood Cost','Discount Rate','Project Life']
        elif obj == 'Preferences':
            param_list = ['Normal Operating Level','Spillway Minimum Flow']
        
        elif obj in [s.name for s in self.controller.species_list]:
            param_list = ['Minimum Relative Discharge (a)', 'Attraction Sensitivity (b)']
        
        else:
            mod = self.controller.mod_lib.get_mod_by_name(obj)
            if mod == False:
                mod = self.controller.mod_lib.get_screen_by_name(obj)
                if mod == False:
                    return False
            param_list = ['Capital Cost', 'Annual Operating Cost']
            #Assume to have a good mod (module or screen) at this point
            if mod.module_class in ['Gen', 'Sed', 'Fish', 'Wat', 'Rec', 'Spill']: #If passage module
                fish_dict = {'Mortality Rate': mod.mort_rates, 'Guidance Efficiency': mod.guide_effs,'Entrance Efficiency': mod.entr_effs,'Passage Efficiency': mod.pass_effs}
                for i in fish_dict:
                    if fish_dict is not None:
                        if fish_dict[i] is not None:
                            for specie in fish_dict[i]:
                                param_list.append(i + ' - ' + specie)
            elif mod.module_class == 'Screen':
                fish_dict = {'Mortality Rate': mod.mort_rates, 'Guidance Efficiency': mod.guide_effs}
                for i in fish_dict:
                    if fish_dict is not None:
                        if fish_dict[i] is not None:
                            for specie in fish_dict[i]:
                                param_list.append(i + ' - ' + specie)
            if mod.module_class == 'Gen':
                param_list.append('Cost of Start-Stops')
            elif mod.module_class == 'Sed':
                if mod.op_mode == 'Sluicing': 
                    param_list.extend(['Design Flow', 'Operating Flow'])
                elif mod.op_mode == 'Flushing':
                    param_list.extend(['Flushing Duration', 'Operating Frequency'])
            elif mod.module_class == 'Fish': 
                param_list.extend(['Design Flow','Maximum Headwater Drop','Maximum Headwater Rise','Minimum Tailwater Level', 'Maximum Tailwater Level'])
            elif mod.module_class == 'Wat':
                param_list.extend(['Design Flow'])
                if mod.op_mode == 'Controlled Spillway':
                    param_list.extend(['Weir Coefficient','Crest Height'])
            elif mod.module_class == 'Rec':
                param_list.extend(['Design Flow','Maximum Headwater Drop','Maximum Headwater Rise','Minimum Tailwater Level', 'Maximum Tailwater Level'])
        return param_list
                
    #Gets the list of units for a given parameter
    def get_unit_list(self):
        param_key = self.par_var.get()
        if param_key == '':
            return False
        elif param_key in ['Capital Cost', 'Annual Operating Cost']:
            return ['$', '% of original']
        elif param_key in['Overhead Cost','Engineering Cost','Contingency Allowance','Annual O&M Cost']:
            return ['($) Total Cost', '(%) Percent of ICC']
        elif param_key == 'Spillway Minimum Flow':
            return ['cfs (Constant)', '% (Percent of inflow)']
        elif param_key in ['Minimum Relative Discharge (a)', 'Attraction Sensitivity (b)']:
            return ['dimensionless']
        else:
            obj = self.obj_var.get()
            if obj == 'Site':
                for i in range(0, len(self.controller.site.labels)):
                    if param_key == self.controller.site.labels[i]:
                        return [self.controller.site.units[i]]
                print('Cannot find site label')
                return False
            elif obj == 'Cost Table':
                for i in range(0, len(self.controller.costs.labels)):
                    if param_key == self.controller.costs.labels[i]:
                        return [self.controller.costs.units[i]]
                print('Cannot find costs label')
                return False
            elif obj == 'Preferences':
                for i in range(0, len(self.controller.preferences.labels)):
                    if param_key == self.controller.preferences.labels[i]:
                        return [self.controller.preferences.units[i]]
                print('Cannot find preferences label')
                return False
            else:
                mod = self.controller.mod_lib.get_mod_by_name(obj)
                if mod == False:
                    mod = self.controller.mod_lib.get_screen_by_name(obj)
                    if mod == False:
                        return False
                for i in range(0, len(mod.labels)):
                    if param_key == mod.labels[i]:
                        return [mod.units[i]]
                    
                return '%' #Assume fish related percentage

    #Gathers the requisite inputs, error checks, then runs the sensitivity analysis through the controller page
    def run_sensitivity(self):
        obj = self.obj_var.get()
        param = self.par_var.get()
        unit = self.unit_var.get()
            
        if '' in [obj, param, unit]:
            tk.messagebox.showerror('Error', 'Please select a proper parameter to vary.')
            return
        
        iters = self.iter_frame.get_values()
        if iters is False:
            tk.messagebox.showerror('Error', 'Please input proper iteration limits.')
            return
        
        var_val = ''
        unit_val = ''
        #If not a module
        if param == 'Stream Width':
            var_val = 'stream_width'
        elif param == 'Trap Efficiency Parameter':
            var_val = 'trap_b'
        elif param == 'Energy Price':
            var_val = 'energy'
        elif param == 'Additional Capital Costs':
            var_val = 'add_capital'
        elif param == 'Additional Non-Capital Costs':
            var_val = 'add_noncapital'
        elif param == 'Excavation Rate':
            var_val = 'excavation'
        elif param == 'Overhead Cost':
            var_val = 'overhead'
            unit_val = 'overhead_type'
        elif param == 'Engineering Cost':
            var_val = 'engineering'
            unit_val = 'engineering_type'
        elif param == 'Contingency Allowance':
            var_val = 'contingency'
            unit_val = 'contingency_type'
        elif param == 'Value of Recreation':
            var_val = 'recreation'
        elif param == 'Annual O&M Cost':
            var_val = 'om'
            unit_val = 'om_type'
        elif param == 'Flood Cost':
            var_val = 'flood'
        elif param == 'Discount Rate':
            var_val = 'discount'
        elif param == 'Project Life':
            var_val = 'proj_life'
        elif param == 'Normal Operating Level':
            var_val = 'nol'
        elif param == 'Spillway Minimum Flow':
            var_val = 'spill_min_flow'
            unit_val = 'min_flow_type'
        elif param == 'Minimum Relative Discharge (a)':
            var_val = 'a'
        elif param == 'Attraction Sensitivity (b)':
            var_val = 'b'
        else:
            mod = self.controller.mod_lib.get_mod_by_name(obj)
            if mod == False:
                mod = self.controller.mod_lib.get_screen_by_name(obj)
                if mod == False:
                    return False
            
            if param == 'Capital Cost':
                if mod.is_dynamic():
                    if (type(mod.cap_cost_t) == mc.Equation) or (type(mod.cap_cost_t) == mc.PiecewiseEquation):
                        var_val = 'cap_cost_t'
                        unit_val = 'Equation'
                else:
                    var_val = 'cap_cost'
            elif param == 'Annual Operating Cost':
                if mod.is_dynamic():
                    if (type(mod.op_cost_t) == mc.Equation)  or (type(mod.op_cost_t) == mc.PiecewiseEquation):
                        var_val = 'op_cost_t'
                        unit_val = 'Equation'
                else:
                    var_val = 'op_cost'
            elif param == 'Cost of Start-Stops':
                var_val = 'cost_ss'
            elif param == 'Design Flow':
                var_val = 'des_flow'
            elif param == 'Operating Flow':
                var_val = 'op_flow'
            elif param == 'Flushing Duration':
                var_val = 'op_dur'
            elif param == 'Operating Frequency':
                var_val = 'op_freq'
            elif param == 'Maximum Headwater Drop':
                var_val = 'max_head_drop'
            elif param == 'Maximum Headwater Rise':
                var_val = 'max_head_rise'
            elif param == 'Minimum Tailwater Level':
                var_val = 'min_tail_ele'
            elif param == 'Maximum Tailwater Level':
                var_val = 'max_tail_ele'
            elif param == 'Weir Coefficient':
                var_val = 'weir_coeff'
            elif param == 'Crest Height':
                var_val = 'crest_height'
            else: #Assume a fish passage metric
                param_split = param.split(' - ')
                if len(param_split) <= 1:
                    tk.messagebox.showerror('Error', 'Unable to interpret the paramater')
                    return False
                fish_eff_type = param_split[0]
                unit_val = param_split[1] #set unit_val to species name
                if fish_eff_type == 'Mortality Rate':
                    var_val = 'mort_rates'
                elif fish_eff_type == 'Guidance Efficiency':
                    var_val = 'guide_effs'
                elif fish_eff_type == 'Entrance Efficiency':
                    var_val = 'entr_effs'
                elif fish_eff_type == 'Passage Efficiency':
                    var_val = 'pass_effs'
                
            
        #Select the object to be iterated
        if obj == 'Site': 
            obj_val = self.controller.site
        elif obj == 'Cost Table':
            obj_val = self.controller.costs
        elif obj == 'Preferences':
            obj_val = self.controller.preferences
        elif obj in [sp.name for sp in self.controller.species_list]:
            for i in self.controller.species_list:
                if i.name == obj:
                    obj_val = i
        else:
            obj_val = mod
            
        #Sets the iteration based on a percentage of the original attribute value with percentages being 0-100
        if unit == '% of original': 
            if unit_val == 'Equation':
                iters['Min'] = iters['Min']/100.
                iters['Max'] = iters['Max']/100.
                iters['Step'] = iters['Step']/100.
            else:
                orig_value = getattr(obj_val, var_val)
                iters['Min'] = (iters['Min']/100.) * orig_value
                iters['Max'] = (iters['Max']/100.) * orig_value
                iters['Step'] = (iters['Step']/100.) * orig_value
        elif unit == '%':
            iters['Min'] = iters['Min']/100.
            iters['Max'] = iters['Max']/100.
            iters['Step'] = iters['Step']/100.
            
        #Start iteration process - must do separate processes for different kinds of units
        orig_value = None
        orig_unit = None
        if var_val in ['mort_rates', 'guide_effs', 'entr_effs', 'pass_effs']:
            orig_value = getattr(obj_val, var_val)[unit_val]
            self.controller.sensitivity_analysis(obj_val, var_val, iters, unit_val, unit_type='Dict')
            getattr(obj_val, var_val)[unit_val] =  orig_value
        elif unit_val == 'Equation':
            orig_eq = getattr(obj_val, var_val)
            if unit == '% of original':
                self.controller.sensitivity_analysis(obj_val, var_val, iters, unit_type='Discount Equation')
            else:
                orig_unit = getattr(obj_val, unit_val)
                setattr(obj_val, unit_val, 'Constant')
                self.controller.sensitivity_analysis(obj_val, var_val, iters)
                setattr(obj_val, unit_val, orig_unit)
                setattr(obj_val, var_val, orig_eq)
        else:
            #Get original values
            orig_value = getattr(obj_val, var_val)
            if unit_val != '':
                orig_unit = getattr(obj_val, unit_val)
            else:
                orig_unit = ''
                
            #Run sensitivity analysis through the controller
            self.controller.sensitivity_analysis(obj_val, var_val, iters)
            
            #Reset to original values
            setattr(obj_val, var_val, orig_value)
            if orig_unit != '':
                setattr(obj_val, unit_val, orig_unit)
            
#%%## OPTIMIZE PAGE - Retrieves GA parameters and runs the optimization procedure
class OptimizePage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.controller = controller
        self.page_name = 'Optimize'
        self.columnconfigure((0,1,2,3), weight=1)
        self.entry_width = 8
        self.direction_txt = 'Directions: This page uses a genetic algorithm (GA) to optimize your facility design given your site, preferences, and cost tables. The GA procedure can be customized by setting the parameters, objective function, and constraints. Note the number of solutions kept, mutated, and randomized must equal the population size. The number of best solutions kept must be greater than zero.'
        self.show_anim_var = tk.IntVar()
        
        self.page_title = tk.Label(self, text = self.page_name, font = PG_TITLE_FONT, bg=TITLE_BG_COLOR) 
        self.directions_lbl = tk.Label(self, text = self.direction_txt, font = TEXT_FONT, bg=DIRECTIONS_BG_COLOR, anchor='w', justify='left', wraplength=self.controller.wrap_length)     
        self.genetic_frame = GeneticParametersFrame(self, self.controller)
        self.objectives_frame = ObjectiveSelectFrame(self, self.controller)
        self.constraints_frame = ConstraintFrame(self, self.controller)
        self.modselect_lbl = tk.Label(self, text ='Select Module Parameter Constraints', font = SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR) 
        self.modselect_frame = tk.Label(self,text='No modules have been created.', font=TEXT_FONT, bg=FRAME_BG_COLOR) #Changes from label to ModuleSelectFrame when at least one module is added
        self.run_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.show_anim_chk = tk.Checkbutton(self.run_frame, text='Show Iterations', variable=self.show_anim_var,  onvalue=1, width=12, anchor='c', padx=3, bg=CHECK_BG_COLOR)
        self.submit_btn = tk.Button(self.run_frame, text='Run Genetic Algorithm',font=TEXT_FONT, command=lambda:self.run_optimization())
        self.sim_results_lbl = tk.Label(self, text ='Simulation Results', font = SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR) 
        self.sim_results = tk.Label(self, text='Please create a facility by pressing the Run button to see results.', font = TEXT_FONT,bg=LABEL_BG_COLOR, wraplength=self.controller.wrap_length)
        self.best_fac_lbl = tk.Label(self, text='Optimal Facility Configuration', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.best_fac_frame = tk.Label(self, text='Please run the optimization algorithm to see results.', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        
        self.pack_attributes()
        

    def pack_attributes(self):
        self.page_title.grid(row=0, column=0, columnspan=2, padx=0, pady=0, sticky='nsew')
        self.directions_lbl.grid(row=1, column=0, columnspan=2, padx=0, pady=5, sticky='nsew')
        self.run_frame.grid(row=2, column=0, columnspan=2, sticky='nsew')
        self.genetic_frame.grid(row=3, column=1, columnspan=1, sticky='nsew', padx=5)
        self.objectives_frame.grid(row=3, column=0, columnspan=1, sticky='nsew', padx=5)
        self.constraints_frame.grid(row=4, column=0, columnspan=2, sticky='nsew')
        self.modselect_lbl.grid(row=5, column=0, columnspan=2, sticky='nsew')
        self.modselect_frame.grid(row=6, column=0, columnspan=2, sticky='nsew')
        self.best_fac_lbl.grid(row=7, column=0, columnspan=2, sticky='nsew')
        self.best_fac_frame.grid(row=8, column=0, columnspan=2, sticky='nsew')
        self.sim_results_lbl.grid(row=9, column=0, columnspan=2, sticky='nsew')
        self.sim_results.grid(row=10, column=0, columnspan=2, sticky='nsew')
        
        #In run_frame
        self.run_frame.columnconfigure((0,1,2), weight=1)
        self.show_anim_chk.grid(row=0, column=0, padx=5, pady=5, sticky='nse')
        self.submit_btn.grid(row=0, column=1, padx=5, pady=5, sticky='nsw')
        
    #Update the ModuleSelectFrame when a module is added
    def update_mod_select_frame(self):
        self.modselect_frame.destroy()
        self.modselect_frame = ModuleSelectFrame(self, self.controller, 'Optimize')
        self.pack_attributes()

    #Gather the inputs, error check, and run the optimization function through the controller 
    def run_optimization(self, msg_off=False):
        vals = self.genetic_frame.get_parameters() # vals = [iterations, pop_size, best_num, mut_num, random_num, cross_num]
        if vals is False:
            tk.messagebox.showerror('Error', 'Make sure genetic algorithm parameters are input properly. The best, mutation, and random inputs must sum to the population size. The best parameter must be greater than 0.')
            return
        objectives = self.objectives_frame.get_obj()
        constraints = self.constraints_frame.get_constraints()
        
        enum_lists = self.modselect_frame.get_enumerate_lists() #enum_lists = [req_mods_dict,pass_mods_list,const_list, iter_list, screen_bool_dict]
        if enum_lists is False:
            return False
        
        error=False
        for v in vals:
            if (str(v) == '') or (str(v) == 'Error'):
                tk.messagebox.showerror("Error", 'Could not run optimization, double check inputs')
                error=True
        if error==False:
            if self.show_anim_var.get() == 1:
                show_anim = True
            else:
                show_anim = False
            self.controller.optimize_facility(enum_lists, objectives, constraints, *vals, show_anim)
     
    #Update the results frame when the optimization is complete
    def optimization_complete(self):
        self.best_fac = self.controller.opt_facs[0]
        self.latest_res = self.best_fac.get_latest_sim_results()
        self.update_results()

    #Update the results frames with the best facility from the optimization process
    def update_results(self):
        if self.latest_res is not False:
            self.sim_results.destroy()
            self.best_fac_frame.destroy()
            self.sim_results = SimResultsFrame(self, self.controller, self.latest_res)
            self.best_fac_frame = FacilityFrame(self, self.controller, self.best_fac)
            self.modselect_frame.update_modselect_frame(self.best_fac)
            self.pack_attributes()
        else:
            tk.messagebox.showerror('Error', 'Unable to gather results due to an error during simulation. Likely causes are due to tight head constraints or improper module inputs.')
    
#Frame the includes the parameters required to run the genetic algorithm
class GeneticParametersFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.controller = controller
        self.page_name = 'Genetic Algorithm Parameters'
        self.entry_width = 8
        self.columnconfigure((0,1), weight=1)
        self.ga_title_lbl = tk.Label(self, text ='Genetic Algorithm Parameters', font = SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR) 
        self.iteration_lbl = tk.Label(self, text = 'Number of Iterations:', font =TEXT_FONT, bg=LABEL_BG_COLOR)
        self.iteration_entry = ttk.Entry(self, width=self.entry_width)
        self.population_lbl = tk.Label(self, text = 'Population Size:', font =TEXT_FONT, bg=LABEL_BG_COLOR)
        self.population_entry = ttk.Entry(self, width=self.entry_width)
        self.best_lbl = tk.Label(self, text = 'Number of Best Solutions Kept:', font =TEXT_FONT, bg=LABEL_BG_COLOR)
        self.best_entry = ttk.Entry(self, width=self.entry_width)
        self.mutate_lbl = tk.Label(self, text = 'Number Mutated:', font =TEXT_FONT, bg=LABEL_BG_COLOR)
        self.mutate_entry = ttk.Entry(self, width=self.entry_width)
        self.random_lbl = tk.Label(self, text = 'Number Randomized:', font =TEXT_FONT, bg=LABEL_BG_COLOR)
        self.random_entry = ttk.Entry(self, width=self.entry_width)
        self.cross_lbl = tk.Label(self, text = 'Number of Cross-overs:', font =TEXT_FONT, bg=LABEL_BG_COLOR)
        self.cross_entry = ttk.Entry(self, width=self.entry_width)

        self.entry_list = [self.iteration_entry, self.population_entry,self.best_entry, self.mutate_entry, self.random_entry, self.cross_entry]
        self.pack_attributes()
        self.default_entries()
        
    #Gathers entries, error checks, and returns values
    def get_parameters(self):
        iterations = check_entry(self.iteration_entry.get(), [int])
        pop_size = check_entry(self.population_entry.get(), [int])
        best_num = check_entry(self.best_entry.get(), [int])
        mut_num = check_entry(self.mutate_entry.get(), [int])
        random_num = check_entry(self.random_entry.get(), [int])
        cross_num = check_entry(self.cross_entry.get(), [int])
        
        if 'Error' in [iterations, pop_size, best_num, mut_num, random_num, cross_num]:
            return False
        if pop_size != sum([best_num, mut_num, random_num, cross_num]):
            return False
        if best_num <=0:
            return False
    
        return iterations, pop_size, best_num, mut_num, random_num, cross_num
        
    #Insert default values
    def default_entries(self):
        self.iteration_entry.insert(0, '20')
        self.population_entry.insert(0, '12')
        self.best_entry.insert(0, '3')
        self.mutate_entry.insert(0, '3')
        self.random_entry.insert(0, '3')
        self.cross_entry.insert(0, '3')
        
    #Place labels and entries
    def pack_attributes(self):
        self.ga_title_lbl.grid(row=0, column=0, columnspan=2, sticky='nsew')
        self.iteration_lbl.grid(row=1, column=0, columnspan=1, sticky='nse', pady=5)
        self.iteration_entry.grid(row=1, column=1, columnspan=1, sticky='nsw', pady=5)
        self.population_lbl.grid(row=2, column=0, columnspan=1, sticky='nse', pady=5)
        self.population_entry.grid(row=2, column=1, columnspan=1, sticky='nsw', pady=5)
        self.best_lbl.grid(row=3, column=0, columnspan=1, sticky='nse', pady=5)
        self.best_entry.grid(row=3, column=1, columnspan=1, sticky='nsw', pady=5)
        self.mutate_lbl.grid(row=4, column=0, columnspan=1, sticky='nse', pady=5)
        self.mutate_entry.grid(row=4, column=1, columnspan=1, sticky='nsw', pady=5)
        self.random_lbl.grid(row=5, column=0, columnspan=1, sticky='nse', pady=5)
        self.random_entry.grid(row=5, column=1, columnspan=1, sticky='nsw', pady=5)
        self.cross_lbl.grid(row=6, column=0, columnspan=1, sticky='nse', pady=5)
        self.cross_entry.grid(row=6, column=1, columnspan=1, sticky='nsw', pady=5)

#Frame that lets the user select an objective function metric
class ObjectiveSelectFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.controller = controller
        self.page_name = 'Objective Select Frame'
        self.columnconfigure((0), weight=1)
        self.check_width = 27
        self.obj_list = ['LCOE ($/MWh)', 'NPV ($)', 'ICC ($)','Unit cost ($/kW)']
        self.obj_var = tk.IntVar()
        self.obj_directions_lbl = tk.Label(self, text = 'Select the objective metric', font =SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.obj_chk_btns = {}
        self.obj_labels = {}
        self.obj_tools = {}
        
        #For the list of objectives, create checkbutton and support tool button
        self.obj_directions_lbl.grid(row=0, column=0, padx=5, sticky='nsew')
        for i in range(0, len(self.obj_list)):
            self.obj_chk_btns[self.obj_list[i]] = tk.Checkbutton(self, var=self.obj_var, text=self.obj_list[i], onvalue=i+1, offvalue=-1, width=self.check_width, anchor='w', padx=5, bg=FRAME_BG_COLOR)
            self.obj_tools[self.obj_list[i]] = tk.Button(self, text='!', command=lambda key=self.obj_list[i]:tool_click(self, key))
            self.obj_chk_btns[self.obj_list[i]].grid(row=i+1, column=0, sticky='nsw', padx=5, pady=2)
            self.obj_tools[self.obj_list[i]].grid(row=i+1, column=0, sticky='nse', padx=5, pady=2)
        self.obj_var.set(1) #Default Entry

    #Returns the selected objective
    def get_obj(self):
        try:
            return self.obj_list[self.obj_var.get() - 1]
        except:
            tk.messagebox.showerror('Error', 'Unable to get objective function value. Make sure one objectitve function metric is selected.')

#Frame the lets the user create, view, and delete constraints for the optimization procedure
class ConstraintFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.controller = controller
        self.page_name = 'Constraint Frame'
        self.entry_width = 8
        self.columnconfigure((0,1,2,3), weight=1)
        
        #There are two types of constraints: performance requirements (objective metric minimums or maximums), or facility design parameters (characteristics of the facility)
        self.constraint_types = ['Performance Requirements', 'Facility Design Parameters']
        self.constraint_objs = ['LCOE ($/MWh)', 'NPV ($)', 'ICC ($)','Unit Cost ($/kW)',  'Annual Energy (MWh)', 'Effective Mortality (%)', 'Effective Passage (%)', 'Sediment Flow Ratio (%)', 'Sediment Passage Frequency (%)', 'Avg Trap Efficiency (%)', 'Recreation Availability (%)', 'Annual Recreation (Hours)', 'Flood Return Period (yr)', 'Avg Impoundment Volume (ft3)', 'Annual Benefit ($)', 'Annual Expenses ($)']
        self.design_params = ['Capacity (kW)', 'Footprint (ft2)', 'Spillway Width (ft)', 'Spillway Design Flood (cfs)']
        self.oper_opts = ['>', '<', '=', '<=', '>=']
        self.oper_var = tk.StringVar()
        self.sub_var = tk.StringVar()
        self.const_list = []        
        self.con_type_var = tk.StringVar()
        self.con_type_var.trace('w', self.on_type_switch)
        
        self.con_title_lbl = tk.Label(self, text='Input Module Selection Optimization Constraints', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.con_type_lbl = tk.Label(self, text='Select a Constraint Type:', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.con_type_menu = tk.OptionMenu(self, self.con_type_var, *self.constraint_types)
        self.con_input_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.con_input_frame.columnconfigure((0,1,2), weight=1) 
        self.view_constraints_btn = tk.Button(self, text='View Constraints', font=TEXT_FONT, command=lambda:self.view_constraints())
        self.clear_btn = tk.Button(self, text='Clear', font=TEXT_FONT, command=lambda:self.clear_constraints())
        self.add_btn = tk.Button(self, text='Add', font=TEXT_FONT, width=15, command=lambda:self.add_constraint())
        self.count_var = tk.StringVar()
        self.count_lbl = tk.Label(self, textvariable=self.count_var, font=TEXT_FONT, bg=FRAME_BG_COLOR)

        self.con_title_lbl.grid(row=0, column=0, columnspan=4,sticky='nsew', padx=0, pady=5)
        self.con_type_lbl.grid(row=1, column=0, columnspan=2,sticky='nsew', padx=5, pady=5)
        self.con_type_menu.grid(row=1, column=2, columnspan=2, sticky='nsew', padx=5, pady=5)
        self.con_input_frame.grid(row=2, column=0, columnspan=4,sticky='nsew', padx=5, pady=5)
        self.count_lbl.grid(row=3, column=0, sticky='nsw', padx=0, pady=0)
        self.add_btn.grid(row=3, column=1, sticky='nse', padx=5, pady=5)
        self.clear_btn.grid(row=3, column=2, sticky='nsew', padx=5, pady=5)
        self.view_constraints_btn.grid(row=3, column=3, sticky='nsew', padx=5, pady=5)
        
        self.con_type_var.set(self.constraint_types[0])#Triggers on_type_switch
        
        self.update()
        
    #When the type of constraint changes, update the menus
    def on_type_switch(self, name, idx, op):
        for widget in self.con_input_frame.winfo_children():
            widget.destroy()
        self.pack_con_input_frame()

    #Delete all contraints
    def clear_constraints(self):
        self.const_list = []
        tk.messagebox.showinfo('Success', 'All constraints have been cleared.')
        self.update()

    #Pack the input widgets
    def pack_con_input_frame(self):
        if self.con_type_var.get() == 'Performance Requirements':
            self.sub_opts = self.constraint_objs
        elif self.con_type_var.get() == 'Facility Design Parameters':
            self.sub_opts = self.design_params
            
        self.con_subject_menu = tk.OptionMenu(self.con_input_frame, self.sub_var, *self.sub_opts)
        self.sub_var.set(self.sub_opts[0])
        self.const_oper_menu = tk.OptionMenu(self.con_input_frame, self.oper_var, *self.oper_opts)
        self.const_entry = ttk.Entry(self.con_input_frame, width=self.entry_width)
        
        self.oper_var.set(self.oper_opts[0])
        
        self.con_subject_menu.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
        self.const_oper_menu.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
        self.const_entry.grid(row=0, column=2, padx=5, pady=5, sticky='nsew')
        
    #Update the constraint count
    def update(self):
        self.count_var.set('Count: {}'.format(len(self.const_list)))

    #Gather inputs, error check, and add constraint to the list
    def add_constraint(self):
        val = check_entry(self.const_entry.get(), [float])
        if (str(val) == '') | (str(val) == 'Error'):
            tk.messagebox.showerror("Error", 'Could not submit constraint, double check that entry is a number')
        else:
            self.const_list.append([self.con_type_var.get(), self.sub_var.get(), self.oper_var.get(), val])
            self.update()
            tk.messagebox.showinfo('Success', 'Successfully added constraint')

    #Create a tableviewer to see the list of constraints
    def view_constraints(self):
        if len(self.const_list) > 0:
            constraint_df = pd.DataFrame(data=self.const_list, columns=['Constraint Type', 'Variable', 'Conditional', 'Value'])
            Tableviewer(self, self.controller, constraint_df, show_header=True, show_index=False)
        else:
            tk.messagebox.showinfo('', 'No constraints have been added yet.')
    
    #Returns the constraints list
    def get_constraints(self):
        return self.const_list

#%%## Module select frame - Frame that controls the module selection function in the enumeration and optimize pages
class ModuleSelectFrame(tk.Frame):
    def __init__(self, parent, controller, page_type):
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.controller = controller
        self.ml = self.controller.mod_lib
        self.mod_frame_list = []
        self.page_type = page_type
        self.non_var = tk.IntVar()
        self.fou_var = tk.IntVar()
        self.flush_var = tk.IntVar()

        counter = 0        
        for cl in self.ml.cl:
            for m in self.ml.all_mods_dict[cl]:
                self.mod_frame_list.append(ModParamSelectFrame(self, self.controller, m, counter, self.page_type))
                counter +=1
        for sc in self.ml.screens_list:#Adds screens to mod select
            self.mod_frame_list.append(ModParamSelectFrame(self, self.controller, sc, counter, self.page_type))
            counter+=1
                    
        for f in self.mod_frame_list:
            f.pack(side='top', fill='x', pady=3)

        self.non_var.set(-1)
        self.fou_var.set(-1)
        self.flush_var.set(-1)
        self.default_entries()

    #Updates the view buttons, so that the Tables will change
    def update_modselect_frame(self, fac): 
        for mod_frame in self.mod_frame_list:
            new_mod = fac.get_mod_by_name(mod_frame.mod.name)
            if new_mod is not False:
                mod_frame.mod = new_mod
                
    #Gather the information needed to run the enumeration: [required mods dict, passage mods list, constant attribute list, iteration attribute list, screen boolean dict]
    def get_enumerate_lists(self):
        if self.non_var.get() == -1:
            tk.messagebox.showerror('Error', 'Must select a non-overflow module.')
            return False
        if self.fou_var.get() == -1:
            tk.messagebox.showerror('Error', 'Must select a foundation module.')
            return False
    
        if self.flush_var.get() == -1:
            flush_mod = None
        else:
            flush_mod = self.mod_frame_list[self.flush_var.get()].mod

        req_mods_dict = {'Non-overflow': self.mod_frame_list[self.non_var.get()].mod, \
                    'Foundation': self.mod_frame_list[self.fou_var.get()].mod, \
                        'Flushing': flush_mod}
        
        spill_mod_list = [] #Used to keep track of spillway modules, can only have one
        spill_mod_counts = [] #Used to keep track of spillway module counts, must have at least one
        pass_mods_list = [] #Stores the passage mods
        iter_list = [] #List that storage [mod name, att, [iters]]
        const_list = [] #List that stores [mod name, attribute, number]
        screen_bool_dict = {}
        for f in self.mod_frame_list:
            if f.att_type == 'on/off checkbutton':
                screen_bool_dict[f.mod.name] = f.get_values()
            elif f.att_type == 'frame':
                mod_params = f.get_values() #if successful (mod obj, param_dict), unsuccessful False
                if mod_params is False:
                    tk.messagebox.showerror('Error', 'Unable to interpret the parameters for the {} module.'.format(f.mod.name))
                    return False
                
                mod = mod_params[0]
                param_dict = mod_params[1] #'Attribute': ('Constant', num) or ('Iterations', {'Min':num, 'Max', num, 'Step', num}) or ('Range', {'Min':num, 'Max': num})
                #Check if there is at least one module listed
                atleast_one = False
                if param_dict['Module Count'][0] == 'Constant':
                    if param_dict['Module Count'][1] > 0:
                        atleast_one = True
                else:
                    if param_dict['Module Count'][1]['Max'] > 0:
                        atleast_one = True
                
                if atleast_one == True: #If at least one module, then add it to the lists
                    if mod.module_class == 'Spill':
                        spill_mod_list.append(mod)
                    else:
                        pass_mods_list.append(mod)
                       
                    for key in param_dict:
                        if param_dict[key][0] == 'Constant':
                            const_list.append([mod.name, key, param_dict[key][1]])
                            if mod.module_class == 'Spill':
                                spill_mod_counts.append(param_dict[key][1])
                        else: #If iterations or range
                            if param_dict[key][1]['Min'] >= param_dict[key][1]['Max']:
                                tk.messagebox.showerror('Error', 'Maximum bounds must be larger than the minimum bounds.')
                                return False
                        
                            pmax = param_dict[key][1]['Max']
                            pmin = param_dict[key][1]['Min']
                            if key == 'Module Count':
                                pmax = int(pmax)
                                pmin = int(pmin)
                                if param_dict[key][0] == 'Iterations':
                                    step = int(param_dict[key][1]['Step'])                                  
                                if mod.module_class == 'Spill':
                                    spill_mod_counts.append(param_dict[key][1]['Min'])
                            elif param_dict[key][0] == 'Iterations':
                                step = param_dict[key][1]['Step']
                                
                            if param_dict[key][0] == 'Range':
                                att_iters = [pmin, pmax]
                            else:
                                if step <= 0:
                                    tk.messagebox.showerror('Error', 'Please enter a non-negative step.')
                                    return False
                                try:
                                    att_iters = list(np.arange(pmin, pmax, step))
                                    if len(att_iters) == 0:
                                        tk.messagebox.showerror('Error', 'Unable to determine iterations of the {} module.'.format(mod.name))
                                        return False
                                    if att_iters[-1] != pmax: #Include max bound if not included
                                        att_iters.append(pmax)
                                except:
                                    tk.messagebox.showerror('Error', 'Unable to determine iterations of the {} module.'.format(mod.name))
                                    return False
                            iter_list.append([mod.name,key,att_iters])
        if len(spill_mod_list) <= 0:
            tk.messagebox.showerror('Error', 'Must have at least one spillway module.')
            return False
        elif len(spill_mod_list) > 1:
            tk.messagebox.showerror('Error', 'Cannot use more than one type of spillway module.')
            return False
        
        if spill_mod_counts[0] <= 0:
            tk.messagebox.showerror('Error', 'Iterations must have a minimum of one spillway module.')
            return False
        
        req_mods_dict['Spill'] = spill_mod_list[0]
    
        return [req_mods_dict,pass_mods_list,const_list, iter_list, screen_bool_dict]
        
    #Set default module counts based on class
    def default_entries(self): 
        spill_selected = False
        for i in range(0, len(self.mod_frame_list)):
            if self.mod_frame_list[i].mod.module_class == 'Gen':
                self.mod_frame_list[i].set_value('1')
            elif self.mod_frame_list[i].mod.module_class == 'Spill':
                if spill_selected == False:
                    self.mod_frame_list[i].set_value('1')
                    spill_selected = True
                else:
                    self.mod_frame_list[i].set_value('0')
            elif self.mod_frame_list[i].mod.module_class in ['Non', 'Fou']:
                self.mod_frame_list[i].set_value(True)
            else:
                self.mod_frame_list[i].set_value('1')
            
#%%## Support Tools - contains the frames and information for the tool tip buttons
class SupportToolWindow(tk.Toplevel):
    def __init__(self, parent, controller, att, tool=None, mod_type=None):
        tk.Toplevel.__init__(self)
        self.controller = controller 
        self.parent = parent
        self.att = att
        self.tool = tool
        self.mod_type = mod_type
        self.wrap_length = 700
        self.frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.frame.pack(fill='both', expand=True)
        self.obj_list = []
        self.out_var = None
        
        self.add_att_desc(self.att)
        if self.tool is not None:
            if len(self.tool) > 0:
                self.add_tools(self.tool[0])
        self.pack_frame()
        
    #place all widgets in the object list
    def pack_frame(self):
        for i in range(0, len(self.obj_list)):
            self.obj_list[i].pack(fill='x', expand=True)
            
    #Function for quickly creating a label for a given text string
    def create_label(self, text):
        self.obj_list.append(tk.Label(self.frame, font=TEXT_FONT, justify='left', bg=FRAME_BG_COLOR, text=text, wraplength=self.wrap_length))
        
    #If the support tool creates an equation, then this button allows it to be imported to the parent frame
    def add_equation_btn(self, orig_eq):
        frame = tk.Frame(self,bg=FRAME_BG_COLOR)
        self.modify_btn = tk.Button(frame, text='Modify Equation', font=TEXT_FONT, command=lambda:self.modify_btn_press(orig_eq))
        self.import_btn = tk.Button(frame, text='Import', font=TEXT_FONT, command=lambda:self.import_btn_press())
        frame.columnconfigure((0,1),weight=1)
        self.modify_btn.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
        self.import_btn.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
        self.obj_list.append(frame)
        
    #Opens the equation creator to modifiy the equation
    def modify_btn_press(self, orig_eq):
        EquationCreator(self, self.controller, 'Default Head Efficiency Curve', 'Relative head (% fo design head)', 'Turbine Efficiency (%)', orig_equation=orig_eq)
        
    #Sets the saved equation
    def update_equation(self, eq): 
        self.out_var = eq
        
    #If the user wants to import the tool value into the parent entry
    def import_btn_press(self):
        try:
            if self.out_var is not None:
                self.parent.import_from_tool(self.tool[0], self.out_var)
                tk.messagebox.showinfo('Success', 'Imported value as a module attribute.')
                self.destroy()
            else:
                tk.messagebox.showerror('Error', 'No value to import. Double check inputs.')
        except:
            tk.messagebox.showerror('Error', 'Unable to import value. Double check inputs.')
    
    #When the stage storage model creates an equation it is updated in the support tool window
    def update_stage_storage_model(self, eq):
        self.out_var = eq
        self.eq_add_frame.update_equation(eq)
        self.eq_add_frame.grid(row=0, column=0, columnspan=2,padx=5, pady=5, sticky='nsew')
        tk.messagebox.showinfo('Success', 'Successfully created the geoemetric stage-storage equation. Please press the import button to add it to the module.')
    
    #When the sediment model is imported it is updated in the support tool window
    def update_sediment_model(self, rec_flow):
        self.out_var = rec_flow
        self.rec_flow_lbl.config(text = 'Recommended Flow: {}cfs'.format(str(rec_flow)))
        tk.messagebox.showinfo('Success', 'The recommended sediment flow of {}cfs has been successfully calculated.'.format(str(rec_flow)))
        self.sed_topl.destroy()
        
    #Open the corresponding support tool model
    def open_trap_efficiency_model(self):
        self.trap_topl = TrapEfficiencyModel(self, self.controller)
    def open_stage_storage_model(self):
        self.stage_topl = GeoReservoirModel(self, self.controller)
    def open_entrain_model(self):
        self.sed_topl = SedEntrainModel(self, self.controller)
    def open_attraction_efficiency_model(self):
        self.sed_topl = AttractionEfficiencyModel(self, self.controller)
    def open_data_download(self):
        autodataFrame(self, self.controller, 'Stage')
    
    #If data is collected using the autodataFrame, autoregress the data and update the equation
    def data_uploaded(self, df):
        x = 'Discharge (cfs)'
        y = 'Stage (ft)'
        out_eq = af.auto_regression('Stage-Discharge Curve', df, x, y, remove_negative=True)
        if type(out_eq) == str:
            tk.messagebox.showerror('Error', 'Unable to upload to regress data. {}'.format(out_eq))
        else:
            tk.messagebox.showinfo('Success', 'Regression sucessful.\nEquation: {}\nR2: {}\nUpper bound: {}\nLower Bound: {}'.format(\
                                    out_eq.get_text(), round(out_eq.regr_results['R2'],2), out_eq.ub, out_eq.lb))
            self.out_var = out_eq
    
    #If the input is an equation with stored data, you can view the data in a tableviewer
    def view_table(self):
        if type(self.out_var) == mc.Equation:
            if self.out_var.df is not None:
                Tableviewer(self, self.controller, self.out_var.df)
            else:
                tk.messagebox.showerror('Error', 'No data to view. Please try downloading again')
        else:
            tk.messagebox.showerror('Error', 'No data to view. Please try downloading again')
                
    #Creates the basic layout for each of the support tools with an entry, definition, unit and notes
    def att_frame(self, att_name, entry_type, defin, unit=None, add_desc=None):
        out_frame = tk.Frame(self.frame, bg=FRAME_BG_COLOR)
        name_label = tk.Label(out_frame, text=att_name,font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR, justify='center')
        entry_type_left = tk.Label(out_frame, text='Entry Type:', font=TEXT_BOLD_FONT, bg=FRAME_BG_COLOR)
        entry_type_right = tk.Label(out_frame, text=entry_type, font=TEXT_FONT, bg=FRAME_BG_COLOR)
        desc_left = tk.Label(out_frame, text='Definition:', font=TEXT_BOLD_FONT, bg=FRAME_BG_COLOR)
        desc_right = tk.Label(out_frame, text=defin, font=TEXT_FONT, bg=FRAME_BG_COLOR, wraplength=self.wrap_length-50, justify='left')
        
        name_label.grid(row=0, column=0, columnspan=2, sticky='nsew', padx=0, pady=0)
        entry_type_left.grid(row=1, column=0, columnspan=1, sticky='nw', padx=5, pady=5)
        entry_type_right.grid(row=1, column=1, columnspan=1, sticky='nw', padx=5, pady=5)
        row=2
        if unit is not None:
            unit_left = tk.Label(out_frame, text='Unit:', font=TEXT_BOLD_FONT, bg=FRAME_BG_COLOR)
            unit_right = tk.Label(out_frame, text=unit, font=TEXT_FONT, bg=FRAME_BG_COLOR)
            unit_left.grid(row=row, column=0, columnspan=1, sticky='nw', padx=5, pady=5)
            unit_right.grid(row=row, column=1, columnspan=1, sticky='nw', padx=5, pady=5)
            row+=1
        desc_left.grid(row=row, column=0, columnspan=1, sticky='nw', padx=5, pady=5)
        desc_right.grid(row=row, column=1, columnspan=1, sticky='nw', padx=5, pady=5)
        row+=1
        if add_desc is not None:
            add_desc_left = tk.Label(out_frame, text='Notes:', font=TEXT_BOLD_FONT, bg=FRAME_BG_COLOR)
            add_desc_right = tk.Label(out_frame, text=add_desc, font=TEXT_FONT, bg=FRAME_BG_COLOR, wraplength=self.wrap_length-50, justify='left')
            add_desc_left.grid(row=row, column=0, columnspan=1, sticky='nw', padx=5, pady=5)
            add_desc_right.grid(row=row, column=1, columnspan=1, sticky='nw', padx=5, pady=5)
        
        self.obj_list.append(out_frame)
        
    #Gets the text description for each attribute in the model
    def add_att_desc(self, att):
        if att == 'Name':
            self.att_frame(att, 'Text', 'The name used to identify the module in figures.')
        elif att == 'Capital Cost':
            self.att_frame(att, 'Numeric', 'The capital cost for a module should include all fixed, one-time costs to prepare a module for operation.', '$','These can include material, equipment, installation, transportation, etc.')
        elif att == 'Annual Operating Cost':
            self.att_frame(att, 'Numeric', 'The annual operating costs for a module should include all annualized expected costs for maintaining and operating the module.', '$', 'Annual operating costs can also be set for the plant as a whole in the Cost Table tab.')        
        elif att == 'Width':
            self.att_frame(att, 'Numeric', 'The module dimension along the dam axis from bank to bank, perpendicular to streamflow.', 'ft')
        elif att == 'Length':
            self.att_frame(att, 'Numeric', 'The module dimension parallel to the flow of water.', 'ft')
        elif att == 'Design Flow':
            if self.mod_type == 'Generation':
                defin = 'The design flow is the peak efficiency flow and is used in the flow efficiency equation.'
                add_desc = None
            elif self.mod_type == 'Water Passage':
                defin = 'The maximum passage flood flow.'
                add_desc = 'The spillway module will be allocated flow up to the design flow. Any flow in excess will be counted as over-flow and incur a flooding penalty.'
            else:
                defin = 'The flow required by the module during normal operation.'
                add_desc = 'The module will not be operated if there is not sufficient flow to meet the design flow.'
            self.att_frame(att, 'Numeric', defin, 'cfs', add_desc)
        elif att == 'Operating Months':
            self.att_frame(att, 'Checkbox', 'The months during which the module is on and is allocated flow. ', 'Months', 'During the operating months, modules are modeled to operate 24/7.')
        elif att == 'Instream or Diversion':
            self.att_frame(att, 'Checkbox', 'Instream modules will be placed along the dam axis and will count towards the dam width. Diversion modules are placed on the banks in the facility schematic and can be used to represent bypasses.', 'Yes or No', 'This is used to calculate the number of required non-overflow modules.')
        elif att == 'Minimum Operating Flow':
            self.att_frame(att, 'Numeric', 'The minimum flow required to operate the module.', 'cfs')
        elif att == 'Maximum Operating Flow':
            self.att_frame(att, 'Numeric', 'The maximum flow that can be allocated to the module. ', 'cfs', 'If the turbine-overrun option  in the preferences tab is turned on, then excess flow will be allocated to increasing allocated flow above the design flow prior to spill allocation. If the turbine-overrun option is off, then design flow acts as the maximum allocated flow.')
        elif att == 'Design Head':
            self.att_frame(att, 'Numeric', 'The gross head at which the module operates at peak efficiency.', 'ft', ' This is used with the head efficiency equation to calculate head turbine efficiency.')
        elif att == 'Maximum Operating Head':
            self.att_frame(att, 'Numeric', 'The maximum gross head allowable during module operation.', 'ft')
        elif att == 'Flow Efficiency Curve':
            self.att_frame(att, 'Equation', 'The power output efficiency coefficient as a function of the relative discharge, which is the flow allocated to the module divided by the design flow (i.e. design flow = 100%).', unit='(0.0-1.0)% vs. cfs', add_desc='The X (relative discharge) should be given as decimals 1.0 referring to 100% efficient. The upper and lower bounds of X should at least span the operating range specified by the minimum and maximum operating limits. The Y value (power efficiency) should be calculated as a decimal where 1.0 is 100% efficiency.')
        elif att == 'Head Efficiency Curve':
            self.att_frame(att, 'Equation', 'The power output efficiency coefficient as a function of the relative head, which is the gross head across the module divided by the design head (i.e. design head = 100%).', unit='(0.0-1.0)% vs. ft', add_desc='The X (relative head) should be given as decimals 1.0 referring to 100% efficient. The upper and lower bounds of X should at least span the operating range specified by the minimum and maximum operating limits. The Y value (power efficiency) should be calculated as a decimal where 1.0 is 100% efficiency.')
        elif att == 'Max Power':
            self.att_frame(att, 'Numeric', 'The max power of the generation is the maximum possible power output of the unit.', 'kW', 'This value is used to calculate generation capacity factors and is used to cap power output during the simulation. If the calculated power output is higher than the designated max power during a given timestep, then the power output is set to the max power. This input is optional and can be used to account for capacity limitations of the generator or other electrical equipment. If an input is not given, then the max power is set to the calculated power at the maximum operating head and flow.')
        elif att == 'Cost of Start-Stops':
            self.att_frame(att, 'Numeric', 'The attributed cost of damages for one ramping cycle of the turbine.', '$', 'A ramping cycle consists of turning the module on and off. Turbines often accumulate damage during these cycles as the flow rate passes through cavitation ranges. More frequent start/stops reduce the expected life of the turbine, which can increase maintenance costs. This metric is optional and is one way of calculating turbine operating costs as a function of operation, as opposed to static annual module or annual plant O&M costs.')
        elif att == 'Maximum Headwater Drop':
            self.att_frame(att, 'Numeric', 'The maximum increase in headwater elevation with respect to the normal operating level allowed during module operation.', 'ft')
        elif att == 'Maximum Headwater Rise':
            self.att_frame(att, 'Numeric', 'The maximum decrease in headwater elevation with respect to the normal operating level allowed during module operation.', 'ft')
        elif att == 'Minimum Tailwater Level':
            self.att_frame(att, 'Numeric', 'The minimum tailwater elevation required for module operation.', 'ft')
        elif att == 'Maximum Tailwater Level':
            self.att_frame(att, 'Numeric', 'The maximum tailwater elevation allowable for module operation.', 'ft')
        elif att == 'Operating Mode':
            if self.mod_type == 'Sediment Passage':
                opts = 'Continuous, Sluicing, or Flushing'
                defin = 'The operating mode determines the conditions under which the module is allocated flow.'
                add_desc = 'Sediment modules can be operated in one of three modes. Continuous: these modules operate at consistent design flows throughout the operating months. Sluicing: these modules operate whenever a designated inflow threshold is met.  Flushing: these modules are used for drawdown flushing where the headpond level is decreased and sediment is passed through low-level outlets at high velocity.'
                self.att_frame(att, 'Option Menu', defin,opts,add_desc=add_desc)
            elif self.mod_type == 'Water Passage':
                opts = 'Continuous, Controlled Spillway, or Uncontrolled Spillway'
                defin = 'The operating mode determines the effect of spillway flow on the headwater elevation.'
                add_desc = 'Water passage modules can operate in one of three modes. Continuous: these modules pass a constant discharge during the simulation timestep. Controlled Spillway: these modules can regulate the amount of flow through the module to maintain a constant headwater elevation. Uncontrolled Spillway: these modules pass flow, but are not able to regulate the headwater elevation (e.g. weirs).'
                self.att_frame(att, 'Option Menu', defin,opts,add_desc=add_desc)
        elif att == 'Operating Flow':
            self.att_frame(att, 'Numeric', 'The minimum inflow threshold required to mobilize bed-load sediments and open the sluice gate.', 'cfs', 'Sediment sluices will only be allocated flow if the total inflow is greater than the operating flow.')
        elif att == 'Flushing Duration':
            self.att_frame(att, 'Numeric', 'The number of timesteps (days) required to flush the reservoir.', 'days', 'This input is only required when the module operates in flushing mode. During flushing events, all passage modules except for spillway and sediment modules are turned off.')
        elif att == 'Operating Frequency':
            self.att_frame(att, 'Numeric', 'The number of flushing events per year.', 'flushes/year', 'This input is only required when the module operates in flushing mode. During flushing events, all passage modules except for spillway and sediment modules are turned off. Flushing events occur at the first available time step. Flushing events outside of the simulation time are not considered.')
        elif att == 'Weir Coefficient': 
            self.att_frame(att, 'Numeric', 'A constant based on the shape of the weir.', 'ft^(1/2)/s', 'This input is only required in uncontrolled spillway mode.')
        elif att == 'Crest Height':
            self.att_frame(att, 'Numeric', 'The height of the top of the weir in reference to the bed elevation.', 'ft', 'This input is only required in uncontrolled spillway mode. The crest height should be at least higher than the normal operating level')
        elif att == 'Site Name':
            self.att_frame(att, 'Text', 'The name of the project.', add_desc='This value is used to identify simulation runs.')
        elif att == 'Stream Width':
            self.att_frame(att, 'Numeric', 'The distance between left and right banks along the dam axis at the height corresponding to the defined normal operating level.', 'ft', 'This value is used as a mininum for the total width of instream modules. ')
        elif att == 'Dam Bed Elevation':
            self.att_frame(att, 'Numeric', 'The bed elevation above mean sea level at the dam axis.', 'ft amsl', 'This input is solely used for graphics and is set to a default of 100ft asl.')
        elif att == 'Stream Slope':
            self.att_frame(att, 'Numeric', 'The average stream slope of the stream reach prior to development.', 'ft', 'This value is used in several places including the sediment entrainment and reservoir volume model support tools.')
        elif att == 'Trap Efficiency Parameter':
            self.att_frame(att, 'Numeric', 'A dimensionless sedimentation factor (Beta) used with the Siyam (2000) formulation of the Brune model to reflect the reduction un reservoir storage capacity due to sedimentation.', 'unitless (0-1)', 'A value of 1 resembles a mixer tank where all sediment is kept in suspension, while a value close to 0 resembles a desilting basin where all sediment falls out of suspension. Thus, smaller values indicate a greater likelihood of sedimentation, which can result from many factors including larger sediment sizes. The original Brune curve illustrated upper, median, and lower curves with values of 0.0055, 0.0079, and 0.015, respectively.')
        elif att == 'Stage-Discharge Curve':
            self.att_frame(att, 'Equation', 'The water depth in the stream prior to development as a function of inflow.', add_desc='The Y value is the river stage in (ft) and the X value is the inflow in (cfs). This equation is used to determine the tailwater elevation after development, which is assumed to maintain similar hydraulic properities.')
        elif att == 'Stage-Storage Curve':
            self.att_frame(att, 'Equation', 'The reservoir volume as a function of the headwater elevation.', add_desc='The Y value is the reservoir volume (ft3) and the X value is the headwater elevation (ft). This equation is used to calculate the sediment trapping efficiency.')
        elif att == 'Energy Price':
            self.att_frame(att, 'Numeric', 'The average price of energy.', '$/MWh', 'Average wholesale energy prices can range from $20/MWh to $60/MWh depending on the region and market trends while hydropower plants typically recieve power purchase agreements for 40-50 $/MWh per the US Hydropower Market Report (2021).')
        elif att == 'Additional Capital Costs':
            self.att_frame(att, 'Numeric', 'The one-time, fixed expenses incurred on capital assets that are not covered by the module capital costs.', '$', 'This can be used to include the costs for buildings, property, eletrical equipment, etc. that do retain value after commissioning. This cost category is included in the initial capital costs (ICC) calculation.')
        elif att == 'Additional Non-Capital Costs':
            self.att_frame(att, 'Numeric', 'The one-time expenses incurred during the development process that do not involve capital assets.', '$', 'This can be used to include the costs for the care of water, parking, recreational features, etc. that do not retain value after commissioning. This cost category is included in the initial capital costs (ICC) calculation.')
        elif att == 'Excavation Rate':
            self.att_frame(att, 'Numeric', 'The cost to excavate overburden material as a function of dam foundation area.', '$/ft2', 'This is one option for pricing excavation. The cost to excavate is this value times the total area of all modules. These costs can also be incorporated into the module capital costs or in the additional cost categories above. ')
        elif att == 'Overhead Cost':
            self.att_frame(att, 'Numeric', 'The cost of overhead activities such as licensing and administration. ', '(%) Percent of ICC or ($) Total Cost', 'Can be input as either a lump sum or as a percent of initial capital costs (ICC). If entered as percent of ICC, please enter as 0-100, rather than as a decimal.')
        elif att == 'Engineering Cost':
            self.att_frame(att, 'Numeric', 'The cost of engineering activities.', '(%) Percent of ICC or ($) Total Cost', 'Can be input as either a lump sum or as a percent of initial capital costs (ICC). If entered as percent of ICC, please enter as 0-100, rather than as a decimal.')
        elif att == 'Contingency Allowance':
            self.att_frame(att, 'Numeric', 'The cost of unexpected expenditures.', '(%) Percent of ICC or ($) Total Cost', 'Can be input as either a lump sum or as a percent of initial capital costs (ICC). If entered as percent of ICC, please enter as 0-100, rather than as a decimal.')
        elif att == 'Annual O&M Cost':
            self.att_frame(att, 'Numeric', 'The annual cost to operate and maintain the facility.', '(%) Percent of ICC or ($) Total Cost', 'Can be input as either a lump sum or as a percent of initial capital costs (ICC). If entered as percent of ICC, please enter as 0-100, rather than as a decimal.')
        elif att == 'Value of Recreation':
            self.att_frame(att, 'Numeric', 'The revenue associated with each recreation module as a functional of availability.', '$/hr', 'While recreation may not be monetized in practice, this is one option for incorporating the value of recreational features to the public.')
        elif att == 'Flood Cost':
            self.att_frame(att, 'Numeric', 'The cost per unit of flow exceeding the facility hydraulic capacity during a given timestep.', '$/cfs', 'Any flow exceeding the flow capacity of all modules will be called over-flow and will incur a flood cost equal to this value times the amount of excess flow.')
        elif att == 'Discount Rate':
            self.att_frame(att, 'Numeric', 'The rate used to discount future cashflows and determine the present value of those cashflows. ', '%', 'This value is used in the calculation of net present value. Please enter as 0-100, rather than as a decimal (i.e. 8% should be entered as 8, and not 0.08)')
        elif att == 'Project Life':
            self.att_frame(att, 'Numeric', 'The expected duration of project operation before plant retirement. ', 'yr', 'This value is used in the calculation of net present value.')
        elif att == 'Normal Operating Level':
            self.att_frame(att, 'Numeric', 'The headwater elevation with respect to the bed elevation at the dam axis that is maintained during normal operation', 'ft', 'If the spillway is controlled, then the headwater level is assumed constant at the normal operating level. If the spillway is uncontrolled, then the crest height must be at least as high as the normal operating level, and any flow allocated to the spillway causes the headwater level to increase.')
        elif att == 'Test Data Start Date':
            self.att_frame(att, 'Date', 'The start date for the simulation period.', 'MM/DD/YYYY', 'The start date must be within the range of dates in the inflows tab.')
        elif att == 'Test Data End Date':
            self.att_frame(att, 'Date', 'The end date for the simulation period.', 'MM/DD/YYYY', 'The end date must be within the range of dates in the inflows tab.')
        elif att == 'Allow Turbine Over-run':
            self.att_frame(att, 'Yes or No', 'This determines whether the generation modules can be allocated flow greater than the design flow when excess flow is available.', add_desc='If yes, then all modules will first be allocated their design flow and then will be ramped up to their max flow if flow is available. This allows the modules to generate more power, but at lower efficiencies. If no, then the module cannot be allocated flow above the design flow.')
        elif att == 'Downstream Guidance Efficiency':
            self.att_frame(att, 'Numeric', 'The percentage of species individuals entrained in the flow allocated to the module that are safely excluded from flow into the module.', unit='(0-100)%', add_desc='A guidance efficiency of 0% means all fish that attempt to enter the module will enter, while an efficiency of 100% means that all fish will be excluded and guided to another structure. This metric is normally measured for fish guidance structures like bar rack and louvers. The value depends on many factors including species physiology, structure dimensions, and flow velocity. Efficiencies can vary between 0% to 100% depending on the technology (see User Guide for examples). Modules without upstream fish guidance structures should assume a guidance efficiency of 100%.')
        elif att == 'Downstream Mortality Rate':
            self.att_frame(att, 'Numeric', 'The percentage of species individuals that are killed or unable to reproduce after passage through the module.', unit='(0-100)%', add_desc='A mortality rate of 0% means that no fish that pass through the module are harmed, while a mortality rate of 100% means that no fish can safely pass. This metric is normally measured for turbines and spillways. The value depends on many factors including species physiology, technology dimensions (e.g., blade length), and flow characteristics. Rates can vary between 0% to 100% depending on the technology (see User Guide for examples). Modules without fish safety features should assume a mortality rate of 100%, while low-head overflow spillways may assume a low mortality rate since low-head spillways were shown to have inconsequential impact on fish passage.')
        elif att == 'Upstream Entrance Efficiency':
            self.att_frame(att, 'Numeric', 'The percentage of species individuals that can successfully enter the module after being attracted to the entrance.', unit='(0-100)%', add_desc='An entrance efficiency of 0% means that no fish can enter the module, while an entrance efficiency of 100% means that all fish can enter safely. This metric is normally measured for volitional fishways. The value depends on the species of interest and the hydraulics of the entrance. Efficiencies can vary between 0% to 100% depending on the technology (see User Guide for examples). Modules without fish passage capabilities should assume a value of 0% unless there is a chance of species entering the module from the downstream side. ')
        elif att == 'Upstream Passage Efficiency':
            self.att_frame(att, 'Numeric', 'The percentage of species individuals that can successfully ascend the module after entering.', unit='(0-100)%', add_desc='A passage efficiency of 0% means that no fish can ascend, while a passage efficiency of 100% means that all fish can ascend safely. This metric is normally measured for volitional fishways. The value depends on the species of interest and the hydraulics of the entrance. Efficiencies can vary between 0% to 100% depending on the technology (see User Guide for examples), although 100% passage rates can be difficult to achieve. Modules without species passage capabilities should assume an efficiency of 0%. ')
        elif att == 'Foundation Depth':
            self.att_frame(att, 'Numeric', 'The thickness of the fouantion module that represents the distance from the top of stable bedrock (after treatment) to the bottom of the overlying modules.', unit='ft')
        elif att == 'Species Name':
            self.att_frame(att, 'Text', 'The name of the species that is used for indexing the Species object throughout figures.')
        elif att == 'Upstream Migratory Months':
            self.att_frame(att, 'Checkbox', 'The months during which the species travel upstream across the dam.', add_desc='The upstream effective passage perfomance of the Species object is only calculated during these months.')
        elif att == 'Downstream Migratory Months':
            self.att_frame(att, 'Checkbox', 'The months during which the species travel downstream across the dam.', add_desc='The downstream effective passage perfomance of the Species object is only calculated during these months.')
        elif att == 'Relative Discharge Parameter (a)':
            self.att_frame(att, 'Numeric', 'A dimensionless parameter used to determine the attraction efficiency function.', add_desc='The higher the value, the higher the relative discharge threshold, which means that modules require more flow relative to the total outflow to attract fish. The relative discharge parameter (a) times the attraction sensitivity parameter equals the 50% attraction relative discharge threshold. Recommended values are betweeen 0.1-1.')
        elif att == 'Attraction Sensitivity Parameter (b)':
            self.att_frame(att, 'Numeric', 'A dimensionless parameter used to determine the attraction efficiency function.', add_desc='The higher the value, the steeper the attraction efficiency function, meaning that modules are penalized more strictly in terms of attraction for smaller changes in relative discharge past the relative discharge threshold. The relative discharge parameter (a) times the attraction sensitivity parameter equals the 50% attraction relative discharge threshold. Recommended values are betweeen 0.1-1.')
        elif att == 'Spillway Notch Flow':
            self.att_frame(att, 'Numeric', 'The flow allocated to the spillway that can help meet minimum flows, but does not affect headwater calculations.', add_desc='This value is optional and can be used to represent cuts or notches in the weir that provide spillway flows that do not contribute to the headwater relationship. This enables the spillway to more accurately calculate the headwater at each timestep and the flow allocation during fish passage modeling.', unit='cfs')
        elif att == 'Spillway Minimum Flow':
            self.att_frame(att, 'Numeric', 'The flow requirement that must be passed downstream over the spillway to meet minimum flow requirements.', add_desc='The value is optional and can be set at constant flow or at a percent of the inflow. During simulation the flow will be allocated to the spillway prior to operation of any other modules. Any spillway notch flows also count towards this minimum flow constraint. Currently these minimum flows can only be passed through the spillway, although we recommend setting a high priority for another module if you wish to pass minimum flows through another module.', unit='cfs')
        elif att == 'Generation Dispatch Mode':
            self.att_frame(att, 'Option Menu', 'The method used to allocate flow between the generation modules.', add_desc='Design Flow - turbines are ramped from smallest to largest. When flow is available, modules are ramped to the design flow before turning on the next module. This method is the fastest and is best  used when peak efficiencies occur at the design flow.\nPeak Efficiency - turbines are ramped from smallest to largest. When flow is available, modules are ramped to the peak efficiency flow before ramping the next module. Once all modules are ramped to the peak efficiency, then they are ramped to the design flow. This method is between the other two in terms of speed and should be used for turbines where the peak efficiency is not close to the design flow (e.g., Kaplan turbines).\nGreedy - a greedy algorithm is used to determine the distribution of flows across modules. This method is the slowest method and should be used when using modules of different sizes.')
        elif att == 'LCOE ($/MWh)':
            self.att_frame(att, 'Checkbox', 'LCOE stands for levlized cost of energy, which is the lifetime discounted costs of the project divided by the discounted annual energy generation.',add_desc='This is the recommended objective metric because it factors both energy and annual costs without consideration for the energy price. Conventional hydropower and other renewables target LCOEs around $40/MWh',unit='$/MWh')
        elif att == 'NPV ($)':
            self.att_frame(att, 'Checkbox', 'NPV stands for net present value, whish is the lifetime discounted net profit of the project.',add_desc='This objective metric is similar to LCOE but accounts for the price of energy. Projects should be built if the net present value is positive and exceeds the total lifetime revenue target.',unit='$')
        elif att == 'ICC ($)':
            self.att_frame(att, 'Checkbox', 'ICC stands for initial capital cost, which is the one-time cost of capital assets for the project.', add_desc='This includes any module capital costs the additional capital cost item in the Cost Table object.',unit='$')
        elif att == 'Unit cost ($/kW)':
            self.att_frame(att, 'Checkbox', 'The one-time total cost of the project, including capital assets and non-capital expenses, divided by the nameplate capacity of the project.',add_desc='This does not include operation and maintenance costs or energy generation.',unit='$/kW')
        elif att == 'Geometric Coefficient':
            self.att_frame(att, 'Numeric', 'A dimensionless coefficient that determines how quickly the reservoir narrows.',add_desc='The geometric coefficient should typically range between 0.5 to 0.16 with a recommended value of 0.26. Larger coefficients represent larger volume to stage ratios.',unit='dimensionless')
        elif att == 'Mean Daily Flow':
            self.att_frame(att, 'Numeric', 'The average daily flow rate.',add_desc='This is used in place of the inflow time series for this support tool.',unit='cfs')
        elif att == 'Height':
            self.att_frame(att, 'Numeric', 'The vertical distance from the bed elevation to the top or crest of the module.', add_desc='This value is used in the calculation of volume.', unit='ft')
        else:
            print('Unknown attribute')
                
    #Adds additional links and buttons to support tools for a given tool name
    def add_tools(self, tool_name):
        if tool_name == 'Tool Tip - Use Google Earth':
            self.create_label('Stream widths can be found using Google Earth and the distance measuring tool. A link is provided below.')
            self.obj_list.append(tk.Label(self.frame, font=LINK_FONT, bg=FRAME_BG_COLOR, fg=LINK_FG_COLOR, text='Google Earth'))
            self.obj_list[1].bind("<Button-1>", lambda e: callback('https://www.google.com/earth/'))
        elif tool_name == 'Stage-Discharge Download':
            self.create_label('This tool will automatically download and regress stage-discharge data from USGS gage to generate a stage-discharge curve. The data can be imported as an equation to the model or press the View Table button to export as a csv.')
            self.btn_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
            self.download_btn = tk.Button(self.btn_frame, text='USGS Download', font=TEXT_FONT, command=lambda:self.open_data_download())
            self.import_btn = tk.Button(self.btn_frame, text='Import', font=TEXT_FONT, command=lambda:self.import_btn_press())
            self.view_btn = tk.Button(self.btn_frame, text='View Table', font=TEXT_FONT, command=lambda:self.view_table())
            self.btn_frame.columnconfigure((0,1,2),weight=1)
            self.download_btn.grid(row=1, column=0, padx=5, pady=5, sticky='nsew')
            self.import_btn.grid(row=1, column=1, padx=5, pady=5, sticky='nsew')
            self.view_btn.grid(row=1, column=2, padx=5, pady=5, sticky='nsew')
            self.obj_list.append(self.btn_frame)
        elif tool_name == 'Stream Slope Data':
            self.create_label('Stream slopes can be found at the SMH Explorer tool. A link is provided below.')
            self.obj_list.append(tk.Label(self.frame, font=LINK_FONT, bg=FRAME_BG_COLOR, fg=LINK_FG_COLOR, text='SMH Explorer'))
            self.obj_list[1].bind("<Button-1>", lambda e: callback('https://www.arcgis.com/apps/webappviewer/index.html?id=a93eb1fcbd8e47abb7792f92374d4908'))
        elif tool_name == 'Trap Efficiency Model':
            self.create_label('The Trap Efficiency Support tool lets the user calculate example trap efficiecies using the models from Eizel-Din (2010).')
            self.btn_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
            self.model_btn = tk.Button(self.btn_frame, text='Launch', font=TEXT_FONT, command=lambda:self.open_trap_efficiency_model())
            self.btn_frame.columnconfigure((0),weight=1)
            self.model_btn.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
            self.obj_list.append(self.btn_frame)
        elif tool_name == 'Attraction Efficiency Model':
            self.create_label('The attraction efficiency model support tool lets the user visualize the attraction efficiency function created by the Relative Discharge Parameter (a) and the Attraction Sensitivity Parameter (b).')
            self.btn_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
            self.model_btn = tk.Button(self.btn_frame, text='Launch', font=TEXT_FONT, command=lambda:self.open_attraction_efficiency_model())
            self.btn_frame.columnconfigure((0),weight=1)
            self.model_btn.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
            self.obj_list.append(self.btn_frame)
        elif tool_name == 'Geometric Reservoir Approach':
            self.create_label('The Geoemtric Reservoir Support tool allows the user to estimate the stage-storage relationship based on a assumed pyramid geometry, which has been used by Lawrence and Cascio (2004) in sedimentation estimates of small dams.')
            self.btn_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
            self.model_btn = tk.Button(self.btn_frame, text='Launch', font=TEXT_FONT, command=lambda:self.open_stage_storage_model())
            self.import_btn = tk.Button(self.btn_frame, text='Import', font=TEXT_FONT, command=lambda:self.import_btn_press())
            self.btn_frame.columnconfigure((0,1),weight=1)
            self.eq_add_frame = EquationAddFrame(self.btn_frame, self.controller,'Geometric Stage-Storage','Normal Operating Level (ft)', 'Reservoir Volume (ft3)' )
            self.model_btn.grid(row=1, column=0, padx=5, pady=5, sticky='nsew')
            self.import_btn.grid(row=1, column=1, padx=5, pady=5, sticky='nsew')
            self.obj_list.append(self.btn_frame)
        elif tool_name == 'Turbine Head Efficiency':
            self.create_label('The turbine head efficiency equation determines a power output efficiency coefficient (See equation XXX in the User Guide) as a function of the relative head, which is the gross head across the turbine divided by the design head (i.e. design head = 100%). Head efficiencies are uncommon in the literature, so this is an optional input and the head efficiency coefficient defaults to 1.\n\nThe X (relative head) should be given as decimals 1.0 referring to 100% efficient. The upper and lower bounds of X should at least span the operating range specified by the minimum and maximum operating limits.\n\nThe Y value (power efficiency) should be calculated as a decimal where 1.0 is 100% efficiency.\n\nA default head efficiency equation is given in Gordon (2001) and can be imported using the button below.')
            self.out_var = mc.Equation('Francis Head Efficiency Curve (Gordon)', 'Polynomial-2', [-0.5, 1, 0.5], 'Relative Head (% of Design Head)','Efficiency (%)', lower_bound=0.0,upper_bound=2.0)
            self.add_equation_btn(self.out_var)
        elif tool_name == 'Sluicing Operating Flow':
            self.create_label('Sediment operating flow is the minimum inflow threshold required to mobilize bed-load sediments and open the sluice gate. Sediment sluices will only be allocated flow if the total inflow is greater than the operating flow. The model below can be used to determine an operating flow based on expected entrainment probabilities for a particle size class.')
            self.btn_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
            self.model_btn = tk.Button(self.btn_frame, text='Launch', font=TEXT_FONT, command=lambda:self.open_entrain_model())
            self.import_btn = tk.Button(self.btn_frame, text='Import', font=TEXT_FONT, command=lambda:self.import_btn_press())
            self.btn_frame.columnconfigure((0,1),weight=1)
            self.rec_flow_lbl = tk.Label(self.btn_frame, text='Use the entrainment model to determine recommended flow.', font=TEXT_FONT, bg=FRAME_BG_COLOR)
            self.rec_flow_lbl.grid(row=0, column=0, columnspan=2,padx=5, pady=5, sticky='nsew')
            self.model_btn.grid(row=1, column=0, padx=5, pady=5, sticky='nsew')
            self.import_btn.grid(row=1, column=1, padx=5, pady=5, sticky='nsew')
            self.obj_list.append(self.btn_frame)
        elif tool_name == 'Tool Tip - Uncontrolled Spillway':
            self.create_label('Uncontrolled spillways cannot regulate flow, so the outflow is a function of the headwater level. Given the flow allocation methodology, the headwater level must be determined for a designated spillway flow. This requires an iterative flow allocation process and back-solving the typical weir equation. The typical weir equation, which relates head over the weir to discharge, is\n\tQ=CL(H^1.5)\nwhere Q = Flow, C = Weir Coefficient, L = Weir Length, H = Head over weir.\n\nThe Weir Coefficient (C): is a constant based on the shape of the weir with the units of ft^(1/2)/s. Typical values range between 2.6-4. Please refer to the USBR Technical Manual (linked below) for common weir coefficients.\n\nCrest Height: the height of the top of the weir in reference to the bed elevation, given in ft. The crest height should be at least higher than the normal operating level. This value is used to calculate the head over the weir (H).')
            self.obj_list.append(tk.Label(self.frame, font=LINK_FONT, bg=FRAME_BG_COLOR, fg=LINK_FG_COLOR, text='USBR Technical Manual (for Weir Coefficients)'))
            self.obj_list[1].bind("<Button-1>", lambda e: callback('https://www.usbr.gov/tsc/techreferences/mands/wmm/'))
        elif tool_name == '':
            pass
        else:
            print('tool name not recognized')
    
#%%## Support Models - these are the extra model functions that can be used through certain support tools
#Lets the user visualize the fish attraction efficiency for different a and b values
class AttractionEfficiencyModel(tk.Toplevel):
    def __init__(self, parent, controller):
        tk.Toplevel.__init__(self)
        self.parent = parent
        self.controller = controller
        plt.ioff()
        self.fig = plt.figure(figsize=(4.5,3))
        self.ax = self.fig.add_subplot(111)
        self.my_eq = []
        
        self.myframe = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.myframe.columnconfigure((0,1,2,3), weight=1)
        self.myframe.pack(fill='x', expand=True)
          
        self.canvas_fig = FigureCanvasTkAgg(self.fig, master=self.myframe)
        self.title_lbl = tk.Label(self.myframe, text='Attraction Efficiency Model', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.directions_lbl = tk.Label(self.myframe, text='This is a novel model that aims to quantify the attraction efficiency of a module based on the module relative discharge. A common problem for fishways are insufficient attraction flows. Fish tend to follow bulk flows to follow the mainstem river, so without sufficient flow, fish may be unable to find the fishway entrance. This model frames attraction efficiency as a sigmoid curve or step function that penalizes attraction whenever the module relative discharge is below a user-defined threshold. The following parameters determine the shape of the attraction efficiency curve. Design manuals recommedn between 5-10% relative discharge thresholds to minimize attraction efficiency losses.', font=TEXT_FONT, bg=DIRECTIONS_BG_COLOR, wraplength=self.parent.wrap_length, justify='left')
        self.update_btn = tk.Button(self.myframe, text='Update', font=TEXT_FONT, command=lambda:self.update())
        
        self.title_lbl.grid(row=0, column=0, columnspan=4, sticky='nsew')
        self.directions_lbl.grid(row=1, column=0, columnspan=4, pady=5, sticky='nsew')
        
        self.input_dict = {'Relative Discharge Parameter (a)': [['text entry'], '', [float], ['Attraction Efficiency Model'], False], \
                           'Attraction Sensitivity Parameter (b)': [['text entry'], '', [float], ['Attraction Efficiency Model'], False]}

        self.att_labels, self.att_entries, self.att_units, self.att_tools, self.input_vars = create_inputs(self, self.myframe, self.input_dict)
        pack_attributes(self, self.myframe, 2)

        self.update_btn.grid(row=4, column=0, columnspan=4, padx=5, pady=5, sticky='nsew')
        self.canvas_fig.get_tk_widget().grid(row=5,rowspan=2, column=0, columnspan=5, padx=0, pady=5, sticky='nsew')
        self.set_defaults()
        self.update()
        
    #Gather the input a and b values, error check, and update the figure
    def update(self):
        ad = get_values(self)
        if ad is False:
            return False
        try:
            self.my_func = self.get_attraction_function(ad['Relative Discharge Parameter (a)'], ad['Attraction Sensitivity Parameter (b)'])
            self.fig, self.ax = self.plot_attraction_fig(self.fig, self.ax)
            self.fig.canvas.draw()
            self.canvas_fig.draw()
            return True
        except:
            tk.messagebox.showerror('Error', 'Unable to create equation, please check inputs.')
            return False
        
    #This the attraction efficiency function with a_s and b_s as inputs
    def get_attraction_function(self, a, b):
        return lambda x: 1/(1 + math.exp(-100*(((1/a)*x)-b)))

    #Set the default parameters
    def set_defaults(self):
        self.att_entries['Relative Discharge Parameter (a)'].insert(0, '0.8')
        self.att_entries['Attraction Sensitivity Parameter (b)'].insert(0, '0.05')
        
    #Plots the fish attraction efficiency function
    def plot_attraction_fig(self, fig=None, ax=None, hide=True):
        if hide == True:
            plt.ioff()
        else:
            plt.ion()

        if ax is None:
            fig, ax = plt.subplots()
        else:
            ax.clear()
        
        Qs = [i/1000 for i in range(0, 100000)] #plots 0.001 to 100 in 0.001 increments
        As = [self.my_func(q) for q in Qs]
        
        ax.plot(Qs, As)
        ax.set_xlim(0.001, 100)
        ax.set_ylim(0, 1.1) 
        ax.set_xscale('log')
        ax.set_title('Attraction Efficiency Function')
        ax.set_xlabel('Relative Discharge (%)')
        ax.set_ylabel('Attraction Efficiency(%)')
        plt.tight_layout()
        return fig, ax

#Lets the user test the geometric reservoir model for different parameter values
class GeoReservoirModel(tk.Toplevel):
    def __init__(self, parent, controller):
        tk.Toplevel.__init__(self)
        self.parent = parent
        self.controller = controller
        plt.ioff()
        self.fig = plt.figure(figsize=(4,3))
        self.ax = self.fig.add_subplot(111)
        self.my_eq = []
        
        self.myframe = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.myframe.columnconfigure((0,1,2,3), weight=1)
        self.myframe.pack(fill='x', expand=True)
          
        self.canvas_fig = FigureCanvasTkAgg(self.fig, master=self.myframe)
        
        self.title_lbl = tk.Label(self.myframe, text='Geometric Reservoir Model', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.directions_lbl = tk.Label(self.myframe, text='This model based on Lawrence and Cascio (2004) uses a simple geometric approach to stage-storage models. This model assumes the reservoir is similar to a triangular pyramid whose base is the dam cross section and extends upstream. The model uses the stream width at the dam axis, the average stream slope, and a geometric coefficient that determines how quickly the reservoir narrows. The geometric coefficient should range between 0.5 to 0.16 with a recommended value of 0.26. Larger coefficients represent larger volume to stage ratios.', font=TEXT_FONT, bg=DIRECTIONS_BG_COLOR, wraplength=self.parent.wrap_length, justify='left')
        self.update_btn = tk.Button(self.myframe, text='Update', font=TEXT_FONT, command=lambda:self.update())
        self.import_btn = tk.Button(self.myframe, text='Import', font=TEXT_FONT, command=lambda:self.import_eq())
        
        self.title_lbl.grid(row=0, column=0, columnspan=4, sticky='nsew')
        self.directions_lbl.grid(row=1, column=0, columnspan=4, pady=5, sticky='nsew')
        
        self.input_dict = {'Stream Slope': [['text entry'], 'ft/ft', [float],[], True], \
                       'Stream Width': [['text entry'], 'ft', [float],[], True], \
                          'Geometric Coefficient': [['text entry'], 'dimensionless (0-1)', [float],[], True]}
            
        self.defaults = {'Stream Slope':0.002, \
                       'Stream Width': 400, \
                          'Geometric Coefficient': 0.26}

        self.att_labels, self.att_entries, self.att_units, self.att_tools, self.input_vars = create_inputs(self, self.myframe, self.input_dict)
        pack_attributes(self, self.myframe, 2)
        
        self.update_btn.grid(row=6, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')
        self.import_btn.grid(row=6, column=2, columnspan=2, padx=5, pady=5, sticky='nsew')
        self.canvas_fig.get_tk_widget().grid(row=7,rowspan=2, column=0, columnspan=5, padx=0, pady=5, sticky='nsew')
        self.set_defaults()
        self.update()
        
    #Gathers values, error checks, and updates the equation and figure
    def update(self):
        ad = get_values(self)
        if ad is False:
            return False
        try:
            self.my_eq = af.geometric_reservoir_volume(ad['Stream Slope'], ad['Stream Width'], ad['Geometric Coefficient'])
            self.fig, self.ax = self.my_eq.get_plot(self.fig, self.ax)
            self.fig.canvas.draw()
            self.canvas_fig.draw()
            return True
        except:
            tk.messagebox.showerror('Error', 'Unable to create equation, please check inputs.')
            return False
        
    #Sends the resulting equation to the parent frame
    def import_eq(self):
        if self.update():
            self.parent.update_stage_storage_model(self.my_eq)
            self.destroy()
        
    #Sets default values for the inputs
    def set_defaults(self):
        clear_entries([self.att_entries['Stream Slope'], self.att_entries['Stream Width']])
        if self.controller.site is not None:
            if self.controller.site.energy_slope is not None:
                self.att_entries['Stream Slope'].insert(0, str(self.controller.site.energy_slope))
            if self.controller.site.stream_width is not None:
                self.att_entries['Stream Width'].insert(0, str(self.controller.site.stream_width))
        else:
            for key in self.input_dict:
                self.att_entries[key].insert(0, str(self.defaults[key]))
        key='Geometric Coefficient'
        self.att_entries[key].insert(0, str(self.defaults[key]))

#This lets the user play around with the trap efficiency model for different parameter and equation values
class TrapEfficiencyModel(tk.Toplevel):
    def __init__(self, parent, controller):
        tk.Toplevel.__init__(self)
        self.parent = parent
        self.controller = controller
        self.my_trap = 0.0
        
        self.myframe = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.myframe.columnconfigure((0,1,2,3), weight=1)
        self.myframe.pack(fill='x', expand=True)
        self.result_var = tk.StringVar()          
        
        self.title_lbl = tk.Label(self.myframe, text='Trap Efficiency Model', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.directions_lbl = tk.Label(self.myframe, text='The average trap efficiency is the average percentage of incoming sediment that accumulates in the reservoir. The model for trap efficiency is based on Siyam (2000) as reported in Eizel-Din (2010). The method uses a flow-weighted capacity inflow ratio and a sedimentation parameter.', font=TEXT_FONT, bg=DIRECTIONS_BG_COLOR, wraplength=self.parent.wrap_length, justify='left')
        self.update_btn = tk.Button(self.myframe, text='Update', font=TEXT_FONT, command=lambda:self.update())
        self.result_lbl = tk.Label(self.myframe, textvariable=self.result_var, font=TEXT_FONT, bg=LABEL_BG_COLOR)
        
        self.title_lbl.grid(row=0, column=0, columnspan=4, sticky='nsew')
        self.directions_lbl.grid(row=1, column=0, columnspan=4, pady=5, sticky='nsew')
        
        self.input_dict = {'Trap Efficiency Parameter': [['text entry'], 'ft/ft', [float],[], True], \
                       'Stage-Storage Curve': [['Equation', ['Headwater vs. Volume', 'Normal Operating Level (ft)','Reservoir volume (cfs)']], 'ft', [float],[], True], \
                           'Normal Operating Level': [['text entry'], 'ft', [float],[], True], \
                          'Mean Daily Flow': [['text entry'], 'cfs', [float],[], True]}
            
        self.defaults = {'Trap Efficiency Parameter':0.0079, \
                       'Stage-Storage Curve': mc.Equation('Example Stage-Storage', 'Power', [87776, 2, 0], 'Headwater elevation (ft)', 'Reservoir volume (cfs)'), \
                          'Normal Operating Level': 16, \
                              'Mean Daily Flow': 4000}

        self.att_labels, self.att_entries, self.att_units, self.att_tools, self.input_vars = create_inputs(self, self.myframe, self.input_dict)
        pack_attributes(self, self.myframe, 2)

        self.update_btn.grid(row=6, column=0, columnspan=4, padx=5, pady=5, sticky='nsew')
        self.result_lbl.grid(row=7, column=0, columnspan=4, padx=5, pady=5, sticky='nsew')
        
        self.set_defaults()
        self.update()
        
    #The trap efficiency equation from Eizel-Din
    def calculate_trap_efficiency(self, ad):
        return min(1.0, 100*math.exp(-365*60*60*24*ad['Trap Efficiency Parameter']*ad['Mean Daily Flow']/ad['Stage-Storage Curve'].get_y(ad['Normal Operating Level'])))

    #Gathers values, error checks, calculates the trap efficiency, and updates the labels
    def update(self):
        ad = get_values(self)
        if ad is False:
            return False
        try:
            self.my_trap = self.calculate_trap_efficiency(ad)*100.0
            self.result_var.set('Trap efficiency: {}%'.format(round(self.my_trap, 4)))
        except:
            self.result_var.set('Trap efficiency: Could not compute')
        
    #Set default values for the inputs
    def set_defaults(self):
        if self.controller.site is not None:
            if self.controller.site.trap_b is not None:
                self.att_entries['Trap Efficiency Parameter'].insert(0, str(self.controller.site.trap_b))
            if self.controller.site.reservoir_eq is not None:
                self.att_entries['Stage-Storage Curve'].update_equation(self.controller.site.reservoir_eq)
        else:
            for key in self.input_dict:
                if key == 'Stage-Storage Curve':
                    self.att_entries[key].update_equation(self.defaults[key])
                else:
                    self.att_entries[key].insert(0, str(self.defaults[key]))
        if self.controller.preferences is not None:
            self.att_entries['Normal Operating Level'].insert(0, str(self.controller.preferences.nol))
        else:
            self.att_entries['Normal Operating Level'].insert(0, str(self.defaults['Normal Operating Level']))

#This model calculates the flow value that correlates to the probability for a particle size class to be entrained in the flow
class SedEntrainModel(tk.Toplevel):
    def __init__(self, parent, controller):
        tk.Toplevel.__init__(self)
        self.parent = parent
        self.controller = controller
        
        self.entry_width = 20
        self.fig = None
        self.ax = None
        self.rec_flow = 0
        
        self.myframe = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.myframe.columnconfigure((0,1,2,3), weight=1)
        
        self.size_names = ['Small Boulder', 'Large Cobble', 'Small Cobble', 'Very Coarse Gravel',\
                           'Coarse Gravel', 'Medium Gravel', 'Fine Gravel', 'Very Fine Gravel', \
                               'Very Coarse Sand', 'Coarse Sand', 'Medium Sand', 'Fine Sand', 'Very Fine Sand']
        self.size_mm = [362, 181, 90.5, 45.3, 22.6, 11.3, 5.66, 2.83, 1.4, 0.707, 0.354, 0.177, 0.088]
        self.size_opts = [self.size_names[i] + ' (' + str(self.size_mm[i]) + 'mm)' for i in range(0, len(self.size_names))]
        self.size_var = tk.StringVar()
        self.size_var.trace('w', self.on_menu_switch)
        
        self.title_lbl = tk.Label(self.myframe, text='Sediment Entrainment Model', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.directions_lbl = tk.Label(self.myframe, text='Use the following inputs to estimate a sediment sluice operating flow. Models described in section XXX of the report and are based on Witt et al. (2018).', font=TEXT_FONT, bg=DIRECTIONS_BG_COLOR, wraplength=self.parent.wrap_length)
        self.slope_lbl = tk.Label(self.myframe, text='Stream Slope', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.slope_entry = ttk.Entry(self.myframe, width=self.entry_width)
        self.slope_unit_lbl = tk.Label(self.myframe, text='ft/ft', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.size_lbl = tk.Label(self.myframe, text='Sediment Size (d50)', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.size_entry = ttk.Entry(self.myframe, width=self.entry_width)
        self.size_unit_lbl = tk.Label(self.myframe, text='mm or ->', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.size_menu = tk.OptionMenu(self.myframe, self.size_var, *self.size_opts)
        self.size_menu.configure(width=25)
        self.stage_lbl = tk.Label(self.myframe, text='Stage-Discharge Curve', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.stage_frame = EquationAddFrame(self.myframe, self.controller, 'Stage vs. Discharge Curve', 'Inflow (cfs)', 'Stage (ft)')
        
        self.prob_lbl = tk.Label(self.myframe, text='Entrainment Probability', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.prob_entry = ttk.Entry(self.myframe, width=self.entry_width)
        self.prob_unit = tk.Label(self.myframe, text='0-100', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.update_btn = tk.Button(self.myframe, text='Update', font=TEXT_FONT, command=lambda:self.update())
        self.import_btn = tk.Button(self.myframe, text='Import', font=TEXT_FONT, command=lambda:self.import_flow())
        
        
        self.myframe.pack(fill='x', expand=True)
        
        self.title_lbl.grid(row=0, column=0, columnspan=4, sticky='nsew', padx=5, pady=5)
        self.directions_lbl.grid(row=1, column=0, columnspan=4, sticky='nsew', padx=5, pady=0)
        self.slope_lbl.grid(row=2, column=0, columnspan=2, sticky='nsew', padx=5, pady=5)
        self.slope_entry.grid(row=2, column=2, columnspan=1, sticky='nsew', padx=5, pady=5)
        self.slope_unit_lbl.grid(row=2, column=3, columnspan=1, sticky='nsew', padx=5, pady=5)
        self.size_lbl.grid(row=3, column=0, columnspan=1, sticky='nsew', padx=5, pady=5)
        self.size_entry.grid(row=3, column=1, columnspan=1, sticky='nsew', padx=5, pady=5)
        self.size_unit_lbl.grid(row=3, column=2, columnspan=1, sticky='nsew', padx=5, pady=5)
        self.size_menu.grid(row=3, column=3, columnspan=1, sticky='nsew', padx=5, pady=5)
        self.stage_lbl.grid(row=4, column=0, columnspan=1, sticky='nsew', padx=5, pady=5)
        self.stage_frame.grid(row=4, column=1, columnspan=3, sticky='nsew', padx=5, pady=5)
        self.slope_lbl.grid(row=5, column=0, columnspan=1, sticky='nsew', padx=5, pady=5)
        self.slope_entry.grid(row=5, column=1, columnspan=1, sticky='nsew', padx=5, pady=5)
        self.slope_unit_lbl.grid(row=5, column=2, columnspan=1, sticky='nsw', padx=5, pady=5)
        self.prob_lbl.grid(row=6, column=0, columnspan=1, sticky='nsew', padx=5, pady=5)
        self.prob_entry.grid(row=6, column=1, columnspan=1, sticky='nsew', padx=5, pady=5)
        self.prob_unit.grid(row=6, column=2, columnspan=1, sticky='nsw', padx=5, pady=5)
        self.update_btn.grid(row=7, column=0, columnspan=2, sticky='nsew', padx=5, pady=5)
        self.import_btn.grid(row=7, column=2, columnspan=2, sticky='nsew', padx=5, pady=5)

        self.set_defaults()
        
    #Send flow to the parent frame
    def import_flow(self):
        if self.rec_flow <= 0:
            tk.messagebox.showerror('Unable to determine a reasonable flow value. Either the model was not run properly or the selected sediment size is too large or too small. Also, please check the bounds on the stage-discharge equation, which sets the possible flow range.')
        else:
            self.parent.update_sediment_model(round(self.rec_flow))
        
    #Set default inputs
    def set_defaults(self):
        if self.controller.site is not None:
            clear_entries([self.slope_entry])
            if self.controller.site.energy_slope is not None:
                self.slope_entry.insert(0, str(self.controller.site.energy_slope))
            else:
                self.slope_entry.insert(0, '0.002')
            self.stage_frame.update_equation(self.controller.site.stage_eq)
        else:
            self.slope_entry.insert(0, '0.002')
            clear_entries([self.size_entry])
            self.size_entry.insert(0, str(self.size_mm[11]))
        
        self.prob_entry.insert(0, '50')
        self.size_var.set(self.size_opts[11])
    
    #Gathers inputs, error checks, calculates the probability of entrainment curve, and redraws the figure
    def update(self):
        slope = check_entry(self.slope_entry.get(), [float])
        size = check_entry(self.size_entry.get(), [float])
        prob = check_entry(self.prob_entry.get(), [float])
        
        for i in [slope, size, prob]:
            if (str(i) == '') or (str(i) == 'Error'):
                tk.messagebox.showerror('Error', 'Unable to interpret inputs. Please double check inputs.')
                return
        
        stage_eq = self.stage_frame.get_equation()
        if stage_eq is None:
            tk.messagebox.showerror('Error', 'Please input a stage-discharge equation')
            return
        
        Qs, Ps = af.calc_entrainment_eq(slope, size, stage_eq)
        self.rec_flow = af.linear_interpolation(prob, Ps, Qs)
        self.fig, self.ax = self.plot_entrain_fig(Qs, Ps, prob)
        self.figure_canvas = FigureCanvasTkAgg(self.fig, master=self.myframe)
        self.figure_canvas.get_tk_widget().grid(row=8, column=0, columnspan=4, sticky='nsew')
        self.figure_canvas.draw()
        
    #Plots the sediment entrainment probability curve for the given stream slope, stage-discharge equation, and particle size
    def plot_entrain_fig(self, Qs, Ps, prob, fig=None, ax=None, hide=True):
        if hide == True:
            plt.ioff()
        else:
            plt.ion()

        if ax is None:
            fig, ax = plt.subplots()
        else:
            ax.clear()
        
        P_upper_bound = 99
        x_ulim = -1
        for i in range(0, len(Ps)):
            if Ps[i] > P_upper_bound:
                x_ulim = Qs[i]
                break
        
        if x_ulim < 0:
            x_ulim = max(Qs)

        ax.plot(Qs, Ps)
        ax.plot([0, self.rec_flow], [prob, prob], color='black')
        ax.plot([self.rec_flow, self.rec_flow], [0, prob], color='black')
        ax.text(0.01, 0.9, 'Recommended Flow: {}cfs'.format(str(round(self.rec_flow))), transform = ax.transAxes)
        ax.set_xlim(0, x_ulim)
        ax.set_ylim(0, 100)
        ax.set_title('Flow Entrainment Probability')
        ax.set_xlabel('Inflow (cfs)')
        ax.set_ylabel('Entrainment Probability (%)')
        plt.tight_layout()
        return fig, ax

    #Changes the particle size input when a standard particle size is selected from the optionmenu
    def on_menu_switch(self, name, idk, op):
        clear_entries([self.size_entry])
        for i in range(0, len(self.size_opts)):
            if self.size_var.get() == self.size_opts[i]:      
                self.size_entry.insert(0, str(self.size_mm[i]))
        

#%%## Busy Window
#Creates a little toplevel to show that the model is working on something
class busywindow(tk.Toplevel):
    def __init__(self, controller, text):
        tk.Toplevel.__init__(self)
        self.controller = controller
        self.l = tk.Label(self, text=text)
        self.l.pack()
    def cleanup(self):
        self.destroy()
        
#%%###Equation Add Frame - Frame that lets the user choose if they want to add an equation, then view or edit once it has been entered
class EquationAddFrame(tk.Frame):
    def __init__(self, parent, controller, equation_name, xlabel, ylabel, auto_type=None, zlabel=None):
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.controller = controller
        self.eq_name = equation_name
        self.eq_out = None
        self.auto_type = auto_type
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.zlabel = zlabel
        self.wrap_length=400
        
        self.update()
        
    #Sets the equation
    def update_equation(self, eq):
        self.eq_out = eq
        self.update()
        
    #Returns the equation
    def get_equation(self):
        return self.eq_out
        
    #Updates the label text and buttons when an equation is added
    def update(self):
        for widget in self.winfo_children():
            widget.destroy()
        if self.eq_out is None:
            self.name_lbl = tk.Label(self, text=self.eq_name, font=TEXT_FONT, bg=FRAME_BG_COLOR, wraplength=self.wrap_length)
            self.add_btn = tk.Button(self, text='Create Equation', font=TEXT_FONT, command=lambda:self.add_equation())
            self.name_lbl.pack(fill='x', expand=True)
            self.add_btn.pack(fill='x', expand=True)
        else:
            self.eq_lbl = tk.Label(self, text=self.eq_out.get_text(), font=TEXT_FONT, bg=FRAME_BG_COLOR)
            self.edit_btn = tk.Button(self, text='Edit', command=lambda:self.edit_equation())
            self.view_btn = tk.Button(self, text='View', command=lambda:self.view_equation())
            self.eq_lbl.grid(row=0,columnspan=2, column=0, sticky='nsew', pady=5)
            self.edit_btn.grid(row=1,columnspan=1, column=0, sticky='nsew', pady=5)
            self.view_btn.grid(row=1,columnspan=1, column=1, sticky='nsew', pady=5)
            self.columnconfigure((0,1), weight=1)
        
    #Opens the equation creator toplevel
    def add_equation(self, eq_orig=None):
        EquationCreator(self, self.controller, self.eq_name,self.xlabel, self.ylabel, eq_orig, self.auto_type, self.zlabel)
        
    #Opers the equation creator toplevel with the current equation parameters
    def edit_equation(self):
        self.add_equation(self.eq_out)
        
    #Creates a window that plots the equation
    def view_equation(self):
        self.eq_out.get_plot()
        
    
#Equation Creator - Frame that lets the user input an equation
class EquationCreator(tk.Toplevel):
    def __init__(self, parent, controller, equation_name, xlabel, ylabel, orig_equation=None, auto_type=None, zlabel=None, dynamic_type=None):
        tk.Toplevel.__init__(self)
        self.page_name = 'Equation Creator'
        self.parent = parent
        self.controller = controller
        self.eq_name = equation_name
        self.entry_width = 15
        self.orig_equation = orig_equation
        self.auto_type = auto_type
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.zlabel = zlabel
        self.wrap_length = 550
        self.width = 50
        self.dynamic_type = dynamic_type
        
        self.eq_types = ['Constant', 'Linear', 'Power', 'Polynomial-2', 'Polynomial-3', 'Binomial', 'Linear Regression', 'Piecewise']
        self.eq_desc = 'X: {}\nY: {}'.format(self.xlabel, self.ylabel)
        
        if self.zlabel is not None: #If two x-variables (x and z)
            self.eq_types = ['Constant', 'Linear', 'Power', 'Polynomial-2', 'Polynomial-3', 'Multi-Linear', 'Multi-Power', 'Binomial']
            self.eq_desc = 'X: {}\nY: {}\nZ: {}'.format(self.xlabel, self.ylabel, self.zlabel)
        
        if self.auto_type is not None:
            self.eq_types.append('USGS Auto Regression')
                
        self.letters = ['a','b','c','d','e','f','g'] #Used to index the variables 
        self.eq_info = {'Linear': [2, 'y = ax + b'], \
                        'Power': [3,'y = ax^b + c'], \
                        'Polynomial-2': [3,'y = ax^2 + bx + c'], \
                        'Polynomial-3': [4,'y = ax^3 + bx^2 + cx + d'], \
                        'Constant': [1, 'y = a'], \
                        'Multi-Linear': [5, 'y = ax^b + cz^d + e'], \
                        'Multi-Power': [4, 'y = a(x^b)(z^c) + d'], \
                        'Binomial': [5, 'y = a(bx + c)^d + e'], \
                        'Linear Regression': [0, 'Upload csv data and automatically regress the data into a linear, power, or polynomial-2 curve.'], \
                        'Piecewise': [0, 'Create a piecewise equation by specifying two equations with a shared bound.'], \
                        'USGS Auto Regression': [0, 'Automatically download data from USGS and regress into a linear, power, or polynomial-2 curve']}
        
        self.myframe = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.myframe.pack(fill='x', expand=True)
        
        self.name_lbl = tk.Label(self.myframe, text='Equation Creator', font=PG_TITLE_FONT, bg=TITLE_BG_COLOR)
        self.desc_lbl = tk.Label(self.myframe, text=self.eq_desc, font=TEXT_FONT, bg=DIRECTIONS_BG_COLOR, justify='left')
        self.manual_lbl = tk.Label(self.myframe, text='Select an equation type', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.eqframe = tk.Frame(self.myframe, bg=FRAME_BG_COLOR)
        self.type_var = tk.StringVar()
        self.type_menu = tk.OptionMenu(self.myframe, self.type_var, *self.eq_types)
        self.type_menu.config(width=self.width)
        self.type_var.trace('w', self.on_switch)
        
        if self.orig_equation == None:
            self.type_var.set(self.eq_types[0])
        else:
            self.type_var.set(self.orig_equation.form)
        
        self.name_lbl.pack(fill='x', padx=5, pady=5)
        self.desc_lbl.pack(fill='x', padx=5)
        self.manual_lbl.pack(fill='x', padx=5, pady=5)
        self.type_menu.pack(fill='x', padx=5)
        self.eqframe.pack(fill='x', expand=True, padx=5)
        self.eqframe.columnconfigure((0,1), weight=1)
        
        self.default_entries()

    #Opens a csvupload window if the user wants to regress data
    def csv_upload(self): 
        self.csv_window = csvUploadWindow(self, self.controller)
        
    #Opens the API window to grab data from USGS
    def auto_download(self):
        autodataFrame(self, self.controller, self.auto_type)
        
    #When data is uploaded, autoregress the data to create an equation
    def data_uploaded(self, df):
        if self.auto_type == 'Stage':
            x = 'Discharge (cfs)'
            y = 'Stage (ft)'
        else: #If the data is not from the API, then use the first two column headings, that is not the index
            x = df.columns[0]
            y = df.columns[1]
        try:
            out_eq = af.auto_regression(self.eq_name, df, x, y, remove_negative=True)
            if type(out_eq) == str:
                tk.messagebox.showerror('Error', 'Unable to upload and regress the data. {}'.format(out_eq))
            else:
                tk.messagebox.showinfo('Success', 'Regression sucessful.\nEquation: {}\nR2: {}\nUpper bound: {}\nLower Bound: {}'.format(\
                                        out_eq.get_text(), round(out_eq.regr_results['R2'],2), out_eq.ub, out_eq.lb))
                self.parent.update_equation(out_eq)
                self.destroy()
        except:
            tk.messagebox.showerror('Error', 'Unable to upload to regress data.')
            
    #When the type of equation is changed, update the entries and labels
    def on_switch(self, name, indx, op):
        for widget in self.eqframe.winfo_children():
            widget.destroy()
        
        self.eq_type = self.type_var.get()
        num_coeffs = self.eq_info[self.eq_type][0]
        lbl_text = self.eq_info[self.eq_type][1]

        self.form_label = tk.Label(self.eqframe, text=lbl_text,font=TEXT_FONT, bg=FRAME_BG_COLOR, wraplength=self.wrap_length, justify='left')
        self.form_label.grid(row=1, column=0, columnspan=2, sticky='nsew', pady=5, padx=5)
        
        self.coeff_entries = []
        self.letter_lbls = []
        row_counter = 2
        for i in range(num_coeffs):
            self.letter_lbls.append(tk.Label(self.eqframe, text=self.letters[i],font=TEXT_FONT, bg=FRAME_BG_COLOR, justify='right'))
            self.coeff_entries.append(ttk.Entry(self.eqframe, width=self.entry_width))
            self.letter_lbls[i].grid(row=row_counter, column=0, sticky='nse', pady=5)
            self.coeff_entries[i].grid(row=row_counter, column=1, sticky='nsw', pady=5)
            row_counter += 1
        
        self.ext_obj = []
        self.num_bounds= 0 
        if self.eq_type == 'Linear Regression':
            self.ext_obj.append(tk.Button(self.eqframe, text='CSV Upload', font=TEXT_FONT,command=lambda:self.csv_upload()))
        elif self.eq_type == 'Piecewise':
            self.ext_obj.append(EquationAddFrame(self.eqframe, self.controller, self.eq_name + ' - first', self.xlabel, self.ylabel, self.auto_type, self.zlabel))
            self.ext_obj.append(EquationAddFrame(self.eqframe, self.controller, self.eq_name + ' - second', self.xlabel, self.ylabel, self.auto_type, self.zlabel))
            self.ext_obj.append(tk.Button(self.eqframe, text='Create Equation', font=TEXT_FONT, command=lambda:self.create_equation()))
            self.num_bounds = 3
        elif self.eq_type == 'USGS Auto Regression':
            self.ext_obj.append(tk.Button(self.eqframe, text='USGS Download', font=TEXT_FONT,command=lambda:self.auto_download()))
        elif (self.eq_type == 'Multi-Linear') or (self.eq_type == 'Multi-Power'):
            self.ext_obj.append(tk.Button(self.eqframe, text='Create Equation', font=TEXT_FONT, command=lambda:self.create_equation()))
            self.num_bounds = 4
        else:
            self.ext_obj.append(tk.Button(self.eqframe, text='Create Equation', font=TEXT_FONT, command=lambda:self.create_equation()))
            self.num_bounds = 2
        
        if self.num_bounds >=2:
            self.lb_lbl = tk.Label(self.eqframe,text='Lower Bound',font=TEXT_FONT, bg=FRAME_BG_COLOR, justify='right')
            self.lb_entry = ttk.Entry(self.eqframe, width=self.entry_width)
            self.lb_lbl.grid(row=row_counter, column=0, sticky='nse', pady=5)
            self.lb_entry.grid(row=row_counter,  column=1, sticky='nsw', pady=5)
            row_counter+=1
            if self.num_bounds ==3:
                self.mb_lbl = tk.Label(self.eqframe,text='Middle Bound',font=TEXT_FONT, bg=FRAME_BG_COLOR, justify='right')
                self.mb_entry = ttk.Entry(self.eqframe, width=self.entry_width)
                self.mb_lbl.grid(row=row_counter, column=0, sticky='nse', pady=5)
                self.mb_entry.grid(row=row_counter, column=1, sticky='nsw', pady=5)
                row_counter+=1
            self.ub_lbl = tk.Label(self.eqframe,text='Upper Bound',font=TEXT_FONT, bg=FRAME_BG_COLOR, justify='right')
            self.ub_entry = ttk.Entry(self.eqframe, width=self.entry_width)
            self.ub_lbl.grid(row=row_counter, column=0, sticky='nse', pady=5)
            self.ub_entry.grid(row=row_counter,  column=1, sticky='nsw', pady=5)
            row_counter+=1
            if self.num_bounds == 4:
                self.zlb_lbl = tk.Label(self.eqframe,text='Z Lower Bound',font=TEXT_FONT, bg=FRAME_BG_COLOR, justify='right')
                self.zlb_entry = ttk.Entry(self.eqframe, width=self.entry_width)
                self.zlb_lbl.grid(row=row_counter, column=0, sticky='nse', pady=5)
                self.zlb_entry.grid(row=row_counter,  column=1, sticky='nsw', pady=5)
                row_counter+=1
                self.zub_lbl = tk.Label(self.eqframe,text='Z Upper Bound',font=TEXT_FONT, bg=FRAME_BG_COLOR, justify='right')
                self.zub_entry = ttk.Entry(self.eqframe, width=self.entry_width)
                self.zub_lbl.grid(row=row_counter, column=0, sticky='nse', pady=5)
                self.zub_entry.grid(row=row_counter,  column=1, sticky='nsw', pady=5)
                row_counter+=1

        for j in range(0, len(self.ext_obj)):
            self.ext_obj[j].grid(row=row_counter, column=0, columnspan=2, sticky='nsew', pady=5)
            row_counter+=1
                
    #Gather inputs, error check, try to create equation and return to parent frame
    def create_equation(self): 
        coeffs = []
        for entry in self.coeff_entries:
            v = check_entry(entry.get(), [float])
            if v == 'Error':
                tk.messagebox.showerror('Error', 'Please input a number for the coefficient.')
                return
            coeffs.append(v)
        
        #lower bound, upper bound, z lower, z upper, middle bound
        bounds = [check_entry(self.lb_entry.get(), [float]), check_entry(self.ub_entry.get(), [float]), None, None, None]
        if (self.eq_type == 'Multi-Linear') or (self.eq_type == 'Multi-Power'):
            bounds[2] = check_entry(self.zlb_entry.get(), [float])
            bounds[3] = check_entry(self.zub_entry.get(), [float])

        elif self.eq_type == 'Piecewise':
            bounds[4] = check_entry(self.mb_entry.get(), [float])
            if (bounds[4] is None) or (bounds[4] == 'Error'):
                tk.messagebox.showerror('Error', 'Piecewise equations require a lower middle and upper bound.')
                return False

        if 'Error' in bounds:
            bounds = [None, None, None, None, None]
            out_text = 'The equation has been created WITHOUT the optional upper or lower bounds.'
        else:
            out_text = 'The equation has been created successfully.'
            
        try:
            if self.eq_type == 'Piecewise':
                eq1 = self.ext_obj[0].get_equation()
                eq2 = self.ext_obj[1].get_equation()
                if None in [eq1, eq2]:
                    tk.messagebox.showinfo('Submitted', 'Please input two equations to create a piecewise equation.')
                    return False
                range_list = [bounds[0], bounds[4], bounds[1]]
                out_eq = mc.Piecewise(self.eq_name, [eq1, eq2], self.xlabel, self.ylabel, range_list, dynamic_type=self.dynamic_type)
            else:    
                out_eq = mc.Equation(self.eq_name, self.eq_type, coeffs, self.xlabel, self.ylabel, lower_bound=bounds[0], upper_bound=bounds[1], z_label=self.zlabel, z_lower_bound=bounds[2], z_upper_bound=bounds[3])
            tk.messagebox.showinfo('Submitted', out_text)
        except:
            tk.messagebox.showerror('Error', 'Unable to create equation. Make sure inputs are correct.')
            return False
        
        self.parent.update_equation(out_eq) 
        self.destroy()
    
    #Inputs default values into the entries if an original equation is provided
    def default_entries(self):
        if self.orig_equation is not None:
            if self.orig_equation.form in ['Constant','Linear', 'Power', 'Polynomial-2', 'Polynomial-3', 'Binomial']:
                for i in range(0, len(self.orig_equation.coeffs)):
                    self.coeff_entries[i].insert(0, str(self.orig_equation.coeffs[i]))
                if self.orig_equation.ub is not None:
                    self.ub_entry.insert(0, str(self.orig_equation.ub))
                if self.orig_equation.lb is not None:
                    self.lb_entry.insert(0, str(self.orig_equation.lb))
            elif self.orig_equation.form == 'Piecewise':
                self.ext_obj[0].update_equation(self.orig_equation.eq_list[0])
                self.ext_obj[1].update_equation(self.orig_equation.eq_list[1])
                if len(self.orig_equation.range_list) == 3:
                    self.lb_entry.insert(0, str(self.orig_equation.range_list[0]))
                    self.mb_entry.insert(0, str(self.orig_equation.range_list[1]))
                    self.ub_entry.insert(0, str(self.orig_equation.range_list[2]))
                    
# MONTH CHECK FRAME - Frame to let user select which months the modules should be on
class MonthCheckFrame(tk.Frame):
    def __init__(self, parent, controller, all_on=False, bg_color=FRAME_BG_COLOR):
        tk.Frame.__init__(self, parent, bg=bg_color) 
        self.page_name = 'Month Check'
        self.controller = controller
        self.columnconfigure((0,1,2,3,4,5),weight=1)
        self.check_width = 3
        self.month_vars = [tk.IntVar() for x in range(0, 12)]
        
        self.jan_box = tk.Checkbutton(self,text='Jan', variable=self.month_vars[0], onvalue=1, offvalue=0, width=self.check_width, anchor='w', padx=3)
        self.feb_box = tk.Checkbutton(self,text='Feb', variable=self.month_vars[1], onvalue=1, offvalue=0, width=self.check_width, anchor='w', padx=3)
        self.mar_box = tk.Checkbutton(self,text='Mar', variable=self.month_vars[2], onvalue=1, offvalue=0, width=self.check_width, anchor='w', padx=3)
        self.apr_box = tk.Checkbutton(self,text='Apr', variable=self.month_vars[3], onvalue=1, offvalue=0, width=self.check_width, anchor='w', padx=3)
        self.may_box = tk.Checkbutton(self,text='May', variable=self.month_vars[4], onvalue=1, offvalue=0, width=self.check_width, anchor='w', padx=3)
        self.jun_box = tk.Checkbutton(self,text='Jun', variable=self.month_vars[5], onvalue=1, offvalue=0, width=self.check_width, anchor='w', padx=3)
        self.jul_box = tk.Checkbutton(self,text='Jul', variable=self.month_vars[6], onvalue=1, offvalue=0, width=self.check_width, anchor='w', padx=3)
        self.aug_box = tk.Checkbutton(self,text='Aug', variable=self.month_vars[7], onvalue=1, offvalue=0, width=self.check_width, anchor='w', padx=3)
        self.sep_box = tk.Checkbutton(self,text='Sep', variable=self.month_vars[8], onvalue=1, offvalue=0, width=self.check_width, anchor='w', padx=3)
        self.oct_box = tk.Checkbutton(self,text='Oct', variable=self.month_vars[9], onvalue=1, offvalue=0, width=self.check_width, anchor='w', padx=3)
        self.nov_box = tk.Checkbutton(self,text='Nov', variable=self.month_vars[10], onvalue=1, offvalue=0, width=self.check_width, anchor='w', padx=3)
        self.dec_box = tk.Checkbutton(self,text='Dec', variable=self.month_vars[11], onvalue=1, offvalue=0, width=self.check_width, anchor='w', padx=3)
        
        self.jan_box.grid(row=0, column=0, sticky='nsew')
        self.feb_box.grid(row=0, column=1, sticky='nsew')
        self.mar_box.grid(row=0, column=2, sticky='nsew')
        self.apr_box.grid(row=0, column=3, sticky='nsew')
        self.may_box.grid(row=0, column=4, sticky='nsew')
        self.jun_box.grid(row=0, column=5, sticky='nsew')
        self.jul_box.grid(row=1, column=0, sticky='nsew')
        self.aug_box.grid(row=1, column=1, sticky='nsew')
        self.sep_box.grid(row=1, column=2, sticky='nsew')
        self.oct_box.grid(row=1, column=3, sticky='nsew')
        self.nov_box.grid(row=1, column=4, sticky='nsew')
        self.dec_box.grid(row=1, column=5, sticky='nsew')
        
        if all_on:
            for i in self.month_vars:
                i.set(1)

    #Returns a list of integers that reflects the index of the on months
    def get_month_list(self):
        output = []
        for i in range(0,12):
            if self.month_vars[i].get() == 1:
                output.append(i+1)
        return output
    
    #Set the on months basd on a list of integers
    def set_values(self, months):
        for i in range(0, 12):
            if (i+1) in months:
                self.month_vars[i].set(1)
            else:
                self.month_vars[i].set(0)

#%%### FACILITY DISPLAY FRAME -lets user view a facility conceptual schematic top-view
class FacilityFrame(tk.Frame):
    def __init__(self,parent, controller, fac):
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.parent = parent
        self.controller = controller
        self.columnconfigure((0,1,2,3), weight=1)
        self.page_name = 'FacilityFrame'
        self.fac = fac
        
        self.fig, self.ax = self.fac.plot_facility(hide=True)
        self.canvas_fig = FigureCanvasTkAgg(self.fig, master=self)
        self.right_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.view_btn = tk.Button(self.right_frame, text='View Specifications',font=TEXT_FONT, command=lambda:self.view_data())
        
        self.canvas_fig.get_tk_widget().pack(side='left')
        self.right_frame.pack(side='right')
        self.view_btn.pack(fill='x', padx=5, pady=5)
        
    #View facility characteristics in a table
    def view_data(self):
        Tableviewer(self, self.controller, self.fac.get_df())

        
#%%### SIMULATION RESULTS FRAME - lets user view the results of simulation
class SimResultsFrame(tk.Frame):
    def __init__(self, parent, controller, sim_results):
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.controller = controller
        self.columnconfigure((0,1,2,3), weight=1)
        self.page_name = 'ResultsFrame'        
        self.res = sim_results
        self.btn_width = 20
        
        self.default_save_bools = [True, False, False, False, False, False]

        self.sim_desc_title = tk.Label(self, text='Economic Summary', font=TEXT_BOLD_FONT, justify='center', bg=FRAME_BG_COLOR)
        self.sim_desc_lbl = tk.Label(self, text=self.res.get_sim_desc(), font=TEXT_FONT, justify='left', bg=FRAME_BG_COLOR)
        self.view_opts = ['Holistic Performance Ratios', 'Flow Allocations', 'Head and Tailwater Elevations', 'Plant Economics', 'Generation Timeseries', 'Species Performance', 'Module Availability Factors', 'Module Cost Breakdown', 'Plant Efficiency']
        self.view_var = tk.StringVar()
        self.fig, self.ax = self.res.get_holistic_perf_plot(hide=True)
        self.canvas_frame=tk.Frame(self, bg=FRAME_BG_COLOR)
        self.canvas_fig = FigureCanvasTkAgg(self.fig, self.canvas_frame)        
        self.view_lbl = tk.Label(self, text='Select a results view:', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.view_menu = tk.OptionMenu(self, self.view_var, *self.view_opts)
        self.view_var.trace('w', self.change_view)
        self.view_var.set(self.view_opts[0])
        
        self.runsFrame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.runsFrame.columnconfigure((0,1), weight=1)
        self.runs_lbl = tk.Label(self.runsFrame, text='Manage Runs', font=TEXT_FONT,bg=FRAME_BG_COLOR)
        self.save_btn = tk.Button(self.runsFrame, text='Save Run', font=TEXT_FONT, command=lambda:self.save_sim_run())
        self.view_runs_btn = tk.Button(self.runsFrame, text='View Runs', font=TEXT_FONT, command=lambda:self.view_runs())
        self.export_runs_btn = tk.Button(self.runsFrame, text='Export Runs', font=TEXT_FONT, command=lambda:self.export_runs())
        self.clear_runs_btn = tk.Button(self.runsFrame, text='Clear Runs', font=TEXT_FONT, command=lambda:self.clear_runs())
        self.runs_lbl.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')
        self.save_btn.grid(row=1, column=0,padx=5, pady=5, sticky='nsew')
        self.view_runs_btn.grid(row=1, column=1,padx=5, pady=5, sticky='nsew')
        self.export_runs_btn.grid(row=2, column=0,padx=5, pady=5, sticky='nsew')
        self.clear_runs_btn.grid(row=2, column=1,padx=5, pady=5, sticky='nsew')
        
        self.pop_btn = tk.Button(self, text='Pop-out', font=TEXT_FONT, command=lambda:self.pop_figure())
        self.table_btn = tk.Button(self, text='View Table', font=TEXT_FONT, command=lambda:self.view_table())
        self.anim_btn = tk.Button(self, text='Show Animation', font=TEXT_FONT, command=lambda:self.show_animation())
        
        self.sim_desc_title.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='sew')
        self.sim_desc_lbl.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='sew')
        self.anim_btn.grid(row=0, rowspan=1, column=2, columnspan=2, padx=5, pady=5, sticky='sew')
        self.runsFrame.grid(row=1, rowspan=1, column=2, columnspan=2, padx=5, pady=5)
        self.view_lbl.grid(row=2, column=0, columnspan=1, padx=5, pady=5, sticky='e')
        self.view_menu.grid(row=2, column=1, columnspan=1, pady=5, sticky='w')
        self.table_btn.grid(row=2, column=2, padx=5, pady=5, sticky='ew')
        self.pop_btn.grid(row=2, column=3, padx=5, pady=5, sticky='ew')
        self.canvas_frame.grid(row=3, column=0, columnspan=4, sticky='nsew')

        self.canvas_fig.get_tk_widget().pack(fill='x')
    
    #Saves the current simulation by opening a window that tells which data to save
    def save_sim_run(self):
        SaveRunWindow(self, self.controller, self.res)
        
    #Creates a tableviewer to show simulation runs
    def view_runs(self):
        if len(self.controller.saved_sim_results) <= 0:
            tk.messagebox.showerror('Error', 'There are no saved runs. Please use the save run button to save the current run.')
            return
        else:
            Tableviewer(self,self.controller, self.controller.saved_sim_results)
    
    #Export the table of runs via a tableviewer
    def export_runs(self):
        if len(self.controller.saved_sim_results) <= 0:
            tk.messagebox.showerror('Error', 'There are no saved runs. Please use the save run button to save the current run.')
            return
        else:
            csvExportWindow(self,self.controller, self.controller.saved_sim_results)

    #Delete all runs from the save table
    def clear_runs(self):
        self.controller.clear_runs()
        tk.messagebox.showinfo('Success', 'The saved runs have been cleared.')
    
    #Opens the Animation Window to show the timeseries data
    def show_animation(self):
        AnimationWindow(self, self.controller, self.res)
    
    #Creates a separate window for the figures
    def pop_figure(self): 
        opt = self.view_var.get()
        if opt == 'Holistic Performance Ratios':
            pass
        elif opt == 'Flow Allocations':
            self.res.plot_flow_allos(hide=False)
        elif opt == 'Plant Economics':
            self.res.get_economic_plot(hide=False)
        elif opt == 'Species Performance':
            self.res.get_fish_plot(hide=False)
        elif opt =='Generation Timeseries':
            self.res.get_generation_series_plot(hide=False)
        elif opt == 'Module Availability Factors':
            self.res.get_capacity_factors_plot(hide=False)
        elif opt == 'Module Cost Breakdown':
            self.res.get_icc_breakdown_plot(hide=False)
        elif opt == 'Plant Efficiency':
            self.res.plant_efficiency_plot(hide=False)
        elif opt == 'Head and Tailwater Elevations':
            self.res.get_elevation_plot(hide=False)
            
    #Creates a tableviewer for the data related to the selected figure
    def view_table(self): 
        opt = self.view_var.get()
        if opt == 'Holistic Performance Ratios':
            Tableviewer(self, self.controller, self.res.get_holistic_df(), show_index=True)
        elif opt == 'Flow Allocations':
            Tableviewer(self, self.controller, self.res.get_allocations_df(), show_index=True)
        elif opt == 'Plant Economics':
            Tableviewer(self, self.controller, self.res.get_economic_df(), show_index=False)
        elif opt == 'Species Performance':
            Tableviewer(self, self.controller, self.res.get_species_df(), show_index=True)
        elif opt =='Generation Timeseries':
            Tableviewer(self, self.controller, self.res.get_generation_timeseries_df(), show_index=True)
        elif opt == 'Module Availability Factors':
            Tableviewer(self, self.controller, self.res.get_availability_df(), show_index=False)
        elif opt == 'Module Cost Breakdown':
            Tableviewer(self, self.controller, self.res.get_module_cost_df(), show_index=True)
        elif opt == 'Plant Efficiency':
            Tableviewer(self, self.controller, self.res.get_generation_timeseries_df(), show_index=True)
        elif opt == 'Head and Tailwater Elevations':
            Tableviewer(self, self.controller, self.res.get_elevation_df(), show_index=True)

    #Changes the figure based on the selection menu
    def change_view(self, name, indx, op):
        opt = self.view_var.get()
        self.ax.set_aspect('auto')
        self.ax.get_xaxis().set_visible(True)
        self.ax.get_yaxis().set_visible(True)
        self.ax.set_axis_on()
        self.ax.set_frame_on(True)
        if opt == 'Holistic Performance Ratios':
            self.fig, self.ax = self.res.get_holistic_perf_plot(fig=self.fig, ax=self.ax, hide=True)
        elif opt == 'Flow Allocations':
            self.fig, self.ax = self.res.plot_flow_allos(fig=self.fig, ax=self.ax, hide=True)
        elif opt == 'Plant Economics':
            self.fig, self.ax = self.res.get_economic_plot(fig=self.fig, ax=self.ax, hide=True)
        elif opt == 'Species Performance':
            self.fig, self.ax = self.res.get_fish_plot(fig=self.fig, ax=self.ax, hide=True)
        elif opt == 'Generation Timeseries':
            self.fig, self.ax = self.res.get_generation_series_plot(fig=self.fig, ax=self.ax, hide=True)
        elif opt == 'Module Availability Factors':
            self.fig, self.ax = self.res.get_capacity_factors_plot(fig=self.fig, ax=self.ax, hide=True)
        elif opt == 'Module Cost Breakdown':
            self.fig, self.ax = self.res.get_icc_breakdown_plot(fig=self.fig, ax=self.ax, hide=True)
        elif opt == 'Plant Efficiency':
            self.fig, self.ax = self.res.plant_efficiency_plot(fig=self.fig, ax=self.ax, hide=True)
        elif opt == 'Head and Tailwater Elevations':
            self.fig, self.ax = self.res.get_elevation_plot(fig=self.fig, ax=self.ax, hide=True)

        self.canvas_fig.draw()

#%%## Save run window - creates a toplevel that lets the user select which information from the simulation to save
class SaveRunWindow(tk.Toplevel):
    def __init__(self, parent, controller, sim_results):
        tk.Toplevel.__init__(self, bg=FRAME_BG_COLOR)
        self.parent = parent
        self.controller = controller
        self.sim_res = sim_results
        self.wrap_length = 400
        self.entry_width = 10
        
        self.title = tk.Label(self, text='Save Run Results', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.directions_lbl = tk.Label(self, text='Please provide a name for the run and select the results you would like to save.', font=TEXT_FONT, bg=DIRECTIONS_BG_COLOR, wraplength=self.wrap_length, justify='left')
        self.name_lbl = tk.Label(self, text='Run Name', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.name_entry = ttk.Entry(self, width=self.entry_width)
        self.res_lbl = tk.Label(self, text='Data Options', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.bools_frame = SaveRunFrame(self, self.controller, self.parent.default_save_bools)
        
        self.title.grid(row=0, column=0, columnspan=4, padx=5, pady=5, sticky='nsew')
        self.directions_lbl.grid(row=1, column=0, columnspan=4, padx=5, pady=0, sticky='nsew')
        self.name_lbl.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')
        self.name_entry.grid(row=2, column=2, columnspan=2, padx=5, pady=5, sticky='nsew')
        self.res_lbl.grid(row=3, column=0, columnspan=4, padx=5, pady=5, sticky='nsew')
        self.bools_frame.grid(row=4, column=0, columnspan=4, padx=20, pady=5, sticky='nsew')

        self.save_btn = tk.Button(self, text='Save', font=TEXT_FONT, command=lambda:self.save_run_press())
        self.save_btn.grid(row=5, column=0, columnspan=5, padx=5, pady=5, sticky='nsew')
        self.insert_default_name()        

    #Insert a default name into the entry
    def insert_default_name(self):
        if len(self.controller.saved_sim_results) == 0:
            self.name_entry.insert(0, 'Run 1')
        else:
            self.name_entry.insert(0, 'Run ' + str(len(self.controller.saved_sim_results.columns)))
        
    #Save the selected data to the simulation table in the parent frame
    def save_run_press(self):
        bools = self.bools_frame.get_bools()
        if True not in bools:
            tk.messagebox.showerror('Error', 'Please select at least one data option.')
            return
        
        run_name = check_entry(self.name_entry.get(), [str])
        if (len(run_name) <= 0) or run_name == 'Error':
            tk.messagebox.showerror('Error', 'Please enter a proper name')
            return
        
        res_dict = self.sim_res.get_run_dict(*bools)
        self.controller.save_run(res_dict,run_name)
        self.parent.default_save_bools = bools
        tk.messagebox.showinfo('Success', 'Run saved successfully. Please select the view runs button to view the data.')
        self.cleanup()
        
    #Destroys the window
    def cleanup(self):
        self.destroy()

#Used within the save run window to select which data to save from a given run
class SaveRunFrame(tk.Frame):
    def __init__(self, parent, controller, default_bools=None):
        tk.Frame.__init__(self, parent, bg=FRAME_BG_COLOR)
        self.parent = parent
        self.controller = controller
        self.default_bools = default_bools
        self.res_opts = ['Objectives', 'Facility Overview', 'Module Overview', 'Initial Costs', 'Annual Benefits', 'Annual Expenses']
        self.res_bools = {}
        self.checkboxes = {}
        self.columnconfigure((0,1), weight=1)
        
        self.subtitle_lbl = tk.Label(self, text='Select Data to Save', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.subtitle_lbl.grid(row=0, column=0, columnspan=2, sticky='nsew')
        counter = 0
        for key in self.res_opts:
            self.res_bools[key] = tk.BooleanVar()
            self.checkboxes[key] = tk.Checkbutton(self, text=key, onvalue=True, offvalue=False, variable=self.res_bools[key])
            self.checkboxes[key].grid(row=int(counter/2)+1, column=counter%2, columnspan=1, padx=5, pady=5, sticky='nsew')
            counter+=1
            
        self.set_default_bools()
            
    #Sets defaults for the data type selection
    def set_default_bools(self):
        if self.default_bools is None:
            self.default_bools = [False for i in self.res_opts]
        counter = 0
        for key in self.checkboxes.keys():
            if self.default_bools[counter]:
                self.checkboxes[key].select()
            else:
                self.checkboxes[key].deselect()
            counter+=1
            
    #Get the boolean values for each possible data type
    def get_bools(self):
        return [self.res_bools[key].get() for key in self.res_bools.keys()]

#%%##Animation Window - creates a toplevel window where users can view the operation of the facility in the simulation
class AnimationWindow(tk.Toplevel):
    def __init__(self, parent, controller, sim_results):
        tk.Toplevel.__init__(self, bg=FRAME_BG_COLOR)
        self.parent = parent
        self.controller = controller
        self.sim_res = sim_results
        self.time_step = 0
        self.isStopped = True
        self.play_text_var = tk.StringVar()
        self.scale_var = tk.IntVar()
        self.desc_var = tk.StringVar()
        
        self.play_text_var.set('Play')
        
        self.profile_fig, self.profile_ax = self.sim_res.plot_dam_profile(0)
        self.allo_fig, self.allo_ax = self.sim_res.plot_flow_allo_bar(0)
        self.flow_series_fig, self.flow_series_ax = self.sim_res.get_daily_flow_point_plot(0)
        self.legend_fig, self.legend_ax = self.sim_res.get_module_legend_plot(self.allo_ax)
        
        self.title_lbl = tk.Label(self, text='View Simulation by Timestep', font=SUBTITLE_FONT,bg=TITLE_BG_COLOR)
       
        self.desc_frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.desc_head_lbl = tk.Label(self.desc_frame, text='Statistics', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.desc_lbl = tk.Label(self.desc_frame, textvariable=self.desc_var, font=TEXT_FONT, bg=FRAME_BG_COLOR, justify='left')

        self.profile_canvas = FigureCanvasTkAgg(self.profile_fig, self)
        self.allo_canvas = FigureCanvasTkAgg(self.allo_fig, self)
        self.flow_series_canvas = FigureCanvasTkAgg(self.flow_series_fig, self)
        self.legend_canvas = FigureCanvasTkAgg(self.legend_fig, self)
        
        self.scale_lbl = tk.Label(self, text='Select a timestep using the slider or press Play', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.time_scale = tk.Scale(self, from_=1, to=len(self.sim_res.inflows), tickinterval=round(len(self.sim_res.inflows)/30), orient='horizontal', variable=self.scale_var)
        self.scale_var.trace('w', self.on_scale_switch)
        
        self.time_lbl = tk.Label(self, text='Sleep (msec):', font=TEXT_FONT, bg=FRAME_BG_COLOR, justify='right')
        self.time_entry = ttk.Entry(self, width=10)
        self.time_entry.insert(0, '100')
        self.play_btn = tk.Button(self, textvariable=self.play_text_var, font=TEXT_FONT, command=lambda:self.on_play_btn())
        
        self.title_lbl.grid(row=0, column=0, columnspan=5, padx=5, pady=5, sticky='nsew')
        self.desc_frame.grid(row=1, rowspan=1, column=0, columnspan=2, padx=5, pady=0, sticky='nsew')
        self.legend_canvas.get_tk_widget().grid(row=2, rowspan=1, column=0, columnspan=2, padx=0, pady=0)
        self.flow_series_canvas.get_tk_widget().grid(row=1,rowspan=1, column=2,columnspan=1, padx=5, pady=5)
        self.profile_canvas.get_tk_widget().grid(row=2, column=2,columnspan=1, padx=5, pady=5)
        self.allo_canvas.get_tk_widget().grid(row=1,rowspan=2, column=3,columnspan=1, padx=5, pady=5)
        self.scale_lbl.grid(row=3, column=0, columnspan=4, padx=5, pady=5, sticky='nsew')
        self.time_scale.grid(row=4, column=0, columnspan=4, padx=5, pady=0, sticky='nsew')
        self.time_lbl.grid(row=5, column=0, columnspan=1, padx=5, pady=5, sticky='nse')
        self.time_entry.grid(row=5, column=1, columnspan=1, padx=5, pady=5, sticky='nsw')
        self.play_btn.grid(row=5, column=2, columnspan=2, padx=5, pady=5, sticky='nsew')
        
        self.desc_head_lbl.pack(fill='x')
        self.desc_lbl.pack(fill='x')
        self.legend_canvas.draw()  
        self.scale_var.set(1)
        
    #When the timestep changes update the figures
    def on_scale_switch(self, name, idx, op):
        self.update_figs(self.scale_var.get())
        
    #Redraw the figures for the given timestep
    def update_figs(self, time_step):
        time_step -= 1 #Accounts for base zero on scale
        self.allo_fig, self.allo_ax = self.sim_res.plot_flow_allo_bar(time_step, self.allo_fig, self.allo_ax)
        self.profile_fig, self.profile_ax = self.sim_res.plot_dam_profile(time_step, self.profile_fig, self.profile_ax)
        self.flow_series_fig, self.flow_series_ax = self.sim_res.get_daily_flow_point_plot(time_step, self.flow_series_fig, self.flow_series_ax)
        self.profile_canvas.draw()
        self.allo_canvas.draw()
        self.flow_series_canvas.draw()
        self.desc_var.set(self.sim_res.get_day_desc(time_step))
        
    #When the play button is pressed, increment the timestep in small intervals based on the user defined sleep time
    def on_play_btn(self):
        if self.isStopped == True:
            self.sleep_time = check_entry(self.time_entry.get(), [int])
            if self.sleep_time == 'Error':
                tk.messagebox.showerror('Error', 'Please input a number in seconds for the sleep time, which is the time between frames.')
                return
            self.play_text_var.set('Pause')
            self.isStopped = False
            self.time_step = self.scale_var.get()
            self.play_anim()
        else:
            self.isStopped = True
            self.play_text_var.set('Play')
           
    #Plays the animation based on the sleep time and current timestep
    def play_anim(self):
        if (self.time_step < len(self.sim_res.inflows)) & (self.isStopped is False):
            self.time_step += 1
            self.scale_var.set(self.time_step)
            self.after(self.sleep_time, self.play_anim)

        

#%%## ONE FRAME WINDOW - creates a toplevel window with one frame that is provided. This is a flexible way of creating a scrollable toplevel
class OneFrameWindow(tk.Toplevel):
    def __init__(self, parent, controller, scroll=False):
        tk.Toplevel.__init__(self, bg=FRAME_BG_COLOR)
        self.parent = parent
        self.controller = controller
        self.columnconfigure(0, weight=1)
        self.canvas_width = 800
        self.canvas_height = 600
        
        if scroll == False:
            self.frame_parent = self
        else: #Create the widgets needed for scrolling and set the parent accordingly
            self.canvas = tk.Canvas(self,width=self.canvas_width, height=self.canvas_height, bg=FRAME_BG_COLOR)
            self.mainframe = tk.Frame(self.canvas, bg=FRAME_BG_COLOR)
            self.scrollbar = tk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
            self.canvas.configure(yscrollcommand=self.scrollbar.set)
            
            self.scrollbar.pack(side='right', expand=False, fill='y')
            self.canvas.pack(side='left', expand=True, fill='both', padx=5) 
            self.canvas_window = self.canvas.create_window((4,4), anchor='nw', window=self.mainframe) 
            
            self.mainframe.bind("<Configure>", self.onFrameConfigure) #bind an event whenever the size of the viewPort frame changes.
            self.canvas.bind("<Configure>", self.onCanvasConfigure)
            
            self.onFrameConfigure(None)
            self.frame_parent = self.mainframe
    
    #When the canvas changes sizes
    def onCanvasConfigure(self, event):
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width = canvas_width)
    
    #When the frame changes sizes, update the scrollregion
    def onFrameConfigure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    #Adds the frame to the toplevel
    def addFrame(self, myframe):
        self.myframe = myframe
        self.myframe.pack(fill='both', expand=True)

    #Destroys the toplevel
    def cleanup(self):
        self.destroy()
    
#%%## Tableviewer - Displays a dataFrame in a TopLevel
class Tableviewer(tk.Toplevel):
    def __init__(self, parent, controller, data, show_header=True, show_index=False):
        tk.Toplevel.__init__(self)
        self.parent = parent
        self.controller = controller
        self.grid_columnconfigure(0, weight = 1)
        self.grid_rowconfigure(0, weight = 1)
        self.data = data

        self.fileMenu = tk.Menu(self, tearoff=False)
        self.fileMenu.add_command(label="Export", underline=1, command=self.onExport)
        self.config(menu=self.fileMenu)

        self.frame = tk.Frame(self)
        self.frame.grid_columnconfigure(0, weight = 1)
        self.frame.grid_rowconfigure(0, weight = 1)
        
        if show_header == True:
            if show_index == True:
                headers = data.reset_index().columns.tolist()
            else:
                headers = data.columns.tolist()
        else:
            headers = None
            
        if show_index == True:
            out_data = data.reset_index().values.tolist()
        else:
            out_data = data.values.tolist()
            
        self.sheet = tksheet.Sheet(self.frame,data = out_data, headers=headers, theme='light blue')
        self.sheet.set_all_cell_sizes_to_text(redraw = True)
        self.sheet.enable_bindings()
        self.frame.grid(row = 0, column = 0, sticky = "nswe")
        self.sheet.grid(row = 0, column = 0, sticky = "nswe")
        
    #Exports the data to a csv using the csvExportwindow
    def onExport(self):
        csvExportWindow(self, self.controller, self.data)

#%%### CSV UPLOAD FRAME - Lets user upload flow data from csv or xlsx using a provided file name.
class csvUploadWindow(tk.Toplevel):
    def __init__(self, parent, controller, defaults=None, just_file_name=False):
        tk.Toplevel.__init__(self)
        self.parent = parent
        self.controller = controller
        self.page_name = 'CsvUploadWindow'
        self.myframe = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.just_file_name = just_file_name
        self.button_width = 15
        self.entry_width = 20
        self.columnconfigure((0,1), weight=1)
        
        self.data_types = ['csv', 'xlsx']
        
        self.type_lbl = tk.Label(self.myframe, text='Select a file type', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.type_var = tk.StringVar()
        self.type_menu = tk.OptionMenu(self.myframe, self.type_var, *self.data_types)
        self.file_lbl = tk.Label(self.myframe, text='File Name\n(e.g. Data/File_Name)', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.file_entry = ttk.Entry(self.myframe, width=self.entry_width)        
        self.sheet_lbl = tk.Label(self.myframe, text='Sheet Name', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.sheet_entry = ttk.Entry(self.myframe, width=self.entry_width)        
        self.upload_btn = tk.Button(self.myframe, text='Upload', font=TEXT_FONT, command=lambda:self.upload())
        
        
        if defaults is not None:
            clear_entries([self.file_entry, self.sheet_entry])
            self.file_entry.insert(0, defaults[1])
            if defaults[0] == 'csv':
                self.type_var.set(self.data_types[0])
            else:
                self.type_var.set(self.data_types[1])
                self.sheet_entry.insert(0, defaults[2])
        else:
            self.type_var.set(self.data_types[0])
        self.type_var.trace('w', self.pack_attributes)
        self.myframe.pack(fill='both')
        self.pack_attributes()
        
    #Places widgets
    def pack_attributes(self, name=0, indx=0, op=0):
        self.myframe.grid_forget()
        if self.just_file_name == True:
            self.file_lbl.grid(row=0, column=0,padx=5, pady=5, sticky='nsew')
            self.file_entry.grid(row=0, column=1, padx=5, pady=5)
            self.upload_btn.grid(row=1, column=0,columnspan=2,padx=5, pady=5)
        elif self.type_var.get() == 'csv':
            self.sheet_entry.grid_forget()
            self.sheet_lbl.grid_forget()
            self.type_lbl.grid(row=0, column=0,padx=5, pady=5, sticky='nsew')
            self.type_menu.grid(row=0, column=1,padx=5, pady=5, sticky='nsew')
            self.file_lbl.grid(row=1, column=0,padx=5, pady=5, sticky='nsew')
            self.file_entry.grid(row=1, column=1, padx=5, pady=5)
            self.upload_btn.grid(row=2, column=0,columnspan=2,padx=5, pady=5)
        else:
            self.type_lbl.grid(row=0, column=0,padx=5, pady=5, sticky='nsew')
            self.type_menu.grid(row=0, column=1,padx=5, pady=5, sticky='nsew')
            self.file_lbl.grid(row=1, column=0,padx=5, pady=5, sticky='nsew')
            self.file_entry.grid(row=1, column=1, padx=5, pady=5)
            self.sheet_lbl.grid(row=2, column=0,padx=5, pady=5, sticky='nsew')
            self.sheet_entry.grid(row=2, column=1, padx=5, pady=5)
            self.upload_btn.grid(row=3, column=0,columnspan=2,padx=5, pady=5)
        
    #Gather file name, error check, try to upload file as df
    def upload(self):
        file_name = check_entry(self.file_entry.get(), [str])
        if (file_name == '') or (file_name == 'Error'):
            tk.messagebox.showerror('Error', 'Please input a proper file name.')
            return
        
        if self.just_file_name == True:
            self.parent.data_uploaded(file_name)
            self.destroy()
            return
            
        if self.type_var.get() == 'xlsx':
            file_name = file_name + '.xlsx'
            sheet_name = check_entry(self.sheet_entry.get(), [str])
            if (file_name == 'Error'):
                tk.messagebox.showerror('Error', 'Please input a proper sheet name.')
                return
            try:
                temp_data = pd.read_excel(file_name, sheet_name=sheet_name)
                result = self.parent.data_uploaded(temp_data)
            except:
                tk.messagebox.showerror("Error", "Unable to read excel file. Please make sure it is formatted properly and that the file name is correct.")
                return
        else:
            file_name = file_name + '.csv'
            try:
                temp_data = pd.read_csv(file_name, parse_dates=True, infer_datetime_format=True)
                result = self.parent.data_uploaded(temp_data)
            except:
                tk.messagebox.showerror("Error", "Unable to read csv file. Please make sure it is formatted properly and that the file name is correct.")
                return
        if result == 'Unsuccessful':
            tk.messagebox.showerror('Error', 'Unable to find the correct data headers or data types, please make sure data is formatted properly.')
        else:
            tk.messagebox.showinfo('Success', 'Successfully uploaded data.')
            self.destroy()
        
# CSV EXPORT WINDOW -Creates a TopLevel to export a dataframe as a csv
class csvExportWindow(tk.Toplevel):
    def __init__(self, parent, controller, df):
        tk.Toplevel.__init__(self)
        self.parent = parent
        self.controller = controller
        self.df = df
        self.wrap_length=550
        
        self.frame = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.frame.pack()
        
        self.title_lbl = tk.Label(self.frame, text='Export Data', font=SUBTITLE_FONT, bg=SUBTITLE_BG_COLOR)
        self.directions_lbl = tk.Label(self.frame, text='Use the inputs below to save the selected data. When inputting a file name, please do not put file extensions. You can specify the subfolder location by using "Folder Name/File name" but the subfolder must already exist. If the csv file or excel sheet already exists, then it will be overwritten.', wraplength=self.wrap_length, bg=DIRECTIONS_BG_COLOR, font=TEXT_FONT, justify='left')
        self.name_lbl = tk.Label(self.frame, text='File Name', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.name_entry = ttk.Entry(self.frame, width=20)
        self.export_csv_btn = tk.Button(self.frame, text='Export to csv', font=TEXT_FONT, command=lambda:self.export_csv())
        self.or_lbl = tk.Label(self.frame, text='Or add a sheet name to Export as an Excel Workbook file (.xlsx)', font=TEXT_FONT, bg=SUBTITLE_BG_COLOR, wraplength=self.wrap_length)
        self.sheet_lbl = tk.Label(self.frame, text='Sheet Name', font=TEXT_FONT, bg=FRAME_BG_COLOR)
        self.sheet_entry = ttk.Entry(self.frame, width=20)
        self.export_xlsx_btn = tk.Button(self.frame, text='Export to Excel', font=TEXT_FONT, command=lambda:self.export_xlsx())
        
        self.title_lbl.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')
        self.directions_lbl.grid(row=1, column=0, columnspan=2, padx=5, pady=0, sticky='nsew')
        self.name_lbl.grid(row=2, column=0, padx=5, pady=5, sticky='nsew')
        self.name_entry.grid(row=2, column=1, padx=5, pady=5, sticky='nsew')
        self.export_csv_btn.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')
        self.or_lbl.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')
        self.sheet_lbl.grid(row=5, column=0, columnspan=1, padx=5, pady=5, sticky='nsew')
        self.sheet_entry.grid(row=5, column=1, columnspan=1, padx=5, pady=5, sticky='nsew')
        self.export_xlsx_btn.grid(row=6, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')

    #Checks if the file already exists to determine if the file should be overrriden
    def check_file_exists(self, file_name):
        exists = os.path.exists(file_name) 
        if exists:
            answer = tk.messagebox.askyesno(title='Overwrite File', message='This file name already exists. Would you like to overwrite the file? All data from the current file will be lost.')
            return answer
        else: #if file doesn't exist, then it is ok to write file
            return True
        
    #Gather the file name, error check, and export the file as an xlsx file
    def export_xlsx(self):
        file_name = check_entry(self.name_entry.get(),[str])
        if (file_name == 'Error') or (len(file_name) <=0):
            tk.messagebox.showerror('Error', 'Please input a proper file name.')
            return
        sheet_name = check_entry(self.sheet_entry.get(),[str])
        if (sheet_name == 'Error') or (len(sheet_name) <=0):
            tk.messagebox.showerror('Error', 'Please input a proper sheet name.')
            return
        file_name = file_name + '.xlsx'
        path = os.getcwd()+ '/' +file_name
        if self.check_file_exists(file_name):
            try:
                book = load_workbook(path)
                writer = pd.ExcelWriter(path, engine='openpyxl')
                writer.book = book
                self.df.to_excel(writer, index=True, sheet_name=sheet_name)
                writer.save()
                writer.close()
                tk.messagebox.showinfo('Success', 'Successfully wrote data to file.')
                self.cleanup()
            except:
                tk.messagebox.showerror('Error', 'Unable to save file. Please double check file names and data structure.')
    
    #Gather the file name, error check, and export the file as a csv file
    def export_csv(self):
        file_name = check_entry(self.name_entry.get(),[str])
        if (file_name == 'Error') or (len(file_name) <=0):
            tk.messagebox.showerror('Error', 'Please input a proper file name.')
            return
        file_name = file_name + '.csv'
        if self.check_file_exists(file_name):
            try:
                self.df.to_csv(file_name)
                tk.messagebox.showinfo('Success', 'Successfully wrote data to file.')
                self.cleanup()
            except:
                tk.messagebox.showerror('Error', 'Unable to save file. Please double check file names and data structure.')
        
    #Destroys the toplevel
    def cleanup(self):
        self.destroy()
       
#%%## DATA THREAD CLASS - Creates a data thread that can download USGS data
class dataThread(threading.Thread):
    def __init__(self, tqueue, rqueue):
        threading.Thread.__init__(self)
        self.results_queue = rqueue
        self.tasks_queue = tqueue
        self.setDaemon(True)
        self.show_dialogue = True
    #Starts a thread that can be run simulatenously to other tkinter processes
    def run(self):
        while not self.tasks_queue.empty():
            data_type, station, start, end = self.tasks_queue.get()
            if data_type == 'Daily':
                self.results_queue.put([af.get_daily_USGS_data(station,start,end, show_dialogue=self.show_dialogue), 'Daily'])
            elif data_type == 'Stage':
                self.results_queue.put([af.get_stage_USGS_data(station,start,end, show_dialogue=self.show_dialogue), 'Stage'])
            elif data_type == 'Peak':
                self.results_queue.put([af.get_peak_USGS_data(station, show_dialogue=self.show_dialogue), 'Peak'])

     
# AUTOMATED DATA RETRIEVAL FRAME - Creates a TopLevel for automatically getting USGS data
class autodataFrame(tk.Toplevel):
    def __init__(self, parent, controller, auto_type):
        tk.Toplevel.__init__(self)
        self.parent = parent
        self.controller = controller
        self.page_name = 'AutoData'
        self.button_width = 15
        self.entry_width = 20
        self.auto_type = auto_type
        self.wrap_length = 500
        
        self.myframe = tk.Frame(self, bg=FRAME_BG_COLOR)
        self.myframe.pack(fill='both')
        
        self.page_title = tk.Label(self.myframe, text ='USGS Data - Automated Retrieval', font =TEXT_FONT, bg=SUBTITLE_BG_COLOR)
        self.directions_txt = 'This page uses the USGS API to automatically retrieve flow and stage data.'
        self.link_text = 'Click here for link'
        self.directions_lbl = tk.Label(self.myframe, text=self.directions_txt, font=TEXT_FONT, bg=DIRECTIONS_BG_COLOR, wraplength=self.wrap_length, justify='left')
        self.link_lbl = tk.Label(self.myframe, text=self.link_text, font=LINK_FONT, bg=DIRECTIONS_BG_COLOR)
        self.station_left_lbl = tk.Label(self.myframe, text='USGS Station ID:', font= TEXT_FONT, bg=LABEL_BG_COLOR)
        self.station_entry = ttk.Entry(self.myframe, width = self.entry_width)
        self.station_right_lbl = tk.Label(self.myframe, text='(8-Digits)', font=TEXT_FONT, bg=LABEL_BG_COLOR)
        self.start_left_lbl = tk.Label(self.myframe, text='Start Date:', font=TEXT_FONT, bg=LABEL_BG_COLOR)
        self.start_date_entry = ttk.Entry(self.myframe, width = self.entry_width)
        self.start_right_lbl = tk.Label(self.myframe, text='(YYYY-MM-DD)', font=TEXT_FONT, bg=LABEL_BG_COLOR)
        self.end_left_lbl = tk.Label(self.myframe, text='End Date:', font=TEXT_FONT, bg=LABEL_BG_COLOR)
        self.end_date_entry = ttk.Entry(self.myframe, width = self.entry_width)
        self.end_right_lbl = tk.Label(self.myframe, text='(YYYY-MM-DD)', font=TEXT_FONT, bg=LABEL_BG_COLOR)
        self.submit_btn = tk.Button(self.myframe, text='Download', width=self.button_width, font=TEXT_FONT, command=lambda:self.get_auto_data())

        self.page_title.grid(row=0, column=0, columnspan=3, sticky='nsew', pady=5)
        self.directions_lbl.grid(row=1, column=0, columnspan=3, sticky='nsew', pady=5)
        self.link_lbl.grid(row=2, column=0, columnspan=3, sticky='nsew', pady=0)
        self.station_left_lbl.grid(row=3, column=0, padx=0, pady=5, sticky='e')
        self.station_entry.grid(row=3, column=1, padx=5, pady=5)
        self.station_right_lbl.grid(row=3, column=2,padx=0, pady=5)
        self.start_left_lbl.grid(row=4, column=0,padx=0, pady=5, sticky='e')
        self.start_date_entry.grid(row=4, column=1, padx=5, pady=5)
        self.start_right_lbl.grid(row=4, column=2,padx=0, pady=5)
        self.end_left_lbl.grid(row=5, column=0,padx=0, pady=5, sticky='e')
        self.end_date_entry.grid(row=5, column=1, padx=0, pady=5)
        self.end_right_lbl.grid(row=5, column=2,padx=0, pady=5)
        self.submit_btn.grid(row=6, column=0, columnspan=3, padx=0, pady=5)

        #There are three API functionalities: for daily flow data, stage-discharge data, and historical peak flow data
        if auto_type == 'Daily':
            self.link_lbl.bind("<Button-1>", lambda e: callback('https://waterdata.usgs.gov/nwis/dv/?referred_module=sw'))
        elif auto_type == 'Stage': 
            self.link_lbl.bind("<Button-1>", lambda e: callback('https://waterservices.usgs.gov/rest/IV-Test-Tool.html'))
        elif auto_type == 'Peak':
            self.link_lbl.bind("<Button-1>", lambda e: callback('https://nwis.waterdata.usgs.gov/usa/nwis/peak'))
        
        self.default_entries()
        
    #Inserts default values into the entries
    def default_entries(self):
        self.station_entry.insert(0, '01170000')
        self.start_date_entry.insert(0, '2000-01-01')
        self.end_date_entry.insert(0, '2020-01-01')
        
    #Creates a thread that works on gathering the requested data
    def get_auto_data(self):
        self.controller.busy('Fetching data...')
        station = self.station_entry.get()
        start = self.start_date_entry.get()
        end = self.end_date_entry.get()
        
        self.return_que = queue.Queue()
        self.work_que = queue.Queue()
        
        if self.auto_type == 'Daily':
            self.work_que.put(['Daily', station, start, end])
        elif  self.auto_type == 'Stage':
            self.work_que.put(['Stage', station, start, end])
        elif self.auto_type == 'Peak':
            self.work_que.put(['Peak', station, start, end])
        
        self.workThread = dataThread(self.work_que, self.return_que)
        self.workThread.start()
        self.controller.master.after(100, self.thread_loop)
        
    #Loops through actions in the thread when they are available
    def thread_loop(self):
        if not self.workThread.results_queue.empty():
            while not self.workThread.results_queue.empty():
                results, typ = self.workThread.results_queue.get()
                data = results[0]
                diag_dict = results[1]
                if len(data) == 0:
                    if 'Error' in diag_dict.keys(): 
                        tk.messagebox.showerror('Error', diag_dict['Error'])
                    else:
                        tk.messagebox.showerror('Error', 'Unable to upload data. Make sure you have connections and the inputs are correct.')
                    self.controller.notbusy()
                else:
                    self.parent.data_uploaded(data)
                    self.controller.notbusy()           
        else: 
            self.controller.master.after(100, self.thread_loop)
            
#%%## Global Functions
def callback(url): #Accesses the internet given a url
    webbrowser.open_new(url)

#Checks whether the entry can be properly cast to a given data type and reports 'Error' otherwise
def check_entry(entry, casts): 
    val = None
    for cast in casts:
        try:
            val = cast(entry)
        except (TypeError, ValueError):
            pass
        else:
            break
    if (val is None) or (val != val):
        val = 'Error'
    return val

#Removes all text from a list of tk.Entry objects
def clear_entries(entry_list):
    for entry in entry_list:
        entry.delete(0, "end")


#%%##Import from Workbook Functions
#Converts the dataframe into an Equation object
def get_equation_from_df(df): #2 columns, [Attribute,Value]
    try:
        eq_name = df.iloc[0, 1]
        eq_form = df.iloc[1, 1]
        if eq_form == 'Linear':
            coeffs = [float(df.iloc[2,1]), float(df.iloc[3,1])]
        else:
            coeffs = [float(df.iloc[2,1]), float(df.iloc[3,1]), float(df.iloc[4,1])]
            
        x_label = df.iloc[5, 1]
        y_label = df.iloc[6,1]
        out_eq = mc.Equation(eq_name, eq_form, coeffs, 'Discharge (cfs)', 'Stage (ft)', x_label, y_label)
        return out_eq
    except:
        return False

#Converts two equation dicts into a piecewise equation
def get_piecewise(eq_name, eq_dict):
    try:
        eq_names = eq_name.split(' + ')
        eq_list = []
        range_list = [eq_dict[eq_names[0]].lb]
        for i in eq_names:
            eq_list.append(eq_dict[i])
            range_list.append(eq_dict[i].ub)
        out_eq = mc.PiecewiseEquation(eq_names[0], eq_list, eq_list[0].xlabel, eq_list[0].ylabel, range_list)
        return out_eq
    except:
        return False

#Creates a module from the dataFrame input
def import_mod_from_df(df, eq_dict):
    mod_class = df.iloc[0,1]
    raw = {}
    ad = {}
    mod_attr = get_static_module_attributes(mod_class)
    row = 1
    for key in mod_attr.keys(): #Based on input order
        raw[key] = df.iloc[row,1]
        row += 1
    
    for key in raw.keys():
        input_type = mod_attr[key][0][0]
        if raw[key] is np.nan:
            ad[key] = None
        else:
            if input_type == 'text entry':
                ad[key] = check_entry(raw[key], mod_attr[key][2])
                if (ad[key] == 'Error') or (ad[key] == ''):
                    if mod_attr[key][4]: #is_optional
                        ad[key] = None
                    else:
                        return False
            elif input_type == 'Equation':
                if raw[key] not in eq_dict.keys():
                    if mod_attr[key][4]:
                        ad[key] = None
                    else:
                        return False
                elif ' + ' in raw[key]: #If a piecewise equation
                    pcwise = get_piecewise(raw[key], eq_dict)
                    if pcwise is False:
                        if mod_attr[key][4]:
                            ad[key] = None
                        else:
                            return False
                else:
                    ad[key] = eq_dict[raw[key]]
                    if ad[key] is False:
                        if mod_attr[key][4]:
                            ad[key] = None
                        else:
                            return False
            elif input_type == 'OptionMenu':
                if raw[key] not in mod_attr[key][0][1]:
                    return False
                else:
                    ad[key] = raw[key]
            elif input_type == 'month box':
                months = get_month_input(raw[key])
                if months is not False:
                    ad[key] = months
                else:
                    return False
            elif input_type == 'checkbox':
                if raw[key] == 'Y':
                    ad[key] = True
                else:
                    ad[key] = False
            else:
                print('input type error')
                return False
    
    mod = create_mod_from_dict(mod_class, ad)
    return mod


#Turns a dict containing all the attribute information into a module object. Checks for optional attributes
def create_mod_from_dict(mod_class, ad): 
    out_mod = False
    try:
        if mod_class == 'Generation':
            out_mod = mc.Generation_module(ad['Name'],ad['Capital Cost'], ad['Annual Operating Cost'],\
                                           ad['Width'], ad['Length'], ad['Design Flow'], ad['Operating Months'], \
                                               ad['Minimum Operating Flow'],ad['Maximum Operating Flow'],ad['Minimum Operating Head'], \
                                                  ad['Design Head'], ad['Maximum Operating Head'],ad['Flow Efficiency Curve'], \
                                                      ad['Head Efficiency Curve'],ad['Max Power'], ad['Cost of Start-Stops'], ad['Instream or Diversion'])    
    
        elif mod_class == 'Fish Passage':
            out_mod = mc.Fish_module(ad['Name'],ad['Capital Cost'], ad['Annual Operating Cost'],\
                                           ad['Width'], ad['Length'], ad['Design Flow'], ad['Operating Months'], \
                                               ad['Maximum Headwater Drop'],ad['Maximum Headwater Rise'],\
                                                   ad['Minimum Tailwater Level'], ad['Maximum Tailwater Level'], ad['Instream or Diversion'])
            
        elif mod_class == 'Sediment Passage':
            if ad['Operating Mode'] == 'Continuous':
                out_mod = mc.Sediment_module(ad['Name'],ad['Capital Cost'], ad['Annual Operating Cost'],\
                                               ad['Width'], ad['Length'], ad['Design Flow'], ad['Operating Months'], \
                                                   ad['Operating Mode'], ad['Instream or Diversion'])
            elif ad['Operating Mode'] == 'Sluicing':
                if ad['Operating Flow'] == 'Error':
                    return False
                else:
                    out_mod = mc.Sediment_module(ad['Name'],ad['Capital Cost'], ad['Annual Operating Cost'],\
                                               ad['Width'], ad['Length'], ad['Design Flow'], ad['Operating Months'], \
                                                   ad['Operating Mode'], ad['Operating Flow'], ad['Instream or Diversion'])
            elif ad['Operating Mode'] == 'Flushing':
                if (ad['Flushing Duration'] == 'Error') or (ad['Operating Frequency'] == 'Error'):
                    return False
                else:
                    out_mod = mc.Sediment_module(ad['Name'],ad['Capital Cost'], ad['Annual Operating Cost'],\
                                               ad['Width'], ad['Length'], ad['Design Flow'], ad['Operating Months'], \
                                                   ad['Operating Mode'], ad['Operating Flow'], ad['Flushing Duration'], \
                                                       ad['Operating Frequency'], ad['Instream or Diversion'])
        elif mod_class == 'Recreation':
            out_mod = mc.Recreation_module(ad['Name'],ad['Capital Cost'], ad['Annual Operating Cost'],\
                                           ad['Width'], ad['Length'], ad['Design Flow'], ad['Operating Months'], \
                                               ad['Maximum Headwater Drop'],ad['Maximum Headwater Rise'],\
                                                   ad['Minimum Tailwater Level'], ad['Maximum Tailwater Level'], ad['Instream or Diversion'])
        elif mod_class == 'Water Passage':
            if (ad['Operating Mode'] == 'Continuous') or (ad['Operating Mode'] == 'Controlled Spillway'):
                out_mod = mc.Water_module(ad['Name'],ad['Capital Cost'], ad['Annual Operating Cost'],\
                                           ad['Width'], ad['Length'], ad['Design Flow'], ad['Operating Months'], \
                                               ad['Operating Mode'], ad['Instream or Diversion'])
            elif ad['Operating Mode'] == 'Uncontrolled Spillway':
                if (ad['Weir Coefficient'] == 'Error') or (ad['Crest Height'] == 'Error'):
                    return False
                else:
                    out_mod = mc.Water_module(ad['Name'],ad['Capital Cost'], ad['Annual Operating Cost'],\
                                           ad['Width'], ad['Length'], ad['Design Flow'], ad['Operating Months'], \
                                               ad['Operating Mode'],ad['Weir Coefficient'],ad['Crest Height'], ad['Instream or Diversion'])
        elif mod_class == 'Non-overflow':
            out_mod = mc.Nonoverflow_module(ad['Name'],ad['Capital Cost'], ad['Annual Operating Cost'],\
                                           ad['Width'], ad['Length'])
        elif mod_class == 'Foundation':
            out_mod = mc.Foundation_module(ad['Name'],ad['Capital Cost'], ad['Annual Operating Cost'],\
                                           ad['Width'], ad['Length'])
        return out_mod
    except:
        return False

#Turns the month input string into a list of month index integers
def get_month_input(entry_str):
    try:
        if entry_str == 'all':
            return [i for i in range(1, 13)]
        else:
            month_strs = entry_str.split(',')
            return [int(i) for i in month_strs]
    except:
        return False

#Imports a certain type of information from the waterSHED workbook when given a path name and type of object to import
def import_from_workbook(path_name, import_type):
    eq_dict = {}
    #Get equations
    try:
        eq_df = pd.read_excel(path_name, sheet_name='Equations')
        for c in range(0, int(len(eq_df.columns)/2)):
            eq = get_equation_from_df(eq_df.iloc[:, 2*c:2*c+2])
            if eq is not False:
                eq_dict[eq.name] = eq
    except:
        pass
    
    all_list = []
    try: 
        #For each page in the workbook, create dataframes based on the assumed sheet structure, check for errors, and try to create the respective object
        if (import_type == 'Site') or (import_type == 'All'):
            df = pd.read_excel(path_name, sheet_name='Site')
            
            char_col = 1
            name = df.iloc[0,char_col]
            width = check_entry(df.iloc[1,char_col], [float])
            elevation = check_entry(df.iloc[2,char_col], [float])
            slope = check_entry(df.iloc[3,char_col], [float])
            trap_b = check_entry(df.iloc[4, char_col], [float])
            
            
            optional = [False, False, True, True, True]
            vals = [name, width,  slope, trap_b,elevation]
            for i in range(0, len(vals)):
                if (vals[i] == '') or (vals[i] == 'Error'):
                    if optional[i] == False:
                        return 'Unable to interpret a required input'
                    else:
                        vals[i] = None
            
            stage_eq_name = df.iloc[5, char_col]
            res_eq_name = df.iloc[6, char_col]
            
            if stage_eq_name in eq_dict.keys():    
                stage_eq = eq_dict[stage_eq_name]
            elif ' + ' in stage_eq_name:
                stage_eq = get_piecewise(stage_eq_name, eq_dict)
                if stage_eq is False:
                    return 'Unable to identify the stage-discharge equation. Please make sure the equation names match.'                
            else:
                return 'Unable to identify the stage-discharge equation. Please make sure the equation names match.'
            
            if res_eq_name in eq_dict.keys():
                res_eq = eq_dict[res_eq_name]
            else:
                res_eq = None

            inf_df = pd.read_excel(path_name, sheet_name='Inflows')
            daily_col = 0
            daily_df = inf_df.iloc[1:, [daily_col,daily_col+1]]
            daily_df.columns = ['dateTime', 'Discharge (cfs)']
            daily_df['Discharge (cfs)'] = pd.to_numeric(daily_df['Discharge (cfs)'], errors='coerce')
            daily_df['dateTime'] = pd.to_datetime(daily_df['dateTime'], infer_datetime_format=True)
            daily_df = daily_df.dropna()
            
            
            if len(daily_df) <=0:
                return 'Unable to import daily flow data which is a required input.'
            else:
                daily_flow_data = mc.FlowData('Daily Inflows', daily_df)
            
            peak_df = pd.read_excel(path_name, sheet_name='Peak Flows')
            peak_col = 0
            peak_df = peak_df.iloc[1:, [peak_col,peak_col+1]]
            peak_df.columns = ['dateTime', 'Discharge (cfs)']
            peak_df['Discharge (cfs)'] = pd.to_numeric(peak_df['Discharge (cfs)'], errors='coerce')
            peak_df['dateTime'] = pd.to_datetime(peak_df['dateTime'], infer_datetime_format=True)
            peak_df = peak_df.dropna()
            
            
            if len(peak_df)<= 0:
                peak_flow_data = None
            else:
                peak_flow_data = mc.FlowData('Peak Flows', peak_df)
            
            out_site = mc.Site(vals[0], vals[1], daily_flow_data, stage_eq, res_eq, vals[2], vals[3], peak_flow_data, vals[4])
            
            if import_type == 'All':
                all_list.append(out_site)
            else:
                return out_site

    
        if (import_type == 'Costs') or (import_type == 'All'):

            df = pd.read_excel(path_name, sheet_name='Costs')
            row = 0
            col = 1
            energy = check_entry(df.iloc[row, col], [float])
            add_capital = check_entry(df.iloc[row+1, col], [float])
            add_noncapital = check_entry(df.iloc[row+2, col], [float])
            excavation = check_entry(df.iloc[row+3, col], [float])
            overhead = check_entry(df.iloc[row+4, col], [float])
            overhead_type = df.iloc[row+4, col+2]
            engineering = check_entry(df.iloc[row+5, col], [float])
            engineering_type = df.iloc[row+5, col+2]
            contingency = check_entry(df.iloc[row+6, col], [float])
            contingency_type = df.iloc[row+6, col+2]
            om = check_entry(df.iloc[row+7, col], [float])
            om_type = df.iloc[row+7, col+2]
            recreation = check_entry(df.iloc[row+8, col], [float])
            flood = check_entry(df.iloc[row+9, col], [float])
            discount = check_entry(df.iloc[row+10, col], [float])
            proj_life = check_entry(df.iloc[row+11, col], [float])
            
            for i in [energy, add_capital, add_noncapital, excavation, overhead, engineering, contingency, om, recreation, flood, discount, proj_life]:
                if (i == '') or (i == 'Error'):
                    return 'Unable to import cost information. Make sure entries are numeric. Any unused entries, must be set to zero.'
            
            for i in [overhead_type, engineering_type, contingency_type, om_type]:
                if i not in ['($) Total Cost', '(%) Percent of ICC']:
                    return 'Make sure unit option are either (%) Percent of ICC or ($) Total Cost'
            
            out_costs = mc.Cost_tables(energy, excavation_cost=excavation,\
                        overhead_cost=[overhead, overhead_type], engineering_cost=[engineering, engineering_type],\
                            contingency_cost=[contingency, contingency_type], recreation_price=recreation,\
                                flood_price =flood, om_costs=[om,om_type], discount_rate=discount, \
                                    project_life=proj_life, add_capital=add_capital, add_noncapital=add_noncapital)
            if import_type == 'All':
                all_list.append(out_costs)
            else:
                return out_costs
        
        if (import_type == 'Preferences') or (import_type == 'All'):

            df = pd.read_excel(path_name, sheet_name='Preferences')
            
            nol = check_entry(df.iloc[0, 1], [float])
            if (nol == '') or (nol == 'Error'):
               return 'Unable to upload normal operating level. Please make sure it is import as a numeric value.'
           
            try:
                start = pd.to_datetime(df.iloc[1, 1])
                end = pd.to_datetime(df.iloc[2, 1])
            except:
                return 'Unable to upload test data start and end dates.'
            
            dispatch_mode = df.iloc[3,1]
            if dispatch_mode not in ['Design Ramping', 'Peak Ramping', 'Simple Greedy', 'Advanced Greedy']:
                dispatch_mode = 'Design Flow'
                
            overrun_input = df.iloc[4, 1]
            if overrun_input == 'Y':
                overrun = True
            else:
                overrun = False
            
            notch_flow = check_entry(df.iloc[5, 1], [float])
            if (notch_flow == '') or (notch_flow == 'Error'):
                notch_flow = None
            min_flow = check_entry(df.iloc[6, 1], [float])
            if (min_flow == '') or (min_flow == 'Error'):
                min_flow = None
            min_flow_type = check_entry(df.iloc[6, 3], [str])
            if (min_flow_type != 'cfs (Constant)') or (min_flow_type != '% (Percent of inflow)'):
                min_flow_type = None
                 
            op_cls = ['Gen', 'Sed', 'Fish', 'Rec', 'Wat']
            op_rank = []
            for rank in range(1, 6):
                for mod in range(0,5):
                    mod_rank = df.iloc[mod+8,1]
                    if mod_rank not in [1,2,3,4,5]:
                        return 'Unable to import operation priority rankings.'
                    if mod_rank == rank:
                        op_rank.append(op_cls[mod])
            
            pref = mc.Facility_preferences(op_rank,nol, start, end, overrun, min_flow, min_flow_type, notch_flow, dispatch_mode)
            if import_type == 'All':
                all_list.append(pref)
            else:
                return pref
            
        if (import_type == 'Module Library') or (import_type == 'All'):
            mod_list = []
            df = pd.read_excel(path_name, sheet_name='Module Library')
            for c in range(0, int(len(df.columns)/2)):
                mod = import_mod_from_df(df.iloc[:,2*c:2*c+2], eq_dict)
                if mod is not False:    
                    mod_list.append(mod)
            if import_type == 'All':
                all_list.append(mod_list)
            else:
                return mod_list     
    
        if (import_type == 'Species') or (import_type == 'All'):
            species_list = []
            try:
                df = pd.read_excel(path_name, sheet_name='Species List')
                for c in range(0, int(len(df.columns)/2)):
                    col = 2*c + 1
                    name = check_entry(df.iloc[0, col], [str])
                    a = check_entry(df.iloc[1, col], [float])
                    b = check_entry(df.iloc[2, col], [float])
                    up = get_month_input(check_entry(df.iloc[3, col], [str]))
                    down = get_month_input(check_entry(df.iloc[4, col], [str]))
                
                    spec = mc.Species(name, up, down, a, b)
                    species_list.append(spec)
            except:
                species_list = []
            if import_type == 'All':
                all_list.append(species_list)
            else:
                return species_list     
        return all_list
    except:
        return 'Unable to import from the watershed workbook. Please double check inputs and that the file is closed.'
    
#%%## Static Module Attributes
#Returns a dict with the attribute and its characteristics for each module class
#attribute name: [input info], unit, data validate, [support tool names], is_optional boolean
def get_static_module_attributes(mod_type): 
    out_dict = {'Name':[['text entry'], '', [str], [], False],\
                       'Capital Cost':[['text entry'], '$', [float], [], False],\
                       'Annual Operating Cost':[['text entry'], '$', [float], [], False],\
                       'Width':[['text entry'], 'ft', [float], [], False],\
                       'Length':[['text entry'], 'ft', [float], [], False]}
        
    if mod_type == 'Foundation':
        return out_dict
    elif mod_type == 'Non-overflow':
        return out_dict
    else:
        temp_passage_module_att_dict = {'Design Flow':[['text entry'], 'cfs', [float], [], False], \
                                'Operating Months':[['month box'], '', [], [], False], \
                                'Instream or Diversion': [['checkbox', 'Diversion (Y/N)'], '', [], [], False]}
        out_dict.update(temp_passage_module_att_dict)
                
        if (mod_type == 'Fish Passage') or (mod_type == 'Recreation'):
            fish_and_rec_dict = {'Maximum Headwater Drop':[['text entry'], 'ft', [float], [], True], \
                             'Maximum Headwater Rise':[['text entry'], 'ft', [float], [], True], \
                            'Minimum Tailwater Level':[['text entry'], 'ft', [float], [], True], \
                            'Maximum Tailwater Level':[['text entry'], 'ft', [float], [], True]}
            out_dict.update(fish_and_rec_dict)
        elif mod_type == 'Generation':
            temp_gen_att_dict = {'Minimum Operating Flow':[['text entry'], 'cfs', [float], [], False],\
                            'Maximum Operating Flow':[['text entry'], 'cfs', [float], [], False],\
                            'Minimum Operating Head':[['text entry'], 'ft', [float], [], False],\
                            'Design Head':[['text entry'], 'ft', [float], [], False],\
                            'Maximum Operating Head':[['text entry'], 'ft', [float], [], False],\
                            'Flow Efficiency Curve':[['Equation',['Efficiency vs. Flow', 'Flow (cfs)','Turbine Efficiency (%)']], '',[], ['Turbine Flow Efficiency'], False],\
                            'Head Efficiency Curve':[['Equation',['Efficiency vs. Head Deviation','Relative Head (%)','Turbine Efficiency (%)']], '', [], ['Turbine Head Efficiency'], True],\
                            'Max Power':[['text entry'], 'kW', [float], [], True],\
                            'Cost of Start-Stops':[['text entry'], '$/start', [float], [], True]}
            out_dict.update(temp_gen_att_dict)
        elif mod_type == 'Sediment Passage':
            temp_sed_att_dict = {'Operating Mode':[['OptionMenu',['Continuous', 'Sluicing', 'Flushing']], '', [], [], False], \
                            'Operating Flow':[['text entry'], 'cfs', [float], ['Sluicing Operating Flow'], True], \
                            'Flushing Duration':[['text entry'], 'days', [int], [], True], \
                            'Operating Frequency':[['text entry'], 'flushes/year', [int], [], True]}
            out_dict.update(temp_sed_att_dict)
        elif mod_type == 'Water Passage':
            temp_wat_att_dict = {'Operating Mode':[['OptionMenu',['Continuous', 'Controlled Spillway', 'Uncontrolled Spillway']], '', [], [], False], \
                            'Weir Coefficient':[['text entry'], '(C)', [float], ['Tool Tip - Uncontrolled Spillway'], True], \
                            'Crest Height':[['text entry'], 'ft', [float], ['Tool Tip - Uncontrolled Spillway'], True]}
            out_dict.update(temp_wat_att_dict)
        return out_dict
    
# Dynamic Module Attributes
#Returns the module attributes and available controlling variables for a given module class
#attribute name: [input info], unit, data validate, [support tool names], is_optional boolean
def get_dynamic_module_attributes(mod_type): 
    out_dict = {'Name':[['text entry'], '', [str], [], False],\
                       'Capital Cost':[['Optional'], '$', [float], [], False],\
                       'Annual Operating Cost':[['Optional'], '$', [float], [], False],\
                       'Width':[['text entry'], 'ft', [float], [], False],\
                       'Length':[['text entry'], 'ft', [float], [], False]}
    if mod_type == 'Foundation':
        temp_foundation_module_dict = {'Depth': [['text entry'], '', [float], ['Foundation Depth'], False]}
        out_dict.update(temp_foundation_module_dict)
        out_vars = ['Volume', 'Depth']
        return out_dict, out_vars
    elif mod_type == 'Non-overflow':
        temp_nonoverflow_module_dict = {'Height': [['Optional'], '', [float], ['Non-overflow Height'], False]}
        out_dict['Length'][0] = ['Optional'] 
        out_dict.update(temp_nonoverflow_module_dict)
        out_vars = ['Volume', 'Normal Operating Level']
        return out_dict, out_vars
    else:
        temp_passage_module_att_dict = {'Design Flow':[['text entry'], 'cfs', [float], [], False], \
                                'Operating Months':[['month box'], '', [], [], False], \
                                'Instream or Diversion': [['checkbox', 'Diversion (Y/N)'], '', [], [], False]}
        out_vars = []
        out_dict.update(temp_passage_module_att_dict)
        if (mod_type == 'Fish Passage') or (mod_type == 'Recreation'):
            fish_and_rec_dict = {'Maximum Headwater Drop':[['text entry'], 'ft', [float], [], True], \
                             'Maximum Headwater Rise':[['text entry'], 'ft', [float], [], True], \
                            'Minimum Tailwater Level':[['text entry'], 'ft', [float], [], True], \
                            'Maximum Tailwater Level':[['text entry'], 'ft', [float], [], True], \
                            'Number of Steps':[['Optional'], 'ft', [float], ['Drop height per step'], False], \
                            'Step Type':[['OptionMenu', ['Continuous', 'Round up', 'Round down']], 'ft', [float], ['Step Type'], False]}
            out_dict['Length'][0] = ['Optional'] #Make sure only number of steps is not a function of number of steps
            out_dict['Design Flow'][0] = ['Optional']
            out_dict.update(fish_and_rec_dict)
            for i in ['Normal Operating Level', 'Mean Daily Flow', 'Number of Steps']:
                out_vars.append(i)
        elif mod_type == 'Generation':
            temp_gen_att_dict = {'Minimum Operating Flow':[['Optional'], 'cfs', [float], [], False],\
                            'Maximum Operating Flow':[['Optional'], 'cfs', [float], [], False],\
                            'Minimum Operating Head':[['Optional'], 'ft', [float], [], False],\
                            'Design Head':[['text entry'], 'ft', [float], [], False],\
                            'Maximum Operating Head':[['Optional'], 'ft', [float], [], False],\
                            'Flow Efficiency Curve':[['Equation',['Efficiency vs. Flow', 'Flow (cfs)','Turbine Efficiency (%)']], '',[], ['Turbine Flow Efficiency'], False],\
                            'Head Efficiency Curve':[['Equation',['Efficiency vs. Head Deviation','Relative Head (%)','Turbine Efficiency (%)']], '', [], ['Turbine Head Efficiency'], True],\
                            'Max Power':[['Optional'], 'kW', [float], [], True],\
                            'Cost of Start-Stops':[['text entry'], '$/start', [float], [], True]}
            out_dict['Width'][0] = ['Optional']
            out_dict['Length'][0] = ['Optional']
            out_dict.update(temp_gen_att_dict)
            out_vars.append('Nominal Power')
            out_vars.append('Design Head')
            out_vars.append('Design Head and Nominal Power')
            out_vars.append('Design Flow and Nominal Power')
            out_vars.append('Design Flow and Design Head')
            
        elif mod_type == 'Sediment Passage':
            temp_sed_att_dict = {'Operating Mode':[['OptionMenu',['Continuous', 'Sluicing', 'Flushing']], '', [], [], False], \
                            'Operating Flow':[['Optional'], 'cfs', [float], ['Sluicing Operating Flow'], True], \
                            'Flushing Duration':[['text entry'], 'days', [int], [], True], \
                            'Operating Frequency':[['text entry'], 'flushes/year', [int], [], True]}
            out_dict.update(temp_sed_att_dict)
            out_dict['Design Flow'][0] = ['Optional']
            out_vars.append('Mean Daily Flow')
        elif mod_type == 'Water Passage':
            temp_wat_att_dict = {'Operating Mode':[['OptionMenu',['Continuous', 'Controlled Spillway', 'Uncontrolled Spillway']], '', [], [], False], \
                            'Weir Coefficient':[['text entry'], '(C)', [float], ['Tool Tip - Uncontrolled Spillway'], True], \
                            'Crest Height':[['Optional'], 'ft', [float], ['Tool Tip - Uncontrolled Spillway'], True]}
            out_dict['Design Flow'][0] = ['Optional']
            out_dict.update(temp_wat_att_dict)
            out_vars.append('Normal Operating Level')
        return out_dict, out_vars
 
#%%## Input creation and retrieval - useful when creating inputs based on dicts
#Takes an input dict from a frame or page and creates a label, entry, unit label, and support tool button for each attribute
#Each input dict has a key that is the name of the attribute
#Each attribute has the following information: [[input info], unit, data type, [support tool names], is_optional boolean]
def create_inputs(page, parent, input_dict, entry_width=20, module_type=None, cvars=None):
    att_labels = {}
    att_entries = {}
    att_units = {}
    att_tools = {}
    input_vars = {}
    
    for key in input_dict:
        input_type = input_dict[key][0][0]
        lbl_text = key
        if input_dict[key][4] == True:
            lbl_text = lbl_text + '*'
        
        att_labels[key] = tk.Label(parent,text=lbl_text, font=TEXT_FONT, bg=FRAME_BG_COLOR)
        
        att_tools[key] = tk.Button(parent, text='!', command=lambda tool=input_dict[key][3], key=key:tool_click(page, key, tool, module_type))
        
        unit = input_dict[key][1]
        if type(unit) == list:
            input_vars[key] = tk.StringVar()
            att_units[key] = tk.OptionMenu(parent, input_vars[key], *unit)
            input_vars[key].set(unit[0])
        else:
            att_units[key] = tk.Label(parent,text=unit, font=TEXT_FONT, bg=FRAME_BG_COLOR)
        
        if input_type == 'text entry':
            att_entries[key] = ttk.Entry(parent, width=entry_width)
        elif input_type == 'OptionMenu':
            input_vars[key] = tk.StringVar(name=key)
            att_entries[key] = tk.OptionMenu(parent, input_vars[key], *input_dict[key][0][1])
            input_vars[key].set(input_dict[key][0][1][0])
        elif input_type == 'Equation':
            if len(input_dict[key][0][1]) == 4: #Has an auto regression type
                att_entries[key] = EquationAddFrame(parent, page.controller, input_dict[key][0][1][0],input_dict[key][0][1][1], input_dict[key][0][1][2], auto_type=input_dict[key][0][1][3])
            else:
                att_entries[key] = EquationAddFrame(parent, page.controller, input_dict[key][0][1][0],input_dict[key][0][1][1], input_dict[key][0][1][2])
        elif input_type == 'month box':
            att_entries[key] = MonthCheckFrame(parent, page.controller, all_on=True)
        elif input_type == 'checkbox':
            input_vars[key] = tk.BooleanVar(name=key)
            input_vars[key].set(False)
            att_entries[key] = tk.Checkbutton(parent, text=input_dict[key][0][1], variable=input_dict[key], onvalue=True, offvalue=False, bg=FRAME_BG_COLOR)
        elif input_type == 'Optional':
            att_entries[key] = OptionalFrame(parent, page.controller, module_type, key, input_dict[key], cvars)    

    return att_labels, att_entries, att_units, att_tools, input_vars

#When a support tool is clicked, it opens a support tool window
#The key is the name of the attribute 
#The tool is the name of any support tool model
#Mod type is used to distinguish between module types with the same attribute name
def tool_click(parent, key, tool=None, mod_type=None):
    SupportToolWindow(parent, parent.controller, key, tool, mod_type)

#Gets the values for each input corresponding to the input dict. The page must have an att_entries object
#The required function is used to determine when an input is necessary for creation of an object
def get_values(parent, required_fxn=None):
    out_dict = {}   
    for key in parent.att_labels:
        input_type = parent.input_dict[key][0][0]
        if required_fxn is not None:
            required = required_fxn(key)
        else:
            required = not (parent.input_dict[key][4])
        if input_type == 'text entry':
            v = check_entry(parent.att_entries[key].get(),parent.input_dict[key][2])
            if (str(v) == '') or (str(v) == 'Error'):
                if not required: 
                    out_dict[key] = None
                else:
                    tk.messagebox.showerror("Error", 'Could not create object, double check {}'.format(key))
                    return False
            else:
                out_dict[key] = v
        elif input_type == 'Equation':
            eq = parent.att_entries[key].get_equation()
            if eq is None:
                if not required: 
                    out_dict[key] = None
                else:
                    tk.messagebox.showerror('Error', 'Please make sure all equations are entered.')
                    return False
            else:
                out_dict[key] = eq
        elif input_type == 'OptionMenu':
            out_dict[key] = parent.input_vars[key].get()
        elif input_type == 'month box':
            out_dict[key] = parent.att_entries[key].get_month_list()
            if required and (len(out_dict[key]) <= 0):
                tk.messagebox.showerror('Error', 'Must select at least one month.')
        elif input_type == 'checkbox':
            out_dict[key] = parent.input_vars[key].get()
        elif input_type == 'Optional':
            v = parent.att_entries[key].get_value()
            if (v is False) and required:
                tk.messagebox.showerror('Error', 'Unable to interpret the {} input'.format(key))
                return False
            elif not required:
                v = None
            out_dict[key] = v
        else:
            print('Entry type not registered')
    return out_dict

#Packs all objects created by the create_inputs function. Pages must have att_labels, att_entries, att_units, and att_tools objects
def pack_attributes(page, parent, row_counter=0):
    parent.grid_forget()
    for key in page.att_labels:
        page.att_labels[key].grid(row=row_counter, column=0, pady=5, sticky='nse', padx=5)
        page.att_entries[key].grid(row=row_counter, column=1, pady=5, sticky='nsew')
        page.att_units[key].grid(row=row_counter, column=2, pady=5, sticky='nsw')
        page.att_tools[key].grid(row=row_counter, column=3, pady=5, padx=5)
        row_counter+=1

#%%## Driver Code 
root = tk.Tk()
app = tkinterApp(root) 
root.mainloop()
plt.close('all')
        