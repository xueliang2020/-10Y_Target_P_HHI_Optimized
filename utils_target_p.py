# -*- coding: utf-8 -*-
"""
Created on Mon Feb 25 16:20:03 2019

@author: liang.xue
"""
import pandas as pd
import numpy as np
from config import Rating_PD_Dict, INPUT_LOCATION, INPUT_INITIAL_WEIGHTS_FILENAME, INPUT_TABLE_TAB, MANDATE_RATING, INPUT_FILENAME

class UtilsTgtPortfolioBuilder(object):
    def __init__(self):
        inputFile = INPUT_LOCATION + INPUT_INITIAL_WEIGHTS_FILENAME
        self.dataDf = self._getInputDF(inputFile)

        self.sblRatingPDDict = None #mapping between SBL rating and PD

        self.nsblRatingList = None
        self.nsblRatingPDDict = None #mapping between NSBL avg rating and avg PD  (avg means avg between Corporate Finance and Project Finance)
        self.nsblRatingPrePCT_PDDict = None # #maping between NSBL before PCT rating and NSBL avg PD
        self.nsblRoundRatingPDDict = None #mapping between rounded NSBL avg rating and avg PD

        self.nsblCountryRatingDict = None
        self.nsblCountryPDDict = None
        
        self.regionalMemList = None
        self.nonRegionalMemList = None
        
        self.originalSBLDf = self._getSBLDf()
        self.original_NSBLDf = self._getNSBLDf()

        self.originalCountryWeightsSBL = self.getOriginalCountryWeights()
        self.originalCountryWeights_NSBL = self.getOriginalCountryWeights(isGetSBL = False)
        self.countryTierMapping = self.getCountryTier()
        
        self.regionalMemList = self.getMemberList(isGetRegional = True)
        self.nonRegionalMemList = self.getMemberList(isGetRegional = False)
        
        self.sblCountryRatingDict = self.getCountryRatingDict(isGetSBL = True)
        self.nsblCountryRatingDict = self.getCountryRatingDict(isGetSBL = False)

        self.sblCountryLGDDict = self.getCountryLGDDict(isGetSBL = True)
        self.nsblCountryLGDDict = self.getCountryLGDDict(isGetSBL = False)

        self.sblCountryPDDict = self.getCountryPDDict(isGetSBL = True)
        self.nsblCountryPDDict = self.getCountryPDDict(isGetSBL = False)

        self.sblCountryELDict = self.getCountryELDict(isGetSBL = True)
        self.nsblCountryELDict = self.getCountryELDict(isGetSBL = False)

        self.nsblRatingList = self._getNSBLDf().NSBL_Rating.unique().tolist() #sorted in a decending order
        print("")

    def interpolateSimple(self, xa, xb, ya, yb, xNew, method = 'log'):
        x_Input = [xa, xb]
        if method == 'linear':
            y_Input = [ya, yb]
        elif method == 'log':
            y_Input = [np.log(ya), np.log(yb)]
        else:
            raise ValueError("Error input of interpolation method: '{0}'!".format(method))

        yNew = np.interp(xNew, x_Input, y_Input)
        return yNew if method != 'log' else np.exp(yNew)

    def _getInputDF(self, inputFile):
        xls = pd.ExcelFile(inputFile)
        return xls.parse(INPUT_TABLE_TAB, skiprows=0, index_col=None, na_values=['NA'])

    def _getSBLDf(self):
        dataDf = self.dataDf.drop(['NSBL_Weights', 'NSBL_Corp_Rating', 'NSBL_Corp_PD', 'NSBL_ProjectF_Rating', 'NSBL_ProjectF_PD', 'NSBL_Rating', 'NSBL_PD', 'NSBL_Rating_Round'], axis=1)
        dataDf = dataDf[(dataDf[["SBL_Weights"]] != 0).all(1)] #drop zero rows if SBL weights is 0
        return dataDf.sort_values(by='SBL_Weights', ascending=False)

    def _getNSBLDf(self):
        dataDf = self.dataDf.drop(['SBL_Weights', 'SBL_Rating', 'SBL_PD'], axis=1)
        dataDf = dataDf[(dataDf[["NSBL_Weights"]] != 0).all(1)] #drop zero rows if NSBL weights is 0
        return dataDf.sort_values(by='NSBL_Weights', ascending=False)
    
    def _getMinWeightsPerRating(self, rating, isGetSBL = True):
        if isGetSBL:
            dataDf = self._getSBLDf()
            dataDf = dataDf[dataDf['SBL_Rating'] == rating]
            return 0 if not dataDf['SBL_Weights'].tolist() else min(dataDf['SBL_Weights'].tolist())
        else:
            dataDf = self._getNSBLDf()
            dataDf = dataDf[dataDf['NSBL_Rating_Round'] == rating]
            return 0 if not dataDf['NSBL_Weights'].tolist() else min(dataDf['NSBL_Weights'].tolist())
    
    def getMemberList(self, isGetRegional = True, isGetSBL = True):
        if isGetRegional:
            dataDf = self.dataDf[self.dataDf['IsRegionalM'] == 1]
        else:
            dataDf = self.dataDf[self.dataDf['IsNonRegionalM'] == 1]

        if isGetSBL:
            dataDf = dataDf[dataDf['SBL_Weights'] != 0]
        else:
            dataDf = dataDf[dataDf['NSBL_Weights'] != 0]

        return dataDf['Country_ISO'].tolist()

    def getCountryRatingDict(self, isGetSBL = True):
        if isGetSBL:
            dataDf = self.dataDf.sort_values(by='SBL_Weights', ascending=False)
            return dict(zip(dataDf.Country_ISO, dataDf.SBL_Rating))
        else:
            dataDf = self.dataDf.sort_values(by='NSBL_Weights', ascending=False)
            return dict(zip(dataDf.Country_ISO, dataDf.NSBL_Rating_Round))

    def getCountryLGDDict(self, isGetSBL = True):
        if isGetSBL:
            dataDf = self.dataDf.sort_values(by='SBL_Weights', ascending=False)
            return dict(zip(dataDf.Country_ISO, dataDf.LGD))
        else:
            dataDf = self.dataDf.sort_values(by='NSBL_Weights', ascending=False)
            return dict(zip(dataDf.Country_ISO, dataDf.LGD))

    def getCountryPDDict(self, isGetSBL = True):
        if isGetSBL:
            dataDf = self.dataDf.sort_values(by='SBL_Weights', ascending=False)
            return dict(zip(dataDf.Country_ISO, dataDf.SBL_PD))
        else:
            dataDf = self.dataDf.sort_values(by='NSBL_Weights', ascending=False)
            return dict(zip(dataDf.Country_ISO, dataDf.NSBL_PD))

    def getCountryELDict(self, isGetSBL = True):
        resultDict = {}
        if isGetSBL:
            countries = list(self.sblCountryPDDict.keys())
            for country in countries:
                resultDict[country] = self.sblCountryPDDict[country] * self.sblCountryLGDDict[country]
        else:
            countries = list(self.nsblCountryPDDict.keys())
            for country in countries:
                resultDict[country] = self.nsblCountryPDDict[country] * self.nsblCountryLGDDict[country]

        return resultDict

    def getHighRatingCountryDict(self, isGetSBL = True, countriesNotInclude = []):
        countryRatingDict = self.getCountryRatingDict(isGetSBL = isGetSBL)
        if isGetSBL:
            return { country : rating for country, rating in countryRatingDict.items() if ((rating >= 1 and rating <= 6) and (country not in countriesNotInclude))} #defination of high rated countries for Sovereign is better than rating 6
        else:
            return { country : rating for country, rating in countryRatingDict.items() if ((rating >= 1 and rating <= 7) and (country not in countriesNotInclude))} #defination of high rated countries for Nonsovereign is better than rating 7

    def getLowRatingCountryDict(self, isGetSBL = True, countriesNotInclude = []):
        countryRatingDict = self.getCountryRatingDict(isGetSBL = isGetSBL)
        if isGetSBL:
            return { country : rating for country, rating in countryRatingDict.items() if ((rating >= 7) and (country not in countriesNotInclude))}
        else:
            return { country : rating for country, rating in countryRatingDict.items() if ((rating >= 8) and (country not in countriesNotInclude))}

    def getHighRatingCountryWeightsDict(self, isGetSBL = True, countryWeightsDictInput = None, countriesNotInclude = []):
        if isGetSBL:
            if not countryWeightsDictInput:
                countryWeightsDictInput = self.originalCountryWeightsSBL

            highRatingCountryDictSBL = self.getHighRatingCountryDict(isGetSBL = isGetSBL, countriesNotInclude = countriesNotInclude)
            return { country : weight for country, weight in countryWeightsDictInput.items() if country in list(highRatingCountryDictSBL.keys())}
        else:
            if not countryWeightsDictInput:
                countryWeightsDictInput = self.originalCountryWeights_NSBL

            highRatingCountryDictNSBL = self.getHighRatingCountryDict(isGetSBL = isGetSBL, countriesNotInclude = countriesNotInclude)
            return { country : weight for country, weight in countryWeightsDictInput.items() if country in list(highRatingCountryDictNSBL.keys())}

    def getLowRatingCountryWeightsDict(self, isGetSBL = True, countryWeightsDictInput = None, countriesNotInclude = []):
        if isGetSBL:
            if not countryWeightsDictInput:
                countryWeightsDictInput = self.originalCountryWeightsSBL
            
            lowRatingCountryDictSBL = self.getLowRatingCountryDict(countriesNotInclude)
            return { country : weight for country, weight in countryWeightsDictInput.items() if country in list(lowRatingCountryDictSBL.keys())}
        else:
            if not countryWeightsDictInput:
                countryWeightsDictInput = self.originalCountryWeights_NSBL

            lowRatingCountryDictNSBL = self.getLowRatingCountryDict(isGetSBL=False, countriesNotInclude = countriesNotInclude)
            return { country : weight for country, weight in countryWeightsDictInput.items() if country in list(lowRatingCountryDictNSBL.keys())}

    def getCountryList(self, isGetSBL = True, countryWeightsDictInput = None):
        #resulting a sorted country list by country weights in decending order
        if not countryWeightsDictInput:
            if isGetSBL:
                dataDf = self._getSBLDf()
                return dataDf['Country_ISO'].tolist()
            else:
                dataDf = self._getNSBLDf()
                return dataDf['Country_ISO'].tolist()
        else:
            return list(self.reOrderCountryWeightDict(countryWeightsDictInput, reverse = True).keys())
    
    def getCountryPDList(self, isGetSBL = True):        
        return [pd for country, pd in self.getCountryPDDict(isGetSBL).items()]
    
    def getTargetRating(self, isGetSBL = True):
        if isGetSBL:
            targetType = 'SBL'
        else:
            targetType = 'NSBL'

        mandateRating = MANDATE_RATING.get(targetType)
        mandateRating_1Up = MANDATE_RATING.get(targetType) + 1

        targetRating = mandateRating + (mandateRating_1Up - mandateRating) / 2
        return targetRating

    def getTargetPD(self, isGetSBL = True):
        targetRating = self.getTargetRating(isGetSBL)
        if isGetSBL:
            targetType = 'SBL'
        else:
            targetType = 'NSBL'

        mandateRating = MANDATE_RATING.get(targetType)
        mandateRating_1Up = MANDATE_RATING.get(targetType) + 1
        pd = self.interpolateSimple(
                            mandateRating,
                            mandateRating_1Up,
                            Rating_PD_Dict.get(mandateRating),
                            Rating_PD_Dict.get(mandateRating_1Up),
                            targetRating,
                            method = 'log'
                        )
        return pd

    def getOriginalCountryWeights(self, isGetSBL = True):
        if isGetSBL:
            dataDf = self._getSBLDf() #the SBL df has been sorted by country weights by decending order
            self.sblRatingPDDict = dict(zip(dataDf.SBL_Rating, dataDf.SBL_PD)) #After PCT rating PD dict
            return dict(zip(dataDf.Country_ISO, dataDf.SBL_Weights)) #use ISO for the mapping. ISO, country SBL weights ordered by original weights decending
        else:
            dataDf = self._getNSBLDf()
            self.nsblRatingPDDict = dict(zip(dataDf.NSBL_Rating, dataDf.NSBL_PD))
            self.nsblRoundRatingPDDict = dict(zip(dataDf.NSBL_Rating_Round, dataDf.NSBL_PD))
            self.nsblRatingPrePCT_PDDict = dict(zip(dataDf.NSBL_ProjectF_Rating, dataDf.NSBL_ProjectF_PD))
            return dict(zip(dataDf.Country_ISO, dataDf.NSBL_Weights))

    def getCountryTier(self):
        return dict(zip(self.dataDf.Country_ISO, self.dataDf.GDPPP_Tier))

    def getMinRatingWeightDict(self, isGetSBL = True):
        ratingDict = {}
        for rating in range(1, 12):
            minWeight = self._getMinWeightsPerRating(rating, isGetSBL)
            ratingDict[rating] = minWeight

        return ratingDict

    def getMaxMinWeights(self, countryWeightsDictInput, isGetMax = True):
        if isGetMax:
            targetValue = max(countryWeightsDictInput.values())
        else:
            targetValue = min(countryWeightsDictInput.values())
        keys = [k for k, v in countryWeightsDictInput.items() if v == targetValue]
        return [keys, targetValue]

    def getSortedLowerRatingDf(self, isGetSBL = True, countryWeightsDictInput = None):
        if isGetSBL:
            if not countryWeightsDictInput:
                dataDf = self._getSBLDf()

            dataDf = dataDf[dataDf['SBL_Rating'].isin([7,8,9,10,11])]
            return dataDf.sort_values(['SBL_Rating', 'SBL_Weights'], ascending=[False, False])
        else:
            if not countryWeightsDictInput:
                dataDf = self._getNSBLDf()

            dataDf = dataDf[dataDf['NSBL_Rating_Round'].isin([8,9,10,11])]
            return dataDf.sort_values(['NSBL_Rating', 'NSBL_Weights'], ascending=[False, False])

    def reOrderCountryWeightDict(self, inputDict, reverse = False):
        outputDict = {}
        for key, value in sorted(inputDict.items(), key=lambda kv: kv[1], reverse=reverse):
            if value > 11:
                #for ratings, remove rating 12 countries
                continue

            outputDict[key] = value
        return outputDict

    def merge_dicts(self, dict1, dict2):
        dict2.update(dict1)
        return dict2

    def reOrderDict(self, inputDict, reverse = True):
        return sorted(inputDict.items(), key=lambda kv: kv[1], reverse=reverse)


class UtilsInsCreator(object):
    """Creating Instruments based on the input Country Weights and Other Parameters
    """
    def __init__(self):
        inputFile = INPUT_LOCATION + INPUT_FILENAME
        self.dataDf = self._getCountryWeights(inputFile)
        print('')

    def _getCountryWeights(self, inputFile):
        xls = pd.ExcelFile(inputFile)
        return xls.parse(INPUT_TABLE_TAB, skiprows=0, index_col=None, na_values=['NA'])


def main_targetP_builder():
    utils = UtilsTgtPortfolioBuilder()
    sblweight = utils.originalCountryWeightsSBL
    nsblweight = utils.originalCountryWeights_NSBL
    retResult = utils.getMinRatingWeightDict(isGetSBL=False)
    print("Returned Result: \n\n\n", retResult)
    print("Result Length: \n\n\n", len(retResult))
    print("SBL Weights: \n\n\n", sblweight)
    print("\n\n\n NSBL Weights:", nsblweight)
    #print(utils.getMaxMinWeights(sblweight, isGetMax=True))
    #print(utils.interpolateSimple(7, 8, 0.012487, 0.024417, 7.499, method = 'log'))



def main_ins_creator():
    utils = UtilsInsCreator()
    sblweight = utils._getCountryWeights('')
    #nsblweight = utils.originalCountryWeights_NSBL

    print(sblweight)
    #print(nsblweight)


if __name__ == "__main__":
    main_targetP_builder()