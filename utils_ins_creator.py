# -*- coding: utf-8 -*-
"""
Created on Mon Feb 25 16:20:03 2019

@author: liang.xue
"""
import pandas as pd
import numpy as np
from utils_math import UtilsMath
from config import Rating_PD_Dict, INPUT_LOCATION, INPUT_TABLE_TAB, OUTPUT_RF_IN_PORTFOLIO_PATH, PROJECTION_YEAR
from config_gdp_proxy import LIMIT_CONFIG, GCORR_SECTORS, CTYISO_GCORR_CTY_MAPPING, CF_RSQ_MAPPING, PF_RSQ_MAPPING, NSBL_UNIFORM_TYPES, NSBL_PF_TYPES

#INPUT_INS_CREATOR_FILENAME = r"2030_Hypothetical_Portfolio_non-regional=SBL-15_NSBL-15.xlsx"

INPUT_INS_CREATOR_FILENAME = r"2030_Hypothetical_Portfolio_non-regional=SBL-15_NSBL-15_Approval=60-40.xlsx"

class UtilsInsCreator(object):
    """Creating Instruments based on the initial input Country Weights and Other Parameters
    """
    def __init__(self, isGetSBL):
        inputFile = INPUT_LOCATION + INPUT_INS_CREATOR_FILENAME.format(PROJECTION_YEAR)
        self.dataDf = self._getInputDF(inputFile, isGetSBL)
        self.utilsMath = UtilsMath()
        #self.nsblCnt = nsblCnt
        print('')

    def _getInputDF(self, inputFile, isGetSBL = True):
        dataTab = 'SBL' if isGetSBL else 'NSBL'
        xls = pd.ExcelFile(inputFile)
        return xls.parse(dataTab, skiprows=0, index_col=None, na_values=['NA'])

    def _getExposure(self, isGetSBL = True, isGetWeights = True):
        """
            - isGetWegights: 
                :: if Ture, the input will get SBL / NSBL weights, if False, it will get absolute DOB amount
        """
        weightsType = 'Weight'#'SBF_Weights' if isGetSBL else 'NSBF_Weights'
        amtType =  'SBF_Amount' if isGetSBL else 'NSBF_Amount'

        exposure = weightsType if isGetWeights else weightsType

        dataDf = self.dataDf[['Country_ISO', 'GDPPP_Tier', amtType, weightsType]]
        dataDf = dataDf[(dataDf[[exposure]] != 0).all(1)] #drop zero rows if NSBL weights is 0
        dataDf =  dataDf.sort_values(by=exposure, ascending=False) 
        return dataDf.reset_index()

    def _drawForList(self, drawType, dataNumbers):
        """drawType: Sector, NSBLType, PFType
        """
        #categoryCnt = len(GCORR_SECTORS) if drawType == 'Sector' else 4
        #typeCnt = NSBL_UNIFORM_TYPES
        if drawType == 'Sector':
            categoryCnt = len(GCORR_SECTORS)#categoryCnt = len(GCORR_SECTORS)
        elif drawType == 'NSBLType':
            categoryCnt = len(NSBL_UNIFORM_TYPES)
        elif drawType == 'PFType':
            categoryCnt = len(NSBL_PF_TYPES)
        else:
            return []

        return self.utilsMath.drawUniformDiscreteDataset(1, categoryCnt, dataNumbers).tolist()

    def _generateInsCharcs(self, dataDf, isGetSBL = True):
        category = 'SBF' if isGetSBL else 'NSBF'

        insList = []
        for index, row in dataDf.iterrows():
            gdpTier = row['GDPPP_Tier']
            dealSize = LIMIT_CONFIG['AVG_SIZE'].get(category, None).get(gdpTier, None)

            if category == 'SBF':
                residualSize = (row['SBF_Amount'] % dealSize)
                intCnt = int( row['SBF_Amount'] / dealSize)
                dealCnt = intCnt + 1 if (row['SBF_Amount'] % dealSize) != 0 else 0
            else:
                residualSize = (row['NSBF_Amount'] % dealSize)
                intCnt = int( row['NSBF_Amount'] / dealSize)
                dealCnt = intCnt + 1 if (row['NSBF_Amount'] % dealSize) != 0 else 0             
                #residualCnt = 1 if (row.SBL_Amount % dealSize) != 0 else 0

            for item in range(1, intCnt + 1):
                #if category == 'SBL':
                insList.append([row['Country_ISO'], dealSize])
                #else:
                #    insList.append([row.Country_ISO, dealSize])
            #print(row)
            if dealCnt != intCnt:
                insList.append([row['Country_ISO'], residualSize])

        if category == 'SBF':
            dataframe = pd.DataFrame(insList, columns = ['Country','DOB'])
            #dataframe['DOB'] = 1000000 * dataframe['DOB']
        else:
            nsblCnt = len(insList)
            sectorTypes = self._drawForList('Sector', nsblCnt)
            nsblTypes = self._drawForList('NSBLType', nsblCnt)

            pfCnt = len([True for item in nsblTypes if item == 1])
            pfTypes = self._drawForList('PFType', pfCnt)

            itemList = []
            for oldInsList, sectorIndex, ntypeIndex in zip(insList, sectorTypes, nsblTypes):
                try:

                    sectorName = GCORR_SECTORS[sectorIndex - 1]
                    proxyCty = CTYISO_GCORR_CTY_MAPPING[oldInsList[0]]

                    nsblType = NSBL_UNIFORM_TYPES[ntypeIndex - 1] if ntypeIndex !=1 else NSBL_PF_TYPES[pfTypes.pop(0) - 1]

                    cfRsq = CF_RSQ_MAPPING[proxyCty + "-" + sectorName]
                    pfRsq = PF_RSQ_MAPPING.get(nsblType, 0)
                    rsq = cfRsq if nsblType == 'CF' else pfRsq
                    itemList.append(oldInsList + [GCORR_SECTORS[sectorIndex-1], rsq, nsblType])
                except Exception as e:
                    print(e)
            print('')
            #for item in insList:
            #NSBL_TYPE_MAPPING.get(), PF_RFQ_MAPPING
            dataframe = pd.DataFrame(itemList, columns = ['Country','DOB', 'Sector', 'RSQ', 'NSBL_TYPE'])

        dataframe['DOB'] = 1000000 * dataframe['DOB']
        return dataframe

def create_output(isGetSBL = True):
    ins_type = "SBL" if isGetSBL else "NSBL"
    utils = UtilsInsCreator(isGetSBL)
    dataDf = utils._getExposure(isGetSBL, False)
    resultDf = utils._generateInsCharcs(dataDf, isGetSBL)
    resultDf.to_excel(OUTPUT_RF_IN_PORTFOLIO_PATH.format(ins_type), index = None, header=True, sheet_name='RawResult')
    print(resultDf)
    return None

def main_ins_creator():
    create_output(True)
    create_output(False)

if __name__ == "__main__":
    main_ins_creator()