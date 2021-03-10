# -*- coding: utf-8 -*-
"""
Created on Thu May 28 13:00:57 2018
@author: liang.xue

Description:
	adjusted version of GDP Proxy script
"""
import sys
import datetime
import pandas as pd
import collections
import numpy as np
sys.path.append("..") #to be used for importing upper level folder result

from utils_target_p import UtilsTgtPortfolioBuilder
from config import RISK_LIMIT_DICT_SBL, PROJECTION_YEAR, COUNTRY_WEIGHTS_COLUMNS
from config import LTFP_PROJECTIONS, ADJUSTMENT_FACTOR_RISK_LIMIT, RISK_LIMIT_DICT_SPB_ASSUMPTIONS

class SBLPortfolioBuilder(object):
    def __init__(self):
        #"Not to Adjust" countries including those already reached to the limit like China if reached to 10%
        self.countriesNotToAdjust = []
        self.nonRegionalCountriesNotToAdjust = []

        self.utils = UtilsTgtPortfolioBuilder()
        
        self.nonRegional_SBLMembers = self.utils.getMemberList(isGetRegional = False, isGetSBL = True)
        #get country full list based on initial SBL country weights in decending order
        self.fullCountryList = self.utils.getCountryList(isGetSBL = True)
        
        #get original SBL country weights mapping from country ISO to SBL country weights
        #self.originalCountryWeights = self.utils.getOriginalCountryWeights(isGetSBL = True)
        
        #get target rating and PD for weighted avg pd adjustment
        self.sblTargetRating = self.utils.getTargetRating(isGetSBL = True)
        self.sblTargetPD = self.utils.getTargetPD(isGetSBL = True)
        
        #get country PD list sorted based on SBL weights in decending order
        self.countryPDList = self.utils.getCountryPDList(isGetSBL = True)

        self.highRatingCountryWeightDict = self.utils.getHighRatingCountryWeightsDict(isGetSBL = True)
        self.lowRatingCountryWeightDict = self.utils.getLowRatingCountryWeightsDict(isGetSBL = True)
        
        #get sorted loan rating country DF sorting by rating and weights in decending order
        self.lowRatingDf = self.utils.getSortedLowerRatingDf(isGetSBL = True)
        
        #get minimum country weights per rating for SBL
        self.getMinRatingWeightDict = self.utils.getMinRatingWeightDict(isGetSBL = True)
        
        self.lowRatingCountryRatingDict = self.utils.getLowRatingCountryDict(isGetSBL = True)
        self.lowRatingCountryRatingDict = self.utils.reOrderCountryWeightDict(self.lowRatingCountryRatingDict, reverse = True) #reorder to decending by rating
        
        print("test")

    def updateCountryWeights(self, updatedCountryWeightsDict):
        """Update Country Weights and Ordering After each Adjustment Cycle
        """
        self.highRatingCountryWeightDict = self.utils.getHighRatingCountryWeightsDict(countryWeightsDictInput = updatedCountryWeightsDict, countriesNotInclude = (self.countriesNotToAdjust + self.nonRegionalCountriesNotToAdjust))
        self.lowRatingCountryWeightDict = self.utils.getLowRatingCountryWeightsDict(countryWeightsDictInput = updatedCountryWeightsDict, countriesNotInclude = (self.countriesNotToAdjust + self.nonRegionalCountriesNotToAdjust))
        self.fullCountryList = self.utils.getCountryList(countryWeightsDictInput = updatedCountryWeightsDict)
        self.countriesNotToAdjust = list(set(self.countriesNotToAdjust)) #remove duplicates
        self.nonRegionalCountriesNotToAdjust = list(set(self.nonRegionalCountriesNotToAdjust)) #remove duplicates
        return self.utils.reOrderCountryWeightDict(updatedCountryWeightsDict, reverse = True)

    def _valiadateCountryLimit(self, countryWeightsDict, projectionYear):
        """Total exposures (both Investment and Treasury Operations) for one country, % total exposures
                => Projected Net DOB BasisN
        """
        #TODO: how can we allocate the treasury exposure for these countries? where does the assumption coming from
        countries, countryWeights = self.get_dict_items(countryWeightsDict)
        singleCountryLimitGen = (item >= RISK_LIMIT_DICT_SBL.get('Country_Exposure_Limit') for item in countryWeights)
        return any(singleCountryLimitGen)
    
    def _validateSingleNameExposureLimit(self, countryWeightsDict, projectionYear):
        """Biggest Single Name Sovereign Exposure against Available Capital should be less than 50%
                => Projected Net DOB Basis
        """
        countries, countryWeights = self.get_dict_items(countryWeightsDict)
        projectionYearDict = LTFP_PROJECTIONS.get(projectionYear)
        sblDOBProjection = projectionYearDict.get('Loans Investments - SBL')
        availableCapitalProjection = projectionYearDict.get('Available_Capital')
        singleNameExposures = [(weight * sblDOBProjection) / availableCapitalProjection  for weight in countryWeights]
        for index, weight in enumerate(singleNameExposures):
            if weight >= RISK_LIMIT_DICT_SBL.get('Single_Sovereign_Limit'):
                countryToAdjust = countries[index]
                print("Breaching Single Sovereign Limit! ", countryToAdjust, " Weights: ", weight)
                weightToAdjust = ((weight - RISK_LIMIT_DICT_SBL.get('Single_Sovereign_Limit') * 0.95) * availableCapitalProjection) / sblDOBProjection
                targetWeight = countryWeights[index] - weightToAdjust
                return [countryToAdjust, weightToAdjust, targetWeight]

        return []

    def _validateTop3NameExposureLimit(self, countryWeightsDict, projectionYear):
        """Top 3 sovereign backed exposures against Available Capital should be less than 90%
                => Projected Net DOB Basis
        """
        countriesToAdjust = []
        notAdjutCountries = list(set( self.countriesNotToAdjust ))
        ctyWeightsToAdjust = []
        oldCountryWeightsPropotion = []
        countries, countryWeights = self.get_dict_items(countryWeightsDict)
        projectionYearDict = LTFP_PROJECTIONS.get(projectionYear)
        sblDOBProjection = projectionYearDict.get('Loans Investments - SBL')
        availableCapitalProjection = projectionYearDict.get('Available_Capital')
        top3NameExposureSumWeight = sum([(weight * sblDOBProjection) for weight in countryWeights[:3]]) / availableCapitalProjection
        if top3NameExposureSumWeight > RISK_LIMIT_DICT_SBL.get('Top_3_Sovereign_Limit'):
            for cty in countries[:3]:
                #TODO: this adjustmeent is used to remove china from the top 3 adjustment if top 3 breaches
                #if (cty == 'CHN') and (countryWeightsDict['CHN'] < chinaLimit) and (countryWeightsDict['CHN'] >= chinaLimit * 0.99):
                #    continue
                if cty in notAdjutCountries:
                    continue

                countriesToAdjust.append(cty)
                ctyWeightsToAdjust.append(countryWeightsDict[cty])

            if not countriesToAdjust:
                #exception handling: that when all top 3 are in not to adjust list, then start to adjust them again
                for item in notAdjutCountries:
                    notAdjutCountries.remove(item)

            countriesToAdjust = [cty for cty in countries[:3]]
            ctyWeightsToAdjust = [countryWeightsDict[cty] for cty in countries[:3]] 
            for cty in countriesToAdjust:
                oldCountryWeightsPropotion.append( countryWeightsDict[cty] / sum(ctyWeightsToAdjust) )

            totalWeightToAdjust = top3NameExposureSumWeight - RISK_LIMIT_DICT_SBL.get('Top_3_Sovereign_Limit')
            weightsToAdjust = [propotion * totalWeightToAdjust for propotion in oldCountryWeightsPropotion]
            targetWeights = [countryWeights[index] - weight for index, weight in enumerate(weightsToAdjust)]
            return [countriesToAdjust, weightsToAdjust, targetWeights]
        return []
    
    def _validateTop5ObligorsLimit(self, countryWeightsDict, projectionYear):
        """Top 5 banking book obligor net DOB against projected total bank exposure should be less than 60%
                => Projected Net DOB Basis
        """
        countries, countryWeights = self.get_dict_items(countryWeightsDict)
        projectionYearDict = LTFP_PROJECTIONS.get(projectionYear)
        sblDOBProjection = projectionYearDict.get('Loans Investments - SBL')
        totalIODOBProjection = sblDOBProjection + projectionYearDict.get('Loans Investments - NSBL') + projectionYearDict.get('Equity investments') + projectionYearDict.get('Bond Investments')
        top5BankingBookWeight = (sum(countryWeights[:5]) * sblDOBProjection) / totalIODOBProjection
        if top5BankingBookWeight > RISK_LIMIT_DICT_SBL.get('Top_5_Obligor_Limit'):
            oldCountryWeightsPropotion = [weight / sum(countryWeights[:5]) for weight in countryWeights[:5]]
            countriesToAdjust = countries[:5]
            totalWeightToAdjust = ((top5BankingBookWeight - RISK_LIMIT_DICT_SBL.get('Top_5_Obligor_Limit') * 0.9) * totalIODOBProjection) / sblDOBProjection
            weightsToAdjust = [propotion * totalWeightToAdjust for propotion in oldCountryWeightsPropotion]
            targetWeights = [countryWeights[index] - weight for index, weight in enumerate(weightsToAdjust)]
            return [countriesToAdjust, weightsToAdjust, targetWeights]

        return []
    
    def _validateWeightedAverageRatingLimit(self, countryWeightsDict):
        """Weighted average rating should meet bank's AAA target rating: 
            - Sovereign: 6
            - Non-Sovereign: 7
            
            Here we adjust using interpolated weighted average PD instead of rating
        """
        countryWeights = list(countryWeightsDict.values())
        countryPDDict = self.utils.getCountryPDDict(isGetSBL = True)
        weightAveragePD = sum([weight * countryPDDict.get(country,0) for country, weight in countryWeightsDict.items()]) / sum(countryWeights)

        print("weighted average PD:{0}".format(weightAveragePD))
        return weightAveragePD >= self.sblTargetPD

    def _valiadateChinaLimit(self, countryWeightsDict):
        chinaWeights = countryWeightsDict.get('CHN')
        return chinaWeights > RISK_LIMIT_DICT_SPB_ASSUMPTIONS.get('China').get('SBL')

    def _valiadateNonRegionalLimit(self, countryWeightsDict):
        nonRegionalWeightsTotal = sum([countryWeightsDict.get(country, 0) for country in self.nonRegional_SBLMembers])
        if round(nonRegionalWeightsTotal, 4) > RISK_LIMIT_DICT_SPB_ASSUMPTIONS.get('Non_Regional').get('SBL'):#RISK_LIMIT_DICT_N_SBL.get('Non_Regional_Mem_Weight_Limit'):
            return {country:weight for country, weight in countryWeightsDict.items() if country in self.nonRegional_SBLMembers}
        else:
            return {}

    def adjust_SingleNameWeights(self, singleNameExposureValidationResult, countryWeightsDict, highRatingCountryWeightDict):
        """Adjust single name country weights until it gets to balanced
             - Strategy: assign the exceed limit weights to the rest of high rating countries
        """
        adjustedHighRatingCountryWeightsDict = {}
        newCountryWeightDict = {}

        
        countryToAdjust, weightToAdjust, targetWeight = singleNameExposureValidationResult
        self.countriesNotToAdjust.append(countryToAdjust)

        sumWeights_HighRatingCountry_ExcludeAdjustCountry = sum(v for k, v in highRatingCountryWeightDict.items() if k != countryToAdjust)
        originalWeightPropotion_HighRatingCountry_ExcludeAdjustCountry = { country : weight/sumWeights_HighRatingCountry_ExcludeAdjustCountry for country, weight in highRatingCountryWeightDict.items() if country != countryToAdjust}
        
        adjustedHighRatingCountryWeightsDict[countryToAdjust] = targetWeight
        for country, originalWeight in highRatingCountryWeightDict.items():
            if country == countryToAdjust:
                continue

            newWeight = originalWeightPropotion_HighRatingCountry_ExcludeAdjustCountry.get(country) * weightToAdjust + highRatingCountryWeightDict.get(country)
            adjustedHighRatingCountryWeightsDict[country] = newWeight

        for country in self.fullCountryList:
            if adjustedHighRatingCountryWeightsDict.get(country):
                newCountryWeightDict[country] = adjustedHighRatingCountryWeightsDict.get(country)
            else:
                newCountryWeightDict[country] = countryWeightsDict.get(country)

        #udpate the country weights as well as the weights
        newCountryWeightDict = self.updateCountryWeights(newCountryWeightDict)
        newCountryWeightsList = list(newCountryWeightDict.values())
        print(newCountryWeightsList)
        return newCountryWeightsList, newCountryWeightDict


    def adjust_ChinaWeights(self, countryWeightsDict, highRatingCountryWeightDict):
        """Adjust China Limits
             - Strategy: assign the exceed limit weights to the rest of high rating countries within Regional
        """
        adjustedHighRatingCountryWeightsDict = {}
        newCountryWeightDict = {}

        countryToAdjust = 'CHN'
        chinaTargetWeight = RISK_LIMIT_DICT_SPB_ASSUMPTIONS['China']['SBL']
        weightToAdjust = countryWeightsDict['CHN'] - chinaTargetWeight
        self.countriesNotToAdjust.append(countryToAdjust)

        sumWeights_HighRatingCountry_ExcludeAdjustCountry = sum(v for k, v in highRatingCountryWeightDict.items() if k != countryToAdjust)
        originalWeightPropotion_HighRatingCountry_ExcludeAdjustCountry = { country : weight/sumWeights_HighRatingCountry_ExcludeAdjustCountry for country, weight in highRatingCountryWeightDict.items() if country != countryToAdjust}
        
        adjustedHighRatingCountryWeightsDict[countryToAdjust] = chinaTargetWeight
        for country, originalWeight in highRatingCountryWeightDict.items():
            if country == countryToAdjust:
                continue

            newWeight = originalWeightPropotion_HighRatingCountry_ExcludeAdjustCountry.get(country) * weightToAdjust + highRatingCountryWeightDict.get(country)
            adjustedHighRatingCountryWeightsDict[country] = newWeight

        for country in self.fullCountryList:
            if adjustedHighRatingCountryWeightsDict.get(country):
                newCountryWeightDict[country] = adjustedHighRatingCountryWeightsDict.get(country)
            elif country == 'CHN':
                newCountryWeightDict[country] = chinaTargetWeight
            else:
                newCountryWeightDict[country] = countryWeightsDict.get(country)

        #udpate the country weights as well as the weights
        newCountryWeightDict = self.updateCountryWeights(newCountryWeightDict)
        newCountryWeightsList = list(newCountryWeightDict.values())
        return newCountryWeightsList, newCountryWeightDict

    #TODO: do this 
    def adjust_Top3ExposureWeights(self, top3NameExposureValidationResult, countryWeightsDict, highRatingCountryWeightDict):
        adjustedHighRatingCountryWeightsDict = {}
        newCountryWeightDict = {}
        top3NewTargetDict = {cty:wtg for cty, wtg in zip(top3NameExposureValidationResult[0], top3NameExposureValidationResult[2])}

        countriesToAdjust, weightsToAdjust, targetWeights = top3NameExposureValidationResult
        #sumWeights_HighRatingCountry_ExcludeAdjustCountry = sum(weight for country, weight in highRatingCountryWeightDict.items() if country not in (countriesToAdjust + self.countriesNotToAdjust + self.nonRegionalCountriesNotToAdjust) )
        
        #tweaked the algorithm to readjust evenly
        originalWeightPropotion_HighRatingCountry_ExcludeAdjustCountry = { country : 1/len(highRatingCountryWeightDict) for country, weight in highRatingCountryWeightDict.items() if country not in (countriesToAdjust + self.countriesNotToAdjust + self.nonRegionalCountriesNotToAdjust)}
        #originalWeightPropotion_HighRatingCountry_ExcludeAdjustCountry = { country : weight/sumWeights_HighRatingCountry_ExcludeAdjustCountry for country, weight in highRatingCountryWeightDict.items() if country not in (countriesToAdjust + self.countriesNotToAdjust + self.nonRegionalCountriesNotToAdjust)}

        for country, originalWeight in highRatingCountryWeightDict.items():
            if (country in countriesToAdjust) or (country in self.countriesNotToAdjust) or (country in self.nonRegionalCountriesNotToAdjust):
                continue
    
            newWeight = originalWeightPropotion_HighRatingCountry_ExcludeAdjustCountry.get(country) * sum(weightsToAdjust) + highRatingCountryWeightDict.get(country)
            adjustedHighRatingCountryWeightsDict[country] = newWeight

        for country in self.fullCountryList: #TODO: this country list need to be updated as the ranking of country is changed
            if adjustedHighRatingCountryWeightsDict.get(country):
                newCountryWeightDict[country] = adjustedHighRatingCountryWeightsDict.get(country)
            elif country in top3NameExposureValidationResult[0]:
                newCountryWeightDict[country] =top3NewTargetDict.get(country)
            else:
                newCountryWeightDict[country] = countryWeightsDict.get(country)

        #udpate the country weights as well as the weights
        newCountryWeightDict = self.updateCountryWeights(newCountryWeightDict)
        newCountryWeightsList = list(newCountryWeightDict.values())
        print(newCountryWeightsList)
        self.countriesNotToAdjust = self.countriesNotToAdjust + top3NameExposureValidationResult[0]
        return newCountryWeightsList, newCountryWeightDict

    def adjust_Top5BankingBookObligator(self, top5BankingBookValidationResult, countryWeightsDict, highRatingCountryWeightDict):
        adjustedHighRatingCountryWeightsDict = {}
        newCountryWeightDict = {}

        countriesToAdjust, weightsToAdjust, targetWeights = top5BankingBookValidationResult
        sumWeights_HighRatingCountry_ExcludeAdjustCountry = sum(weight for country, weight in highRatingCountryWeightDict.items() if country not in countriesToAdjust)
        originalWeightPropotion_HighRatingCountry_ExcludeAdjustCountry = { country : weight/sumWeights_HighRatingCountry_ExcludeAdjustCountry for country, weight in highRatingCountryWeightDict.items() if country not in countriesToAdjust}

        for country, weight in zip(countriesToAdjust, targetWeights):
            adjustedHighRatingCountryWeightsDict[country] = weight

        for country, originalWeight in highRatingCountryWeightDict.items():
            if country in countriesToAdjust:
                continue

            newWeight = originalWeightPropotion_HighRatingCountry_ExcludeAdjustCountry.get(country) * sum(weightsToAdjust) + highRatingCountryWeightDict.get(country)
            adjustedHighRatingCountryWeightsDict[country] = newWeight

        for country in self.fullCountryList: #TODO: this country list need to be updated as the ranking of country is changed
            if adjustedHighRatingCountryWeightsDict.get(country):
                newCountryWeightDict[country] = adjustedHighRatingCountryWeightsDict.get(country)
            else:
                newCountryWeightDict[country] = countryWeightsDict.get(country)

        #udpate the country weights as well as the weights
        newCountryWeightDict = self.updateCountryWeights(newCountryWeightDict)
        newCountryWeightsList = list(newCountryWeightDict.values())
        print(newCountryWeightsList)
        
        #add the adjsuted top 5 to make sure it will not be adjusted again?
        return newCountryWeightsList, newCountryWeightDict

    def adjust_NonRegionalCountryWeights(self, countryWeightsDict, nonRegionalValidationResult):
        """In SBL case, adjust the nonregional total country weights
        """
        newCountryWeightDict = {}
        adjusted_Non_Regional_CountryWeightDict = {}
        adjusted_Regional_CountryWeightDict = {}
        targetWeights = RISK_LIMIT_DICT_SPB_ASSUMPTIONS.get('Non_Regional').get('SBL')

        nonRegionalCountriesInScope = list(nonRegionalValidationResult.keys())
        totalNonRegionalWeightsOrigin = sum(list(nonRegionalValidationResult.values()))
        adjustWeights = totalNonRegionalWeightsOrigin - targetWeights

        originalWeightPropotion_Non_Regional = { country : weight/totalNonRegionalWeightsOrigin for country, weight in countryWeightsDict.items() if country in nonRegionalCountriesInScope}  
        for country, weight in nonRegionalValidationResult.items():
            newWeight = originalWeightPropotion_Non_Regional.get(country) * targetWeights
            adjusted_Non_Regional_CountryWeightDict[country] = newWeight
        
        newCountryWeightDict = adjusted_Non_Regional_CountryWeightDict
        sumWeights_Regional = sum(weight for country, weight in countryWeightsDict.items() if country not in (nonRegionalCountriesInScope + self.countriesNotToAdjust))
        
        #get the regional countries and take out those "not to adjust" countries from the regional country list. "Not to Adjust" countries including those already reached to the limit like China if reached to 10%
        originalWeightPropotion_Regional = { country : weight/sumWeights_Regional for country, weight in countryWeightsDict.items() if country not in (nonRegionalCountriesInScope + self.countriesNotToAdjust)}
        for country, originalWeight in countryWeightsDict.items():
            if (country in nonRegionalCountriesInScope) or (country in self.countriesNotToAdjust):
                continue

            newWeight = originalWeightPropotion_Regional.get(country) * adjustWeights + originalWeight
            adjusted_Regional_CountryWeightDict[country] = newWeight

        newCountryWeightDict.update(adjusted_Regional_CountryWeightDict)
        for country in self.countriesNotToAdjust:
            newCountryWeightDict.update({country: countryWeightsDict[country]})

        newCountryWeightDict = self.updateCountryWeights(newCountryWeightDict)
        print(len(list(newCountryWeightDict.values())))
        print(sum(list(newCountryWeightDict.values())))

        newCountryWeightDict = self.updateCountryWeights(newCountryWeightDict)
        self.nonRegionalCountriesNotToAdjust = nonRegionalCountriesInScope
        return newCountryWeightDict

    def adjust_WeightedAverageRating(self, countryWeightsDict, highRatingCountryWeightDict, lowRatingCountryRatingDict):
        non_RegMemberList = self.nonRegional_SBLMembers
        regMemberList = self.utils.getMemberList(isGetRegional = True, isGetSBL = True)

        #added asof 2020-10-19 night, for stop adjustment for prventing good countries to be readjusted again
        for country, weight in countryWeightsDict.items():
            countryRtg = self.utils.sblCountryRatingDict[country]
            if (country not in (self.countriesNotToAdjust + non_RegMemberList)) and (weight >= 0.09) and (countryRtg <= 6):
                #if the country weights is big enough then stop adjustment
                #only if it's a good country in this case then stop adjustment
                self.countriesNotToAdjust.append(country)

        ctyWeightsDict_Left_Over = {k:w for k,w in countryWeightsDict.items() if k in self.countriesNotToAdjust}

        ctyWeightsDict_Regional = {k:w for k,w in countryWeightsDict.items() if (k in regMemberList)}
        highRatingCountryWeight_Regional = self.utils.getHighRatingCountryWeightsDict(isGetSBL = True, countryWeightsDictInput = countryWeightsDict, countriesNotInclude = (self.countriesNotToAdjust + non_RegMemberList))
        lowRatingCountryRtgDict_Regional = self.utils.getLowRatingCountryDict(isGetSBL = True, countriesNotInclude = (self.countriesNotToAdjust + non_RegMemberList))
        isWeightedAverageRatingExceeded_Regional = self._validateWeightedAverageRatingLimit(ctyWeightsDict_Regional)
        new_ctyWeightsDict_Regional = ctyWeightsDict_Regional
        while isWeightedAverageRatingExceeded_Regional:
            weightsDict_Regional = self._adj_Rtg_By_Regions(new_ctyWeightsDict_Regional, highRatingCountryWeight_Regional, lowRatingCountryRtgDict_Regional, self.countriesNotToAdjust)
            isWeightedAverageRatingExceeded_Regional = self._validateWeightedAverageRatingLimit(weightsDict_Regional[1])
            new_ctyWeightsDict_Regional = weightsDict_Regional[1]
            highRatingCountryWeight_Regional = self.utils.getHighRatingCountryWeightsDict(isGetSBL = True, countryWeightsDictInput = new_ctyWeightsDict_Regional, countriesNotInclude = (self.countriesNotToAdjust + non_RegMemberList))
            #lowRatingCountryRtgDict_Regional = self.utils.getLowRatingCountryDict(isGetSBL = True, countriesNotInclude = (self.countriesNotToAdjust + non_RegMemberList))

        ctyWeightsDict_Non_Regional = {k:w for k,w in countryWeightsDict.items() if (k in non_RegMemberList)}
        highRatingCountryWeight_Non_Regional = self.utils.getHighRatingCountryWeightsDict(isGetSBL = True, countryWeightsDictInput = countryWeightsDict, countriesNotInclude = (self.countriesNotToAdjust + regMemberList))
        lowRatingCountryRtgDict_Non_Regional = self.utils.getLowRatingCountryDict(isGetSBL = True, countriesNotInclude = (self.countriesNotToAdjust + regMemberList))
        isWeightedAverageRatingExceeded_Non_Regional = self._validateWeightedAverageRatingLimit(ctyWeightsDict_Non_Regional)
        new_ctyWeightsDict_Non_Regional = ctyWeightsDict_Non_Regional
        while isWeightedAverageRatingExceeded_Non_Regional:
            weightsDict_Non_Regional = self._adj_Rtg_By_Regions(new_ctyWeightsDict_Non_Regional, highRatingCountryWeight_Non_Regional, lowRatingCountryRtgDict_Non_Regional, self.countriesNotToAdjust)
            isWeightedAverageRatingExceeded_Non_Regional = self._validateWeightedAverageRatingLimit(weightsDict_Non_Regional[1])
            new_ctyWeightsDict_Non_Regional = weightsDict_Non_Regional[1]
            highRatingCountryWeight_Non_Regional = self.utils.getHighRatingCountryWeightsDict(isGetSBL = True, countryWeightsDictInput = new_ctyWeightsDict_Non_Regional, countriesNotInclude = (self.countriesNotToAdjust + regMemberList))

        finalCtyWeightsDict = self.utils.merge_dicts(new_ctyWeightsDict_Regional, new_ctyWeightsDict_Non_Regional)
        finalCtyWeightsDict = self.utils.merge_dicts(finalCtyWeightsDict, ctyWeightsDict_Left_Over)
        finalCtyWeightsList = list(finalCtyWeightsDict.values())
        print("total weights: {0}".format(sum(finalCtyWeightsList)))
        if sum(finalCtyWeightsList) > 1:
            #post adjustment for weights if total weights bigger than 1 due to accumulated decimal or rounding
            finalCtyWeightsList = { country : weight/sum(finalCtyWeightsList) for country, weight in finalCtyWeightsDict.items() }

        #udpate the country weights as well as the weights
        finalCtyWeightsDict = self.updateCountryWeights(finalCtyWeightsDict)
        finalCtyWeightsList = list(finalCtyWeightsDict.values())

        return finalCtyWeightsList, finalCtyWeightsDict

    def _adj_Rtg_By_Regions(self, countryWeightsDict, highRatingCountryWeightDict, lowRatingCountryRatingDict, countriesNotToAdjust):
        inputCountryList = list(countryWeightsDict.keys())
        adjustedHighRatingCountryWeightsDict = {}
        adjustedLowerRatingCountryWeightsDict = {}
        newCountryWeightDict = {}
        
        #sum for weights and exclude thost not to be adjusted
        sumWeightsToBeAdjusted = sum(weight for country, weight in highRatingCountryWeightDict.items()  if country not in countriesNotToAdjust)
        originalWeightPropotion_HighRatingCountry_ToBeAdjusted = { country : weight/sumWeightsToBeAdjusted for country, weight in highRatingCountryWeightDict.items() if country not in countriesNotToAdjust}
        
        high = sum(list(highRatingCountryWeightDict.values()))
        low = sum([weight for country, weight in countryWeightsDict.items() if country in list(lowRatingCountryRatingDict.keys())])
        rest = sum( [weight for country, weight in countryWeightsDict.items() if country not in (list(highRatingCountryWeightDict.keys()) + list(lowRatingCountryRatingDict.keys()))])
        
        ##########################DEBUGGING: for debugging purpose #####################################################
        print("total weights  high: {0}".format(high))
        print("total weights  low: {0}".format(low))
        print("total weights  rest: {0}".format(rest))
        print("total weights  sum high low rest: {0}".format(high+low+rest))
        ##########################DEBUGGING: for debugging purpose #####################################################

        tempHighCountryRatingDict = highRatingCountryWeightDict
        for countryLowRtg, rating in lowRatingCountryRatingDict.items():
            ##########################DEBUGGING: for debugging purpose #####################################################
            #if country == 'FJI':
            #    print("")
            ##########################DEBUGGING: for debugging purpose #####################################################

            lowCountryWeight = countryWeightsDict.get(countryLowRtg)
            if lowCountryWeight <= ADJUSTMENT_FACTOR_RISK_LIMIT:
                adjustedLowerRatingCountryWeightsDict[countryLowRtg] = lowCountryWeight 
                continue

            newLowCountryWeight = lowCountryWeight - ADJUSTMENT_FACTOR_RISK_LIMIT
            if newLowCountryWeight <= self.getMinRatingWeightDict.get(rating):
                #if adjusted rating below the min rating limit, then go to next country to do the adjustment
                adjustedLowerRatingCountryWeightsDict[countryLowRtg] = lowCountryWeight 
                continue
            
            #adjustment start from the worst rating with highest GDP country
            adjustedLowerRatingCountryWeightsDict[countryLowRtg] = newLowCountryWeight

            adjustedHighRatingCountryWeightsDict = {}
            for countryHighRtg, originalWeight in tempHighCountryRatingDict.items():
                #check china weights
                if 'CHN' in list(tempHighCountryRatingDict.keys()):
                    chinaWeightTemp = tempHighCountryRatingDict['CHN']
                    chinaLimit = RISK_LIMIT_DICT_SPB_ASSUMPTIONS['China']['SBL']
                    if (chinaWeightTemp < chinaLimit) and (chinaWeightTemp >= chinaLimit * 0.99) and ('CNH' not in countriesNotToAdjust):
                        self.countriesNotToAdjust.append('CHN')
                        countriesNotToAdjust.append('CHN')

                #adjust for the high rated countries
                if countryHighRtg in countriesNotToAdjust:
                    #do not adjust for those in the not to adjust list
                    adjustedHighRatingCountryWeightsDict[countryHighRtg] = originalWeight
                    continue
                
                newWeight = originalWeightPropotion_HighRatingCountry_ToBeAdjusted.get(countryHighRtg) * ADJUSTMENT_FACTOR_RISK_LIMIT + originalWeight
                adjustedHighRatingCountryWeightsDict[countryHighRtg] = newWeight

            #update temp high rating dict to adjusted high rating country weight dict
            tempHighCountryRatingDict = adjustedHighRatingCountryWeightsDict

        ##########################DEBUGGING: for debugging purpose #####################################################
        new_high = sum(list(adjustedHighRatingCountryWeightsDict.values()))
        new_low = sum(list(adjustedLowerRatingCountryWeightsDict.values()))
        print("total weights adjust high: {0}".format(new_high))
        print("total weights adjust low: {0}".format(new_low))
        ##########################DEBUGGING: for debugging purpose #####################################################

        for country in inputCountryList:
            if adjustedHighRatingCountryWeightsDict.get(country):
                newCountryWeightDict[country] = adjustedHighRatingCountryWeightsDict.get(country)
            elif adjustedLowerRatingCountryWeightsDict.get(country):
                newCountryWeightDict[country] = adjustedLowerRatingCountryWeightsDict.get(country)
            else:
                newCountryWeightDict[country] = countryWeightsDict.get(country)

        newCountryWeightDict = self.updateCountryWeights(newCountryWeightDict)
        newCountryWeightsList = list(newCountryWeightDict.values())
        return newCountryWeightsList, newCountryWeightDict

    def get_dict_items(self, weight_dict):
        keys = []
        weights = []

        for key, weight in weight_dict.items():
            keys.append(key)
            weights.append(weight)
        return keys, weights

    def _check_all_limits(self, countryWeightsDict):
        top5BankingBookValidationResult = self._validateTop5ObligorsLimit(countryWeightsDict, PROJECTION_YEAR)
        isTop5ObligorsLImitExceeded = any(top5BankingBookValidationResult)
        isCountryLimitExceeded = self._valiadateCountryLimit(countryWeightsDict, PROJECTION_YEAR)
        singleNameExposureValidationResult = self._validateSingleNameExposureLimit(countryWeightsDict, PROJECTION_YEAR)
        isSingleNameExposureExceeded = any(singleNameExposureValidationResult)
        top3NameExposureValidationResult = self._validateTop3NameExposureLimit(countryWeightsDict, PROJECTION_YEAR)
        isTop3NameExposureExceeded = any(top3NameExposureValidationResult)
        isChinaLimitExceeded = self._valiadateChinaLimit(countryWeightsDict)
        nonRegionalValidationResult = self._valiadateNonRegionalLimit(countryWeightsDict)
        isNonRegionalOverWeighted = any(nonRegionalValidationResult)
        isWeightedAverageRatingExceeded = self._validateWeightedAverageRatingLimit(countryWeightsDict)

        return isTop5ObligorsLImitExceeded, isTop3NameExposureExceeded, isSingleNameExposureExceeded, \
            isCountryLimitExceeded, isWeightedAverageRatingExceeded, isChinaLimitExceeded, isNonRegionalOverWeighted

    def _validate_limits(self, countryWeightsDict):
        count = 0

        isTop5ObligorsLImitExceeded, \
            isTop3NameExposureExceeded, \
                isSingleNameExposureExceeded, \
                    isCountryLimitExceeded, \
                        isWeightedAverageRatingExceeded, \
                            isChinaLimitExceeded, \
                                isNonRegionalOverWeighted = self._check_all_limits(countryWeightsDict)

        while (isTop5ObligorsLImitExceeded or 
                   isTop3NameExposureExceeded or 
                       isSingleNameExposureExceeded or 
                           isCountryLimitExceeded or 
                               isWeightedAverageRatingExceeded or
                                   isChinaLimitExceeded or
                                       isNonRegionalOverWeighted):
            count = count + 1
            print("Exceeding limits... Redrawing... {0} \n".format(count))
            print(isTop5ObligorsLImitExceeded,isTop3NameExposureExceeded,isSingleNameExposureExceeded,isCountryLimitExceeded, isWeightedAverageRatingExceeded)
            countryWeights = list(countryWeightsDict.values())
            countryWeightsDict = self.validate_and_adj_risk_weights(countryWeights, countryWeightsDict)

            isTop5ObligorsLImitExceeded, \
                isTop3NameExposureExceeded, \
                    isSingleNameExposureExceeded, \
                        isCountryLimitExceeded, \
                            isWeightedAverageRatingExceeded, \
                                isChinaLimitExceeded, \
                                    isNonRegionalOverWeighted = self._check_all_limits(countryWeightsDict)

        return countryWeightsDict

    def _single_name_limit_process(self, countryWeights, countryWeightsDict):
        singleNameExposureValidationResult = self._validateSingleNameExposureLimit(countryWeightsDict, PROJECTION_YEAR)
        isSingleNameExposureExceeded = any(singleNameExposureValidationResult)
        while isSingleNameExposureExceeded:
            highRatingCountryWeight = self.utils.getHighRatingCountryWeightsDict(countryWeightsDictInput = countryWeightsDict, countriesNotInclude = (self.countriesNotToAdjust + self.nonRegionalCountriesNotToAdjust)) #{ country : weight for country, weight in countryWeightsDict.items() if country in list(HIGH_RATING_COUNTRY_DICT.keys())}
            countryWeights, countryWeightsDict = self.adjust_SingleNameWeights(singleNameExposureValidationResult, countryWeightsDict, highRatingCountryWeight)
            singleNameExposureValidationResult = self._validateSingleNameExposureLimit(countryWeightsDict, PROJECTION_YEAR)
            isSingleNameExposureExceeded = any(singleNameExposureValidationResult)
        isSingleNameExposureExceeded = False
        return countryWeights, countryWeightsDict, isSingleNameExposureExceeded

    def _top_3_limit_process(self, countryWeights, countryWeightsDict):
        top3NameExposureValidationResult = self._validateTop3NameExposureLimit(countryWeightsDict, PROJECTION_YEAR)
        isTop3NameExposureExceeded = any(top3NameExposureValidationResult)
        while isTop3NameExposureExceeded:
            highRatingCountryWeight = self.utils.getHighRatingCountryWeightsDict(countryWeightsDictInput = countryWeightsDict, countriesNotInclude = (self.countriesNotToAdjust + self.nonRegionalCountriesNotToAdjust + top3NameExposureValidationResult[0])) #{ country : weight for country, weight in countryWeightsDict.items() if country in list(HIGH_RATING_COUNTRY_DICT.keys())}
            countryWeights, countryWeightsDict = self.adjust_Top3ExposureWeights(top3NameExposureValidationResult, countryWeightsDict, highRatingCountryWeight)
            top3NameExposureValidationResult = self._validateTop3NameExposureLimit(countryWeightsDict, PROJECTION_YEAR)
            isTop3NameExposureExceeded = any(top3NameExposureValidationResult)
        isTop3NameExposureExceeded = False
        return countryWeights, countryWeightsDict, isTop3NameExposureExceeded

    def _top_5_bankbook_limit_process(self, countryWeights, countryWeightsDict):
        top5BankingBookValidationResult = self._validateTop5ObligorsLimit(countryWeightsDict, PROJECTION_YEAR)
        isTop5ObligorsLImitExceeded = any(top5BankingBookValidationResult)
        while isTop5ObligorsLImitExceeded:
            highRatingCountryWeight = self.utils.getHighRatingCountryWeightsDict(countryWeightsDictInput = countryWeightsDict, countriesNotInclude = (self.countriesNotToAdjust + self.nonRegionalCountriesNotToAdjust)) #{ country : weight for country, weight in countryWeightsDict.items() if country in list(HIGH_RATING_COUNTRY_DICT.keys())}
            countryWeights, countryWeightsDict = self.adjust_Top5BankingBookObligator(top5BankingBookValidationResult, countryWeightsDict, highRatingCountryWeight)
            top5BankingBookValidationResult = self._validateTop5ObligorsLimit(countryWeightsDict, PROJECTION_YEAR)
            isTop5ObligorsLImitExceeded = any(top5BankingBookValidationResult)
        isTop5ObligorsLImitExceeded = False
        return countryWeights, countryWeightsDict, isTop5ObligorsLImitExceeded

    def _china_limit_process(self, countryWeights, countryWeightsDict):
        isChinaLimitExceeded = self._valiadateChinaLimit(countryWeightsDict)
        if isChinaLimitExceeded:
            highRatingCountryWeight = self.utils.getHighRatingCountryWeightsDict(countryWeightsDictInput = countryWeightsDict, countriesNotInclude = (self.countriesNotToAdjust + self.nonRegionalCountriesNotToAdjust)) #{ country : weight for country, weight in countryWeightsDict.items() if country in list(HIGH_RATING_COUNTRY_DICT.keys())}
            countryWeights, countryWeightsDict = self.adjust_ChinaWeights(countryWeightsDict, highRatingCountryWeight)
        isChinaLimitExceeded = False
        return countryWeights, countryWeightsDict, isChinaLimitExceeded

    def _nonregional_limit_process(self, countryWeights, countryWeightsDict):
        nonRegionalValidationResult = self._valiadateNonRegionalLimit(countryWeightsDict)
        isNonRegionalOverWeighted = any(nonRegionalValidationResult)
        if isNonRegionalOverWeighted:
            countryWeightsDict  = self.adjust_NonRegionalCountryWeights(countryWeightsDict, nonRegionalValidationResult)
        isNonRegionalOverWeighted = False
        countryWeights = list(countryWeightsDict.values())
        return countryWeights, countryWeightsDict, isNonRegionalOverWeighted

    def _avg_rtg_limit_process(self, countryWeights, countryWeightsDict):
        #validate weighted average rating for SBL
        isWeightedAverageRatingExceeded = self._validateWeightedAverageRatingLimit(countryWeightsDict)
        while isWeightedAverageRatingExceeded:
            highRatingCountryWeight = self.utils.getHighRatingCountryWeightsDict(isGetSBL = True, countryWeightsDictInput = countryWeightsDict, countriesNotInclude = self.countriesNotToAdjust)
            lowRatingCountryRtgDict = self.utils.getLowRatingCountryDict(isGetSBL = True, countriesNotInclude = self.countriesNotToAdjust)
            countryWeights, countryWeightsDict = self.adjust_WeightedAverageRating(countryWeightsDict, highRatingCountryWeight, lowRatingCountryRtgDict)
            isWeightedAverageRatingExceeded = self._validateWeightedAverageRatingLimit(countryWeightsDict)
        isWeightedAverageRatingExceeded = False
        return countryWeights, countryWeightsDict, isWeightedAverageRatingExceeded

    def _temp_validate_limits(self, countryWeightsDict, limit_perm_fun_item):
        count = 0

        isTop5ObligorsLImitExceeded, \
            isTop3NameExposureExceeded, \
                isSingleNameExposureExceeded, \
                    isCountryLimitExceeded, \
                        isWeightedAverageRatingExceeded, \
                            isChinaLimitExceeded, \
                                isNonRegionalOverWeighted = self._check_all_limits(countryWeightsDict)

        while (isTop5ObligorsLImitExceeded or 
                   isTop3NameExposureExceeded or 
                       isSingleNameExposureExceeded or 
                           isCountryLimitExceeded or 
                               isWeightedAverageRatingExceeded or
                                   isChinaLimitExceeded or
                                       isNonRegionalOverWeighted):
            count = count + 1
            print("Exceeding limits... Redrawing... {0} \n".format(count))
            print(isTop5ObligorsLImitExceeded,isTop3NameExposureExceeded,isSingleNameExposureExceeded,isCountryLimitExceeded, isWeightedAverageRatingExceeded)
            countryWeights = list(countryWeightsDict.values())
            countryWeightsDict = self.temp_permuattion_validate_and_adj_risk_weights(countryWeights, countryWeightsDict, limit_perm_fun_item)

            isTop5ObligorsLImitExceeded, \
                isTop3NameExposureExceeded, \
                    isSingleNameExposureExceeded, \
                        isCountryLimitExceeded, \
                            isWeightedAverageRatingExceeded, \
                                isChinaLimitExceeded, \
                                    isNonRegionalOverWeighted = self._check_all_limits(countryWeightsDict)

        return countryWeightsDict

    def temp_permuattion_validate_and_adj_risk_weights(self, countryWeights, countryWeightsDict, limit_perm_fun_item):
        """Main process of the adjustment: 
                To adjust SBL country DOB weights to make sure the result country weights still fits for risk limits in Risk Appetite Statement
        """
        result_data_set = []
        for limit_func in limit_perm_fun_item:
            temp_result = limit_func(countryWeights, countryWeightsDict)
            countryWeights = temp_result[0]
            countryWeightsDict = temp_result[1]

        countryWeightsDict = self._temp_validate_limits(countryWeightsDict, limit_perm_fun_item)
        result_data_set.append(countryWeightsDict)
        print("Successfully draw result:")
        return countryWeightsDict

    def temp_assign_permutation(self, countryWeights, countryWeightsDict):
        initial_country_weights = countryWeights
        initial_country_weights_dict = countryWeightsDict

        limit_adj_functions = [self._china_limit_process, self._single_name_limit_process, self._top_3_limit_process, \
            self._top_5_bankbook_limit_process, self._nonregional_limit_process, self._avg_rtg_limit_process]

        from itertools import permutations
        limit_fun_perm_full_set = list(permutations(limit_adj_functions))

        #override for debugging purpose
        ###################TODO: to be removed once debugging is done###############################################

        #limit_fun_perm_full_set = [ [self._china_limit_process, self._single_name_limit_process, self._top_3_limit_process, \
        #    self._top_5_bankbook_limit_process, self._nonregional_limit_process, self._avg_rtg_limit_process] ]

        #limit_fun_perm_full_set = limit_fun_perm_full_set[:10]

        ###################TODO: to be removed once debugging is done###############################################

        result_list = []
        for limit_perm_fun_item in limit_fun_perm_full_set:
            countryWeightsDict = self.temp_permuattion_validate_and_adj_risk_weights(initial_country_weights, initial_country_weights_dict, limit_perm_fun_item)
            result_list.append(countryWeightsDict)
        return result_list


    def get_optimized_weight_hhi(self, final_result_df):
        final_result_df.drop_duplicates(keep=False, inplace=True) #remove duplicated results
        print("Unique Solution Numbers: {0}".format(len(final_result_df)))

        final_result_hhi_temp = np.power(final_result_df,2) * 100
        final_result_hhi_temp['sum'] = final_result_hhi_temp[list(final_result_hhi_temp.columns)].sum(axis=1)

        #get optimized HHI score
        hhi_optimized_score = final_result_hhi_temp['sum'].min()

        #filter the most optimized portfolio
        final_result_hhi_temp = final_result_hhi_temp.loc[ final_result_hhi_temp['sum'] == hhi_optimized_score ]

        final_result_hhi = np.sqrt( final_result_hhi_temp / 100 )
        final_result_hhi.drop("sum", axis=1, inplace=True)
        return final_result_hhi

    """     
    def get_optimized_weight_hhi_EL_weighted(self, simulated_df, final_result_dict):
        countries = list(final_result_dict.keys())

        simulated_df_transposed = simulated_df.transpose() #transposed weight table

        dataframe_list = []
        for country in countries:
            temp_df = np.power(simulated_df_transposed[simulated_df_transposed.index == country] * self.utils.sblCountryELDict[country], 2) * 100000000
            dataframe_list.append(temp_df)

        final_result_df = pd.concat(dataframe_list, axis=0)
        final_result_df.loc['Total']= final_result_df.sum()

        final_result_df.reset_index(inplace = True)
        final_result_df.rename(columns={'index':'Country'}, inplace=True)


        final_result_df.drop_duplicates(keep=False, inplace=True)
        print("Unique Solution Numbers: {0}".format(len(final_result_df)))

        final_result_hhi_temp = np.power(final_result_df,2) * 100
        final_result_hhi_temp['sum'] = final_result_hhi_temp[list(final_result_hhi_temp.columns)].sum(axis=1)

        #get optimized HHI score
        hhi_optimized_score = final_result_hhi_temp['sum'].min()

        #filter the most optimized portfolio
        final_result_hhi_temp = final_result_hhi_temp.loc[ final_result_hhi_temp['sum'] == hhi_optimized_score ]

        final_result_hhi = np.sqrt( final_result_hhi_temp / 100 )
        return final_result_hhi 
    """

    def assign_country_weights_main(self):

        def _unpack_weight_results(result_country_weight_sbl_sets):
            
            country_values = list(result_country_weight_sbl_sets[0].keys())
            weight_valus = [[] for item in country_values]
            final_result_dict = dict(zip(country_values, weight_valus))

            for dict_item in result_country_weight_sbl_sets:
                for country_key, weight_value in dict_item.items():
                    final_result_dict[country_key].append(weight_value)

            return final_result_dict

        time_stamp = int(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        countryWeights = list(self.utils.originalCountryWeightsSBL.values())
        
        #Main process: iteratively adjusting the country weights to meet the risk limit policy
        result_country_weight_sbl_sets = self.temp_assign_permutation(countryWeights, self.utils.originalCountryWeightsSBL)

        temp_output = r"C://Working//python//Target_Portfolio_VOct202020_20210309Updated//temp_permutation_sbl_output_{0}_{1}.xlsx"
        final_result_dict = _unpack_weight_results(result_country_weight_sbl_sets)
        final_result_df = pd.DataFrame(final_result_dict)
        print("Final Total Permutation Numbers: {0}".format(len(final_result_df)))

        final_result_df = self.get_optimized_weight_hhi(final_result_df)
        
        writer = pd.ExcelWriter(temp_output.format(PROJECTION_YEAR, time_stamp), engine='xlsxwriter')
        final_result_df.to_excel(writer, "Result", index = False)

        writer.save()
        #return final_result_df

        sbl_CountryWeights = final_result_df.transpose().to_dict()[1]
        return sbl_CountryWeights

if __name__ == "__main__":
    #from itertools import permutations
    #l = list(permutations(range(1, 4))) 
    #print(l)

    def a():
        print("a1")
    
    def b():
        print("b2")

    def c():
        print("c3")

    def d():
        print("d4")

    def e():
        print("e5")

    def f():
        print("f6")

    def g():
        print("g7")

    def h():
        print("h8")

    func_list = [a, b, c, d, e, f, g, h]
    from itertools import permutations
    permutation_list = list(permutations(func_list))
    for l_item in permutation_list:
        result = [ x() for x in l_item ]
    #pBuilder = SBLPortfolioBuilder()
    #outputPath = r'C:\temp\Sovereign_Country_Weights_Target_Portfolio_{0}_{1}.xlsx'.format(PROJECTION_YEAR, int(round(datetime.datetime.now().timestamp(),0)))#r"//WF//Sharefolder//RM//LiangXue//test//country_weight_output_Test.xlsx"

    #countryWeights = pBuilder.assign_country_weights_main()
    #dataframe = pd.DataFrame([a for a in countryWeights.items()], columns = ['Country','Weight'])
    #dataframe.to_excel(outputPath, index = None, header=True, sheet_name='RawResult')