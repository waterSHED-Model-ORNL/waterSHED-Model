# -*- coding: utf-8 -*-
"""
Last updated on April 25 2022

@author: Colin Sasthav
"""
#%%## IMPORT PACKAGES
import module_classes as mc
import waterSHED_styles as styles
import math

#%%## Notes

#The following dynamic modules are subclasses of the SMH module classes from the module_classes file
#Instead of constant values for attribute, the attributes marked with _t can be an Equation object or a constant value
#Using an Equation allows the value of the attribute to change for defined site or project characteristics called the contolling variables
#The type of available control variables differs for each module class, since they have to be hard coded
#Each module will initialize the parent class with default values
#Each module also has thte following functions
##redesign_by_name - allows the model to recalculate the module attributes by providing a controlling variable name and value
##redesign - when provided all of the controlling variables, the module attributes are recalculated. The valid attribute is True if the redesign worked properly and is within the Equation bounds
#update_att - changes a specified attribute using the Equation object and the specified controlling variable values
#validate - checks if the redesign problem was successful

#%%## GENERATION DYNAMIC MODULES
class Dynamic_Generation(mc.Generation_module): #_t stands for tuple
    def __init__(self, module_name, capital_cost_t, operating_cost_t,\
                 width_t, length_t, design_flow_c, op_months,\
                     min_op_flow_t, max_op_flow_t, min_op_head_t, design_head_c, max_op_head_t,\
                         flow_eff_eq, head_eff_eq=None,nominal_power=None, max_power=None, cost_ss=None, diversion=False):
        
        self.full_name = module_name
        self.dynamic_class = 'Dynamic_Generation'
        self.cap_cost_t = capital_cost_t
        self.op_cost_t = operating_cost_t
        self.width_t = width_t
        self.length_t = length_t
        self.min_op_flow_t = min_op_flow_t
        self.max_op_flow_t = max_op_flow_t
        self.min_op_head_t = min_op_head_t
        self.max_op_head_t = max_op_head_t
        self.valid = True


        super().__init__(module_name, 1, 1, 1, 1, design_flow_c, op_months,\
                     0, 1, 0, design_head_c, 1, flow_eff_eq, head_eff_eq=head_eff_eq,nominal_power=nominal_power, max_power=max_power, cost_ss=cost_ss, diversion=diversion)
        self.control_vars_dict = {'Design Flow':self.design_flow, 'Design Head':self.design_head}
        self.redesign(design_flow_c, design_head_c)
        
        
    def redesign_by_name(self, att, val):
        if att == 'Design Head':
            self.redesign(self.design_flow, val)
        elif att == 'Design Flow':
            self.redesign(val, self.design_head)
        else:
            print('Unknown redesign parameter.')
        
    def redesign(self, flow, head):
        orig_flow = self.design_flow
        orig_head = self.design_head
        try:
            self.design_flow = flow
            self.design_head = head
            self.max_power = None
            new_nom_power = self.get_power(flow, head)
            new_cap_cost = self.update_att(self.cap_cost_t, flow, head, new_nom_power)
            new_op_cost = self.update_att(self.op_cost_t, flow, head, new_nom_power)
            new_width = self.update_att(self.width_t, flow, head, new_nom_power)
            new_length = self.update_att(self.length_t, flow, head, new_nom_power)
            new_min_op_flow = self.update_att(self.min_op_flow_t, flow, head, new_nom_power)
            new_max_op_flow = self.update_att(self.max_op_flow_t, flow, head, new_nom_power)
            new_min_op_head = self.update_att(self.min_op_head_t, flow, head, new_nom_power)
            new_max_op_head = self.update_att(self.max_op_head_t, flow, head, new_nom_power)

        
            if 'Error' not in [new_nom_power, new_cap_cost, new_op_cost, new_width, new_length, new_min_op_flow, new_max_op_flow, new_min_op_head,new_max_op_head]:
                self.nom_power = new_nom_power
                self.cap_cost = new_cap_cost
                self.op_cost = new_op_cost
                self.width = new_width
                self.length = new_length
                self.min_op_flow = new_min_op_flow
                self.max_op_flow = new_max_op_flow
                self.min_op_head = new_min_op_head
                self.max_op_head = new_max_op_head
                self.peak_eff_flow, self.peak_eff = self.get_peak_eff_flow()
                self.set_default_max_power()
                self.full_name = styles.format_value(self.nom_power, 'comma', 'kW') + ' ' + self.name
                self.update_data_list()
                self.valid = True
                
                return True
            else:
                self.design_flow = orig_flow
                self.design_head = orig_head
                self.valid = False
                return False
                        
        except:
            self.design_flow = orig_flow
            self.design_head = orig_head
            self.valid = False
            return False
    

    
    def update_att(self, att, flow, head, nom_power):
        if type(att) == mc.Equation:
            form = att.dynamic_type
        else:
            form = 'Constant'
            
        if form == 'Constant':
            out_val = att
        elif form == 'Function of Design Head':
            out_val = att.get_y(head)
        elif form == 'Function of Design Flow':
            out_val = att.get_y(flow)
        elif form == 'Function of Nominal Power':
            out_val = att.get_y(nom_power)    
        elif form == 'Function of Design Head and Nominal Power':
            out_val = att.get_y((head, nom_power))
        elif form == 'Function of Design Flow and Nominal Power':
            out_val = att.get_y((flow, nom_power))
        elif form == 'Function of Design Flow and Design Head':
            out_val = att.get_y((flow, head))
        if (type(out_val) == bool) and (out_val == False):
            out_val = 'Error'
        return out_val
        
    def validate(self):
        return self.valid

#%%## Dynamic Nonoverflow
class Dynamic_Nonoverflow(mc.Nonoverflow_module):
    def __init__(self, module_name, capital_cost_t, operating_cost_t, width, length_t, height_t):
        
        self.full_name = module_name
        self.dynamic_class = 'Dynamic_Nonoverflow'
        self.cap_cost_t = capital_cost_t
        self.op_cost_t = operating_cost_t
        self.length_t = length_t
        self.height_t = height_t
        self.valid = True
        self.volume = 1 #Temporary values
        self.design_nol = 10 #Temporary values


        super().__init__(module_name, 1, 1, width, 1) #Default 
        self.control_vars_dict = {'Volume':self.volume, 'Normal Operating Level':self.design_nol}
        self.redesign(self.design_nol)
                
    def redesign(self, nol):
        try:            
            new_height = self.update_att(self.height_t, nol)
            new_length = self.update_att(self.length_t, nol)
            new_volume = new_height * new_length * self.width
            new_cap_cost = self.update_att(self.cap_cost_t, nol, new_volume)
            new_op_cost = self.update_att(self.op_cost_t, nol, new_volume)
            
            if 'Error' not in [new_height, new_length, new_volume, new_cap_cost, new_op_cost]:
                self.design_nol = nol
                self.height = new_height
                self.length = new_length
                self.volume = new_volume
                self.cap_cost = new_cap_cost
                self.op_cost = new_op_cost
                self.full_name = styles.format_value(self.volume, 'comma', 'ft3') + ' ' + self.name
                self.update_data_list()
                self.valid = True                
                return True
            else:
                self.valid = False
                return False                        
        except:
            self.valid = False
            return False
    
    def update_att(self, att, nol, vol=None):
        if type(att) == mc.Equation:
            form = att.dynamic_type
        else:
            form = 'Constant'            
            
        if form == 'Constant':
            out_val = att
        elif form == 'Function of Volume':
            out_val = att.get_y(vol)
        elif form == 'Function of Normal Operating Level':
            out_val = att.get_y(nol)   
            
        if (type(out_val) == bool) and (out_val == False):
            out_val = 'Error'
        
        return out_val
        
    def validate(self):
        return self.valid

#%%## Dynamic Foundation
class Dynamic_Foundation(mc.Foundation_module): 
    def __init__(self, module_name, capital_cost_t, operating_cost_t, width, length, depth):
        
        self.full_name = module_name
        self.dynamic_class = 'Dynamic_Foundation'
        self.cap_cost_t = capital_cost_t
        self.op_cost_t = operating_cost_t
        self.depth = depth
        self.valid = True
        self.volume = width * length * depth

        super().__init__(module_name, 1, 1, width, length) #Default 
        self.control_vars_dict = {'Volume':self.volume, 'Depth':self.depth}
        self.redesign(self.depth)
    
    def redesign_by_name(self, att, val):
        if att == 'Depth':
            self.redesign(val)
        else:
            print('Unknown redesign parameter.')            
    
    def redesign(self, depth):
        try:            
            new_volume = self.width * self.length * depth
            new_cap_cost = self.update_att(self.cap_cost_t, depth, new_volume)
            new_op_cost = self.update_att(self.op_cost_t, depth, new_volume)
            
            if 'Error' not in [new_cap_cost, new_op_cost]:
                self.depth = depth
                self.volume = new_volume
                self.cap_cost = new_cap_cost
                self.op_cost = new_op_cost
                self.full_name = styles.format_value(self.depth, 'comma', 'ft') + ' ' + self.name
                self.update_data_list()
                self.valid = True                
                return True
            else:
                self.valid = False
                return False                        
        except:
            self.valid = False
            return False
    
    def update_att(self, att, depth, vol):
        if type(att) == mc.Equation:
            form = att.dynamic_type
        else:
            form = 'Constant'            
            
        if form == 'Constant':
            out_val = att
        elif form == 'Function of Depth':
            out_val = att.get_y(depth)
        elif form == 'Function of Volume':
            out_val = att.get_y(vol)  
        if (type(out_val) == bool) and (out_val == False):
            out_val = 'Error'
        return out_val
        
    def validate(self):
        return self.valid

#%%## Dynamic Recreation
class Dynamic_Recreation(mc.Recreation_module): 
    def __init__(self, module_name, capital_cost_t, operating_cost_t,\
                  width, length_t, design_flow_t, op_months,num_steps_t, steps_type,\
                      max_head_drop=None, max_head_rise=None, min_tail_ele=None, max_tail_ele=None, diversion=False):
        
        self.full_name = module_name
        self.dynamic_class = 'Dynamic_Recreation'
        self.cap_cost_t = capital_cost_t
        self.op_cost_t = operating_cost_t
        self.length_t = length_t
        self.design_flow_t = design_flow_t
        self.num_steps_t = num_steps_t
        self.steps_type = steps_type
        self.num_steps = 1#Temporary
        self.design_nol = 10#Temporary
        self.design_mdf = 1000#Temporary - design mean daily flow
        self.valid = True


        super().__init__(module_name, 1, 1, width, 1, 1, op_months, max_head_drop=max_head_drop, max_head_rise=max_head_rise, min_tail_ele=min_tail_ele, max_tail_ele=max_tail_ele, diversion=diversion) #Default 
        self.control_vars_dict = {'Normal Operating Level':self.design_nol, 'Mean Daily Flow':self.design_mdf}
        self.redesign(self.design_nol,self.design_mdf)
                
    def redesign(self, nol, mdf):
        try:            
            new_num_steps = self.update_att(self.num_steps_t, nol, mdf)
            if new_num_steps != 'Error':
                if self.steps_type == 'Round up':
                    new_num_steps = math.ceil(new_num_steps)
                elif self.steps_type == 'Round down':
                    new_num_steps = math.floor(new_num_steps)
            else:
                self.valid = False
                return
                    
            new_des_flow = self.update_att(self.design_flow_t, nol, mdf, new_num_steps)
            new_cap_cost = self.update_att(self.cap_cost_t, nol, mdf, new_num_steps)
            new_op_cost = self.update_att(self.op_cost_t, nol, mdf, new_num_steps)
            new_length = self.update_att(self.length_t, nol, mdf, new_num_steps)
            
            if 'Error' not in [new_des_flow, new_cap_cost, new_op_cost, new_length]:
                self.num_steps = new_num_steps
                self.design_nol = nol
                self.design_mdf = mdf
                self.design_flow = new_des_flow
                self.cap_cost = new_cap_cost
                self.op_cost = new_op_cost
                self.length = new_length
                self.full_name = styles.format_value(self.num_steps, 'comma', 'step') + ' ' + self.name
                self.update_data_list()
                self.valid = True                
                return True
            else:
                self.valid = False
                return False                        
        except:
            self.valid = False
            return False
    
    def update_att(self, att, nol, mdf, num_steps=None):
        if type(att) == mc.Equation:
            form = att.dynamic_type
        else:
            form = 'Constant'            
            
        if form == 'Constant':
            out_val = att
        elif form == 'Function of Mean Daily Flow':
            out_val = att.get_y(mdf)
        elif form == 'Function of Normal Operating Level':
            out_val = att.get_y(nol)  
        elif form == 'Function of Number of Steps':
            out_val = att.get_y(num_steps)
            
        if (type(out_val) == bool) and (out_val == False):
            out_val = 'Error'
            
        return out_val
        
    def validate(self):
        return self.valid

#%%## Dynamic Fish
class Dynamic_Fish(mc.Fish_module): 
    def __init__(self, module_name, capital_cost_t, operating_cost_t,\
                  width, length_t, design_flow_t, op_months,num_steps_t, steps_type,\
                      max_head_drop=None, max_head_rise=None, min_tail_ele=None, max_tail_ele=None, diversion=False):
        
        self.full_name = module_name
        self.dynamic_class = 'Dynamic_Fish'
        self.cap_cost_t = capital_cost_t
        self.op_cost_t = operating_cost_t
        self.length_t = length_t
        self.design_flow_t = design_flow_t
        self.num_steps_t = num_steps_t
        self.steps_type = steps_type
        self.num_steps = 1#Temporary
        self.design_nol = 10#Temporary
        self.design_mdf = 1000#Temporary - design mean daily flow
        self.valid = True

    
        super().__init__(module_name, 1, 1, width, 1, 1, op_months, max_head_drop=max_head_drop, max_head_rise=max_head_rise, min_tail_ele=min_tail_ele, max_tail_ele=max_tail_ele, diversion=diversion) #Default 
        self.control_vars_dict = {'Normal Operating Level':self.design_nol, 'Mean Daily Flow':self.design_mdf}
        self.redesign(self.design_nol,self.design_mdf)
                
    def redesign(self, nol, mdf):
        try:            
            new_num_steps = self.update_att(self.num_steps_t, nol, mdf)
            if new_num_steps != 'Error':
                if self.steps_type == 'Round up':
                    new_num_steps = math.ceil(new_num_steps)
                elif self.steps_type == 'Round down':
                    new_num_steps = math.floor(new_num_steps)
            else:
                self.valid = False
                return
                    
            new_des_flow = self.update_att(self.design_flow_t, nol, mdf, new_num_steps)
            new_cap_cost = self.update_att(self.cap_cost_t, nol, mdf, new_num_steps)
            new_op_cost = self.update_att(self.op_cost_t, nol, mdf, new_num_steps)
            new_length = self.update_att(self.length_t, nol, mdf, new_num_steps)
            
            if 'Error' not in [new_des_flow, new_cap_cost, new_op_cost, new_length]:
                self.num_steps = new_num_steps
                self.design_nol = nol
                self.design_mdf = mdf
                self.design_flow = new_des_flow
                self.cap_cost = new_cap_cost
                self.op_cost = new_op_cost
                self.length = new_length
                self.full_name = styles.format_value(self.num_steps, 'comma', 'step') + ' ' + self.name
                self.update_data_list()
                self.valid = True                
                return True
            else:
                self.valid = False
                return False                        
        except:
            self.valid = False
            return False
    
    def update_att(self, att, nol, mdf, num_steps=None):
        if type(att) == mc.Equation:
            form = att.dynamic_type
        else:
            form = 'Constant'            
            
        if form == 'Constant':
            out_val = att
        elif form == 'Function of Mean Daily Flow':
            out_val = att.get_y(mdf)
        elif form == 'Function of Normal Operating Level':
            out_val = att.get_y(nol)  
        elif form == 'Function of Number of Steps':
            out_val = att.get_y(num_steps)
            
        if (type(out_val) == bool) and (out_val == False):
            out_val = 'Error'
            
        return out_val
        
    def validate(self):
        return self.valid

#%%## Dynamic Water
class Dynamic_Water(mc.Water_module): 
    def __init__(self, module_name, capital_cost_t, operating_cost_t,\
                  width, length, design_flow_t, op_months,\
                      operating_mode, weir_coefficient=-1, crest_height_t=-1, diversion=False):
        
        self.full_name = module_name
        self.dynamic_class = 'Dynamic_Water'
        self.cap_cost_t = capital_cost_t
        self.op_cost_t = operating_cost_t
        self.design_flow_t = design_flow_t
        self.crest_height_t = crest_height_t
        self.design_nol = 10#Temporary
        self.valid = True

    
        super().__init__(module_name, 1, 1,\
                  width, length, 1, op_months,\
                      operating_mode, weir_coefficient=weir_coefficient, crest_height=1, diversion=diversion) #Default 
        self.control_vars_dict = {'Normal Operating Level':self.design_nol}
        self.redesign(self.design_nol)
                
    def redesign(self, nol):
        try:         
            new_cap_cost = self.update_att(self.cap_cost_t, nol)
            new_op_cost = self.update_att(self.op_cost_t, nol)
            new_design_flow = self.update_att(self.design_flow_t, nol)
            if self.crest_height_t is not None:    
                new_crest_height = self.update_att(self.crest_height_t, nol)
            else:
                new_crest_height = None
                

            if 'Error' not in [new_cap_cost, new_op_cost, new_design_flow, new_crest_height]: 
                self.design_nol = nol
                self.cap_cost = new_cap_cost
                self.op_cost = new_op_cost
                self.design_flow = new_design_flow
                self.crest_height = new_crest_height
                self.full_name = styles.format_value(self.design_flow, 'comma', 'cfs') + ' ' + self.name
                self.update_data_list()
                self.valid = True                
                return True
            else:
                self.valid = False
                return False                        
        except:
            self.valid = False
            return False
    
    def update_att(self, att, nol):
        if (type(att) == mc.Equation) or (type(att) == mc.PiecewiseEquation): #Add the piecewise check to all of them
            form = att.dynamic_type
        else:
            form = 'Constant'            
            
        if form == 'Constant':
            out_val = att
        elif form == 'Function of Normal Operating Level':
            out_val = att.get_y(nol)   
            
        if (type(out_val) == bool) and (out_val == False):
            out_val = 'Error'
        return out_val
        
    def validate(self):
        return self.valid

#%%## Dynamic Sediment
class Dynamic_Sediment(mc.Sediment_module): 
    def __init__(self, module_name, capital_cost_t, operating_cost_t,\
                 width, length, design_flow_t, op_months,\
                     operating_mode,operating_flow_t=None, operating_duration=None, operating_frequency=None, diversion=False):
        
        self.full_name = module_name
        self.dynamic_class = 'Dynamic_Sediment'
        self.cap_cost_t = capital_cost_t
        self.op_cost_t = operating_cost_t
        self.design_flow_t = design_flow_t
        self.op_flow_t = operating_flow_t
        self.design_mdf = 1000 #Temporary
        self.valid = True

    
        super().__init__(module_name, 1, 1,\
                 width, length, 1, op_months,\
                     operating_mode,1, operating_duration=operating_duration, operating_frequency=operating_frequency, diversion=diversion) #Default 
        self.control_vars_dict = {'Mean Daily Flow':self.design_mdf}
        self.redesign(self.design_mdf)
                
    def redesign(self, mdf):
        try:        
            
            new_cap_cost = self.update_att(self.cap_cost_t, mdf)
            new_op_cost = self.update_att(self.op_cost_t, mdf)
            new_design_flow = self.update_att(self.design_flow_t, mdf)
            if self.op_flow_t is not None:    
                new_op_flow = self.update_att(self.op_flow_t, mdf)
            else:
                new_op_flow = None
                

            if 'Error' not in [new_cap_cost, new_op_cost, new_design_flow, new_op_flow]: 
                self.design_mdf = mdf
                self.cap_cost = new_cap_cost
                self.op_cost = new_op_cost
                self.design_flow = new_design_flow
                self.op_flow = new_op_flow
                self.full_name = styles.format_value(self.design_flow, 'comma', 'cfs') + ' ' + self.name
                self.update_data_list()
                self.valid = True                
                return True
            else:
                self.valid = False
                return False                        
        except:
            self.valid = False
            return False
    
    def update_att(self, att, mdf):
        if type(att) == mc.Equation:
            form = att.dynamic_type
        else:
            form = 'Constant'            
            
        if form == 'Constant':
            out_val = att
        elif form == 'Function of Mean Daily Flow':
            out_val = att.get_y(mdf)    
            
        if (type(out_val) == bool) and (out_val == False):
            out_val = 'Error'
        return out_val
        
    def validate(self):
        return self.valid
