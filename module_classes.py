# -*- coding: utf-8 -*-
"""
Last updated on April 25 2022

@author: Colin Sasthav
"""
#%%## IMPORT PACKAGES
from copy import deepcopy
from matplotlib.patches import Rectangle
import pandas as pd
import math
import matplotlib.pyplot as plt
import matplotlib.ticker as plticker
import numpy as np
import random
import statistics as stats
import waterSHED_styles as sty
import aux_functions as af
import time
import itertools
#%%## Plot Styles
MODULE_COLORS = sty.MODULE_COLORS

#%%## SMH PROJECT CLASS - compiles all the objects need to create and simulate a facility
class SMH_project:
    def __init__(self, site, costs, facility_prefs, mod_lib, species_list=None):
        self.site = site
        self.costs = costs
        self.fac_prefs = facility_prefs
        self.mod_lib = mod_lib
        self.species_list = species_list
        self.cl = ['Gen', 'Wat', 'Sed', 'Fish', 'Fou', 'Rec', 'Non', 'Spill']
        
    #Changes a given attribute so that a new facility can be created
    def set_enum_params(self, req_mods_dict, pass_mods_list, pass_mods_counts, spill_mod_count, mod_name, att_name, att_val):
        if att_name == 'Module Count': #Set the module counts for constant cases
            if mod_name == req_mods_dict['Spill'].name:
                spill_mod_count = att_val
            else:
                for j in range(0, len(pass_mods_list)):
                    if pass_mods_list[j].name == mod_name:
                        pass_mods_counts[j] = att_val
                        break
        else:  #Redesign dynamic modules for the constant cases
            if mod_name == req_mods_dict['Spill'].name: #If redesigning the spillway mod
                req_mods_dict['Spill'].redesign_by_name(att_name, att_val)
                if req_mods_dict['Spill'].validate() == False: #If there is an error during redesign, stop enumeration
                    return False, False, False, False
            elif mod_name == req_mods_dict['Foundation'].name: #If redesigning the foundation mod
                req_mods_dict['Foundation'].redisgn_by_name(att_name, att_val)
                if req_mods_dict['Foundation'].validate() == False: #If there is an error during redesign, stop enumeration
                    return False, False, False, False
            else:
                for j in range(0, len(pass_mods_list)): #If redesigning another module type
                    if pass_mods_list[j].name == mod_name:
                        if (pass_mods_list[j].module_class == 'Gen') and (att_name == 'Design Flow'): #If generation module using enumeration, want to divide the design flow by the number of modules
                            if pass_mods_counts[j] > 0: 
                                pass_mods_list[j].redesign_by_name(att_name, att_val/pass_mods_counts[j]) #Divide the initial design flow setting by the number of modules, this assumes the module count has already been set
                            else:
                                pass_mods_list[j].redesign_by_name(att_name, att_val)
                            break
                        else:    
                            pass_mods_list[j].redesign_by_name(att_name, att_val)
                        break
                if pass_mods_list[j].validate() == False: #If there is an error during redesign, stop enumeration
                    return False, False, False, False
        return req_mods_dict, pass_mods_list, pass_mods_counts, spill_mod_count
    
    #Sets the attributes that are not changed through the enumeration process
    def set_noniterable_parameters(self, req_mods_dict, pass_mods_list):
        maf = self.site.daily_inflow.get_mean_daily_flow()
        nol = self.fac_prefs.nol
        if req_mods_dict['Non-overflow'].is_dynamic():
            req_mods_dict['Non-overflow'].redesign(nol)
        if req_mods_dict['Spill'].is_dynamic():
            req_mods_dict['Spill'].redesign(nol)
        if req_mods_dict['Flushing'] is not None:
            if req_mods_dict['Flushing'].is_dynamic():
                req_mods_dict['Flushing'].redesign(maf)
        
        for i in pass_mods_list:
            if i.is_dynamic():
                if i.module_class == 'Sed':
                    i.redesign(maf)
                elif i.module_class == 'Wat':
                    i.redesign(nol)
                elif i.module_class == 'Rec':
                    i.redesign(nol, maf)
                elif i.module_class == 'Fish':
                    i.redesign(nol, maf)
        return req_mods_dict, pass_mods_list
    
    #Run the enumeration by trying all attribute combinations, creating facilities, simulating them, and keeping the highest objective
    def enumeration_optimization(self, objective, enum_lists,save_bools, show_anim=False):
        if show_anim == True:
            fig = None
            ax = None
            plt.close('all')
        
        #enum_dicts = [req_mods_dict,pass_mods_list,const_dict, enum_dict]
        req_mods_dict = enum_lists[0] #{'Foundation':mod, 'Non-overflow':mod, 'Spill': mod, 'Flushing': mod or None}
        pass_mods_list = enum_lists[1] #[mod, mod, mod, ...]
        const_list = enum_lists[2] #each element = [Mod name, attribute, number] 
        enum_list = enum_lists[3] #each element = [mod name, attribute, [iters]]
        screen_bool_dict = enum_lists[4] #Screen name: True or False
        pass_mods_counts = [0 for i in range(0, len(pass_mods_list))]
        spill_mod_count = 1
        
        req_mods_dict, pass_mods_list = self.set_noniterable_parameters(req_mods_dict, pass_mods_list)
        
        #Set constant values
        for i in const_list:
            req_mods_dict, pass_mods_list, pass_mods_counts, spill_mod_count = self.set_enum_params(req_mods_dict, pass_mods_list, pass_mods_counts, spill_mod_count,i[0], i[1], i[2])
            if req_mods_dict is False:
                return False
        #Set the initial module counts and parameters to the first enum case
        for i in enum_list:
            req_mods_dict, pass_mods_list, pass_mods_counts, spill_mod_count = self.set_enum_params(req_mods_dict, pass_mods_list, pass_mods_counts, spill_mod_count,i[0], i[1], i[2][0])
            if req_mods_dict is False:
                return False

        #Get screen list
        screens_list = []
        for i in range(0, len(self.mod_lib.screens_list)):
            if self.mod_lib.screens_list[i].name in list(screen_bool_dict.keys()):
                if screen_bool_dict[self.mod_lib.screens_list[i].name] == True:                
                    screens_list.append(self.mod_lib.screens_list[i])
        
        #Set the objective
        if objective in ['LCOE ($/MWh)', 'ICC ($)','Unit Cost ($/kW)']:
            maximize = False
            best_obj = 1000000000000
        else:
            maximize = True
            best_obj = -1000000000000
            
            
        results_df = pd.DataFrame()
        best_fac = None
        best_sim_res = None
        counter = 1
        iter_lists = [i[2] for i in enum_list]
        for att_vals in itertools.product(*iter_lists): #Loop through all attribute iteration combinations
            time_start = time.perf_counter()
            for i in range(0, len(enum_list)):
                req_mods_dict, pass_mods_list, pass_mods_counts, spill_mod_count = self.set_enum_params(req_mods_dict, pass_mods_list, pass_mods_counts, spill_mod_count,enum_list[i][0], enum_list[i][1], att_vals[i])
                if req_mods_dict is False:
                    return False
            run_name = 'Enum {}'.format(counter)
            #Create a facility with enumerated attributes
            fac = Facility(run_name, self, pass_mods_list, pass_mods_counts, req_mods_dict['Spill'], spill_mod_count, req_mods_dict['Non-overflow'], req_mods_dict['Foundation'], req_mods_dict['Flushing'], screens=screens_list)
            #Evaluate the facility
            sim_res = self.evaluate(fac)
            time_end = time.perf_counter()
            sim_res.add_time(round(time_end - time_start, 2))
            if sim_res is False:
                print('Unable to simulate iteration: {}'.format(run_name))
            else:
                #Save the objectives and input values
                results_dict = sim_res.get_run_dict(*save_bools) 
                results_dict['Enumeration Objective'] = sim_res.obj_dict[objective]
                results_dict['Input Values'] = att_vals
                temp_df = pd.DataFrame.from_dict(results_dict, orient='index', columns=[run_name]).reset_index()
                temp_df.rename(columns={'index':'Metric'},inplace=True)
                if len(results_df) <= 0:
                    results_df = temp_df
                else:
                    results_df = pd.merge(results_df, temp_df, on='Metric', sort=False, how='outer')
                        
                #Find and save if the new results is better the previous best
                if maximize == True:
                    if sim_res.obj_dict[objective] > best_obj:
                        best_obj = sim_res.obj_dict[objective]
                        best_fac = deepcopy(fac)
                        best_sim_res = sim_res
                else:
                    if sim_res.obj_dict[objective] < best_obj:
                        best_obj = sim_res.obj_dict[objective]
                        best_fac = deepcopy(fac) 
                        best_sim_res = sim_res
                        
                if show_anim ==True:
                    fig, ax = fac.plot_facility(fig=fig, ax=ax, it=counter, obj=fac.get_latest_objective(objective, formatted=True))
            counter +=1
        return [best_fac, best_sim_res, results_df]
    
    #Use the custom genetic algorithm to optimize the module combinations and attributes
    def optimize(self, objective, constraints, enum_lists, iterations=5, population_size=9, best_count=3, mutate_count=3, random_count=3, cross_num=3, show_anim = False, print_results=True):
        if show_anim == True:
            fig = None
            ax = None
            plt.close('all')
        
        #enum_lists[0] = req_mods_dict, enum_lists[1] = pass_mods_list
        enum_lists[0], enum_lists[1] = self.set_noniterable_parameters(enum_lists[0], enum_lists[1])
        
        #Get screen list
        #enum_lists[4] = screen_bool_dict = {'Screen name': True or False}
        screens_list = []
        for i in range(0, len(self.mod_lib.screens_list)):
            if self.mod_lib.screens_list[i].name in list(enum_lists[4].keys()):
                if enum_lists[4][self.mod_lib.screens_list[i].name] == True:                
                    screens_list.append(self.mod_lib.screens_list[i])
        enum_lists[4] = screens_list
        
        #Create a population of possible solutions
        popu = Population(self, objective, constraints, enum_lists, population_size) 
        
        if popu.valid == False:
            return 'Error when designing modules. The dynamic modules can become invalid with the iteration paramaters.'
        
        #### GA Loop
        for i in range(0, iterations):#Run for a specified number of iterations
            for j in range(0, len(popu.fac_list)):
                #Evaluate each facility in the population
                self.evaluate(popu.fac_list[j])
            popu.get_obj_ranks()
            #Display results
            if print_results == True:
                print('\nIteration {}'.format(i))
                popu.print_results()
            if show_anim ==True:
                best_fac = popu.get_optimal_facs(count=1)[0]
                fig, ax = best_fac.plot_facility(fig=fig, ax=ax, it=i, obj=best_fac.get_latest_objective(objective, formatted=True))
            
            #Evolve population
            if i != iterations - 1:
                popu.evolve(i, best=best_count, mutate=mutate_count, random_num=random_count, cross_num=cross_num)
        return popu.get_optimal_facs(count=1)

    #Evaluate the facility by setting up a simulation and gathering the simulation results
    def evaluate(self, fac):
        start_date = self.fac_prefs.test_start
        end_date = self.fac_prefs.test_end
        inflows = self.site.daily_inflow.get_flow_subset(start_date, end_date)
        op_outs = self.simulate_operation(fac, inflows['Discharge (cfs)'])
        if op_outs is not False:
            sim_res = SimResults(self, fac, inflows, *op_outs)
            fac.add_simulation_results(sim_res)
            return sim_res
        else:
            fac.add_simulation_results(False)
            return False
        
    #Simulates daily facility operation using a time series of inflows
    def simulate_operation(self, fac, flows):
        pass_allos = np.zeros((len(fac.rule_curve),len(flows)))
        spill_allos = np.zeros(len(flows))
        flush_allos = np.zeros(len(flows))
        over_allos = np.zeros(len(flows))
        flush_idx = []
        
        if fac.flush_mod is not None:
            flush_idx = fac.flush_mod.get_flushing_indices(flows)
        
        #Initialize headwaters and tailwaters
        tail_eles = [self.site.get_tailwater_depth(i) for i in flows]
        hwater_eles = [[self.fac_prefs.nol for i in range(0, len(fac.rule_curve))]for j in range(0, len(flows))]
        spill_hwaters = [self.fac_prefs.nol for i in range(0, len(flows))]
        
        #Calculate the notch flows
        if self.fac_prefs.notch_flow == 0.0:
            notch_flows = [0.0 for i in flows]
        else:
            notch_flows = [min(self.fac_prefs.notch_flow, i) for i in flows]
        
        #Calculate the minimum flows for each day ahead of time
        if self.fac_prefs.spill_min_flow == 0.0:
            spill_min_flows = [0.0 for i in flows]
        else:
            if self.fac_prefs.min_flow_type == '% (Percent of inflow)':
                #If the min flow is greater than notch flow, allocate required flow to meet minimum, otherwise set to zero
                spill_min_flows = [max((self.fac_prefs.spill_min_flow/100)*flows[i] - notch_flows[i], 0) for i in range(0, len(flows))]
            else:
                # spill_min_flows = [min(self.fac_prefs.spill_min_flow, i) for i in flows]
                spill_min_flows = [min(max((self.fac_prefs.spill_min_flow - notch_flows[i], 0)), flows[i] - notch_flows[i]) for i in range(0, len(flows))]
                
        for i in range(0, len(flows)):#For each day in the simulation
            if i in flush_idx: #If flushing day
                flush_allos[i] = flows[i]
            else: #If not flushing day
                if (fac.spill_mod.op_mode == 'Controlled Spillway') and (fac.has_screens==False): #Controlled = constant head
                    # hwater_eles.append(self.fac_prefs.nol)
                    allos, spill, over, head_constrained_idx = self.allocate_pass_day(flows[i], flows.index[i], fac, tail_eles[i],spill_min_flows[i], notch_flows[i], hwater_eles[i])
                    pass_allos[:,i] = allos
                    spill_allos[i] = spill
                    over_allos[i] = over
                else: #Uncontrolled spillway or has screens, meaning the head is going to change based on operation
                    #Allocate flows ignoring head constraints to calculate expected spillflow
                    allos, spill, over, head_constrained_idx = self.allocate_pass_day(flows[i],flows.index[i], fac, tail_eles[i], spill_min_flows[i], notch_flows[i]) 
                    temp_hwaters, temp_spillh = self.get_headwaters(fac, allos, spill, notch_flows[i])                    
                    allos, spill, over, head_constrained_idx = self.allocate_pass_day(flows[i],flows.index[i], fac, tail_eles[i], spill_min_flows[i],notch_flows[i], temp_hwaters)                    
                    check_hwaters, temp_spillh2 = self.get_headwaters(fac, allos, spill, notch_flows[i])
                    
                    if (len(head_constrained_idx) == 0) and (temp_hwaters == check_hwaters): #If the allocation works the first time without head constraint issues and consistent headwaters
                        pass_allos[:,i] = allos
                        spill_allos[i] = spill
                        over_allos[i] = over
                        hwater_eles[i] = check_hwaters
                        spill_hwaters[i] = temp_spillh
                    else: #If a module is turned off due to head fluctuations
                        for j in range(0, len(fac.rule_curve)): #Try to resolve head constraints up to a limit of all modules
                            temp_hwaters = check_hwaters.copy()
                            #turns off modules until the head constraints is resolved
                            allos, spill, over, head_constrained_idx = self.allocate_pass_day(flows[i],flows.index[i], fac, tail_eles[i], spill_min_flows[i],notch_flows[i], temp_hwaters, head_constrained_idx)
                            check_hwaters, temp_spillh = self.get_headwaters(fac, allos, spill, notch_flows[i])
                            
                            if (len(head_constrained_idx) == 0) and (temp_hwaters == check_hwaters):
                                pass_allos[:,i] = allos
                                spill_allos[i] = spill
                                over_allos[i] = over
                                hwater_eles[i] = check_hwaters
                                spill_hwaters[i] = temp_spillh
                                break
                            
                        if len(head_constrained_idx) > 0:
                            print('Error unable to resolve head constraints')
                            return False

        return pass_allos, spill_allos, over_allos, flush_allos, hwater_eles, spill_hwaters, tail_eles
                
    #Calculates the headwater elevation based on the type of spillway and spillway flow
    def get_headwaters(self, fac, allos, spill, notch_flow):
        if fac.spill_mod.op_mode == 'Controlled Spillway': #Controlled spillways assume constant headwater levels
            spill_head = self.fac_prefs.nol
        else:
            spill_head = fac.get_headwater_elevation(spill - notch_flow)
        
        #If there is a screen, then the head may be different across each module, so must account for screen head losses
        pass_hwaters = [spill_head for i in fac.rule_curve]
        if fac.has_screens:
            for j in range(0, len(fac.screens)): #For each screen
                screen_flow = 0
                for i in range(0, len(fac.rule_curve)): #Calculate total flow through screen
                    if fac.screens[j].check_covered(fac.rule_curve[i][0].name):
                        screen_flow += allos[i]
                for i in range(0, len(fac.rule_curve)): #Recalculate headwater for each covered module based on screen flow
                    if fac.screens[j].check_covered(fac.rule_curve[i][0].name):
                        pass_hwaters[i] = fac.screens[j].calculate_head_after_loss(screen_flow, pass_hwaters[i])
        return pass_hwaters, spill_head
        
    #Uses rule-based allocation to allocate flow across the passage modules
    def allocate_pass_day(self, flow, date, fac, tail, spill_min_flow, notch_flow, hwaters=None, off_rule_idx=[]): #If head equals None, then ignore head constraints
        rule_curve = fac.rule_curve    
        allos = np.zeros(len(rule_curve))
        month = date.month
        spill_flow = spill_min_flow + notch_flow
        head_constrained_idx = []
        if hwaters is not None:
            hwater_diffs = [self.fac_prefs.nol - i for i in hwaters]
            gross_heads = [i - tail for i in hwaters]
            
        i = 0
        while i < len(rule_curve): #Loops through all modules, although generaiton modules are all allocated at once
            spent_flow = sum(allos) + spill_flow
            if i not in off_rule_idx: #If module is not set to be turned off due to headwater constraint
                if spent_flow < flow: #Stop when all flow has been allocated
                    mod = rule_curve[i][0]
                    if mod.on_month(month): #module must be on to allocate flow
                        if mod.module_class == 'Sed': 
                            if mod.op_mode == 'Sluicing':
                                if flow >= mod.op_flow:
                                    if flow - spent_flow >= mod.design_flow:
                                        allos[i] = mod.design_flow
                            elif mod.op_mode == 'Continuous':
                                if flow - spent_flow >= mod.design_flow:
                                        allos[i] = mod.design_flow
                            else:
                                print('Incorrect sediment module operating mode')
                        elif mod.module_class == 'Gen':
                            #Check if gen mods are on                           
                            gen_mods_on = [True for j in range(0, fac.num_gen)]
                            for m in range(0, fac.num_gen):
                                if fac.gen_mods[m].on_month(month) == False:
                                    gen_mods_on[m] = False
                                elif hwaters is not None:
                                    if fac.gen_mods[m].check_head(gross_heads[i]) == False: #If outside of head range
                                        gen_mods_on[m] = False
                            #Get the generation allocation
                            avail_flow = math.floor(flow - spent_flow)
                            gen_allos = fac.get_gen_allocation(avail_flow, gen_mods_on, self.fac_prefs.allow_overrun)
                            for j in range(0, fac.num_gen):
                                allos[i+j] = gen_allos[j]
                            i += fac.num_gen - 1 #skips the rest of the generation modules

                        elif mod.module_class == 'Wat': #This is for continuous water passage modules, not spillways
                            if flow - spent_flow >= mod.design_flow:
                                allos[i] = mod.design_flow
                            else: 
                                allos[i] = flow - spent_flow                              
                        elif (mod.module_class == 'Fish') or (mod.module_class == 'Rec'):
                            if hwaters is None: #If no head constraints
                                if mod.check_tailwater_elevation(tail) == True: #If within tail constraints
                                    if flow - spent_flow >= mod.design_flow: #If design flow available
                                        allos[i] = mod.design_flow
                            else: #If head constraints
                                if (mod.check_head(hwater_diffs[i]) == True):
                                    if mod.check_tailwater_elevation(tail)==True: #If outside of head range
                                        if flow - spent_flow >= mod.design_flow: #If design flow available
                                            allos[i] = mod.design_flow
                                else: #if in head range
                                    head_constrained_idx.append(i)
                        else:
                            print('Unknown module type')
            i+=1
        spent_flow = sum(allos) + spill_flow            
        if spent_flow < flow: 
            if flow - spent_flow > fac.total_spill_cap - spill_flow: #If too much flow for spillway
                spill_flow = fac.total_spill_cap
                over_flow = flow - sum(allos) - fac.total_spill_cap
            else: #Spill all
                spill_flow += flow - spent_flow
                over_flow = 0
        elif spent_flow > flow:
            over_flow = 0
            print('Error - flow allocated improperly - Inflow: {}, Spent Flow {}'.format(flow, spent_flow))
        else:
            over_flow = 0
        
        return allos, spill_flow, over_flow, head_constrained_idx
    
#%%## POPULATION CLASS - stores a list of facilities for the genetic algorithm and facilitates evolution
class Population:
    def __init__(self, proj, objective, constraints, enum_lists, pop_size, fac_list=None):
        self.proj = proj
        self.mod_lib = proj.mod_lib
        self.objective = objective
        self.constraints =  constraints #List in form [constraint type (i.e. Module Count or Performance Requirement), subject (i.e. Module or Performance Metric), conditional, value]
        self.req_mods_dict, self.pass_mods_list, self.const_list, self.iter_list, self.screens_list = enum_lists
        self.size = pop_size
        
        #Tries to create an initial population, and sets self.valid to False if it doesn't work
        try:
            self.default_fac = self.get_default_fac() #Uses a default facility to set the constant modules and attributes
            if fac_list == None:
                self.fac_list = []
                self.valid = self.get_initial_pop() #Returns true if the initial population was created successfully
            else:
                self.fac_list = fac_list #A facility list can be provided if desired
                self.size = len(fac_list)
            self.update()
        except:
            self.valid=False

    #Resets/initializes the rankings and objective
    def update(self):
        self.size = len(self.fac_list)
        self.obj_list = [None] * self.size
        self.ranks = [None] * self.size
        if self.objective in ['LCOE ($/MWh)', 'ICC ($)','Unit Cost ($/kW)']:
            self.maximize = False
            self.penalty = 10000000
        else:            
            self.maximize = True
            self.penalty = -10000000
        
    #The default facility includes all the modules and attributes that must be included in the facility
    def get_default_fac(self):
        pass_mods = []
        pass_mod_counts = []
        spill_mod_count = 0
        spill_mod_name = self.req_mods_dict['Spill'].name
                
        #Go through constant list
        #const_list = [mod name, attribute, number]
        for i in range(0, len(self.const_list)):
            mod_name = self.const_list[i][0]
            att = self.const_list[i][1]
            num = self.const_list[i][2]
            if att == 'Module Count': #Set the module counts
                if mod_name == spill_mod_name:
                    spill_mod_count = num
                else:
                    for j in self.pass_mods_list:
                        if j.name == mod_name:
                            if num > 0:
                                pass_mods.append(j)
                                pass_mod_counts.append(num)
                            break
            else: #set constant dynamic module attributes
                if mod_name == spill_mod_name:
                    self.req_mods_dict['Spill'].redesign_by_name(att, num)
                    if self.req_mods_dict['Spill'].validate() == False: #If there is an error during redesign, stop enumeration
                        return False
                elif mod_name == self.req_mods_dict['Foundation'].name:
                    self.req_mods_dict['Foundation'].redisgn_by_name(att, num)
                    if self.req_mods_dict['Foundation'].validate() == False: #If there is an error during redesign, stop enumeration
                        return False
                else:
                    for j in self.pass_mods_list:
                        if j.name == mod_name:
                            j.redesign_by_name(att, num)                            
                            if j.validate() == False: #If there is an error during redesign, stop enumeration
                                return False
                            break
                             
        #Go through ranges and set the default facility as the minimum
        #iter_list = [mod name, att, [min, max]]
        for i in range(0, len(self.iter_list)):
            mod_name = self.iter_list[i][0]
            att = self.iter_list[i][1]
            num = self.iter_list[i][2][0] #Minimum of range
            if att == 'Module Count':
                if mod_name == spill_mod_name:
                    spill_mod_count = num
                else:
                    for j in self.pass_mods_list:
                        if j.name == mod_name:
                            if num > 0:
                                pass_mods.append(j) 
                                pass_mod_counts.append(num)
                            break
            else: #set dynamic module attribute minimums
                if mod_name == spill_mod_name:
                    self.req_mods_dict['Spill'].redesign_by_name(att, num)
                    if self.req_mods_dict['Spill'].validate() == False: #If there is an error during redesign, stop enumeration
                        return False
                elif mod_name == self.req_mods_dict['Foundation'].name:
                    self.req_mods_dict['Foundation'].redisgn_by_name(att, num)
                    if self.req_mods_dict['Foundation'].validate() == False: #If there is an error during redesign, stop enumeration
                        return False
                elif mod_name == self.req_mods_dict['Non-overflow'].name:
                    self.req_mods_dict['Non-overflow'].redisgn_by_name(att, num)
                    if self.req_mods_dict['Non-overflow'].validate() == False: #If there is an error during redesign, stop enumeration
                        return False
                elif self.req_mods_dict['Flushing'] is not None:
                    if mod_name == self.req_mods_dict['Flushing'].name:
                        self.req_mods_dict['Flushin'].redisgn_by_name(att, num)
                        if self.req_mods_dict['Flushing'].validate() == False: #If there is an error during redesign, stop enumeration
                            return False
                else:
                    for j in self.pass_mods_list:
                        if j.name == mod_name: 
                            j.redesign_by_name(att, num)                            
                            if j.validate() == False: #If there is an error during redesign, stop enumeration
                                return False
                            break
        #Create default facility
        default_fac = Facility('Default', self.proj, pass_mods, pass_mod_counts, self.req_mods_dict['Spill'], spill_mod_count,  self.req_mods_dict['Non-overflow'],  self.req_mods_dict['Foundation'],  self.req_mods_dict['Flushing'], self.screens_list)
        return default_fac

    #Add facility to the list
    def add_fac(self, fac):
        self.fac_list.append(fac)
        self.update()
        return self.fac_list     
    
    #Prints the results of the enumeration iteration to the screen
    def print_results(self):
        for i in range(0, len(self.ranks)):
            for f in range(0, len(self.fac_list)):
                if self.ranks[f] == i:
                    print('{}). {}: {}'.format(i+1, self.fac_list[f].name, self.obj_list[f]))
            
    #Returns a module for a given module name
    def get_mod_by_name(self, name):
        for i in self.pass_mods_list:
            if i.name == name:
                return i
        return False
    
    #Returns a random facility by using the default facility and getting random modules/attributes within the specified ranges
    def get_random_fac(self, name):
        fac = deepcopy(self.default_fac)
        fac.name = name
        #Set random module counts and attributes
        for i in self.iter_list:
            mod_name = i[0]
            att = i[1]
            min_range = i[2][0]
            max_range = i[2][1]
            mod = self.get_mod_by_name(mod_name)
            if mod is False:
                print('Trying to get module that does not exist.')
                break
            
            if att == 'Module Count': #Get a random module count
                rand_num = random.randint(min_range, max_range)
                fac.set_mod_count(mod, rand_num)
            else: #This assumes that modules are already in the facility (i.e. module count comes before other attributes, which I think they should)
                rand_num = random.random()
                rand_att = min_range + (rand_num*(max_range-min_range))
                fac_valid = fac.set_mod_att(mod, att, rand_att)
                if fac_valid == False:
                    print('Error - dynamic module is not valid.')
                    return False
        fac.update()
        return fac
            
    #Get an initial population by creating random facilities
    def get_initial_pop(self):
        for i in range(0, self.size):
            name = 'Iter 1, Rand {}'.format(i+1)
            new_fac = self.get_random_fac(name)
            if new_fac is False: #Tries twice to get a facility that is valid
                second_fac = self.get_random_fac(name)
                if second_fac is False:
                    return False #The module iteration parameters lead to invalid designs
            else:
                self.add_fac(self.get_random_fac(name))
        return True

    #Evolves the population by mutating, randomizing, crossing over, and keeping best based on the user specific parameters
    def evolve(self, iteration, best=2, mutate=2, random_num=2, cross_num=2):
        new_fac_list = []
        #Keep the best facilities
        best_facs = self.get_optimal_facs(count=best)
        for i in best_facs:
            new_fac_list.append(i)
        #Mutate - a random facility in population
        for i in range(0, mutate):
            mut_fac = self.mutate(self.fac_list[random.randint(0, len(self.fac_list)-1)])
            mut_fac.name = 'Iter {}, Muta {}'.format(iteration, i)
            new_fac_list.append(mut_fac)
        #Random - get a new random facility
        for i in range(0, random_num):
            name = 'Iter {}, Rand {}'.format(iteration, i)
            new_fac_list.append(self.get_random_fac(name))
        #Crossover - get new facility by crossing over mods from good facility to a random fac
        for i in range(0, cross_num):
            name = 'Iter {}, Cross {}'.format(iteration, i)
            cross_fac = self.fac_list[random.randint(0, len(self.fac_list)-1)]
            good_fac = best_facs[random.randint(0, len(best_facs)-1)]
            new_fac = self.crossover(cross_fac, good_fac)
            new_fac.name = name
            new_fac_list.append(new_fac)
        
        if len(self.fac_list) != len(new_fac_list):
            print('error')
        self.fac_list = new_fac_list
    
    #Return one module, takes modules from a good facility fac2 and gives it to another (cross_fac)
    def crossover(self, cross_fac, good_fac): 
        out_fac = deepcopy(cross_fac)
        possible_mod_names = []
        for i in self.iter_list:
            mod_name = i[0]
            if (mod_name in good_fac.pass_dict.keys()) and (mod_name not in possible_mod_names):
                possible_mod_names.append(mod_name)
        if len(possible_mod_names) <=0: #if good_fac has no pass mods, then return a random
            return self.get_random_fac()
        elif len(possible_mod_names) == 1:
            num_mod_cross = 1
            mod_indices = [0]
        else:
            num_mod_cross = random.randint(1, len(possible_mod_names)-1) #Pick up to the number of iter_list length of attributes to mutate
            mod_indices = [x for x in range(0, len(possible_mod_names)-1)]
            random.shuffle(mod_indices)
        
        for i in range(0, num_mod_cross):
            mod, count = good_fac.get_pass_mod(possible_mod_names[mod_indices[i]])
            out_fac.add_pass_mod(mod, count)
        out_fac.update()
        return out_fac
                
    #Creates a new facilitiy by random modifying the module counts and module attributes (must be within the specified ranges)
    def mutate(self, fac): #only works with passage modules
        result_fac = deepcopy(fac)
        #Randomly pick the number of attributes/modules to mutate
        if len(self.iter_list) == 1:
            num_att_mut = 1
            att_indices= [0]
        else:
            num_att_mut = random.randint(1, len(self.iter_list)-1) #Pick up to the number of iter_list length of attributes to mutate
            att_indices = [x for x in range(0, len(self.iter_list)-1)]
            random.shuffle(att_indices)
        #Randomly mutate the selected number of attributes/moduels
        for i in range(0, num_att_mut):
            mod_name, att, minmax_list = self.iter_list[att_indices[i]]
            mod = self.get_mod_by_name(mod_name)
            if att == 'Module Count':
                ran_count = random.randint(minmax_list[0], minmax_list[1])
                result_fac.set_mod_count(mod, ran_count)
            else:
                rand_num = random.random()
                rand_att = minmax_list[0] + (rand_num*(minmax_list[1]-minmax_list[0]))
                fac_valid = result_fac.set_mod_att(mod, att, rand_att)
                if fac_valid == False:
                    print('Error - dynamic module is not valid.')
                    return False
        result_fac.update()
        return result_fac
        
    #Checks if a value satisfies a constraint    
    def check_constraint(self, val, operand, req):
        try:
            if val is None:
                return False
            else:
                if operand == '>':
                    return val > req
                elif operand == '<':
                    return val < req
                elif operand == '<=':
                    return val <= req
                elif operand == '>=':
                    return val < req
                elif operand == '=':
                    return val == req
        except:
            return False
        
    #Return the list of objectives for each facility in the population
    #Applies constraints using a penalty function
    def get_obj_list(self): 
        obj_list = [fac.get_latest_objective(self.objective) for fac in self.fac_list] #Get objectives from the facilities
        for i in range(0, len(self.constraints)):
            for f in range(0, len(obj_list)):
                val = None
                #constraint = ['Performance Requirements' or 'Facility Design Parameters', Subject, operand, val]
                con_type, obj, operand, req = self.constraints[i]
                if con_type == 'Performance Requirements': #If performance constraint get the value from the obj_dict
                    val = self.fac_list[f].get_latest_sim_results().obj_dict[obj]    
                elif con_type == 'Facility Design Parameters': #If facility design constraint, get the corresponding facility attribute
                    if obj == 'Capacity (kW)':
                        val = self.fac_list[f].nameplate_cap
                    elif obj == 'Footprint (ft2)':
                        val = self.fac_list[f].footprint
                    elif obj == 'Spillway Width (ft)':
                        val = self.fac_list[f].total_spill_width
                    elif obj == 'Spillway Design Flood (cfs)':
                        val = self.fac_list[f].total_spill_cap
                if (val is None) or (val is False):
                    print('Error calculating constraint') 
                else:
                    if self.check_constraint(val, operand, req) == False:
                        obj_list[f] += self.penalty
        return obj_list
    
    #Ranks the objectives of each facility in the population
    #Returns a list with numbers corresponding to the rank of the self.fac_list
    def get_obj_ranks(self): #Creates a list with the ranks corresponding to the objective list
        ranks = [None] * len(self.obj_list)
        self.obj_list = self.get_obj_list() #Get objectives
        for i in range(0, len(self.obj_list)): #Go through list, if unable to simulate, then objective will be False, so need to set objective to infinitely bad obejective
            if self.obj_list[i] is False: #Account for errors
                if self.maximize==True:
                    self.obj_list[i] = -1*self.M
                else:
                    self.obj_list[i] = self.M
            
        #Sort list
        for i, x in enumerate(sorted(range(len(self.obj_list)), key=lambda y: self.obj_list[y])):
            if self.maximize==True:
                ranks[x] = (len(ranks)- 1) - i
            else:
                if x >= len(ranks):
                    print('error')
                else:
                    ranks[x] = i
        self.ranks = ranks
    
    #Returns a list of facilities with the best scores
    def get_optimal_facs(self, count=1): 
        opt_list = []
        for i in range(0, count):
            for j in range(0, len(self.fac_list)):
                if self.ranks[j] == i:
                    opt_list.append(self.fac_list[j])
        return opt_list
    

#%%## SIMULATION RESULTS - saves the results of the facility simulation and computes performance metrics
class SimResults:
    def __init__(self, proj, fac, inflows, pass_allos, spill_allos, over_allos, \
                 flush_allos, hwater_eles, spill_eles, tail_eles):
        #Created once a facility is evaluated in the SMH Project                  
        self.proj = proj
        self.fac = fac
        self.site = self.proj.site
        self.fac_prefs = self.proj.fac_prefs
        self.rule_curve = self.fac.rule_curve
        self.inflows = inflows
        self.pass_allos = pass_allos
        self.spill_allos = spill_allos
        self.over_allos = over_allos
        self.flush_allos = flush_allos
        self.hwater_eles = hwater_eles
        self.spill_eles = spill_eles
        self.tail_eles = tail_eles  
        
        #Combines the passage module, spillway, flushing allocations
        self.comb_rule_curve = self.rule_curve.copy()
        self.comb_pass_allos = self.pass_allos.copy()
        if self.fac.flushing:
            self.comb_rule_curve.append([self.fac.flush_mod, 1])
            self.comb_pass_allos = np.append(self.comb_pass_allos, [self.flush_allos], axis=0)
        self.comb_rule_curve.append([self.fac.spill_mod, 1])
        self.comb_pass_allos = np.append(self.comb_pass_allos,[self.spill_allos], axis=0)
            
        self.mod_colors = plt.rcParams['axes.prop_cycle'].by_key()['color'] #Sets the module colors for plots
        
        self.M = 100000000 #Arbitrarily high penalty function
        
        #Calculates the heads and reservoir volumes for each timestep
        self.heads = [[j - self.tail_eles[i] for j in self.hwater_eles[i]] for i in range(0, len(self.hwater_eles))] 
        self.gross_heads = [self.spill_eles[i] - self.tail_eles[i] for i in range(0, len(self.inflows))]
        if self.site.reservoir_eq is not None:
            self.res_vols = [self.site.reservoir_eq.get_y(hw) for hw in self.spill_eles]          
        else:
            self.res_vols = None
        
        #Use functions to calculate the performance metrics for the simulation
        self.initial_costs_dict, self.icc_breakdown_dict = self.calc_initial_costs()
        self.icc = round(self.initial_costs_dict['ICC'])
        self.total_cost = self.initial_costs_dict['Total']
        self.sim_years = len(self.inflows)/365
        self.gen_perf_dict, self.gen_cf_dict, self.gen_series_dict = self.calc_gen_performance()
        self.pass_mod_hours = self.calc_mod_hours()
        self.pass_mod_cfs = self.calc_mod_cfs()
        self.pass_mod_flow_ratios = self.calc_mod_flow_ratios()
        self.start_stop_list = self.calc_mod_start_stops()
        self.rec_perf_dict = self.calc_recreation_performance()
        self.fish_up_dict, self.fish_down_dict = self.calc_fish_performance()
        self.sed_perf_dict = self.calc_sediment_performance()
        self.bene_dict = self.calc_annual_benefits()
        self.expns_dict = self.calc_annual_expenses()
        self.NPV = self.calc_npv()
        self.LCOE = self.calc_LCOE()
        
        #Calculate $/kW only if nameplate capacity is greater than zero
        if self.fac.nameplate_cap > 0:
            self.cost_per_kw = round(self.total_cost / self.fac.nameplate_cap, 2)
        else:
            self.cost_per_kw = 'N/A'

        #Calculate flood performance metrics only if peak flow data is provided
        if self.site.peak_flows is not None:
            self.design_flood_period = round(self.site.peak_flows.get_return_period_from_flow(self.fac.total_spill_cap), 2)
            self.flood_period_percent = round(min(1.0, self.design_flood_period/100), 4) #% design flood period based on reference design flood of 100 years
        else:
            self.design_flood_period = None
            self.flood_period_percent = None
        
        #Calculate average reservoir volume only if a volume equation is provided
        if self.res_vols is not None:
            self.avg_imp_volume = np.mean(self.res_vols)
        else:
            self.avg_imp_volume = None
        
        #This dict contains all of the possible objective function metrics that can be used as objectives or constraints
        self.obj_dict = {'LCOE ($/MWh)': self.LCOE, 'NPV ($)':self.NPV, 'ICC ($)':self.icc,'Unit cost ($/kW)': self.cost_per_kw, \
                         'Annual Energy (MWh)':self.gen_perf_dict['Total Annual MWh'], 'Effective Mortality (%)':self.get_fish_performance('M_eff'), 
                         'Effective Passage (%)': self.get_fish_performance('U_eff'),'Sediment Flow Ratio (%)':self.pass_mod_flow_ratios['Sed'],
                         'Sediment Passage Frequency (%)': self.sed_perf_dict['Sediment Passage Frequency'], 'Avg Trap Efficiency (%)': self.sed_perf_dict['Trap Efficiency'], \
                         'Recreation Availability (%)': self.rec_perf_dict['Recreation Availability'], 'Annual Recreation (Hours)': self.rec_perf_dict['Annual Recreation Hours'],\
                         'Flood Return Period (yr)': self.design_flood_period, 'Avg Impoundment Volume (ft3)':self.avg_imp_volume, \
                         'Annual Benefits ($)': self.bene_dict['Total Annual'],'Annual Expenses ($)': self.expns_dict['Total Annual']}
            
    #Returns a dict with the requested information, that can be turned into a dataframe
    def get_run_dict(self, obj=True, fac=False, mods=False, cost=False, bene=False, expns=False):
        out_dict = {}
        if obj:
            out_dict.update(self.obj_dict)
        if fac:
            out_dict.update(self.fac.get_fac_overview_dict())
        if mods:
            out_dict.update(self.fac.get_mod_overview_dict())
        if cost:
            out_dict.update(self.initial_costs_dict)
        if bene:
            out_dict.update(self.bene_dict)
        if expns:
            out_dict.update(self.expns_dict)
        return out_dict
        
    #Saves a computation time
    def add_time(self, time):
        self.computation_time = time
        self.obj_dict['Computation Time (sec)'] = self.computation_time

#####Simualtion Results - Plots
    #Each plot has code that allows the figure to be popped out if hide = False, or plotted on an existing figure in the Tkinter Window
    #Line plot of the headwater, tailwater, and gross head as a function of inflow
    def get_elevation_plot(self, fig=None, ax=None, hide=True):
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
            
        df = self.get_elevation_df()
        df.sort_values('Inflow (cfs)', inplace=True)
        ax.plot(df['Inflow (cfs)'],df['Spillway Headwater Elevation (ft)'])
        ax.plot(df['Inflow (cfs)'],df['Tailwater Elevation (ft)'])
        ax.plot(df['Inflow (cfs)'],df['Gross Head (ft)'])
        ax.set_title('Head and Tailwater Elevations')
        ax.set_xlabel('Inflow (cfs)')
        ax.set_ylabel('Elevation (ft)')
        ax.legend(['Headwater', 'Tailwater', 'Gross Head'])
        return fig, ax
        
    #Line plot of the plant efficiency as a function of powerhouse flow
    def plant_efficiency_plot(self, fig=None, ax=None, hide=True):
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
            
        df = self.get_generation_timeseries_df()
        peak_eff_flow = max(df['Inflow (cfs)'])
        df = df[(df['Total Plant Generation (kW)'] > 0) & (df['Inflow (cfs)'] < peak_eff_flow)]
        df.sort_values('Inflow (cfs)', inplace=True)
        ax.plot(df['Inflow (cfs)'],df['Plant Efficiency (%)'])
        
        ax.set_title('Plant Efficiency')
        ax.set_xlabel('Inflow (cfs)')
        ax.set_ylabel('Efficiency (%)')
        ax.legend(['Simulated'])
        return fig, ax
    
    #Line plot of the plant power output as a time series
    def get_generation_series_plot(self, fig=None, ax=None, hide=True):
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

        x = [h for h in range(1, len(self.inflows)+1)]
        ys = []
        lbls = []
        for m in range(0, len(self.fac.rule_curve)):
            mod = self.fac.rule_curve[m][0]
            if mod.module_class == 'Gen':
                ys.append(self.gen_series_dict[self.get_rule_names()[m]])
                lbls.append(self.get_rule_names()[m])
                
        ax.stackplot(x, ys, labels=lbls)
        
        ax.set_title('Plant Power Output')
        ax.set_xlabel('Timestep')
        ax.set_ylabel('Power (kW)')
        ax.legend()
        return fig, ax
        
    #Bar chart of the availability factors of each module
    def get_capacity_factors_plot(self, fig=None, ax=None, hide=True): 
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
            
        ax.barh(self.get_rule_names(), self.pass_mod_cfs)
        ax.set_title('Module Availability Factors')
        ax.set_xlabel('Availability (0-100%)')
        ax.set_xlim(0.0, 1.0)
        return fig, ax
            
    #Bar chart of the economic, social, and environmental performance metrics that are 0-100
    def get_holistic_perf_plot(self, fig=None, ax=None, hide=True): 
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
            
        holi_dict = self.get_holistic_dict()
        
        if len(holi_dict) <=0:
            ax.text(0.1,0.5, 'No performance measures to plot. Module classes and other site inputs must be included in order to view performance.',  horizontalalignment='left', verticalalignment='center', transform=ax.transAxes)
            return fig, ax
        else:
            lbls = list(holi_dict.keys())
            values = list(holi_dict.values())
            
        if (max(values) > 1) or (min(values) < 0 ):
            print('Error in ratio values')
            
        my_cmap = plt.cm.get_cmap('RdYlGn')
        ax.barh(lbls, values, color=my_cmap(values))
        ax.set_title('Holistic Performance Ratios')
        ax.set_xlabel('Ratio (0-100%)')
        ax.set_xlim(0.0, 1.0)
        return fig, ax
     
    #Pie chart of the initial capital costs
    def get_icc_breakdown_plot(self, fig=None, ax=None, hide=False):
        if hide == False:
            plt.ion()
        else:
            plt.ioff()
            
        if fig is None:
            fig = plt.figure(constrained_layout=True) #
        if ax is None:
            ax = fig.add_subplot(111)
        else:
            ax.clear()
            
        data = []
        lbls = []
        for key in self.icc_breakdown_dict.keys():
            data.append(self.icc_breakdown_dict[key])
            lbls.append(key)
        
        ax.pie(data, labels=lbls)
        my_circle=plt.Circle( (0,0), 0.75, color='white')
        ax.add_artist(my_circle)
        ax.text(0,0,'Total Module Cost\n{}'.format(sty.format_value(sum(data), 'dollar')), ha='center', va='center')
        return fig, ax

    #Bar chart of the total costs, annual benefits, and annual expenses
    def get_economic_plot(self, fig=None, ax=None, hide=False):
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

        #Initial Costs
        lbls = ['ICC', 'Excavation', 'Overhead', 'Contingency', 'Engineering']
        bottom = 0
        for i in lbls:
            ax.bar('Total Costs', self.initial_costs_dict[i], bottom=bottom, width=0.5,label=i)
            bottom += self.initial_costs_dict[i]
                        
        #Annual Benefits
        lbls = ['Generation', 'Recreation']
        bottom = 0
        for i in lbls:
            # data.append(self.inital_costs_dict[i])
            ax.bar('Annual Benefits', self.bene_dict[i], bottom=bottom, width=0.5,label=i)
            bottom += self.bene_dict[i]
        
        #Annual Expenses
        lbls = ['Annual O&M','Annual Start Stop Cost','Annual Flood Cost']
        bottom = 0
        for i in lbls:
            # data.append(self.inital_costs_dict[i])
            ax.bar('Annual Expenses', self.expns_dict[i], bottom=bottom, width=0.5,label=i)
            bottom += self.expns_dict[i]
        
        ax.text(0.3, 0.9, 'LCOE: {}\nNPV: {}\nUnit Cost: {}'.format(sty.format_value(self.LCOE, 'cents', '/MWh'), sty.format_value(self.NPV, 'dollar'), sty.format_value(self.cost_per_kw, 'dollar', '/kW')), horizontalalignment='left', verticalalignment='center', transform=ax.transAxes)
        ax.legend()
        ax.set_ylabel('Cost ($)')
        return fig, ax
        
    #Line plot of the inflow timeseries with a point on the current timestep in the animation window
    def get_daily_flow_point_plot(self, time_step, fig=None, ax=None, hide=True):
        if hide == False:
            plt.ion()
        else:
            plt.ioff()
            
        if fig is None:
            fig = plt.figure(figsize=(6, 3))
        if ax is None:
            ax = fig.add_subplot(111)
        else:
            ax.clear()
            
        ax.plot(range(0, len(self.inflows['Discharge (cfs)'])), self.inflows['Discharge (cfs)'])
        ax.plot(time_step, self.inflows['Discharge (cfs)'].iloc[time_step], 'ro')
        ax.set_ylabel('Flow (cfs)')
        ax.set_xlabel('Timestep')
        ax.set_title('Flow Timeseries')
        fig.tight_layout()
        return fig, ax
    
    #Plots the module legend for the flow allocation bar chart
    def get_module_legend_plot(self, other_ax, hide=True):
        if hide == False:
            plt.ion()
        else:
            plt.ioff()
            
        fig = plt.figure(figsize=[3,3])
        ax_leg = fig.add_subplot(111)

        ax_leg.legend(*other_ax.get_legend_handles_labels(), loc='center')
        ax_leg.axis('off')
        fig.tight_layout()
        return fig, ax_leg
    
    #Bar chart of the flow allocation across the modules for a given timestep
    def plot_flow_allo_bar(self, time_step, fig=None, ax=None, hide=True):
        if hide == False:
            plt.ion()
        else:
            plt.ioff()
            
        if fig is None:
            fig = plt.figure(figsize=(2, 6))
        if ax is None:
            ax = fig.add_subplot(111)
            
        else:
            ax.clear()
        
        lbls = self.get_rule_names()
        allos = self.pass_allos[:,time_step].tolist()
        
        allos.append(self.spill_allos[time_step])
        lbls.append(self.fac.spill_mod.name)
        if self.fac.flush_mod is not None:
            allos.append(self.flush_allos[time_step])
            lbls.append(self.fac.flush_mod.name)
       
        allos.append(self.over_allos[time_step])
        lbls.append('Over-flow')
        
        if sum(allos) != self.inflows['Discharge (cfs)'].iloc[time_step]:
            print('Allocations does not equal inflows')
        
        norm_allos = [i/sum(allos) for i in allos]
        
        bottom = 0
        for i in range(0, len(allos)):
            ax.bar(time_step, norm_allos[i], width=0.5, bottom=bottom, align='center', label=lbls[i])
            bottom += norm_allos[i]

        ax.set_ylim(0, 1)
        ax.get_xaxis().set_visible(False)
        ax.set_ylabel('Percent of Inflow (%)')
        ax.set_title('Flow\nAllocations')
        fig.tight_layout()
        return fig, ax
        
    #Line plots of the dam profile, headwater, tailwater, and module constraints for a given timestep
    def plot_dam_profile(self, time_step,  fig=None, ax=None, hide=True):
        if hide == False:
            plt.ion()
        else:
            plt.ioff()
        
        bed_ele = self.site.bed_elevation
        if fig is None:
            fig = plt.figure(figsize=(6,3))
        if ax is None:
            ax = fig.add_subplot(111)
            
        else:
            ax.clear()

        if self.fac.spill_mod.op_mode == 'Controlled Spillway':
            spill_height = self.fac_prefs.nol
        else:    
            spill_height = self.fac.spill_mod.crest_height
            
        spill_rec = Rectangle((0, bed_ele), self.fac.spill_mod.length, spill_height, facecolor='grey', edgecolor='black')
        ax.add_patch(spill_rec)
        
        x_min = -3*self.fac.spill_mod.length
        x_max = 3*self.fac.spill_mod.length
        
        #Add boundary lines
        ylevels = []
        for i in range(0, len(self.fac.rule_curve)):
            mod = self.fac.rule_curve[i][0]
            if mod.module_class in ['Rec', 'Fish']:
                if mod.max_head_drop is not None:
                    ax.plot([x_min, 0], [bed_ele + self.fac_prefs.nol - mod.max_head_drop, bed_ele + self.fac_prefs.nol - mod.max_head_drop], label=mod.name, color=self.mod_colors[i], linestyle='--', alpha=0.7)
                    ylevels.append(bed_ele + self.fac_prefs.nol - mod.max_head_drop)
                if mod.max_head_rise is not None:
                    ax.plot([x_min, 0], [bed_ele + self.fac_prefs.nol + mod.max_head_rise, bed_ele + self.fac_prefs.nol + mod.max_head_rise], label=mod.name, color=self.mod_colors[i], linestyle='--', alpha=0.7)
                    ylevels.append(bed_ele + self.fac_prefs.nol + mod.max_head_rise)
                if mod.min_tail_ele is not None:
                    ax.plot([self.fac.spill_mod.length, x_max], [bed_ele + mod.min_tail_ele, bed_ele + mod.min_tail_ele], label=mod.name, color=self.mod_colors[i], linestyle='--', alpha=0.7)
                    ylevels.append(bed_ele + mod.min_tail_ele)
                if mod.max_tail_ele is not None:
                    ax.plot([self.fac.spill_mod.length, x_max], [bed_ele + mod.max_tail_ele, bed_ele + mod.max_tail_ele], label=mod.name, color=self.mod_colors[i], linestyle='--', alpha=0.7)
                    ylevels.append(bed_ele + mod.max_tail_ele)
        
        ax.plot([x_min, 0], [self.spill_eles[time_step]+bed_ele, self.spill_eles[time_step]+bed_ele], color='blue') #Add colors and stuff
        ax.plot([self.fac.spill_mod.length, x_max], [self.tail_eles[time_step]+bed_ele, self.tail_eles[time_step]+bed_ele], color='blue')
        ax.plot([x_min, x_max], [bed_ele, bed_ele], color='brown')
        
        max_hwater = max([h + bed_ele for h in self.spill_eles])
        if len(ylevels) > 0:
            max_ylim = max(max(ylevels), max_hwater)
        else:
            max_ylim = max_hwater
        ax.get_xaxis().set_visible(False)
        ax.set_xlabel('Stream-wise Direction (X)')
        ax.set_ylabel('Elevation (ft)')
        ax.set_title('Dam Profile - Headwater and Tailwater Elevations')
        ax.set_ylim(bed_ele, max_ylim+1) 
        fig.tight_layout()
        return fig, ax
        
    #Stackplot of the flow allocations to each passage module across the time series
    def plot_flow_allos(self, fig=None, ax=None, hide=False):
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
        
        x = [h for h in range(1, len(self.inflows)+1)]
        lbls = self.get_rule_names()
        y = self.pass_allos.tolist()
        y.append(self.spill_allos.tolist())
        lbls.append(self.fac.spill_mod.name)
        if self.fac.flush_mod is not None:
            y.append(self.flush_allos.tolist())
            lbls.append(self.fac.flush_mod.name)
        if sum(self.over_allos) > 0:
            y.append(self.over_allos.tolist())
            lbls.append('Over-flow')
            
        ax.stackplot(x,y,labels=lbls)
        ax.legend()
        ax.set_yscale('log')
        ax.set_ylabel('Flow (cfs)')
        ax.set_xlabel('Time (days)')
        ax.set_title('Flow Allocations')
        if hide == False:
            fig.show()
            fig.canvas.draw()
        
        return fig, ax
    
    #Line plots of the downstream and upstream fish passage performance metrics as a time series
    def get_fish_plot(self, fig=None, ax=None, hide=False):
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
            
        legend_labels = []
        if (self.fish_up_dict is False) and (self.fish_down_dict is False):
            ax.text(0.1,0.5, 'Could not simulate fish passage performance. Make sure inputs are entered properly.',  horizontalalignment='left', verticalalignment='center', transform=ax.transAxes)
        else:
            if self.fish_up_dict is not False:
                plot_dict = self.fish_up_dict
                for spec in self.proj.species_list:
                    s = spec.name
                    if plot_dict[s] is not False:
                        ax.plot(range(0, len(self.inflows)), plot_dict[s])
                        legend_labels.append('Effective Passage: ' + s)
            if self.fish_down_dict is not False:
                plot_dict = self.fish_down_dict
                for spec in self.proj.species_list:
                    s = spec.name
                    if plot_dict[s] is not False:
                        ax.plot(range(0, len(self.inflows)), plot_dict[s])
                        legend_labels.append('Effective Mortality: ' + s)
        
            ax.legend(legend_labels)
            ax.set_ylabel('Percentage (%)')
            ax.set_xlabel('Time (days)')
            ax.set_title('Fish Passage Performance')
        return fig, ax

    ##### Simulation Results - Calculations    
    #The relevant metrics are annualized using the sim_years
    
    ###Sediment
    #Calculates several sediment performance measures
    def calc_sediment_performance(self):
        out_dict = {'Sediment Flow Ratio': self.pass_mod_flow_ratios['Sed']}
        freq_counter = 0
        for i in range(0, len(self.inflows)):
            day_sed_flow = self.flush_allos[i]
            for j in range(0, len(self.rule_curve)):
                mod = self.rule_curve[j][0]
                if mod.module_class == 'Sed':
                    day_sed_flow += self.pass_allos[j][i]
            if day_sed_flow > 0:
                freq_counter += 1
            
        out_dict['Sediment Passage Frequency'] = round(freq_counter / len(self.inflows), 4)
        if self.res_vols is not None:
            out_dict['Trap Efficiency'] = round(self.calc_trap_eff_sim(), 4)
        else:
            out_dict['Trap Efficiency'] = None
        return out_dict
    #Calculates the trap efficiency for one time step using the Eizel-Din model
    def calc_trap_eff_t(self, t):
        Q_t = self.inflows['Discharge (cfs)'][t]
        return 100*math.exp(-365*self.site.trap_b*Q_t*60*60*24/self.site.reservoir_eq.get_y(self.spill_eles[t])) 
    #Flow weights and averages the trap efficiencies across the simulation
    def calc_trap_eff_sim(self): 
        TE_t_list = [self.calc_trap_eff_t(t)*self.inflows.iloc[t][0] for t in range(0,len(self.inflows))]
        return sum(TE_t_list)/sum(self.inflows['Discharge (cfs)'])
    
    ####Economic
    #Calculates several generation performance measures
    def calc_gen_performance(self):
        gen_dict = {}
        gen_series = {}
        cf_dict = {}
        for m in range(0, len(self.fac.rule_curve)):
            mod = self.fac.rule_curve[m][0]
            if mod.module_class == 'Gen':
                gen_series[self.get_rule_names()[m]] = [self.get_mod_power(m,t) for t in range(0, len(self.inflows))]
                mod_heads = [i[m] for i in self.heads]
                gen_dict[self.get_rule_names()[m]] = self.calc_annual_mod_gen(mod, self.pass_allos[m], mod_heads)
                cf_dict[self.get_rule_names()[m]] = gen_dict[self.get_rule_names()[m]]/(mod.nom_power * mod.hours_available())
        
        total_gen = round(sum(gen_dict.values()))
        gen_dict['Total Simulation Generation'] = round(total_gen * self.sim_years) #gen_dict has annual mod gen
        gen_dict['Total Annual'] = total_gen
        gen_dict['Total Annual MWh'] = round(total_gen/1000)
        gen_series['Total Plant Generation (kW)'] = [self.calc_day_plant_power(t) for t in range(0, len(self.inflows))] 
        if self.fac.nameplate_cap > 0:
            cf_dict['Plant'] = round(total_gen/(self.fac.nameplate_cap * 8760), 4) #This is based on nameplate capacity, not max_cap, so it might go over 100%
        else:
            cf_dict['Plant'] = 0
        return gen_dict, cf_dict, gen_series
    #Calculates net present value
    def calc_npv(self):
        ann_benefits = self.bene_dict['Total Annual']
        ann_expenses = self.expns_dict['Total Annual']
        npv = sum([(ann_benefits-ann_expenses)/((1+(self.proj.costs.discount/100))**t) for t in range(1, int(self.proj.costs.proj_life)+1)]) - self.total_cost
        return round(npv)
    #Calculates the levelized cost of energy
    def calc_LCOE(self): 
        if self.gen_perf_dict['Total Annual'] <= 0:
            return self.M
        else:
            disc_ann_costs = sum([(self.expns_dict['Total Annual']/((1+(self.proj.costs.discount/100)))**t) for t in range(1, int(self.proj.costs.proj_life)+1)])
            disc_ann_gen = sum([(self.gen_perf_dict['Total Annual MWh']/((1+(self.proj.costs.discount/100)))**t) for t in range(1, int(self.proj.costs.proj_life)+1)])
            return round((self.initial_costs_dict['Total']+disc_ann_costs)/disc_ann_gen, 4)
    #Calculate the annual revenue from generation and recreation
    def calc_annual_benefits(self):
        costs = self.proj.costs
        bene_dict = {'Generation':round((self.gen_perf_dict['Total Annual MWh'] * costs.energy), 2),\
                     'Recreation':round((self.rec_perf_dict['Annual Recreation Hours'] * costs.recreation), 2)}
        bene_dict['Total Annual'] = sum(bene_dict.values())
        return bene_dict
    #Calculate annual expenses from modules, start stops, and annual op costs
    def calc_annual_expenses(self):
        cs_tb = self.proj.costs
        start_stops = self.start_stop_list
        flood_volume = sum(self.over_allos)
        
        #Annual Plant O&M Costs
        if cs_tb.om_type == '(%) Percent of ICC': #Fixed Cost
            om = (cs_tb.om/100.0) * self.initial_costs_dict['ICC']
        else: 
            om = cs_tb.om
        for m in self.fac.rule_curve:
            om += m[0].op_cost
        om += self.fac.fou_mod.op_cost * self.fac.num_fou
        om += self.fac.non_mod.op_cost * self.fac.num_non
        om += self.fac.spill_mod.op_cost * self.fac.num_spill
        for s in self.fac.screens:
            om += s.op_cost
        
        #Gen Start Stop Costs
        gen_ss_total = 0
        for i in range(0, len(self.fac.rule_curve)):
            mod = self.fac.rule_curve[i][0]
            if mod.module_class == 'Gen':
                gen_ss_total += mod.cost_ss * start_stops[i]
            
        expns_dict = {'Total Annual': 0, \
                      'Annual O&M': round(om, 2),\
                      'Annual Start Stop Cost': round(gen_ss_total/self.sim_years, 2),\
                          'Annual Flood Cost': round((flood_volume * cs_tb.flood)/self.sim_years, 2)}
        expns_dict['Total Annual'] = round(expns_dict['Annual O&M'] + expns_dict['Annual Start Stop Cost'] + expns_dict['Annual Flood Cost']) 
        return expns_dict
    #Calcuate the plant powerhouse output
    def calc_day_plant_power(self, time_step):
        out_power = 0
        for i in range(0, len(self.rule_curve)):
            if self.rule_curve[i][0].module_class == 'Gen':
                out_power += self.get_mod_power(i, time_step)
        return out_power
    #Calculate the power from one module for the specifed flow at the timestep
    def get_mod_power(self, rule_curve_index, time_step):
        return self.rule_curve[rule_curve_index][0].get_power(self.pass_allos[rule_curve_index][time_step], self.heads[time_step][rule_curve_index])
    #Calculate the annualized module generation
    def calc_annual_mod_gen(self, gen_mod, allos, heads):
        gen_sum = sum([gen_mod.get_power(allos[f], heads[f]) for f in range(0, len(allos))])
        return gen_sum * 24 / self.sim_years #kW/day * 1day * (24hrs/day) 
    #Calculate the initial costs and save the components as a dict
    def calc_initial_costs(self): 
        cs_tb = self.proj.costs
        costs_dict = {'Total':0, 'Additional Capital Costs': cs_tb.add_capital,'Additional Non-Capital Costs': cs_tb.add_noncapital,'ICC':0, 'Excavation': 0, 'Overhead':0, 'Engineering':0,'Contingency':0}
        icc_breakdown_dict = {}
        #Module Costs i.e. ICC       
        for m in self.fac.rule_curve:
            costs_dict['ICC'] += m[0].cap_cost
            if m[0].name in icc_breakdown_dict.keys():
                icc_breakdown_dict[m[0].name] += m[0].cap_cost
            else:
                icc_breakdown_dict[m[0].name] = m[0].cap_cost
        costs_dict['ICC'] += self.fac.fou_mod.cap_cost * self.fac.num_fou
        costs_dict['ICC'] += self.fac.non_mod.cap_cost * self.fac.num_non
        costs_dict['ICC'] += self.fac.spill_mod.cap_cost * self.fac.num_spill
        costs_dict['ICC'] += cs_tb.add_capital
        icc_breakdown_dict[self.fac.fou_mod.name] = self.fac.fou_mod.cap_cost * self.fac.num_fou
        icc_breakdown_dict[self.fac.non_mod.name] = self.fac.non_mod.cap_cost * self.fac.num_non
        icc_breakdown_dict[self.fac.spill_mod.name] = self.fac.spill_mod.cap_cost * self.fac.num_spill
        icc_breakdown_dict['Additional'] = cs_tb.add_capital
        for s in self.fac.screens:
            icc_breakdown_dict[s.name] = s.cap_cost
            costs_dict['ICC'] += s.cap_cost
        
        #Excavation Cost
        costs_dict['Excavation'] += cs_tb.excavation * self.fac.footprint
        if self.fac.total_width > self.site.stream_width:
            mup, mdown = self.fac.get_long_fac_bounds()
            fac_len = mup + mdown
            costs_dict['Excavation'] += cs_tb.excavation * ((self.fac.total_width - self.site.stream_width)*fac_len)
            
        #Overhead cost
        if cs_tb.overhead_type == '(%) Percent of ICC': #Overhead input as percent of ICC, otherwise constant
            costs_dict['Overhead'] += (cs_tb.overhead/100.0) * costs_dict['ICC']
        else:
            costs_dict['Overhead'] += cs_tb.overhead
       
        #Engineering cost
        if cs_tb.engineering_type == '(%) Percent of ICC': #Engineering input as percent of ICC, otherwise constant
            costs_dict['Engineering'] += (cs_tb.engineering/100.0) * costs_dict['ICC']
        else:
            costs_dict['Engineering'] += cs_tb.engineering
            
        #Contingency cost
        if cs_tb.contingency_type == '(%) Percent of ICC': #Contingency input as percent of ICC, otherwise constant
            costs_dict['Contingency'] += (cs_tb.contingency/100.0) * costs_dict['ICC']
        else:
            costs_dict['Contingency'] += cs_tb.contingency

        costs_dict['Total'] = round(costs_dict['ICC'] + costs_dict['Excavation'] + costs_dict['Overhead'] + costs_dict['Engineering']+ costs_dict['Contingency'] + costs_dict['Additional Non-Capital Costs'])

        icc_sum = 0
        for i in icc_breakdown_dict.keys():
            icc_sum += icc_breakdown_dict[i]
        
        return costs_dict, icc_breakdown_dict
    
    ####Operation
    #Module flow ratios are the total flow allocated to the module during the simulation divided by the total inflow
    def calc_mod_flow_ratios(self):
        total_inflow = sum(self.inflows['Discharge (cfs)'])
        out_dict = {'Gen': 0, 'Sed': sum(self.flush_allos), 'Wat': 0, 'Rec': 0,'Fish':0,\
                    'Spill': sum(self.spill_allos)/total_inflow, 'Over-flow': sum(self.over_allos)/total_inflow}
        for i in range(0, len(self.rule_curve)):
            mod = self.rule_curve[i][0]
            out_dict[mod.module_class] += sum(self.pass_allos[i])
            
        for i in self.fac.pass_mod_cls:
            out_dict[i] = round(out_dict[i] / total_inflow, 4)
        
        return out_dict
    #Module capacitry factors are the percentage of time on divided by the time available
    def calc_mod_cfs(self):
        out_list = []
        for i in range(0, len(self.fac.rule_curve)):
            mod = self.fac.rule_curve[i][0]
            total_poss = 0
            total_on = 0
            for t in range(0, len(self.inflows)):
                if self.inflows.index[t].month in mod.op_months:
                    total_poss += mod.design_flow
                    total_on += self.pass_allos[i][t]
            out_list.append(round(total_on/total_poss, 2))
        return out_list
    #Module hours are the total number of days the module is on times 24hrs/day
    def calc_mod_hours(self):
        out_list = []
        for i in range(0, len(self.fac.rule_curve)):
            hours = 0
            for x in self.pass_allos[i]:
                if x > 0:
                    hours += 24
            out_list.append(hours)
        return out_list
    #Calculates the number of time the modules are turned on and then off (on then off counts as one)
    def calc_mod_start_stops(self):
        ss_counts = []
        allos = self.pass_allos
        for m in range(0, len(self.fac.rule_curve)):
            count = 0
            for i in range(0, len(self.fac.rule_curve)):
                for j in range(1, len(allos)):
                    if (allos[i][j] >= 0) and (allos[i][j-1] <=0): #Counts if flow went from zero to non-zero in flow allocations
                        count += 1
            ss_counts.append(count)
        return ss_counts
        
    ###Recreation
    #Calcualtes several recreation performance metrics
    def calc_recreation_performance(self):
        out_dict = {}
        total_hours = 0
        for i in range(0, len(self.fac.rule_curve)):
            mod = self.fac.rule_curve[i][0]
            if mod.module_class == 'Rec':
                total_hours += self.pass_mod_hours[i]
                out_dict[self.get_rule_names()[i] + ' Hours On'] = self.pass_mod_hours[i]
                out_dict[self.get_rule_names()[i] + ' Capacity Factor'] = self.pass_mod_cfs[i]
            
        out_dict['Total Simulation Recreation Hours'] = round(total_hours)
        out_dict['Annual Recreation Hours'] = round(total_hours/self.sim_years)
    
        total_possible_steps = 0
        total_available_steps = 0
        for t in range(0, len(self.inflows)):
            for j in range(0, len(self.fac.rule_curve)):
                mod = self.fac.rule_curve[j][0]
                if mod.module_class == 'Rec':
                    if mod.on_month(self.inflows.index[t].month):
                        total_possible_steps += 1
                        if self.pass_allos[j][t] > 0:
                            total_available_steps +=1
                    
        if total_possible_steps > 0:
            out_dict['Recreation Availability'] = round(total_available_steps/total_possible_steps,2)
        else:
            out_dict['Recreation Availability'] = 0

        return out_dict
    
    ###Fish
    #Facilitates the calculation of both upstream and downstream passage metrics
    def calc_fish_performance(self):
        Umst_dict = {}
        Mst_dict = {}
        if self.proj.species_list is not None:
            for spec in self.proj.species_list:
                s = spec.name
                if self.fac.check_up_fish_complete(s):
                    Umst_dict[s] = self.calc_upstream_passage_efficiency(spec)
                if self.fac.check_down_fish_complete(s):
                    Mst_dict[s] = self.calc_downstream_mortality(spec)
                    
            if len(Umst_dict) <= 0:
                Umst_dict = False
            if len(Mst_dict) <= 0:
                Mst_dict = False
                
            return Umst_dict, Mst_dict
        else:
            return False, False
         
    #Calculate the effective upstream passage for a given species at each timestep
    def calc_upstream_passage_efficiency(self, species): #Returns array of U_s,t that is len(inflows) long
        Ust_list = []
        for t in range(0, len(self.inflows)):
            Amst_list = []
            Ems_list = []
            Pms_list = []
            if species.on_up_month(self.inflows.index[t].month):
                for j in range(0, len(self.comb_rule_curve)):
                    rel_dis = self.comb_pass_allos[j][t]/sum(self.comb_pass_allos[:,t])
                    Amst_list.append(species.get_attraction_eff(rel_dis))
                    Ems_list.append(self.comb_rule_curve[j][0].entr_effs[species.name])
                    Pms_list.append(self.comb_rule_curve[j][0].pass_effs[species.name])
                sum_EA = sum([Ems_list[i]*Amst_list[i] for i in range(0, len(self.comb_rule_curve))])
                if sum_EA <= 0: #No attraction flows
                    Ust = 0
                else:
                    Ust = sum([((Ems_list[i]**2)*(Amst_list[i]**2)*Pms_list[i])/(sum_EA) for i in range(0, len(self.comb_rule_curve))])
            else:
                Ust = None
            Ust_list.append(Ust)
        return Ust_list
    #Calculates the downstream effective mortality for a given species at each timestep
    def calc_downstream_mortality(self, species): #Gives Meff,s,t or the effective mortality for a given species at time t
        Mst_list = []
        for t in range(0, len(self.inflows)):
            guid_weighted_flows = []
            mort_rates = []
            if species.on_down_month(self.inflows.index[t].month): #If migratory month
                if self.fac.has_screens == True: #If there is a screen, then have to create a screen tree
                    tree = ScreenTree('Root')                    
                    for s in self.fac.screens:
                        self.add_screen_to_tree(tree, s, self.comb_rule_curve)
                    mod_fish_flow_percs = tree.calc_fish_flow(self.comb_rule_curve, self.comb_pass_allos[:,t], species)
                    Mst = 1.0 - sum(mod_fish_flow_percs)
                else: #If no screen tree, then apply across all modules at once
                    for j in range(0, len(self.comb_rule_curve)):
                        mod = self.comb_rule_curve[j][0]
                        guid_weighted_flows.append((1-mod.guide_effs[species.name])*self.comb_pass_allos[j][t])
                        mort_rates.append(mod.mort_rates[species.name])
                    if sum(guid_weighted_flows) <= 0: #If no where to go, then all are killed
                        Mst = 1
                    else:
                        Mst = sum([(guid_weighted_flows[k]*mort_rates[k])/sum(guid_weighted_flows) for k in range(0, len(self.comb_rule_curve))])
            else:
                Mst = None #Set mortality to none if no migration
            Mst_list.append(Mst)
        return Mst_list
    #Adds a screen to the tree to create the top down structure that fish flow through
    def add_screen_to_tree(self, tree, screen, rule_curve):
        all_nodes = tree.get_all_nodes()
        new_screen_cover_list = [screen.check_covered(i[0].name) for i in rule_curve]
        new_node = ScreenNode(screen)
        
        if len(all_nodes) == 0: #first screen in list is always the farthest upstream
            tree.add_child(new_node)
        else:
            added = False
            for node in all_nodes:
                node_screen_cover_list = [node.screen.check_covered(i[0].name) for i in rule_curve]
                overlap_list = [x and y for (x, y) in zip(new_screen_cover_list, node_screen_cover_list)]
                if True in overlap_list:
                    node.add_child(new_node)
                    added=True
                    break
            if added == False:
                tree.add_child(new_node)
                
##### Simulation Results - Retrieval Functions   
#Several of these functions pair with the results figures, so that users can download tabular data along with the figures
    #Returns a line by line textual summary of the simulation for the simulation results frame
    def get_sim_desc(self):
        out_text = 'Total Cost: {}\nNameplate Capacity: {}\nICC: {}\nLCOE: {}\nNPV: {}\nUnit Cost: {}\nAnnual Generation: {}\nAnnual Recreation Hours: {}'.format(\
                    sty.format_value(self.total_cost, 'dollar'), \
                        sty.format_value(self.fac.nameplate_cap, 'round-2', 'kW'),sty.format_value(self.icc, 'dollar'), \
                        sty.format_value(self.LCOE, 'cents', '/MWh'), sty.format_value(self.NPV, 'dollar'), \
                            sty.format_value(self.cost_per_kw, 'dollar', '/kW'), \
                            sty.format_value(self.gen_perf_dict['Total Annual MWh'], 'comma', 'MWh'), \
                            sty.format_value(self.rec_perf_dict['Annual Recreation Hours'], 'comma', 'hrs'))
        return out_text
    #Returns a textural description of the timestep characteristics for the animation frame
    def get_day_desc(self, time_step):
        up_fish = self.get_fish_performance('U_t', time=time_step)
        down_fish = self.get_fish_performance('M_t', time=time_step)
        if (up_fish is False) or (up_fish is None):
            up_fish = 'N/A'
        else:
            up_fish = sty.format_value(up_fish, 'percent')
        
        if (down_fish is False) or (down_fish is None):
            down_fish = 'N/A'
        else:
            down_fish = sty.format_value(down_fish,'percent')
        
        if self.res_vols is not None:
            res_out = sty.format_value(self.res_vols[time_step], 'comma', 'ft3')
            trap_out = sty.format_value(self.calc_trap_eff_t(time_step), 'percent-4')
        else:
            res_out = None
            trap_out = None
        return 'Day: {}\nInflow: {}\nPower: {}\nGross Head: {}\nReservoir Volume: {}\nTrap Efficiency: {}\nCross-species Mortality: {}\nCross-species Passage: {}'.format(\
            self.inflows.index[time_step].strftime('%m-%d-%y'), \
                sty.format_value(self.inflows['Discharge (cfs)'].iloc[time_step], 'comma', 'cfs'), \
                    sty.format_value(self.calc_day_plant_power(time_step), 'round-2', 'kW'), \
                        sty.format_value(self.gross_heads[time_step], 'round-2', 'ft'), \
                        res_out, trap_out, down_fish, up_fish, )
    #Returns text of the rule curve with module name and counts
    def get_rule_names(self):
        return [m[0].name + ' ' + str(m[1]) for m in self.fac.rule_curve]

    #Returns the fish passage performance metrics for a specified species, timestep, and module number. The index notation is described in the user guide: m-module,s-species,t-time, 
    def get_fish_performance(self, metric, time=None, species=None, mod_num=None): #dict key is s, umst[] is by time umst[][] is by module
        if (metric[0] == 'U') and (self.fish_up_dict is False): # If fish up not sucessful, return False
            return False
        if (metric[0] == 'M') and (self.fish_down_dict is False): #If fish down not successful, return False
            return False
        if metric == 'U_s,t':
            return round(self.fish_up_dict[species][time], 4)
        elif metric == 'U_s':
            num_steps = sum(x is not None for x in self.fish_up_dict[species])
            if num_steps<= 0:
                print('No fish timesteps')
                return None
            else:
                return round(sum(filter(None, self.fish_up_dict[species]))/num_steps, 4)
        elif metric == 'U_t':
            ust = []
            for s in list(self.fish_up_dict.keys()):
                if self.fish_up_dict[s][time] is not None:
                    ust.append(self.fish_up_dict[s][time])
            if len(ust) <= 0:
                return None
            else:
                return round(np.mean(ust), 4)
        elif metric == 'U_eff':
            U_s_list = []
            for s in list(self.fish_up_dict.keys()):
                num_steps = sum(x is not None for x in self.fish_up_dict[s])
                U_s_list.append(sum(filter(None, self.fish_up_dict[s]))/num_steps)
            return round(np.mean(U_s_list), 4)
        elif metric == 'M_s,t':
            return round(self.fish_down_dict[species][time], 4)
        elif metric == 'M_s':
            num_steps = sum(x is not None for x in self.fish_down_dict[species])
            if num_steps<= 0:
                print('No fish timesteps')
                return None
            else:
                return round(sum(filter(None, self.fish_down_dict[species]))/num_steps, 4)
        elif metric == 'M_t':
            mst = []
            for s in list(self.fish_down_dict.keys()):
                if self.fish_down_dict[s][time] is not None:
                    mst.append(self.fish_down_dict[s][time])
            if len(mst) <= 0:
                return None
            else:
                return round(np.mean(mst), 4)
        elif metric == 'M_eff':
            M_s_list = []
            for s in list(self.fish_down_dict.keys()):
                num_steps = sum(x is not None for x in self.fish_down_dict[s])
                M_s_list.append(sum(filter(None, self.fish_down_dict[s]))/num_steps)
            return round(np.mean(M_s_list), 4)
    #Returns a table that can be output to describe the costs and revenues with the economic summary figure
    def get_economic_df(self):
        icc_df = pd.DataFrame.from_dict(self.initial_costs_dict, orient='index', columns=['Value'])
        icc_df.index.name = 'Initial Costs'
        
        bene_df = pd.DataFrame.from_dict(self.bene_dict, orient='index', columns=['Value'])
        bene_df.index.name = 'Annual Benefits'
        
        expns_df = pd.DataFrame.from_dict(self.expns_dict, orient='index', columns=['Value'])
        expns_df.index.name = 'Annual Expenses'
        
        out_df = pd.concat([icc_df.reset_index(), bene_df.reset_index(), expns_df.reset_index()], axis=1)        
        out_df.fillna('', inplace=True)
        return out_df
    #Returns a table of initial costs by module type
    def get_module_cost_df(self):
        cost_df = pd.DataFrame.from_dict(self.icc_breakdown_dict, orient='index', columns=['Cost ($)'])
        cost_df.index.name = 'Module Name'
        return cost_df
    #Returns a data frame of the flow allocation time series
    def get_allocations_df(self):
        labels = self.get_rule_names()
        data = self.pass_allos.tolist()
        data.append(self.spill_allos.tolist())
        labels.append(self.fac.spill_mod.name)
        if self.fac.flush_mod is not None:
            data.append(self.flush_allos.tolist())
            labels.append(self.fac.flush_mod.name)
        data.append(self.over_allos.tolist())
        labels.append('Over-flow')
        df = pd.DataFrame(data=np.transpose(data), columns=labels)
        df['dateTime'] = self.inflows.index
        df.set_index('dateTime', inplace=True, drop=True)
        return df
    #Returns a table of the species pasaage time series
    def get_species_df(self):
        temp_up_dict = {}
        if self.fish_up_dict is not False:
            for key in self.fish_up_dict.keys():
                temp_up_dict['Upstream Passage - ' + key] = self.fish_up_dict[key]
        temp_down_dict = {}
        if self.fish_down_dict is not False:
            for key in self.fish_down_dict.keys():
                temp_down_dict['Downstream Mortality - ' + key] = self.fish_down_dict[key]
        temp_up_dict.update(temp_down_dict)
        if len(temp_up_dict) <= 0:
            out_df = pd.DataFrame(data=['Could not assess fish passage performance'], columns=['Error'])
        else:
            out_df = pd.DataFrame(temp_up_dict)
            out_df['dateTime'] = self.inflows.index
            out_df.set_index('dateTime', drop=True, inplace=True)
        return out_df
    #Returns a table with the generation related time series data
    def get_generation_timeseries_df(self):
        out_df = pd.DataFrame.from_dict(self.gen_series_dict)
        out_df['dateTime'] = self.inflows.index
        out_df.set_index('dateTime', drop=True, inplace=True)
        out_df['Spillway Headwater Elevations (ft)'] = self.spill_eles
        out_df['Tailwater Elevations (ft)'] = self.tail_eles
        out_df['Gross Head (ft)'] = self.gross_heads
        out_df['Inflow (cfs)'] = self.inflows
        out_df['Max Potential Power (kW)'] =  (9810*(out_df['Gross Head (ft)']*0.3048)*(out_df['Inflow (cfs)']*0.0283))/1000
        out_df['Plant Efficiency (%)'] = out_df['Total Plant Generation (kW)']/out_df['Max Potential Power (kW)']
        return out_df
    #Returns a table with the availability factors for each module
    def get_availability_df(self):
        out_df = pd.DataFrame(list(zip(self.get_rule_names(), self.pass_mod_cfs)), columns=['Module', 'Availability Factor'])
        return out_df
    #Returns a table with the head and tailwater elevation time series data
    def get_elevation_df(self):
        out_df = pd.DataFrame(list(zip(self.inflows.iloc[:,0].values, self.spill_eles, self.tail_eles, self.gross_heads)), index=self.inflows.index, columns=['Inflow (cfs)', 'Spillway Headwater Elevation (ft)', 'Tailwater Elevation (ft)', 'Gross Head (ft)'])
        return out_df
    #Returns a dict of the holistic performance metrics
    def get_holistic_dict(self):
        holi_dict = {}
        if self.res_vols is not None:
           holi_dict['1 - Average Trap Efficiency'] = round(1-self.sed_perf_dict['Trap Efficiency'], 4)
        #Check if has generation module
        has_gen = False
        for i in range(0, len(self.fac.rule_curve)):
            mod = self.fac.rule_curve[i][0]
            if mod.module_class == 'Gen':
                has_gen = True
                break
        if has_gen:
            holi_dict['Generation Capacity Factor'] = round(self.gen_cf_dict['Plant'], 4)
    
        #Check if has sediment passage module
        has_sed = False
        for i in range(0, len(self.fac.rule_curve)):
            mod = self.fac.rule_curve[i][0]
            if mod.module_class == 'Sed':
                has_sed = True
                break
        if has_sed:
            holi_dict['Sediment Flow Ratio'] = round(self.sed_perf_dict['Sediment Flow Ratio'], 4)
            holi_dict['Sediment Passage Frequency'] = round(self.sed_perf_dict['Sediment Passage Frequency'], 4)
            
        #Fish
        M_eff = self.get_fish_performance('M_eff')
        if M_eff is not False:
            holi_dict['1 - Cross-species Effective Mortality'] = round(1 - M_eff, 4)
        U_eff = self.get_fish_performance('U_eff')
        if U_eff is not False:
            holi_dict['Cross-species Effective Passage'] = round(U_eff, 4)
            
        #Social
        if self.flood_period_percent is not False:
            holi_dict['Design Flood (100yr Benchmark)'] = round(self.flood_period_percent, 4)
        if self.rec_perf_dict['Recreation Availability'] is not False:
            holi_dict['Recreation Availability'] = round(self.rec_perf_dict['Recreation Availability'], 4)
                        
        return holi_dict
    #Turns the holistic dict into a dataframe
    def get_holistic_df(self):
        holi_dict = self.get_holistic_dict()
        out_df = pd.DataFrame.from_dict(holi_dict, orient='index', columns=['Values']).reset_index()
        out_df.rename(columns={'index':'Metric'}, inplace=True)
        out_df.set_index('Metric',drop=True, inplace=True)
        return out_df
    

#%%## SPECIES - represents a migratory species of interest that is used as an index for the fish passage models
class Species:
    def __init__(self, name, up_months, down_months, a=0.8, b=0.05):
        self.name = name
        self.up_months = up_months #Upstream passage months
        self.down_months = down_months #Downstream passage months
        self.a = a #Relative discharge parameter
        self.b = b #Attraction sensitivity parameter
        
    #Check if a month is during the upstream passage months
    def on_up_month(self, month):
       return month in self.up_months
    #Check if a month is during the downstream passage months
    def on_down_month(self, month):
       return month in self.down_months
   #Returns the attraction efficiency using the sigmoid function for a given relative discharge
    def get_attraction_eff(self, rel_dis):
        if rel_dis <= 0:
            return 0
        else:
            Amst = 1/(1 + math.exp(-100*(((1/self.a)*rel_dis)-self.b)))
            return Amst
    
    
    
#%%## Flow Data - used to save flow data and create figures
class FlowData: 
    def __init__(self, name, data_df): #The data_df must include the following columns: dateTime, Discharge (cfs)
        self.name = name
        self.start_date = data_df['dateTime'].iloc[0]
        self.end_date = data_df['dateTime'].iloc[-1]
        self.datetimes = data_df['dateTime'].tolist()
        self.flows = data_df['Discharge (cfs)'].tolist()
        self.df = data_df.set_index('dateTime')
        
        self.sorted_flows, self.sorted_flow_probs = self.build_flow_duration()
        
    #Returns a subset of the flow time series between two dates
    def get_flow_subset(self, start_date, end_date):
        mask = (self.df.index >= start_date) & (self.df.index < end_date)
        return self.df.loc[mask]
    #Returns the original dataframe
    def get_df(self):
        return self.df
    #Returns a flow value for a given exceedance probability
    def get_flow_from_prob(self,prob):
        P_index = self.sorted_flow_probs.index(min(self.sorted_flow_probs, key=lambda x:abs(x-prob)))
        return self.sorted_flows[P_index]
    #Returns an exceedance probabilty for a given flow value
    def get_prob_from_flow(self,Q):
        return af.linear_interpolation(Q, self.sorted_flows, self.sorted_flow_probs)
    #Returns the mean daily flow
    def get_mean_daily_flow(self):
        return np.mean(self.flows)
    #Creates a flow duration curve using the sorted flows and corresponding sorted flow probabilties
    def build_flow_duration(self):
        river_flow = [x for x in self.flows if np.isnan(x) == False] #assign river flow to discharge and remove 'nan' values
        sorted_river_flow = np.sort(river_flow) #sort array in ascending order and normalize
        P_order = np.arange(1,len(sorted_river_flow) + 1,1) #generate probabilities in ascending order
        sorted_river_flow_probabilities = [100-100.*xx/(len(P_order)+1) for xx in P_order]
        return sorted_river_flow, sorted_river_flow_probabilities
    #Get the flow duration curves for specific operating months
    def get_module_flow_duration(self, op_months):
        flow_input = self.df[self.df.index.month.isin(op_months)]['Discharge']
        river_flow = flow_input.values
        river_flow = river_flow[~np.isnan(river_flow)]
        sorted_river_flow = np.sort(river_flow)#sort array in ascending order and normalize
        P_order = np.arange(1,len(sorted_river_flow) + 1,1)#generate probabilities in ascending order
        sorted_river_flow_probabilities = [100-100.*xx/(len(P_order)+1) for xx in P_order]
        return sorted_river_flow, sorted_river_flow_probabilities
    #Line plot of the flow duration curve in log-y space
    def get_flow_duration_plot(self, fig=None, ax=None, hide=True, prob=None):
        if hide == True:    
            plt.ioff()
        else:
            plt.ion()
            
        if ax is None:
           fig, ax = plt.subplots()
            
        fig, ax = self.log_plot(self.sorted_flow_probs, self.sorted_flows, fig=fig, ax=ax)
        ax.set_xscale('linear')
        ax.set_xlim(0, 100)
        if prob is not None:
            flow = self.get_flow_from_prob(prob)
            ax.plot((prob, prob), (0, flow), 'k--', alpha = 0.7)
            ax.text(prob, flow+110, '$Q_{' + str(round(prob)) + '}$ = ' +str(round(flow)) + ' cfs', fontsize = 12)
        ax.set_xlabel('Flow Duration Probability (%)')
        ax.tick_params(axis='both', which='both', direction = 'out',\
                        right = False, top = False, labelsize=11)        
        
        ax.set_title('Flow Duration Curve\n(based on flow data from %s to %s)' % \
              (self.start_date.year, self.end_date.year), fontsize = 12)
        ax.set_ylabel('Flow (cfs)')
        plt.tight_layout()
        return fig, ax
    #Line plot of the mean annual flows for different years
    def get_mean_annual_plot(self, fig=None, ax=None, hide=True):
        if hide == True:    
            plt.ioff()
        else:
            plt.ion()
        annual_data = self.df.copy()
        mean_annual = annual_data.resample('Y').mean()
        
        if ax is None:
            fig, ax = plt.subplots()

        ax.plot(mean_annual.index.year, mean_annual['Discharge (cfs)'])
        ax.xaxis.set_major_locator(plticker.MaxNLocator(integer=True))
        ax.set_xlabel('Year')
        ax.set_ylabel('Mean Flow (cfs)')  
        ax.set_title('Mean Annual Flow')
        plt.tight_layout()
        return fig, ax
    #Line plot of total annual inflow for each year in the dataset
    def get_total_annual_plot(self, fig=None, ax=None, hide=True):
        if hide == True:    
            plt.ioff()
        else:
            plt.ion()
        annual_data = self.df.copy()
        sum_annual = annual_data.resample('Y').sum()
        
        if ax is None:
            fig, ax = plt.subplots()

        ax.plot(sum_annual.index.year, sum_annual['Discharge (cfs)'])
        ax.xaxis.set_major_locator(plticker.MaxNLocator(integer=True))
        ax.set_xlabel('Year')
        ax.set_ylabel('Annual Flow (cfs)')    
        ax.set_title('Total Annual Inflow')
        plt.tight_layout()
        return fig, ax
    #Line plot the flow time series
    def get_flow_timeseries_plot(self, fig=None, ax=None, hide=True):
        if hide == True:    
            plt.ioff()
        else:
            plt.ion()
            
        if ax is None:
            fig, ax = plt.subplots()

        time = self.datetimes
        discharge = self.flows
        ax.plot(time, discharge)
        ax.tick_params(axis='both', which='both', direction = 'out',\
                        right = False, top = False, labelsize=11)
        
        ax.set_xlabel('Datetime')
        ax.set_ylabel('Discharge (cfs)')
        ax.set_title('Flow Timeseries\n(Daily flow data from %s to %s)' % \
              (self.start_date.year, self.end_date.year), fontsize = 12)
        plt.tight_layout()
        return fig, ax
    #Line plot of the average flow for each month
    def get_average_month_plot(self, fig=None, ax=None, hide=True):
        if hide == True:    
            plt.ioff()
        else:
            plt.ion()
            
        flow_timeseries = self.df
        if ax is None:
            fig, ax = plt.subplots()

        monthly_avgs = flow_timeseries.resample('m').mean()
        monthly = [stats.mean(monthly_avgs[monthly_avgs.index.month == i]['Discharge (cfs)']) for i in range(1, 13)]
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        ax.plot(months, monthly)
        ax.set_ylabel('Mean Daily Flow (cfs)')
        ax.set_title('Monthly Mean Flows - Seasonal Variation')
        return fig, ax
    #Creates a log-log plot
    def log_plot(self, x, y, fig=None, ax=None, hide=True):
        if hide == True:    
            plt.ioff()
        else:
            plt.ion()
        if ax is None:
            fig, ax = plt.subplots()

        ax.plot(x, y)
        ax.tick_params(axis='both', which='both', direction = 'out',\
                        right = False, top = False, labelsize=11)        
        ax.set_yscale('log') #convert to log
        ax.set_xscale('log')
        rect=fig.patch
        rect.set_facecolor('white') 
        plt.tight_layout()
        return fig, ax
    #Conduct a peak flood analysis and line plot the results with a scatter plot of the raw data
    def get_flood_analysis_plot(self, fig=None, ax=None, hide=True):
        if hide == True:    
            plt.ioff()
        else:
            plt.ion()
            
        if ax is None:    
            fig, ax = plt.subplots()
        else:
            ax.clear()

        peak_analysis_flows = self.peak_flood_analysis()
        if peak_analysis_flows is not False:
            ax.plot(self.flood_years, peak_analysis_flows)
            ax.set_xscale('log')
            ax.set_yscale('log')
    
            x = [1/i for i in self.peak_exc_prob]
            y = self.sorted_peak_flows
            plt.scatter(x, y, color='orange')
            plt.title('Flood Frequency Analysis using Log-Pearson Type III Distribution')
            plt.xlabel('Flood Year')
            plt.ylabel('Flood Flow (cfs)')
            plt.grid(which='both')
            ax.set_axisbelow(True)
            for axis in [ax.xaxis, ax.yaxis]:
                axis.set_major_formatter(plt.ScalarFormatter())
            plt.tight_layout()    
            return fig, ax
        else:
            return 'Error', 'Unable to complete flood analysis'
    
    #Uses linear interpolation on the Log-Pearson regression data to get the flood return period for a given flow
    def get_return_period_from_flow(self, flow): 
        peak_analysis_flows = self.peak_flood_analysis()
        if (peak_analysis_flows is not False):
            if flow <= peak_analysis_flows[0]:
                return af.linear_interpolation(flow,[0, self.flood_years[0]], [0, peak_analysis_flows[0]])
            elif flow >= peak_analysis_flows[-1]:
                return peak_analysis_flows[-1]
            else:
                return af.linear_interpolation(flow, peak_analysis_flows, self.flood_years)
        else:
            return False
        
    #Conducts a flood frequency analysis using peak flow data and the Log-Pearson Type III distribution method described in the link below
    def peak_flood_analysis(self): #Source: https://streamflow.engr.oregonstate.edu/analysis/floodfreq/#log  Suggested by USGS Bulletin 17B
        self.sorted_peak_flows = np.sort(self.flows)[::-1]
        n = len(self.sorted_peak_flows)
        if n > 3: 
            self.flood_years = [1,2,5,10,25,50,100,200]
            log_q = [math.log(x) for x in self.sorted_peak_flows]
            avg_log_q = sum(log_q)/n 
            var2 = [(ql - avg_log_q)**2 for ql in log_q]
            var3 = [(ql - avg_log_q)**3 for ql in log_q]
            return_per = [(n+1)/m for m in range(1, 1+len(self.sorted_peak_flows))]
            self.peak_exc_prob = [1/rp for rp in return_per] 
            var = sum(var2)/len(var2)
            theta = var**(1/2)
            skew = (n * sum(var3))/((n-1)*(n-2)*(theta**3))
            Cs = round(skew, 1)
            if (Cs <=3) & (Cs >= -3):
                ks = self.get_k_values(Cs)
            else:
                print('Unable to retrieve k value, using k=0')
                ks = self.get_k_values(0)
            res_log = [avg_log_q + ks[i] * theta for i in range(0, len(ks))]
            return [math.exp(x) for x in res_log]
        else:
            print('Not enough data points for flood analysis')
            return False
        
    #Returns coefficient values for the flood frequency analysis
    def get_k_values(self,Cs): 
        k_header = ['Cs','99','50','20','10','4','2','1','0.5']
        k_table =   [[3,-0.667,-0.396,0.42,1.18,2.278,3.152,4.051,4.97],[2.9,-0.69,-0.39,0.44,1.195,2.277,3.134,4.013,4.904],[2.8,-0.714,-0.384,0.46,1.21,2.275,3.114,3.973,4.847],[2.7,-0.74,-0.376,0.479,1.224,2.272,3.093,3.932,4.783],\
                    [2.6,-0.769,-0.368,0.499,1.238,2.267,3.071,3.889,4.718],[2.5,-0.799,-0.36,0.518,1.25,2.262,3.048,3.845,4.652],[2.4,-0.832,-0.351,0.537,1.262,2.256,3.023,3.8,4.584],[2.3,-0.867,-0.341,0.555,1.274,2.248,2.997,3.753,4.515],\
                    [2.2,-0.905,-0.33,0.574,1.284,2.24,2.97,3.705,4.444],[2.1,-0.946,-0.319,0.592,1.294,2.23,2.942,3.656,4.372],[2,-0.99,-0.307,0.609,1.302,2.219,2.912,3.605,4.298],[1.9,-1.037,-0.294,0.627,1.31,2.207,2.881,3.553,4.223],\
                    [1.8,-1.087,-0.282,0.643,1.318,2.193,2.848,3.499,4.147],[1.7,-1.14,-0.268,0.66,1.324,2.179,2.815,3.444,4.069],[1.6,-1.197,-0.254,0.675,1.329,2.163,2.78,3.388,3.99],[1.5,-1.256,-0.24,0.69,1.333,2.146,2.743,3.33,3.91],\
                    [1.4,-1.318,-0.225,0.705,1.337,2.128,2.706,3.271,3.828],[1.3,-1.383,-0.21,0.719,1.339,2.108,2.666,3.211,3.745],[1.2,-1.449,-0.195,0.732,1.34,2.087,2.626,3.149,3.661],[1.1,-1.518,-0.18,0.745,1.341,2.066,2.585,3.087,3.575],\
                    [1,-1.588,-0.164,0.758,1.34,2.043,2.542,3.022,3.489],[0.9,-1.66,-0.148,0.769,1.339,2.018,2.498,2.957,3.401],[0.8,-1.733,-0.132,0.78,1.336,1.993,2.453,2.891,3.312],[0.7,-1.806,-0.116,0.79,1.333,1.967,2.407,2.824,3.223],\
                    [0.6,-1.88,-0.099,0.8,1.328,1.939,2.359,2.755,3.132],[0.5,-1.955,-0.083,0.808,1.323,1.91,2.311,2.686,3.041],[0.4,-2.029,-0.066,0.816,1.317,1.88,2.261,2.615,2.949],[0.3,-2.104,-0.05,0.824,1.309,1.849,2.211,2.544,2.856],\
                    [0.2,-2.178,-0.033,0.83,1.301,1.818,2.159,2.472,2.763],[0.1,-2.252,-0.017,0.836,1.292,1.785,2.107,2.4,2.67],[0,-2.326,0,0.842,1.282,1.751,2.054,2.326,2.576],[-0.1,-2.4,0.017,0.846,1.27,1.716,2,2.252,2.482],\
                    [-0.2,-2.472,0.033,0.85,1.258,1.68,1.945,2.178,2.388],[-0.3,-2.544,0.05,0.853,1.245,1.643,1.89,2.104,2.294],[-0.4,-2.615,0.066,0.855,1.231,1.606,1.834,2.029,2.201],[-0.5,-2.686,0.083,0.856,1.216,1.567,1.777,1.955,2.108],\
                    [-0.6,-2.755,0.099,0.857,1.2,1.528,1.72,1.88,2.016],[-0.7,-2.824,0.116,0.857,1.183,1.488,1.663,1.806,1.926],[-0.8,-2.891,0.132,0.856,1.166,1.448,1.606,1.733,1.837],[-0.9,-2.957,0.148,0.854,1.147,1.407,1.549,1.66,1.749],\
                    [-1,-3.022,0.164,0.852,1.128,1.366,1.492,1.588,1.664],[-1.1,-3.087,0.18,0.848,1.107,1.324,1.435,1.518,1.581],[-1.2,-3.149,0.195,0.844,1.086,1.282,1.379,1.449,1.501],[-1.3,-3.211,0.21,0.838,1.064,1.24,1.324,1.383,1.424],\
                    [-1.4,-3.271,0.225,0.832,1.041,1.198,1.27,1.318,1.351],[-1.5,-3.33,0.24,0.825,1.018,1.157,1.217,1.256,1.282],[-1.6,-3.88,0.254,0.817,0.994,1.116,1.166,1.197,1.216],[-1.7,-3.444,0.268,0.808,0.97,1.075,1.116,1.14,1.155],\
                    [-1.8,-3.499,0.282,0.799,0.945,1.035,1.069,1.087,1.097],[-1.9,-3.553,0.294,0.788,0.92,0.996,1.023,1.037,1.044],[-2,-3.605,0.307,0.777,0.895,0.959,0.98,0.99,0.995],[-2.1,-3.656,0.319,0.765,0.869,0.923,0.939,0.946,0.949],\
                    [-2.2,-3.705,0.33,0.752,0.844,0.888,0.9,0.905,0.907],[-2.3,-3.753,0.341,0.739,0.819,0.855,0.864,0.867,0.869],[-2.4,-3.8,0.351,0.725,0.795,0.823,0.83,0.832,0.833],[-2.5,-3.845,0.36,0.711,0.711,0.793,0.798,0.799,0.8],\
                    [-2.6,-3.899,0.368,0.696,0.747,0.764,0.768,0.769,0.769],[-2.7,-3.932,0.376,0.681,0.724,0.738,0.74,0.74,0.741],[-2.8,-3.973,0.384,0.666,0.702,0.712,0.714,0.714,0.714],[-2.9,-4.013,0.39,0.651,0.681,0.683,0.689,0.69,0.69],\
                    [-3,-4.051,0.396,0.636,0.66,0.666,0.666,0.667,0.667]]
        k_df = pd.DataFrame(data=k_table, columns=k_header)
        return k_df[k_df['Cs']==Cs].iloc[0].drop('Cs')

    

#%%## Equation - an object used to capture an equation used throughout different model inputs
class Equation:
    def __init__(self, name, form, coefficients, xlabel, ylabel, \
                 lower_bound=None,upper_bound=None, df=None, regr_results_dict=None,\
                     z_label=None, z_lower_bound=None, z_upper_bound=None, dynamic_type=None, discount_factor=None):
        self.name = name
        self.form = form #Forms = Linear, Power, Polynomial-2, Polynomial-3, Constant, Multi-linear, Multi-power, and Binomial
        self.coeffs = coefficients
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.z_label = z_label
        self.lb = lower_bound
        self.ub = upper_bound
        self.lbz = z_lower_bound
        self.ubz = z_upper_bound
        self.df = df
        self.regr_results = regr_results_dict #keys = R2, Predicted Y, Data Count, Outlier Count
        self.dynamic_type = dynamic_type #Used to storage the parameters used for redesigning of dynamic modules
        self.discount_factor = discount_factor #Used to scale the output linearly during sensitivity analysis
        
        #Check for incorrect bounds
        if self.lb != self.lb: #Checks for nan
            self.lb = None
        if self.ub != self.ub:
            self.ub = None
        if z_label is not None:
            self.is_multi = True
            if self.lbz != self.lbz:
                self.lbz = None
            if self.ubz != self.ubz:
                self.ubz = None
        else:
            self.is_multi = False
        
        self.set_func()
    #Sets a discount coefficient
    def set_discount_factor(self, val):
        self.discount_factor = val
    #Sets the dynamic module attribute type
    def set_dynamic_type(self, text):
        self.dynamic_type = text
    #Sets the function that represents the actual equation
    def set_func(self):
        if self.form == 'Linear':
            self.func = lambda x: self.coeffs[0]*x + self.coeffs[1]
        elif self.form == 'Power':
            self.func = lambda x: self.coeffs[0]*(x**self.coeffs[1]) + self.coeffs[2]
        elif self.form == 'Polynomial-2':
            self.func = lambda x: self.coeffs[0]*(x**2) + self.coeffs[1]*x + self.coeffs[2]
        elif self.form == 'Polynomial-3': 
            self.func = lambda x: self.coeffs[0]*(x**3) + self.coeffs[1]*(x**2) + self.coeffs[2]*x + self.coeffs[3]
        elif self.form == 'Constant':
            self.func = lambda x: self.coeffs[0]
        elif self.form == 'Multi-Linear': #only avaialble for dynamic modules
            self.func = lambda x:self.coeffs[0]*(x[0]**self.coeffs[1]) + self.coeffs[2]*(x[1]**self.coeffs[3])+self.coeffs[4]
        elif self.form == 'Multi-Power': #only avaialble for dynamic modules
            self.func = lambda x:self.coeffs[0]*(x[0]**self.coeffs[1])*(x[1]**self.coeffs[2])+self.coeffs[3]
        elif self.form == 'Binomial':
            self.func = lambda x:self.coeffs[0]*(self.coeffs[1]*x + self.coeffs[2])**self.coeffs[3] + self.coeffs[4]
    #Return the result of the equation for a given x
    #Multi variable equations must send x as a tuple (x,z)
    def get_y(self, x):
        if self.check_bounds(x) == False:
            return False
        else:
            try:
                out_val = self.func(x)
        
                if self.discount_factor is not None:
                    out_val = out_val * self.discount_factor
                
                return out_val
            except:
                return False
            
    #Checks if the provided x is without the specified bounds
    def check_bounds(self, x): 
        if type(x) == tuple:
            if self.lb is not None:
                if x[0] < self.lb:
                    return False
            if self.ub is not None:
                if x[0] > self.ub:
                    return False
            if self.lbz is not None:
                if x[1] < self.lbz:
                    return False
            if self.ubz is not None:
                if x[1] > self.ubz:
                    return False
        else:
            if self.lb is not None:
                if x < self.lb:
                    return False
            if self.ub is not None:
                if x > self.ub:
                    return False
        return True
        
    #Returns the equation in text form
    def get_text(self, digits=2):
        if self.form == 'Linear':
            return 'y = {}x + {}'.format(round(self.coeffs[0], digits), round(self.coeffs[1],digits))
        elif self.form == 'Power':
            return 'y = {}x^{} + {}'.format(round(self.coeffs[0], digits),round(self.coeffs[1], digits),round(self.coeffs[2], digits))
        elif self.form == 'Polynomial-2':
            return 'y = {}x^2 + {}x + {}'.format(round(self.coeffs[0], digits),round(self.coeffs[1], digits),round(self.coeffs[2], digits))
        elif self.form == 'Polynomial-3':
            return 'y = {}x^3 + {}x^2 + {}x + {}'.format(round(self.coeffs[0], digits), round(self.coeffs[1], digits),round(self.coeffs[2], digits),round(self.coeffs[3], digits))
        elif self.form == 'Constant':
            return 'y = {}'.format(round(self.coeffs[0], digits))
        elif self.form == 'Multi-Linear':
            return 'y = {}x^{} + {}z^{} + {}'.format(round(self.coeffs[0], digits), round(self.coeffs[1], digits), round(self.coeffs[2], digits), round(self.coeffs[3], digits), round(self.coeffs[4], digits))
        elif self.form == 'Multi-Power':
            return 'y = {}x^{}z^{} + {}'.format(round(self.coeffs[0], digits), round(self.coeffs[1], digits), round(self.coeffs[2], digits), round(self.coeffs[3], digits))
        elif self.form == 'Binomial':
            return 'y = {}({}x+{})^{} + {}'.format(round(self.coeffs[0], digits), round(self.coeffs[1], digits), round(self.coeffs[2], digits), round(self.coeffs[3], digits), round(self.coeffs[4], digits))
    #Returns a line plot of the equation, any data is shown as a scatter plot
    def get_plot(self, fig=None, ax=None):
        if ax == None:
            plt.ion()
            fig, ax = plt.subplots()
        else:
            plt.ioff()
            ax.clear()
            
        try:
            if self.lb == None: #Sets bounds to 0-100 if no provided bounds
                lb = 0
            else:
                lb = self.lb
            if self.ub == None:
                ub = 100
            else:
                ub = self.ub

                
            x = [i for i in np.arange(lb, ub, 0.1)]
            
            #If a multi variable plot, selects and plots lines for 4 z values
            if self.is_multi:
                if self.lbz is None:
                    lbz = 0
                else:
                    lbz = self.lbz
                
                if self.ubz is None:
                    ubz = 100
                else:
                    ubz = self.ubz
                
                num_z_lines = 4
                z_list = list(np.arange(lbz, ubz, (ubz-lbz)/num_z_lines))
                z_list.append(ubz)
                
                for z in z_list:
                    y = [self.get_y((i,z)) for i in x]
                    ax.plot(x, y)
                    plt.legend(z_list)
            else:
                y = [self.get_y(i) for i in x]
                ax.plot(x, y,'-g')
                
                
            if self.df is not None:
                ax.scatter(self.df[self.xlabel], self.df[self.ylabel], c='b',alpha=0.1)
                
            text = self.get_text()
            if self.regr_results != None:
                text = text + '\nR2: {}\nData Count: {}\nOutlier Count: {}'.format(round(self.regr_results['R2'],2), self.regr_results['Data Count'],self.regr_results['Outlier Count'])
                
            ax.text(0.05,0.95, text, transform=ax.transAxes, verticalalignment='top')
            ax.set_xlabel(self.xlabel)
            ax.set_ylabel(self.ylabel)    
            ax.set_title(self.name)
            plt.tight_layout()
        except:
            print('Unable to plot this function')
        return fig, ax
    
#Allows the user to create a piecewise equation by specifying multiple equations and their applicable ranges
class PiecewiseEquation:
    def __init__(self, name, equations_list, xlabel, ylabel, range_list, dynamic_type=None):
        self.name = name
        self.eq_list = equations_list
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.range_list = range_list #Range must share bounds between upper and lower  equations, i.e. a two equation piecewise will have lower bound, middle bound, upper bound
        self.lb = self.range_list[0]
        self.ub = self.range_list[-1]
        self.dynamic_type = dynamic_type
        self.form = 'Piecewise'

    #Returns the result of the equation for a given x
    #Multi-variate equations are not possible in piecewise yet
    def get_y(self, x):
        if (x < self.lb) or (x > self.ub):
            return False
        else:
            for i in range(0, len(self.range_list)-1):#Bottom inclusive
                if (x >= self.range_list[i]) and (x <= self.range_list[i+1]):
                    return self.eq_list[i].get_y(x)
        return False
    #Returns text string of piecwise equation, on two lines
    def get_text(self):
        out_str = ''
        for i in range(0, len(self.range_list)-1):
            out_str = out_str + str(self.range_list[i]) + '-' + str(self.range_list[i+1]) + ': ' + self.eq_list[i].get_text() + '\n'
        return out_str

    #Plots lineplot of piecewise equation
    def get_plot(self, fig=None, ax=None):
        if ax == None:
            plt.ion()
            fig, ax = plt.subplots()
        else:
            plt.ioff()
            ax.clear()
            
        if self.lb == None:
            lb = 0
            ub = 100
        else:
            lb = self.lb
            ub = self.ub
            
        x = [i for i in np.arange(lb, ub, 0.1)]
        y = [self.get_y(i) for i in x]
        
        ax.plot(x, y,'-g')
        
        ax.text(0.05,0.95, self.get_text(), transform=ax.transAxes, verticalalignment='top')
        ax.set_xlabel(self.xlabel)
        ax.set_ylabel(self.ylabel)    
        ax.set_title(self.name)
        plt.tight_layout()
        return fig, ax            


#%%## PREFERENCES CLASS - collects information about the users design and operation preferences
class Facility_preferences:
    def __init__(self, operation_priorities, design_nol, test_start, test_end, allow_overrun, spill_min_flow=None, min_flow_type=None, notch_flow=None, gen_dispatch_mode='Design Flow'):
        self.op_rules = operation_priorities #List of module type strings e.g. ['Generation', 'Sediment Passage', 'Aquatic Species', 'Recreation', 'Water Passage']
        self.nol = design_nol #Normal operating headwater level
        self.test_start = test_start #Start date of simulation, must be within inflow data
        self.test_end = test_end #End date of simulation, must be within inflow data
        self.gen_dispatch_mode = gen_dispatch_mode #'Design Ramping','Peak Ramping', 'Simple Greedy', 'Advanced Greedy'  
        self.allow_overrun = allow_overrun #Allows the turbines to be ramped past the design flow
        if spill_min_flow is None: #Allocates the spillway minium flow before allocation
            self.spill_min_flow = 0.0
        else:
            self.spill_min_flow = spill_min_flow
        self.min_flow_type = min_flow_type #Can be constant or a percent of inflow
        if notch_flow is None: #Notch flows are allocated before rule-based operation and the flow does not affect headwater levels
            self.notch_flow = 0.0
        else:
            self.notch_flow = notch_flow
            
        self.labels = ['Normal Operating Level', 'Test Data Start Date', 'Test Data End Date', 'Spillway Minimum Flow', 'Minimum Flow Type', 'Spillway Notch Flow', 'Generation Dispatch Mode']
        self.units = ['ft', 'Date', 'Date', 'cfs', 'Text', 'cfs', 'Text']
        self.update_data_list()
    #Returns a table of the information
    def get_df(self):
         return pd.DataFrame(data=self.data_list, index=self.labels, columns=['Value']).rename_axis('Attribute')
    #Updates the data list
    def update_data_list(self):
        self.data_list = [round(self.nol, 2), self.test_start.strftime('%Y-%m-%d'), self.test_end.strftime('%Y-%m-%d'), self.spill_min_flow, self.min_flow_type, self.notch_flow, self.gen_dispatch_mode]  
    
#%%## MODULE LIBRARY CLASS - collects the modules the be used in facility creation
class Module_library:
    def __init__(self, static_modules=[], dynamic_modules=[], screens_list=[]):
        self.cl = ['Gen', 'Wat', 'Sed', 'Fish', 'Rec', 'Fou',  'Non', 'Spill']
        self.cl_full = ['Generation', 'Water Passage', 'Sediment Passage', 'Aquatic Species Passage', 'Recreation', 'Foundation', 'Non-overflow', 'Spillway']
        self.pass_cl = ['Gen', 'Wat', 'Sed', 'Fish', 'Rec', 'Spill']
       
        #Contains all static modules and all dynamic modules that are on
        self.all_mods_dict = {'Gen': [], 'Sed': [], 'Wat': [], 'Fish': [], 'Rec': [], 'Fou':[], 'Non': [], 'Spill':[]}
        self.all_mods_list = []
        self.pass_mods_list = [] #Contains all passage modules that are on, except for spill
        self.screens_list = []
        
        #Static modules have constant attributes that cannot be changed during enumeration or optimization
        self.static_mods = {'Gen': [], 'Sed': [], 'Wat': [], 'Fish': [], 'Rec': [], 'Fou':[], 'Non': [], 'Spill':[]}
        #Dynamic modules have attributes that can be changed during enumeration or optimization
        self.dynamic_mods = {'Gen': [], 'Sed': [], 'Wat': [], 'Fish': [], 'Rec': [], 'Fou':[], 'Non': [], 'Spill':[]}
        
        #Modules can be added during initilization or after
        if len(static_modules) > 0:
            for i in range(0, len(static_modules)):
                self.add_static(static_modules[i])
        if len(dynamic_modules) > 0:
            for i in range(0, len(dynamic_modules)):
                self.add_dynamic(dynamic_modules[i])

        self.update()
        
    #Remove specific screen if name is provided, otherwise remove all screens
    def clear_screens(self, name=None):
        if name == None:
            self.screens_list = []
        else:
            for i in range(0, len(self.screens_list)):
                if self.screens_list[i].name == name:
                    self.screens_list.pop(i)
                    break
    #Add screen to the library
    def add_screen(self, screen):
        self.screens_list.append(screen)
    #Checks if there's a screen with the same name
    def check_name_in_screens(self, name):
        for i in self.screens_list:
            if i.name==name:
                return True
        return False
    #Returns screen with a given name, returns False if there's no screen with that name
    def get_screen_by_name(self, name):
        for screen in self.screens_list:
            if name == screen.name:
                return screen
        return False
    #Returns module with a given name, returns False if there's no module with that name
    def get_mod_by_name(self, name):
        for key in self.all_mods_dict:
            for mod in self.all_mods_dict[key]:
                if name == mod.name:
                    return mod
        return False
    #Adds a static module
    def add_static(self, smod):
        self.static_mods[smod.module_class].append(smod)
        self.update()
    #Removes a static module
    def remove_static(self, smod):
        try:
            for i in range(0, len(self.static_mods[smod.module_class])):
                if self.static_mods[smod.module_class][i].name == smod.name:
                    self.static_mods[smod.module_class].pop(i)
                    self.update_mod_lists()
                    return 'Successful'
        except:
            return 'Unsuccessful'
    #Removes a dynamic module
    def remove_dynamic(self, dmod):
        try:
            for i in range(0, len(self.dynamic_mods[dmod.module_class])):
                if self.dynamic_mods[dmod.module_class][i].name == dmod.name:
                    self.dynamic_mods[dmod.module_class].pop(i)
                    self.update_mod_lists()
                    return 'Successful'
        except:
            return 'Unsuccessful'
    #Adds a dynmaic module
    def add_dynamic(self, dmod):
        self.dynamic_mods[dmod.module_class].append(dmod)
        self.update()
    #Removes all static modules
    def clear_static(self):
        self.static_mods = {'Gen': [], 'Sed': [], 'Wat': [], 'Fish': [], 'Rec': [], 'Fou':[], 'Non': [], 'Spill':[]}
        self.update()
    #Removes all dynamic modules
    def clear_dynamic(self):
        self.dynamic_mods = {'Gen': [], 'Sed': [], 'Wat': [], 'Fish': [], 'Rec': [], 'Fou':[], 'Non': [], 'Spill':[]}
        self.update()
    #Calls update mod lists
    def update(self):
        self.update_mod_lists()
    #Checks if the module library has enough modules if it includes a foundation, a non-overflow, and a water passage module
    def check_complete(self): 
        if (len(self.all_mods_dict['Non']) > 0) and (len(self.all_mods_dict['Fou']) > 0) and (len(self.all_mods_dict['Spill']) > 0):
            return True
        else:
            return False
    #Returns a table of all static modules
    def get_export_df(self):
        df_list = []
        for key in self.static_mods.keys():
            for mod in self.static_mods[key]:
                df_list.append(mod.get_df().reset_index())
        return pd.concat(df_list, axis=1)
        
    #Updates the mod_list and pass_mod_list 
    def update_mod_lists(self):
        a_dict = {'Gen': [], 'Sed': [], 'Wat': [], 'Fish': [], 'Rec': [], 'Fou':[], 'Non': [], 'Spill':[]}
        a_list = []
        p_list = []
        for c in self.cl:
            for m in self.static_mods[c]:
                a_dict[m.module_class].append(m)
                if m.module_class in self.pass_cl:
                    p_list.append(m) 
                    a_list.append(m)
            for m in self.dynamic_mods[c]: 
                if m.module_class == 'Gen':
                    a_dict[m.module_class].append(m)
                    a_list.append(m)
                    if m.module_class in self.pass_cl:
                        p_list.append(m) 
                else:
                    a_dict[m.module_class].append(m)
                    a_list.append(m)
                    if m.module_class in self.pass_cl:
                        p_list.append(m) 
                            
        self.all_mods_list = a_list
        self.all_mods_dict = a_dict
        self.pass_mods_list = p_list
        return 
    #Returns a list of module names
    def get_name_list(self, passage_only=False):
        names=[]
        if passage_only == False:
            for cl in self.all_mods_dict:
                for m in self.all_mods_dict[cl]:
                    names.append(m.name)
        else:
            for m in self.pass_mods_list:
                names.append(m.name)
        return names
                    
#%%## SITE CLASS - collects the attributes of the project site   
class Site:
    def __init__(self, name, stream_width, daily_inflow, \
                 stage_eq, reservoir_eq=None, energy_slope=None, trap_b=None,  peak_flows=None, bed_elevation=None):
        self.name = name
        self.stream_width = stream_width #The lateral width of the stream (dam-axis)
        self.daily_inflow = daily_inflow #FlowData object - this data is used for operation simulation
        self.stage_eq = stage_eq #The stage-discharge equation used for the tailwater depth
        self.energy_slope = energy_slope #The stream slope
        self.reservoir_eq = reservoir_eq #The stage-storage curve for the reservoir
        self.trap_b = trap_b #The sedimentation parameter for the reservoir
        self.peak_flows = peak_flows #FlowData object - the flood flows used for flood frequency analysis
        if bed_elevation is None: #The bed elevation used for plotting figures
            self.bed_elevation = 100
        else:
            self.bed_elevation = bed_elevation
        
        self.labels = ['Site Name','Stream Width', 'Dam Bed Elevation','Stream Slope','Trap Efficiency Parameter', 'Stage Discharge Equation', 'Reservoir Volume Equation']
        self.units = ['Text', 'ft', 'ft amsl', 'ft/ft', 'unitless', 'Equation', 'Equation']
        
        self.update_data_list()
    #Returns the tailwater depth based on the stage-discharge curve
    def get_tailwater_depth(self, flow):
        return self.stage_eq.get_y(flow)
    #Returns a table of the atribute values
    def get_df(self):
        return pd.DataFrame(data=self.data_list, index=self.labels, columns=['Value']).rename_axis('Attribute')
    #Updates the data list
    def update_data_list(self):
        if self.reservoir_eq is not None:
            res_out = self.reservoir_eq.get_text()
        else:
            res_out = None
        self.data_list =[self.name, round(self.stream_width, 2), round(self.bed_elevation, 2), self.energy_slope, self.trap_b, self.stage_eq.get_text(), res_out]
   
#%%## COST TABLES CLASS - collects the cost attributes and assumptions
class Cost_tables:
    def __init__(self, energy_cost, excavation_cost=0.0, overhead_cost=0.0, \
                 engineering_cost=0.0,contingency_cost=0.0, recreation_price=0.0, flood_price = 0.0,\
                     om_costs=0.0, discount_rate=0.0, project_life=0.0, add_capital=0.0, add_noncapital=0.0):
        self.energy = energy_cost #The $/MWh
        self.excavation = excavation_cost #The $/ft2 of the plant footprint
        self.overhead = overhead_cost[0] #The cost of overhead
        self.overhead_type = overhead_cost[1] #Can be defined as a constant value or percentage of ICC
        self.engineering = engineering_cost[0] #The cost of engineering
        self.engineering_type = engineering_cost[1] #Can be defined as a constant value or percentage of ICC
        self.contingency = contingency_cost[0] #The cost of contingency
        self.contingency_type = contingency_cost[1] #Can be defined as a constant value or percentage of ICC
        self.recreation = recreation_price #The $/hr for recreation availability
        self.om = om_costs[0] #The annual operating and maintenance costs
        self.om_type = om_costs[1] #Can be defined as a constant value or percentage of ICC
        self.flood = flood_price #The $/cfs cost of flood overflow
        self.discount = discount_rate  #The discount rate for NPV and LCOE calculations
        self.proj_life = project_life #The life of the project in years
        self.add_capital = add_capital #Additional captial costs, included in the ICC
        self.add_noncapital = add_noncapital #Additional non-captial costs, not included in the ICC
        
        self.cost_opts = ['($) Total Cost', '(%) Percent of ICC']
    
        self.labels = ['Energy Price','Additional Capital Costs', 'Additional Non-Capital Costs','Excavation Rate','Overhead Cost','Engineering Cost','Contingency Allowance',\
                              'Value of Recreation','Annual O&M Cost','Flood Cost','Discount Rate','Project Life']
        self.units = ['$/MWh','$', '$','$/ft2', self.overhead_type,self.engineering_type,self.contingency_type,'$/hr',self.om_type,'$/cfs','%','yr']
        self.update_data_list()
    #Returns a table of values 
    def get_df(self):
        return pd.DataFrame({'Value':self.data_list, 'Units': self.units}, index=self.labels).rename_axis('Attribute')
    #Updates the data list
    def update_data_list(self):
        self.data_list = [self.energy, self.add_capital, self.add_noncapital, self.excavation, self.overhead, self.engineering, self.contingency, \
                          self.recreation, self.om, self.flood, self.discount, self.proj_life]

#%%## Screen - an object that is placed in front of modules and represents trash racks, fish screens, log booms, etc.
class Screen:
    def __init__(self, screen_name, capital_cost_equation, operating_cost_equation, head_loss_equation, width_equation, height_equation, covering_mod_name_list, fractional_open_area=None, vertical_angle=None, bottom_elevation=None, guide_effs=None, mort_rates=None):
        self.name = screen_name
        self.module_class = 'Screen'
        #Each equation has a dynamic_type that describes what it is a function of
        self.cap_cost_eq = capital_cost_equation #Equation for the capital cost
        self.op_cost_eq = operating_cost_equation #Equation for the operating cost
        self.head_loss_eq = head_loss_equation #Equation for the screen head loss
        self.width_eq = width_equation #Equation for the screen width
        self.height_eq = height_equation #Equation for the screen height
        self.cmod_names_list = covering_mod_name_list #The list of modules names that are covered by the screen
        self.guide_effs = guide_effs #The downstream fish passage guidance efficiency
        self.mort_rates = mort_rates #The upstream fish passge mortality rate
        
        if fractional_open_area is None: #The percentage of the screen area that passes flow
            self.frac_area = 1
        else:
            self.frac_area = fractional_open_area
        if vertical_angle is None: #The vertical angle of the screen in the stream-wise direction
            self.vert_angle = 90
        else:
            self.vert_angle = vertical_angle
        if bottom_elevation is None: #The bottom elevation of the screen 
            self.bot_ele = 0
        else:
            self.bot_ele = bottom_elevation
        
        self.total_area = 0
        self.design_flow = 0
        self.design_head_loss = 0
        self.width = 0
        self.height = 0
        self.cap_cost = 0
        self.op_cost = 0
        self.labels = ['Name', 'Capital Cost', 'Annual Operating Cost', 'Screen Width', \
                    'Screen Height', 'Fractional Open Area','Vertical Angle', 'Bottom Elevation',\
                    'Total Area', 'Design Head Loss', 'Design Flow']
        self.units = ['Text', '$', '$', 'ft', 'ft', 'ft2/ft2', 'Degrees', 'ft', 'ft2', 'ft', 'cfs']
        self.update_data_list()
        
    #Not considered a dynamic module
    def is_dynamic(self):
        return False
    #Update the data list
    def update_data_list(self):
        self.data_list = [self.name, round(self.cap_cost), round(self.op_cost), round(self.width, 2), round(self.height, 2), self.frac_area, self.vert_angle, \
                    self.bot_ele, round(self.total_area), self.calc_design_head_loss(), self.design_flow]
    #Checks if the fish passage metrics are filled out for a given species
    def check_down_fish_complete(self, species):
        complete = True
        for i in [self.guide_effs, self.mort_rates]:
            if i is None:
                return False
            else:
                if species not in list(i.keys()):
                    return False
        return complete
    #Checks if a module is covered by the screen
    def check_covered(self, mod_name):
        if mod_name in self.cmod_names_list:
            return True
        else:
            return False
    #Calculates the design head loss based on the design flow
    def calc_design_head_loss(self):
        active_area = self.total_area * self.frac_area
        flow = self.design_flow
        if self.head_loss_eq.dynamic_type == 'Constant':
            return self.head_loss_eq.get_y(0)
        elif self.head_loss_eq.dynamic_type == 'Function of Active Area':
            return self.head_loss_eq.get_y(active_area)
        elif self.head_loss_eq.dynamic_type == 'Function of Op. Flow':
            return self.head_loss_eq.get_y(flow)
        elif self.head_loss_eq.dynamic_type == 'Function of Active Area and Op. Flow':
            return self.head_loss_eq.get_y((flow, active_area))
        else:
            return False
    #Designs the screen for a facility when provided the site conditions and module counts
    def design_screen(self, pass_mods, pass_count_dict, nol, stream_width): #Pass_count_dict = {mod name: count}
        try:
            #Calculate height
            if type(self.height_eq) == Equation:
                if self.height_eq.dynamic_type == 'Constant':
                    self.height = self.height_eq.get_y(0)
                elif self.height_eq.dynamic_type == 'Function of NOL':
                    self.height = self.height_eq.get_y(nol)
            else:
                self.height = self.height_eq
            
            #Calculate width
            if type(self.width_eq) == Equation:
                if self.width_eq.dynamic_type == 'Constant':
                    self.width = self.width_eq.get_y(0)
                elif self.width_eq.dynamic_type == 'Function of Module Width':
                    mod_widths = 0
                    for i in range(0, len(pass_mods)):
                        mod = pass_mods[i]
                        if mod.name in self.cmod_names_list:
                            mod_widths += mod.width * pass_count_dict[mod.name]
                    self.width = self.width_eq.get_y(mod_widths)
                elif self.width_eq.dynamic_type == 'Function of Stream Width':
                    self.width = self.width_eq.get_y(stream_width)
            else:
                self.width = self.width_eq
            #Calculate total area
            self.total_area = self.width * self.height
            
            des_flow = 0
            for i in range(0, len(pass_mods)):
                mod = pass_mods[i]
                if mod.name in self.cmod_names_list:
                    des_flow += mod.design_flow * pass_count_dict[mod.name]
            self.design_flow = des_flow
            
            self.design_head_loss = self.calc_design_head_loss() #Calculate design head loss
            self.calculate_costs() #Calculate screen costs
                
            return True
        except:
            print('Error calculating screen area')
            return False
    #Calculate the screen costs once it has been designed
    def calculate_costs(self): #Called in the redesign screen function
        if type(self.cap_cost_eq) == Equation:
            if self.cap_cost_eq.dynamic_type == 'Constant':
                self.cap_cost = self.cap_cost_eq.get_y(0)
            elif self.cap_cost_eq.dynamic_type == 'Function of Total Area':
                self.cap_cost = self.cap_cost_eq.get_y(self.total_area)
            elif self.cap_cost_eq.dynamic_type == 'Function of Design Flow':
                self.cap_cost = self.cap_cost_eq.get_y(self.design_flow)
        else:
            self.cap_cost = self.cap_cost_eq
            
        if type(self.op_cost_eq) == Equation:
            if self.op_cost_eq.dynamic_type == 'Constant':
                self.op_cost = self.op_cost_eq.get_y(0)
            elif self.op_cost_eq.dynamic_type == 'Function of Total Area':
                self.op_cost = self.op_cost_eq.get_y(self.total_area)
            elif self.op_cost_eq.dynamic_type == 'Function of Design Flow':
                self.op_cost = self.op_cost_eq.get_y(self.design_flow)
        else:
            self.op_cost = self.op_cost_eq
    #Calculate the head loss for a given screen flow and headwater level
    def calculate_head_after_loss(self, flow, hwater):
        try:
            #Calculate active area
            y_screen = hwater - self.bot_ele
            if y_screen > self.height:
                y_screen = self.height #height is the distance from bottom elevation to top of screen
            active_area = np.sin(np.deg2rad(self.vert_angle))*y_screen*self.width*self.frac_area

            if type(self.head_loss_eq) == Equation:
                if self.head_loss_eq.dynamic_type == 'Constant':
                    return hwater - self.head_loss_eq.get_y(0)
                elif self.head_loss_eq.dynamic_type == 'Function of Active Area':
                    return hwater - self.head_loss_eq.get_y(active_area)
                elif self.head_loss_eq.dynamic_type == 'Function of Op. Flow':
                    return hwater - self.head_loss_eq.get_y(flow)
                elif self.head_loss_eq.dynamic_type == 'Function of Active Area and Op. Flow':
                    return hwater - self.head_loss_eq.get_y((flow, active_area)) 
                else:
                    return False
            else:
                return hwater - self.head_loss_eq
        except:
            print('Error calculating head loss')
            
    #Calculates the total flow through the screen for a given flow allocation
    def calc_screen_flow(self, rule_curve, pass_allos_t):
        in_screen = [self.check_covered(i[0].name) for i in rule_curve]
        out_flow = 0
        for i in range(0, len(pass_allos_t)):
            if in_screen[i]:
                out_flow += pass_allos_t[i]
        return out_flow
    #Add fish passage metrics to the screen object
    def add_fish_effs(self, species_name, guidance, mortality):
        if type(self.guide_effs) != dict:
            self.guide_effs = {}
            self.mort_rates = {}
        self.guide_effs[species_name] = guidance
        self.mort_rates[species_name] = mortality
    #Returns a table of the screen characteristics
    def get_df(self, units=False):
        if units == True:
            return pd.DataFrame({'Value':self.data_list, 'Units': self.units}, index=self.labels).rename_axis('Attribute')
        else:
            return pd.DataFrame(data=self.data_list, index=self.labels, columns=['Value']).rename_axis('Attribute')
        
#%%## Screen Tree - used to facilitate the downstream fish passage model
class ScreenTree(): #This object acts as the top of the screen tree containing screen nodes
    def __init__(self, root_name):
        self.root_name = root_name
        self.children = []
        self.all_nodes = []
        self.parent = None
    #Adds a child screen to the tree
    def add_child(self, screenNode):
        screenNode.parent = self
        self.children.append(screenNode)
    #Gets all nodes in the tree
    def get_all_nodes(self):
        all_nodes = []
        for child in self.children:
            all_nodes.append(child)
        for child in self.children:
            if child.getChildNodes(all_nodes) != None:
                child.getChildNodes(self.Nodes)
        return all_nodes
    #Allocates fish flow across the children nodes and calls the children to calculate fish flow lower in the tree
    def calc_fish_flow(self, rule_curve, pass_allos_t, species):
        mod_fish_flows = [0 for i in rule_curve]
        mods_accounted = [False for i in rule_curve]
        mort_rates = [0 for i in rule_curve]
        mod_fish_flow_sum = 0
        for child in self.children:
            #Calculate flow through each screen
            screen_flow = child.screen.calc_screen_flow(rule_curve, pass_allos_t)
            mod_screen_flow = screen_flow*(1.0-child.screen.guide_effs[species.name])
            mod_fish_flow_sum += mod_screen_flow
            for m in range(0, len(rule_curve)):
                if child.screen.check_covered(rule_curve[m][0].name):
                    mod_fish_flows[m] = mod_screen_flow
                    mort_rates[m] = child.screen.mort_rates[species.name]
                    mods_accounted[m] = True    
        for m in range(0, len(rule_curve)): #account for mods without screens
            if mods_accounted[m] == False:
                mod_fish_flows[m] = pass_allos_t[m]*(1.0-rule_curve[m][0].guide_effs[species.name])
                mod_fish_flow_sum += mod_fish_flows[m]
                mort_rates[m] = rule_curve[m][0].mort_rates[species.name]
                
        if sum(mod_fish_flows) == 0:
            mod_fish_flow_percs = [0.0 for i in range(0, len(mod_fish_flows))]
        else:
            mod_fish_flow_percs = [mod_fish_flows[i]*(1.0-mort_rates[i])/mod_fish_flow_sum for i in range(0, len(mod_fish_flows))] #get percentages for the first screen level, applying mortality rate for screens and any uncovered modules
        
        for child in self.children:
            child.calc_fish_flow(mod_fish_flow_percs, rule_curve, pass_allos_t, species)
            
        return mod_fish_flow_percs
        
#Acts a node in the screen tree and is related to a screen in the facility
class ScreenNode:
    def __init__(self, screen):
        self.screen = screen
        self.children = []
        self.parent = None
    #Add a child screen node
    def add_child(self, screenNode):
        screenNode.parent = self
        self.children.append(screenNode)
    #Returns a list of child nodes
    def getChildNodes(self, out_list):
        for child in self.children:
            if len(child.children) > 0:
                child.getChildNodes(out_list)
            out_list.append(child)
    #allocates the fish flow across child modules and screen nodes
    def calc_fish_flow(self, mod_fish_flow_percentages, rule_curve, pass_allos_t, species):        
        mods_in_node = [self.screen.check_covered(i[0].name) for i in rule_curve]
        sub_mod_fish_flows = [0 for i in rule_curve]
        mort_rates = [0 for i in rule_curve]
        mod_fish_flow_sum = 0
        if len(self.children) > 0:
            mods_accounted = [False for i in rule_curve]            
            for child in self.children:
                #Calculate flow through each screen
                screen_flow = child.screen.calc_screen_flow(rule_curve, pass_allos_t) 
                mod_screen_flow = screen_flow*(1.0-child.screen.guide_effs[species.name])
                mod_fish_flow_sum += mod_screen_flow
                for m in range(0, len(rule_curve)):
                    if mods_in_node[m]:
                        sub_mod_fish_flows[m] = mod_screen_flow
                        mort_rates[m] = child.screen.mort_rates[species.name]
                        mods_accounted[m] = True    
            for m in range(0, len(rule_curve)): #account for mods without screens
                if (mods_accounted[m] == False) and (mods_in_node[m]==True):
                    sub_mod_fish_flows[m] = pass_allos_t[m]*(1.0-rule_curve[m][0].guide_effs[species.name])
                    mod_fish_flow_sum += sub_mod_fish_flows[m]
                    mort_rates[m] = rule_curve[m][0].mort_rates[species.name]
                  
            if sum(sub_mod_fish_flows) == 0:
                sub_mod_fish_flow_percs = [0.0 for i in range(0, len(sub_mod_fish_flows))]
            else:
                sub_mod_fish_flow_percs = [sub_mod_fish_flows[i]*(1.0-mort_rates[i])/mod_fish_flow_sum for i in range(0, len(sub_mod_fish_flows))] #get percentages for the first screen level
            for m in range(0, len(rule_curve)):
                if mods_in_node[m]==True:
                    mod_fish_flow_percentages[m] = mod_fish_flow_percentages[m] * sub_mod_fish_flow_percs[m]
            
            for child in self.children: #Recursively call calc_fish_flow for any sub mods
                child.calc_fish_flow(mod_fish_flow_percentages, rule_curve, pass_allos_t, species)
        else:
            for m in range(0, len(rule_curve)): #account for mods without screens
                if mods_in_node[m]==True:
                    sub_mod_fish_flows[m] = pass_allos_t[m]*(1.0-rule_curve[m][0].guide_effs[species.name])
                    mort_rates[m] = rule_curve[m][0].mort_rates[species.name]
                    
            if sum(sub_mod_fish_flows) == 0:
                sub_mod_fish_flow_percs = [0.0 for i in range(0, len(sub_mod_fish_flows))]
            else:
                sub_mod_fish_flow_percs = [sub_mod_fish_flows[i]*(1.0-mort_rates[i])/sum(sub_mod_fish_flows) for i in range(0, len(sub_mod_fish_flows))]
            for m in range(0, len(rule_curve)): #account for mods without screens
                if mods_in_node[m]==True:
                    mod_fish_flow_percentages[m] = mod_fish_flow_percentages[m] * sub_mod_fish_flow_percs[m]

#%%## MODULE CLASS - the parent class for all SMH modules
class Module:
    def __init__(self, module_name, module_class, capital_cost, operating_cost, width, length):
        self.name = module_name
        self.module_class = module_class
        self.cap_cost = capital_cost
        self.op_cost = operating_cost
        self.width = width
        self.length = length
    #Checks if it is a dynamic module
    def is_dynamic(self):
        if hasattr(self, 'dynamic_class'):
            return True
        else:
            return False
    #Returns the footprint area
    def get_footprint(self):
        return self.width * self.length
    #Returns a table of attributes using the data list
    def get_df(self, units=False):
        out_list = ['' for i in range(0, len(self.data_list))]
        for i in range(0, len(self.data_list)):
            val = self.data_list[i]
            if (type(val) == int) or (type(val) == float):
                out_list[i] = str(val)
            elif type(val) == bool:
                if val == True:
                    out_list[i] = 'Y'
                else:
                    out_list[i] = 'N'
            elif type(val) == str:
                out_list[i] = val
            elif val is None:
                out_list[i] == 'N/A'
            elif type(val) is list:
                if len(val) == 12:
                    out_list[i] = 'all'
                else:
                    out_list[i] = str.join(",", [str(i) for i in val])
            elif isinstance(val, Equation):
                if val.name == 'Constant Head Efficiency':
                    out_list[i] = 'N/A'
                else:
                    out_list[i] = val.name
            else:
                print('unknown value type')

        if units == True:
            return pd.DataFrame({'Value':out_list, 'Units': self.units}, index=self.labels).rename_axis('Attribute')
        else:    
            return pd.DataFrame(data=out_list, index=self.labels, columns=['Value']).rename_axis('Attribute')
    
#%%## PASSAGE MODULE CLASS - describes any module that passes flow
class Passage_module(Module):
    def __init__(self, module_name, module_class, capital_cost, operating_cost,\
                 width, length, design_flow, op_months, guide_effs=None, mort_rates=None,\
                     entr_effs=None,pass_effs=None, diversion=False):
        
        super().__init__(module_name, module_class, capital_cost,operating_cost, width, length)
        
        self.design_flow = design_flow #The flow allocated at normal operation
        self.guide_effs = guide_effs #A dict of the downstream fish passage guidance efficiencies, each key is a species name
        self.mort_rates = mort_rates #A dict of the downstream fish passage mortality efficiencies, each key is a species name
        self.entr_effs = entr_effs #A dict of the upstream fish passage entrance efficiencies, each key is a species name
        self.pass_effs = pass_effs #A dict of the upstream fish passage passage efficiencies, each key is a species name
        self.diversion = diversion #Whether the module is instream or a diversion, which does not count toward the facility width requirements
        if len(op_months) == 0: #The months during which the module is on and should be allocated flow
            self.op_months = [x for x in range(1, 13)]
        else:
            self.op_months = op_months
    #Check if the module has the proper passage and entrance metrics for a given species
    def check_up_fish_complete(self, species):
        complete = True
        for i in [self.entr_effs, self.pass_effs]:
            if i is None:
                return False
            else:
                if species not in list(i.keys()):
                    return False
        return complete
    #Check if the module has the proper mortality and guidance metrics for a given species
    def check_down_fish_complete(self, species):
        complete = True
        for i in [self.guide_effs, self.mort_rates]:
            if i is None:
                return False
            else:
                if species not in list(i.keys()):
                    return False
        return complete
    #Add fish passage metrics to the module
    def add_fish_effs(self, species_name, guide, mort, entr, pass_eff):
        if type(self.guide_effs) != dict:
            self.guide_effs = {}
            self.mort_rates = {}
            self.entr_effs = {}
            self.pass_effs = {}
        self.guide_effs[species_name] = guide
        self.mort_rates[species_name] = mort
        self.entr_effs[species_name] = entr
        self.pass_effs[species_name] = pass_eff
    #Checks if the given month is during the operating months
    def on_month(self, month):
       return month in self.op_months
   #Calculates the number of maximum possible hours available depending on the operating months
    def hours_available(self):
        days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        return sum([days[m-1] for m in self.op_months]) * 24



#%%## GENERATION MODULE CLASS - reflects turbine and powertrain technologies
class Generation_module(Passage_module):
    def __init__(self, module_name, capital_cost, operating_cost,\
                 width, length, design_flow, op_months,\
                     min_op_flow, max_op_flow, min_op_head, design_head, max_op_head,\
                         flow_eff_eq, head_eff_eq=None,nominal_power=None, max_power=None, cost_ss=None, diversion=False):
        
        super().__init__(module_name, 'Gen', capital_cost, operating_cost, width, length, design_flow, op_months, diversion=diversion)
            
        self.min_op_flow = min_op_flow #The minimum flow needed for operation
        self.max_op_flow = max_op_flow #The maximum flow allowed for operation
        self.min_op_head = min_op_head #The minimum head needed for operation
        self.design_head = design_head #The design head used for the head efficiency
        self.max_op_head = max_op_head #The maximum head allowed for operationg
        self.flow_eff_eq = flow_eff_eq #The relationship between module flow ratio (allocated flow /design flow) and generation efficiency
        
        if head_eff_eq is None: #The relationship between module head ratio (module head /design head) and generation efficiency
            self.head_eff_eq = Equation('Constant Head Efficiency', 'Constant', [1], 'Relative Head (% design head)', 'Efficiency (%)')
        else:
            self.head_eff_eq = head_eff_eq
        
        if max_power is None: #The maximum power output of the module, may be constrained by electrical infrastructure
            self.set_default_max_power()
        else:
            self.max_power = max_power
            
        if nominal_power is None: #The nominal power output at the design head and flow
            self.nom_power = self.get_power(design_flow, design_head)
        else:
            self.nom_power = nominal_power

        if cost_ss is None: #The cost of a start-stop cycle
            self.cost_ss = 0
        else:
            self.cost_ss = cost_ss
            
        self.peak_eff_flow, self.peak_eff = self.get_peak_eff_flow()
            
        self.labels = ['Name','Capital Cost','Annual Operating Cost',\
                    'Width', 'Length','Design Flow','Operating Months','Instream or Diversion',\
                        'Minimum Operating Flow','Maximum Operating Flow','Minimum Operating Head', \
                           'Design Head','Maximum Operating Head','Flow Efficiency Curve', \
                               'Head Efficiency Curve', 'Max Power','Cost of Start-Stops', 'Nominal Power']
        self.units = ['Text', '$', '$', 'ft', 'ft', 'cfs', 'Month List', 'Y/N', 'cfs', 'cfs', 'ft', 'ft', 'ft', 'Equation', 'Equation', 'kW', '$/start-stop', 'kW']
                    
        self.update_data_list()
    #Updates the data list
    def update_data_list(self):
        self.data_list = [self.name, round(self.cap_cost), round(self.op_cost), round(self.width,2), round(self.length,2), self.design_flow,\
                self.op_months, self.diversion, self.min_op_flow, self.max_op_flow, self.min_op_head, self.design_head,\
                    self.max_op_head, self.flow_eff_eq.get_text(), self.head_eff_eq.get_text(), round(self.max_power), self.cost_ss, round(self.nom_power)]

    #Setst the default max power and the max head and max flow design points
    def set_default_max_power(self):
        head_eff = self.head_eff_eq.get_y(self.max_op_head/self.design_head)
        flow_eff = self.flow_eff_eq.get_y(self.max_op_flow/self.design_flow)
        if head_eff is False:
            head_eff = 1 
            print('Error getting head efficiency, set to 1')
        if flow_eff is False:
            flow_eff = 1
            print('Error getting flow efficiency, set to 1')
        self.max_power = round(self.hydropower_equation(self.max_op_head, self. max_op_flow, flow_eff, head_eff),2)
    
    #Gets the module flow efficiency curve
    def plot_eff_curve(self):
        self.flow_eff_eq.get_plot() 
    #Calculates power output for a given head and flow
    def hydropower_equation(self, head_ft, flow_cfs, flow_eff, head_eff):
        return (9810*(head_ft*0.3048)*(flow_cfs*0.0283)*flow_eff*head_eff)/1000
    #Gets the flow efficency for a given flow
    def get_eff(self, flow_cfs):
        per_flow = flow_cfs/self.design_flow
        flow_eff = self.flow_eff_eq.get_y(per_flow)
        if flow_eff is False:
            flow_eff = 1
            print('Flow outside of efficiency bounds, set to 1')
        return flow_eff

    #Calculates the power output for a given gross head and module flow
    def get_power(self, flow_cfs, head_ft): 
        if flow_cfs == 0:
            return 0
        else:
            per_flow = flow_cfs/self.design_flow
            flow_eff = self.flow_eff_eq.get_y(per_flow)
            if flow_eff is False:
                flow_eff = 1
                print('Flow outside of efficiency bounds, set to 1')
            if self.head_eff_eq is not None:
                per_head = head_ft/self.design_head
                head_eff = self.head_eff_eq.get_y(per_head)
                if head_eff is False:
                    head_eff = 1
                    print('Head outside of efficiency bounds, set to 1')
            else:
                head_eff = 1
                
            power_kw = self.hydropower_equation(head_ft, flow_cfs, flow_eff, head_eff)
            if self.max_power is not None:
                if power_kw > self.max_power:
                    power_kw = self.max_power
                
            return power_kw    
    #Calculates the flow at which the peak efficiency occurs. Takes the largest flow if points are equal
    def get_peak_eff_flow(self):
        if (type(self.flow_eff_eq) == Equation) or (type(self.flow_eff_eq) == PiecewiseEquation):
            try: #Start at the max flow and decrease by one cfs until decreasing
                peak_flow = self.design_flow
                flows = [i for i in range(math.ceil(self.min_op_flow), math.floor(self.design_flow), 1)] #Get all flows by integers between the min flow and the design flow
                flows = flows[::-1] #Reverse direction, so we start from the top
                for i in range(0, len(flows)-1): #continue to decrease the flow as long as the efficiency is increasing
                    if self.flow_eff_eq.get_y(flows[i]/self.design_flow) < self.flow_eff_eq.get_y(flows[i+1]/self.design_flow): #If de
                        peak_flow = flows[i+1]
                    else:
                        break
            except:
                peak_flow = self.design_flow
        else:
            peak_flow = self.design_flow
        peak_eff = self.flow_eff_eq.get_y(peak_flow/self.design_flow)
        return peak_flow, peak_eff
    #Checks if the given head is within the head operating range
    def check_head(self, head):
        if (head >= self.min_op_head) & (head <= self.max_op_head):
            return True
        else:
            return False

#%%## FISH MODULE CLASS - reflects fish passage technologies like volitional fishways
class Fish_module(Passage_module): 
    def __init__(self, module_name, capital_cost, operating_cost,\
                 width, length, design_flow, op_months,\
                      max_head_drop=None, max_head_rise=None, min_tail_ele=None, max_tail_ele=None, diversion=False):

        super().__init__(module_name, 'Fish', capital_cost, operating_cost, width, length, design_flow, op_months, diversion=diversion)
        
        self.max_head_drop = max_head_drop #The maximum decrease in headwater elevation allowed for operation
        self.max_head_rise = max_head_rise #The maximum increase in headwater elevation allowed for operation
        self.min_tail_ele = min_tail_ele #The minimum tailwater elevation allowed for operation
        self.max_tail_ele = max_tail_ele #The maximum tailwater elevation allowed for operation
        self.labels = ['Name','Capital Cost','Annual Operating Cost',\
                    'Width', 'Length','Design Flow','Operating Months','Instream or Diversion', \
                        'Maximum Headwater Drop','Maximum Headwater Rise',\
                            'Minimum Tailwater Level', 'Maximum Tailwater Level']
        self.units = ['Text', '$', '$', 'ft', 'ft', 'cfs', 'Months List', 'Y/N', 'ft', 'ft', 'ft', 'ft']
        self.update_data_list() 
    #Updates the data list
    def update_data_list(self):
        self.data_list = [self.name, round(self.cap_cost), round(self.op_cost), round(self.width, 2), round(self.length, 2), self.design_flow,\
                self.op_months, self.diversion, self.max_head_drop, self.max_head_rise, self.min_tail_ele, self.max_tail_ele]
    #Checks if the headwater change is within allowed bounds
    def check_head(self, head_diff):
        ok_head = True
        if self.max_head_drop is not None:
            if head_diff < -1*self.max_head_drop:
                ok_head = False
        if self.max_head_rise is not None:
            if head_diff > self.max_head_drop:
                ok_head = False
        return ok_head
    #Checks if the tailwater elevation is within allowed bounds
    def check_tailwater_elevation(self, tail_ele):
        ok_tail = True
        if self.min_tail_ele is not None:
            if tail_ele < self.min_tail_ele:
                ok_tail = False
        if self.max_tail_ele is not None:
            if tail_ele > self.max_tail_ele:
                ok_tail = False
        return ok_tail
    
#%%## RECREATION MODULE CLASS - represents low-head recreation passage technologies like boat chutes     
class Recreation_module(Passage_module):
    def __init__(self, module_name, capital_cost, operating_cost,\
                 width, length, design_flow, op_months,\
                      max_head_drop=None, max_head_rise=None, min_tail_ele=None, max_tail_ele=None, diversion=False):

        super().__init__(module_name, 'Rec', capital_cost, operating_cost, width, length, design_flow, op_months, diversion=diversion)
        
        self.max_head_drop = max_head_drop #The maximum decrease in headwater elevation allowed for operation
        self.max_head_rise = max_head_rise #The maximum increase in headwater elevation allowed for operation
        self.min_tail_ele = min_tail_ele #The minimum tailwater elevation allowed for operation
        self.max_tail_ele = max_tail_ele #The maximum tailwater elevation allowed for operation
        
        self.labels = ['Name','Capital Cost','Annual Operating Cost',\
                    'Width', 'Length','Design Flow','Operating Months', 'Instream or Diversion', \
                        'Maximum Headwater Drop','Maximum Headwater Rise',\
                            'Minimum Tailwater Level', 'Maximum Tailwater Level']
        self.units = ['Text', '$', '$', 'ft', 'ft', 'cfs', 'Months List', 'Y/N', 'ft', 'ft', 'ft', 'ft']
        self.update_data_list()
    #Updates the data list
    def update_data_list(self):
        self.data_list = [self.name, round(self.cap_cost), round(self.op_cost), round(self.width, 2), round(self.length, 2), self.design_flow,\
                self.op_months, self.diversion, self.max_head_drop, self.max_head_rise, self.min_tail_ele, self.max_tail_ele]
    #Checks if the headwater change is within allowed bounds
    def check_head(self, head_diff):
        ok_head = True
        if self.max_head_drop is not None:
            if head_diff < -1*self.max_head_drop:
                ok_head = False
        if self.max_head_rise is not None:
            if head_diff > self.max_head_drop:
                ok_head = False
        return ok_head
    #Checks if the tailwater elevation is within allowed bounds       
    def check_tailwater_elevation(self, tail_ele):
        ok_tail = True
        if self.min_tail_ele is not None:
            if tail_ele < self.min_tail_ele:
                ok_tail = False
        if self.max_tail_ele is not None:
            if tail_ele > self.max_tail_ele:
                ok_tail = False
        return ok_tail
#%%## SEDIMENT MODULE CLASS - represents sediment passage technologies like sluice gates                    
class Sediment_module(Passage_module):
    def __init__(self, module_name, capital_cost, operating_cost,\
                 width, length, design_flow, op_months,\
                     operating_mode,operating_flow=None, operating_duration=None, operating_frequency=None, diversion=False):
        
        super().__init__(module_name, 'Sed', capital_cost, operating_cost, width, length, design_flow, op_months, diversion=diversion)
        
        self.op_mode = operating_mode #Can be continuous, sluicing, or flushing
        self.op_flow = operating_flow #For sluicing operation, the minimum inflow required for operation
        self.op_dur = operating_duration #For flushing operation, the number of days that the flushing event occurs
        self.op_freq = operating_frequency #For flushing operationg, the times per year that flushing occurs
        self.labels = ['Name','Capital Cost','Annual Operating Cost',\
                    'Width', 'Length','Design Flow','Operating Months', 'Instream or Diversion',\
                        'Operating Mode', 'Operating Flow', 'Flushing Duration', \
                                                       'Operating Frequency']
        self.units = ['Text', '$', '$', 'ft', 'ft', 'cfs', 'Months List', 'Y/N', 'Text', 'cfs', 'Days','Flushes/year']
        self.update_data_list()
    #Updates the data list
    def update_data_list(self):
        self.data_list = [self.name, round(self.cap_cost), round(self.op_cost), round(self.width, 2), round(self.length, 2), self.design_flow,\
                self.op_months, self.diversion, self.op_mode, self.op_flow, self.op_dur, self.op_freq]
    #Based on the flushing duration and frequency, determines the indices of the provided flow time series where flushing occurs
    def get_flushing_indices(self, flows):
        if self.op_mode == 'Flushing':
            if (self.op_freq <= 0) or (int(self.op_dur) <= 0):
                return []
            else:
                idx = []
                days_btwn_flush = math.ceil(365/self.op_freq)
                for i in range(0, len(flows)):
                    if i % days_btwn_flush == 0:
                        idx.append(i)
                        for j in range(0, int(self.op_dur)-1):
                            i+=1
                            idx.append(i)
                return idx
        else:
            print('Not a flushing module')
            return False

#%%## WATER MODULE CLASS - represents spillways and bypass technologies       
class Water_module(Passage_module):
    def __init__(self, module_name, capital_cost, operating_cost,\
                 width, length, design_flow, op_months,\
                     operating_mode, weir_coefficient=None, crest_height=None, diversion=False):    
        
        if (operating_mode == 'Uncontrolled Spillway') or (operating_mode == 'Controlled Spillway'):
            mod_class = 'Spill'
        else:
            mod_class = 'Wat'
        super().__init__(module_name, mod_class, capital_cost, operating_cost, width, length, design_flow, op_months, diversion=diversion)
        
        self.op_mode = operating_mode #Continuous, controlled spillway, or uncontrolled spillway
        self.weir_coeff = weir_coefficient #For uncontrolled spillway operation, the C coefficient for the weir equation
        self.crest_height = crest_height #For uncontrolled spillway operation, the height of the weir crest for the weir equation
        self.labels = ['Name','Capital Cost','Annual Operating Cost',\
                    'Width', 'Length','Design Flow','Operating Months', 'Instream or Diversion', \
                    'Operating Mode','Weir Coefficient','Crest Height']
        self.units = ['Text', '$', '$', 'ft', 'ft', 'cfs', 'Months List', 'Y/N', 'Text', 'ft^(1/2)/s', 'ft']
        self.update_data_list()
    #Updates the dat list
    def update_data_list(self):
        if self.crest_height is not None:
            crest_height = round(self.crest_height, 2)
        else:
            crest_height = self.crest_height
        self.data_list = [self.name, round(self.cap_cost), round(self.op_cost), round(self.width,2), round(self.length, 2), round(self.design_flow,2),\
                self.op_months, self.diversion, self.op_mode, self.weir_coeff, crest_height]
            

#%%## FOUNDATION MODULE CLASS - represents foundation technologies in rectangular form (i.e. a per unit of footprint basis)
class Foundation_module(Module):
    def __init__(self, module_name, capital_cost, operating_cost, width, length):
        super().__init__(module_name, 'Fou', capital_cost, operating_cost, width, length)
        
        self.labels = ['Name','Capital Cost','Annual Operating Cost',\
                    'Width', 'Length']
        self.units = ['Text', '$', '$', 'ft', 'ft']
        self.update_data_list()
    #Updates the data list
    def update_data_list(self):
        self.data_list = [self.name, round(self.cap_cost), round(self.op_cost), round(self.width, 2), round(self.length, 2)]        

#%%## NON-OVERFLOW MODULE CLASS - represents dam technologies like concrete or earthen dams
class Nonoverflow_module(Module):
    def __init__(self, module_name, capital_cost, operating_cost, width, length):    
        super().__init__(module_name, 'Non', capital_cost, operating_cost, width, length)
        self.labels = ['Name','Capital Cost','Annual Operating Cost',\
                    'Width', 'Length']
        self.units = ['Text', '$', '$', 'ft', 'ft']
        self.update_data_list()
    #Update the data list
    def update_data_list(self):
        self.data_list = [self.name, round(self.cap_cost), round(self.op_cost), round(self.width, 2), round(self.length, 2)]  


#%%## FACILITY CLASS - represents an SMH facility as a collection of SMH modules at a given site
class Facility:
    def __init__(self, name, proj, passage_modules, passage_counts, spill_mod, spill_mod_count, non_mod, foundation_mod, flush_mod=None, screens=[]):
        self.name = name
        self.site = proj.site #The site helps inform design
        self.fac_prefs = proj.fac_prefs #The facility preferences helps inform design
        
        self.pass_mods = passage_modules #List of passage module objects
        self.spill_mod = spill_mod #The spillway module object
        self.num_spill = spill_mod_count #The number of spillway modules
        self.non_mod = non_mod #The non-overflow module object
        self.fou_mod = foundation_mod #The foundation module object
        self.flush_mod = flush_mod #The flushing sediment module object, None if no flushing mod
        self.screens = screens #List of screen objects in order from upstream to downstream
        
        #initialize variables
        self.has_screens = False
        self.flushing = False   
        self.total_width = 0
        self.total_spill_width = 0
        self.total_spill_cap = 0
        self.footprint = 0
        self.num_non = 0
        self.num_fou = 0
        self.rule_curve = []
        self.nameplate_cap = 0 #kW
        self.max_cap = 0
        self.pass_mod_cls = ['Gen', 'Sed', 'Fish', 'Rec', 'Wat']    
        self.results_list = [] #Store simulation results objects
        
        #Save a dict of the module module names and counts
        self.pass_dict = {}
        for i in range(0, len(self.pass_mods)):
            self.pass_dict[self.pass_mods[i].name] = passage_counts[i]

        self.update()
      
    ####Facility - Update Functions        
    def update(self):
        self.rule_curve = self.create_dispatch_order()
        self.total_spill_width, self.total_spill_cap = self.update_spillway()
        self.in_mods = self.get_in_mods()
        self.num_non = self.get_nonoverflow_num()
        self.footprint = self.get_fac_footprint()
        self.num_fou = self.get_foundation_num()
        self.total_width = self.get_facility_width()
        self.nameplate_cap = self.get_nameplate_cap()
        self.max_cap = self.get_max_cap()
        self.flushing = self.get_sediment_characteristics()
        self.update_screens()
        self.get_gen_mods_list()
        if self.fac_prefs.gen_dispatch_mode == 'Simple Greedy':
            self.gen_dispatch_dict, self.gen_qe_dict = self.get_simple_greedy_gen_dispatch()
        elif self.fac_prefs.gen_dispatch_mode == 'Advanced Greedy':
            self.gen_dispatch_dict = self.get_adv_greedy_gen_dispatch()
    #Set the module count 
    def set_mod_count(self, mod, count):
        if mod.name in self.pass_dict.keys(): #module already in facility
            if count <= 0: #If removing module
                self.pass_dict.pop(mod.name)
                for i in range(0, len(self.pass_mods)):
                    if mod.name == self.pass_mods[i].name:
                        self.pass_mods.pop(i)
                        break
            else:
                self.pass_dict[mod.name] = count
        elif mod.name == self.spill_mod.name: #If changing a spillway module count
            if count >= 0:
                self.num_spill = count
        else: #Adding new module
            if count >= 0:
                self.pass_mods.append(mod)
                self.pass_dict[mod.name] = count
    #Set a dynamic module attribute
    def set_mod_att(self, mod, att, val):
        if mod.name in self.pass_dict.keys(): #If in list
            for i in range(0, len(self.pass_mods)):
                if mod.name == self.pass_mods[i].name:
                    self.pass_mods[i].redesign_by_name(att, val)
                    return self.pass_mods[i].validate()
        elif mod.name == self.spill_mod.name:
            self.spill_mod.redesign_by_name(att, val)
            return self.spill_mod.validate()
        elif mod.name == self.flush_mod.name:
            self.flush_mod.redesign_by_name(att, val)
            return self.flush_mod.validate()
        else:
            return False
            
    #Design the screens for the current module configuration
    def update_screens(self):
        for i in range(0, len(self.screens)):
            self.screens[i].design_screen(self.pass_mods, self.pass_dict, self.fac_prefs.nol,self.site.stream_width)
            if self.has_screens == False:
                for j in self.pass_mods:
                    if self.screens[i].check_covered(j.name):
                        self.has_screens = True
    #Return a dict of the main facility characteristics
    def get_fac_overview_dict(self):
        out_dict = {'Capacity (kW)': round(self.nameplate_cap), \
                    'Spillway Module': self.spill_mod.name,'Spillway Count':self.num_spill, 'Spillway Capacity (cfs)':round(self.total_spill_cap), \
                        'Footprint (ft2)':round(self.footprint), 'Foundation Module': self.fou_mod.name, 'Foundation Count': self.num_fou,\
                            'Total Width (ft)': round(self.total_width), 'Non-overflow Module':self.non_mod.name, 'Non-overflow Num': self.num_non}
        if self.flushing:
            out_dict['Flushing Module'] = self.flush_mod.name
        else:
            out_dict['Flushing Module'] = 'N/A'
        return out_dict
    #Return a dict of the module names and counts
    def get_mod_overview_dict(self):
        out_dict = {}
        for key in self.pass_dict.keys():
            out_dict[key + ' Count'] = self.pass_dict[key]
        return out_dict
    #Add a simulation result to the saved list
    def add_simulation_results(self, sim_res):
        self.results_list.append(sim_res)
    #Returns the latest simulation results
    def get_latest_sim_results(self):
        if len(self.results_list) > 0:
            return self.results_list[-1]
        else:
            return False #No simulation results         
    #Gets the objective metric value from the latest simulation
    def get_latest_objective(self, obj, formatted=False):
        if len(self.results_list) > 0:
            latest_res = self.results_list[-1]
            if latest_res is False:
                return False
            else:
                latest_obj = latest_res.obj_dict[obj]
        else:
            return False #No simulation results   
        
        if formatted == True:
            if obj == 'LCOE ($/MWh)':
                return sty.format_value(latest_obj, 'cents', '/MWh')
            elif obj == 'NPV ($)':
                return sty.format_value(latest_obj, 'dollar')
            elif obj == 'ICC ($)':
                return sty.format_value(latest_obj, 'dollar')
            elif obj == 'Unit Cost ($/kW)':
                return sty.format_value(latest_obj, 'dollar', '/kW')
            else:
                return latest_obj
        else:
            return latest_obj
        
    #Gets the headwater elevation for uncontrolled spillways using the general weir equation
    def get_headwater_elevation(self, flow): 
        if flow == 0:
            return self.fac_prefs.nol
        elif flow < 0:
            print('Error calculating spill flow')
            return False
        else: #Uncontrolled spillway uses the weir equation
            mod = self.spill_mod
            return ((flow/(self.total_spill_width*mod.weir_coeff))**(2/3)) + mod.crest_height

    #Checks if there is a flushing gate
    def get_sediment_characteristics(self):
        if self.flush_mod is None:
            return False
        else:
            return True

    #Checks if there is enough information to run the upstream fish passage models
    def check_up_fish_complete(self, species):
        complete = True
        for i in self.pass_mods:
            if i.check_up_fish_complete(species) == False:
                return False
        return complete
    #Checks if there is enough information to run the downstream fish passage models
    def check_down_fish_complete(self, species):
        complete = True
        for i in self.pass_mods:
            if i.check_down_fish_complete(species) == False:
                return False
        for i in self.screens:
            if i.check_down_fish_complete(species) == False:
                return False
        return complete
    #Returns the instream modules 
    def get_in_mods(self):
        in_list = []
        for i in self.pass_mods:
            if i.diversion == False:
                in_list.append(i)
        return in_list
    #Updates the total spillway width and capacity
    def update_spillway(self):
        tot_width = self.spill_mod.width * self.num_spill
        tot_capacity = self.spill_mod.design_flow * self.num_spill
        return tot_width, tot_capacity
    #Calculates the number of non-overflow modules needed to span the river width
    def get_nonoverflow_num(self):
        width_sum = 0
        num = 0
        for m in self.in_mods:
            mod_count = self.pass_dict[m.name]
            width_sum += m.width * mod_count
        if self.spill_mod.diversion == False:
            width_sum += self.total_spill_width
        if width_sum < self.site.stream_width:
            num = math.ceil((self.site.stream_width - width_sum)/self.non_mod.width)
        return num
    #Calculates the total facility footprint
    def get_fac_footprint(self): 
        area = 0
        for mod in self.pass_mods:
            area += mod.get_footprint() * self.pass_dict[mod.name]
        area += self.spill_mod.length * self.total_spill_width
        area += self.non_mod.get_footprint() * self.num_non
        return area
    #Calculates the number of foundation modules needed based on the facility footprint
    def get_foundation_num(self):
        return math.ceil(self.footprint / self.fou_mod.get_footprint())
    
    #Calculates the total facility width
    def get_facility_width(self, count_non=True):
        width = 0
        for m in self.in_mods:
            mod_count = self.pass_dict[m.name]
            width += m.width * mod_count
        if count_non == True:
            width += self.non_mod.width * self.num_non            
        width += self.total_spill_width    
        return width
    #Calculates the nameplant powerhouse capacity (kW)
    def get_nameplate_cap(self):
        cap = 0
        for mod in self.get_pass_class_list('Gen'):
            cap += mod.nom_power * self.pass_dict[mod.name]
        return round(cap)
    #Get the maximum powerhouse power ouput
    def get_max_cap(self):
        cap = 0
        for mod in self.get_pass_class_list('Gen'):
            if mod.max_power is None:
                cap += mod.nom_power * self.pass_dict[mod.name]
            else:
                cap += mod.max_power * self.pass_dict[mod.name]
        return cap
    #Returns a table describing the facility characteristics
    def get_df(self):
        out_dict = {}
        out_dict['Attribute'] = ['Name', 'Capacity', 'Dam Width','Footprint', 'Spillway Width', 'Spillway Design Flood']
        out_dict['Value'] = [self.name, round(self.nameplate_cap,2), round(self.total_width), round(self.footprint), round(self.total_spill_width), round(self.total_spill_cap)]
        out_dict['Unit'] = ['Text', 'kW', 'ft', 'ft2', 'ft', 'cfs']
        module_names = [m.name for m in self.pass_mods]
        for i in [self.spill_mod.name, self.non_mod.name, self.fou_mod.name]:    
            module_names.append(i)
        out_dict['Modules'] = module_names

        module_counts = list(self.pass_dict.values())
        for i in [self.num_spill, self.num_non, self.num_fou]:
            module_counts.append(i)
        out_dict['Counts'] = module_counts
        out_dict['Operation Priority'] = [i for i in range(1, len(self.rule_curve)+1)]
        out_dict['Module'] = [i[0].name + ' ' + str(i[1]) for i in self.rule_curve]
        out_df = pd.DataFrame.from_dict(out_dict, orient='index').T
        out_df = out_df.fillna('')
        return out_df
            
    #Adds a passage module to the facility, the update function must be called after adding modules
    def add_pass_mod(self, mod, count): 
        self.pass_dict[mod.name] = count    
        if mod.name in self.pass_dict.keys():
            for i in range(0, len(self.pass_mods)):
                if self.pass_mods[i].name == mod.name: #Replace existing module
                    self.pass_mods[i] = mod
                    break
        else: #new module addition
            self.pass_mods.append(mod)
    #Returns a passage module and its count for a given name if it exists
    def get_pass_mod(self, mod_name):
        if mod_name in self.pass_dict.keys():
            count = self.pass_dict[mod_name]
            for i in range(0, len(self.pass_mods)):
                if self.pass_mods[i].name == mod_name:
                    mod = deepcopy(self.pass_mods[i])
                    break
            return mod, count
        else: 
            return False, False     

    ####Facility - Retrieval Functions
    #Sorts ascending based on design flow
    def sort_mods(self, mod_list, atr): 
        import operator
        return sorted(mod_list, key=operator.attrgetter(atr))    
    #Returns list of modules for a given class
    def get_pass_class_list(self, mod_class):
        out_list = []
        for m in self.pass_mods:
            if m.module_class == mod_class:
                out_list.append(m)
        return out_list
    #Returns module for a given module name if it exists
    def get_mod_by_name(self, module_name):
        for mod in self.pass_mods:
            if mod.name == module_name:
                return mod
            
        for screen in self.screens:
            if screen.name == module_name:
                return screen
            
        if module_name == self.spill_mod.name:
            return self.spill_mod
        elif module_name == self.non_mod.name:
            return self.non_mod
        elif module_name == self.fou_mod.name:
            return self.fou_mod
        elif self.flush_mod is not None:
            if module_name == self.flush_mod.name:
                return self.flush_mod
        else:
            return False #No module by that name
    

    #### Facility - Simulation Functions
    #Creates the dispatch order using the user-defined preferences and returns a rule_curve list
    def create_dispatch_order(self): #Returns a list with [Mod, index]
        out_rule = []
        for cl in self.fac_prefs.op_rules:
            mod_list = self.get_pass_class_list(cl)
            if len(mod_list) > 1: #If there are more than one of one type of module, then first allocate to mods with smallest design flow
                sorted_mod_list = self.sort_mods(mod_list, 'design_flow')
                for i in range(0, len(sorted_mod_list)):
                    for j in range(0, self.pass_dict[sorted_mod_list[i].name]):
                        out_rule.append([sorted_mod_list[i], i+1])
            elif len(mod_list) == 1:
                for j in range(0, self.pass_dict[mod_list[0].name]):
                    out_rule.append([mod_list[0], j+1])
        return out_rule
    
    #Sets the lists of minimum, maximum, peak, and design flows for the generation modules
    def get_gen_mods_list(self):
        self.gen_mods = []
        for i in range(0, len(self.rule_curve)):
            if self.rule_curve[i][0].module_class == 'Gen':
                self.gen_mods.append(self.rule_curve[i][0])
        self.num_gen = len(self.gen_mods)
        if self.num_gen > 0:
            self.min_gen_flows = [math.ceil(m.min_op_flow) for m in self.gen_mods]
            self.min_gen_flow = math.ceil(min(self.min_gen_flows))
            self.des_gen_flows = [m.design_flow for m in self.gen_mods]
            self.peak_gen_flows = [m.peak_eff_flow for m in self.gen_mods]
            if self.fac_prefs.allow_overrun == True: #If turbine overrun is allowed, then the max is the max operating flow, otherwise the max is the design flow
                self.max_gen_flows = [math.floor(m.max_op_flow) for m in self.gen_mods]
            else:
                self.max_gen_flows = [math.floor(m.design_flow) for m in self.gen_mods]
                
            counter = 0 
            for i in self.pass_mods:
                if i.module_class == 'Gen':
                    counter += 1
            if counter == 1:
                self.all_gen_mods_same = True
            else:
                self.all_gen_mods_same = False
            self.max_gen_flow = math.floor(sum(self.max_gen_flows))
    #Runs the generation module dispatch for one timestep and available flow based on the selected dispatch model
    def get_gen_allocation(self, avail_flow, gen_mods_on, allow_overrun):
        try:
            all_mods_on = not(False in gen_mods_on)
            if (avail_flow < self.min_gen_flow) or (not True in gen_mods_on): #If not enough flow to turn on a module, return zero allocations
                return [0 for j in range(0, self.num_gen)]
            elif self.fac_prefs.gen_dispatch_mode == 'Simple Greedy':
                if all_mods_on: 
                    if avail_flow > self.max_gen_flow:
                        return self.gen_dispatch_dict[self.max_gen_flow]
                    else:
                        return self.gen_dispatch_dict[int(avail_flow)]
                else:
                    res = self.get_simple_greedy_gen_allocation_partial(avail_flow, gen_mods_on)
                    if res is False:
                        print('Error during simple greedy partial allocation')
                        return self.get_peak_ramping_allocation(avail_flow, gen_mods_on)
                    else:
                        return res
            elif self.fac_prefs.gen_dispatch_mode == 'Advanced Greedy':
                if all_mods_on: 
                    if avail_flow > self.max_gen_flow:
                        return self.gen_dispatch_dict[self.max_gen_flow]
                    else:
                        return self.gen_dispatch_dict[int(avail_flow)]
                else:
                    res = self.get_adv_greedy_gen_dispatch_partial(avail_flow, gen_mods_on)
                    if res is False:
                        print('Error during advanced greedy partial allocation')
                        return self.get_peak_ramping_allocation(avail_flow, gen_mods_on)
                    else:
                        return res
            elif self.fac_prefs.gen_dispatch_mode == 'Design Ramping':
                return self.get_design_allocation(avail_flow, gen_mods_on, allow_overrun)
            else: #By default will use the 'Peak Ramping' mode
                return self.get_peak_ramping_allocation(avail_flow, gen_mods_on, allow_overrun)
        except:
            print('Error allocating gen flows - reporting zero generation')
            return [0 for j in range(0, self.num_gen)]

    #Design ramping model - ramps generation modules to the design flow one at a time
    def get_design_allocation(self, avail_flow, gen_mods_on, allow_overrun):
        gen_allos = [0 for i in range(0, self.num_gen)]
        for j in range(0, self.num_gen): #Ramp turbines to design flow
            if gen_mods_on[j]: #If turbine is not already full and is on
                if avail_flow >= self.des_gen_flows[j]: #If enough to ramp to the design flow, do that
                    avail_flow -= self.des_gen_flows[j]
                    gen_allos[j] = self.des_gen_flows[j]
                elif avail_flow >= self.min_gen_flows[j]: #If not enought to ramp to the design flow, then allocate what is left
                    gen_allos[j] = avail_flow
                    avail_flow = 0
                    break
        if allow_overrun and avail_flow > 0: #If flow left over, ramp to the max operating flow, this assumes all units are at the design flow 
            for j in range(0, self.num_gen): #Ramp turbines to design flow
                if (gen_allos[j] < self.max_gen_flows[j]) and gen_mods_on[j] and gen_allos[j] > 0: #If turbine is not already full and is on
                    if avail_flow > self.max_gen_flows[j] - gen_allos[j]: #If enough to ramp to the design flow, do that
                        avail_flow -= self.max_gen_flows[j] - gen_allos[j]
                        gen_allos[j] = self.max_gen_flows[j]
                    else: #If not enought to ramp to the design flow, then allocate what is left
                        gen_allos[j] = gen_allos[j] + avail_flow
                        break
        return gen_allos

    #Peak ramping model - ramps generation modules to the peak efficiency flow one at a time and then to the design flow
    def get_peak_ramping_allocation(self,avail_flow, gen_mods_on, allow_overrun):
        gen_allos = [0 for i in range(0, self.num_gen)]
        for j in range(0, self.num_gen): #Ramp turbines to peak eff
            if gen_mods_on[j]:
                if avail_flow >= self.peak_gen_flows[j]: #If enough flow to meet peak eff, do that
                    gen_allos[j] = self.peak_gen_flows[j]
                    avail_flow -= self.peak_gen_flows[j] 
                elif avail_flow >= self.min_gen_flows[j]: #If not enough for peak flow, but enough to turn on, then do that
                    gen_allos[j] = avail_flow
                    avail_flow = 0
                    break
        if avail_flow > 0: #If flow left over, ramp to design flows, this assumes that all units are at the peak eff flow
            for j in range(0, self.num_gen): #Ramp turbines to design flow
                if (gen_allos[j] < self.des_gen_flows[j]) and gen_mods_on[j] and gen_allos[j] > 0: #If turbine is not already full and is on
                    if avail_flow >= self.des_gen_flows[j] - gen_allos[j]: #If enough to ramp to the design flow, do that
                        avail_flow -= self.des_gen_flows[j] - gen_allos[j]
                        gen_allos[j] = self.des_gen_flows[j]
                    else: #If not enought to ramp to the design flow, then allocate what is left
                        gen_allos[j] = gen_allos[j] + avail_flow
                        avail_flow = 0 
                        break
        if allow_overrun and avail_flow > 0: #If flow left over, ramp to the max operating flow, this assumes all units are at the design flow 
            for j in range(0, self.num_gen): #Ramp turbines to design flow
                if (gen_allos[j] < self.max_gen_flows[j]) and gen_mods_on[j] and gen_allos[j] > 0: #If turbine is not already full and is on
                    if avail_flow >= self.max_gen_flows[j] - gen_allos[j]: #If enough to ramp to the design flow, do that
                        avail_flow -= self.max_gen_flows[j] - gen_allos[j]
                        gen_allos[j] = self.max_gen_flows[j]
                    else: #If not enought to ramp to the design flow, then allocate what is left
                        gen_allos[j] = gen_allos[j] + avail_flow
                        #avail_flow = 0 
                        break
        return gen_allos
    #Simple greedy dispatch model - uses incremental greedy approach to select allocation with largest incremental increase in power output. Returns allocations for all possible inflows assuming all modules are on.
    def get_simple_greedy_gen_dispatch(self):
        try:
            gen_dispatch_dict = {}
            gen_qe_dict = {}
            cur_allos = [0.0 for i in range(0, self.num_gen)]
            cur_qe = [0.0 for i in range(0, self.num_gen)]
                    
            cum_q = self.min_gen_flow
            for i in range(self.min_gen_flow, self.max_gen_flow+1, 1): #For each possible flow
                qe_inc = np.array([0.0 for i in range(0, self.num_gen)])
                new_qes = np.array([np.nan for i in range(0, self.num_gen)])

                for j in range(0, self.num_gen): #Try allocating flow to each module
                    new_q = cur_allos[j] + cum_q
                    if (new_q <= self.max_gen_flows[j]) and (new_q >= self.min_gen_flows[j]): #If the added flow is within the min and max allowed flow range, then test allocating flow
                        new_qe = self.gen_mods[j].get_eff(new_q) * new_q
                        new_qes[j] = new_qe
                        qe_inc[j] = new_qe - cur_qe[j] #Calculate the increment in qe by allocating to module j

                if max(qe_inc) <= 0: #If no module has an increase (can't ramp anything)
                    gen_dispatch_dict[i] = cur_allos.copy()
                    cum_q += 1
                else:
                    k = np.argmax(qe_inc) #index of max increase (takes the lowest index if equal)
                    cur_allos[k] += cum_q #Allocate flow to the module with the greatest qe increase
                    cur_qe[k] = new_qes[k]
                    cum_q = 1
                    gen_dispatch_dict[i] = cur_allos.copy()
                    gen_qe_dict[i] = cur_qe.copy()
 
            return gen_dispatch_dict , gen_qe_dict 
        except:
            return False, False
        
    #Simple greedy model that applies to partial flows when only a subset of the genration modules are on, returns allocation for one timestep
    def get_simple_greedy_gen_allocation_partial(self, avail_flow, gen_mods_on):
        try:
            cur_allos = [0 for i in range(0, self.num_gen)]
            cur_qe = [0 for i in range(0, self.num_gen)]
            cum_q = self.min_gen_flow

            for i in range(self.min_gen_flow, int(avail_flow)+1, 1): #For each possible flow
                qe_inc = np.array([0.0 for i in range(0, self.num_gen)])
                new_qes = np.array([np.nan for i in range(0, self.num_gen)])
                for j in range(0, self.num_gen): #Try allocating flow to each module
                    new_q = cur_allos[j] + cum_q
                    if (new_q <= self.max_gen_flows[j]) and (new_q >= self.min_gen_flows[j]) and (gen_mods_on[j]): #If the added flow is within the flow range, then test allocating flow
                        new_qe = self.gen_mods[j].get_eff(new_q) * new_q
                        new_qes[j] = new_qe
                        qe_inc[j] = new_qe - cur_qe[j] #Calculate the increment in qe

                if max(qe_inc) <= 0: #If no module has an increase (can't ramp anything)
                    cum_q += 1
                else:
                    k = np.argmax(qe_inc) #index of max increase (takes the lowest index if equal)
                    cur_allos[k] += cum_q
                    cur_qe[k] = new_qes[k]
                    cum_q = 1

            return cur_allos
        except:
            return False
    #Uses a greedy algorithm to allocate a given flow to modules that are already on
    def greedy_allocate(self, avail_flow, cur_allos): #Can only allocate flow to modules that are on
        cur_qe = [0.0 if cur_allos[i] <= 0 else self.gen_mods[i].get_eff(cur_allos[i])*cur_allos[i] for i in range(0, len(cur_allos))]
        cum_q = 1
        for k in range(0, int(math.floor(avail_flow))): #Until we run out of flow
            qe_inc = np.array([0.0 for n in range(0, self.num_gen)])
            new_qes = np.array([np.nan for n in range(0, self.num_gen)])
            for j in range(0, self.num_gen): #Try allocating flow to each module
                new_q = cur_allos[j] + cum_q
                if (new_q <= self.max_gen_flows[j]) and (new_q >= self.min_gen_flows[j]) and  cur_allos[j] > 0: #If the added flow is within the min and max allowed flow range, then test allocating flow
                    new_qe = self.gen_mods[j].get_eff(new_q) * new_q
                    new_qes[j] = new_qe
                    qe_inc[j] = new_qe - cur_qe[j] #Calculate the increment in qe by allocating to module j
            if max(qe_inc) > 0: #If no module has an increase (can't ramp anything)
                max_idx = np.argmax(qe_inc) #index of max increase (takes the lowest index if equal)
                cur_allos[max_idx] += cum_q #Allocate flow to the module with the greatest qe increase
                cur_qe[max_idx] = new_qes[max_idx]
                cum_q = 1
            else:
                cum_q += 1
        return sum(cur_qe), cur_allos
    #Advanced greedy approach - uses a nested greedy algorithm to decide when to turn on a new turbine and how to allocate flow across turbines that are on. Returns allocation for all inflows, assuming all modules are on.
    def get_adv_greedy_gen_dispatch(self):
        try:
            gen_dispatch_dict = {}
            mods_on = [False for i in range(0, self.num_gen)]
            for i in range(self.min_gen_flow, self.max_gen_flow+1, 1): #For each possible flow
                cur_allos = [0.0 if not(mods_on[j]) else self.min_gen_flows[j] for j in range(0, self.num_gen)]  

                avail_flow = i - sum(cur_allos)
                cur_qe = [0.0 for i in range(0, self.num_gen)]
                mods_on_allos = [[] for i in range(0, self.num_gen)]
                for j in range(0, self.num_gen): #Try to find a module to turn on
                    if (not mods_on[j]) and (avail_flow >= self.min_gen_flows[j]):
                        temp_allos = cur_allos.copy()
                        temp_allos[j] = self.min_gen_flows[j]
                        cur_qe[j], mods_on_allos[j] = self.greedy_allocate(avail_flow - self.min_gen_flows[j], temp_allos)
                        if self.all_gen_mods_same:
                            break
                #Try allocating flow across mods that are already on
                qe_keep, allos_keep = self.greedy_allocate(avail_flow, cur_allos.copy())
                
                if qe_keep > max(cur_qe): #If it is best just to allocate to the current on modules
                    gen_dispatch_dict[i] = allos_keep.copy()
                else:
                    max_idx = np.argmax(cur_qe) #index of max increase (takes the lowest index if equal)
                    mods_on[max_idx] = True
                    gen_dispatch_dict[i] = mods_on_allos[max_idx].copy()
            return gen_dispatch_dict
        except:
            return False
    
    #Uses advanced greedy model to allocate flows for one timestep when not all modules are on
    def get_adv_greedy_gen_dispatch_partial(self, avail_flow, gen_mods_on):
        try:
            cur_allos = [0.0 for i in range(0, self.num_gen)]
            cur_qe = [0.0 for i in range(0, self.num_gen)]
            for j in range(0, self.num_gen): #Try to get each turbine to peak efficiency
                peak_qes = [0.0 for i in range(0, self.num_gen)]
                for k in range(0, self.num_gen): #Pick the best one to turn on
                    if (avail_flow >= self.peak_gen_flows[k]) and cur_allos[k] <=0 and (gen_mods_on[k]): #If enough flow and not turned on yet
                        peak_qes[k] = self.peak_gen_flows[k]*self.gen_mods[k].peak_eff
                if max(peak_qes) > 0: #If I can ramp something
                    max_idx = np.argmax(peak_qes) #index of max increase (takes the lowest index if equal)
                    cur_allos[max_idx] = self.peak_gen_flows[max_idx]
                    avail_flow -= self.peak_gen_flows[max_idx]
                    cur_qe[max_idx] = peak_qes[max_idx]
                   
            #Modules will be ramped to peak_efficiency if they can
            #Now try to turn on any modules that are not already on 
            if (avail_flow > 0) and (0 in cur_allos):
                for j in range(0, self.num_gen): #Try to get each turbine to peak efficiency
                    min_qes = [0.0 for i in range(0, self.num_gen)]
                    for k in range(0, self.num_gen): #Pick the best one to turn on
                        if (avail_flow >= self.min_gen_flows[k]) and cur_allos[k] <=0 and (gen_mods_on[k]): #If enough flow and not turned on yet
                            min_qes[k] = self.min_gen_flows[k]*self.gen_mods[k].get_eff(self.min_gen_flows[k])
                    if max(min_qes) > 0: #If I can ramp something
                        max_idx = np.argmax(min_qes) #index of max increase (takes the lowest index if equal)
                        cur_allos[max_idx] = self.min_gen_flows[max_idx]
                        avail_flow -= self.min_gen_flows[max_idx]
                        cur_qe[max_idx] = min_qes[max_idx]
                                                
            #Now that all modules are on and potentially up to the peak efficiency point, use greedy to allocate the rest
            if avail_flow > 0:
                cum_q = 1
                for k in range(0, int(math.floor(avail_flow))): #Until we run out of flow
                    qe_inc = np.array([0.0 for n in range(0, self.num_gen)])
                    new_qes = np.array([np.nan for n in range(0, self.num_gen)])
                    for j in range(0, self.num_gen): #Try allocating flow to each module
                        new_q = cur_allos[j] + cum_q
                        if (new_q <= self.max_gen_flows[j]) and (new_q >= self.min_gen_flows[j]) and (gen_mods_on[j]): #If the added flow is within the min and max allowed flow range, then test allocating flow
                            new_qe = self.gen_mods[j].get_eff(new_q) * new_q
                            new_qes[j] = new_qe
                            qe_inc[j] = new_qe - cur_qe[j] #Calculate the increment in qe by allocating to module j
                    if max(qe_inc) <= 0: #If no module has an increase (can't ramp anything)
                        cum_q += 1
                    else:
                        max_idx = np.argmax(qe_inc) #index of max increase (takes the lowest index if equal)
                        cur_allos[max_idx] += cum_q #Allocate flow to the module with the greatest qe increase
                        cur_qe[max_idx] = new_qes[max_idx]
                        cum_q = 1
            return cur_allos
        except:
            return False
    
    ####Facility - Display functions     
    #Get the upper and lower facility bounds for the facility plot
    def get_long_fac_bounds(self):
        max_up = 0
        max_down = 0
        for m in self.pass_mods:
            if m.module_class == 'Rec':
                if max_up < (m.length/2):
                    max_up = m.length/2
                if max_down < (m.length/2):
                    max_down = (m.length/2)
            elif m.module_class == 'Fish':
                if max_up < m.length:
                    max_up = m.length
            else:
                if max_down < m.length:
                    max_down = m.length
            
        for m in [self.spill_mod, self.flush_mod, self.non_mod]:
            if m is not None:
                if max_down < m.length:
                    max_down = m.length    
        return max_up, max_down
    #Create a top-down view of the modular facility using rectangles
    def plot_facility(self, fig=None, ax=None, it=None, obj=None, title=None, hide=False):
        mod_order = ['Gen', 'Non', 'Wat', 'Spill', 'Sed', 'Fish','Rec'] 
                
        if hide == True:
            plt.ioff()
        else:
            plt.ion()
        
        if fig is None:
            fig = plt.figure()
            
        if ax is None:
            ax = fig.add_subplot(111)
        else:
            ax.clear()
        
        ax.grid(True, which='both', axis='both', linestyle='-', linewidth=1, alpha=0.3)
        xloc = plticker.MultipleLocator(base=self.fou_mod.width)
        yloc = plticker.MultipleLocator(base=self.fou_mod.length)
        ax.xaxis.set_minor_locator(xloc)
        ax.yaxis.set_minor_locator(yloc)
        
        x_offset = 10
        y_offset = 10
        x = 0
        y = 0
        recs = []
        mup, mdown = self.get_long_fac_bounds()
        
        #Diversion start
        left_div = x
        right_div = self.total_width
        
        #Plot modules
        patch_list = [] #[name, patch]
        for i in range(0, len(mod_order)):
            if mod_order[i] == 'Non':
                m = self.non_mod
                for j in range(0, self.num_non):
                    non_rec = Rectangle((x, y), m.width, -m.length, facecolor=sty.MODULE_COLORS[mod_order[i]], edgecolor='black')
                    ax.add_patch(non_rec)
                    patch_list.append([m.name, non_rec])
                    x += m.width
                    if j == 0:
                        recs.append([m.name,non_rec])
            elif mod_order[i] == 'Spill':
                #Add spillway
                m = self.spill_mod
                for j in range(0, self.num_spill):
                    if m.diversion == True:
                        spill_rec = Rectangle((right_div, y), m.width,-m.length, facecolor=sty.MODULE_COLORS[mod_order[i]], edgecolor='black',zorder=2)
                        ax.add_patch(spill_rec)
                        patch_list.append([m.name, spill_rec])
                        right_div += m.width
                        if j == 0:
                            recs.append([m.name,spill_rec])
                    else:
                        spill_rec = Rectangle((x, y), m.width, -m.length, facecolor=sty.MODULE_COLORS[mod_order[i]], edgecolor='black',zorder=2)
                        ax.add_patch(spill_rec)
                        patch_list.append([m.name, spill_rec])
                        x += m.width
                        if j == 0:
                            recs.append([m.name,spill_rec])
            elif mod_order[i] == 'Rec':
                for m in self.get_pass_class_list(mod_order[i]): 
                    for k in range(0, self.pass_dict[m.name]):
                        if m.diversion == True:
                            rec_rec = Rectangle((right_div, y), m.width, m.length, facecolor=sty.MODULE_COLORS[mod_order[i]], edgecolor='black',zorder=2)
                            rec_rec.xy = (x, y-(m.length/2))
                            ax.add_patch(rec_rec)
                            patch_list.append([m.name, rec_rec])
                            right_div += m.width
                            if k == 0:
                                recs.append([m.name,rec_rec])
                        else:
                            rec_rec = Rectangle((x, y), m.width, m.length, facecolor=sty.MODULE_COLORS[mod_order[i]], edgecolor='black',zorder=2)
                            rec_rec.xy = (x, y-(m.length/2))
                            ax.add_patch(rec_rec)
                            patch_list.append([m.name, rec_rec])
                            x += m.width
                            if k == 0:
                                recs.append([m.name,rec_rec])
            elif mod_order[i] == 'Fish':
                for m in self.get_pass_class_list(mod_order[i]): 
                    for k in range(0, self.pass_dict[m.name]):
                        if m.diversion == True:
                            fish_rec = Rectangle((right_div, y), m.width, m.length, facecolor=sty.MODULE_COLORS[mod_order[i]], edgecolor='black',zorder=2)
                            ax.add_patch(fish_rec)
                            patch_list.append([m.name, fish_rec])
                            right_div += m.width
                            if k == 0:
                                recs.append([m.name,fish_rec])
                        else:
                            fish_rec = Rectangle((x, y), m.width, m.length, facecolor=sty.MODULE_COLORS[mod_order[i]], edgecolor='black',zorder=2)
                            ax.add_patch(fish_rec)
                            patch_list.append([m.name, fish_rec])
                            x += m.width
                            if k == 0:
                                recs.append([m.name,fish_rec])
            else:
                for m in self.get_pass_class_list(mod_order[i]):
                    for k in range(0, self.pass_dict[m.name]):
                        if m.diversion == True:
                            pass_rec = Rectangle((left_div - m.width, y), m.width, -m.length, facecolor=sty.MODULE_COLORS[mod_order[i]], edgecolor='black',zorder=2)
                            ax.add_patch(pass_rec)
                            patch_list.append([m.name, pass_rec])
                            left_div -= m.width
                            if k==0:
                                recs.append([m.name,pass_rec])
                        else:
                            pass_rec = Rectangle((x, y), m.width, -m.length, facecolor=sty.MODULE_COLORS[mod_order[i]], edgecolor='black',zorder=2)
                            ax.add_patch(pass_rec)
                            patch_list.append([m.name, pass_rec])
                            x += m.width
                            if k==0:
                                recs.append([m.name,pass_rec])

        #Add patches for screens
        for j in range(0, len(self.screens)):
            for i in range(0, len(patch_list)):
                mod_name = patch_list[i][0]
                patch = patch_list[i][1]
                if self.screens[j].check_covered(mod_name):
                    x,y = patch.get_xy()
                    screen_patch = Rectangle((x,y+(2*(j+1))), patch.get_width(), 2, facecolor=sty.MODULE_COLORS['Screen'], edgecolor='black',zorder=3)
                    ax.add_patch(screen_patch)
                    if i == 0:
                        recs.append([self.screens[j].name, screen_patch])
                
        
        #Left bank
        left_bank_rec = Rectangle((left_div-x_offset,-y_offset-mdown), abs(left_div)+x_offset, (mup+mdown+(2*y_offset)), facecolor='tab:brown')
        ax.add_patch(left_bank_rec)
        #Right bank
        right_bank_rec = Rectangle((self.total_width,-y_offset-mdown), right_div+x_offset, (mup+mdown+(2*y_offset)), facecolor='tab:brown')
        ax.add_patch(right_bank_rec)
       
        recs.append(['Banks', left_bank_rec])
       
        #original bank line
        if self.total_width > self.site.stream_width:
            orig_bank = Rectangle((self.site.stream_width,-y_offset-mdown), (x_offset+self.total_width-self.site.stream_width), (mup+mdown+(2*y_offset)), facecolor='brown', alpha=0.2)
            ax.add_patch(orig_bank)
            recs.append(['Original Bank', orig_bank])
            
        ax.set_xlim(left_div-x_offset, right_div+x_offset)
        ax.set_ylim(-y_offset-mdown, mup+y_offset)
        
        for i in range(0, len(recs)):
            recs[i][1].width = 1
            recs[i][1].height = 1
                        
        lbls= [x[0] for x in recs]
        rcs = [x[1] for x in recs]
        
        if title is not None:
            ax.set_title(title)
        elif it is not None:
            ax.set_title('Iter: {} - Obj: {}'.format(it, obj)) 
        else:
            ax.set_title('SMH Facility Schematic- {}'.format(self.site.name))
            
        ax.legend(rcs, lbls, loc='upper left', bbox_to_anchor=(1,1))
        fig.tight_layout()
        ax.set_xlabel('Lateral Coordinate (ft)')
        ax.set_ylabel('Streamwise Coordinate (ft)')
        fig.subplots_adjust(bottom=0.11, left=0.11,top=0.95)
       
        if hide == False:
            fig.show()
            fig.canvas.draw()
            plt.pause(1)
         
        return fig, ax            
