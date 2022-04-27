# -*- coding: utf-8 -*-
"""
Last updated on April 25 2022

@author: Colin Sasthav
"""
#%%## IMPORT PACKAGES
import module_classes as mc
import pandas as pd
import requests
import io
import math
import numpy as np
from scipy import stats
from scipy.optimize import curve_fit

#%%## Helpful functions
#Finds a value of y for a given x using a linear interpolation of the sets x_s and y_s
def linear_interpolation(x, x_s, y_s): #x_s should be sorted
    for i in range(0, len(x_s)-1):
        if ((x >= x_s[i]) and (x < x_s[i+1])) or ((x < x_s[i]) and (x >= x_s[i+1])):
            slope = (y_s[i+1] - y_s[i])/(x_s[i+1] - x_s[i])
            return slope*(x-x_s[i]) + y_s[i]
    return False   

def linear(x, a, b):
    return (a*x) + b

def power(x, a, b, c):
    return (a*(x**b)) + c

def poly_2(x, a, b, c):
    return (a*(x**2)) + (b*x) + c

def poly_3(x, a, b, c, d):
    return (a*(x**3)) + (b*(x**2)) + (c*x) + d

#Checks if all values in a list are equal
def check_all_equal(val_list):
    if len(val_list) > 0 :
        result = all(elem == val_list[0] for elem in val_list)
        return result
    else:
        return False
#Uses a custom process the automatically regress data in a dataframe to one of the following equation types: Linear, Power, and 2 degree Polynomial
#Returns an Equation Object from the module classes script
#Inputs include the equation name, a dataframe, the x metric column name, the y metric column name, an r2 threshold used to prioritize lower complexity equations, and a remove_negative option that will remove negative values from the data
def auto_regression(eq_name, in_data, x_metric, y_metric, r2_threshold=0.97, remove_negative=False): 
    min_sample_size = 2 #Only runs model if length of data is greater than this
    r2_threshold = r2_threshold
    model_types = ['Linear', 'Power', 'Polynomial-2', 'Polynomial-3']
    model_fns = [linear, power, poly_2, poly_3]
    z_score_max = 3 
    #Initialize vars to keep track of best model
    best_coeffs = []
    best_r2 = -100
    model_type = ''
    best_y_pred = [0]
   
    data, outliers = remove_outliers(in_data, [x_metric, y_metric],z_score_max,remove_negative=remove_negative)
    x = data[x_metric].to_numpy()
    y = data[y_metric].to_numpy()
    
    if len(y) < min_sample_size:
        return 'Sample size too small'
    else:
        for i in range(0, len(model_types)):
            try:
                popt, pcov = curve_fit(model_fns[i], x, y)
                y_pred = model_fns[i](x, *popt)
                res = y - y_pred
                ss_res = np.sum(res**2)
                ss_tot = np.sum((y-np.mean(y))**2)
                r2 = 1.0 - (ss_res/ss_tot)
                
                if r2 > best_r2:
                    best_r2 = r2
                    model_type = model_types[i]
                    best_coeffs = popt
                    best_y_pred = y_pred
                    
                if best_r2 > r2_threshold:
                    break
            except:
                pass
            
    if best_r2 < 0:
        return 'Unable to determine an adequate regression relationship.'
                        
    regr_results = {'Predicted Y': best_y_pred, 'R2':best_r2, 'Data Count': len(data),'Outlier Count': len(outliers)}
    #Currently sets the bounds as the in_data bounds not the data used for regression
    out_eq = mc.Equation(eq_name, model_type, best_coeffs, x_metric, y_metric, min(in_data[x_metric]), max(in_data[x_metric]), in_data, regr_results)
    return out_eq

#Removes outliers from a dataset if the z-score is above a given threshold
#Returns the cleaned dataframe and the outliers dataframe
def remove_outliers(df, metrics, threshold, remove_negative=False):
    df_in = df.copy().reset_index()
    result = df_in.dropna(subset=metrics)    
    for i in metrics:
        result['z-score'] = np.abs(stats.zscore(result[i]))
        if remove_negative == True:
            result = result[(result['z-score'] <= threshold) & (result[i] > 0)]
        else:
            result = result[result['z-score'] <= threshold]
    outliers = df_in[~df_in.index.isin(result.index)]
    result = result.reset_index(drop=True)
    return result, outliers 


#%%## USGS Flow API Retrieval Functions

#When provided a USGS station ID, typically a string of 8 numbers, will scrub the USGS peak flow data API for flood flows if available
#Station_id = String, show_dialogue = True or False
#If successful, returns a dataframe with ['dateTime', 'Discharge', 'Stage'] and a diagnostic dict
#If unsuccessful, returns an empty list and a diagnostic dict with the error message
def get_peak_USGS_data(station_id, show_dialogue=False):
    diag_dict = {}
    try:
        peak_url = 'https://nwis.waterdata.usgs.gov/nwis/peak?site_no={}&agency_cd=USGS&format=rdb'.format(station_id)
        try:
            r = requests.get(peak_url)
        except:
            peak_data = [] 
            diag_dict['Error'] ='Unable to access USGS API. Please check internet connection.'
            if show_dialogue:
                print('Peak flow data retrieval: UNSUCCESSFUL')
            return peak_data, diag_dict
            
        peakData = pd.read_table(io.StringIO(r.text),skiprows=r.text.count('\r\n#') + 1)
        peakData = peakData[['peak_dt', 'peak_va', 'gage_ht']]
        peakData.columns = ['dateTime','Discharge (cfs)', 'Stage (ft)']
        peakData = peakData[1:]
        peakData['dateTime'] = pd.to_datetime(peakData['dateTime'], format='%Y-%m-%d')
        peakData = peakData.set_index('dateTime')
        peakData['Discharge (cfs)'] = peakData['Discharge (cfs)'].astype(float)
        peakData['Stage (ft)'] = peakData['Stage (ft)'].astype(float)
        
        earliest_date = peakData.index.min()
        latest_date = peakData.index.max()
        num_data_points = len(peakData.index)
        diag_dict = {'Earliest Date': earliest_date, 'Latest Date': latest_date, 'Data Count': num_data_points}
        
        if show_dialogue == True:
            print('Peak flow data retrieval: SUCCESSFUL')
            print('Earliest Date: {}'.format(earliest_date))
            print('Latest Date: {}'.format(latest_date))
            print('Number of Data Points: {}'.format(num_data_points))
            
        peakData.reset_index(inplace=True)
    except:
        if show_dialogue:
            print('Peak flow data retrieval: UNSUCCESSFUL')
        peakData = []
        diag_dict['Error'] = 'Error converting USGS data into a Dataframe due to unexpected data structure.'
    return peakData, diag_dict

#When provided a USGS station ID and a date range, this will look for stage-discharge data by first scrubbing the daily USGS data and then the instantaneous (15-min) flow data API if daily is not available
#This function is used for stage-discharge curves, so missing dates are not filled
#Station_id = String, start_date and end_dates = string in 'YYYY-MM-DD' format, show_dialogue = True or False
#If successful, returns a dataframe with ['dateTime', 'Discharge', 'Stage'] and a diagnostic dict
#If unsuccessful, returns an empty list and a diagnostic dict with the error message
def get_stage_USGS_data(station_id, start_date, end_date, show_dialogue=False):
    daily_data, daily_diag_dict = get_daily_USGS_data(station_id, start_date, end_date, show_dialogue=show_dialogue)
    if len(daily_data) > 0:
        if len(daily_data.columns) > 2: #Has stage data
            daily_diag_dict['Source'] = 'Daily'
            return daily_data, daily_diag_dict
    
    #If daily didn't return stage data
    inst_data, inst_diag_dict = get_inst_USGS_data(station_id,start_date, end_date, show_dialogue=show_dialogue)
    if len(inst_data) > 0:
        if len(inst_data.columns) > 2: #Has stage data
            inst_diag_dict['Source'] = 'Instantaneous'
            return inst_data, inst_diag_dict
        
    #If instantaneous didn't work either
    diag_dict = {'Error': 'Unable to retrieve data from the Daily or Instantaneous data sources.', 'Daily Diag Dict': daily_diag_dict, 'Instantaneous Diag Dict': inst_diag_dict}
    return [], diag_dict

#When provided a USGS station ID and a date range, this will scrub the USGS instantaneous (15-min) flow data API for flows if available
#This function is used for stage-discharge curves, so missing dates are not filled
#Station_id = String, start_date and end_dates = string in 'YYYY-MM-DD' format, show_dialogue = True or False
#If successful, returns a dataframe with ['dateTime', 'Discharge', 'Stage'] and a diagnostic dict
#If unsuccessful, returns an empty list and a diagnostic dict with the error message
def get_inst_USGS_data(station_id, start_date, end_date, show_dialogue=False):
    diag_dict = {}
    try:
        try:
            inst_url = 'https://waterservices.usgs.gov/nwis/iv/?format=json&sites={}&startDT={}&endDT={}&parameterCd=00060,00065&siteStatus=all'.format(station_id, start_date, end_date)
            r = requests.get(inst_url)
            j = r.json()
        except:
            inst_data = [] 
            diag_dict['Error'] ='Unable to access USGS API. Please check internet connection.'
            if show_dialogue:
                print('Instantaneous flow data retrieval: UNSUCCESSFUL')
            return inst_data, diag_dict
        

        no_data_value = j['value']['timeSeries'][0]['variable']['noDataValue']
        
        discharge = j['value']['timeSeries'][0]['values'][0]
        dis_df = pd.DataFrame.from_dict(discharge['value'])
        dis_df.pop('qualifiers')
        stage = j['value']['timeSeries'][1]['values'][0]
        stage_df = pd.DataFrame.from_dict(stage['value'])
        stage_df.pop('qualifiers')
        
        #Example: 2010-01-01T00:45:00.000-05:00
        dis_df['dateTime'] = dis_df['dateTime'].map(lambda x: x[0:-10])
        stage_df['dateTime'] = stage_df['dateTime'].map(lambda x: x[0:-10])
        stage_df['dateTime'] = pd.to_datetime(stage_df['dateTime'], format='%Y-%m-%dT%H:%M:%S')
        dis_df['dateTime'] = pd.to_datetime(dis_df['dateTime'], format='%Y-%m-%dT%H:%M:%S')
        
        inst_data = pd.merge(dis_df, stage_df, how='inner', on='dateTime')
        inst_data.columns = ['Discharge (cfs)','dateTime', 'Stage (ft)']
        
        inst_data['Discharge (cfs)'] = inst_data['Discharge (cfs)'].astype(float).fillna(no_data_value)
        inst_data['Stage (ft)'] = inst_data['Stage (ft)'].astype(float).fillna(no_data_value)
        
        pre_dis_len = len(inst_data)
        inst_data = inst_data[inst_data['Discharge (cfs)'] != no_data_value]
        post_dis_len = len(inst_data)
        dis_missing = pre_dis_len - post_dis_len
        inst_data = inst_data[inst_data['Stage (ft)'] != no_data_value]
        stg_missing = post_dis_len - len(inst_data) 
        inst_data = inst_data.set_index('dateTime')
        
        earliest_date = inst_data.index.min()
        latest_date = inst_data.index.max()
        dt_range = pd.date_range(start=earliest_date, end=latest_date)
        missing_dates = dt_range.difference(inst_data.index)
        num_missing = len(missing_dates)
        year_count = latest_date.year - earliest_date.year
        num_data_points = len(inst_data.index)
    
        diag_dict = {'Earliest Date': earliest_date, 'Latest Date': latest_date, 'Years of Data': year_count, 'Number of Data Points': num_data_points, \
                     'Number of Discharge Missing': dis_missing, 'Number of Stage Missing': stg_missing, 'Number of Dates Missing': num_missing}
    
        if show_dialogue == True:
            print('Instantaneous flow data retrieval: SUCCESSFUL')
            print('\nEarliest Date: {}'.format(earliest_date))
            print('Latest Date: {}'.format(latest_date))
            print('Years of Data: {}'.format(year_count))
            print('Number of Data Points: {}'.format(num_data_points))
        
        inst_data.reset_index(inplace=True)
    except:
        if show_dialogue:
            print('Instantaneous flow data retrieval: UNSUCCESSFUL')
        inst_data = []
        diag_dict['Error'] = 'Error converting USGS data into a Dataframe due to unexpected data structure.'
    
    return inst_data, diag_dict

#When provided a USGS station ID and a date range, this will scrub the USGS daily flow data API for flows if available
#This function is used for timeseries, so missing dates are not filled. If stage data is available it will be gathered
#Station_id = String, start_date and end_dates = string in 'YYYY-MM-DD' format, show_dialogue = True or False
#If successful, returns a dataframe with ['dateTime', 'Discharge', 'Stage'], although 'Stage' will only be present if availble, and a diagnostic dict
#If unsuccessful, returns an empty list and a diagnostic dict with the error message
def get_daily_USGS_data(station_id, start_date, end_date, show_dialogue=False):
    diag_dict = {}
    try:
        try:
            daily_url = 'https://waterservices.usgs.gov/nwis/dv/?format=json&sites={}&startDT={}&endDT={}&parameterCd=00060,00065&siteStatus=all'.format(station_id, start_date, end_date)
            r = requests.get(daily_url)
            d = r.json()
        except:
            daily_data = [] 
            diag_dict['Error'] ='Unable to access USGS API. Please check internet connection.'
            if show_dialogue:
                print('Daily flow data retrieval: UNSUCCESSFUL')
            return daily_data, diag_dict
        
        no_data_value = d['value']['timeSeries'][0]['variable']['noDataValue']
        
        discharge = d['value']['timeSeries'][0]['values'][0]
        daily_data = pd.DataFrame.from_dict(discharge['value'])
        daily_data.pop('qualifiers')
        
        #Example: 2010-01-01T00:45:00.000-05:00
        daily_data['dateTime'] = daily_data['dateTime'].map(lambda x: x[0:-10])
        daily_data['dateTime'] = pd.to_datetime(daily_data['dateTime'], format='%Y-%m-%dT%H:%M:%S')
        daily_data.columns = ['Discharge (cfs)', 'dateTime']
        daily_data['Discharge (cfs)'] = daily_data['Discharge (cfs)'].astype(float).fillna(no_data_value)
        daily_data = daily_data[daily_data['Discharge (cfs)']!= no_data_value]
        daily_data = daily_data.set_index('dateTime')
        
        earliest_date = daily_data.index.min()
        latest_date = daily_data.index.max()
        dt_range = pd.date_range(start=earliest_date, end=latest_date)
        missing_dates = dt_range.difference(daily_data.index)
        num_missing = len(missing_dates)
        year_count = latest_date.year - earliest_date.year
        if len(missing_dates) > 0:
            daily_data.reindex(dt_range).fillna(method='ffill')
            
        num_data_points = len(daily_data)
        diag_dict = {'Earliest Date': earliest_date, 'Latest Date': latest_date, 'Years of Data': year_count, 'Number of Data Points': num_data_points, \
                     'Number of Discharge Missing': num_missing}
        
    
        if len(d['value']['timeSeries']) > 1: #Has stage data
            if d['value']['timeSeries'][1]['variable']['variableName'] != 'Gage height, ft':
                diag_dict['Original Stage Variable Name'] = d['value']['timeSeries'][1]['variable']['variableName']
                if show_dialogue:
                    print('Actual variable name (interpreted as Stage (ft) ' +  d['value']['timeSeries'][1]['variable']['variableName'])
                
            stage = d['value']['timeSeries'][1]['values'][0]
            stage_data = pd.DataFrame.from_dict(stage['value'])
            stage_data.pop('qualifiers')
            #Example: 2010-01-01T00:45:00.000-05:00
            stage_data['dateTime'] = stage_data['dateTime'].map(lambda x: x[0:-10])
            stage_data['dateTime'] = pd.to_datetime(stage_data['dateTime'], format='%Y-%m-%dT%H:%M:%S')
            stage_data.columns = ['Stage (ft)', 'dateTime']
            stage_data['Stage (ft)'] = stage_data['Stage (ft)'].astype(float).fillna(no_data_value)
            pre_stg_num = len(stage_data)
            stage_data = stage_data[stage_data['Stage (ft)']!= no_data_value]
            num_stage = len(stage_data)
            
            num_stg_missing = pre_stg_num - len(stage_data)
            diag_dict['Original Stage Number'] = num_stage
            diag_dict['Original Stage Missing'] =  num_stg_missing
            
            stage_data = stage_data.set_index('dateTime')
            
            ##Pairs the stage data to the daily data, if the stage data doesn't have a flow date match, then it is not kept
            daily_data = daily_data.merge(stage_data, how='left', left_index=True, right_index=True)
            if daily_data.sum(axis=0, skipna=True)['Stage (ft)'] <= 0: #No matching stage
                daily_data.drop('Stage (ft)', axis=1, inplace=True)
            else:
                diag_dict['Matching Stage Number': daily_data.count()['Stage (ft)']]
                if show_dialogue:
                    print('Stage added')   
                
        if show_dialogue == True:
            print('Daily flow data retrieval: SUCCESSFUL')
            print('\nEarliest Date: {}'.format(earliest_date))
            print('Latest Date: {}'.format(latest_date))
            print('Years of Data: {}'.format(year_count))
            print('Number of Missing Dates (Initially): {}'.format(len(missing_dates)))
    
        daily_data.reset_index(inplace=True)
    except:
        if show_dialogue:
            print('Daily flow data retrieval: UNSUCCESSFUL')
        daily_data = []
        diag_dict['Error'] = 'Error converting USGS data into a Dataframe due to unexpected data structure.'
    return daily_data, diag_dict

#%%## Sediment Functions

#Probability of entrainment model
#Calculates the probability of entrainment for a particle size at a given site
#The inputs are slope (ft/ft), particule size in mm, and a stage equation as an Equation Object
#Returns a list of flows and a list of probabilities
def calc_entrainment_eq(slope, size, stage_eq): 
    size = size/1000 #convert size to meters    
    if size <= .002: #Fine
        T_max = 1.727
        Rp = (size/(1.31*(10**-6)))*(((2650/1000)-1)*9.81*size)**0.5
        T_c = 0.22*(Rp**-0.6)+0.06*(10**(-7.7*(Rp**-0.6)))
        
    else: #Coarse
        T_max = 0.509
        T_c = math.cos(math.radians(slope))/89.8
        
    X_c = np.log(T_c)
    # X_m = np.log(T_max)
    X_bar = 0.5*np.log(T_max*T_c)
    O_x = (1/6)*np.log(T_max/T_c)
    mc = (X_c-X_bar)/O_x
    
    flow_step = 10
    if stage_eq.ub is not None:
        max_flow = stage_eq.ub
    else:
        max_flow = 100000
        
    Q_list = list(range(0, int(max_flow), flow_step))
    P_list = []

    for q in Q_list:
        if q == 0:
            P_list.append(0)
        else:
            h = stage_eq.get_y(q) * 0.3048
            if h is False: #If error, default to zero
                P_list.append(0)
            else:
                T_s = 1000*slope*h/((2650-1000)*size)
                if T_s < T_c:
                    P_list.append(0)
                elif T_s > T_max:
                    P_list.append(100)
                else:
                    X = np.log(T_s)
                    m = (X - X_bar)/O_x
                    P = (1+math.exp(-0.07056*(m**3)-1.5976*m))**-1 - (1+math.exp(-0.07056*(mc**3)-1.5976*mc))**-1
                    P_list.append(P*100)
                
    return Q_list, P_list

#%%##Geometric reservoir volume model
#Creates a stage-storage equation object based on the following inputs
#Slope (ft/ft), river width, and gemoetric coefficient between 0-1
#Returns an equation object
def geometric_reservoir_volume(slope, width, coeff):
    a = coeff * width / slope
    out_eq = mc.Equation('Geometric Stage-Storage', 'Power', [a, 2, 0], 'Normal Operating Level (ft)', 'Reservoir Volume (ft3)')
    return out_eq