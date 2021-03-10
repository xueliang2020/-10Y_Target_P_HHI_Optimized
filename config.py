# -*- coding: utf-8 -*-
"""
Created on Wen Oct 16 21:21:31 2019

@author: liang.xue
"""
#TODO: this config is the input projection year number which need user to input
PROJECTION_YEAR = 2030

INPUT_LOCATION = r"C://Working//python//Target_Portfolio_VOct202020_20210309Updated//"

#INPUT_FILENAME = r'input_initial_weights_2020-Sep.xlsx'
#added this input for testing purpose to remove the GDP model China pre-adjustment process
INPUT_FILENAME = r'Input_Weights_GDP_Process_20210309.xlsx'
#INPUT_INITIAL_WEIGHTS_FILENAME = r"input_initial_weights_2020-Oct.xlsx" #initial weights from GDP proxy s/s model
INPUT_INITIAL_WEIGHTS_FILENAME = r'Input_Weights_GDP_Process_20210309.xlsx'
INPUT_INS_CREATOR_FILENAME = r"Result_Target_Portfolio_Country_Weights_YEAR_{0}.xlsx" #result weights from limits adjustments python codes
INPUT_TABLE_TAB = r"CountryWeightsResult"

OUTPUT_LIMIT_ADJUSTED_WEIGHTS_PATH = r"C://Working//python//Target_Portfolio_VOct202020_20210309Updated//Result_TargetP_{0}_{1}.xlsx"
OUTPUT_RF_IN_PORTFOLIO_PATH = r"C://Working//python//Target_Portfolio_VOct202020_20210309Updated//Result_Final_RF_PORTFOLIO_{0}_NonRegional_Cap.xlsx"

COUNTRY_WEIGHTS_COLUMNS = ['Country_ISO','Weight']
OUTPUT_PATH_FINAL = r'C://Working//python//Target_Portfolio_VOct202020_20210309Updated//Result_Target_Portfolio_Country_Weights_YEAR_{0}_{1}_NonRegional_Cap.xlsx'


ADJUSTMENT_FACTOR_RISK_LIMIT = 0.0001#0.0001
MANDATE_RATING = {
        'SBL': 6,
        'NSBL': 7,
}

RISK_LIMIT_DICT_SPB_ASSUMPTIONS = {
            'China':{
                    'SBL':0.1, #China share will be 10% within SBL share
                    'NSBL':0.1, #China share will be 10% within NSBL share
            },
            #assumption 1: 15% (0.14999)for SBF, 15% (0.071499940) for NSBF
            'Non_Regional':{
                    'SBL':0.15,#0.0499, #Non-Regional will be 5% within SBL share
                    'NSBL':0.15,#0.0999, #Non-Regional will be 10% within NSBL share
            }
        }

RISK_LIMIT_DICT_SBL = {
            'Single_Sovereign_Limit': 0.5,#0.23,#0.5, #Level 1: Sovereign backed Exposure Limit: Single sovereign backed exposure/ Available Capital
            'Top_3_Sovereign_Limit': 0.8999,#0.4,#0.9, #Level 1: Sovereign backed Exposure Limit: Top 3 sovereign backed exposures/ Available Capital
            'Top_5_Obligor_Limit': 0.6,#0.6, #0.6 #Level 2: Concentration by top 5 banking book obligors against total DOB (SBL+NSBL)
            'Country_Exposure_Limit': 0.5
        }

#based on disbursement and outstanding 'DOB'
#updated on Sep 2020 based on Aug 2020 version LTFP that updated on Aug 2020 by Yunan, Gao
LTFP_PROJECTIONS = {
    #TODO: update the 2033 data
    2030:{
        'Available_Capital':24754, #paid-in capital = 20,000,  retained earnings = 9,011
        'Treasury Portfolio':38012,
        'Loans Investments - SBL':  39952,#59686,#51140, # total SBL Loan DOB 
        'Loans Investments - NSBL': 17219,#32912,#27599, # total NSBL Loan DOB
        'Equity investments': 2508,
        'Bond Investments':167,
        'Other assets':56
    },
    2022:{
        'Available_Capital':24754, #paid-in capital = 20,000,  retained earnings = 9,011
        'Treasury Portfolio':38012,
        'Loans Investments - SBL':  39952,#59686,#51140, # total SBL Loan DOB 
        'Loans Investments - NSBL': 17219,#32912,#27599, # total NSBL Loan DOB
        'Equity investments': 2508,
        'Bond Investments':167,
        'Other assets':56
    }

}

Rating_PD_Dict = {
    1:0.0003,
    2:0.000978,
    3:0.001439,
    4:0.002534,
    5:0.004427,
    6:0.007419,
    7:0.012487,
    8:0.024417,
    9:0.045755,
    10:0.086656,
    11:0.294341,
    12:1
}