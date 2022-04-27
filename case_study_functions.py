# -*- coding: utf-8 -*-
"""
Last updated on April 25 2022

@author: Colin Sasthav
"""
#%%## IMPORT PACKAGES
import module_classes as mc
import dynamic_modules as dm
import numpy as np

#%%## Constants
ft_to_m = 0.3048
cfs_to_cms = 0.0283

temp_eq = mc.Equation('Temp', 'Constant', [1], 'Temp X', 'Temp Y')
all_months = [i for i in range(1, 13)]
#%%## Retrieval functions
#Returns the list of modules for a given case study
def get_default_modules(case_name):
    fou_scaling_factors = {'Deerfield': 1.82, 'Housatonic': 1.2, 'Schuylkill':1.40}
    fou_scaling = fou_scaling_factors[case_name]
    out_mods = []
    def_mods = {'Generation': {'Kaplan':get_kaplan_dict()}, \
                          'Fish Passage': {'Vertical Slot':get_verticalslot_dict()}, \
                          'Sediment Passage': {'Sluice Gate': get_sluice_dict()}, \
                              'Recreation': {'Boat Chute':get_chute_dict()}, \
                                'Water Passage': {'Obermeyer':get_obermeyer_dict()},\
                                    'Non-overflow': {'Precast Concrete':get_precastnon_dict()}, \
                                        'Foundation': {'Precast Concrete Foundation':get_precastfou_dict(fou_scaling)}}

    for mod_type in def_mods.keys():
        for mod in def_mods[mod_type].keys():
            ad = def_mods[mod_type][mod]
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
            out_mods.append(out_mod)
    return out_mods
                    

#%%## Dynamic module dicts - these return the dynamic modules attributes in dict form for the modules used in the case studies
#Please refer to the Sasthav Dissertation for more information on the case studies

#Conceptual Kaplan turbine module
def get_kaplan_dict(): 
    width_coeff = (0.5*3/ft_to_m)*(cfs_to_cms**0.457)# width = 3 * tur_dia #Using case study assumptions that module width is 3*Dia
    width_exp = 0.457
    length_coeff = (0.5*7/ft_to_m)*(cfs_to_cms**0.457)# length = 7 * tur_dia #Using case study assumptions that module length is 7*Dia
    length_exp = 0.457
    min_op_flow_per = 0.40
    max_op_flow_per = 1.05
    min_op_head_per = 0.65
    max_op_head_per = 1.25
    
    peak_eff = 0.80
    snl_coeff = 12.28
    peak_eff_ratio = 0.85
    left_coeffs = [-1.0*peak_eff*snl_coeff, -1.0/peak_eff_ratio, 1.0, 7.2, peak_eff]
    right_coeffs = [-1.0, 1.0/peak_eff_ratio, -1, 1.5, peak_eff]
    flow_eff_eq_left = mc.Equation('Kaplan Flow Efficiency Curve - Left', 'Binomial', left_coeffs, 'Relative Discharge (% of Design Flow)','Efficiency (%)', lower_bound=min_op_flow_per,upper_bound=peak_eff_ratio)
    flow_eff_eq_right = mc.Equation('Kaplan Flow Efficiency Curve - Right', 'Binomial', right_coeffs, 'Relative Discharge (% of Design Flow)','Efficiency (%)', lower_bound=peak_eff_ratio,upper_bound=max_op_flow_per)    
    flow_eff_eq = mc.PiecewiseEquation('Kaplan Flow Efficiency Curve', [flow_eff_eq_left, flow_eff_eq_right], 'Relative Discharge (% of Design Flow)','Efficiency (%)', [min_op_flow_per, peak_eff_ratio, max_op_flow_per])
    
    head_eff_eq = mc.Equation('Kaplan Head Efficiency Curve (Gordon)', 'Polynomial-2', [-0.5, 1, 0.5], 'Relative Head (% of Design Head)','Efficiency (%)', lower_bound=min_op_head_per,upper_bound=max_op_head_per)    
    
    fixed_cap_costs = 50000 #Per turbine component of switchyard and interconnection
    
    #Fen, Zhang, and Smith (2012) - Small Hydropower Cost Reference Model
    scaling_factor = 3.7   
    # cost = 1536*(head**-0.193)*(power**0.982)*conversion_rate
    cap_cost_eq = mc.Equation('Kaplan Capital Cost', 'Multi-Power', [1536*scaling_factor,-0.193,0.982,fixed_cap_costs*scaling_factor], 'Head (ft)', 'Cost ($)', z_label='Power (kW)', dynamic_type='Function of Design Head and Nominal Power')
    # op_cost_per = 0.05
    # op_cost_eq = mc.Equation('Kaplan Operating Cost', 'Multi-Power', [op_cost_per*1536*scaling_factor,-0.193,0.982,0], 'Head (ft)', 'Cost ($)', z_label='Power (kW)', dynamic_type='Function of Design Head and Nominal Power')
    op_cost_eq = 0

    out_dict = {'Name': 'Kaplan',\
                'Capital Cost': cap_cost_eq,\
                'Annual Operating Cost':op_cost_eq,\
                'Width':mc.Equation('Kaplan Width', 'Power', [width_coeff, width_exp, 0], 'Design Flow', 'Width', dynamic_type='Function of Design Flow'),\
                'Length': mc.Equation('Kaplan Length', 'Power', [length_coeff, length_exp, 0], 'Design Flow', 'Length', dynamic_type='Function of Design Flow'),\
                'Design Flow': 338, \
                'Design Head': 10.4,\
                'Operating Months':all_months, \
                'Instream or Diversion': False, \
                'Minimum Operating Flow': mc.Equation('Kaplan Min Op Flow', 'Linear', [min_op_flow_per, 0], 'Design Flow', 'Minmum Operating Flow', dynamic_type='Function of Design Flow'),\
                'Maximum Operating Flow': mc.Equation('Kaplan Max Op Flow', 'Linear', [max_op_flow_per, 0], 'Design Flow', 'Maximum Operating Flow', dynamic_type='Function of Design Flow'),\
                'Minimum Operating Head': mc.Equation('Kaplan Min Op Head', 'Linear', [min_op_head_per, 0], 'Design Head', 'Minmum Operating Head', dynamic_type='Function of Design Head'),\
                'Maximum Operating Head': mc.Equation('Kaplan Max Op Head', 'Linear', [max_op_head_per, 0], 'Design Head', 'Maximum Operating Head', dynamic_type='Function of Design Head'),\
                'Flow Efficiency Curve':flow_eff_eq,\
                'Head Efficiency Curve':head_eff_eq,\
                'Max Power': None,\
                'Cost of Start-Stops':0} 
    
    return out_dict

#Conceptual vertical slot fishway
def get_verticalslot_dict():

    scaling_factor = 1
    #Dimension Components
    length_per_step = 13.625 #ft 13ft pool + walls
    width_per_step = 11.3 #ft 10.4ft pool + walls
    length = mc.Equation('Vertical Slot Length', 'Linear', [length_per_step, 0], 'Number of Steps', 'Length (ft)', dynamic_type = 'Function of Number of Steps')
    
    #NOL - 1.5ft submergence / slope 
    slope = 0.055
    submergence = 1.5
    number_of_steps_eq = mc.Equation('Vertical Slot Number of Steps', 'Linear', [(1.0/(slope*length_per_step)), -1*(submergence/(slope*length_per_step))], 'Normal Operating Level (ft)', 'Number of steps', dynamic_type='Function of Normal Operating Level')
    
    #Cost components
    slide_gate = 30000
    rack = 20000
    concrete_rate = 975 #$/m3
    reference_concrete_quantity = 260 #m3
    cost_per_step = concrete_rate * reference_concrete_quantity / 16
    cap_cost_eq = mc.Equation('Vertical Slot Capital Cost', 'Linear', [(cost_per_step)*scaling_factor, scaling_factor*(slide_gate+rack)], 'Number of Steps', 'Capital Cost ($)', dynamic_type = 'Function of Number of Steps')
    fish_months = [3,4,5,6]
    
    
    out_dict =  {'Name': 'Vertical Slot Fishway',\
                'Capital Cost': cap_cost_eq,\
                'Annual Operating Cost': 0,\
                'Width': width_per_step,\
                'Length':length,\
                'Design Flow': 34.5, \
                'Operating Months':fish_months, \
                'Instream or Diversion': False, \
                'Number of Steps':number_of_steps_eq, \
                'Step Type': 'Round down', \
                'Maximum Headwater Drop':None, \
                'Maximum Headwater Rise':None, \
                'Minimum Tailwater Level':2.1, \
                'Maximum Tailwater Level':4.9}
    return out_dict

#Conceptual sediment sluice gate
def get_sluice_dict():
#The design flow is assumed 20% of operating flow (6774*0.2 = 1355 in case study report
    op_flow = 6774.0
    design_flow = op_flow * 0.2
    out_dict =  {'Name': 'Sediment Sluice Gate',\
                'Capital Cost': 288000,\
                'Annual Operating Cost': 0,\
                'Width': 15,\
                'Length':30,\
                'Design Flow': design_flow, \
                'Operating Months':all_months, \
                'Operating Mode': 'Sluicing', \
                'Operating Flow': op_flow, \
                'Flushing Duration': None, \
                'Operating Frequency': None, \
                'Instream or Diversion': False}
    return out_dict

#Conceptual boat chute
def get_chute_dict(): 

    #Dimension Components
    length_per_step = 29.5 #ft 20ft pool + drop structure
    width_per_step = 21 #ft 6.4m pool (including walls)
    length = mc.Equation('Boat Chute Length', 'Linear', [length_per_step, 0], 'Number of Steps', 'Length (ft)', dynamic_type = 'Function of Number of Steps')
    
    #NOL - 1.5ft submergence / slope 
    min_tailwater_depth = 1.9 #ft
    max_drop_height = 1.3 #ft
    submergence_below_nol = 1.5
    number_of_steps_eq = mc.Equation('Boat Chute Number of Steps', 'Linear', [(1.0/max_drop_height), -1*((submergence_below_nol + min_tailwater_depth)/max_drop_height)], 'Normal Operating Level (ft)', 'Number of steps', dynamic_type='Function of Normal Operating Level')
    
    #Cost components
    control_building = 18000
    gate_and_controls = 178000
    misc_safety = 110000
    cost_per_step = 604000 / 7
    cap_cost_eq = mc.Equation('Vertical Slot Capital Cost', 'Linear', [(cost_per_step), (control_building+gate_and_controls+misc_safety)], 'Number of Steps', 'Capital Cost ($)', dynamic_type = 'Function of Number of Steps')
    
    design_flow = 50.5 #Average of the minimum and maximum flow range described in the case study report.
    rec_months = [5, 6, 7, 8, 9, 10, 11]
    #Round down because you can optimize

    out_dict =  {'Name': 'Boat Chute',\
                'Capital Cost': cap_cost_eq,\
                'Annual Operating Cost': 0,\
                'Width': width_per_step,\
                'Length':length,\
                'Design Flow': design_flow, \
                'Operating Months': rec_months, \
                'Instream or Diversion': False, \
                'Number of Steps': number_of_steps_eq, \
                'Step Type': 'Round down', \
                'Maximum Headwater Drop':None, \
                'Maximum Headwater Rise':None, \
                'Minimum Tailwater Level':1.9, \
                'Maximum Tailwater Level':None}
    return out_dict

#Conceptual Obermeyer overshot spillway gate
def get_obermeyer_dict(): 
       
    cap_cost_eq_left = mc.Equation('Obermeyer Capital Cost - Left', 'Constant', [387833], 'Normal Operating Level', 'Capital Cost ($)', dynamic_type='Function of Normal Operating Level')
    cap_cost_eq_right = mc.Equation('Obermeyer Capital Cost - Right', 'Linear', [14200, 196133], 'Normal Operating Level', 'Capital Cost ($)', dynamic_type='Function of Normal Operating Level')
    cap_cost_eq = mc.PiecewiseEquation('Obermeyer Capital Cost', [cap_cost_eq_left, cap_cost_eq_right], 'Normal Operating Level', 'Capital Cost ($)', [0, 13.5, 1000], dynamic_type='Function of Normal Operating Level')
    out_dict =  {'Name': 'Obermeyer Spillway',\
                'Capital Cost': cap_cost_eq,\
                'Annual Operating Cost': 0,\
                'Width': 20,\
                'Length':29,\
                'Design Flow': 5500, \
                'Operating Months':all_months, \
                'Instream or Diversion': False, \
                'Operating Mode': 'Controlled Spillway', \
                'Weir Coefficient': None, \
                'Crest Height': None}
    return out_dict

#Conceptual precast concrete nonoverflow module
def get_precastnon_dict(): 
    scaling_factor = 0.87
    length_to_height_ratio = 3.7/4.3 #3.7m long to 4.3m high
    free_board = 0.5 #ft - module height above nol
    
    precast_percent = 0.28
    fill_percent = 0.72
    precast_cost = 975
    fill_cost = 600 #$/m3
    handrail_cost = 500 #$/m
    vol_coeff = (precast_percent*precast_cost + fill_percent*fill_cost)/35.3 #$/ft3 35.3ft3/m3
    cap_cost_eq =  mc.Equation('Precast Capital Cost', 'Linear', [vol_coeff*scaling_factor,handrail_cost*scaling_factor], 'Volume (ft3)', 'Capital Cost ($)', dynamic_type='Function of Volume')
    

    out_dict =  {'Name': 'Precast Concrete',\
                'Capital Cost':cap_cost_eq,\
                'Annual Operating Cost': 0,\
                'Width': 3.28,\
                'Length': mc.Equation('Precast Length', 'Linear', [length_to_height_ratio, free_board*length_to_height_ratio], 'Normal Operating Level', 'Length (ft)', dynamic_type='Function of Normal Operating Level'),\
                'Height': mc.Equation('Precast Height', 'Linear', [1, free_board], 'Normal Operating Level', 'Height (ft)', dynamic_type='Function of Normal Operating Level')}
    return out_dict

#Conceptual precast concrete foundation modules
def get_precastfou_dict(scaling_factor=1): 
    width = 3.28 #ft - 1m
    length = 3.28 #ft - 1m
    
    # scaling_factor = 1.82
    width_m = width * ft_to_m
    length_m = length * ft_to_m
    depth = 5
    #Foundation cost ($/m3)= site clearing + excavate loose rock + leveling concrete + precast concrete + rock anchors
    
    #Constant components
    clearing_depth = 0.5 #m - assumed
    site_clearing = 19.75 * (width_m) * (length_m) * clearing_depth#$19.75/m3
    leveling_depth = 0.5 #m - assumed
    leveling = 620 * (width_m) * (length_m) * leveling_depth #$620/m3
    anchor = 490 * (width_m) * (length_m) #490/m2, $145 per m, 4.5m rod, 0.75 anchors per m2
    
    excavate = 32.75 * (width_m) * (length_m)  #$/m3 depth for schulykill is 1.5m
    precast = 975 * (width_m) * (length_m) * 0.8 #$/m3 depth for schulykill is 1.2m, 0.8 accounts for the difference in precast and excavation depths i.e. the top of foundation is lower than the original bed elevation
    #Need to put the depth (ft) in m to match the others, so divide by ft_to_m
    cap_cost_eq = mc.Equation('Precast Capital Cost', 'Linear', [((excavate+precast)*ft_to_m*scaling_factor), scaling_factor*(site_clearing+leveling+anchor)], 'Depth (ft)', 'Capital Cost ($)', dynamic_type='Function of Depth')
   
    out_dict =  {'Name': 'Precast Foundation',\
                'Capital Cost': cap_cost_eq,\
                'Annual Operating Cost': 0,\
                'Width': width,\
                'Length':length,\
                'Depth': depth}
    return out_dict


def get_75in_screen_dict(): 
#2792 $/cfs from accompanying dissertation cost estimates
#om costs assume 5% of capital costs
    cap_cost = mc.Equation('0.75in Screen Capital Cost', 'Linear', [2792,0], 'Design Flow (cfs)', 'Cost ($)', dynamic_type='Function of Design Flow')
    op_cost = mc.Equation('0.75in Screen Operating Cost', 'Linear', [2792*0.0025,0], 'Design Flow (cfs)', 'Cost ($)', dynamic_type='Function of Design Flow')
    
    #From USBR
    #k = hl/(v^2 / 2g)
    #h1 = k*v^2/(2g)
    #h1 = (k/2g) * (Q)^2 * (fractional_open_area * A)^-2
    k = 0.975
    frac_open_area = 0.50
    g = 32.1
    head_loss_eq = mc.Equation('Velocity Head Loss', 'Multi-Power', [(k/(2*g)), 2, -2, 0], 'Flow (cfs)', 'Head Loss (ft)', z_label='Active Area (ft2)', dynamic_type='Function of Active Area and Op. Flow')
    screen_angle = 40.64
    #cos(angle) = Module Width/Screen Width
    width_eq = mc.Equation('Screen Width', 'Linear', [(1/np.cos(np.deg2rad(screen_angle))), 0], 'Module Width (ft)', 'Screen Width (ft)', dynamic_type='Function of Module Width')
    
    out_dict = {'Name':'0.75in Fish Screen', \
                'Capital Cost':cap_cost,\
                'Annual Operating Cost':op_cost,\
                'Head Loss':head_loss_eq,\
                'Screen Width':width_eq, \
                'Screen Height':10, \
                'Fractional Open Area': frac_open_area, \
                'Vertical Angle': 90, \
                'Bottom Elevation':0}
    return out_dict      
