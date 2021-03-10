# -*- coding: utf-8 -*-
"""
Created on Wed Oct 16 20:18:46 2019

@author: liang.xue
"""
import pandas as pd
import datetime
from portfolio_builder_sbl import SBLPortfolioBuilder
from portfolio_builder_non_sbl import NonSBLPortfolioBuilder
from config import PROJECTION_YEAR, COUNTRY_WEIGHTS_COLUMNS, OUTPUT_LIMIT_ADJUSTED_WEIGHTS_PATH, LTFP_PROJECTIONS, PROJECTION_YEAR
from utils_target_p import UtilsTgtPortfolioBuilder

def runner():

    projectionYearDict = LTFP_PROJECTIONS.get(PROJECTION_YEAR)
    sblDOBProjection = projectionYearDict.get('Loans Investments - SBL')
    n_sblDOBProjection = projectionYearDict.get('Loans Investments - NSBL')
    time_stamp = int(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
    utils = UtilsTgtPortfolioBuilder()

    sblDfOrigin = utils.originalSBLDf
    n_sblDfOrigin = utils.original_NSBLDf
    
    sbl_Builder = SBLPortfolioBuilder()
    sbl_CountryWeights = sbl_Builder.assign_country_weights_main()
    sbl_CountryWeights = utils.reOrderCountryWeightDict(sbl_CountryWeights, reverse = True) #reorder to decending by rating
    #debugging purpose
    #df_SBL_Weights = pd.DataFrame([a for a in sbl_CountryWeights.items()], columns = COUNTRY_WEIGHTS_COLUMNS)
    #df_SBL_Weights.to_excel(r"testing_output_sbl_weight_{0}.xlsx".format(time_stamp), 'SBL', index=False)

    nsbl_Builder = NonSBLPortfolioBuilder(sbl_CountryWeights)
    nsbl_CountryWeights = nsbl_Builder.assign_country_weights_main()
    nsbl_CountryWeights = utils.reOrderCountryWeightDict(nsbl_CountryWeights, reverse = True) #reorder to decending by rating

    df_SBL_Weights = pd.DataFrame([a for a in sbl_CountryWeights.items()], columns = COUNTRY_WEIGHTS_COLUMNS)
    df_N_SBL_Weights = pd.DataFrame([a for a in nsbl_CountryWeights.items()], columns = COUNTRY_WEIGHTS_COLUMNS)

    df_SBL = pd.merge(df_SBL_Weights, sblDfOrigin, on='Country_ISO', how='left')
    df_SBL.drop(['SBL_Weights'], axis=1, inplace=True)
    df_SBL.drop_duplicates(keep=False,inplace=True, subset=['Country_ISO']) 
    df_SBL['SBF_Amount'] = sblDOBProjection * df_SBL['Weight']

    df_N_SBL = pd.merge(df_N_SBL_Weights, n_sblDfOrigin, on='Country_ISO', how='left')
    df_N_SBL.drop(['NSBL_Rating', 'NSBL_PD', 'NSBL_Rating_Round', 'NSBL_Weights'], axis=1, inplace=True)
    df_N_SBL.drop_duplicates(keep=False,inplace=True, subset=['Country_ISO']) 
    df_N_SBL['NSBF_Amount'] = n_sblDOBProjection * df_N_SBL['Weight']

    writer = pd.ExcelWriter(OUTPUT_LIMIT_ADJUSTED_WEIGHTS_PATH.format(PROJECTION_YEAR, time_stamp), engine='xlsxwriter') # pylint: disable=abstract-class-instantiated
    df_SBL.to_excel(writer, 'SBL', index=False)
    df_N_SBL.to_excel(writer, 'NSBL', index=False)

    writer.save()

if __name__ == "__main__":
    runner()
    