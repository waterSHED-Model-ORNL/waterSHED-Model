# -*- coding: utf-8 -*-
"""
Last updated on April 25 2022

@author: Colin Sasthav
"""

#%%## Colors

TITLE_BG_COLOR = 'light gray'
SUBTITLE_BG_COLOR = 'ivory2'
LINK_FG_COLOR = 'blue'
SIDEBAR_BG_COLOR = 'forest green'
FRAME_BG_COLOR = 'white'
LABEL_BG_COLOR = 'white'
DYNAMIC_MODULE_BG_COLOR = 'azure2'
CHECK_BG_COLOR = 'white'
DIRECTIONS_BG_COLOR = 'honeydew2'
DYNAMIC_BOX_COLOR = 'white smoke'
MODULE_COLORS ={'Gen': 'mediumseagreen', 'Non':'gray', 'Wat':'cornflowerblue', 'Sed': 'darkkhaki',\
                'Fish':'peru', 'Rec':'mediumpurple', 'Fou':'saddlebrown','Spill': 'royalblue', 'Screen':'salmon'}

#%%## Fonts
PG_TITLE_FONT = ("Verdana", 20)
TEXT_FONT = ("Verdana", 10)
TEXT_BOLD_FONT = ("Verdana", 10, "bold")
TEXT_ITALICS_FONT = ("Verdana", 10, "italic")
SUBTITLE_FONT = ("Verdana", 12, "bold")
LINK_FONT = ("Verdana", 12, "bold")

#%%## Formatting Functions
def format_value(value, format_type, unit=None): #[value, 'format type', 'unit']
    out = ''
    if (value is None) or (value == '') or (value == 'N/A'):
        return 'N/A'
    
    if format_type == 'dollar':
        out += format_dollar(value)
    elif format_type == 'cents':
        out += format_dollar(value, cents=True)
    elif format_type == 'percent':
        out += format_percent(value)
    elif format_type == 'percent-4':
        out += format_percent(value, two_digits=True)
    elif format_type == 'str':
        out += value
    elif format_type == 'int':
        out += str(value)
    elif format_type == 'comma':
        out += format_comma(int(value))
    elif format_type == 'comma-dec':
        out += format_comma(value)
    elif format_type == 'round':
        out += str(round(value))
    elif format_type == 'round-2':
        out += str(round(value, 2))
    elif format_type == 'round-4':
        out += str(round(value, 4))
    else:
        print('Error in value format')
    
    if unit is not None:
        out += unit
    return out

def format_dollar(val, cents=False):
    if cents:
        return '${:,.2f}'.format(val)
    else:
        return '${:,.0f}'.format(val)

def format_percent(val, two_digits=False):
    if two_digits:
        return '{0:.2%}'.format(val)
    else:   
        return '{0:.0%}'.format(val)
def format_comma(val):
    return '{:,}'.format(val)
    